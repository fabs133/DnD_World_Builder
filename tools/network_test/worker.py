#!/usr/bin/env python3
"""DnD World Builder — Multiplayer Test Worker.

Self-contained WebSocket client that connects to a DnD host session
as a simulated player. Exposes a tiny HTTP API so the orchestrator
can send commands (chat, cursor, draw, claim, action) from outside.

Designed to run on Raspberry Pis with only ``aiohttp`` as a dependency.
No imports from the DnD project — protocol knowledge is inlined.

Usage:
    python3 worker.py --host 192.168.178.30 --port 8765 --name "Player 1"
    python3 worker.py --host 192.168.178.30 --port 8765 --name "Player 1" --api-port 9100
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from collections import deque
from typing import Any

import aiohttp
from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("worker")

# ── Inlined protocol constants ────────────────────────────────────────

PROTOCOL_VERSION = "1.0"


def _make_msg(msg_type: str, payload: dict | None = None) -> str:
    """Build a JSON message string matching the DnD protocol format."""
    return json.dumps({
        "type": msg_type,
        "seq": 0,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "payload": payload or {},
    })


# ── Worker state ──────────────────────────────────────────────────────


class WorkerState:
    """Tracks the worker's connection and game state."""

    def __init__(self, player_name: str):
        self.player_name = player_name
        self.player_id: str = ""
        self.session_id: str = ""
        self.color: str = "#888888"
        self.claimed_entity: str = ""
        self.connected = False
        self.available_entities: list[dict] = []
        self.message_log: deque[dict] = deque(maxlen=100)
        self.ws: aiohttp.ClientWebSocketResponse | None = None

    def to_status(self) -> dict:
        return {
            "player_name": self.player_name,
            "player_id": self.player_id,
            "session_id": self.session_id,
            "color": self.color,
            "claimed_entity": self.claimed_entity,
            "connected": self.connected,
            "available_entities": [
                e.get("name", "?") for e in self.available_entities
            ],
            "log_count": len(self.message_log),
        }


# ── WebSocket client ──────────────────────────────────────────────────


async def ws_connect(
    state: WorkerState,
    host: str,
    port: int,
) -> None:
    """Connect to the DnD host, perform handshake, and enter listen loop."""
    url = f"http://{host}:{port}/ws"
    log.info(f"Connecting to {url} as '{state.player_name}'...")

    async with aiohttp.ClientSession() as session:
        try:
            ws = await session.ws_connect(url, timeout=10)
        except Exception as exc:
            log.error(f"Connection failed: {exc}")
            return

        state.ws = ws
        state.connected = True

        # 1. Send HELLO
        hello = _make_msg("HELLO", {
            "player_name": state.player_name,
            "version": PROTOCOL_VERSION,
        })
        await ws.send_str(hello)
        log.info("Sent HELLO")

        # 2. Wait for WELCOME
        raw = await ws.receive_str(timeout=10)
        msg = json.loads(raw)
        if msg.get("type") == "ERROR":
            log.error(f"Handshake rejected: {msg.get('payload', {}).get('message')}")
            state.connected = False
            return
        if msg.get("type") != "WELCOME":
            log.error(f"Expected WELCOME, got {msg.get('type')}")
            state.connected = False
            return

        payload = msg.get("payload", {})
        state.player_id = payload.get("player_id", "")
        state.session_id = payload.get("session_id", "")
        state.color = payload.get("color", "#888888")
        state.available_entities = payload.get("entities", [])
        log.info(
            f"Connected: player_id={state.player_id}, "
            f"color={state.color}, "
            f"entities={len(state.available_entities)}"
        )

        # 3. Listen loop
        try:
            async for ws_msg in ws:
                if ws_msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(ws_msg.data)
                        state.message_log.append({
                            "time": time.time(),
                            "type": data.get("type", "?"),
                            "payload": data.get("payload", {}),
                        })
                        msg_type = data.get("type", "?")
                        log.debug(f"Received: {msg_type}")

                        # Track entity claims
                        if msg_type == "ENTITY_CLAIMED":
                            p = data.get("payload", {})
                            if p.get("player_id") == state.player_id:
                                state.claimed_entity = p.get("entity_id", "")
                    except json.JSONDecodeError:
                        log.warning(f"Non-JSON message: {ws_msg.data[:100]}")
                elif ws_msg.type in (
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.ERROR,
                ):
                    break
        except Exception as exc:
            log.error(f"Listen loop error: {exc}")
        finally:
            state.connected = False
            state.ws = None
            log.info("Disconnected")


