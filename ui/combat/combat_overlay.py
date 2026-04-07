"""Combat grid overlay manager for movement range, attack range, and LoS."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PyQt5.QtGui import QColor

# Overlay colors
COLORS = {
    "move_normal": QColor(60, 120, 220, 77),
    "move_climb": QColor(220, 180, 40, 77),
    "move_jump": QColor(220, 140, 40, 77),
    "attack_melee": QColor(200, 40, 40, 77),
    "attack_ranged": QColor(200, 80, 80, 60),
    "threatened": QColor(220, 140, 40, 60),
    "los_blocked": QColor(0, 0, 0, 100),
    "path_preview": QColor(60, 180, 120, 100),
}


class CombatOverlay:
    """Manages visual overlays on the combat grid scene.

    Computes which tiles to highlight and delegates rendering
    to CombatGridScene.apply_overlay_to_tiles().
    """

    def __init__(
        self,
        combat_grid_scene: Any,
        combat_instance: Any,
        tile_map: Any = None,
    ):
        self._scene = combat_grid_scene
        self._instance = combat_instance
        self._tile_map = tile_map

    def show_movement_range(self, combatant_name: str) -> None:
        """Highlight reachable tiles for the named combatant."""
        combatant = self._find_combatant(combatant_name)
        if not combatant:
            return

        budget = combatant.movement_remaining
        origin = combatant.position

        if self._tile_map:
            from core.engine.pathfinder import reachable_tiles_with_elevation
            grid = getattr(self._instance, "grid", {})
            result = reachable_tiles_with_elevation(origin, budget, self._tile_map, grid)
        else:
            result = {origin: {"cost": 0, "traversal_type": "flat"}}

        normal = []
        climb = []
        jump = []

        for pos, info in result.items():
            if pos == origin:
                continue
            ttype = info.get("traversal_type", "flat")
            if ttype in ("climb", "climb_hard"):
                climb.append(pos)
            elif ttype == "jump_down":
                jump.append(pos)
            else:
                normal.append(pos)

        self._scene.apply_overlay_to_tiles(normal, COLORS["move_normal"])
        self._scene.apply_overlay_to_tiles(climb, COLORS["move_climb"])
        self._scene.apply_overlay_to_tiles(jump, COLORS["move_jump"])

    def clear_movement_range(self) -> None:
        self._scene.clear_all_overlays()

    def show_attack_range(
        self, combatant_name: str, attack_type: str = "melee", range_ft: int = 5,
    ) -> None:
        """Highlight tiles within attack range."""
        combatant = self._find_combatant(combatant_name)
        if not combatant:
            return

        cx, cy = combatant.position
        range_tiles = range_ft // 5
        targets = []

        w = self._instance.grid_width
        h = self._instance.grid_height

        for x in range(max(0, cx - range_tiles), min(w, cx + range_tiles + 1)):
            for y in range(max(0, cy - range_tiles), min(h, cy + range_tiles + 1)):
                if (x, y) == (cx, cy):
                    continue
                dist = max(abs(x - cx), abs(y - cy))  # Chebyshev
                if dist <= range_tiles:
                    targets.append((x, y))

        color = COLORS["attack_melee"] if attack_type == "melee" else COLORS["attack_ranged"]
        self._scene.apply_overlay_to_tiles(targets, color)

    def clear_attack_range(self) -> None:
        self._scene.clear_all_overlays()

    def show_threatened_squares(self) -> None:
        """Highlight tiles adjacent to enemy combatants."""
        threatened = set()
        w = self._instance.grid_width
        h = self._instance.grid_height

        for c in self._instance.enemies:
            if not c.is_conscious:
                continue
            ex, ey = c.position
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = ex + dx, ey + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        threatened.add((nx, ny))

        self._scene.apply_overlay_to_tiles(list(threatened), COLORS["threatened"])

    def clear_threatened_squares(self) -> None:
        self._scene.clear_all_overlays()

    def show_path_preview(
        self, from_pos: Tuple[int, int], to_pos: Tuple[int, int],
    ) -> None:
        """Show planned movement path as green tiles."""
        if not self._tile_map:
            return

        from core.engine.pathfinder import find_path
        path = find_path(from_pos, to_pos, self._tile_map)
        if path:
            self._scene.apply_overlay_to_tiles(path, COLORS["path_preview"])

    def clear_path_preview(self) -> None:
        self._scene.clear_all_overlays()

    def refresh_all(self, combatant_name: str) -> None:
        """Show all relevant overlays for a combatant's turn."""
        self._scene.clear_all_overlays()
        self.show_movement_range(combatant_name)
        self.show_threatened_squares()

    def clear_all(self) -> None:
        self._scene.clear_all_overlays()

    def _find_combatant(self, name: str) -> Any:
        for c in self._instance.combatants:
            if c.name == name:
                return c
        return None
