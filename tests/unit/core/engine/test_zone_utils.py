"""Tests for encounter-zone utilities."""

from __future__ import annotations

import pytest
from types import SimpleNamespace

from core.engine.zone_utils import (
    build_zone_map,
    has_any_zones,
    get_zone_at,
    zone_positions,
    entities_in_zone,
    nearby_combatants,
)


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _tile(pos, zone_id=None, user_label=None):
    """Return a minimal tile dict."""
    d = {"position": list(pos)}
    if zone_id is not None:
        d["zone_id"] = zone_id
    if user_label is not None:
        d["user_label"] = user_label
    return d


def _entity(name, pos, entity_type="enemy"):
    return SimpleNamespace(name=name, position=pos, entity_type=entity_type, hp=10)


# ------------------------------------------------------------------ #
# build_zone_map
# ------------------------------------------------------------------ #

class TestBuildZoneMap:

    def test_zone_id_takes_precedence(self):
        tiles = [_tile((0, 0), zone_id="Throne", user_label="Hall")]
        zm = build_zone_map(tiles)
        assert zm[(0, 0)] == "Throne"

    def test_falls_back_to_user_label(self):
        tiles = [_tile((1, 2), user_label="Guard Post")]
        zm = build_zone_map(tiles)
        assert zm[(1, 2)] == "Guard Post"

    def test_no_zone_maps_to_none(self):
        tiles = [_tile((3, 3))]
        zm = build_zone_map(tiles)
        assert zm[(3, 3)] is None

    def test_multiple_tiles(self):
        tiles = [
            _tile((0, 0), zone_id="A"),
            _tile((0, 1), zone_id="A"),
            _tile((5, 5), zone_id="B"),
            _tile((9, 9)),
        ]
        zm = build_zone_map(tiles)
        assert zm[(0, 0)] == "A"
        assert zm[(0, 1)] == "A"
        assert zm[(5, 5)] == "B"
        assert zm[(9, 9)] is None


# ------------------------------------------------------------------ #
# has_any_zones
# ------------------------------------------------------------------ #

class TestHasAnyZones:

    def test_true_when_zones_present(self):
        zm = {(0, 0): "Guard Post", (1, 1): None}
        assert has_any_zones(zm) is True

    def test_false_when_all_none(self):
        zm = {(0, 0): None, (1, 1): None}
        assert has_any_zones(zm) is False

    def test_empty_map(self):
        assert has_any_zones({}) is False


# ------------------------------------------------------------------ #
# get_zone_at
# ------------------------------------------------------------------ #

class TestGetZoneAt:

    def test_returns_zone(self):
        zm = {(2, 3): "Main Hall"}
        assert get_zone_at(zm, (2, 3)) == "Main Hall"

    def test_returns_none_for_missing(self):
        zm = {(0, 0): "A"}
        assert get_zone_at(zm, (99, 99)) is None

    def test_returns_none_for_unzoned(self):
        zm = {(0, 0): None}
        assert get_zone_at(zm, (0, 0)) is None


# ------------------------------------------------------------------ #
# zone_positions
# ------------------------------------------------------------------ #

class TestZonePositions:

    def test_collects_matching_positions(self):
        zm = {(0, 0): "Guard Post", (0, 1): "Guard Post", (5, 5): "Hall"}
        result = zone_positions(zm, "Guard Post")
        assert result == frozenset({(0, 0), (0, 1)})

    def test_case_insensitive(self):
        zm = {(0, 0): "Guard Post"}
        assert (0, 0) in zone_positions(zm, "guard post")
        assert (0, 0) in zone_positions(zm, "GUARD POST")

    def test_empty_for_unknown_zone(self):
        zm = {(0, 0): "A"}
        assert zone_positions(zm, "B") == frozenset()


# ------------------------------------------------------------------ #
# entities_in_zone
# ------------------------------------------------------------------ #

class TestEntitiesInZone:

    def test_filters_by_zone(self):
        zm = {(0, 0): "A", (5, 5): "B"}
        entities = [_entity("Wolf", (0, 0)), _entity("Spider", (5, 5))]
        result = entities_in_zone(entities, zm, "A")
        assert len(result) == 1
        assert result[0].name == "Wolf"

    def test_excludes_entities_without_position(self):
        zm = {(0, 0): "A"}
        e = SimpleNamespace(name="Ghost", position=None, entity_type="enemy")
        result = entities_in_zone([e], zm, "A")
        assert len(result) == 0

    def test_excludes_entities_on_unzoned_tiles(self):
        zm = {(0, 0): None}
        entities = [_entity("Wolf", (0, 0))]
        result = entities_in_zone(entities, zm, "A")
        assert len(result) == 0

    def test_case_insensitive(self):
        zm = {(0, 0): "Guard Post"}
        entities = [_entity("Wolf", (0, 0))]
        assert len(entities_in_zone(entities, zm, "guard post")) == 1
        assert len(entities_in_zone(entities, zm, "GUARD POST")) == 1

    def test_multiple_entities_same_zone(self):
        zm = {(0, 0): "A", (0, 1): "A", (5, 5): "B"}
        entities = [
            _entity("Wolf 1", (0, 0)),
            _entity("Wolf 2", (0, 1)),
            _entity("Spider", (5, 5)),
        ]
        result = entities_in_zone(entities, zm, "A")
        assert len(result) == 2
        names = {e.name for e in result}
        assert names == {"Wolf 1", "Wolf 2"}


# ------------------------------------------------------------------ #
# nearby_combatants
# ------------------------------------------------------------------ #

class TestNearbyCombatants:

    def test_radius_filter(self):
        entities = [
            _entity("Near", (3, 3)),
            _entity("Far", (20, 20)),
        ]
        result = nearby_combatants(entities, (3, 4), radius=3)
        assert len(result) == 1
        assert result[0].name == "Near"

    def test_players_always_included(self):
        entities = [
            _entity("Fighter", (99, 99), entity_type="player"),
            _entity("Wolf", (3, 3)),
        ]
        result = nearby_combatants(entities, (3, 4), radius=3)
        names = {e.name for e in result}
        assert "Fighter" in names
        assert "Wolf" in names

    def test_no_position_excluded(self):
        e = SimpleNamespace(name="Ghost", position=None, entity_type="enemy", hp=5)
        result = nearby_combatants([e], (0, 0), radius=10)
        assert len(result) == 0

    def test_chebyshev_distance(self):
        # Chebyshev: max(|dx|, |dy|). (5,5) to (3,3) = max(2,2) = 2
        entities = [_entity("Diagonal", (5, 5))]
        assert len(nearby_combatants(entities, (3, 3), radius=2)) == 1
        assert len(nearby_combatants(entities, (3, 3), radius=1)) == 0
