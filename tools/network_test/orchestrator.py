#!/usr/bin/env python3
"""DnD World Builder — Multiplayer Test Orchestrator.

Deploys worker scripts to Raspberry Pis, sends commands, and verifies
multiplayer protocol correctness.

Usage:
    python orchestrator.py --deploy-only          # Push worker to all reachable Pis
    python orchestrator.py --scenario all          # Run all test scenarios
    python orchestrator.py --scenario connection   # Single test
    python orchestrator.py --simulate-cursors      # Visual cursor sweep
    python orchestrator.py --list-scenarios        # Show available scenarios
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print("ERROR: requests required. pip install requests")
    sys.exit(1)

from config import HOST_IP, HOST_PORT, WORKERS, REMOTE_WORKER_DIR, REMOTE_WORKER_SCRIPT


_THIS_DIR = Path(__file__).resolve().parent
_WORKER_SCRIPT = _THIS_DIR / "worker.py"
_REQUIREMENTS = _THIS_DIR / "requirements_worker.txt"


# ── SSH helpers (sshpass + ssh/scp) ───────────────────────────────────


def _ssh(ip: str, user: str, password: str, cmd: str, timeout: int = 30) -> tuple[int, str]:
    """Run a command on a remote host via SSH.

    Uses the native ``ssh`` command (Windows OpenSSH or Git ssh).
    Key-based auth is assumed (password param kept for config compat).
    """
    proc = subprocess.run(
        ["ssh",
         "-o", "StrictHostKeyChecking=no",
         "-o", "ConnectTimeout=10",
         "-o", "BatchMode=yes",
         f"{user}@{ip}", cmd],
        capture_output=True, text=True, timeout=timeout,
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def _scp(ip: str, user: str, password: str, local: Path, remote: str) -> bool:
    """Copy a file to a remote host via SCP.

    Key-based auth is assumed (password param kept for config compat).
    """
    proc = subprocess.run(
        ["scp",
         "-o", "StrictHostKeyChecking=no",
         "-o", "ConnectTimeout=10",
         "-o", "BatchMode=yes",
         str(local), f"{user}@{ip}:{remote}"],
        capture_output=True, text=True, timeout=30,
    )
    return proc.returncode == 0


def _is_reachable(ip: str) -> bool:
    """Quick ping check."""
    proc = subprocess.run(
        ["ping", "-n", "1", "-w", "1000", ip],
        capture_output=True, text=True, timeout=5,
    )
    return "Reply from" in proc.stdout


# ── Worker HTTP API helpers ───────────────────────────────────────────


def _api(worker: dict, endpoint: str, method: str = "GET", data: dict | None = None) -> dict | None:
    """Call a worker's HTTP API. Returns parsed JSON or None on failure."""
    url = f"http://{worker['ip']}:{worker['api_port']}{endpoint}"
    try:
        if method == "GET":
            resp = requests.get(url, timeout=5)
        else:
            resp = requests.post(url, json=data or {}, timeout=5)
        return resp.json()
    except Exception as exc:
        return None


def _wait_for_api(worker: dict, timeout: int = 15) -> bool:
    """Wait until a worker's HTTP API responds."""
    start = time.time()
    while time.time() - start < timeout:
        result = _api(worker, "/status")
        if result is not None:
            return True
        time.sleep(1)
    return False


def _wait_for_connection(worker: dict, timeout: int = 20) -> bool:
    """Wait until a worker reports connected=True."""
    start = time.time()
    while time.time() - start < timeout:
        status = _api(worker, "/status")
        if status and status.get("connected"):
            return True
        time.sleep(1)
    return False


def _get_log(worker: dict, msg_type: str | None = None) -> list[dict]:
    """Fetch the worker's message log, optionally filtered by type."""
    endpoint = "/log" if not msg_type else f"/log?type={msg_type}"
    result = _api(worker, endpoint)
    return result if isinstance(result, list) else []


# ── Deploy ────────────────────────────────────────────────────────────


