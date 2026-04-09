"""Play Session dialog — the playable game experience.

Manages the full play lifecycle: intro -> exploration -> combat -> exploration.
Supports Player, DM, and Spectator roles with info filtering.

Game logic is delegated to three controllers:
- CombatTurnController  — turn loop, initiative, session lifecycle
- ExplorationController  — exploration actions, NPC interaction
- CombatActionHandler    — player combat action routing
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QSplitter, QWidget, QFrame, QStackedWidget, QCheckBox,
    QMainWindow, QDockWidget,
)
from PyQt5.QtCore import Qt, QTimer, QSettings
from PyQt5.QtGui import QFont

from core.engine.play_state import PlayState, PlayerRole
from core.engine.info_filter import InfoFilter
from core.engine.ui_adapter import UIInputAdapter
from core.engine.play_session import (
    PlaySessionRunner, PlayConfig, extract_entities_from_tiles, default_test_party,
)
from core.engine.entity_utils import filter_combatants
from models.entities.entity_type import EntityType
from core.engine.ai.heuristic_adapter import HeuristicAIAdapter
from ui.combat.action_bar_panel import ActionBarPanel
from ui.exploration.exploration_bar_panel import ExplorationBarPanel
from ui.panels.party_status_strip import PartyStatusStrip
from ui.combat.play_map_widget import PlayMapScene
from ui.panels.initiative_panel import InitiativePanel
from ui.widgets.intro_screen import ScenarioIntroWidget

from ui.map_view import MapView

from ui.dialogs.combat_turn_controller import CombatTurnController
from ui.dialogs.exploration_controller import ExplorationController
from ui.dialogs.combat_action_handler import CombatActionHandler


class _DockSectionAdapter:
    """Adapts QDockWidget to the CollapsibleSection interface
    expected by CombatTurnController and ExplorationController."""

    def __init__(self, dock: QDockWidget):
        self._dock = dock

    def setVisible(self, v: bool):
        self._dock.setVisible(v)

    def set_open(self, v: bool):
        self._dock.setVisible(v)
        if v:
            self._dock.raise_()

    def set_title(self, title: str):
        self._dock.setWindowTitle(title)


class PlaySessionDialog(QDialog):
    """Full-screen play dialog with state machine lifecycle.

    States: INTRO -> EXPLORATION -> COMBAT -> (EXPLORATION | ENDED)
    """

    def __init__(self, tile_dicts: list[dict],
                 scenario_name: str = "Scenario",
                 role: PlayerRole = PlayerRole.PLAYER,
                 selected_character=None,
                 meta: dict | None = None,
                 quests: list[dict] | None = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.Window | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.ApplicationModal)
        self._tile_dicts = tile_dicts
        self._tile_by_pos: dict[tuple[int, int], dict] = {}
        for td in tile_dicts:
            pos = tuple(td.get("position", [0, 0]))
            self._tile_by_pos[pos] = td
        self._quests = quests or []
        self._role = role
        self._selected_character = selected_character
        self._meta = meta or {}
        self._play_state = PlayState.SETUP
        self._runner: PlaySessionRunner | None = None
        self._ui_adapter: UIInputAdapter | None = None
        self._is_running = False
        self._animator = None
        self._current_state = None
        self._combat_cooldown = False
        self._current_tile_pos: tuple[int, int] | None = None
        self._combat_scene: "PlayMapScene | None" = None
        self._combat_map_view = None
        self._world_positions: dict[str, tuple] = {}
        self._combat_overlay = None
        self._pending_spell = None

        # Extract entities once — they persist across exploration and combat
        self._all_entities, self._start_position = extract_entities_from_tiles(tile_dicts)

        # Zone map for encounter scoping
        from core.engine.zone_utils import (
            build_zone_map, get_zone_at, entities_in_zone,
            has_any_zones, nearby_combatants,
        )
        self._zone_map = build_zone_map(tile_dicts)
        self._current_zone: str | None = get_zone_at(self._zone_map, self._start_position)
        self._cleared_zones: set[str] = set()

        # Spawn default party if no players
        players = [e for e in self._all_entities if e.entity_type == "player"]
        if not players:
            from models.entities.game_entity import GameEntity
            for pdict in default_test_party():
                pe = GameEntity.from_dict(pdict)
                pe.position = self._start_position
                self._all_entities.append(pe)

        # Build info filter
        party = frozenset(
            e.name for e in self._all_entities if e.entity_type == "player"
        )
        char_name = getattr(selected_character, "name", None) if selected_character else None
        self._info_filter = InfoFilter(role, char_name, party)

        self.setWindowTitle(f"Play Session — {scenario_name}")
        self.setMinimumSize(900, 550)
        self._build_ui(scenario_name)

        # Transition engine for animated mode switches
        from ui.transitions.transition_engine import TransitionEngine
        from core.audio.ui_sound_manager import UISoundManager
        self._transition_engine = TransitionEngine(
            parent_widget=self,
            sound_manager=UISoundManager.instance(),
        )

        # ── Create controllers ──
        self._turn_ctrl = CombatTurnController(
            get_play_state=lambda: self._play_state,
            set_play_state=self._set_play_state,
            get_runner=lambda: self._runner,
            get_ui_adapter=lambda: self._ui_adapter,
            get_is_running=lambda: self._is_running,
            set_is_running=self._set_is_running,
            get_combat_scene=lambda: self._combat_scene,
            get_mini_map_scene=lambda: self._mini_map_scene,
            get_map_scene=lambda: self._map_scene,
            get_animator=lambda: self._animator,
            set_animator=self._set_animator,
            get_info_filter=lambda: self._info_filter,
            turn_label=self._turn_label,
            log=self._log,
            action_bar=self._action_bar,
            move_btn=self._move_btn,
            initiative_panel=self._initiative_panel,
            initiative_section=self._initiative_section,
            on_enter_exploration=self._enter_exploration,
            on_advance_turns_ready=None,
            on_combat_finished=self._on_session_ended,
            get_combat_map_view=lambda: getattr(self, '_combat_map_view', None),
            run_transition=self._run_transition,
            get_choreographer=lambda: getattr(self, '_choreographer', None),
            encounter_strip=None,  # Set after strip is created
        )

        # Wire encounter strip <-> turn controller (bidirectional)
        self._turn_ctrl._encounter_strip = self._encounter_strip
        self._encounter_strip._turn_controller = self._turn_ctrl

        # Action choreographer for multi-phase combat animations
        from ui.animations.action_choreographer import ActionChoreographer
        self._choreographer = ActionChoreographer()

        self._explore_ctrl = ExplorationController(
            get_play_state=lambda: self._play_state,
            role=self._role,
            get_all_entities=lambda: self._all_entities,
            tile_dicts=self._tile_dicts,
            zone_map=self._zone_map,
            get_current_zone=lambda: self._current_zone,
            set_current_zone=self._set_current_zone,
            cleared_zones=self._cleared_zones,
            get_current_tile_pos=lambda: self._current_tile_pos,
            set_current_tile_pos=lambda pos: setattr(self, '_current_tile_pos', pos),
            selected_character=self._selected_character,
            info_filter=self._info_filter,
            turn_label=self._turn_label,
            log=self._log,
            log_section=self._log_section,
            zone_detail=self._zone_detail,
            map_scene=self._map_scene,
            mini_map_scene=self._mini_map_scene,
            party_strip=self._party_strip,
            find_entity=self._find_entity,
            enter_combat=self._enter_combat,
            load_tile_at=self._load_tile_at,
            refit_maps=self._refit_map_views,
        )

        # Wire side-event panel actions to the controller
        self._zone_detail.side_event_panel.action_clicked.connect(
            self._explore_ctrl.on_side_event_action)

        # Give controller access to the inventory panel (created later in _build_ui)
        # Deferred assignment — the panel is set after _build_ui completes.
        self._explore_ctrl._inventory_panel = None

        self._action_handler = CombatActionHandler(
            get_play_state=lambda: self._play_state,
            get_ui_adapter=lambda: self._ui_adapter,
            get_combat_scene=lambda: self._combat_scene,
            turn_label=self._turn_label,
            log=self._log,
            action_bar=self._action_bar,
            move_btn=self._move_btn,
            find_entity=self._find_entity,
            parent_widget=self,
        )

        # Update global sound bridge with the active character name
        from core.audio.sound_event_bridge import SoundEventBridge
        bridge = SoundEventBridge.instance()
        if bridge:
            bridge.set_viewer(
                getattr(self._selected_character, "name", "") or "")

        # ── Multiplayer cursor/draw wiring ──────────────────
        self._mp_player_color = "#888888"
        self._mp_player_id = ""
        self._mp_cursor_pending: tuple[float, float] | None = None

        # Cursor throttle: created but NOT started until multiplayer connects
        self._cursor_throttle = QTimer()
        self._cursor_throttle.setInterval(66)
        self._cursor_throttle.timeout.connect(self._send_cursor_update)

        # Draw mode shortcut (D key) — works in both single and multiplayer,
        # but strokes are only broadcast when a session manager is connected.
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        self._draw_shortcut = QShortcut(QKeySequence("D"), self)
        self._draw_shortcut.activated.connect(self._toggle_draw_mode)

        self._enter_intro()

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def _run_transition(self, transition_id: str, on_complete=None) -> None:
        """Execute a registered transition with the current view stack."""
        outgoing = self._view_stack.currentWidget()
        # For combat→exploration, incoming is the zone detail or map view
        # For exploration→combat, incoming is the combat map view
        incoming = None
        if "to_exploration" in transition_id:
            incoming = self._view_stack.widget(1) if self._view_stack.count() > 1 else None

        def _after():
            if incoming:
                idx = self._view_stack.indexOf(incoming)
                if idx >= 0:
                    self._view_stack.setCurrentIndex(idx)
                incoming.show()
            if on_complete:
                on_complete()

        self._transition_engine.execute(
            transition_id,
            outgoing=outgoing,
            incoming=incoming,
            on_complete=_after,
        )

    # ------------------------------------------------------------------
    # Private setters for controller access
    # ------------------------------------------------------------------

    def _set_play_state(self, state: PlayState) -> None:
        self._play_state = state

    def _set_is_running(self, value: bool) -> None:
        self._is_running = value

    def _set_animator(self, value) -> None:
        self._animator = value

    def _set_current_zone(self, zone: str | None) -> None:
        self._current_zone = zone

    def _build_ui(self, scenario_name: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Banner
        banner = QLabel("PLAY MODE")
        banner.setAlignment(Qt.AlignCenter)
        banner.setStyleSheet(
            "background: #1a472a; color: #e0e0e0; padding: 8px; "
            "font-weight: bold; font-size: 14px; letter-spacing: 2px;"
        )
        layout.addWidget(banner)

        # Turn indicator
        self._turn_label = QLabel("Initializing...")
        self._turn_label.setAlignment(Qt.AlignCenter)
        self._turn_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 6px;"
        )
        layout.addWidget(self._turn_label)

        # ── Inner QMainWindow for dock support ──
        self._inner_main = QMainWindow()
        self._inner_main.setWindowFlags(Qt.Widget)
        self._inner_main.setDockNestingEnabled(True)

        # Central widget: view stack — intro (0) | zone detail (1) | full map (2)
        from PyQt5.QtWidgets import QSizePolicy
        self._view_stack = QStackedWidget()
        self._view_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Index 0: Intro screen
        description = self._meta.get("description", "")
        self._intro_widget = ScenarioIntroWidget(scenario_name, description)
        self._intro_widget.begin_requested.connect(self._on_intro_complete)
        self._view_stack.addWidget(self._intro_widget)

        # Index 1: Zone detail (PRIMARY exploration/combat view)
        from ui.exploration.zone_detail_widget import ZoneDetailWidget
        self._zone_detail = ZoneDetailWidget()
        self._zone_detail.navigate_to_map.connect(self._show_full_map)
        self._zone_detail.navigate_direction.connect(self._on_direction_move)
        self._zone_detail.navigate_to_zone.connect(self._on_navigate_to_zone)
        self._zone_detail.entity_clicked.connect(self._on_entity_clicked)
        self._zone_detail.entity_info_requested.connect(self._on_entity_info_fallback)
        self._view_stack.addWidget(self._zone_detail)

        # NPC interaction panel (lives inside ZoneDetailWidget layout)
        self._npc_panel = self._zone_detail.npc_panel
        self._npc_panel.interaction_chosen.connect(self._on_interaction_chosen)
        self._npc_panel.dismissed.connect(lambda: None)

        # Index 2: Full map (temporary, accessed via sidebar or zone detail)
        self._map_scene = PlayMapScene(self._tile_dicts, tile_size=36)
        self._map_scene.set_info_filter(self._info_filter)
        self._full_map_view = MapView()
        self._full_map_view.setScene(self._map_scene)
        self._full_map_view.set_auto_fit(True)
        self._view_stack.addWidget(self._full_map_view)

        self._inner_main.setCentralWidget(self._view_stack)

        # ── Dock panels ──
        self._dock_widgets: list[QDockWidget] = []

        def _add_dock(title, widget, object_name, area=Qt.RightDockWidgetArea,
                      visible=True):
            dock = QDockWidget(title, self._inner_main)
            dock.setObjectName(object_name)
            dock.setWidget(widget)
            self._inner_main.addDockWidget(area, dock)
            dock.setVisible(visible)
            self._dock_widgets.append(dock)
            return dock

        # Mini-map
        self._mini_map_scene = PlayMapScene(self._tile_dicts, tile_size=20)
        self._mini_map_scene.set_info_filter(self._info_filter)
        self._mini_map_view = MapView()
        self._mini_map_view.setScene(self._mini_map_scene)
        self._mini_map_view.set_auto_fit(True)
        self._mini_map_view.setMaximumHeight(350)
        self._dock_minimap = _add_dock("Map", self._mini_map_view, "dock_minimap")

        # Initiative panel
        self._initiative_panel = InitiativePanel(role=self._info_filter.initiative_role())
        self._initiative_panel.next_turn_button.clicked.connect(self._on_end_turn)
        self._dock_initiative = _add_dock(
            "Initiative", self._initiative_panel, "dock_initiative", visible=False)

        # Party status strip
        self._party_strip = PartyStatusStrip()
        self._dock_party = _add_dock("Party", self._party_strip, "dock_party")

        # Inventory panel
        from ui.panels.inventory_panel import InventoryPanel
        self._inventory_panel = InventoryPanel()
        self._dock_inventory = _add_dock(
            "Inventory", self._inventory_panel, "dock_inventory", visible=False)
        # Wire to controller
        if hasattr(self, "_explore_ctrl"):
            self._explore_ctrl._inventory_panel = self._inventory_panel

        # DM automation controls
        if self._role == PlayerRole.DM:
            from PyQt5.QtWidgets import QButtonGroup, QRadioButton
            from core.engine.play_state import DMAutomation
            self._dm_automation = DMAutomation.ENEMIES_ONLY

            dm_widget = QWidget()
            dm_layout = QVBoxLayout(dm_widget)
            dm_layout.setContentsMargins(4, 4, 4, 4)

            auto_enemies = QRadioButton("Auto-run enemies")
            auto_enemies.setToolTip("AI controls enemies/NPCs — you control the party")
            auto_enemies.setChecked(True)

            auto_all = QRadioButton("Full auto (watch)")
            auto_all.setToolTip("AI controls everyone — simulation mode")

            auto_manual = QRadioButton("Manual (control all)")
            auto_manual.setToolTip("You control everything — pure tabletop mode")

            self._auto_btn_group = QButtonGroup(self)
            self._auto_btn_group.addButton(auto_enemies, DMAutomation.ENEMIES_ONLY.value)
            self._auto_btn_group.addButton(auto_all, DMAutomation.ALL_AUTO.value)
            self._auto_btn_group.addButton(auto_manual, DMAutomation.MANUAL.value)
            self._auto_btn_group.idToggled.connect(self._on_automation_changed)

            dm_layout.addWidget(auto_enemies)
            dm_layout.addWidget(auto_all)
            dm_layout.addWidget(auto_manual)
            self._dock_dm = _add_dock("DM Controls", dm_widget, "dock_dm")
        else:
            self._dm_automation = None
            self._auto_btn_group = None

        # Combat / Event log
        from ui.widgets.combat_log_widget import CombatLogWidget
        self._log = CombatLogWidget()
        self._dock_log = _add_dock("Event Log", self._log, "dock_log")

        # Narration panel
        from ui.panels.narration_panel import NarrationPanel
        self._narration_panel = NarrationPanel()
        self._dock_narration = _add_dock("Narration", self._narration_panel, "dock_narration")

        # Quest log panel + tracker
        from ui.panels.quest_log_panel import QuestLogPanel
        self._quest_panel = QuestLogPanel()
        if self._quests:
            self._quest_panel.load_quests(self._quests)

        # Initialize quest tracker with scenario quests
        from core.engine.quest_tracker import QuestTracker
        try:
            from models.quest.quest_registry import SHATTERED_REALMS_QUESTS
            self._quest_tracker = QuestTracker(
                SHATTERED_REALMS_QUESTS,
                on_quest_completed=self._on_quest_completed)
            self._quest_panel.refresh_from_tracker(self._quest_tracker)
        except ImportError:
            self._quest_tracker = None

        # Give controller a callback to refresh quests after flag changes
        self._explore_ctrl._on_flags_changed = self.refresh_quest_state

        self._dock_quests = _add_dock("Quest Log", self._quest_panel, "dock_quests")

        # Adapter shims for controllers (CollapsibleSection interface)
        self._initiative_section = _DockSectionAdapter(self._dock_initiative)
        self._log_section = _DockSectionAdapter(self._dock_log)

        # View menu for toggling dock panels
        view_menu = self._inner_main.menuBar().addMenu("View")
        for dock in self._dock_widgets:
            view_menu.addAction(dock.toggleViewAction())

        layout.addWidget(self._inner_main, stretch=1)

        # Wire map signals
        self._mini_map_scene.tile_clicked.connect(self._on_sidebar_tile_clicked)
        self._mini_map_scene.tile_double_clicked.connect(self._on_tile_detail)
        self._map_scene.tile_double_clicked.connect(self._on_tile_detail)
        self._map_scene.tile_clicked.connect(self._on_full_map_tile_clicked)

        # Action stack: exploration bar (idx 0) | combat bar (idx 1)
        self._action_stack = QStackedWidget()

        # Exploration page
        explore_page = QWidget()
        explore_layout = QHBoxLayout(explore_page)
        explore_layout.setContentsMargins(0, 0, 0, 0)
        self._exploration_bar = ExplorationBarPanel(
            role=self._role.value)
        explore_layout.addWidget(self._exploration_bar, stretch=1)

        self._start_combat_btn = QPushButton("Roll Initiative")
        self._start_combat_btn.setStyleSheet(
            "font-weight: bold; padding: 8px 16px; background: #8b2020; color: white;"
        )
        self._start_combat_btn.clicked.connect(self._enter_combat)
        explore_layout.addWidget(self._start_combat_btn)
        self._action_stack.addWidget(explore_page)

        # Combat page
        combat_page = QWidget()
        combat_layout = QHBoxLayout(combat_page)
        combat_layout.setContentsMargins(0, 0, 0, 0)
        self._action_bar = ActionBarPanel(role="player")
        combat_layout.addWidget(self._action_bar, stretch=1)

        self._move_btn = QPushButton("Move")
        self._move_btn.setToolTip("Move toward the nearest enemy")
        self._move_btn.setMinimumHeight(32)
        self._move_btn.clicked.connect(self._on_move)
        combat_layout.addWidget(self._move_btn)
        self._action_stack.addWidget(combat_page)

        self._action_stack.hide()

        # Wire action bar signals
        self._action_bar.action_selected.connect(self._on_action_bar_action)
        self._action_bar.end_turn_requested.connect(self._on_end_turn)
        self._action_bar.spell_cast_requested.connect(self._on_spell_cast)

        # Wire exploration bar signals
        self._exploration_bar.action_selected.connect(self._on_exploration_action)
        self._exploration_bar.rest_requested.connect(self._on_rest_requested)

        # Combat encounter strip (animated attack sequence)
        from ui.widgets.combat_encounter_strip import CombatEncounterStrip
        self._encounter_strip = CombatEncounterStrip()
        layout.addWidget(self._encounter_strip)

        layout.addWidget(self._action_stack)

        # Bottom controls
        bottom = QHBoxLayout()
        bottom.addStretch()
        close_btn = QPushButton("End Session")
        close_btn.clicked.connect(self.close)
        bottom.addWidget(close_btn)
        layout.addLayout(bottom)

        # Restore dock layout from previous session
        self._restore_dock_state()


    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def _update_ui_for_state(self) -> None:
        """Synchronise action bar and sidebar for the current play state."""
        is_explore = self._play_state == PlayState.EXPLORATION
        is_combat = self._play_state == PlayState.COMBAT

        # Action stack
        if is_explore:
            self._action_stack.setCurrentIndex(0)
            self._action_stack.show()
            self._start_combat_btn.setVisible(self._role == PlayerRole.DM)
        elif is_combat:
            self._action_stack.setCurrentIndex(1)
            self._action_stack.show()
            self._action_bar.hide()
            self._move_btn.hide()
        else:
            self._action_stack.hide()

        # Dock panels: swap visibility per state
        self._dock_initiative.setVisible(is_combat)
        self._dock_party.setVisible(is_explore or is_combat)
        self._dock_minimap.setVisible(is_explore)
        self._dock_log.setWindowTitle("Combat Log" if is_combat else "Event Log")

        # During combat, collapse non-essential docks and move Party to
        # right side so it doesn't squash the combat map from the top.
        if is_combat:
            self._dock_quests.setVisible(False)
            self._dock_narration.setVisible(False)
            self._dock_minimap.setVisible(False)
            # Force Party dock to right area during combat
            if self._inner_main.dockWidgetArea(self._dock_party) != Qt.RightDockWidgetArea:
                self._inner_main.addDockWidget(Qt.RightDockWidgetArea, self._dock_party)
            self._party_strip.setMaximumHeight(120)
        elif is_explore:
            self._dock_quests.setVisible(True)
            self._dock_narration.setVisible(True)
            self._party_strip.setMaximumHeight(16777215)  # Qt default max
        if is_explore:
            self._explore_ctrl.refresh_party_strip()

    def _enter_intro(self) -> None:
        self._play_state = PlayState.INTRO
        self._view_stack.setCurrentIndex(0)
        self._turn_label.setText("")
        self._update_ui_for_state()

    def _on_intro_complete(self) -> None:
        self._enter_exploration()

    def _enter_exploration(self) -> None:
        self._play_state = PlayState.EXPLORATION
        self._view_stack.setCurrentIndex(1)  # Zone detail (primary)
        self._update_ui_for_state()

        # Configure fog on both map scenes
        fog = self._info_filter.should_fog()
        self._map_scene.set_fog_enabled(fog)
        self._mini_map_scene.set_fog_enabled(fog)

        # Render entities on both maps
        vision = self._info_filter.get_vision_entities(self._all_entities)
        vision_arg = vision if fog else None
        self._map_scene.update_entities(
            self._all_entities, None, vision_entities=vision_arg,
        )
        self._mini_map_scene.update_entities(
            self._all_entities, None, vision_entities=vision_arg,
        )
        self._map_scene.invalidate()
        self._mini_map_scene.invalidate()
        self._refit_map_views()

        # Auto-load starting tile into zone detail
        self._load_tile_at(self._start_position)

        self._turn_label.setText("Exploration — click tiles to move")
        self._turn_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 6px; color: #5dcaa5;"
        )

        if hasattr(self._log, "add_system_message"):
            self._log.add_system_message("=== Exploration mode ===", "explore")
        else:
            self._log.append("=== Exploration mode ===")

    _TERRAIN_TO_PRESET = {
        "GRASS": "forest", "FLOOR": "dungeon", "MOUNTAIN": "cave",
        "SAND": "open_field", "SWAMP": "forest", "WATER": "open_field",
    }

    def _enter_combat(self) -> None:
        if self._play_state == PlayState.COMBAT:
            return
        self._play_state = PlayState.COMBAT
        self._update_ui_for_state()

        # Create session with role-aware config
        self._ui_adapter = UIInputAdapter(parent=self)
        self._ui_adapter.action_requested.connect(self._on_action_requested)

        char_name = getattr(self._selected_character, "name", "") if self._selected_character else ""
        config = PlayConfig(
            seed=42, max_rounds=100,
            role=self._role.value,
            controlled_character=char_name,
        )
        # Zone-scoped combat: only entities in the current zone fight.
        from core.engine.zone_utils import (
            has_any_zones, entities_in_zone, nearby_combatants,
        )
        if has_any_zones(self._zone_map) and self._current_zone:
            combat_entities = entities_in_zone(
                self._all_entities, self._zone_map, self._current_zone)
            zone_label = self._current_zone
        else:
            # Fallback: proximity to the triggering position
            trigger_pos = getattr(self._selected_character, "position", None) \
                or self._start_position
            combat_entities = nearby_combatants(
                self._all_entities, trigger_pos, radius=5)
            zone_label = "nearby area"

        # Abort if no alive enemies — prevents empty-combat loops
        alive_enemies = [
            e for e in combat_entities
            if getattr(e, "entity_type", "") in (EntityType.ENEMY, EntityType.MONSTER, EntityType.HOSTILE)
            and getattr(e, "hp", 0) > 0
        ]
        if not alive_enemies:
            self._play_state = PlayState.EXPLORATION
            if self._current_zone:
                self._cleared_zones.add(self._current_zone.strip().lower())
            return

        # -- Generate per-tile combat grid --
        from models.combat.grid_generator import (
            generate_combat_grid, combat_grid_to_tile_dicts,
        )
        from models.combat.terrain_presets import get_preset

        # Pick terrain preset from current tile
        tile_terrain = "GRASS"
        if self._current_tile_pos:
            for td in self._tile_dicts:
                if tuple(td.get("position", [0, 0])) == self._current_tile_pos:
                    tile_terrain = td.get("terrain", "GRASS")
                    break
        preset_id = self._TERRAIN_TO_PRESET.get(tile_terrain.upper(), "open_field")
        preset = get_preset(preset_id) or get_preset("open_field")

        grid_w, grid_h = 10, 10
        combat_grid = generate_combat_grid(grid_w, grid_h, preset, seed=42)
        combat_tile_dicts = combat_grid_to_tile_dicts(combat_grid)

        # Build set of blocked cells for spawn placement
        blocked = set()
        for (col, row), td in combat_grid.items():
            if any(t.name == "BLOCKS_MOVEMENT" for t in td.tags):
                blocked.add((row, col))

        # Save world positions and remap entities to combat grid
        self._world_positions = {
            e.name: getattr(e, "position", None) for e in combat_entities
        }
        players = [e for e in combat_entities
                    if getattr(e, "entity_type", "") == EntityType.PLAYER]
        enemies = [e for e in combat_entities if e not in players]

        def _place(entities, start_row, row_dir):
            idx = 0
            for e in entities:
                while True:
                    r = start_row + row_dir * (idx // grid_w)
                    c = idx % grid_w
                    idx += 1
                    if 0 <= r < grid_h and (r, c) not in blocked:
                        e.position = (r, c)
                        break
                    if idx > grid_w * grid_h:
                        e.position = (start_row, 0)
                        break

        _place(players, grid_h - 1, -1)   # bottom rows
        _place(enemies, 0, 1)              # top rows

        # Create or reuse combat scene and view
        if self._combat_scene is None:
            self._combat_scene = PlayMapScene(combat_tile_dicts, tile_size=48)
            from PyQt5.QtWidgets import QSizePolicy
            self._combat_map_view = MapView()
            self._combat_map_view.setScene(self._combat_scene)
            self._combat_map_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._combat_map_view.setMinimumSize(200, 200)
            self._view_stack.addWidget(self._combat_map_view)
        else:
            self._combat_scene.reset(combat_tile_dicts, tile_size=48)
        # (Re)configure signals — disconnect first to avoid duplicates
        try:
            self._combat_scene.tile_clicked.disconnect(self._on_combat_tile_clicked)
        except TypeError:
            pass
        try:
            self._combat_scene.tile_hovered.disconnect(self._on_combat_tile_hovered)
        except TypeError:
            pass
        self._combat_scene.tile_clicked.connect(self._on_combat_tile_clicked)
        self._combat_scene.tile_hovered.connect(self._on_combat_tile_hovered)
        self._combat_scene.set_info_filter(self._info_filter)
        self._combat_scene.set_fog_enabled(self._info_filter.should_fog())
        self._combat_map_view.hide()  # hidden until transition reveals it

        # -- Create session --
        self._runner = PlaySessionRunner.from_entities(
            combat_entities, config, self._ui_adapter)

        # Configure initiative panel
        init_role = self._info_filter.initiative_role()
        self._initiative_panel.set_role(init_role, viewer_entity_name=char_name)
        self._dock_initiative.setVisible(True)
        self._dock_initiative.raise_()

        if hasattr(self._log, "add_system_message"):
            self._log.add_system_message(f"=== Combat in {zone_label} ===", "combat")
            self._log.add_system_message(f"Combatants: {len(self._runner.entities)}", "combat")
        else:
            self._log.append(f"=== Combat in {zone_label} ===")
            self._log.append(f"Combatants: {len(self._runner.entities)}")

        # Start animator + choreographer
        tile_lookup = lambda r, c: self._combat_scene._tiles.get((r, c))
        try:
            from ui.animations.combat_animator import CombatAnimator
            self._animator = CombatAnimator(
                scene=self._combat_scene,
                tile_lookup=tile_lookup,
            )
        except Exception:
            pass

        # Wire choreographer with combat scene context
        if hasattr(self, '_choreographer') and self._choreographer:
            self._choreographer._scene = self._combat_scene
            self._choreographer._tile_lookup = tile_lookup
            self._choreographer._animator = self._animator

        # Apply current DM automation mode to swap adapters BEFORE the loop
        if self._dm_automation is not None:
            self._set_dm_automation(self._dm_automation)

        # ── Run the exploration→combat transition ──
        # The outgoing widget is the current view; incoming is the combat view.
        outgoing = self._view_stack.currentWidget()

        def _on_transition_complete():
            # Ensure combat view is the active stack page
            idx = self._view_stack.indexOf(self._combat_map_view)
            if idx >= 0:
                self._view_stack.setCurrentIndex(idx)
            self._combat_map_view.show()
            # Don't use auto_fit — it conflicts with our manual fit.
            # Instead, fit once after layout settles.
            QTimer.singleShot(50, self._fit_combat_map)
            QTimer.singleShot(300, self._fit_combat_map)

            # Initiative rolled sound (transition 9: combat_setup_to_initiative)
            try:
                from core.audio.ui_sound_manager import UISoundManager, SoundCategory
                UISoundManager.instance().play_shared("initiative", SoundCategory.COMBAT)
            except Exception:
                pass

            self._is_running = True
            self._turn_ctrl.update_table()
            QTimer.singleShot(100, self._advance_turns)

        self._transition_engine.execute(
            "exploration_to_combat",
            outgoing=outgoing,
            incoming=self._combat_map_view,
            on_complete=_on_transition_complete,
        )

    def _fit_combat_map(self) -> None:
        """Zoom combat map to fill the view area."""
        if not self._combat_scene or not self._combat_map_view:
            return
        rect = self._combat_scene.sceneRect()
        if rect.isEmpty():
            return

        # Force the MapView to match the stack size — it may not have
        # resized automatically since it was added after the stack was shown.
        sw = self._view_stack.width()
        sh = self._view_stack.height()
        if sw > 50 and sh > 50:
            self._combat_map_view.resize(sw, sh)
            self._combat_map_view.fitInView(
                rect.adjusted(-20, -20, 20, 20), Qt.KeepAspectRatio)

    def _on_session_ended(self) -> None:
        result = self._turn_ctrl.on_session_ended(
            world_positions=self._world_positions,
            all_entities=self._all_entities,
            view_stack=self._view_stack,
            combat_map_view=self._combat_map_view,
            combat_scene=self._combat_scene,
            move_range_outline=self._action_handler.move_range_outline,
            current_zone=self._current_zone,
            cleared_zones=self._cleared_zones,
        )
        # Apply returned state
        self._combat_map_view = result["combat_map_view"]
        self._combat_scene = result["combat_scene"]
        self._action_handler.move_range_outline = result["move_range_outline"]
        if result.get("outcome") == "victory":
            self._explore_ctrl.combat_cooldown = True

    # ------------------------------------------------------------------
    # Delegate: combat turn loop
    # ------------------------------------------------------------------

    def _advance_turns(self) -> None:
        self._turn_ctrl.advance_turns()

    def _update_table(self) -> None:
        self._turn_ctrl.update_table()

    def _log_action_result(self, result) -> None:
        self._turn_ctrl.log_action_result(result)

    # ------------------------------------------------------------------
    # Delegate: exploration
    # ------------------------------------------------------------------

    def _get_active_character(self):
        return self._explore_ctrl.get_active_character()

    def _on_explore_move(self, row: int, col: int) -> None:
        """Handle single-click tile movement in exploration mode."""
        self._explore_ctrl.on_explore_move(row, col)

    def _check_encounter(self, entity, pos: tuple) -> None:
        self._explore_ctrl.check_encounter(entity, pos)

    def _refresh_party_strip(self) -> None:
        self._explore_ctrl.refresh_party_strip()

    def _on_exploration_action(self, action_id: str) -> None:
        self._explore_ctrl.on_exploration_action(action_id)

    def _on_rest_requested(self, rest_type: str) -> None:
        self._explore_ctrl.on_rest_requested(rest_type)

    def _on_entity_clicked(self, entity_or_name) -> None:
        """Handle click on an entity in the zone detail view."""
        self._explore_ctrl.on_entity_clicked(entity_or_name)

    def _on_entity_info_fallback(self, entity_name: str, entity_type: str) -> None:
        self._explore_ctrl.on_entity_info_fallback(entity_name, entity_type)

    # ------------------------------------------------------------------
    # Multiplayer: cursors and draw
    # ------------------------------------------------------------------

    def connect_session_manager(self, session_manager) -> None:
        """Wire multiplayer cursor/draw signals from a SessionManager.

        Called by the host/join flow after the session is established.
        Enables multiplayer-only features (cursor sharing, draw broadcast)
        that are dormant in single-player mode.
        """
        signals = session_manager.signals
        signals.cursor_updated.connect(self._on_remote_cursor)
        signals.draw_received.connect(self._on_remote_draw)
        self._mp_session_manager = session_manager

        # Wire outgoing cursor/draw signals and enable multiplayer flag
        for scene in (self._combat_scene, self._map_scene, self._mini_map_scene):
            if scene:
                scene._multiplayer_active = True
                scene.cursor_moved.connect(self._on_local_cursor_moved)
                scene.draw_completed.connect(self._on_draw_completed)

        self._cursor_throttle.start()

    def set_player_identity(self, player_id: str, color: str) -> None:
        """Set the local player's multiplayer identity (from WELCOME)."""
        self._mp_player_id = player_id
        self._mp_player_color = color

    def _on_local_cursor_moved(self, x: float, y: float) -> None:
        """Buffer cursor position for throttled sending."""
        self._mp_cursor_pending = (x, y)

    def _send_cursor_update(self) -> None:
        """Send buffered cursor position to the session (called by throttle timer)."""
        if self._mp_cursor_pending is None:
            return
        mgr = getattr(self, "_mp_session_manager", None)
        if not mgr:
            return
        x, y = self._mp_cursor_pending
        self._mp_cursor_pending = None
        from network.protocol import make_cursor_update
        msg = make_cursor_update(
            self._mp_player_id, "", x, y, self._mp_player_color,
        )
        mgr.send_message(msg)

    def _on_remote_cursor(
        self, player_id: str, player_name: str,
        x: float, y: float, color: str,
    ) -> None:
        """Update a remote player's cursor on all active map scenes."""
        for scene in (self._combat_scene, self._map_scene, self._mini_map_scene):
            if scene:
                scene.update_remote_cursor(player_id, player_name, x, y, color)

    def _on_draw_completed(self, points: list) -> None:
        """Send a completed draw stroke to the session."""
        mgr = getattr(self, "_mp_session_manager", None)
        if not mgr:
            return
        from network.protocol import make_draw_stroke
        msg = make_draw_stroke(self._mp_player_id, points, self._mp_player_color)
        mgr.send_message(msg)

    def _on_remote_draw(
        self, player_id: str, points: list, color: str,
    ) -> None:
        """Show a remote player's draw stroke on all active map scenes."""
        for scene in (self._combat_scene, self._map_scene, self._mini_map_scene):
            if scene:
                scene.show_draw_stroke(player_id, points, color)

    def _toggle_draw_mode(self) -> None:
        """Toggle draw mode on/off (shortcut: D key)."""
        new_state = not getattr(self._combat_scene, "_draw_mode", False)
        for scene in (self._combat_scene, self._map_scene, self._mini_map_scene):
            if scene:
                scene.set_draw_mode(new_state)
        if new_state:
            self._turn_label.setText("Draw mode ON (drag to draw, release to send)")
            self._turn_label.setStyleSheet(
                "font-size: 14px; font-weight: bold; padding: 6px; color: #f39c12;")
        else:
            self._turn_label.setText("")
            self._turn_label.setStyleSheet("")

    def _on_interaction_chosen(self, entity_name: str, interaction_id: str) -> None:
        self._explore_ctrl.on_interaction_chosen(
            entity_name, interaction_id, parent_widget=self)

    def _on_automation_changed(self, btn_id: int, checked: bool) -> None:
        """Handle DM automation radio button change."""
        if not checked:
            return
        from core.engine.play_state import DMAutomation
        try:
            mode = DMAutomation(btn_id)
        except ValueError:
            return
        self._set_dm_automation(mode)

    def _set_dm_automation(self, mode) -> None:
        """Reassign adapters based on DM automation setting.

        Handles ALL_AUTO, ENEMIES_ONLY, and MANUAL modes by swapping
        HeuristicAIAdapter vs _ui_adapter on each entity.
        """
        from core.engine.play_state import DMAutomation
        self._dm_automation = mode

        if not self._runner or not self._ui_adapter:
            return

        from core.engine.ai.heuristic_adapter import HeuristicAIAdapter
        entities_by_name = {e.name: e for e in self._runner.entities}

        for entity in self._runner.entities:
            etype = getattr(entity, "entity_type", "")
            is_enemy = etype in (EntityType.ENEMY, EntityType.MONSTER, EntityType.HOSTILE, EntityType.NPC)

            if mode == DMAutomation.ALL_AUTO:
                # AI controls everyone
                self._runner.set_adapter(
                    entity.name, HeuristicAIAdapter(entities_by_name=entities_by_name))
            elif mode == DMAutomation.ENEMIES_ONLY:
                # AI for enemies, UI for players
                if is_enemy:
                    self._runner.set_adapter(
                        entity.name, HeuristicAIAdapter(entities_by_name=entities_by_name))
                else:
                    self._runner.set_adapter(entity.name, self._ui_adapter)
            elif mode == DMAutomation.MANUAL:
                # DM controls everything via UI
                self._runner.set_adapter(entity.name, self._ui_adapter)

        labels = {
            DMAutomation.ALL_AUTO: "Full Auto — AI controls everyone",
            DMAutomation.ENEMIES_ONLY: "Enemies Auto — DM controls party",
            DMAutomation.MANUAL: "Manual — DM controls everyone",
        }
        self._log.append(f"  Automation: {labels.get(mode, str(mode))}")

    # ------------------------------------------------------------------
    # Delegate: combat actions
    # ------------------------------------------------------------------

    def _on_action_requested(self, entity_name: str, game_state,
                             available_actions: list) -> None:
        self._action_handler.on_action_requested(
            entity_name, game_state, available_actions)

    def _on_action_bar_action(self, action_id: str) -> None:
        self._action_handler.on_action_bar_action(action_id)

    def _on_move(self) -> None:
        self._action_handler.on_move()

    def _on_combat_tile_clicked(self, row: int, col: int) -> None:
        """Handle tile click on the combat grid for targeting or movement."""
        self._action_handler.on_combat_tile_clicked(row, col)

    def _on_combat_tile_hovered(self, row: int, col: int) -> None:
        self._action_handler.on_combat_tile_hovered(row, col)

    def _on_end_turn(self) -> None:
        self._action_handler.on_end_turn()

    def _on_spell_cast(self) -> None:
        self._action_handler.on_spell_cast()

    # ------------------------------------------------------------------
    # Tile detail view
    # ------------------------------------------------------------------

    def _on_tile_detail(self, tile_dict: dict) -> None:
        """Load tile zone data into the zone detail view."""
        zones = tile_dict.get("zones", [])
        if not zones:
            return

        try:
            from models.tiles.tile_zone import TileZone
            from models.exploration.zone_scene_data import build_zone_scene

            tile_zones = [TileZone.from_dict(z) for z in zones]
            all_zones = {z.zone_id: z for z in tile_zones}
            first_zone = tile_zones[0]

            scene_data = build_zone_scene(
                first_zone, all_zones,
                player_entity_name=self._action_handler.current_entity_name or None,
            )
            # If zone has no background, fall back to biome background
            if not scene_data.background_image:
                scene_data.background_image = tile_dict.get("background_image")
            # Collect entities from zone placements (primary source)
            entities_here = [p.entity for p in first_zone.placements
                             if hasattr(p, "entity") and p.entity]
            # Also include entities defined directly on the zone
            for e in getattr(first_zone, "entities", []):
                if e not in entities_here:
                    entities_here.append(e)
            # Fall back to tile-level entities matched by position.
            # Collect all tile positions belonging to this zone so we find
            # entities placed on ANY tile within the zone, not just the
            # tile the player navigated to.
            if not entities_here:
                zone_id = first_zone.zone_id
                zone_positions = set()
                for td in self._tile_dicts:
                    for z in td.get("zones", []):
                        if z.get("zone_id") == zone_id:
                            zone_positions.add(tuple(td.get("position", [0, 0])))
                if not zone_positions:
                    zone_positions = {self._current_tile_pos}
                entities_here = [
                    e for e in self._all_entities
                    if getattr(e, "position", None) in zone_positions
                ]
            # If the scene has no objects but we found entities, inject them
            # into the scene so they render as tokens on the canvas.
            if entities_here and not any(scene_data.objects_by_depth.values()):
                from models.exploration.zone_scene_data import (
                    _make_scene_object, _get_faction,
                )
                spread = 1.0 / max(len(entities_here), 1)
                player_name = self._action_handler.current_entity_name or None
                for i, entity in enumerate(entities_here):
                    from models.exploration.zone_scene_data import SceneObject
                    etype = getattr(entity, "entity_type", "")
                    if player_name and entity.name == player_name:
                        scene_data.player_position = ((i + 0.5) * spread, 3)
                    else:
                        obj = _make_scene_object(
                            entity, depth=3, x_percent=(i + 0.5) * spread)
                        scene_data.objects_by_depth[3].append(obj)
            # Replace zone connection arrows with grid-adjacent tile arrows only.
            # Zone connections can teleport to non-adjacent tiles which is
            # confusing — the player should navigate spatially on the grid.
            from models.exploration.zone_scene_data import NavArrow
            scene_data.nav_arrows = self._build_adjacent_arrows(
                self._current_tile_pos or (0, 0))
            self._zone_detail.load_zone(scene_data, entities=entities_here)
            self._view_stack.setCurrentIndex(1)  # Zone detail is primary
        except Exception as e:
            self._log.append(f"  Zone view error: {e}")

    def _build_adjacent_arrows(self, pos: tuple[int, int]) -> list:
        """Build nav arrows for grid-adjacent tiles only."""
        from models.exploration.zone_scene_data import NavArrow
        arrows = []
        _dir_map = {(-1, 0): "up", (1, 0): "down", (0, -1): "left", (0, 1): "right"}
        for (dr, dc), direction in _dir_map.items():
            adj_pos = (pos[0] + dr, pos[1] + dc)
            adj_td = self._tile_by_pos.get(adj_pos)
            if adj_td:
                adj_label = (adj_td.get("user_label")
                             or adj_td.get("zone_id")
                             or adj_td.get("terrain", "?"))
                arrows.append(NavArrow(
                    target_zone_id=f"tile_{adj_pos[0]}_{adj_pos[1]}",
                    target_label=adj_label,
                    direction=direction,
                ))
        return arrows

    def _refit_map_views(self) -> None:
        """Re-fit map views after fog reveals new tiles."""
        if hasattr(self, "_full_map_view") and self._full_map_view:
            self._full_map_view.refit()
        if hasattr(self, "_mini_map_view") and self._mini_map_view:
            self._mini_map_view.refit()

    def _show_full_map(self) -> None:
        """Switch to full-screen map view."""
        if self._play_state == PlayState.COMBAT:
            if self._combat_map_view:
                idx = self._view_stack.indexOf(self._combat_map_view)
                if idx >= 0:
                    self._view_stack.setCurrentIndex(idx)
            return
        self._run_transition(
            "tile_detail_to_map",
            on_complete=lambda: self._view_stack.setCurrentIndex(2))

    def _return_to_detail(self) -> None:
        """Return from full map to zone detail view."""
        if self._play_state == PlayState.COMBAT:
            return  # Stay on combat grid
        if self._view_stack.currentIndex() == 2:
            self._run_transition(
                "map_to_tile_detail",
                on_complete=lambda: self._view_stack.setCurrentIndex(1))
        else:
            self._view_stack.setCurrentIndex(1)

    def _on_navigate_to_zone(self, zone_id: str) -> None:
        """Handle nav arrow click — move to an adjacent tile on the grid."""
        if self._play_state == PlayState.COMBAT:
            return

        # All nav arrows now use "tile_R_C" format (grid-adjacent only)
        if zone_id.startswith("tile_"):
            parts = zone_id.split("_")
            if len(parts) == 3:
                try:
                    row, col = int(parts[1]), int(parts[2])
                    self._on_explore_move(row, col)
                    return
                except ValueError:
                    pass

    def _on_direction_move(self, drow: int, dcol: int) -> None:
        """Handle arrow key / WASD movement from the detail view."""
        if self._play_state == PlayState.COMBAT:
            return
        # Find current player position
        for e in self._all_entities:
            if getattr(e, "entity_type", "") == "player" and e.position:
                new_row = e.position[0] + drow
                new_col = e.position[1] + dcol
                # Validate tile exists
                if (new_row, new_col) in {
                    (t["position"][0], t["position"][1])
                    for t in self._tile_dicts
                }:
                    self._fade_to_tile((new_row, new_col))
                    if self._play_state == PlayState.EXPLORATION:
                        self._on_explore_move(new_row, new_col)
                return

    def _fade_to_tile(self, pos: tuple[int, int]) -> None:
        """Fade out zone detail, load new tile, fade back in."""
        from PyQt5.QtWidgets import QGraphicsOpacityEffect
        from PyQt5.QtCore import QPropertyAnimation, QEasingCurve

        widget = self._zone_detail
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

        # Fade out
        fade_out = QPropertyAnimation(effect, b"opacity")
        fade_out.setDuration(150)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.InQuad)

        def _on_faded_out():
            self._load_tile_at(pos)
            # Fade in
            fade_in = QPropertyAnimation(effect, b"opacity")
            fade_in.setDuration(150)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.OutQuad)
            fade_in.finished.connect(lambda: widget.setGraphicsEffect(None))
            self._current_fade = fade_in  # prevent GC
            fade_in.start()

        fade_out.finished.connect(_on_faded_out)
        self._current_fade = fade_out  # prevent GC
        fade_out.start()

    def _on_sidebar_tile_clicked(self, row: int, col: int) -> None:
        """Handle click on sidebar mini-map — load tile into detail view."""
        if self._play_state == PlayState.COMBAT:
            return  # Don't switch views during combat
        self._load_tile_at((row, col))
        # Only the DM can click-teleport the active character.
        if (self._play_state == PlayState.EXPLORATION
                and self._role == PlayerRole.DM):
            self._on_explore_move(row, col)

    def _on_full_map_tile_clicked(self, row: int, col: int) -> None:
        """Handle click on full map — load tile and return to detail."""
        if self._play_state == PlayState.COMBAT:
            return  # Don't switch views during combat
        self._load_tile_at((row, col))
        self._return_to_detail()
        # Only the DM can click-teleport the active character.
        if (self._play_state == PlayState.EXPLORATION
                and self._role == PlayerRole.DM):
            self._on_explore_move(row, col)

    def _load_tile_at(self, pos: tuple[int, int]) -> None:
        """Load the tile at the given position into the zone detail view."""
        self._current_tile_pos = pos
        # Highlight current position on both maps
        self._mini_map_scene.highlight_current_tile(pos[0], pos[1])
        self._map_scene.highlight_current_tile(pos[0], pos[1])

        td = self._tile_by_pos.get(pos)
        if td is None:
            return

        # Ambient audio: crossfade to new track, or stop if tile has none
        ambient = td.get("ambient_audio")
        try:
            from core.audio.ui_sound_manager import UISoundManager
            snd = UISoundManager.instance()
            if ambient:
                snd.play_ambient(ambient)
            else:
                snd.stop_ambient()
        except Exception:
            pass
        zones = td.get("zones", [])
        if zones:
            self._on_tile_detail(td)
        else:
            # Simple tile view with entity list
            label = (td.get("user_label")
                     or td.get("zone_id")
                     or td.get("terrain", "Unknown"))
            note = td.get("note") or ""
            entities_here = [
                e for e in self._all_entities
                if getattr(e, "position", None) == pos
            ]
            self._zone_detail.load_simple_tile(
                label, note, entities_here, self._info_filter,
                background_image=td.get("background_image"),
                nav_arrows=self._build_adjacent_arrows(pos))
            self._check_side_event(pos, td)
            if self._view_stack.currentIndex() == 2:
                self._run_transition(
                    "map_to_tile_detail",
                    on_complete=lambda: self._view_stack.setCurrentIndex(1))
            else:
                self._view_stack.setCurrentIndex(1)

    # ------------------------------------------------------------------
    #  Side-event interaction for empty tiles
    # ------------------------------------------------------------------

    def _check_side_event(self, pos: tuple[int, int], td: dict) -> None:
        """Show the side-event interaction panel when entering a tile."""
        se = td.get("side_event")
        if not se:
            self._explore_ctrl._current_side_event = None
            return
        try:
            from models.side_events import get_event, get_interaction_type
            event = get_event(se["event_id"])
            if not event:
                return
            variant = event.variants[se["variant"]]
            itype = get_interaction_type(event, variant)
        except (KeyError, IndexError):
            return

        # Cache the event on the controller for resolution
        self._explore_ctrl._current_side_event = {
            "pos": pos, "event": event, "variant": variant, "itype": itype,
        }

        # Always log the narrative
        header = f"[{variant.name}]"
        if hasattr(self._log, "add_system_message"):
            self._log.add_system_message(
                f"{header} {variant.narrative}", "explore")
        else:
            self._log.append(f"{header} {variant.narrative}")

        state = self._explore_ctrl._side_event_state.get(pos, {})

        if state.get("status") == "completed":
            # Already resolved — show abbreviated view
            self._zone_detail.side_event_panel.show_completed(
                variant.name, "(Already explored)")
        else:
            # Show interactive panel
            self._explore_ctrl._side_event_state[pos] = {"status": "seen"}
            self._explore_ctrl._trigger_side_event_panel()

    def keyPressEvent(self, event) -> None:
        key = event.key()

        if key == Qt.Key_Escape:
            if self._action_handler.target_selection_mode or self._action_handler.movement_mode:
                self._action_handler.target_selection_mode = False
                self._action_handler.movement_mode = False
                if self._combat_scene:
                    self._combat_scene.clear_all_overlays()
                self._turn_label.setText(
                    f"Your turn: {self._action_handler.current_entity_name}")
                self._turn_label.setStyleSheet(
                    "font-size: 16px; font-weight: bold; padding: 6px; color: #c9952a;")
                return
            if self._view_stack.currentIndex() == 2:
                self._return_to_detail()
                return

        # Combat-only shortcuts
        if self._play_state == PlayState.COMBAT:
            # Space: end turn
            if key == Qt.Key_Space:
                self._action_handler.on_end_turn()
                return
            # 1-6: action bar shortcuts
            _ACTION_KEYS = {
                Qt.Key_1: "attack", Qt.Key_2: "cast_spell",
                Qt.Key_3: "dash", Qt.Key_4: "dodge",
                Qt.Key_5: "disengage", Qt.Key_6: "help",
            }
            if key in _ACTION_KEYS and self._action_bar.isVisible():
                action_id = _ACTION_KEYS[key]
                if action_id == "cast_spell":
                    self._action_handler.on_spell_cast()
                else:
                    self._action_handler.on_action_bar_action(action_id)
                return
            # Tab: cycle initiative focus
            if key == Qt.Key_Tab:
                self._cycle_initiative_focus()
                return

        # Map navigation (all modes)
        _NAV_KEYS = {
            Qt.Key_W: (0, -50), Qt.Key_Up: (0, -50),
            Qt.Key_S: (0, 50), Qt.Key_Down: (0, 50),
            Qt.Key_A: (-50, 0), Qt.Key_Left: (-50, 0),
            Qt.Key_D: (50, 0), Qt.Key_Right: (50, 0),
        }
        if key in _NAV_KEYS:
            dx, dy = _NAV_KEYS[key]
            self._pan_map(dx, dy)
            return

        super().keyPressEvent(event)

    def _cycle_initiative_focus(self):
        """Cycle camera focus through initiative order."""
        if not hasattr(self, '_initiative_focus_idx'):
            self._initiative_focus_idx = 0
        entries = self._initiative_panel.get_entries() if hasattr(self._initiative_panel, 'get_entries') else []
        if not entries:
            return
        self._initiative_focus_idx = (self._initiative_focus_idx + 1) % len(entries)
        # Center camera on entity if possible

    def _pan_map(self, dx, dy):
        """Scroll the active map view by pixel offset."""
        view = None
        if hasattr(self, '_combat_map_view') and self._combat_map_view:
            view = self._combat_map_view
        elif hasattr(self, '_full_map_view') and self._full_map_view:
            view = self._full_map_view
        if view:
            view.horizontalScrollBar().setValue(view.horizontalScrollBar().value() + dx)
            view.verticalScrollBar().setValue(view.verticalScrollBar().value() + dy)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_entity(self, name: str):
        if self._runner:
            for e in self._runner.entities:
                if e.name == name:
                    return e
        for e in self._all_entities:
            if e.name == name:
                return e
        # Search zone placement entities (not in _all_entities)
        try:
            for item_idx in range(self._zone_detail._entity_list.count()):
                item = self._zone_detail._entity_list.item(item_idx)
                data = item.data(Qt.UserRole)
                if data is not None and not isinstance(data, str):
                    if getattr(data, "name", None) == name:
                        return data
        except Exception:
            pass
        return None

    def _find_nearest_enemy(self, state, actor_name: str):
        actor_snap = None
        for es in state.entities:
            if es.name == actor_name:
                actor_snap = es
                break
        if not actor_snap:
            return None

        best = None
        best_dist = float("inf")
        for es in state.entities:
            if es.entity_type == "enemy" and es.hp > 0:
                dx = es.position[0] - actor_snap.position[0]
                dy = es.position[1] - actor_snap.position[1]
                dist = abs(dx) + abs(dy)
                if dist < best_dist:
                    best_dist = dist
                    best = es.name
        if best:
            return self._find_entity(best)
        for es in state.entities:
            if es.entity_type == "player" and es.hp > 0:
                return self._find_entity(es.name)
        return None

    def _find_nearest_enemy_position(self, state, actor_name: str):
        actor_snap = None
        for es in state.entities:
            if es.name == actor_name:
                actor_snap = es
                break
        if not actor_snap:
            return None

        best_pos = None
        best_dist = float("inf")
        for es in state.entities:
            if es.entity_type != actor_snap.entity_type and es.hp > 0:
                dx = es.position[0] - actor_snap.position[0]
                dy = es.position[1] - actor_snap.position[1]
                dist = abs(dx) + abs(dy)
                if dist < best_dist:
                    best_dist = dist
                    best_pos = es.position
        return best_pos

    # ------------------------------------------------------------------
    # Dock state persistence
    # ------------------------------------------------------------------

    def _save_dock_state(self) -> None:
        settings = QSettings("DnDWorldBuilder", "PlaySession")
        settings.setValue("dock_state", self._inner_main.saveState())

    def _restore_dock_state(self) -> None:
        settings = QSettings("DnDWorldBuilder", "PlaySession")
        state = settings.value("dock_state")
        if state:
            self._inner_main.restoreState(state)

    # ------------------------------------------------------------------
    #  Session save/load
    # ------------------------------------------------------------------

    def save_session(self, path=None) -> None:
        """Save the complete session state to a JSON file."""
        from pathlib import Path
        from core.engine.session_state import capture_session

        if path is None:
            path = Path("workspace/session_save.json")

        se_state = getattr(self._explore_ctrl, "_side_event_state", {})
        state = capture_session(
            play_state_str=self._play_state.value if hasattr(self._play_state, "value") else str(self._play_state),
            all_entities=self._all_entities,
            tile_dicts=self._tile_dicts,
            current_tile_pos=self._current_tile_pos,
            side_event_state=se_state,
            quest_tracker=getattr(self, "_quest_tracker", None),
        )
        state.save(path)
        self._log_msg(f"Session saved to {path.name}")

    def _log_msg(self, msg: str) -> None:
        if hasattr(self._log, "add_system_message"):
            self._log.add_system_message(msg, "explore")
        else:
            self._log.append(msg)

    # ------------------------------------------------------------------
    #  Quest tracking
    # ------------------------------------------------------------------

    def _on_quest_completed(self, quest) -> None:
        """Called when a quest's objectives are all met."""
        msg = f"Quest completed: {quest.title}!"
        if hasattr(self._log, "add_system_message"):
            self._log.add_system_message(msg, "explore")
        else:
            self._log.append(msg)
        # Apply rewards
        if quest.rewards.get("gold"):
            entity = self._explore_ctrl.get_active_character()
            if entity:
                entity.stats["gold"] = entity.stats.get("gold", 0) + quest.rewards["gold"]
                self._log.append(f"  Reward: {quest.rewards['gold']} gold")
        if quest.rewards.get("xp"):
            self._log.append(f"  Reward: {quest.rewards['xp']} XP")
        self._quest_panel.refresh_from_tracker(self._quest_tracker)

    def refresh_quest_state(self) -> None:
        """Re-check quest flags after NPC conversations or side events."""
        if not self._quest_tracker:
            return
        # Collect all dialogue flags from all entities
        flags: dict[str, bool] = {}
        for entity in self._all_entities:
            if hasattr(entity, "dialogue_flags"):
                flags.update(entity.dialogue_flags)
        self._quest_tracker.check_flags(flags)
        self._quest_panel.refresh_from_tracker(self._quest_tracker)

    def closeEvent(self, event) -> None:
        self._save_dock_state()
        self._persist_entity_state()
        try:
            self.save_session()
        except Exception:
            pass
        self._is_running = False
        self._play_state = PlayState.ENDED
        if self._animator:
            self._animator.cleanup()
            self._animator = None
        if self._ui_adapter:
            self._ui_adapter.cancel()
        super().closeEvent(event)

    def _persist_entity_state(self) -> None:
        """Write entity changes (inventory, gold, HP) back to tile dicts."""
        for entity in self._all_entities:
            pos = getattr(entity, "position", None)
            if not pos:
                continue
            td = self._tile_by_pos.get(pos)
            if not td:
                continue
            ename = getattr(entity, "name", "")
            for i, edict in enumerate(td.get("entities", [])):
                if edict.get("name") == ename:
                    td["entities"][i] = entity.to_dict()
                    break
