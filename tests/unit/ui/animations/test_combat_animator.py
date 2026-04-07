import pytest
from unittest.mock import MagicMock, patch
from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsRectItem

from core.events import (
    ATTACK_MISSED, COMBAT_ENDED, CONDITION_APPLIED, CONDITION_REMOVED,
    ENTITY_DAMAGED, ENTITY_DIED, ENTITY_HEALED, ROUND_STARTED,
    SPELL_CAST, TURN_STARTED,
)
from core.gameCreation.event_bus import EventBus
from ui.animations.combat_animator import CombatAnimator
from ui.animations.particle_item import ParticleItem


class MockTile(QGraphicsRectItem):
    _tile_size = 40

    def __init__(self, x=0, y=0):
        super().__init__(0, 0, 40, 40)
        self.setPos(x, y)


@pytest.fixture(autouse=True)
def reset_event_bus():
    """Reset EventBus before/after each test to avoid cross-contamination."""
    EventBus.reset()
    yield
    EventBus.reset()


@pytest.fixture
def scene(qapp):
    return QGraphicsScene()


@pytest.fixture
def tile():
    return MockTile(100, 100)


@pytest.fixture
def animator(scene, tile):
    lookup = lambda r, c: tile if (r, c) == (1, 2) else None
    anim = CombatAnimator(scene=scene, tile_lookup=lookup)
    yield anim
    anim.cleanup()


class TestConstructor:
    def test_no_scene_no_crash(self, qapp):
        anim = CombatAnimator(scene=None)
        anim.cleanup()

    def test_subscribes_to_events(self, qapp):
        anim = CombatAnimator(scene=None)
        # Verify subscriptions exist by checking EventBus internals
        for event in CombatAnimator.SUBSCRIBE_EVENTS:
            subs = EventBus._instance._subscribers.get(event, [])
            assert len(subs) > 0, f"Not subscribed to {event}"
        anim.cleanup()


class TestDirectCallMethods:
    def test_on_damage_creates_items(self, animator, scene):
        initial_count = len(scene.items())
        animator.on_damage("goblin", (1, 2), 10)
        assert len(scene.items()) > initial_count

    def test_on_damage_disabled(self, animator, scene):
        animator.set_enabled(False)
        initial_count = len(scene.items())
        animator.on_damage("goblin", (1, 2), 10)
        assert len(scene.items()) == initial_count

    def test_on_damage_no_scene(self, qapp):
        anim = CombatAnimator(scene=None)
        anim.on_damage("goblin", (1, 2), 10)  # Should not raise
        anim.cleanup()

    def test_on_damage_crit(self, animator, scene):
        animator.on_damage("goblin", (1, 2), 20, is_crit=True)
        # Should have items (floating text + particles)
        assert len(scene.items()) > 0

    def test_on_miss_creates_text(self, animator, scene):
        initial_count = len(scene.items())
        animator.on_miss("goblin", (1, 2))
        assert len(scene.items()) > initial_count

    def test_on_heal_creates_items(self, animator, scene):
        initial_count = len(scene.items())
        animator.on_heal("goblin", (1, 2), 5)
        assert len(scene.items()) > initial_count

    def test_on_damage_unknown_tile(self, animator, scene):
        """Tile lookup returns None for unknown position."""
        initial_count = len(scene.items())
        animator.on_damage("goblin", (99, 99), 10)
        assert len(scene.items()) == initial_count


class TestEventBusHandlers:
    def test_entity_damaged_event(self, animator, scene):
        initial_count = len(scene.items())
        EventBus.emit(ENTITY_DAMAGED, {
            "entity_name": "goblin",
            "damage": 8,
            "position": (1, 2),
        })
        assert len(scene.items()) > initial_count

    def test_entity_healed_event(self, animator, scene):
        initial_count = len(scene.items())
        EventBus.emit(ENTITY_HEALED, {
            "entity_name": "fighter",
            "amount": 5,
            "position": (1, 2),
        })
        assert len(scene.items()) > initial_count

    def test_attack_missed_event(self, animator, scene):
        initial_count = len(scene.items())
        EventBus.emit(ATTACK_MISSED, {
            "target": "goblin",
            "position": (1, 2),
        })
        assert len(scene.items()) > initial_count

    def test_spell_cast_event(self, animator, scene):
        initial_count = len(scene.items())
        EventBus.emit(SPELL_CAST, {
            "target": "goblin",
            "position": (1, 2),
        })
        assert len(scene.items()) > initial_count

    def test_entity_died_event(self, animator, scene):
        initial_count = len(scene.items())
        EventBus.emit(ENTITY_DIED, {
            "entity": "goblin",
            "position": (1, 2),
        })
        assert len(scene.items()) > initial_count

    def test_handlers_safe_without_scene(self, qapp):
        anim = CombatAnimator(scene=None)
        # None of these should raise
        EventBus.emit(ENTITY_DAMAGED, {"position": (1, 2), "damage": 5})
        EventBus.emit(ENTITY_HEALED, {"position": (1, 2), "amount": 3})
        EventBus.emit(ATTACK_MISSED, {"position": (1, 2)})
        EventBus.emit(SPELL_CAST, {"position": (1, 2)})
        EventBus.emit(ENTITY_DIED, {"position": (1, 2)})
        anim.cleanup()

    def test_handlers_safe_without_position(self, animator, scene):
        initial_count = len(scene.items())
        EventBus.emit(ENTITY_DAMAGED, {"damage": 5})  # No position
        assert len(scene.items()) == initial_count