def deploy(workers: list[dict]) -> list[dict]:
    """Deploy worker.py to all reachable Pis. Returns list of successfully deployed workers."""
    deployed = []
    for w in workers:
        name, ip = w["name"], w["ip"]
        print(f"\n[{name}] Checking {ip}...")

        if not _is_reachable(ip):
            print(f"  SKIP: {ip} unreachable")
            continue

        # Create remote directory
        rc, out = _ssh(ip, w["ssh_user"], w["ssh_pass"], f"mkdir -p {REMOTE_WORKER_DIR}")
        if rc != 0:
            print(f"  FAIL: mkdir failed: {out}")
            continue

        # Copy worker script
        if not _scp(ip, w["ssh_user"], w["ssh_pass"], _WORKER_SCRIPT, REMOTE_WORKER_SCRIPT):
            print(f"  FAIL: scp worker.py failed")
            continue

        # Copy requirements
        _scp(ip, w["ssh_user"], w["ssh_pass"], _REQUIREMENTS,
             f"{REMOTE_WORKER_DIR}/requirements_worker.txt")

        # Install deps (best-effort — may already be installed)
        _ssh(ip, w["ssh_user"], w["ssh_pass"],
             f"pip3 install -q -r {REMOTE_WORKER_DIR}/requirements_worker.txt 2>/dev/null || true")

        print(f"  OK: deployed to {ip}")
        deployed.append(w)

    return deployed


def start_workers(workers: list[dict]) -> None:
    """Start the worker script on each deployed Pi (kills any existing instance first)."""
    for w in workers:
        ip = w["ip"]
        name = w["name"]
        print(f"[{name}] Starting worker on {ip}...")

        # Kill any existing worker
        _ssh(ip, w["ssh_user"], w["ssh_pass"],
             "pkill -f 'python3.*worker.py' 2>/dev/null || true")
        time.sleep(1)

        # Start in background
        cmd = (
            f"cd {REMOTE_WORKER_DIR} && "
            f"nohup python3 worker.py "
            f"--host {HOST_IP} --port {HOST_PORT} "
            f"--name '{name}' --api-port {w['api_port']} "
            f"> worker.log 2>&1 &"
        )
        _ssh(ip, w["ssh_user"], w["ssh_pass"], cmd)
        print(f"  Started (waiting for API...)")

        if _wait_for_api(w):
            print(f"  API responding on :{w['api_port']}")
        else:
            print(f"  WARNING: API not responding after 15s")


def stop_workers(workers: list[dict]) -> None:
    """Stop worker scripts on all Pis."""
    for w in workers:
        _ssh(w["ip"], w["ssh_user"], w["ssh_pass"],
             "pkill -f 'python3.*worker.py' 2>/dev/null || true")
        print(f"[{w['name']}] Stopped")


# ── Test scenarios ────────────────────────────────────────────────────


def test_connection(workers: list[dict]) -> bool:
    """Verify all workers connected and received WELCOME."""
    print("\n=== Test: Connection ===")
    all_ok = True
    for w in workers:
        status = _api(w, "/status")
        if not status:
            print(f"  [{w['name']}] FAIL: API unreachable")
            all_ok = False
            continue
        if not status.get("connected"):
            print(f"  [{w['name']}] FAIL: not connected")
            all_ok = False
            continue
        pid = status.get("player_id", "?")
        color = status.get("color", "?")
        print(f"  [{w['name']}] OK: player_id={pid}, color={color}")
    return all_ok


def test_chat(workers: list[dict]) -> bool:
    """Worker A sends chat → Worker B receives it."""
    print("\n=== Test: Chat Relay ===")
    if len(workers) < 2:
        print("  SKIP: need at least 2 workers")
        return True

    a, b = workers[0], workers[1]

    # Clear logs
    _api(b, "/clear_log", method="POST")

    # A sends chat
    _api(a, "/chat", method="POST", data={"message": "Hello from test!"})
    time.sleep(2)

    # B should have received it
    log_entries = _get_log(b, "CHAT")
    received = any("Hello from test" in str(e.get("payload", {})) for e in log_entries)
    if received:
        print(f"  [{b['name']}] OK: received chat from {a['name']}")
        return True
    else:
        print(f"  [{b['name']}] FAIL: no chat received (log: {len(log_entries)} entries)")
        return False


