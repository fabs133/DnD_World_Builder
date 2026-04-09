#!/usr/bin/env python3
"""Pre-playtest network reliability smoke test.

Verifies that ReliableChannel delivers messages under various adverse
conditions. Run before every multiplayer session.

Usage::

    python tools/network_smoke.py
    python tools/network_smoke.py --clients 4 --messages 50
    python tools/network_smoke.py --verbose

Exit code 0 = all green, 1 = any failure.

No Qt or UI imports — runs headless in a plain Python process.
"""

from __future__ import annotations

import argparse
import asyncio
import socket
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from network.websocket_transport import WebSocketServer, WebSocketClient
from network.chaos_transport import (
    ChaosConnection, ChaosScenario,
    CLEAN, HIGH_LATENCY, SLOW_LOSSY, SUDDEN_DISCONNECT,
)
from network.reliable_channel import ReliableChannel, PING_TIMEOUT
from network.protocol import make_turn_change, Message


ALL_SCENARIOS = [CLEAN, HIGH_LATENCY, SLOW_LOSSY, SUDDEN_DISCONNECT]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@dataclass
class ScenarioResult:
    scenario: str
    n_clients: int
    n_messages: int
    expected: int
    delivered: int
    disconnect_detected: bool
    elapsed: float
    passed: bool
    error: str = ""


async def run_scenario(scenario: ChaosScenario, n_clients: int,
                       n_messages: int, verbose: bool) -> ScenarioResult:
    """Run a single scenario and return results."""
    port = _free_port()
    is_disconnect = scenario.disconnect_after > 0
    t0 = time.perf_counter()

    server = WebSocketServer("127.0.0.1", port)
    done_events: list[asyncio.Event] = []
    server_channels: list[ReliableChannel] = []
    conn_events: list[asyncio.Event] = []
    conn_idx = [0]

    for _ in range(n_clients):
        conn_events.append(asyncio.Event())
        done_events.append(asyncio.Event())

    async def on_conn(conn):
        i = conn_idx[0]
        conn_idx[0] += 1
        chaos = ChaosConnection(conn, scenario)
        ch = ReliableChannel(chaos, f"smoke-server-{i}")
        server_channels.append(ch)
        await ch.start()
        if i < len(conn_events):
            conn_events[i].set()
        if i < len(done_events):
            await done_events[i].wait()

    server.on_connection(on_conn)

    try:
        await server.start()
    except Exception as e:
        return ScenarioResult(
            scenario=scenario.name, n_clients=n_clients, n_messages=n_messages,
            expected=0, delivered=0, disconnect_detected=False,
            elapsed=0, passed=False, error=f"Server bind failed: {e}")

    client_channels: list[ReliableChannel] = []
    ws_clients: list[WebSocketClient] = []
    disconnect_flags: list[asyncio.Event] = []

    try:
        # Connect clients
        for i in range(n_clients):
            wsc = WebSocketClient("127.0.0.1", port)
            raw = await wsc.connect()
            chaos = ChaosConnection(raw, scenario)
            ch = ReliableChannel(chaos, f"smoke-client-{i}")

            dc_event = asyncio.Event()
            ch.on_disconnect = lambda _e=dc_event: _e.set()
            disconnect_flags.append(dc_event)

            await ch.start()
            client_channels.append(ch)
            ws_clients.append(wsc)
            await asyncio.wait_for(conn_events[i].wait(), timeout=3.0)

        if is_disconnect:
            # For disconnect scenario: send until error, check detection
            detected = False
            for sch in server_channels:
                for j in range(n_messages):
                    try:
                        msg = make_turn_change(f"e_{j}", j)
                        await sch.fire(msg)
                    except (ConnectionError, OSError):
                        break
                    await asyncio.sleep(0.01)

            # Wait for at least one client to detect disconnect
            for df in disconnect_flags:
                try:
                    await asyncio.wait_for(df.wait(), timeout=PING_TIMEOUT + 5)
                    detected = True
                    break
                except asyncio.TimeoutError:
                    continue

            elapsed = time.perf_counter() - t0
            return ScenarioResult(
                scenario=scenario.name, n_clients=n_clients,
                n_messages=n_messages, expected=0, delivered=0,
                disconnect_detected=detected, elapsed=elapsed,
                passed=detected)

        else:
            # Delivery scenario: collect messages
            expected = n_clients * n_messages
            collectors = []
            for cch in client_channels:
                messages: list[Message] = []
                evt = asyncio.Event()

                def _handler(msg, _m=messages, _e=evt, _n=n_messages):
                    _m.append(msg)
                    if len(_m) >= _n:
                        _e.set()

                cch.on_message = _handler
                collectors.append((messages, evt))

            # Server broadcasts to each client
            for i in range(n_messages):
                msg = make_turn_change(f"entity_{i}", i)
                for sch in server_channels:
                    await sch.request(msg)

            # Wait for delivery
            timeout = 5.0 if scenario == CLEAN else 15.0
            for messages, evt in collectors:
                try:
                    await asyncio.wait_for(evt.wait(), timeout=timeout)
                except asyncio.TimeoutError:
                    pass

            delivered = sum(len(m) for m, _ in collectors)
            elapsed = time.perf_counter() - t0

            if verbose:
                for i, (messages, _) in enumerate(collectors):
                    print(f"  Client {i}: {len(messages)}/{n_messages}")

            return ScenarioResult(
                scenario=scenario.name, n_clients=n_clients,
                n_messages=n_messages, expected=expected, delivered=delivered,
                disconnect_detected=False, elapsed=elapsed,
                passed=(delivered == expected))

    except Exception as e:
        elapsed = time.perf_counter() - t0
        return ScenarioResult(
            scenario=scenario.name, n_clients=n_clients,
            n_messages=n_messages, expected=0, delivered=0,
            disconnect_detected=False, elapsed=elapsed,
            passed=False, error=str(e))

    finally:
        for ch in client_channels:
            await ch.stop()
        for ch in server_channels:
            await ch.stop()
        for de in done_events:
            de.set()
        await asyncio.sleep(0.1)
        for wsc in ws_clients:
            await wsc.close_session()
        await server.stop()


