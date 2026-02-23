"""Tests for domain.specs.base — Specification pattern core."""

import pytest

from domain.specs.base import (
    Specification,
    SpecResult,
    AndSpec,
    OrSpec,
    NotSpec,
    AllOf,
    AnyOf,
    AlwaysTrue,
    AlwaysFalse,
    LambdaSpec,
)


# ── SpecResult ──────────────────────────────────────────────────────────────

class TestSpecResult:
    def test_passed_is_truthy(self):
        r = SpecResult(rule_id="x", passed=True)
        assert bool(r) is True

    def test_failed_is_falsy(self):
        r = SpecResult(rule_id="x", passed=False)
        assert bool(r) is False

    def test_repr_contains_checkmark_on_pass(self):
        r = SpecResult(rule_id="test_rule", passed=True, message="ok")
        assert "✓" in repr(r)

    def test_repr_contains_cross_on_fail(self):
        r = SpecResult(rule_id="test_rule", passed=False, message="bad")
        assert "✗" in repr(r)

    def test_to_dict_roundtrip(self):
        original = SpecResult(
            rule_id="r1",
            passed=True,
            message="hello",
            suggested_fix="do this",
            tags=frozenset({"a", "b"}),
            data={"key": 42},
        )
        d = original.to_dict()
        restored = SpecResult.from_dict(d)
        assert restored.rule_id == original.rule_id
        assert restored.passed == original.passed
        assert restored.message == original.message
        assert restored.suggested_fix == original.suggested_fix
        assert restored.data == original.data
        assert set(restored.tags) == set(original.tags)

    def test_from_dict_minimal(self):
        r = SpecResult.from_dict({"rule_id": "x", "passed": False})
        assert r.rule_id == "x"
        assert r.passed is False
        assert r.message == ""
        assert r.suggested_fix is None

    def test_frozen(self):
        r = SpecResult(rule_id="x", passed=True)
        with pytest.raises(AttributeError):
            r.passed = False


# ── AlwaysTrue / AlwaysFalse ────────────────────────────────────────────────

class TestAlwaysTrue:
    def test_always_passes(self):
        spec = AlwaysTrue()
        result = spec.is_satisfied_by("anything")
        assert result.passed is True

    def test_rule_id(self):
        assert AlwaysTrue().rule_id == "always_true"

    def test_to_dict(self):
        assert AlwaysTrue().to_dict() == {"type": "AlwaysTrue"}

    def test_from_dict(self):
        spec = AlwaysTrue.from_dict({"type": "AlwaysTrue"})
        assert spec.is_satisfied_by(None).passed is True

    def test_with_context(self):
        result = AlwaysTrue().is_satisfied_by("x", context={"extra": 1})
        assert result.passed is True


class TestAlwaysFalse:
    def test_always_fails(self):
        spec = AlwaysFalse()
        result = spec.is_satisfied_by("anything")
        assert result.passed is False

    def test_custom_message(self):
        spec = AlwaysFalse(message="blocked", suggested_fix="try again")
        result = spec.is_satisfied_by(None)
        assert result.message == "blocked"
        assert result.suggested_fix == "try again"

    def test_rule_id(self):
        assert AlwaysFalse().rule_id == "always_false"

    def test_from_dict(self):
        spec = AlwaysFalse.from_dict({"message": "nope", "suggested_fix": "fix"})
        result = spec.is_satisfied_by(None)
        assert result.message == "nope"
        assert result.suggested_fix == "fix"

    def test_tags_include_blocker(self):
        result = AlwaysFalse().is_satisfied_by(None)
        assert "blocker" in result.tags


# ── AndSpec (& operator) ────────────────────────────────────────────────────

class TestAndSpec:
    def test_both_pass(self):
        spec = AlwaysTrue() & AlwaysTrue()
        assert spec.is_satisfied_by(None).passed is True

    def test_left_fails(self):
        spec = AlwaysFalse() & AlwaysTrue()
        assert spec.is_satisfied_by(None).passed is False

    def test_right_fails(self):
        spec = AlwaysTrue() & AlwaysFalse()
        assert spec.is_satisfied_by(None).passed is False

    def test_both_fail(self):
        spec = AlwaysFalse() & AlwaysFalse()
        assert spec.is_satisfied_by(None).passed is False

    def test_rule_id_contains_and(self):
        spec = AlwaysTrue() & AlwaysFalse()
        assert "AND" in spec.rule_id

    def test_to_dict(self):
        spec = AlwaysTrue() & AlwaysFalse()
        d = spec.to_dict()
        assert d["type"] == "AndSpec"
        assert "left" in d
        assert "right" in d


# ── OrSpec (| operator) ─────────────────────────────────────────────────────

class TestOrSpec:
    def test_both_pass(self):
        spec = AlwaysTrue() | AlwaysTrue()
        assert spec.is_satisfied_by(None).passed is True

    def test_left_passes(self):
        spec = AlwaysTrue() | AlwaysFalse()
        assert spec.is_satisfied_by(None).passed is True

    def test_right_passes(self):
        spec = AlwaysFalse() | AlwaysTrue()
        assert spec.is_satisfied_by(None).passed is True

    def test_both_fail(self):
        spec = AlwaysFalse() | AlwaysFalse()
        assert spec.is_satisfied_by(None).passed is False

    def test_rule_id_contains_or(self):
        spec = AlwaysTrue() | AlwaysFalse()
        assert "OR" in spec.rule_id


