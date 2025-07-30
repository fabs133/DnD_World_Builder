from .world_tile_manager import WorldTileManager
from .world_lore import WorldLore
from models.tiles.tile_data import TileData, TileTag
from core.gameCreation.turn_manager import TurnManager


class World:
    """
    The World class combines tile management with world lore.
    """

    def __init__(self, world_version, width, height, tile_type, description, map_data, time_of_day, weather_conditions):
        """
        Initialize a new World instance.

        :param world_version: Integer version of the world.
        :type world_version: int
        :param width: Width of the world in tiles.
        :type width: int
        :param height: Height of the world in tiles.
        :type height: int
        :param tile_type: The default type of tile for the world.
        :type tile_type: Any
        :param description: Description of the world.
        :type description: str
        :param map_data: Data representing the world map.
        :type map_data: Any
        :param time_of_day: Current time of day in the world.
        :type time_of_day: str
        :param weather_conditions: Current weather conditions in the world.
        :type weather_conditions: str
        """
        self.tile_manager = WorldTileManager(width, height, tile_type)
        self.world_version = world_version
        self.lore = WorldLore(description, map_data, time_of_day, weather_conditions)
        self.turn_manager = TurnManager()

    def place_entity(self, entity, x, y):
        """
        Place an entity at the specified coordinates.

        :param entity: The entity to place.
        :type entity: Any
        :param x: X-coordinate.
        :type x: int
        :param y: Y-coordinate.
        :type y: int
        """
        self.tile_manager.place_entity(entity, x, y)

    def get_entities_at(self, x, y):
        """
        Get all entities at the specified coordinates.

        :param x: X-coordinate.
        :type x: int
        :param y: Y-coordinate.
        :type y: int
        :return: List of entities at the given position.
        :rtype: list
        """
        return self.tile_manager.get_entities_at(x, y)

    def move_entity(self, entity, new_x, new_y):
        """
        Move an entity to a new position.

        :param entity: The entity to move.
        :type entity: Any
        :param new_x: New X-coordinate.
        :type new_x: int
        :param new_y: New Y-coordinate.
        :type new_y: int
        """
        self.tile_manager.move_entity(entity, new_x, new_y)

    def get_adjacent_tiles(self, x, y):
        """
        Get tiles adjacent to the specified coordinates.

        :param x: X-coordinate.
        :type x: int
        :param y: Y-coordinate.
        :type y: int
        :return: List of adjacent tiles.
        :rtype: list
        """
        return self.tile_manager.get_adjacent_tiles(x, y)

    def describe_world(self):
        """
        Get a description of the world.

        :return: Description string.
        :rtype: str
        """
        return self.lore.describe_world()

    def update_weather(self, new_weather):
        """
        Update the world's weather conditions.

        :param new_weather: New weather conditions.
        :type new_weather: str
        """
        self.lore.update_weather(new_weather)

    def update_time_of_day(self, new_time):
        """
        Update the world's time of day.

        :param new_time: New time of day.
        :type new_time: str
        """
        self.lore.update_time_of_day(new_time)

    def save_to_db(self, db_conn):
        """
        Save the world's lore to the database.

        :param db_conn: Database connection object.
        :type db_conn: Any
        """
        self.lore.save_to_db(db_conn)

    def can_see(self, from_pos, to_pos, max_range):
        """
        Determine if an entity at `from_pos` can see a tile at `to_pos`.

        Visibility is blocked if:
        - Manhattan distance > max_range
        - Any intermediate tile has TileTag.BLOCKS_VISION

        :param from_pos: (x, y) tuple of the observer's position.
        :type from_pos: tuple
        :param to_pos: (x, y) tuple of the target position.
        :type to_pos: tuple
        :param max_range: Maximum vision range.
        :type max_range: int
        :return: True if visible, False otherwise.
        :rtype: bool
        """
        dx = to_pos[0] - from_pos[0]
        dy = to_pos[1] - from_pos[1]
        dist = abs(dx) + abs(dy)
        if dist > max_range:
            return False

        # Bresenham‐style line check for blocking tiles
        steps = max(abs(dx), abs(dy))
        for step in range(1, steps):
            # linear interpolation to find intermediate coords
            xt = from_pos[0] + round(dx * step / steps)
            yt = from_pos[1] + round(dy * step / steps)
            tile = self.tile_manager.tiles[(xt, yt)]
            if TileTag.BLOCKS_VISION in tile.tags:
                return False

        return True
