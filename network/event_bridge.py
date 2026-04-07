"""
Event Bridge - Connects EventBus to Network State Sync

Subscribes to game events and broadcasts state deltas to connected players.
Provides the real-time sync between DM actions and player views.
"""

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from core.events import (
    COMBAT_ENDED, COMBAT_GRID_READY, COMBAT_STARTED, CONDITION_APPLIED,
    CONDITION_REMOVED, ENTITY_ADDED, ENTITY_DAMAGED, ENTITY_DIED,
    ENTITY_HEALED, ENTITY_MOVED, ENTITY_REMOVED, INITIATIVE_ROLLED,
    PLAYER_ENTERED_ZONE, PLAYER_LEFT_ZONE, ROUND_STARTED,
    TILE_MODIFIED, TILE_TERRAIN_CHANGED, TRIGGER_FIRED, TURN_ENDED,
    TURN_STARTED,
)
from core.gameCreation.event_bus import EventBus
from network.sync import serialize_world, compute_delta
from network.protocol import make_state_delta, make_turn_change

if TYPE_CHECKING:
    from network.session_host import SessionHost

logger = logging.getLogger(__name__)


# Events that trigger state sync
SYNC_EVENTS = frozenset({
    ENTITY_MOVED,
    ENTITY_ADDED,
    ENTITY_REMOVED,
    ENTITY_DAMAGED,
    ENTITY_HEALED,
    ENTITY_DIED,
    TILE_MODIFIED,
    TILE_TERRAIN_CHANGED,
    COMBAT_STARTED,
    COMBAT_ENDED,
    TURN_STARTED,
    TURN_ENDED,
    ROUND_STARTED,
    CONDITION_APPLIED,
    CONDITION_REMOVED,
    TRIGGER_FIRED,
    PLAYER_ENTERED_ZONE,
    PLAYER_LEFT_ZONE,
    COMBAT_GRID_READY,
    INITIATIVE_ROLLED,
})


class EventBridge:
    """Bridges :class:`~core.gameCreation.event_bus.EventBus` events to network state broadcasts.

    Subscribes to every event type listed in :data:`SYNC_EVENTS`, batches rapid
    changes via a configurable throttle window, computes state deltas using
    :func:`~network.sync.compute_delta`, and broadcasts them through the
    :class:`~network.session_host.SessionHost`.

    :param session_host: The host instance used for broadcasting.
    :type session_host: ~network.session_host.SessionHost
    :param gamemaster: The Gamemaster whose world provides the authoritative state.
    :param throttle_ms: Minimum milliseconds between consecutive broadcasts.
    :type throttle_ms: int

    Example::

        bridge = EventBridge(session_host, gamemaster)
        bridge.start()
        # ... game runs, events auto-broadcast ...
        bridge.stop()
    """

    def __init__(
        self,
        session_host: "SessionHost",
        gamemaster,
        throttle_ms: int = 100,
    ):
        self.session_host = session_host
        self.gamemaster = gamemaster
        self.throttle_ms = throttle_ms
        
        self._last_state = None
        self._pending_sync = False
        self._last_sync_time = 0
        self._running = False
        self._loop = None
        self._subscribed_events = []
    
    def start(self):
        """Start listening to :class:`~core.gameCreation.event_bus.EventBus` events.

        Captures an initial world snapshot and subscribes to all
        :data:`SYNC_EVENTS`.  Safe to call multiple times (subsequent calls
        are no-ops).
        """
        if self._running:
            return
            
        self._running = True
        self._last_state = serialize_world(self.gamemaster.world)
        
        # Get or create event loop
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.get_event_loop()
        
        # Subscribe to all sync events
        for event_type in SYNC_EVENTS:
            EventBus.subscribe(event_type, self._on_event)
            self._subscribed_events.append(event_type)
        
        logger.info(f"EventBridge started, watching {len(SYNC_EVENTS)} event types")
    
    def stop(self):
        """Stop listening and unsubscribe from all events."""
        if not self._running:
            return
            
        self._running = False
        
        # Unsubscribe from all events
        for event_type in self._subscribed_events:
            EventBus.unsubscribe(event_type, self._on_event)
        self._subscribed_events.clear()
        
        logger.info("EventBridge stopped")
    
    def _on_event(self, data: dict):
        """Handle an EventBus event.

        Called synchronously from game code.  Applies throttle logic and
        schedules the async broadcast on the background event loop.

        :param data: Event payload forwarded by the EventBus.
        :type data: dict
        """
        if not self._running:
            return
        
        # Throttle: don't sync more than once per throttle_ms
        now = time.time() * 1000
        if now - self._last_sync_time < self.throttle_ms:
            self._pending_sync = True
            # Schedule a delayed sync
            if self._loop:
                self._loop.call_later(
                    self.throttle_ms / 1000,
                    self._maybe_sync,
                )
            return
        
        self._schedule_sync()
    
    def _maybe_sync(self):
        """Called after throttle delay to check if sync is still needed."""
        if self._pending_sync and self._running:
            self._schedule_sync()
    
    def _schedule_sync(self):
        """Schedule the async sync operation."""
        self._pending_sync = False
        self._last_sync_time = time.time() * 1000
        
        if self._loop and self._running:
            asyncio.run_coroutine_threadsafe(
                self._broadcast_delta(),
                self._loop,
            )
    
    async def _broadcast_delta(self):
        """Compute and broadcast a state delta to all connected players.

        Serializes the current world, diffs it against the last snapshot,
        and sends a :data:`~network.protocol.MessageType.STATE_DELTA` message
        if any changes are detected.
        """
        if not self._running:
            return
        
        try:
            new_state = serialize_world(self.gamemaster.world)
            
            if self._last_state is None:
                self._last_state = new_state
                return
            
            changes = compute_delta(self._last_state, new_state)
            
            if not changes:
                return
            
            self._last_state = new_state
            
            # Broadcast to all players
            msg = make_state_delta(changes)
            await self.session_host.broadcast(msg)
            
            logger.debug(f"Broadcast {len(changes)} state changes")
            
        except Exception as e:
            logger.error(f"Error broadcasting delta: {e}")
    
    async def force_full_sync(self):
        """Force a :data:`~network.protocol.MessageType.FULL_STATE` broadcast.

        Serializes the entire world, entity list, and turn data and sends it
        to every connected player.  Resets the internal snapshot afterwards.
        """
        if not self._running:
            return
        
        try:
            world_data = serialize_world(self.gamemaster.world)
            entities = [
                {"name": e.name, "position": list(e.position) if e.position else None}
                for e in self.gamemaster.game_entities
            ]
            turn_data = {
                "current_turn": self.gamemaster.turn_system.current_turn,
                "round_number": self.gamemaster.turn_system.round_number,
            }
            
            from network.protocol import make_full_state
            msg = make_full_state(world_data, entities, turn_data)
            await self.session_host.broadcast(msg)
            
            self._last_state = world_data
            
            logger.info("Broadcast full state sync")
            
        except Exception as e:
            logger.error(f"Error broadcasting full state: {e}")


