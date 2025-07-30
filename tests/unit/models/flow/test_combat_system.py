import pytest
from models.flow.combat_system import CombatSystem

def test_player_victory(capsys):
    # Enemy stub: starts at 5 HP, should never get its turn
    class EnemyStub:
        def __init__(self):
            self.name = "Ogre"
            self.hp = 5
        def take_turn(self):
            pytest.fail("Enemy.take_turn should not be called after death")

    enemy = EnemyStub()

    # Player stub: on first turn, reduces enemy to 0
    class PlayerStub:
        def __init__(self):
            self.name = "Hero"
            # character with hp > 0
            self.character = type("C", (), {"name": "Hero", "hp": 10})()
        def take_turn(self):
            enemy.hp = 0

    player = PlayerStub()

    cs = CombatSystem(player, enemy)
    cs.start_combat()

    out = capsys.readouterr().out.splitlines()
    # 1) combat begins
    assert out[0] == "Combat begins between Hero and Ogre!"
    # 2) round 1
    assert out[1] == "Round 1"
    # 3) ogre defeated
    assert out[2] == "Ogre is defeated!"
    # 4) combat ends
    assert out[3] == "Combat ends."

def test_enemy_victory(capsys):
    # Player stub: does nothing on its turn
    class PlayerStub:
        def __init__(self):
            self.name = "Hero"
            self.character = type("C", (), {"name": "Hero", "hp": 3})()
        def take_turn(self):
            pass

    player = PlayerStub()

    # Enemy stub: kills player on its turn
    class EnemyStub:
        def __init__(self):
            self.name = "Goblin"
            self.hp = 10
        def take_turn(self):
            player.character.hp = 0

    enemy = EnemyStub()

    cs = CombatSystem(player, enemy)
    cs.start_combat()

    out = capsys.readouterr().out.splitlines()
    assert out[0] == "Combat begins between Hero and Goblin!"
    assert out[1] == "Round 1"
    # hero defeated
    assert out[2] == "Hero is defeated!"
    assert out[3] == "Combat ends."

def test_fight_multiple_rounds(capsys):
    # Test that combat_round increments properly
    logs = []
    class PlayerStub:
        def __init__(self):
            self.name = "P"
            self.character = type("C", (), {"name": "P", "hp": 6})()
            self._turns = 0
        def take_turn(self):
            # deal 1 damage per turn, so takes 3 rounds to kill 4-HP enemy
            self._turns += 1
            enemy.hp -= 1

    player = PlayerStub()
    class EnemyStub:
        def __init__(self):
            self.name = "E"
            self.hp = 3
            self._turns = 0
        def take_turn(self):
            # deal 2 damage per turn, won't kill P too soon
            self._turns += 1
            player.character.hp -= 2

    enemy = EnemyStub()
    cs = CombatSystem(player, enemy)
    cs.start_combat()

    out = capsys.readouterr().out
    # Expect lines:
    # Combat begins...
    # Round 1
    # Round 2
    # Round 3
    # E is defeated!
    # Combat ends.
    assert "Round 1" in out
    assert "Round 2" in out
    assert "Round 3" in out
    assert "E is defeated!" in out
    assert out.strip().endswith("Combat ends.")
