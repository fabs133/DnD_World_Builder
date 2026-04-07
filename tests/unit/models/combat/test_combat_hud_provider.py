"""Tests for CombatHUDProvider."""

from models.combat.combat_hud_provider import CombatHUDProvider
from models.combat.combatant import Combatant, CombatantFaction
from models.combat.combat_instance import CombatInstance, CombatState


class FakeEntity:
    def __init__(self, name="Hero", hp=20, max_hp=20, armor_class=16, speed=30):
        self.name = name
        self.hp = hp
        self.max_hp = max_hp
        self.armor_class = armor_class
        self.speed = speed


class TestInitiativeDisplay:

    def test_dm_sees_exact_hp(self):
        c = Combatant(entity=FakeEntity("Hero", hp=15, max_hp=20), faction=CombatantFaction.PLAYER)
        entries = CombatHUDProvider.get_initiative_display([c], "dm", current_turn_index=0)
        assert entries[0]["hp"] == 15
        assert entries[0]["hp_max"] == 20

    def test_player_sees_health_category(self):
        c = Combatant(entity=FakeEntity("Goblin", hp=3, max_hp=10), faction=CombatantFaction.ENEMY)
        entries = CombatHUDProvider.get_initiative_display([c], "player", current_turn_index=0)
        assert "hp" not in entries[0]
        assert entries[0]["health_category"] == "bloodied"

    def test_player_sees_is_you_flag(self):
        c = Combatant(entity=FakeEntity("Hero"), faction=CombatantFaction.PLAYER)
        entries = CombatHUDProvider.get_initiative_display(
            [c], "player", viewer_entity_name="Hero", current_turn_index=0
        )
        assert entries[0]["is_you"] is True

    def test_current_turn_flagged(self):
        c1 = Combatant(entity=FakeEntity("A"), faction=CombatantFaction.PLAYER)
        c2 = Combatant(entity=FakeEntity("B"), faction=CombatantFaction.ENEMY)
        entries = CombatHUDProvider.get_initiative_display([c1, c2], "dm", current_turn_index=1)
        assert entries[0]["is_current_turn"] is False
        assert entries[1]["is_current_turn"] is True


class TestActionBar:

    def test_all_available_on_fresh_turn(self):
        c = Combatant(entity=FakeEntity(speed=30), faction=CombatantFaction.PLAYER)
        c.reset_turn()
        inst = CombatInstance(instance_id="1", template_id="t", template_name="T")

        bar = CombatHUDProvider.get_action_bar(c, inst)
        assert bar["movement_remaining"] == 30
        assert len(bar["actions"]) >= 5
        assert bar["reaction_available"] is True

    def test_action_disabled_after_use(self):
        c = Combatant(entity=FakeEntity(), faction=CombatantFaction.PLAYER)
        c.action_used = True
        inst = CombatInstance(instance_id="1", template_id="t", template_name="T")

        bar = CombatHUDProvider.get_action_bar(c, inst)
        assert len(bar["actions"]) == 0


class TestEnemyStatBlock:

    def test_dm_fields(self):
        c = Combatant(
            entity=FakeEntity("Goblin", hp=7, max_hp=7, armor_class=13, speed=30),
            faction=CombatantFaction.ENEMY,
        )
        block = CombatHUDProvider.get_enemy_stat_block(c)
        assert block["name"] == "Goblin"
        assert block["ac"] == 13
        assert block["hp"] == 7
        assert block["speed"] == 30


class TestCombatSummary:

    def test_summary_correct(self):
        c1 = Combatant(entity=FakeEntity("Hero", hp=10), faction=CombatantFaction.PLAYER)
        c2 = Combatant(entity=FakeEntity("Goblin", hp=0), faction=CombatantFaction.ENEMY)
        inst = CombatInstance(
            instance_id="1", template_id="t", template_name="T",
            combatants=[c1, c2], round_number=3, state=CombatState.ACTIVE,
        )

        summary = CombatHUDProvider.get_combat_summary(inst)
        assert summary["round_number"] == 3
        assert summary["total_combatants"] == 2
        assert summary["active_combatants"] == 1
        assert summary["state"] == "active"