# ── HTTP command API ──────────────────────────────────────────────────


def build_api(state: WorkerState) -> web.Application:
    """Build the aiohttp web app for the orchestrator command API."""

    async def handle_status(request: web.Request) -> web.Response:
        return web.json_response(state.to_status())

    async def handle_log(request: web.Request) -> web.Response:
        # Optional filter by message type
        msg_type = request.query.get("type")
        entries = list(state.message_log)
        if msg_type:
            entries = [e for e in entries if e["type"] == msg_type]
        return web.json_response(entries)

    async def handle_chat(request: web.Request) -> web.Response:
        data = await request.json()
        if not state.ws or state.ws.closed:
            return web.json_response({"error": "not connected"}, status=503)
        msg = _make_msg("CHAT", {
            "sender": state.player_name,
            "message": data.get("message", ""),
        })
        await state.ws.send_str(msg)
        return web.json_response({"ok": True})

    async def handle_claim(request: web.Request) -> web.Response:
        data = await request.json()
        if not state.ws or state.ws.closed:
            return web.json_response({"error": "not connected"}, status=503)
        msg = _make_msg("CLAIM_ENTITY", {
            "entity_id": data.get("entity_id", ""),
        })
        await state.ws.send_str(msg)
        return web.json_response({"ok": True})

    async def handle_cursor(request: web.Request) -> web.Response:
        data = await request.json()
        if not state.ws or state.ws.closed:
            return web.json_response({"error": "not connected"}, status=503)
        msg = _make_msg("CURSOR_UPDATE", {
            "player_id": state.player_id,
            "player_name": state.player_name,
            "x": float(data.get("x", 0)),
            "y": float(data.get("y", 0)),
            "color": state.color,
        })
        await state.ws.send_str(msg)
        return web.json_response({"ok": True})

    async def handle_draw(request: web.Request) -> web.Response:
        data = await request.json()
        if not state.ws or state.ws.closed:
            return web.json_response({"error": "not connected"}, status=503)
        msg = _make_msg("DRAW_STROKE", {
            "player_id": state.player_id,
            "points": data.get("points", []),
            "color": state.color,
        })
        await state.ws.send_str(msg)
        return web.json_response({"ok": True})

    async def handle_action(request: web.Request) -> web.Response:
        data = await request.json()
        if not state.ws or state.ws.closed:
            return web.json_response({"error": "not connected"}, status=503)
        msg = _make_msg("ACTION_REQUEST", {
            "action_type": data.get("action_type", ""),
            "params": data.get("params", {}),
        })
        await state.ws.send_str(msg)
        return web.json_response({"ok": True})

    async def handle_disconnect(request: web.Request) -> web.Response:
        if state.ws and not state.ws.closed:
            msg = _make_msg("DISCONNECT")
            await state.ws.send_str(msg)
            await state.ws.close()
        return web.json_response({"ok": True})

    async def handle_clear_log(request: web.Request) -> web.Response:
        state.message_log.clear()
        return web.json_response({"ok": True})

    app = web.Application()
    app.router.add_get("/status", handle_status)
    app.router.add_get("/log", handle_log)
    app.router.add_post("/chat", handle_chat)
    app.router.add_post("/claim", handle_claim)
    app.router.add_post("/cursor", handle_cursor)
    app.router.add_post("/draw", handle_draw)
    app.router.add_post("/action", handle_action)
    app.router.add_post("/disconnect", handle_disconnect)
    app.router.add_post("/clear_log", handle_clear_log)
    return app


# ── Main ──────────────────────────────────────────────────────────────


async def main(host: str, port: int, name: str, api_port: int) -> None:
    state = WorkerState(name)

    # Start both the WebSocket client and HTTP API concurrently
    api_app = build_api(state)
    runner = web.AppRunner(api_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", api_port)
    await site.start()
    log.info(f"HTTP API listening on :{api_port}")

    # Connect to the DnD host (reconnects on failure)
    while True:
        try:
            await ws_connect(state, host, port)
        except Exception as exc:
            log.error(f"Connection error: {exc}")
        log.info("Reconnecting in 5s...")
        await asyncio.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DnD Multiplayer Test Worker")
    parser.add_argument("--host", default="192.168.178.30", help="DnD host IP")
    parser.add_argument("--port", type=int, default=8765, help="DnD host port")
    parser.add_argument("--name", default="TestPlayer", help="Player display name")
    parser.add_argument("--api-port", type=int, default=9100, help="HTTP API port")
    args = parser.parse_args()

    asyncio.run(main(args.host, args.port, args.name, args.api_port))
