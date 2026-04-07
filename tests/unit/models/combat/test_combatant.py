"""Tests for Combatant."""

from models.combat.combatant import Combatant, CombatantFaction


class FakeEntity:
    def __init__(self, name="Hero", hp=20, max_hp=20, speed=30):
        self.name = name
        self.hp = hp
        self.max_hp = max_hp
        self.speed = speed


class TestCombatant:

    def test_reset_turn_restores_resources(self):
        entity = FakeEntity(speed=30)
        c = Combatant(entity=entity, faction=CombatantFaction.PLAYER)
        c.movement_remaining = 0
        c.action_used = True
        c.bonus_action_used = True
        c.reaction_used = True

        c.reset_turn()

        assert c.movement_remaining == 30
        assert c.action_used is False
        assert c.bonus_action_used is False
        assert c.reaction_used is False

    def test_health_category_healthy(self):
        c = Combatant(entity=FakeEntity(hp=20, max_hp=20), faction=CombatantFaction.PLAYER)
        assert c.health_category == "healthy"

    def test_health_category_wounded(self):
        c = Combatant(entity=FakeEntity(hp=12, max_hp=20), faction=CombatantFaction.PLAYER)
        assert c.health_category == "wounded"

    def test_health_category_bloodied(self):
        c = Combatant(entity=FakeEntity(hp=6, max_hp=20), faction=CombatantFaction.PLAYER)
        assert c.health_category == "bloodied"

    def test_health_category_near_death(self):
        c = Combatant(entity=FakeEntity(hp=2, max_hp=20), faction=CombatantFaction.PLAYER)
        assert c.health_category == "near_death"

    def test_health_category_unconscious(self):
        c = Combatant(entity=FakeEntity(hp=0, max_hp=20), faction=CombatantFaction.PLAYER)
        assert c.health_category == "unconscious"

    def test_health_category_unknown(self):
        c = Combatant(entity=FakeEntity(hp=0, max_hp=0), faction=CombatantFaction.ENEMY)
        assert c.health_category == "unknown"

    def test_is_conscious_true(self):
        c = Combatant(entity=FakeEntity(hp=5), faction=CombatantFaction.PLAYER)
        assert c.is_conscious is True

    def test_is_conscious_false(self):
        c = Combatant(entity=FakeEntity(hp=0), faction=CombatantFaction.PLAYER)
        assert c.is_conscious is False

    def test_name_from_entity(self):
        c = Combatant(entity=FakeEntity(name="Gandalf"), faction=CombatantFaction.ALLY)
        assert c.name == "Gandalf"

    def test_to_dict(self):
        c = Combatant(
            entity=FakeEntity(name="Hero"),
            faction=CombatantFaction.PLAYER,
            initiative=15,
            position=(2, 3),
        )
        data = c.to_dict()
        assert data["entity_name"] == "Hero"
        assert data["faction"] == "player"
        assert data["initiative"] == 15
        assert data["position"] == [2, 3]