async def run_all(n_clients: int, n_messages: int, verbose: bool) -> list[ScenarioResult]:
    results = []
    for scenario in ALL_SCENARIOS:
        if verbose:
            print(f"\nRunning {scenario.name}...")
        result = await run_scenario(scenario, n_clients, n_messages, verbose)
        results.append(result)
    return results


def print_table(results: list[ScenarioResult]) -> None:
    print()
    print("DnD World Builder - Network Smoke Test")
    print("=" * 70)
    print(f"{'Scenario':<22} {'Clients':>7}  {'Messages':>8}  {'Delivered':>10}  {'Status'}")
    print("-" * 70)

    for r in results:
        if r.scenario == "SUDDEN_DISCONNECT":
            delivered_str = "n/a"
            status = "PASS (disconnect detected)" if r.passed else "FAIL (no disconnect)"
        else:
            delivered_str = f"{r.delivered}/{r.expected}"
            status = "PASS" if r.passed else "FAIL"

        if r.error:
            status = f"FAIL ({r.error})"

        print(f"{r.scenario:<22} {r.n_clients:>7}  {r.n_messages:>8}  {delivered_str:>10}  {status}")

    print("-" * 70)
    all_pass = all(r.passed for r in results)
    if all_pass:
        print("Overall: PASS - session is ready to host")
    else:
        print("Overall: FAIL - fix connection issues before hosting")
        for r in results:
            if not r.passed:
                reason = r.error or f"only {r.delivered}/{r.expected} delivered"
                print(f"  FAIL {r.scenario}: {reason}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pre-playtest network reliability smoke test")
    parser.add_argument("--clients", type=int, default=3,
                        help="Number of simulated players (default: 3)")
    parser.add_argument("--messages", type=int, default=30,
                        help="Messages per client per scenario (default: 30)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print per-client delivery details")
    args = parser.parse_args()

    results = asyncio.run(run_all(args.clients, args.messages, args.verbose))
    print_table(results)
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
