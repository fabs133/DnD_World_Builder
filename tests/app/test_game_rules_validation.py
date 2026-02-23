"""Game rules validation tests using post-run validators."""

from __future__ import annotations

import pytest

from core.testing import (
    BehavioralTestHarness,
    ScenarioConfig,
    HarnessConfig,
)
from core.testing.validation.validators import (
    validate_no_negative_hp,
    validate_dead_entities_dont_act,
    validate_initiative_order_respected,
    validate_damage_consistency,
    validate_session,
)
from core.engine.scenarios.scenario_loader import ScenarioLoader


def _run_session_with_seed(yaml_path: str, seed: int):
    """Run a single game session and return the result."""
    loader = ScenarioLoader(yaml_path)
    session = loader.build_session(mode="mock", seed=seed, max_rounds=20)
    session.setup()
    return session.run()


class TestNoNegativeHP:
    """No entity's HP should go below 0."""

    @pytest.mark.parametrize("seed", range(1, 6))
    def test_no_negative_hp(self, goblin_ambush_yaml, seed):
        result = _run_session_with_seed(str(goblin_ambush_yaml), seed)
        vr = validate_no_negative_hp(result)
        assert vr.passed, f"Violations: {vr.violations}"


class TestDeadDontAct:
    """Dead entities should be skipped."""

    @pytest.mark.parametrize("seed", range(1, 6))
    def test_dead_entities_dont_act(self, goblin_ambush_yaml, seed):
        result = _run_session_with_seed(str(goblin_ambush_yaml), seed)
        vr = validate_dead_entities_dont_act(result)
        assert vr.passed, f"Violations: {vr.violations}"


class TestInitiativeOrder:
    """Turns should follow initiative order."""

    @pytest.mark.parametrize("seed", range(1, 4))
    def test_initiative_order(self, goblin_ambush_yaml, seed):
        result = _run_session_with_seed(str(goblin_ambush_yaml), seed)
        vr = validate_initiative_order_respected(result)
        assert vr.passed, f"Violations: {vr.violations}"


class TestDamageConsistency:
    """Damage values in logs should be non-negative."""

    @pytest.mark.parametrize("seed", range(1, 4))
    def test_damage_matches_logs(self, goblin_ambush_yaml, seed):
        result = _run_session_with_seed(str(goblin_ambush_yaml), seed)
        vr = validate_damage_consistency(result)
        assert vr.passed, f"Violations: {vr.violations}"


class TestFullValidation:
    """Run all validators at once."""

    def test_full_session_validation(self, goblin_ambush_yaml):
        result = _run_session_with_seed(str(goblin_ambush_yaml), seed=42)
        vr = validate_session(result)
        assert vr.passed, f"Violations: {vr.violations}"
