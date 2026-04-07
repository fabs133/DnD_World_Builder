"""Registry of all pre-defined view transitions."""

from __future__ import annotations

from typing import Dict, List, Optional

from ui.transitions.transition_spec import TransitionSpec, TransitionType

TRANSITIONS: Dict[str, TransitionSpec] = {}


def register_transition(transition_id: str, spec: TransitionSpec) -> None:
    TRANSITIONS[transition_id] = spec


def get_transition(transition_id: str) -> Optional[TransitionSpec]:
    return TRANSITIONS.get(transition_id)


def list_transitions() -> List[str]:
    return list(TRANSITIONS.keys())


# ── App lifecycle (4) ────────────────────────────────────────────────────

register_transition("launcher_to_overview", TransitionSpec(
    name="Launcher to scenario overview",
    transition_type=TransitionType.CUT, duration_ms=0,
))

register_transition("overview_to_editor", TransitionSpec(
    name="Scenario overview to map editor",
    transition_type=TransitionType.FADE, duration_ms=400,
    sound_id="panel_open", theme_after="tome",
))

register_transition("launcher_to_character", TransitionSpec(
    name="Launcher to character creator",
    transition_type=TransitionType.CUT, duration_ms=0,
))

register_transition("editor_to_overview", TransitionSpec(
    name="Map editor back to overview",
    transition_type=TransitionType.FADE, duration_ms=300,
    sound_id="save",
))

# ── Exploration — tome theme (4) ─────────────────────────────────────────

register_transition("map_to_tile_detail", TransitionSpec(
    name="Map view to tile detail",
    transition_type=TransitionType.ZOOM, duration_ms=350,
    direction="in", sound_id="zone_enter",
))

register_transition("tile_detail_to_map", TransitionSpec(
    name="Tile detail back to map",
    transition_type=TransitionType.ZOOM, duration_ms=300,
    direction="out", sound_id="panel_open",
))

register_transition("zone_to_zone", TransitionSpec(
    name="Zone to zone within tile",
    transition_type=TransitionType.SLIDE, duration_ms=250,
    direction="left", sound_id="tab_switch",
))

register_transition("map_tile_pan", TransitionSpec(
    name="Party moves on map",
    transition_type=TransitionType.CUT, duration_ms=0,
))

register_transition("tile_to_tile", TransitionSpec(
    name="Move between tiles in exploration",
    transition_type=TransitionType.FADE, duration_ms=300,
    sound_id="tab_switch",
))

# ── Combat mode changes — theme swap (3) ─────────────────────────────────

register_transition("exploration_to_combat", TransitionSpec(
    name="Enter combat mode",
    transition_type=TransitionType.CINEMATIC, duration_ms=2200,
    easing="OutQuart", direction="up",
    sound_id="combat_start", sound_category="alert",
    theme_before="tome", theme_after="stone",
    hold_black_ms=350, dust_particles=True, shake_frames=5,
))

register_transition("combat_to_exploration_victory", TransitionSpec(
    name="Exit combat — victory",
    transition_type=TransitionType.CINEMATIC, duration_ms=1800,
    easing="OutCubic", direction="down",
    sound_id="victory", sound_category="alert",
    theme_before="stone", theme_after="tome",
    hold_black_ms=200,
))

register_transition("combat_to_exploration_defeat", TransitionSpec(
    name="Exit combat — defeat",
    transition_type=TransitionType.CINEMATIC, duration_ms=2000,
    easing="InOutCubic", direction="crack",
    sound_id="defeat", sound_category="alert",
    theme_before="stone", theme_after="tome",
    hold_black_ms=500,
))

# ── Within combat — stone theme (3) ──────────────────────────────────────

register_transition("combat_setup_to_initiative", TransitionSpec(
    name="Lock positions, roll initiative",
    transition_type=TransitionType.FADE, duration_ms=300,
    sound_id="initiative", sound_category="combat",
))

register_transition("turn_advance", TransitionSpec(
    name="Turn advances to next combatant",
    transition_type=TransitionType.CUT, duration_ms=0,
    sound_id="your_turn", sound_category="alert",
))

register_transition("round_advance", TransitionSpec(
    name="New round begins",
    transition_type=TransitionType.CUT, duration_ms=0,
    sound_id="round_bell", sound_category="combat",
))

# ── Multiplayer (3) ──────────────────────────────────────────────────────

register_transition("solo_to_hosting", TransitionSpec(
    name="Start hosting session",
    transition_type=TransitionType.SLIDE, duration_ms=300,
    direction="left", sound_id="panel_open",
))

register_transition("join_to_connected", TransitionSpec(
    name="Player joins session",
    transition_type=TransitionType.FADE, duration_ms=400,
    sound_id="panel_open",
))

register_transition("connected_to_disconnected", TransitionSpec(
    name="Connection lost",
    transition_type=TransitionType.FADE, duration_ms=300,
    sound_id="error", sound_category="alert",
))

# ── HUD panel transitions (4) ────────────────────────────────────────────

register_transition("side_panel_tab", TransitionSpec(
    name="Side panel tab switch",
    transition_type=TransitionType.CUT, duration_ms=0,
    sound_id="tab_switch",
))

register_transition("action_to_spell_selector", TransitionSpec(
    name="Open spell selector dialog",
    transition_type=TransitionType.FADE, duration_ms=200,
    sound_id="click",
))

register_transition("open_character_sheet", TransitionSpec(
    name="Open character sheet panel",
    transition_type=TransitionType.SLIDE, duration_ms=250,
    direction="left", sound_id="panel_open",
))

register_transition("open_inventory", TransitionSpec(
    name="Open inventory panel",
    transition_type=TransitionType.SLIDE, duration_ms=250,
    direction="left", sound_id="panel_open",
))
