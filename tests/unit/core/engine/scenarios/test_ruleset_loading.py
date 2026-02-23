"""Tests for YAML rules: section → Ruleset → ActionExecutor pipeline."""

import pytest

from core.engine.scenarios.scenario_loader import ScenarioLoader, _parse_ruleset
from domain.specs.ruleset import Ruleset, RuleInstance


class TestParseRuleset:

    def test_returns_none_when_absent(self):
        assert _parse_ruleset(None) is None
        assert _parse_ruleset({}) is None

    def test_basic_ruleset_from_dict(self):
        data = {
            "ruleset_id": "test_rules",
            "name": "Test Rules",
            "active_rules": [
                {"rule_id": "is_alive"},
                {"rule_id": "can_take_action"},
            ],
        }
        rs = _parse_ruleset(data)
        assert rs is not None
        assert rs.ruleset_id == "test_rules"
        assert rs.name == "Test Rules"
        assert len(rs.active_rules) == 2
        assert rs.active_rules[0].rule_id == "is_alive"

    def test_rule_with_params(self):
        data = {
            "ruleset_id": "trap_rules",
            "name": "Trap Zone",
            "active_rules": [
                {
                    "rule_id": "skill_check",
                    "params": {"skill": "Perception", "dc": 15},
                },
            ],
        }
        rs = _parse_ruleset(data)
        rule = rs.active_rules[0]
        assert rule.rule_id == "skill_check"
        assert rule.params == {"skill": "Perception", "dc": 15}

    def test_inverted_rule(self):
        data = {
            "ruleset_id": "inv",
            "name": "Inverted",
            "active_rules": [
                {"rule_id": "is_alive", "inverted": True},
            ],
        }
        rs = _parse_ruleset(data)
        assert rs.active_rules[0].inverted is True

    def test_enforce_base_rules_default_true(self):
        data = {"ruleset_id": "test", "name": "Test"}
        rs = _parse_ruleset(data)
        assert rs.enforce_base_rules is True

    def test_enforce_base_rules_can_be_disabled(self):
        data = {
            "ruleset_id": "test",
            "name": "Test",
            "enforce_base_rules": False,
        }
        rs = _parse_ruleset(data)
        assert rs.enforce_base_rules is False


class TestScenarioLoaderRules:

    def test_session_receives_ruleset_from_yaml(self, tmp_path):
        """Ruleset from YAML is passed through to the GameSession."""
        yaml_file = tmp_path / "rules_scenario.yaml"
        yaml_file.write_text("""\
name: "Rules Test"
description: "Test rules loading"
map_size: [5, 5]
max_rounds: 5
rules:
  ruleset_id: scenario_trap
  name: "Trap Zone Rules"
  active_rules:
    - rule_id: is_alive
    - rule_id: can_take_action
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

        # The session's executor should have the ruleset
        assert session._executor._ruleset is not None
        assert session._executor._ruleset.ruleset_id == "scenario_trap"
        assert len(session._executor._ruleset.active_rules) == 2

    def test_session_without_rules_has_no_ruleset(self, tmp_path):
        """When no rules: section exists, ruleset is None."""
        yaml_file = tmp_path / "no_rules.yaml"
        yaml_file.write_text("""\
name: "No Rules"
description: "Scenario without rules section"
map_size: [5, 5]
max_rounds: 5
entities:
  - name: "Fighter"
    type: "player"
    hp: 20
    position: [0, 0]
""")
        loader = ScenarioLoader(yaml_file)
        session = loader.build_session(mode="mock", seed=42)

        assert session._executor._ruleset is None


class TestActionExecutorWithRuleset:

    def test_executor_uses_ruleset_specs(self):
        """When a ruleset is configured, its specs are used for validation."""
        from core.engine.action_executor import ActionExecutor
        from domain.specs.ruleset import Ruleset

        ruleset = Ruleset(
            ruleset_id="test",
            name="Test",
            enforce_base_rules=True,
        )
        ruleset.add_rule("has_movement", required=5)

        executor = ActionExecutor(ruleset=ruleset)
        specs = executor._build_specs(None)

        # Should include base rules (is_alive, can_take_action) plus has_movement
        rule_ids = [s.rule_id for s in specs]
        assert "is_alive" in rule_ids
        assert "can_take_action" in rule_ids
        assert "has_movement_5" in rule_ids

    def test_executor_without_ruleset_uses_defaults(self):
        """Without a ruleset, executor falls back to hardcoded specs."""
        from core.engine.action_executor import ActionExecutor

        executor = ActionExecutor(ruleset=None)
        specs = executor._build_specs(None)

        assert len(specs) == 2
        rule_ids = [s.rule_id for s in specs]
        assert "is_alive" in rule_ids
        assert "can_take_action" in rule_ids


class TestRulesetRoundTrip:

    def test_yaml_to_ruleset_to_dict_roundtrip(self, tmp_path):
        """Ruleset loaded from YAML can be serialized and deserialized."""
        yaml_file = tmp_path / "roundtrip.yaml"
        yaml_file.write_text("""\
name: "Roundtrip"
description: "Test roundtrip"
map_size: [5, 5]
max_rounds: 5
rules:
  ruleset_id: rt_test
  name: "Roundtrip Rules"
  description: "Testing serialization"
  active_rules:
    - rule_id: is_alive
    - rule_id: skill_check
      params:
        skill: Perception
        dc: 15
    - rule_id: has_movement
      params:
        required: 10
entities:
  - name: "Fighter"
    type: "player"
    hp: 20
    position: [0, 0]
""")
        loader = ScenarioLoader(yaml_file)
        session = loader.build_session(mode="mock", seed=42)
        original = session._executor._ruleset

        # Serialize and deserialize
        data = original.to_dict()
        restored = Ruleset.from_dict(data)

        assert restored.ruleset_id == original.ruleset_id
        assert restored.name == original.name
        assert len(restored.active_rules) == len(original.active_rules)
        for orig, rest in zip(original.active_rules, restored.active_rules):
            assert orig.rule_id == rest.rule_id
            assert orig.params == rest.params
