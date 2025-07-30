# tests/unit/models/tiles/test_tile_preset.py
import pytest
from copy import deepcopy

from models.tiles.tile_preset import TilePreset
from models.tiles.tile_data import TileData, TerrainType, TileTag
from models.entities.game_entity import GameEntity
from core.gameCreation.trigger import Trigger
from models.flow.condition.condition_list import AlwaysTrue
from core.gameCreation.event_bus import EventBus


def dummy_reaction(data):
    data['called'] = True

@pytest.fixture
def sample_entities_and_triggers():
    # Create a sample GameEntity
    entity = GameEntity(name='TestEntity', entity_type='npc')
    # Create a sample Trigger
    trigger = Trigger(
        event_type='TEST_EVENT',
        condition=AlwaysTrue(),
        reaction=dummy_reaction
    )
    return [entity], [trigger]


def test_from_tile_data_creates_independent_preset(sample_entities_and_triggers):
    entities, triggers = sample_entities_and_triggers
    # Setup a TileData with various properties
    tile_data = TileData(
        tile_id='tile1',
        position=(2,3),
        terrain=TerrainType.MOUNTAIN,
        tags=[TileTag.BLOCKS_MOVEMENT, TileTag.START_ZONE],
        overlay_color='#ABCDEF',
        note='Dangerous area',
        user_label='ZoneA',
        entities=deepcopy(entities),
        triggers=deepcopy(triggers)
    )
    # Create preset from tile data
    preset = TilePreset.from_tile_data(tile_data)

    # All fields should copy correctly
    assert preset.terrain == tile_data.terrain
    assert preset.tags == tile_data.tags
    assert preset.overlay_color == tile_data.overlay_color
    assert preset.note == tile_data.note
    assert preset.user_label == tile_data.user_label
    # Entities should have the same data but be independent instances
    assert [e.name for e in preset.entities] == [e.name for e in tile_data.entities]
    assert all(e1 is not e2 for e1, e2 in zip(preset.entities, tile_data.entities))
    assert preset.triggers != tile_data.triggers or preset.triggers[0] is not tile_data.triggers[0]

    # Mutating preset lists should not affect original tile_data
    preset.tags.append(TileTag.TRAP_ZONE)
    preset.entities.append(GameEntity('Another', 'npc'))
    assert TileTag.TRAP_ZONE not in tile_data.tags
    assert len(tile_data.entities) == len(entities)


def test_apply_to_visual_only_does_not_change_logic_fields(mocker, sample_entities_and_triggers):
    entities, triggers = sample_entities_and_triggers
    preset = TilePreset(
        terrain=TerrainType.WATER,
        tags=[TileTag.TRAP_ZONE],  # use a valid TileTag
        overlay_color='#123456',
        note='NoteX',
        user_label='LabelX',
        entities=entities,
        triggers=triggers
    )
    tile = TileData()

    # Spy on EventBus.subscribe
    subscribe_spy = mocker.spy(EventBus, 'subscribe')

    # Apply visual only
    preset.apply_to(tile, logic=False)

    # Graphical fields updated
    assert tile.terrain == TerrainType.WATER
    assert tile.tags == [TileTag.TRAP_ZONE]
    assert tile.overlay_color == '#123456'

    # Logic fields should remain defaults (None or empty)
    assert tile.note is None
    assert tile.user_label is None
    assert tile.entities == []
    assert tile.triggers == []
    # No subscribe calls for logic=False
    assert not subscribe_spy.called


def test_apply_to_with_logic_subscribes_triggers(mocker, sample_entities_and_triggers):
    entities, triggers = sample_entities_and_triggers
    preset = TilePreset(
        terrain=TerrainType.GRASS,
        tags=[TileTag.TRAP_ZONE],
        overlay_color='#654321',
        note='NoteY',
        user_label='LabelY',
        entities=entities,
        triggers=triggers
    )
    tile = TileData()

    # Patch EventBus.subscribe to track subscriptions
    subscribe_spy = mocker.spy(EventBus, 'subscribe')

    # Apply with logic enabled
    preset.apply_to(tile, logic=True)

    # Logic fields updated
    assert tile.note == 'NoteY'
    assert tile.user_label == 'LabelY'
    # Entities should have the same data but be independent instances
    assert [e.name for e in tile.entities] == [e.name for e in entities]
    assert all(e1 is not e2 for e1, e2 in zip(tile.entities, entities))
    assert tile.triggers != []

    # subscribe called once per trigger
    for trig in tile.triggers:
        subscribe_spy.assert_any_call(trig.event_type, trig.check_and_react)


def test_deepcopy_of_preset_lists():
    # Ensure that modifying preset input lists does not affect stored preset
    base_entities = [GameEntity('E1', 'npc')]
    base_triggers = [Trigger('EV', AlwaysTrue(), dummy_reaction)]
    preset = TilePreset(entities=base_entities, triggers=base_triggers)

    # Mutate base lists
    base_entities.clear()
    base_triggers.clear()

    # Preset should still hold its own copies
    assert len(preset.entities) == 1
    assert len(preset.triggers) == 1
