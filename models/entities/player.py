from models.entities.game_entity import GameEntity

class Player(GameEntity):
    """
    Represents a player in the game.

    Inherits from :class:`GameEntity` and manages player-specific data and actions.
    """

    def __init__(self, character, db_conn, player_id):
        """
        Initialize a Player instance.

        :param character: Character object associated with the player.
        :type character: Character
        :param db_conn: Database connection object.
        :type db_conn: sqlite3.Connection
        :param player_id: Unique identifier for the player.
        :type player_id: int
        """
        super().__init__(character.name, "player")
        self.character = character  # Character object
        self.db_conn = db_conn # Database-related connection
        self.player_id = player_id # Integer: Unique identifier for the player
        self.position = (0, 0)  # (x, y) position on the map

    def take_turn(self):
        """
        Stub for the per-turn loop.

        You’ll want to hook this into your UI or CLI.

        :raises NotImplementedError: Always, as this should be implemented by the game loop or UI.
        """
        raise NotImplementedError("take_turn must be driven by your game loop or UI")

    def move(self, direction: str):
        """
        Move the player north, south, east, or west by one tile and persist the new position to the database.

        :param direction: Direction to move ('north', 'south', 'east', 'west').
        :type direction: str
        :return: The new position as a tuple (x, y).
        :rtype: tuple
        """
        dirs = {
            "north": (0,  1),
            "south": (0, -1),
            "east":  (1,  0),
            "west":  (-1, 0),
        }
        dx, dy = dirs.get(direction.lower(), (0, 0))
        x, y = self.position
        new_pos = (x + dx, y + dy)
        self.position = new_pos

        # Persist new position—make sure you’ve created a `players` table with x,y columns!
        cur = self.db_conn.cursor()
        cur.execute("""
            UPDATE players
               SET x = ?, y = ?
             WHERE player_id = ?
        """, (new_pos[0], new_pos[1], self.player_id))
        self.db_conn.commit()
        return new_pos

    def attack(self, target):
        """
        Perform a simple STR-based attack against a target and log the result in the combat log.

        :param target: The entity being attacked. Must have `armor_class` and `take_damage()` attributes.
        :type target: object
        :return: Tuple indicating if the attack hit and the damage dealt (hit: bool, damage: int).
        :rtype: tuple
        """
        import random

        str_mod = self.character.stats.get("str", 0)
        roll = random.randint(1, 20) + str_mod
        ac   = getattr(target, "armor_class", 0)
        hit  = roll >= ac

        damage = 0
        if hit:
            damage = max(1, str_mod)
            target.take_damage(damage)

        # record in combat_log (turn_number left to your game loop)
        cur = self.db_conn.cursor()
        cur.execute("""
            INSERT INTO combat_log
                (turn_number, attacker_id, target_id, damage_dealt, spell_used, ability_used)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            None,                   # fill in current turn from the engine
            self.player_id,
            getattr(target, "player_id", None) or getattr(target, "character_id", None),
            damage,
            None,                   # no spell used
            None                    # no special ability
        ))
        self.db_conn.commit()
        return hit, damage

    def cast_spell(self, spell_name, target):
        """
        Cast a spell using the associated Character's `cast_spell` method.

        :param spell_name: Name of the spell to cast.
        :type spell_name: str
        :param target: The target of the spell.
        :type target: object
        :return: Result of the Character's `cast_spell` method.
        """
        return self.character.cast_spell(spell_name, target)

    def investigate(self, location):
        """
        Perform a Wisdom-based investigation check (d20 + WIS modifier).

        :param location: The location or object being investigated.
        :type location: object
        :return: The total roll (d20 + WIS modifier).
        :rtype: int
        """
        import random
        wis_mod = self.character.stats.get("wis", 0)
        roll = random.randint(1, 20) + wis_mod
        # Here you’d compare to a DC based on `location` data
        return roll

    def interact(self, obj):
        """
        Interact with an object if it has an `interact(player)` method.

        :param obj: The object to interact with.
        :type obj: object
        :return: The result of the object's `interact` method, or None if not available.
        """
        if hasattr(obj, "interact"):
            return obj.interact(self)
        return None