class TestConditionHandlers:
    def test_condition_applied_creates_particle(self, animator, scene):
        EventBus.emit(CONDITION_APPLIED, {
            "entity_name": "fighter",
            "condition": "Poisoned",
            "position": (1, 2),
        })
        assert ("fighter", "Poisoned") in animator._status_particles

    def test_condition_removed_stops_particle(self, animator, scene):
        EventBus.emit(CONDITION_APPLIED, {
            "entity_name": "fighter",
            "condition": "Poisoned",
            "position": (1, 2),
        })
        assert ("fighter", "Poisoned") in animator._status_particles

        EventBus.emit(CONDITION_REMOVED, {
            "entity_name": "fighter",
            "condition": "Poisoned",
        })
        assert ("fighter", "Poisoned") not in animator._status_particles

    def test_duplicate_condition_not_doubled(self, animator, scene):
        EventBus.emit(CONDITION_APPLIED, {
            "entity_name": "fighter",
            "condition": "Poisoned",
            "position": (1, 2),
        })
        first_item = animator._status_particles.get(("fighter", "Poisoned"))

        EventBus.emit(CONDITION_APPLIED, {
            "entity_name": "fighter",
            "condition": "Poisoned",
            "position": (1, 2),
        })
        # Should be the same item, not replaced
        assert animator._status_particles[("fighter", "Poisoned")] is first_item

    def test_unknown_condition_ignored(self, animator, scene):
        EventBus.emit(CONDITION_APPLIED, {
            "entity_name": "fighter",
            "condition": "UnknownCondition",
            "position": (1, 2),
        })
        assert len(animator._status_particles) == 0

    def test_condition_removed_unknown_no_crash(self, animator, scene):
        EventBus.emit(CONDITION_REMOVED, {
            "entity_name": "nobody",
            "condition": "Nothing",
        })
        # Should not raise


class TestTurnStarted:
    def test_turn_started_with_position(self, animator, scene):
        EventBus.emit(TURN_STARTED, {
            "entity_name": "fighter",
            "position": (1, 2),
        })
        assert "active_turn" in animator._game_particles

    def test_turn_started_replaces_previous(self, animator, scene):
        EventBus.emit(TURN_STARTED, {
            "entity_name": "fighter",
            "position": (1, 2),
        })
        first = animator._game_particles.get("active_turn")

        EventBus.emit(TURN_STARTED, {
            "entity_name": "rogue",
            "position": (1, 2),
        })
        second = animator._game_particles.get("active_turn")
        assert second is not first


class TestCleanup:
    def test_cleanup_unsubscribes(self, qapp):
        anim = CombatAnimator(scene=None)
        anim.cleanup()
        for event in CombatAnimator.SUBSCRIBE_EVENTS:
            subs = EventBus._instance._subscribers.get(event, [])
            handler = getattr(anim, f"_on_{event}")
            assert handler not in subs

    def test_cleanup_stops_status_particles(self, animator, scene):
        EventBus.emit(CONDITION_APPLIED, {
            "entity_name": "fighter",
            "condition": "Poisoned",
            "position": (1, 2),
        })
        assert len(animator._status_particles) > 0
        animator.cleanup()
        assert len(animator._status_particles) == 0

    def test_cleanup_stops_game_particles(self, animator, scene):
        EventBus.emit(TURN_STARTED, {
            "entity_name": "fighter",
            "position": (1, 2),
        })
        assert len(animator._game_particles) > 0
        animator.cleanup()
        assert len(animator._game_particles) == 0


class TestCombatEnded:
    def test_combat_ended_clears_particles(self, animator, scene):
        EventBus.emit(TURN_STARTED, {
            "entity_name": "fighter",
            "position": (1, 2),
        })
        EventBus.emit(CONDITION_APPLIED, {
            "entity_name": "fighter",
            "condition": "Blessed",
            "position": (1, 2),
        })
        assert len(animator._game_particles) > 0 or len(animator._status_particles) > 0

        EventBus.emit(COMBAT_ENDED, {})
        assert len(animator._game_particles) == 0
        assert len(animator._status_particles) == 0


class TestSetEnabled:
    def test_disabled_blocks_all(self, animator, scene):
        animator.set_enabled(False)
        initial_count = len(scene.items())
        EventBus.emit(ENTITY_DAMAGED, {
            "entity_name": "goblin",
            "damage": 10,
            "position": (1, 2),
        })
        assert len(scene.items()) == initial_count
