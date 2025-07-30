from models.tiles.tile_data import TileData

class WorldTileManager:
    """
    Manages the tiles and entities in the world grid.
    """

    def __init__(self, width, height, tile_type):
        """
        Initialize the WorldTileManager.

        :param width: Width of the world grid.
        :type width: int
        :param height: Height of the world grid.
        :type height: int
        :param tile_type: Type of tiles ("square" or "hex").
        :type tile_type: str
        """
        self.width  = width
        self.height = height
        self.tile_type = tile_type
        self.tiles  = self.generate_tiles()
        self.entities = {}   # maps (x,y) → list of GameEntity

    def place_entity(self, entity, x, y):
        """
        Place an entity at the specified tile.

        :param entity: The entity to place.
        :type entity: GameEntity
        :param x: X-coordinate of the tile.
        :type x: int
        :param y: Y-coordinate of the tile.
        :type y: int
        :raises ValueError: If the tile is invalid.
        """
        if not self.is_valid_tile(x, y):
            raise ValueError(f"Cannot place {entity.name} at invalid tile ({x},{y})")
        entity.position = (x, y)
        self.entities.setdefault((x, y), []).append(entity)
        print(f"Placed {entity.name} at {entity.position}")

    def get_entities_at(self, x, y):
        """
        Get a list of entities at the specified tile.

        :param x: X-coordinate of the tile.
        :type x: int
        :param y: Y-coordinate of the tile.
        :type y: int
        :return: List of entities at the tile.
        :rtype: list
        """
        return list(self.entities.get((x, y), []))

    def generate_tiles(self):
        """
        Generate the tiles for the world grid.

        :return: Dictionary mapping (x, y) to TileData.
        :rtype: dict
        """
        tiles = {}
        for x in range(self.width):
            for y in range(self.height):
                td = TileData(position=(x, y))
                tiles[(x, y)] = td
        return tiles

    def get_adjacent_tiles(self, x, y):
        """
        Get adjacent tiles based on the tile_type ("square" or "hex").

        :param x: X-coordinate of the tile.
        :type x: int
        :param y: Y-coordinate of the tile.
        :type y: int
        :return: List of adjacent tile coordinates.
        :rtype: list
        """
        if self.tile_type == "square":
            adjacent_tiles = [
                (x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y)
            ]
        elif self.tile_type == "hex":
            adjacent_tiles = [
                (x + 1, y), (x - 1, y), (x, y - 1), (x, y + 1), 
                (x - 1, y + 1), (x + 1, y - 1)
            ]
        return [tile for tile in adjacent_tiles if self.is_valid_tile(tile[0], tile[1])]

    def is_valid_tile(self, x, y):
        """
        Check if a tile is within the grid boundaries.

        :param x: X-coordinate of the tile.
        :type x: int
        :param y: Y-coordinate of the tile.
        :type y: int
        :return: True if the tile is valid, False otherwise.
        :rtype: bool
        """
        return 0 <= x < self.width and 0 <= y < self.height

    def move_entity(self, entity, new_x, new_y):
        """
        Move an entity to a new tile if the tile is valid.

        :param entity: The entity to move.
        :type entity: GameEntity
        :param new_x: New X-coordinate.
        :type new_x: int
        :param new_y: New Y-coordinate.
        :type new_y: int
        """
        if self.is_valid_tile(new_x, new_y):
            entity.position = (new_x, new_y)
            print(f"{entity.name} moved to tile ({new_x}, {new_y})")
        else:
            print(f"Invalid move for {entity.name}.")

    def display_world(self):
        """
        Display a simple debug view of the world grid.
        """
        for y in range(self.height):
            row = "".join("[ ]" for x in range(self.width))
            print(row)