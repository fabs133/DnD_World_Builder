"""
Base Specification Pattern Implementation

This module provides the foundation for encoding D&D rules as composable,
traceable specifications. Each spec is a pure function that evaluates
a candidate against a rule and returns a rich result.

Design principles (from Agent Specification Pattern):
- Specs are pure: no IO, no state mutation, deterministic
- Results are structured: rule_id, passed, message, suggested_fix, tags, data
- Composition via operators: &, |, ~
- Full traceability: every evaluation can be logged and debugged
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar, Callable

# Type variable for the candidate being evaluated
T = TypeVar("T")


@dataclass(frozen=True)
class SpecResult:
    """
    Rich result from a specification evaluation.
    
    This replaces simple bool returns with structured data that enables:
    - Player feedback: "You need 5 more feet of movement"
    - GM tracing: See exactly which rules passed/failed
    - Self-correction: suggested_fix tells what to do next
    - Debugging: data dict has all relevant values
    
    Attributes:
        rule_id: Stable identifier for this rule (e.g., "has_movement_30")
        passed: Whether the specification was satisfied
        message: Human-readable description of the outcome
        suggested_fix: Concrete action to take if failed (for player/AI guidance)
        tags: Category labels for filtering/grouping (e.g., {"combat", "movement"})
        data: Structured details for debugging (e.g., {"required": 30, "available": 25})
    """
    rule_id: str
    passed: bool
    message: str = ""
    suggested_fix: str | None = None
    tags: frozenset[str] = field(default_factory=frozenset)
    data: dict[str, Any] = field(default_factory=dict)
    
    def __bool__(self) -> bool:
        """Allow using SpecResult directly in boolean context."""
        return self.passed
    
    def __repr__(self) -> str:
        status = "✓" if self.passed else "✗"
        return f"SpecResult({status} {self.rule_id}: {self.message})"
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize for logging/storage."""
        return {
            "rule_id": self.rule_id,
            "passed": self.passed,
            "message": self.message,
            "suggested_fix": self.suggested_fix,
            "tags": list(self.tags),
            "data": self.data,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpecResult:
        """Deserialize from dict."""
        return cls(
            rule_id=data["rule_id"],
            passed=data["passed"],
            message=data.get("message", ""),
            suggested_fix=data.get("suggested_fix"),
            tags=frozenset(data.get("tags", [])),
            data=data.get("data", {}),
        )


class Specification(ABC, Generic[T]):
    """
    Abstract base for all specifications.
    
    A Specification encapsulates a single business rule that can be:
    - Evaluated against a candidate object
    - Combined with other specs using boolean operators
    - Serialized for storage/transmission
    - Traced for debugging
    
    Type parameter T is the type of object being evaluated
    (e.g., EntityState, TileState, Scenario).
    
    Example:
        class HasMovement(Specification[EntityState]):
            def __init__(self, required: int):
                self.required = required
            
            @property
            def rule_id(self) -> str:
                return f"has_movement_{self.required}"
            
            def is_satisfied_by(self, entity, context=None):
                available = entity.movement_remaining
                passed = available >= self.required
                return SpecResult(
                    rule_id=self.rule_id,
                    passed=passed,
                    message=f"Need {self.required}ft, have {available}ft",
                    suggested_fix=None if passed else "Use Dash action",
                    tags=frozenset({"movement", "resource"}),
                    data={"required": self.required, "available": available}
                )
    """
    
    @property
    @abstractmethod
    def rule_id(self) -> str:
        """
        Stable identifier for this rule.
        
        Used for:
        - Tracing: "Which rule failed?"
        - Routing: "If rule X failed, go to step Y"
        - Deduplication: Prevent identical retries
        
        Should be deterministic based on spec parameters.
        """
        pass
    
    @abstractmethod
    def is_satisfied_by(self, candidate: T, context: dict[str, Any] | None = None) -> SpecResult:
        """
        Evaluate whether the candidate satisfies this specification.
        
        Args:
            candidate: The object to evaluate (entity, tile, scenario, etc.)
            context: Optional additional context (roll results, game state, etc.)
                     Context is for data that isn't part of the candidate itself.
        
        Returns:
            SpecResult with full evaluation details
        
        Contract:
            - MUST be pure (no side effects)
            - MUST be deterministic (same inputs → same outputs)
            - MUST NOT mutate candidate or context
        """
        pass
    
    def __and__(self, other: Specification[T]) -> AndSpec[T]:
        """Compose with AND: both must pass."""
        return AndSpec(self, other)
    
    def __or__(self, other: Specification[T]) -> OrSpec[T]:
        """Compose with OR: at least one must pass."""
        return OrSpec(self, other)
    
    def __invert__(self) -> NotSpec[T]:
        """Negate: passes when inner fails."""
        return NotSpec(self)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.rule_id})"
    
    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the specification for storage.
        
        Override in subclasses to include parameters.
        """
        return {"type": self.__class__.__name__}
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Specification:
        """
        Deserialize from dict.
        
        Override in subclasses. Base implementation raises.
        """
        raise NotImplementedError(
            f"from_dict not implemented for {cls.__name__}. "
            "Use the SpecRegistry for polymorphic deserialization."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Composite Specifications
# ─────────────────────────────────────────────────────────────────────────────

class AndSpec(Specification[T]):
    """
    Composite spec: both left AND right must pass.
    
    Short-circuits on first failure for efficiency.
    """
    
    def __init__(self, left: Specification[T], right: Specification[T]):
        self.left = left
        self.right = right
    
    @property
    def rule_id(self) -> str:
        return f"({self.left.rule_id} AND {self.right.rule_id})"
    
    def is_satisfied_by(self, candidate: T, context: dict[str, Any] | None = None) -> SpecResult:
        left_result = self.left.is_satisfied_by(candidate, context)
        
        if not left_result.passed:
            # Short-circuit: return the failure
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message=left_result.message,
                suggested_fix=left_result.suggested_fix,
                tags=left_result.tags | frozenset({"and_failed_left"}),
                data={"failed_rule": self.left.rule_id, "result": left_result.to_dict()}
            )
        
        right_result = self.right.is_satisfied_by(candidate, context)
        
        if not right_result.passed:
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message=right_result.message,
                suggested_fix=right_result.suggested_fix,
                tags=right_result.tags | frozenset({"and_failed_right"}),
                data={"failed_rule": self.right.rule_id, "result": right_result.to_dict()}
            )
        
        # Both passed
        return SpecResult(
            rule_id=self.rule_id,
            passed=True,
            message="All conditions satisfied",
            tags=left_result.tags | right_result.tags,
            data={
                "left": left_result.to_dict(),
                "right": right_result.to_dict()
            }
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "AndSpec",
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }


class OrSpec(Specification[T]):
    """
    Composite spec: at least one of left OR right must pass.
    
    Short-circuits on first success.
    """
    
    def __init__(self, left: Specification[T], right: Specification[T]):
        self.left = left
        self.right = right
    
    @property
    def rule_id(self) -> str:
        return f"({self.left.rule_id} OR {self.right.rule_id})"
    
    def is_satisfied_by(self, candidate: T, context: dict[str, Any] | None = None) -> SpecResult:
        left_result = self.left.is_satisfied_by(candidate, context)
        
        if left_result.passed:
            # Short-circuit: return the success
            return SpecResult(
                rule_id=self.rule_id,
                passed=True,
                message=left_result.message,
                tags=left_result.tags | frozenset({"or_passed_left"}),
                data={"passed_rule": self.left.rule_id, "result": left_result.to_dict()}
            )
        
        right_result = self.right.is_satisfied_by(candidate, context)
        
        if right_result.passed:
            return SpecResult(
                rule_id=self.rule_id,
                passed=True,
                message=right_result.message,
                tags=right_result.tags | frozenset({"or_passed_right"}),
                data={"passed_rule": self.right.rule_id, "result": right_result.to_dict()}
            )
        
        # Both failed - combine failure info
        return SpecResult(
            rule_id=self.rule_id,
            passed=False,
            message=f"{left_result.message}; {right_result.message}",
            suggested_fix=left_result.suggested_fix or right_result.suggested_fix,
            tags=left_result.tags | right_result.tags | frozenset({"or_both_failed"}),
            data={
                "left": left_result.to_dict(),
                "right": right_result.to_dict()
            }
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "OrSpec",
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }


class NotSpec(Specification[T]):
    """
    Inverts the inner specification: passes when inner fails.
    """
    
    def __init__(self, inner: Specification[T]):
        self.inner = inner
    
    @property
    def rule_id(self) -> str:
        return f"(NOT {self.inner.rule_id})"
    
    def is_satisfied_by(self, candidate: T, context: dict[str, Any] | None = None) -> SpecResult:
        inner_result = self.inner.is_satisfied_by(candidate, context)
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=not inner_result.passed,
            message=f"Inverted: {inner_result.message}",
            suggested_fix=None if not inner_result.passed else f"Condition should NOT be met: {self.inner.rule_id}",
            tags=inner_result.tags | frozenset({"negated"}),
            data={"inner_result": inner_result.to_dict()}
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "NotSpec",
            "inner": self.inner.to_dict(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Collection Specifications (for evaluating multiple specs)
# ─────────────────────────────────────────────────────────────────────────────

class AllOf(Specification[T]):
    """
    All specifications in the list must pass.
    
    Unlike chained AndSpec, this:
    - Evaluates ALL specs (no short-circuit) for complete error reporting
    - Returns a list of all failures in data
    - Useful for validation where you want all errors at once
    """
    
    def __init__(self, *specs: Specification[T], short_circuit: bool = False):
        self.specs = list(specs)
        self.short_circuit = short_circuit
    
    @property
    def rule_id(self) -> str:
        inner = ", ".join(s.rule_id for s in self.specs)
        return f"AllOf({inner})"
    
    def is_satisfied_by(self, candidate: T, context: dict[str, Any] | None = None) -> SpecResult:
        results: list[SpecResult] = []
        failures: list[SpecResult] = []
        
        for spec in self.specs:
            result = spec.is_satisfied_by(candidate, context)
            results.append(result)
            
            if not result.passed:
                failures.append(result)
                if self.short_circuit:
                    break
        
        if failures:
            # Aggregate failure messages
            messages = [f.message for f in failures]
            first_fix = next((f.suggested_fix for f in failures if f.suggested_fix), None)
            all_tags = frozenset().union(*(f.tags for f in failures))
            
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message="; ".join(messages),
                suggested_fix=first_fix,
                tags=all_tags | frozenset({"all_of_failed"}),
                data={
                    "total": len(self.specs),
                    "passed": len(results) - len(failures),
                    "failed": len(failures),
                    "failures": [f.to_dict() for f in failures],
                }
            )
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=True,
            message=f"All {len(self.specs)} conditions satisfied",
            tags=frozenset().union(*(r.tags for r in results)),
            data={"total": len(self.specs), "results": [r.to_dict() for r in results]}
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "AllOf",
            "specs": [s.to_dict() for s in self.specs],
            "short_circuit": self.short_circuit,
        }


class AnyOf(Specification[T]):
    """
    At least one specification must pass.
    
    Unlike chained OrSpec, this:
    - Can short-circuit on first success (default) or evaluate all
    - Returns which spec(s) passed in data
    """
    
    def __init__(self, *specs: Specification[T], short_circuit: bool = True):
        self.specs = list(specs)
        self.short_circuit = short_circuit
    
    @property
    def rule_id(self) -> str:
        inner = ", ".join(s.rule_id for s in self.specs)
        return f"AnyOf({inner})"
    
    def is_satisfied_by(self, candidate: T, context: dict[str, Any] | None = None) -> SpecResult:
        results: list[SpecResult] = []
        successes: list[SpecResult] = []
        
        for spec in self.specs:
            result = spec.is_satisfied_by(candidate, context)
            results.append(result)
            
            if result.passed:
                successes.append(result)
                if self.short_circuit:
                    break
        
        if successes:
            first = successes[0]
            return SpecResult(
                rule_id=self.rule_id,
                passed=True,
                message=first.message,
                tags=first.tags | frozenset({"any_of_passed"}),
                data={
                    "passed_rule": first.rule_id,
                    "successes": [s.to_dict() for s in successes],
                }
            )
        
        # All failed
        messages = [r.message for r in results]
        fixes = [r.suggested_fix for r in results if r.suggested_fix]
        all_tags = frozenset().union(*(r.tags for r in results))
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=False,
            message=f"None of {len(self.specs)} options satisfied: " + "; ".join(messages),
            suggested_fix=fixes[0] if fixes else None,
            tags=all_tags | frozenset({"any_of_failed"}),
            data={
                "total": len(self.specs),
                "failures": [r.to_dict() for r in results],
            }
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "AnyOf",
            "specs": [s.to_dict() for s in self.specs],
            "short_circuit": self.short_circuit,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Specifications
# ─────────────────────────────────────────────────────────────────────────────

class AlwaysTrue(Specification[T]):
    """Specification that always passes. Useful for testing and as a default."""
    
    @property
    def rule_id(self) -> str:
        return "always_true"
    
    def is_satisfied_by(self, candidate: T, context: dict[str, Any] | None = None) -> SpecResult:
        return SpecResult(
            rule_id=self.rule_id,
            passed=True,
            message="Always passes",
            tags=frozenset({"constant"})
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {"type": "AlwaysTrue"}
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlwaysTrue:
        return cls()


class AlwaysFalse(Specification[T]):
    """Specification that always fails. Useful for testing and blocking."""
    
    def __init__(self, message: str = "Always fails", suggested_fix: str | None = None):
        self._message = message
        self._suggested_fix = suggested_fix
    
    @property
    def rule_id(self) -> str:
        return "always_false"
    
    def is_satisfied_by(self, candidate: T, context: dict[str, Any] | None = None) -> SpecResult:
        return SpecResult(
            rule_id=self.rule_id,
            passed=False,
            message=self._message,
            suggested_fix=self._suggested_fix,
            tags=frozenset({"constant", "blocker"})
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "AlwaysFalse",
            "message": self._message,
            "suggested_fix": self._suggested_fix,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlwaysFalse:
        return cls(
            message=data.get("message", "Always fails"),
            suggested_fix=data.get("suggested_fix")
        )


class LambdaSpec(Specification[T]):
    """
    Wrap a simple predicate function as a Specification.
    
    Useful for quick one-off rules without defining a full class.
    Note: Not serializable (lambdas can't be pickled).
    
    Example:
        is_adult = LambdaSpec(
            "is_adult",
            lambda entity, ctx: entity.age >= 18,
            fail_message="Must be 18 or older"
        )
    """
    
    def __init__(
        self,
        rule_id: str,
        predicate: Callable[[T, dict[str, Any] | None], bool],
        pass_message: str = "Condition satisfied",
        fail_message: str = "Condition not satisfied",
        suggested_fix: str | None = None,
        tags: frozenset[str] | None = None,
    ):
        self._rule_id = rule_id
        self._predicate = predicate
        self._pass_message = pass_message
        self._fail_message = fail_message
        self._suggested_fix = suggested_fix
        self._tags = tags or frozenset()
    
    @property
    def rule_id(self) -> str:
        return self._rule_id
    
    def is_satisfied_by(self, candidate: T, context: dict[str, Any] | None = None) -> SpecResult:
        passed = self._predicate(candidate, context)
        return SpecResult(
            rule_id=self.rule_id,
            passed=passed,
            message=self._pass_message if passed else self._fail_message,
            suggested_fix=None if passed else self._suggested_fix,
            tags=self._tags | frozenset({"lambda"})
        )
