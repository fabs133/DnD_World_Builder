"""
Canonical event name constants for the EventBus.

All EventBus event names should be referenced through these constants
rather than string literals.  This enables IDE navigation, typo
detection, and serves as the single inventory of all events in the
system.

Two routing mechanisms exist in EventBus (see event_bus.py):

- **Spatial events**: payload includes ``position`` + ``world`` keys.
  Dispatched to entities at/near that position via
  ``entity.handle_event()``.  Used by the trigger system.
- **Global events**: payload has no ``position``/``world`` keys.
  Broadcast to all callbacks registered via ``EventBus.subscribe()``.
  Used by animations, audio, and network sync.

Event Payload Contracts
-----------------------
Each constant below documents its expected payload keys.
Emitters MUST include these keys; subscribers MAY rely on them.
"""

# -- Combat lifecycle (global) ------------------------------------------------

COMBAT_STARTED = "combat_started"
"""Payload: ``{"instance_id": str, "template_name": str}``

Emitters: ``combat_orchestrator.py``, ``game_master.py``
Subscribers: ``sound_event_bridge.py``, ``event_bridge.py`` (network sync)
"""

COMBAT_ENDED = "combat_ended"
"""Payload: ``{"outcome": str, "rounds": int, ...}``  (full summary dict)

Emitters: ``combat_orchestrator.py``
Subscribers: ``sound_event_bridge.py``, ``combat_animator.py``, ``event_bridge.py``
"""

ROUND_STARTED = "round_started"
"""Payload: ``{"round": int}``

Emitters: ``combat_orchestrator.py``
Subscribers: ``sound_event_bridge.py``, ``combat_animator.py``, ``event_bridge.py``
"""

TURN_STARTED = "turn_started"
"""Payload: ``{"entity": str, "round": int}``

Emitters: ``combat_orchestrator.py``
Subscribers: ``combat_animator.py``, ``sound_event_bridge.py``, ``event_bridge.py``
"""

TURN_ENDED = "turn_ended"
"""Payload: ``{"entity": str}``

Emitters: ``combat_orchestrator.py``
Subscribers: ``event_bridge.py`` (network sync)
"""

INITIATIVE_ROLLED = "initiative_rolled"
"""Payload: ``{"rolls": list[InitiativeEntry]}``

Emitters: ``combat_orchestrator.py``
Subscribers: ``sound_event_bridge.py``, ``event_bridge.py``
"""

# -- Entity state changes (global) --------------------------------------------

ENTITY_DAMAGED = "entity_damaged"
"""Payload: ``{"entity_name": str, "source": str, "damage": int,
"damage_type": str, "remaining_hp": int}``

Emitters: ``spell_action.py``
Subscribers: ``combat_animator.py``, ``sound_event_bridge.py``, ``event_bridge.py``
"""

ENTITY_HEALED = "entity_healed"
"""Payload: ``{"entity_name": str, "source": str, "amount": int,
"new_hp": int}``

Emitters: ``spell_action.py``
Subscribers: ``combat_animator.py``, ``event_bridge.py``
"""

ENTITY_DIED = "entity_died"
"""Payload: ``{"entity_name": str, "source": str}``

Emitters: ``spell_action.py``, ``combat_orchestrator.py``
Subscribers: ``combat_animator.py``, ``sound_event_bridge.py``, ``event_bridge.py``
"""

ENTITY_MOVED = "entity_moved"
"""Payload: ``{"entity_name": str, "old_position": tuple, "new_position": tuple}``

Emitters: (game logic)
Subscribers: ``event_bridge.py``
"""

ENTITY_ADDED = "entity_added"
"""Payload: ``{"position": tuple, "entity_name": str}``

Emitters: ``entities_panel.py``
Subscribers: ``event_bridge.py``
"""

ENTITY_REMOVED = "entity_removed"
"""Payload: ``{"position": tuple | None, "entity_name": str}``

Emitters: ``entities_panel.py``
Subscribers: ``event_bridge.py``
"""

ATTACK_MISSED = "attack_missed"
"""Payload: ``{"attacker": str, "target": str, "position": tuple}``

Emitters: (combat logic)
Subscribers: ``combat_animator.py``
"""