def test_cursor(workers: list[dict]) -> bool:
    """Worker A sends cursor position → Worker B receives CURSOR_UPDATE."""
    print("\n=== Test: Cursor Sharing ===")
    if len(workers) < 2:
        print("  SKIP: need at least 2 workers")
        return True

    a, b = workers[0], workers[1]
    _api(b, "/clear_log", method="POST")

    _api(a, "/cursor", method="POST", data={"x": 150.5, "y": 300.0})
    time.sleep(2)

    log_entries = _get_log(b, "CURSOR_UPDATE")
    received = any(
        abs(e.get("payload", {}).get("x", 0) - 150.5) < 1
        for e in log_entries
    )
    if received:
        print(f"  [{b['name']}] OK: received cursor update from {a['name']}")
        return True
    else:
        print(f"  [{b['name']}] FAIL: no cursor update received")
        return False


def test_draw(workers: list[dict]) -> bool:
    """Worker A sends draw stroke → Worker B receives DRAW_STROKE."""
    print("\n=== Test: Draw Stroke ===")
    if len(workers) < 2:
        print("  SKIP: need at least 2 workers")
        return True

    a, b = workers[0], workers[1]
    _api(b, "/clear_log", method="POST")

    points = [[0, 0], [50, 50], [100, 0]]
    _api(a, "/draw", method="POST", data={"points": points})
    time.sleep(2)

    log_entries = _get_log(b, "DRAW_STROKE")
    if log_entries:
        print(f"  [{b['name']}] OK: received draw stroke ({len(log_entries[0].get('payload', {}).get('points', []))} points)")
        return True
    else:
        print(f"  [{b['name']}] FAIL: no draw stroke received")
        return False


def test_claim(workers: list[dict]) -> bool:
    """Worker A claims an entity → all workers see ENTITY_CLAIMED."""
    print("\n=== Test: Entity Claim ===")
    a = workers[0]
    status = _api(a, "/status")
    entities = status.get("available_entities", []) if status else []
    if not entities:
        print(f"  SKIP: no claimable entities")
        return True

    entity_name = entities[0]
    for w in workers:
        _api(w, "/clear_log", method="POST")

    _api(a, "/claim", method="POST", data={"entity_id": entity_name})
    time.sleep(2)

    # Check all workers received the claim broadcast
    all_ok = True
    for w in workers:
        log_entries = _get_log(w, "ENTITY_CLAIMED")
        if log_entries:
            print(f"  [{w['name']}] OK: saw claim for {entity_name}")
        else:
            # Sender might not get the broadcast back (exclude=sender)
            if w == a:
                print(f"  [{w['name']}] OK: sender (excluded from broadcast)")
            else:
                print(f"  [{w['name']}] FAIL: missed claim broadcast")
                all_ok = False
    return all_ok


def test_disconnect(workers: list[dict]) -> bool:
    """Worker A disconnects → others remain connected."""
    print("\n=== Test: Disconnect ===")
    if len(workers) < 2:
        print("  SKIP: need at least 2 workers")
        return True

    a, b = workers[0], workers[1]
    _api(a, "/disconnect", method="POST")
    time.sleep(3)

    # A should be disconnected
    status_a = _api(a, "/status")
    a_ok = status_a and not status_a.get("connected", True)

    # B should still be connected
    status_b = _api(b, "/status")
    b_ok = status_b and status_b.get("connected", False)

    if a_ok:
        print(f"  [{a['name']}] OK: disconnected")
    else:
        print(f"  [{a['name']}] FAIL: still shows connected")
    if b_ok:
        print(f"  [{b['name']}] OK: still connected")
    else:
        print(f"  [{b['name']}] FAIL: lost connection")

    return a_ok and b_ok


SCENARIOS = {
    "connection": test_connection,
    "chat": test_chat,
    "cursor": test_cursor,
    "draw": test_draw,
    "claim": test_claim,
    "disconnect": test_disconnect,
}


