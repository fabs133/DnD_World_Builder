"""Pure Python layout calculator for zone depth rendering.

No Qt imports — fully testable headlessly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from models.entities.entity_type import EntityType

# Depth layer height ratios (fraction of canvas height)
LAYER_HEIGHTS = {1: 0.85, 2: 0.65, 3: 0.45}
FLOOR_HEIGHT_RATIO = 0.20


@dataclass
class SceneObject:
    """A renderable object positioned in the scene."""
    name: str
    obj_type: str  # "npc", "object", "furniture", "decoration"
    depth: int
    x_percent: float
    faction: Optional[str] = None
    initials: str = "?"
    interaction_types: List[str] = field(default_factory=list)
    entity_id: Optional[str] = None
    image_path: Optional[str] = None


@dataclass
class NavArrow:
    """A navigation connection to another zone."""
    target_zone_id: str
    target_label: str
    direction: str  # "left", "right", "up", "down"
    locked: bool = False
    lock_description: str = ""


@dataclass
class ZoneSceneData:
    """Complete scene layout data for rendering a zone."""
    zone_id: str
    zone_label: str
    zone_description: str
    objects_by_depth: Dict[int, List[SceneObject]]
    nav_arrows: List[NavArrow]
    player_position: Optional[Tuple[float, int]] = None
    background_image: Optional[str] = None


def _get_faction(entity: Any) -> Optional[str]:
    etype = getattr(entity, "entity_type", "")
    if etype in (EntityType.NPC, EntityType.ALLY, EntityType.COMPANION):
        return "friendly"
    if etype in (EntityType.ENEMY, EntityType.MONSTER, EntityType.HOSTILE):
        return "hostile"
    if etype in (EntityType.PLAYER,):
        return None
    return "neutral"


def _get_initials(name: str) -> str:
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return name[0].upper() if name else "?"


def _infer_direction(label: str, index: int) -> str:
    lower = label.lower()
    # Vertical hints
    if any(k in lower for k in ("north", "up", "stair", "upper", "above", "roof", "tower")):
        return "up"
    if any(k in lower for k in ("south", "down", "cellar", "lower", "below", "trap", "crypt")):
        return "down"
    # Horizontal hints
    if any(k in lower for k in ("east", "right", "sunrise")):
        return "right"
    if any(k in lower for k in ("west", "left", "sunset")):
        return "left"
    # Distribute evenly across all four edges
    _cycle = ("left", "right", "up", "down")
    return _cycle[index % len(_cycle)]


def build_zone_scene(
    zone: Any,
    all_zones: Dict[str, Any],
    player_entity_name: Optional[str] = None,
) -> ZoneSceneData:
    """Build renderable scene data from a TileZone.

    :param zone: TileZone instance.
    :param all_zones: All zones in the parent tile keyed by zone_id.
    :param player_entity_name: The player's entity name (to identify their token).
    """
    objects_by_depth: Dict[int, List[SceneObject]] = {1: [], 2: [], 3: []}
    player_pos = None

    # Build objects from placements (or auto-generate from entities)
    placements = getattr(zone, "placements", [])
    if not placements:
        # Auto-generate from entities if they exist
        entities = getattr(zone, "entities", [])
        if entities:
            spread = 1.0 / max(len(entities), 1)
            for i, entity in enumerate(entities):
                obj = _make_scene_object(entity, depth=3, x_percent=(i + 0.5) * spread)
                if player_entity_name and entity.name == player_entity_name:
                    player_pos = (obj.x_percent, 3)
                else:
                    objects_by_depth[3].append(obj)
    else:
        for placement in placements:
            entity = placement.entity
            obj = SceneObject(
                name=entity.name,
                obj_type=_classify_entity(entity),
                depth=placement.depth,
                x_percent=placement.x_percent,
                faction=_get_faction(entity),
                initials=_get_initials(entity.name),
                interaction_types=list(placement.interaction_types),
                entity_id=entity.name,
                image_path=getattr(entity, "image_path", None),
            )
            if player_entity_name and entity.name == player_entity_name:
                player_pos = (obj.x_percent, placement.depth)
            else:
                depth = max(1, min(3, placement.depth))
                objects_by_depth[depth].append(obj)

    # Build nav arrows from connections
    nav_arrows = []
    for i, conn_id in enumerate(getattr(zone, "connections", [])):
        target_zone = all_zones.get(conn_id)
        target_label = target_zone.label if target_zone else conn_id
        locked = target_zone.locked if target_zone else False
        lock_desc = f"DC {target_zone.lock_dc}" if target_zone and locked else ""

        direction = _infer_direction(target_label, i)
        nav_arrows.append(NavArrow(
            target_zone_id=conn_id,
            target_label=target_label,
            direction=direction,
            locked=locked,
            lock_description=lock_desc,
        ))

    return ZoneSceneData(
        zone_id=zone.zone_id,
        zone_label=zone.label,
        zone_description=getattr(zone, "description", "") or "",
        objects_by_depth=objects_by_depth,
        nav_arrows=nav_arrows,
        player_position=player_pos,
        background_image=getattr(zone, "background_image", None),
    )


def _classify_entity(entity: Any) -> str:
    etype = getattr(entity, "entity_type", "")
    if etype in (EntityType.NPC, EntityType.PLAYER, EntityType.ALLY, EntityType.COMPANION,
                 EntityType.ENEMY, EntityType.MONSTER):
        return "npc"
    return "object"


def _make_scene_object(entity: Any, depth: int, x_percent: float) -> SceneObject:
    return SceneObject(
        name=entity.name,
        obj_type=_classify_entity(entity),
        depth=depth,
        x_percent=x_percent,
        faction=_get_faction(entity),
        initials=_get_initials(entity.name),
        interaction_types=["inspect"],
        entity_id=entity.name,
        image_path=getattr(entity, "image_path", None),
    )