# -- Spellcasting (global) ----------------------------------------------------

SPELL_CAST = "spell_cast"
"""Payload: ``{"caster": str, "spell": str, "targets": list[str],
"level": int, "position": tuple | None}``

Emitters: ``spell_action.py``
Subscribers: ``combat_animator.py``
"""

# -- Conditions (global) ------------------------------------------------------

CONDITION_APPLIED = "condition_applied"
"""Payload: ``{"entity_name": str, "condition": str, "source": str}``

Emitters: ``spell_action.py``
Subscribers: ``combat_animator.py``, ``event_bridge.py``
"""

CONDITION_REMOVED = "condition_removed"
"""Payload: ``{"entity_name": str, "condition": str}``

Emitters: (combat logic)
Subscribers: ``combat_animator.py``, ``event_bridge.py``
"""

# -- Trigger system (spatial -- include position + world in payload) -----------

TRIGGER_TURN_START = "TURN_START"
"""**Spatial.** Payload: ``{"entity": Entity, "position": tuple,
"world": World, "round_number": int}``

Emitters: ``game_session.py``
Routing: spatial dispatch → ``entity.handle_event()`` for triggers at/near position
"""

TRIGGER_ON_DAMAGE = "ON_DAMAGE"
"""**Spatial.** Payload: ``{"entity": Entity, "target": Entity,
"damage": int, "damage_type": str, "position": tuple, "world": World}``

Emitters: ``attack_action.py``
Routing: spatial dispatch → triggers at target's position
"""

TRIGGER_ENTER_TILE = "ENTER_TILE"
"""**Spatial.** Payload: ``{"entity": Entity, "position": tuple,
"old_position": tuple, "world": World}``

Emitters: ``move_action.py``
Routing: spatial dispatch → triggers at the entered tile
"""

# -- Turn system (global) -----------------------------------------------------

ACTION_PROPOSED = "ACTION_PROPOSED"
"""Payload: the proposed Action object.

Emitters: ``turn_system.py``
Subscribers: (reaction queue)
"""

ACTION_EXECUTED = "ACTION_EXECUTED"
"""Payload: the executed Action object.

Emitters: ``turn_system.py``
Subscribers: (logging)
"""

# -- World / editor (global) --------------------------------------------------

TILE_MODIFIED = "tile_modified"
"""Payload: ``{"position": tuple, "tile_id": str}``

Emitters: ``core_values_panel.py``, ``color_paint_command.py``
Subscribers: ``event_bridge.py``
"""

TILE_TERRAIN_CHANGED = "tile_terrain_changed"
"""Payload: ``{"position": tuple, "old_terrain": str, "new_terrain": str}``

Emitters: (editor logic)
Subscribers: ``event_bridge.py``
"""

PLAYER_ENTERED_ZONE = "player_entered_zone"
"""Payload: ``{"zone_id": str, "tile_id": str}``

Emitters: ``main_window.py``
Subscribers: ``event_bridge.py``
"""

PLAYER_LEFT_ZONE = "player_left_zone"
"""Payload: ``{"zone_id": str}``

Emitters: (zone logic)
Subscribers: ``event_bridge.py``
"""

COMBAT_GRID_READY = "combat_grid_ready"
"""Payload: ``{"grid_data": dict}``

Emitters: (combat setup)
Subscribers: ``event_bridge.py``
"""

TRIGGER_FIRED = "trigger_fired"
"""Payload: ``{"trigger_label": str, "event_type": str}``

Emitters: (trigger system)
Subscribers: ``event_bridge.py``
"""

# -- Voice (global) ------------------------------------------------------------

VOICE_LINE_READY = "voice_line_ready"
"""Payload: ``{"cache_key": str, "entity_name": str, "text": str}``

Emitters: ``voice_queue.py``
Subscribers: (voice playback UI)
"""

# -- Narration ----------------------------------------------------------------

NARRATION_TRIGGERED = "narration_triggered"
"""Payload: ``{"message": str, "source": str}``

Emitters: ``reactions_list.py`` (AlertGamemaster)
Subscribers: ``narration_panel.py``
"""
