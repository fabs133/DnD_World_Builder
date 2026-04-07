"""Tests for encounter template data models."""

from models.combat.encounter_template import (
    EnemySpawn, TerrainPreset, EncounterTemplate, EncounterBinding,
)


class TestEnemySpawn:
    def test_roundtrip(self):
        spawn = EnemySpawn(position=(3, 2), creature_index="goblin", count=2, variance=1)
        data = spawn.to_dict()
        restored = EnemySpawn.from_dict(data)
        assert restored.position == (3, 2)
        assert restored.creature_index == "goblin"
        assert restored.count == 2
        assert restored.variance == 1

    def test_defaults(self):
        spawn = EnemySpawn(position=(0, 0), creature_index="kobold")
        assert spawn.count == 1
        assert spawn.variance == 0


class TestTerrainPreset:
    def test_roundtrip(self):
        preset = TerrainPreset(
            preset_id="test",
            name="Test Preset",
            base_terrain="grass",
            obstacles=[{"terrain": "wall", "label": "Tree"}],
            obstacle_density=0.2,
            difficult_terrain_chance=0.1,
        )
        data = preset.to_dict()
        restored = TerrainPreset.from_dict(data)
        assert restored.preset_id == "test"
        assert restored.name == "Test Preset"
        assert len(restored.obstacles) == 1
        assert restored.obstacle_density == 0.2

    def test_defaults(self):
        preset = TerrainPreset(preset_id="x", name="X")
        assert preset.base_terrain == "floor"
        assert preset.obstacle_density == 0.1


class TestEncounterTemplate:
    def test_roundtrip(self):
        template = EncounterTemplate(
            template_id="tmpl_001",
            name="Tavern Brawl",
            grid_width=8,
            grid_height=6,
            enemy_spawns=[
                EnemySpawn(position=(5, 1), creature_index="bandit", count=3),
            ],
            player_spawn_zone=[(0, 4), (1, 4), (2, 4)],
            environment_tags=["indoor", "tavern"],
            difficulty_label="medium",
        )
        data = template.to_dict()
        restored = EncounterTemplate.from_dict(data)
        assert restored.template_id == "tmpl_001"
        assert restored.name == "Tavern Brawl"
        assert restored.grid_width == 8
        assert len(restored.enemy_spawns) == 1
        assert restored.enemy_spawns[0].creature_index == "bandit"
        assert len(restored.player_spawn_zone) == 3
        assert restored.environment_tags == ["indoor", "tavern"]

    def test_empty_template_valid(self):
        template = EncounterTemplate(template_id="empty", name="Empty")
        assert template.enemy_spawns == []
        assert template.player_spawn_zone == []
        data = template.to_dict()
        restored = EncounterTemplate.from_dict(data)
        assert restored.template_id == "empty"

    def test_defaults(self):
        template = EncounterTemplate(template_id="t", name="T")
        assert template.grid_type == "square"
        assert template.difficulty_label == "medium"


class TestEncounterBinding:
    def test_roundtrip(self):
        binding = EncounterBinding(
            template_id="tmpl_001",
            location_type="zone",
            location_id="tavern_bar",
            trigger_mode="on_enter",
            once_only=True,
        )
        data = binding.to_dict()
        restored = EncounterBinding.from_dict(data)
        assert restored.template_id == "tmpl_001"
        assert restored.location_type == "zone"
        assert restored.location_id == "tavern_bar"
        assert restored.trigger_mode == "on_enter"
        assert restored.once_only is True

    def test_trigger_event_mode(self):
        binding = EncounterBinding(
            template_id="tmpl_002",
            trigger_mode="trigger_event",
            trigger_id="trap_trigger_001",
        )
        data = binding.to_dict()
        restored = EncounterBinding.from_dict(data)
        assert restored.trigger_mode == "trigger_event"
        assert restored.trigger_id == "trap_trigger_001"

    def test_defaults(self):
        binding = EncounterBinding(template_id="t")
        assert binding.location_type == "tile"
        assert binding.trigger_mode == "manual"
        assert binding.trigger_id is None
        assert binding.once_only is True