class TurnBridge:
    """Specialized bridge for turn-related events.

    Subscribes to ``"turn_started"`` and ``"round_started"`` EventBus events
    and broadcasts :data:`~network.protocol.MessageType.TURN_CHANGE` messages
    to all connected players.

    :param session_host: The host instance used for broadcasting.
    :type session_host: ~network.session_host.SessionHost
    :param gamemaster: The Gamemaster whose turn system provides state.
    """

    def __init__(self, session_host: "SessionHost", gamemaster):
        self.session_host = session_host
        self.gamemaster = gamemaster
        self._running = False
        self._loop = None

    def start(self):
        """Start listening for turn events on the EventBus."""
        if self._running:
            return
        
        self._running = True
        
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.get_event_loop()
        
        EventBus.subscribe(TURN_STARTED, self._on_turn_started)
        EventBus.subscribe(ROUND_STARTED, self._on_round_started)
        
        logger.info("TurnBridge started")
    
    def stop(self):
        """Stop listening and unsubscribe from turn events."""
        if not self._running:
            return

        self._running = False
        EventBus.unsubscribe(TURN_STARTED, self._on_turn_started)
        EventBus.unsubscribe(ROUND_STARTED, self._on_round_started)
        
        logger.info("TurnBridge stopped")
    
    def _on_turn_started(self, data: dict):
        """Handle a ``turn_started`` event by scheduling a broadcast."""
        if self._loop and self._running:
            asyncio.run_coroutine_threadsafe(
                self._broadcast_turn_update(),
                self._loop,
            )
    
    def _on_round_started(self, data: dict):
        """Handle a ``round_started`` event by scheduling a broadcast."""
        if self._loop and self._running:
            asyncio.run_coroutine_threadsafe(
                self._broadcast_turn_update(),
                self._loop,
            )
    
    async def _broadcast_turn_update(self):
        """Broadcast the current turn state to all connected players."""
        try:
            turn_system = self.gamemaster.turn_system
            
            current_entity = None
            if turn_system.turn_order and turn_system.current_turn < len(turn_system.turn_order):
                current_entity = turn_system.turn_order[turn_system.current_turn].name
            
            msg = make_turn_change(
                current_entity=current_entity,
                round_number=turn_system.round_number,
            )
            await self.session_host.broadcast(msg)
            
        except Exception as e:
            logger.error(f"Error broadcasting turn update: {e}")
