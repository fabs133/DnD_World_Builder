"""Dice expressions: parsing and rolling.

Supported syntax (whitespace and case are ignored)::

    d20            one die
    2d6+3          dice plus a flat modifier
    1d8+2d6-1      several dice terms and modifiers
    2d20kh1        keep the highest N dice (advantage); ``kl`` keeps the lowest

Rolling takes the random source as a parameter so results are reproducible
with a seeded :class:`random.Random`.
"""

from __future__ import annotations

import random as _random
import re
from dataclasses import dataclass

#: Upper bounds that keep a typo like ``1000000d6`` from freezing the UI.
MAX_DICE = 100
MAX_SIDES = 1000

_TERM = re.compile(r"([+-])(?:(\d*)d(\d+)(?:(kh|kl)(\d+))?|(\d+))")


@dataclass(frozen=True)
class DiceTerm:
    """One ``NdS`` term (``sides`` > 0) or a flat modifier (``sides`` == 0)."""

    sign: int
    count: int
    sides: int
    keep: str | None = None  #: "kh" or "kl"
    keep_count: int = 0

    @property
    def is_modifier(self) -> bool:
        return self.sides == 0

    def label(self) -> str:
        if self.is_modifier:
            return str(self.count)
        keep = f"{self.keep}{self.keep_count}" if self.keep else ""
        return f"{self.count}d{self.sides}{keep}"


@dataclass(frozen=True)
class TermResult:
    term: DiceTerm
    rolls: tuple[int, ...]  #: every die rolled (empty for modifiers)
    kept: tuple[int, ...]  #: dice that count towards the total
    subtotal: int  #: signed contribution to the total


@dataclass(frozen=True)
class DiceRoll:
    expression: str
    results: tuple[TermResult, ...]
    total: int

    @property
    def rolls(self) -> list[int]:
        """All kept dice values, in order."""
        return [value for r in self.results for value in r.kept]

    @property
    def modifier(self) -> int:
        """Sum of the flat modifiers."""
        return sum(r.subtotal for r in self.results if r.term.is_modifier)


def parse(expression: str) -> tuple[DiceTerm, ...]:
    """Parse ``expression`` into terms.

    :raises ValueError: If the expression is malformed, has no dice, or exceeds the limits.
    """
    text = expression.replace(" ", "").lower()
    if not text:
        raise ValueError(f"Invalid dice expression: {expression!r}")
    if text[0] not in "+-":
        text = "+" + text

    terms = []
    pos = 0
    while pos < len(text):
        match = _TERM.match(text, pos)
        if not match:
            raise ValueError(f"Invalid dice expression: {expression!r}")
        sign = 1 if match.group(1) == "+" else -1
        if match.group(6) is not None:
            terms.append(DiceTerm(sign, int(match.group(6)), 0))
        else:
            count = int(match.group(2)) if match.group(2) else 1
            sides = int(match.group(3))
            keep = match.group(4)
            keep_count = int(match.group(5)) if keep else 0
            if not 1 <= count <= MAX_DICE or not 2 <= sides <= MAX_SIDES:
                raise ValueError(
                    f"Dice out of range in {expression!r}: up to {MAX_DICE} dice with 2-{MAX_SIDES} sides"
                )
            if keep and not 1 <= keep_count <= count:
                raise ValueError(f"Cannot keep {keep_count} of {count} dice in {expression!r}")
            terms.append(DiceTerm(sign, count, sides, keep, keep_count))
        pos = match.end()

    if all(t.is_modifier for t in terms):
        raise ValueError(f"Invalid dice expression: {expression!r} has no dice")
    return tuple(terms)


def roll(expression: str, rng: _random.Random | None = None) -> DiceRoll:
    """Roll ``expression``.

    :param rng: Anything with ``randint(a, b)``; defaults to the ``random`` module.
    :raises ValueError: See :func:`parse`.
    """
    source = rng if rng is not None else _random
    results = []
    for term in parse(expression):
        if term.is_modifier:
            results.append(TermResult(term, (), (), term.sign * term.count))
            continue
        rolls = tuple(source.randint(1, term.sides) for _ in range(term.count))
        if term.keep:
            ordered = sorted(rolls, reverse=(term.keep == "kh"))
            kept = tuple(ordered[: term.keep_count])
        else:
            kept = rolls
        results.append(TermResult(term, rolls, kept, term.sign * sum(kept)))
    return DiceRoll(expression.strip(), tuple(results), sum(r.subtotal for r in results))


def format_roll(result: DiceRoll) -> str:
    """Human-readable breakdown, e.g. ``2d6+3: [4, 2] +3 = 9``."""
    parts = []
    for r in result.results:
        sign = "-" if r.term.sign < 0 else "+"
        if r.term.is_modifier:
            body = str(r.term.count)
        elif r.term.keep:
            body = f"{list(r.rolls)}→{list(r.kept)}"
        else:
            body = str(list(r.rolls))
        parts.append(f"{sign}{body}")
    breakdown = " ".join(parts)
    if breakdown.startswith("+"):
        breakdown = breakdown[1:]
    return f"{result.expression}: {breakdown} = {result.total}"
