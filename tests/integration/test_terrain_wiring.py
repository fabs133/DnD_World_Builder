"""Integration tests: YAML terrain config → tile_map → pathfinder → engine."""

import pytest

from core.engine.scenarios.scenario_loader import ScenarioLoader
from core.engine.pathfinder import find_path
from core.engine.actions.move_action import MoveAction


class TestTerrainWiring:
    """Verify that terrain defined in scenario YAML feeds through to the tile map."""

    def test_movement_cost_from_yaml(self, tmp_path):
        """Scenario YAML with movement_cost:2 stores cost directly (no multiplier)."""
        yaml_file = tmp_path / "terrain_test.yaml"
        yaml_file.write_text("""\
name: "Terrain Test"
description: "Test terrain wiring"
map_size: [5, 5]
max_rounds: 5
terrain:
  rubble:
    positions: [[2, 2], [3, 2]]
    movement_cost: 2
entities:
  - name: "Fighter"
    type: "player"
    hp: 20
    armor_class: 16
    dex: 12
    position: [0, 0]
""")
        loader = ScenarioLoader(yaml_file)
        session = loader.build_session(mode="mock", seed=42)
        tm = session._gm.world_tile_manager

        assert tm.get_movement_cost(2, 2) == 2  # stored directly from YAML
        assert tm.get_movement_cost(3, 2) == 2
        assert tm.get_movement_cost(0, 0) == 5   # default

    def test_blocking_from_yaml(self, tmp_path):
        """Scenario YAML with blocking:true makes tiles impassable."""
        yaml_file = tmp_path / "blocking_test.yaml"
        yaml_file.write_text("""\
name: "Blocking Test"
description: "Test blocking wiring"
map_size: [5, 5]
max_rounds: 5
terrain:
  pillars:
    positions: [[2, 0], [2, 1], [2, 2], [2, 3], [2, 4]]
    blocking: true
entities:
  - name: "Fighter"
    type: "player"
    hp: 20
    armor_class: 16
    dex: 12
    position: [0, 0]
""")
        loader = ScenarioLoader(yaml_file)
        session = loader.build_session(mode="mock", seed=42)
        tm = session._gm.world_tile_manager

        for y in range(5):
            assert tm.is_blocking(2, y)
        assert not tm.is_blocking(0, 0)

    def test_pathfinder_respects_blocking_from_yaml(self, tmp_path):
        """Pathfinder returns None when entire column is blocked."""
        yaml_file = tmp_path / "pathfinder_test.yaml"
        yaml_file.write_text("""\
name: "Pathfinder Test"
description: "Test pathfinding with blocking"
map_size: [5, 5]
max_rounds: 5
terrain:
  wall:
    positions: [[2, 0], [2, 1], [2, 2], [2, 3], [2, 4]]
    blocking: true
entities:
  - name: "Fighter"
    type: "player"
    hp: 20
    armor_class: 16
    dex: 12
    position: [0, 0]
""")
        loader = ScenarioLoader(yaml_file)
        session = loader.build_session(mode="mock", seed=42)
        tm = session._gm.world_tile_manager

        # Complete wall — no way through
        assert find_path((0, 0), (4, 0), tm) is None

    def test_pathfinder_goes_around_partial_wall(self, tmp_path):
        """Pathfinder routes around a partial wall when a gap exists."""
        yaml_file = tmp_path / "gap_test.yaml"
        yaml_file.write_text("""\
name: "Gap Test"
description: "Partial wall with gap"
map_size: [5, 5]
max_rounds: 5
terrain:
  wall:
    positions: [[2, 0], [2, 1], [2, 2], [2, 3]]
    blocking: true
entities:
  - name: "Fighter"
    type: "player"
    hp: 20
    armor_class: 16
    dex: 12
    position: [0, 0]
""")
        loader = ScenarioLoader(yaml_file)
        session = loader.build_session(mode="mock", seed=42)
        tm = session._gm.world_tile_manager

        # Gap at (2, 4) — path should exist
        path = find_path((0, 0), (4, 0), tm)
        assert path is not None
        assert path[0] == (0, 0)
        assert path[-1] == (4, 0)
        # Must pass through the gap
        assert any(p[0] == 2 and p[1] == 4 for p in path)