# ── Cursor simulation ─────────────────────────────────────────────────


def simulate_cursors(workers: list[dict], duration: int = 30) -> None:
    """Make each worker sweep its cursor across the map in a distinct pattern."""
    print(f"\n=== Cursor Simulation ({duration}s) ===")
    print("  Watch the DM's map for colored cursor ghosts moving.")
    print("  Press Ctrl+C to stop early.\n")

    start = time.time()
    step = 0
    try:
        while time.time() - start < duration:
            t = time.time() - start
            for i, w in enumerate(workers):
                if i == 0:
                    # Horizontal sweep
                    x = (t * 30) % 600
                    y = 300
                elif i == 1:
                    # Vertical sweep
                    x = 300
                    y = (t * 30) % 600
                else:
                    # Circular
                    x = 300 + 200 * math.cos(t * 0.5)
                    y = 300 + 200 * math.sin(t * 0.5)
                _api(w, "/cursor", method="POST", data={"x": x, "y": y})

            step += 1
            if step % 15 == 0:
                elapsed = int(time.time() - start)
                print(f"  {elapsed}s / {duration}s")
            time.sleep(0.066)  # ~15Hz
    except KeyboardInterrupt:
        print("\n  Stopped by user")
    print("  Simulation complete")


# ── Main ──────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="DnD Multiplayer Test Orchestrator")
    parser.add_argument("--deploy-only", action="store_true", help="Deploy workers, don't run tests")
    parser.add_argument("--scenario", default="all", help="Test scenario to run (or 'all')")
    parser.add_argument("--simulate-cursors", action="store_true", help="Visual cursor sweep")
    parser.add_argument("--list-scenarios", action="store_true", help="List available scenarios")
    parser.add_argument("--stop", action="store_true", help="Stop all workers")
    parser.add_argument("--workers", type=str, help="Comma-separated worker indices (0,1,2)")
    args = parser.parse_args()

    if args.list_scenarios:
        for name in sorted(SCENARIOS):
            print(f"  {name}")
        return 0

    # Filter workers if specified
    active_workers = WORKERS
    if args.workers:
        indices = [int(i) for i in args.workers.split(",")]
        active_workers = [WORKERS[i] for i in indices if i < len(WORKERS)]

    if args.stop:
        stop_workers(active_workers)
        return 0

    # Deploy
    print("=" * 60)
    print("DEPLOYING WORKERS")
    print("=" * 60)
    deployed = deploy(active_workers)

    if not deployed:
        print("\nNo workers deployed. Check Pi connectivity.")
        return 1

    if args.deploy_only:
        print(f"\nDeployed to {len(deployed)} workers. Starting...")
        start_workers(deployed)
        print("\nWorkers are running. Use --scenario to run tests.")
        return 0

    # Start workers and wait for connections
    start_workers(deployed)
    print(f"\nWaiting for workers to connect to host at {HOST_IP}:{HOST_PORT}...")
    connected = []
    for w in deployed:
        if _wait_for_connection(w):
            connected.append(w)
            print(f"  [{w['name']}] Connected")
        else:
            print(f"  [{w['name']}] TIMEOUT — not connected")

    if not connected:
        print("\nNo workers connected. Is the DnD host running in multiplayer mode?")
        stop_workers(deployed)
        return 1

    if args.simulate_cursors:
        simulate_cursors(connected)
        stop_workers(deployed)
        return 0

    # Run test scenarios
    print("\n" + "=" * 60)
    print("RUNNING TESTS")
    print("=" * 60)

    scenarios_to_run = (
        list(SCENARIOS.items())
        if args.scenario == "all"
        else [(args.scenario, SCENARIOS.get(args.scenario))]
    )

    results = {}
    for name, test_fn in scenarios_to_run:
        if test_fn is None:
            print(f"\nUnknown scenario: {name}")
            continue
        try:
            results[name] = test_fn(connected)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            results[name] = False

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  {name:20s} {status}")
    print(f"\n  {passed} passed, {failed} failed")

    # Cleanup
    stop_workers(deployed)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
