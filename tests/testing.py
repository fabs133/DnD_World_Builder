import random

### UTILITIES ###

def roll(dice_str):
    """Roll dice like '2d6'."""
    num, die = map(int, dice_str.lower().split('d'))
    return sum(random.randint(1, die) for _ in range(num))


### EVENT BUS ###

class EventBus:
    listeners = {}

    @classmethod
    def on(cls, event_name, callback):
        cls.listeners.setdefault(event_name, []).append(callback)

    @classmethod
    def emit(cls, event_name, data):
        print(f"[EventBus] Event emitted: {event_name}")
        for callback in cls.listeners.get(event_name, []):
            callback(data)


### REACTION QUEUE ###

class ReactionQueue:
    _queue = []

    @classmethod
    def add(cls, reaction):
        cls._queue.append(reaction)
        print(f"[ReactionQueue] Queued reaction: {reaction}")

    @classmethod
    def blocked(cls):
        return bool(cls._queue)

    @classmethod
    def resolve(cls):
        print("[ReactionQueue] Resolving reactions...")
        while cls._queue:
            reaction = cls._queue.pop(0)
            reaction.resolve()
        print("[ReactionQueue] Done.")


### BASE CLASSES ###

class GameEntity:
    def __init__(self, name, hp):
        self.name = name
        self.hp = hp

    def take_damage(self, amount, damage_type=None):
        self.hp -= amount
        print(f"{self.name} takes {amount} {damage_type or ''} damage. [HP: {self.hp}]")

    def __str__(self):
        return f"{self.name}(HP={self.hp})"


class GameState:
    def __init__(self):
        self.entities = []


### ACTIONS ###

class Action:
    def __init__(self, actor):
        self.actor = actor

    def validate(self, game_state):
        return True  # Stub

    def execute(self, game_state):
        raise NotImplementedError


class SpellAction(Action):
    def __init__(self, caster, spell_name, damage_dice, targets):
        super().__init__(caster)
        self.spell_name = spell_name
        self.damage_dice = damage_dice
        self.targets = targets

    def validate(self, game_state):
        # Could check range, line of sight, etc.
        return True

    def execute(self, game_state):
        print(f"{self.actor.name} casts {self.spell_name}!")
        for target in self.targets:
            dmg = roll(self.damage_dice)
            target.take_damage(dmg, damage_type="arcane")


### REACTIONS ###

class CounterspellReaction:
    def __init__(self, reactor, target_action):
        self.reactor = reactor
        self.target_action = target_action

    def resolve(self):
        # Simulated chance to counterspell
        success = random.random() < 0.7
        if success:
            print(f"{self.reactor.name} counterspells {self.target_action.spell_name}!")
            self.target_action.execute = lambda *_: print(f"{self.target_action.spell_name} was countered!")
        else:
            print(f"{self.reactor.name} fails to counterspell.")


### VALIDATOR ###

class ActionValidator:
    @staticmethod
    def validate(action, game_state=None):
        try:
            return action.validate(game_state)
        except Exception as e:
            print(f"[Validator] Invalid: {e}")
            return False


### TURN SYSTEM ###

class TurnSystem:
    def __init__(self, entities):
        self.entities = entities
        self.current = 0

    def run_turn(self, game_state):
        actor = self.entities[self.current]
        print(f"\n-- {actor.name}'s turn --")

        action = actor.decide_action(game_state)
        if ActionValidator.validate(action, game_state):
            EventBus.emit("ACTION_PROPOSED", action)

        if not ReactionQueue.blocked():
            action.execute(game_state)
            EventBus.emit("ACTION_EXECUTED", action)
        else:
            ReactionQueue.resolve()

        self.current = (self.current + 1) % len(self.entities)


### SAMPLE ENTITIES W/ AI ###

class Wizard(GameEntity):
    def decide_action(self, game_state):
        target = next(e for e in game_state.entities if e != self)
        return SpellAction(self, "Magic Missile", "2d6", [target])


class Countermage(GameEntity):
    def __init__(self, name, hp):
        super().__init__(name, hp)
        EventBus.on("ACTION_PROPOSED", self.maybe_counterspell)

    def decide_action(self, game_state):
        target = next(e for e in game_state.entities if e != self)
        return SpellAction(self, "Magic Missile", "2d6", [target])

    def maybe_counterspell(self, action):
        if isinstance(action, SpellAction):
            ReactionQueue.add(CounterspellReaction(self, action))


### RUNNING IT ###

def main():
    alice = Wizard("Alice", 20)
    bob = Countermage("Bob", 20)

    game_state = GameState()
    game_state.entities = [alice, bob]

    ts = TurnSystem(game_state.entities)

    for _ in range(2):
        ts.run_turn(game_state)


if __name__ == "__main__":
    main()
