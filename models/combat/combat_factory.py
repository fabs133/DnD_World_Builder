"""Factory for creating CombatInstance from EncounterTemplate."""

from __future__ import annotations

import copy
import random
import uuid
from typing import Any, List

from core.logger import app_logger
from models.combat.encounter_template import EncounterTemplate
from models.combat.combatant import Combatant, CombatantFaction
from models.combat.combat_instance import CombatInstance


def create_combat_instance(
    template: EncounterTemplate,
    player_entities: List[Any],
    seed: int | None = None,
) -> CombatInstance:
    """Instantiate a live combat from a template.

    1. Resolve enemy spawns into GameEntity instances.
    2. Create Combatant wrappers for all participants.
    3. Place player combatants in the spawn zone.
    4. Return a CombatInstance in SETUP state.
    """
    rng = random.Random(seed)
    instance_id = uuid.uuid4().hex[:8]

    combatants: list[Combatant] = []

    # Resolve enemy spawns
    for spawn in template.enemy_spawns:
        count = spawn.count
        if spawn.variance > 0:
            count = max(1, count + rng.randint(-spawn.variance, spawn.variance))

        for i in range(count):
            entity = _resolve_creature(spawn.creature_index, i, spawn.position)
            combatant = Combatant(
                entity=entity,
                faction=CombatantFaction.ENEMY,
                position=spawn.position,
            )
            combatants.append(combatant)

    # Wrap player entities
    spawn_zone = template.player_spawn_zone or [(0, template.grid_height - 1)]
    for idx, player_entity in enumerate(player_entities):
        pos = spawn_zone[min(idx, len(spawn_zone) - 1)]
        combatant = Combatant(
            entity=player_entity,
            faction=CombatantFaction.PLAYER,
            position=pos,
        )
        combatants.append(combatant)

    instance = CombatInstance(
        instance_id=instance_id,
        template_id=template.template_id,
        template_name=template.name,
        grid_width=template.grid_width,
        grid_height=template.grid_height,
        combatants=combatants,
    )

    app_logger.info(
        f"Created combat instance {instance_id} from template '{template.name}' "
        f"with {len(combatants)} combatants"
    )

    return instance


def _resolve_creature(creature_index: str, index: int, position: tuple) -> Any:
    """Create a GameEntity from an SRD creature reference.

    Falls back to placeholder stats if creature not found in SRD data.
    """
    from models.entities.game_entity import GameEntity

    # Try to load from SRD bestiary
    srd_data = _lookup_srd_creature(creature_index)

    if srd_data:
        name = f"{srd_data.get('name', creature_index)}_{index + 1}"
        hp = srd_data.get("hit_points", 10)
        ac = srd_data.get("armor_class", 12)
        if isinstance(ac, list):
            ac = ac[0].get("value", 12) if ac else 12
        speed_data = srd_data.get("speed", {})
        speed = speed_data.get("walk") if isinstance(speed_data, dict) else 30
        if isinstance(speed, str):
            speed = int(speed.replace(" ft.", "").replace("ft", "").strip() or 30)
        dex = 10
        for stat in srd_data.get("ability_scores", []):
            if stat.get("name") == "DEX":
                dex = stat.get("value", 10)
    else:
        name = f"{creature_index}_{index + 1}"
        hp = 10
        ac = 12
        speed = 30
        dex = 10
        app_logger.warning(f"SRD creature '{creature_index}' not found, using defaults")

    entity = GameEntity(
        name=name,
        entity_type="enemy",
        stats={"hp": hp, "Dexterity": dex, "max_hp": hp},
    )
    entity.hp = hp
    entity.max_hp = hp
    entity.armor_class = ac
    entity.speed = speed
    entity.position = position

    return entity


def _lookup_srd_creature(creature_index: str) -> dict | None:
    """Look up a creature in the SRD bestiary JSON."""
    import json
    from pathlib import Path

    bestiary_path = Path("core/data_/rulebook_json/5e-SRD-Monsters.json")
    if not bestiary_path.exists():
        return None

    try:
        with open(bestiary_path, "r", encoding="utf-8") as f:
            monsters = json.load(f)
        for monster in monsters:
            if monster.get("index", "").lower() == creature_index.lower():
                return monster
            if monster.get("name", "").lower() == creature_index.lower():
                return monster
    except (json.JSONDecodeError, OSError):
        return None

    return None
