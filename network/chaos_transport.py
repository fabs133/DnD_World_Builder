"""Chaos transport — TEST-ONLY fault injection for network reliability testing.

This module wraps any :class:`~network.transport.TransportConnection` and
injects configurable fault conditions so the :class:`~network.reliable_channel.ReliableChannel`
retry/ACK/heartbeat logic can be exercised under adverse conditions.

**Never import this module in production code.**

How the parameters map to real conditions:

- ``delay_ms`` simulates **one-way latency**. A value of 200 means each
  ``send()`` and ``recv()`` sleeps 200 ms, so the observed round-trip time
  is approximately ``2 × delay_ms``.

- ``disconnect_after`` triggers a hard :class:`ConnectionError` on the
  *N*-th ``send()`` call (0-indexed: sends 0 .. N-1 succeed, send N fails).
  The :class:`ReliableChannel` ``PING_TIMEOUT`` window determines how
  quickly the peer detects the dead connection.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from network.transport import TransportConnection, TransportClient


# ── Scenario definitions ─────────────────────────────────────────

@dataclass
class ChaosScenario:
    """Configurable fault scenario for a chaos-wrapped connection."""

    name: str
    delay_ms: float = 0.0
    disconnect_after: int = 0


CLEAN = ChaosScenario(name="CLEAN")
HIGH_LATENCY = ChaosScenario(name="HIGH_LATENCY", delay_ms=200.0)
SUDDEN_DISCONNECT = ChaosScenario(name="SUDDEN_DISCONNECT", disconnect_after=10)
SLOW_LOSSY = ChaosScenario(name="SLOW_LOSSY", delay_ms=100.0)


# ── ChaosConnection ─────────────────────────────────────────────

class ChaosConnection(TransportConnection):
    """Wraps a transport connection and injects faults per the scenario."""

    def __init__(self, inner: TransportConnection, scenario: ChaosScenario):
        self._inner = inner
        self._scenario = scenario
        self._send_count = 0

    async def send(self, data: str) -> None:
        if self._inner.closed:
            raise ConnectionError("ChaosTransport: connection closed")

        # Check disconnect threshold BEFORE sending
        if (self._scenario.disconnect_after > 0
                and self._send_count >= self._scenario.disconnect_after):
            await self._inner.close()
            raise ConnectionError("ChaosTransport: forced disconnect")

        # Inject send delay
        if self._scenario.delay_ms > 0:
            await asyncio.sleep(self._scenario.delay_ms / 1000.0)

        await self._inner.send(data)
        self._send_count += 1

    async def recv(self) -> str:
        data = await self._inner.recv()

        # Inject recv delay
        if self._scenario.delay_ms > 0:
            await asyncio.sleep(self._scenario.delay_ms / 1000.0)

        return data

    async def close(self) -> None:
        await self._inner.close()

    @property
    def closed(self) -> bool:
        return self._inner.closed


# ── ChaosClient ──────────────────────────────────────────────────

class ChaosClient(TransportClient):
    """Wraps a transport client so that ``connect()`` returns a ChaosConnection."""

    def __init__(self, inner: TransportClient, scenario: ChaosScenario):
        self._inner = inner
        self._scenario = scenario

    async def connect(self) -> ChaosConnection:
        conn = await self._inner.connect()
        return ChaosConnection(conn, self._scenario)
