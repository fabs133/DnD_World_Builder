import pytest
from models.tiles.tile_data import TileData, TerrainType, TileTag
from models.entities.game_entity import GameEntity


@pytest.fixture
def sample_tile():
    return TileData(
        tile_id="test-tile",
        position=(0, 0),
        terrain=TerrainType.GRASS,
        tags=[TileTag.START_ZONE]
    )

def test_add_entity(sample_tile):
    entity = GameEntity(name="Hero", entity_type="player")
    sample_tile.add_entity(entity)

    assert entity in sample_tile.entities
    assert sample_tile.is_occupied() is True
    assert sample_tile.has_entity_type("player") is True

def test_remove_entity(sample_tile):
    entity = GameEntity(name="Goblin", entity_type="enemy")
    sample_tile.add_entity(entity)

    sample_tile.remove_entity(entity)
    assert entity not in sample_tile.entities
    assert sample_tile.is_occupied() is False

def test_is_occupied_with_non_combatant(sample_tile):
    npc = GameEntity(name="Barrel", entity_type="object")
    sample_tile.add_entity(npc)

    assert sample_tile.is_occupied() is False  # not a player/npc/enemy

def test_has_entity_type(sample_tile):
    wizard = GameEntity(name="Wizard", entity_type="player")
    trap = GameEntity(name="Trap", entity_type="trap")
    sample_tile.add_entity(wizard)
    sample_tile.add_entity(trap)

    assert sample_tile.has_entity_type("trap") is True
    assert sample_tile.has_entity_type("npc") is False
