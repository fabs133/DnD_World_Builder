from core.events import COMBAT_STARTED
from core.logger import app_logger
from models.entities.game_entity import GameEntity
from models.flow.combat_system import CombatSystem
from models.flow.turn_system import TurnSystem
from models.world.world import World
from models.world.world_lore import WorldLore
from models.world.world_tile_manager import WorldTileManager
from core.gameCreation.event_bus import EventBus
from models.flow.action.action import Action

class Gamemaster:
    """
    The Gamemaster class manages the core systems, entities, items, and events in the game.
    """

    def __init__(self):
        """
        Initialize the Gamemaster with default systems and empty collections.
        """
        self.game_entities = []  # List to store Game Entity objects
        self.stat_blocks = {}  # Dictionary to store stat blocks of entities
        self.world_items = []  # List to store items in the world
        self.temp_obstacles = []  # List to store temporary obstacles
        # Store core systems as attributes, using minimal “empty” defaults
        # CombatSystem expects (player, enemy)
        self.combat_system = CombatSystem(None, None)
        # TurnSystem expects a list of entities
        self.turn_system   = TurnSystem([])
        # Provide minimal defaults to World and WorldLore so no __init__ errors
        self.world           = World(
            world_version=1,
            width=1, height=1,
            tile_type="square",
            description="",
            map_data={},
            time_of_day="",
            weather_conditions=""
        )
        self.world_lore      = self.world.lore  # same WorldLore instance
        self.world_tile_manager = self.world.tile_manager
        # Combat encounter management
        self.encounter_templates = {}
        self.encounter_bindings = []
        self.active_combat = None

    def add_entity(self, entity):
        """
        Add an entity to the game.

        :param entity: GameEntity object to add.
        :type entity: GameEntity
        """
        self.game_entities.append(entity)
        self.stat_blocks[entity.name] = entity.stats

    def encounter(self, entity):
        """
        Handle an encounter with an entity.

        :param entity: The entity being encountered.
        :type entity: GameEntity
        """
        app_logger.info(f"Encounter with {entity.name}!")
        # Interaction logic here

    def event(self, description):
        """
        Handle an event in the game.

        :param description: Description of the event.
        :type description: str
        """
        app_logger.info(f"Event: {description}")
        # Event logic here

    def add_item(self, item):
        """
        Add an item to the world.

        :param item: Item object to add.
        :type item: object
        """
        self.world_items.append(item)

    def add_obstacle(self, obstacle):
        """
        Add a temporary obstacle to the world.

        :param obstacle: Obstacle object to add.
        :type obstacle: object
        """
        self.temp_obstacles.append(obstacle)

    def loop_back(self):
        """
        Loop back with sarcastic comments to the party.
        """
        app_logger.info("Oh, you thought you could get away that easily? Think again!")
        # Additional sarcastic comments and logic here

    def register_scene_trigger(self, event_type, condition, cutscene):
        """
        Register a trigger for a scene based on an event type and condition.

        :param event_type: The type of event to subscribe to.
        :type event_type: str
        :param condition: A callable that takes event data and returns True if the cutscene should trigger.
        :type condition: Callable
        :param cutscene: The cutscene function to execute when the condition is met.
        :type cutscene: Callable
        """
        EventBus.subscribe(event_type, lambda data: cutscene(data) if condition(data) else None)

    def register_encounter(self, template, binding=None):
        """Register an encounter template, optionally binding to a location."""
        self.encounter_templates[template.template_id] = template
        if binding:
            self.encounter_bindings.append(binding)

    def start_combat(self, template_id, player_entities):
        """Start combat from a registered template.

        Returns a CombatOrchestrator.
        """
        from models.combat.combat_factory import create_combat_instance
        from models.combat.combat_orchestrator import CombatOrchestrator

        template = self.encounter_templates.get(template_id)
        if template is None:
            raise ValueError(f"No encounter template with id '{template_id}'")

        instance = create_combat_instance(template, player_entities)
        self.active_combat = CombatOrchestrator(instance, self)

        EventBus.emit(COMBAT_STARTED, {
            "instance_id": instance.instance_id,
            "template_name": instance.template_name,
        })

        return self.active_combat

    def end_combat(self):
        """End the active combat encounter."""
        if self.active_combat:
            outcome = self.active_combat.check_end_conditions() or "ended"
            self.active_combat.end_combat(outcome)
            self.active_combat = None