"""Tests for CombatInstance."""

from models.combat.combat_instance import CombatInstance, CombatState
from models.combat.combatant import Combatant, CombatantFaction


class FakeEntity:
    def __init__(self, name="Hero", hp=20, max_hp=20):
        self.name = name
        self.hp = hp
        self.max_hp = max_hp


class TestCombatInstance:

    def test_current_combatant_empty(self):
        inst = CombatInstance(instance_id="1", template_id="t", template_name="T")
        assert inst.current_combatant is None

    def test_current_combatant(self):
        c1 = Combatant(entity=FakeEntity("A"), faction=CombatantFaction.PLAYER)
        c2 = Combatant(entity=FakeEntity("B"), faction=CombatantFaction.ENEMY)
        inst = CombatInstance(
            instance_id="1", template_id="t", template_name="T",
            combatants=[c1, c2],
        )
        assert inst.current_combatant is c1

    def test_active_combatants_excludes_unconscious(self):
        c1 = Combatant(entity=FakeEntity("A", hp=10), faction=CombatantFaction.PLAYER)
        c2 = Combatant(entity=FakeEntity("B", hp=0), faction=CombatantFaction.ENEMY)
        inst = CombatInstance(
            instance_id="1", template_id="t", template_name="T",
            combatants=[c1, c2],
        )
        assert len(inst.active_combatants) == 1
        assert inst.active_combatants[0] is c1

    def test_players_and_enemies_filters(self):
        p = Combatant(entity=FakeEntity("Player"), faction=CombatantFaction.PLAYER)
        e = Combatant(entity=FakeEntity("Enemy"), faction=CombatantFaction.ENEMY)
        a = Combatant(entity=FakeEntity("Ally"), faction=CombatantFaction.ALLY)
        inst = CombatInstance(
            instance_id="1", template_id="t", template_name="T",
            combatants=[p, e, a],
        )
        assert len(inst.players) == 1
        assert len(inst.enemies) == 1

    def test_log_event(self):
        inst = CombatInstance(instance_id="1", template_id="t", template_name="T")
        inst.log_event("damage", target="Goblin", amount=5)
        assert len(inst.event_log) == 1
        assert inst.event_log[0]["type"] == "damage"
        assert inst.event_log[0]["target"] == "Goblin"

    def test_to_dict(self):
        inst = CombatInstance(
            instance_id="abc",
            template_id="tmpl",
            template_name="Test",
            round_number=3,
            state=CombatState.ACTIVE,
        )
        data = inst.to_dict()
        assert data["instance_id"] == "abc"
        assert data["state"] == "active"
        assert data["round_number"] == 3

    def test_initial_state_is_setup(self):
        inst = CombatInstance(instance_id="1", template_id="t", template_name="T")
        assert inst.state == CombatState.SETUP
