"""Reliable communication channel over a WebSocket connection.

Wraps a raw :class:`~network.transport.TransportConnection` and adds:
- **fire(msg)** — send without waiting (cursor, ping, chat)
- **request(msg)** — send and wait for ACK with retry (critical messages)
- Heartbeat ping every ``PING_INTERVAL`` seconds
- Dead connection detection after ``PING_TIMEOUT`` seconds with no data
- Per-send timeout (``SEND_TIMEOUT``)
- Auto-increment sequence numbers
- Deduplication of retried messages on the receiving end

Both the session host and client instantiate one ``ReliableChannel`` per
connection. The host creates one per player; the client creates one for
its server connection.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Any, Callable

from network.protocol import (
    Message, MessageType, CRITICAL_TYPES, make_ack,
)

logger = logging.getLogger(__name__)


# ── Constants ─────────────────────────────────────────────────────────

PING_INTERVAL: float = 10.0    # seconds between heartbeat pings
PING_TIMEOUT: float = 30.0     # seconds without any message → dead
SEND_TIMEOUT: float = 5.0      # seconds per individual send attempt
MAX_RETRIES: int = 3            # request mode retry count
DEDUP_WINDOW: int = 50          # last N sequence numbers tracked


# ── ReliableChannel ───────────────────────────────────────────────────


class ReliableChannel:
    """Reliable communication channel wrapping a WebSocket connection.

    :param conn: The underlying transport connection (must support
        async ``send(str)``, ``recv() -> str``, ``close()``, and a
        ``closed`` property).
    :param channel_id: Human-readable identifier for logging (e.g.
        player ID or ``"client"``).
    """

    def __init__(self, conn: Any, channel_id: str = ""):
        self.conn = conn
        self.channel_id = channel_id

        # Callbacks set by the owner (host / client)
        self.on_message: Callable[[Message], None] | None = None
        self.on_disconnect: Callable[[], None] | None = None

        # Internal state
        self._seq: int = 0
        self._pending_acks: dict[int, asyncio.Future] = {}
        self._seen_seqs: deque[int] = deque(maxlen=DEDUP_WINDOW)
        self._last_seen: float = time.time()
        self._alive: bool = True
        self._heartbeat_task: asyncio.Task | None = None
        self._listen_task: asyncio.Task | None = None

    # ── Lifecycle ─────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the listen loop and heartbeat as background tasks."""
        self._alive = True
        self._listen_task = asyncio.ensure_future(self._listen_loop())
        self._heartbeat_task = asyncio.ensure_future(self._heartbeat_loop())

    async def stop(self) -> None:
        """Gracefully shut down the channel."""
        self._alive = False
        for task in (self._heartbeat_task, self._listen_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
        # Resolve any pending ACKs as failed
        for future in self._pending_acks.values():
            if not future.done():
                future.cancel()
        self._pending_acks.clear()

    @property
    def alive(self) -> bool:
        return self._alive and not self.conn.closed

    # ── Sequence number ───────────────────────────────────────────

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    # ── Fire mode (no ACK) ────────────────────────────────────────

    async def fire(self, msg: Message) -> bool:
        """Send a message without waiting for acknowledgement.

        Returns ``True`` on success, ``False`` if the send failed
        (connection dead or timed out).
        """
        if not self._alive or self.conn.closed:
            return False
        msg.seq = self._next_seq()
        try:
            await asyncio.wait_for(
                self.conn.send(msg.to_json()),
                timeout=SEND_TIMEOUT,
            )
            return True
        except (ConnectionError, asyncio.TimeoutError, OSError) as exc:
            logger.debug(
                f"[{self.channel_id}] fire failed: {exc.__class__.__name__}"
            )
            self._handle_dead()
            return False

    # ── Request mode (wait for ACK) ───────────────────────────────

    async def request(
        self,
        msg: Message,
        retries: int = MAX_RETRIES,
        timeout: float = 5.0,
    ) -> bool:
        """Send a message and wait for an ACK.

        Retries with exponential backoff on timeout. Returns ``True`` if
        an ACK was received, ``False`` if all retries were exhausted or
        the connection died.
        """
        seq = self._next_seq()
        msg.seq = seq

        for attempt in range(retries):
            if not self._alive or self.conn.closed:
                return False

            loop = asyncio.get_running_loop()
            future: asyncio.Future = loop.create_future()
            self._pending_acks[seq] = future

            try:
                await asyncio.wait_for(
                    self.conn.send(msg.to_json()),
                    timeout=SEND_TIMEOUT,
                )
                await asyncio.wait_for(future, timeout=timeout)
                return True
            except asyncio.TimeoutError:
                backoff = min(2 ** attempt, 10)
                logger.debug(
                    f"[{self.channel_id}] request seq={seq} timeout "
                    f"(attempt {attempt + 1}/{retries}), backoff {backoff}s"
                )
                await asyncio.sleep(backoff)
            except (ConnectionError, OSError):
                self._handle_dead()
                return False
            finally:
                self._pending_acks.pop(seq, None)

        logger.warning(
            f"[{self.channel_id}] request seq={seq} failed after "
            f"{retries} retries"
        )
        return False

    # ── Receive loop ──────────────────────────────────────────────

    async def _listen_loop(self) -> None:
        """Main receive loop. Dispatches messages and handles ACKs/pings."""
        while self._alive and not self.conn.closed:
            try:
                raw = await asyncio.wait_for(
                    self.conn.recv(),
                    timeout=PING_TIMEOUT,
                )
                msg = Message.from_json(raw)
                self._last_seen = time.time()

                # Handle protocol-level messages internally
                if msg.type == MessageType.PING:
                    await self.fire(Message(type=MessageType.PONG))
                    continue
                elif msg.type == MessageType.PONG:
                    # Just updates _last_seen (done above)
                    continue
                elif msg.type == MessageType.ACK:
                    self._resolve_ack(msg.payload.get("ack_seq", 0))
                    continue

                # Deduplication: if we've already processed this seq,
                # re-send ACK but don't dispatch again.
                if msg.seq and msg.seq in self._seen_seqs:
                    if msg.type in CRITICAL_TYPES:
                        await self.fire(make_ack(msg.seq))
                    continue
                if msg.seq:
                    self._seen_seqs.append(msg.seq)

                # Auto-ACK critical messages
                if msg.type in CRITICAL_TYPES:
                    await self.fire(make_ack(msg.seq))

                # Dispatch to owner's handler
                if self.on_message:
                    try:
                        self.on_message(msg)
                    except Exception as exc:
                        logger.error(
                            f"[{self.channel_id}] message handler error: {exc}"
                        )

            except asyncio.TimeoutError:
                logger.warning(
                    f"[{self.channel_id}] no data in {PING_TIMEOUT}s — "
                    f"connection presumed dead"
                )
                self._handle_dead()
                break
            except asyncio.CancelledError:
                break
            except (ValueError, ConnectionError, OSError) as exc:
                logger.info(
                    f"[{self.channel_id}] listen loop ended: "
                    f"{exc.__class__.__name__}: {exc}"
                )
                self._handle_dead()
                break

    # ── Heartbeat ─────────────────────────────────────────────────

    async def _heartbeat_loop(self) -> None:
        """Send PING every ``PING_INTERVAL`` seconds."""
        while self._alive:
            try:
                await asyncio.sleep(PING_INTERVAL)
            except asyncio.CancelledError:
                break
            if not self._alive:
                break
            ok = await self.fire(Message(type=MessageType.PING))
            if not ok:
                break

    # ── Internal helpers ──────────────────────────────────────────

    def _resolve_ack(self, ack_seq: int) -> None:
        """Resolve a pending ACK future."""
        future = self._pending_acks.pop(ack_seq, None)
        if future and not future.done():
            future.set_result(True)

    def _handle_dead(self) -> None:
        """Mark the channel as dead and notify the owner."""
        if not self._alive:
            return  # already handled
        self._alive = False
        logger.info(f"[{self.channel_id}] connection lost")
        # Cancel pending ACKs
        for future in self._pending_acks.values():
            if not future.done():
                future.cancel()
        self._pending_acks.clear()
        # Notify owner
        if self.on_disconnect:
            try:
                self.on_disconnect()
            except Exception:
                pass

    @property
    def last_seen(self) -> float:
        """Timestamp of the last received message (any type)."""
        return self._last_seen

    @property
    def latency_estimate(self) -> float:
        """Seconds since the last received message."""
        return time.time() - self._last_seen