# ── NotSpec (~ operator) ────────────────────────────────────────────────────

class TestNotSpec:
    def test_inverts_true(self):
        spec = ~AlwaysTrue()
        assert spec.is_satisfied_by(None).passed is False

    def test_inverts_false(self):
        spec = ~AlwaysFalse()
        assert spec.is_satisfied_by(None).passed is True

    def test_double_negation(self):
        spec = ~~AlwaysTrue()
        assert spec.is_satisfied_by(None).passed is True

    def test_rule_id_contains_not(self):
        spec = ~AlwaysTrue()
        assert "NOT" in spec.rule_id


# ── AllOf ────────────────────────────────────────────────────────────────────

class TestAllOf:
    def test_all_pass(self):
        spec = AllOf(AlwaysTrue(), AlwaysTrue(), AlwaysTrue())
        assert spec.is_satisfied_by(None).passed is True

    def test_one_fails(self):
        spec = AllOf(AlwaysTrue(), AlwaysFalse(), AlwaysTrue())
        assert spec.is_satisfied_by(None).passed is False

    def test_reports_all_failures_without_short_circuit(self):
        spec = AllOf(
            AlwaysFalse(message="err1"),
            AlwaysFalse(message="err2"),
            short_circuit=False,
        )
        result = spec.is_satisfied_by(None)
        assert result.passed is False
        assert result.data["failed"] == 2

    def test_short_circuit_stops_early(self):
        spec = AllOf(
            AlwaysFalse(message="first"),
            AlwaysTrue(),
            short_circuit=True,
        )
        result = spec.is_satisfied_by(None)
        assert result.passed is False
        # With short-circuit, should stop after first failure
        assert result.data["failed"] == 1

    def test_empty_allof_passes(self):
        spec = AllOf()
        assert spec.is_satisfied_by(None).passed is True

    def test_rule_id(self):
        spec = AllOf(AlwaysTrue(), AlwaysFalse())
        assert "AllOf" in spec.rule_id


# ── AnyOf ────────────────────────────────────────────────────────────────────

class TestAnyOf:
    def test_one_passes(self):
        spec = AnyOf(AlwaysFalse(), AlwaysTrue(), AlwaysFalse())
        assert spec.is_satisfied_by(None).passed is True

    def test_none_pass(self):
        spec = AnyOf(AlwaysFalse(), AlwaysFalse())
        assert spec.is_satisfied_by(None).passed is False

    def test_short_circuit_default(self):
        spec = AnyOf(AlwaysTrue(), AlwaysFalse())
        result = spec.is_satisfied_by(None)
        assert result.passed is True

    def test_all_pass(self):
        spec = AnyOf(AlwaysTrue(), AlwaysTrue())
        assert spec.is_satisfied_by(None).passed is True

    def test_rule_id(self):
        spec = AnyOf(AlwaysTrue())
        assert "AnyOf" in spec.rule_id


# ── LambdaSpec ───────────────────────────────────────────────────────────────

class TestLambdaSpec:
    def test_predicate_true(self):
        spec = LambdaSpec("gt10", lambda x, _: x > 10, fail_message="too small")
        result = spec.is_satisfied_by(15)
        assert result.passed is True

    def test_predicate_false(self):
        spec = LambdaSpec("gt10", lambda x, _: x > 10, fail_message="too small")
        result = spec.is_satisfied_by(5)
        assert result.passed is False
        assert result.message == "too small"

    def test_uses_context(self):
        spec = LambdaSpec(
            "ctx_check",
            lambda x, ctx: ctx and ctx.get("ok", False),
        )
        assert spec.is_satisfied_by(None, {"ok": True}).passed is True
        assert spec.is_satisfied_by(None, {"ok": False}).passed is False

    def test_tags(self):
        spec = LambdaSpec("t", lambda x, _: True, tags=frozenset({"custom"}))
        result = spec.is_satisfied_by(None)
        assert "custom" in result.tags
        assert "lambda" in result.tags

    def test_suggested_fix(self):
        spec = LambdaSpec("t", lambda x, _: False, suggested_fix="do X")
        result = spec.is_satisfied_by(None)
        assert result.suggested_fix == "do X"


# ── Composition chaining ────────────────────────────────────────────────────

class TestComposition:
    def test_and_or_chain(self):
        spec = (AlwaysTrue() & AlwaysTrue()) | AlwaysFalse()
        assert spec.is_satisfied_by(None).passed is True

    def test_not_and(self):
        spec = ~(AlwaysTrue() & AlwaysFalse())
        assert spec.is_satisfied_by(None).passed is True

    def test_complex_chain(self):
        spec = (AlwaysTrue() | AlwaysFalse()) & ~AlwaysFalse()
        assert spec.is_satisfied_by(None).passed is True
