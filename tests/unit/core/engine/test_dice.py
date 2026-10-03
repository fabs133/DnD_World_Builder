"""Tests for dice expression parsing and rolling."""

import random

import pytest

from core.engine.dice import MAX_DICE, format_roll, parse, roll


class FixedRng:
    """randint returns queued values in order."""

    def __init__(self, *values):
        self._values = list(values)

    def randint(self, a, b):
        value = self._values.pop(0)
        assert a <= value <= b
        return value


class TestParse:

    @pytest.mark.parametrize("expr,labels", [
        ("d20", ["1d20"]),
        ("2d6+3", ["2d6", "3"]),
        (" 1D8 + 2d6 - 1 ", ["1d8", "2d6", "1"]),
        ("2d20kh1", ["2d20kh1"]),
        ("-1+d4", ["1", "1d4"]),
    ])
    def test_valid(self, expr, labels):
        assert [t.label() for t in parse(expr)] == labels

    @pytest.mark.parametrize("expr", [
        "", "no dice here", "2d6+3xyz", "5", "d1", "2d", "d6++2",
        f"{MAX_DICE + 1}d6", "2d6kh3", "1d6kh0",
    ])
    def test_invalid(self, expr):
        with pytest.raises(ValueError):
            parse(expr)


class TestRoll:

    def test_sum_of_dice_and_modifiers(self):
        result = roll("2d6+3-1", FixedRng(4, 2))
        assert result.total == 8
        assert result.rolls == [4, 2]
        assert result.modifier == 2

    def test_negative_dice_term(self):
        assert roll("d20-d4", FixedRng(10, 3)).total == 7

    def test_keep_highest_and_lowest(self):
        assert roll("2d20kh1", FixedRng(5, 17)).total == 17
        assert roll("2d20kl1", FixedRng(5, 17)).total == 5
        assert roll("4d6kh3", FixedRng(1, 6, 3, 5)).total == 14

    def test_seeded_rng_is_reproducible(self):
        a = roll("3d8+2", random.Random(42))
        b = roll("3d8+2", random.Random(42))
        assert a == b
        assert 5 <= a.total <= 26

    def test_format(self):
        assert format_roll(roll("2d6+3", FixedRng(4, 2))) == "2d6+3: [4, 2] +3 = 9"
        assert format_roll(roll("2d20kh1", FixedRng(5, 17))) == "2d20kh1: [5, 17]→[17] = 17"
