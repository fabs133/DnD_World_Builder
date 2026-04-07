"""Smoke tests for critical user paths.

Verify major flows don't crash or silently fail.
"""

import pytest
from pathlib import Path


class TestScenarioRoundtrip:
    def test_tile_data_with_zones_roundtrip(self):
        from models.tiles.tile_data import TileData, TerrainType
        from models.tiles.tile_zone import TileZone, ZonePlacement
        from models.entities.game_entity import GameEntity

        entity = GameEntity("Guard", "npc", stats={"hp": 11})
        zone = TileZone(zone_id="entrance", label="Entrance",
                        connections=["main_hall"],
                        placements=[ZonePlacement(entity=entity, depth=2, x_percent=0.3)])
        td = TileData(position=(0, 0), terrain=TerrainType.FLOOR,
                      zones=[zone], elevation=2)
        data = td.to_dict()
        restored = TileData.from_dict(data)
        assert restored.has_zones
        assert restored.elevation == 2
        assert len(restored.zones[0].placements) == 1


class TestZoneSceneBuilder:
    def test_build_scene_with_placements(self):
        from models.tiles.tile_zone import TileZone, ZonePlacement
        from models.exploration.zone_scene_data import build_zone_scene

        class FakeEntity:
            name = "Marta"
            entity_type = "npc"

        zone = TileZone(zone_id="hall", label="Main Hall",
                        connections=["entrance"],
                        placements=[ZonePlacement(entity=FakeEntity(), depth=2)])
        entrance = TileZone(zone_id="entrance", label="Entrance")
        all_zones = {"hall": zone, "entrance": entrance}

        scene = build_zone_scene(zone, all_zones)
        assert scene.zone_label == "Main Hall"
        assert len(scene.nav_arrows) == 1
        assert len(scene.objects_by_depth[2]) == 1


class TestCombatFullFlow:
    def test_create_and_run_combat(self):
        from models.combat.encounter_template import EncounterTemplate, EnemySpawn
        from models.combat.combat_factory import create_combat_instance
        from models.combat.combat_orchestrator import CombatOrchestrator
        from models.combat.combat_instance import CombatState
        from unittest.mock import MagicMock

        template = EncounterTemplate(
            template_id="t1", name="Test",
            enemy_spawns=[EnemySpawn(position=(3, 0), creature_index="goblin", count=2)],
            player_spawn_zone=[(0, 0)],
        )

        class FakePlayer:
            name = "Hero"
            hp = 20
            max_hp = 20
            speed = 30
            entity_type = "player"
            stats = {"hp": 20, "Dexterity": 14, "max_hp": 20}

        instance = create_combat_instance(template, [FakePlayer()], seed=42)
        orch = CombatOrchestrator(instance, gamemaster=MagicMock())

        orch.start_setup()
        assert instance.state == CombatState.SETUP

        orch.roll_initiative(seed=42)
        assert instance.state == CombatState.INITIATIVE

        orch.begin_combat()
        assert instance.state == CombatState.ACTIVE

        # End a few turns
        for _ in range(3):
            orch.end_turn()

        orch.end_combat("victory")
        assert instance.state == CombatState.ENDED


class TestSoundBridgeEvents:
    def test_bridge_receives_events(self):
        from unittest.mock import MagicMock
        from core.events import COMBAT_STARTED
        from core.gameCreation.event_bus import EventBus
        from core.audio.sound_event_bridge import SoundEventBridge

        EventBus.reset()
        sound = MagicMock()
        bridge = SoundEventBridge(sound, viewer_entity_name="")
        bridge.start()

        EventBus.emit(COMBAT_STARTED, {})
        sound.play_shared.assert_called()

        bridge.stop()
        EventBus.reset()


class TestTransitionRegistry:
    def test_all_21_specs_valid(self):
        from ui.transitions.transition_registry import TRANSITIONS, get_transition
        assert len(TRANSITIONS) == 22
        for tid in TRANSITIONS:
            spec = get_transition(tid)
            assert spec is not None
            assert spec.name


class TestElevationPathfinder:
    def test_elevation_costs_correct(self):
        from models.combat.elevation import evaluate_traversal, TraversalType
        info = evaluate_traversal(0, 2)
        assert info.traversal_type == TraversalType.CLIMB
        assert info.movement_cost_multiplier == 2.0

        info = evaluate_traversal(0, 4)
        assert info.traversal_type == TraversalType.IMPASSABLE


class TestVoicePresets:
    def test_all_presets(self):
        from core.voice.voice_preset_registry import list_presets
        presets = list_presets()
        assert len(presets) >= 10

    def test_seed_files_exist(self):
        seed_dir = Path("core/audio/voice_seeds")
        if seed_dir.exists():
            wavs = list(seed_dir.glob("*.wav"))
            assert len(wavs) >= 10


class TestEntityPalette:
    def test_srd_data_loadable(self):
        srd_path = Path("core/data_/rulebook_json/5e-SRD-Monsters.json")
        if srd_path.exists():
            import json
            with open(srd_path, "r") as f:
                monsters = json.load(f)
            assert len(monsters) > 100