class TestMoveActionTerrainValidation:
    """Verify MoveAction.validate() respects terrain via the pathfinder."""

    def test_move_blocked_by_wall(self, tmp_path):
        """MoveAction rejects a move when the only path is blocked."""
        yaml_file = tmp_path / "move_wall.yaml"
        yaml_file.write_text("""\
name: "Move Wall Test"
description: "Wall blocks movement"
map_size: [5, 5]
max_rounds: 5
terrain:
  wall:
    positions: [[2, 0], [2, 1], [2, 2], [2, 3], [2, 4]]
    blocking: true
entities:
  - name: "Fighter"
    type: "player"
    hp: 20
    armor_class: 16
    dex: 12
    speed: 30
    position: [0, 0]
""")
        loader = ScenarioLoader(yaml_file)
        session = loader.build_session(mode="mock", seed=42)
        tm = session._gm.world_tile_manager
        fighter = session._gm.game_entities[0]

        action = MoveAction(fighter, (4, 0), world_tile_manager=tm)
        assert action.validate(None) is False
        assert any("No path" in msg for msg in action.execution_log)

    def test_move_through_gap_succeeds(self, tmp_path):
        """MoveAction allows move when a path exists around partial wall."""
        yaml_file = tmp_path / "move_gap.yaml"
        yaml_file.write_text("""\
name: "Move Gap Test"
description: "Partial wall with gap"
map_size: [5, 5]
max_rounds: 5
terrain:
  wall:
    positions: [[2, 0], [2, 1], [2, 2], [2, 3]]
    blocking: true
entities:
  - name: "Fighter"
    type: "player"
    hp: 20
    armor_class: 16
    dex: 12
    speed: 60
    position: [0, 0]
""")
        loader = ScenarioLoader(yaml_file)
        session = loader.build_session(mode="mock", seed=42)
        tm = session._gm.world_tile_manager
        fighter = session._gm.game_entities[0]

        # With enough speed, the long path around the wall should be valid
        action = MoveAction(fighter, (4, 0), world_tile_manager=tm)
        assert action.validate(None) is True

    def test_move_exceeds_speed_budget(self, tmp_path):
        """MoveAction rejects a move whose path cost exceeds entity speed."""
        yaml_file = tmp_path / "move_budget.yaml"
        yaml_file.write_text("""\
name: "Move Budget Test"
description: "Speed budget limits movement"
map_size: [10, 3]
max_rounds: 5
entities:
  - name: "Fighter"
    type: "player"
    hp: 20
    armor_class: 16
    dex: 12
    speed: 15
    position: [0, 0]
""")
        loader = ScenarioLoader(yaml_file)
        session = loader.build_session(mode="mock", seed=42)
        tm = session._gm.world_tile_manager
        fighter = session._gm.game_entities[0]

        # 15ft speed = 3 tiles. Moving 7 tiles (35ft) should fail
        action = MoveAction(fighter, (7, 0), world_tile_manager=tm)
        assert action.validate(None) is False
        assert any("exceeds speed" in msg for msg in action.execution_log)

    def test_move_within_speed_succeeds(self, tmp_path):
        """MoveAction allows move within speed budget."""
        yaml_file = tmp_path / "move_ok.yaml"
        yaml_file.write_text("""\
name: "Move OK Test"
description: "Move within budget"
map_size: [10, 3]
max_rounds: 5
entities:
  - name: "Fighter"
    type: "player"
    hp: 20
    armor_class: 16
    dex: 12
    speed: 30
    position: [0, 0]
""")
        loader = ScenarioLoader(yaml_file)
        session = loader.build_session(mode="mock", seed=42)
        tm = session._gm.world_tile_manager
        fighter = session._gm.game_entities[0]

        # 30ft speed = 6 tiles. Moving 3 tiles (15ft) should succeed
        action = MoveAction(fighter, (3, 0), world_tile_manager=tm)
        assert action.validate(None) is True

    def test_difficult_terrain_costs_double(self, tmp_path):
        """Difficult terrain (cost:10) uses double movement, limiting distance."""
        yaml_file = tmp_path / "move_difficult.yaml"
        yaml_file.write_text("""\
name: "Difficult Terrain Test"
description: "Difficult terrain costs double"
map_size: [6, 3]
max_rounds: 5
terrain:
  mud:
    positions: [[1, 0], [2, 0], [3, 0]]
    movement_cost: 10
entities:
  - name: "Fighter"
    type: "player"
    hp: 20
    armor_class: 16
    dex: 12
    speed: 20
    position: [0, 0]
""")
        loader = ScenarioLoader(yaml_file)
        session = loader.build_session(mode="mock", seed=42)
        tm = session._gm.world_tile_manager
        fighter = session._gm.game_entities[0]

        # Tiles 1-3 cost 10ft each. Path (0,0)->(1,0)->(2,0)->(3,0)->(4,0)
        # Cost = 10 + 10 + 10 + 5 = 35ft.  Speed = 20ft -> too far.
        action = MoveAction(fighter, (4, 0), world_tile_manager=tm)
        assert action.validate(None) is False

        # But moving just 2 tiles into mud: (0,0)->(1,0)->(2,0)
        # Cost = 10 + 10 = 20ft.  Speed = 20ft -> exactly enough.
        action2 = MoveAction(fighter, (2, 0), world_tile_manager=tm)
        assert action2.validate(None) is True
