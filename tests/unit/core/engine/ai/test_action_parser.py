"""Tests for ActionParser."""

import pytest
from core.engine.ai.action_parser import ActionParser, ParseError
from core.engine.game_state import GameState, EntitySnapshot
from core.engine.actions.attack_action import AttackAction
from core.engine.actions.move_action import MoveAction
from core.engine.actions.end_turn_action import EndTurnAction


class SimpleEntity:
    def __init__(self, name, hp=10):
        self.name = name
        self.hp = hp


def _make_state():
    goblin = EntitySnapshot(
        name="Goblin", entity_type="enemy", hp=7, max_hp=7,
        armor_class=13, position=(2, 0), conditions=(), stats={},
        speed=30, faction="enemy", is_alive=True,
    )
    return GameState(
        round_number=1, current_entity_name="Fighter",
        entities=(goblin,), initiative_order=("Fighter", "Goblin"),
        world_width=5, world_height=5, tile_type="square",
    )


class TestActionParser:
    def test_parse_attack(self):
        parser = ActionParser()
        actor = SimpleEntity("Fighter")
        target = SimpleEntity("Goblin")
        state = _make_state()

        action = parser.parse(
            "ACTION: ATTACK TARGET: Goblin",
            actor, state, entities_by_name={"Goblin": target},
        )
        assert isinstance(action, AttackAction)

    def test_parse_move(self):
        parser = ActionParser()
        actor = SimpleEntity("Fighter")
        state = _make_state()

        action = parser.parse("ACTION: MOVE POSITION: 3,4", actor, state)
        assert isinstance(action, MoveAction)
        assert action.target_position == (3, 4)

    def test_parse_end_turn(self):
        parser = ActionParser()
        actor = SimpleEntity("Fighter")
        state = _make_state()

        action = parser.parse("ACTION: END_TURN", actor, state)
        assert isinstance(action, EndTurnAction)

    def test_parse_case_insensitive(self):
        parser = ActionParser()
        actor = SimpleEntity("Fighter")
        state = _make_state()

        action = parser.parse("action: end_turn", actor, state)
        assert isinstance(action, EndTurnAction)

    def test_parse_with_surrounding_text(self):
        parser = ActionParser()
        actor = SimpleEntity("Fighter")
        target = SimpleEntity("Goblin")
        state = _make_state()

        action = parser.parse(
            "I think I should attack. ACTION: ATTACK TARGET: Goblin\nThat seems best.",
            actor, state, entities_by_name={"Goblin": target},
        )
        assert isinstance(action, AttackAction)

    def test_parse_no_action_pattern(self):
        parser = ActionParser()
        actor = SimpleEntity("Fighter")
        state = _make_state()

        with pytest.raises(ParseError, match="Could not find ACTION"):
            parser.parse("I want to attack the goblin", actor, state)

    def test_parse_attack_missing_target(self):
        parser = ActionParser()
        actor = SimpleEntity("Fighter")
        state = _make_state()

        with pytest.raises(ParseError, match="ATTACK requires TARGET"):
            parser.parse("ACTION: ATTACK", actor, state)

    def test_parse_move_missing_position(self):
        parser = ActionParser()
        actor = SimpleEntity("Fighter")
        state = _make_state()

        with pytest.raises(ParseError, match="MOVE requires POSITION"):
            parser.parse("ACTION: MOVE", actor, state)

    def test_parse_unknown_action(self):
        parser = ActionParser()
        actor = SimpleEntity("Fighter")
        state = _make_state()

        with pytest.raises(ParseError, match="Unknown action type"):
            parser.parse("ACTION: FLY", actor, state)

    def test_parse_target_not_found(self):
        parser = ActionParser()
        actor = SimpleEntity("Fighter")
        state = _make_state()

        with pytest.raises(ParseError, match="not found"):
            parser.parse("ACTION: ATTACK TARGET: Dragon", actor, state)

    def test_parse_dash_maps_to_end_turn(self):
        parser = ActionParser()
        actor = SimpleEntity("Fighter")
        state = _make_state()

        action = parser.parse("ACTION: DASH", actor, state)
        assert isinstance(action, EndTurnAction)

    def test_parse_error_includes_raw_output(self):
        parser = ActionParser()
        actor = SimpleEntity("Fighter")
        state = _make_state()

        try:
            parser.parse("garbage text", actor, state)
        except ParseError as e:
            assert e.raw_output == "garbage text"
