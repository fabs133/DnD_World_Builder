import sys
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QComboBox, QLabel,
    QFileDialog, QMessageBox,
)
from PyQt5.QtCore import Qt
from core.gameCreation.main_controller import MainController
from core.characterCreation.character_gui import CharacterCreationWindow
from core.settings_manager import SettingsManager
from core.theme_engine import ThemeEngine, ThemeMode


# Map user-friendly names to ThemeMode
THEME_MAP = {
    "Adventurer's Tome": ThemeMode.TOME,
    "Dungeon Stone": ThemeMode.STONE,
}


class LaunchDialog(QWidget):
    def __init__(self, settings, theme_engine):
        super().__init__()
        self.setWindowFlags(
            Qt.Window | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint
        )
        self.settings = settings
        self.theme_engine = theme_engine
        self.setWindowTitle("DnD Project - Launcher")
        self.setMinimumSize(340, 520)
        self.init_ui()

    def init_ui(self):
        from core.icon_provider import themed_icon
        from ui.widgets.ornamental_divider import OrnamentalDivider

        layout = QVBoxLayout()
        self.setLayout(layout)

        play_button = QPushButton("  Play Scenario")
        play_button.setIcon(themed_icon("play"))
        play_button.setProperty("themeRole", "primary")
        play_button.clicked.connect(self.launch_play_session)
        layout.addWidget(play_button)

        layout.addSpacing(6)

        game_button = QPushButton("  Open Game Creation")
        game_button.setIcon(themed_icon("map"))
        game_button.clicked.connect(self.launch_game_creation)
        layout.addWidget(game_button)

        character_button = QPushButton("  Open Character Creator")
        character_button.setIcon(themed_icon("person"))
        character_button.clicked.connect(self.launch_character_creator)
        layout.addWidget(character_button)

        layout.addWidget(OrnamentalDivider())

        mp_label = QLabel("Multiplayer")
        mp_label.setProperty("themeRole", "section-title")
        layout.addWidget(mp_label)

        host_button = QPushButton("  Host Multiplayer Session")
        host_button.setIcon(themed_icon("host"))
        host_button.clicked.connect(self.launch_host_session)
        layout.addWidget(host_button)

        join_button = QPushButton("  Join Multiplayer Session")
        join_button.setIcon(themed_icon("join"))
        join_button.clicked.connect(self.launch_join_session)
        layout.addWidget(join_button)

        layout.addWidget(OrnamentalDivider())

        theme_label = QLabel("Theme")
        theme_label.setProperty("themeRole", "section-title")
        layout.addWidget(theme_label)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEME_MAP.keys())

        # Select the currently saved theme
        current = self.settings.get("ui_theme", "tome")
        for name, mode in THEME_MAP.items():
            if mode.value == current:
                self.theme_combo.setCurrentText(name)
                break

        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        layout.addWidget(self.theme_combo)

        # Extensions section
        ext_label = QLabel("Extensions")
        ext_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 8px;")
        layout.addWidget(ext_label)

        from ui.extensions_panel import ChatterboxExtensionCard
        self._voice_card = ChatterboxExtensionCard()
        layout.addWidget(self._voice_card)

    def _on_theme_changed(self, theme_name):
        mode = THEME_MAP.get(theme_name, ThemeMode.TOME)
        self.theme_engine.swap_to(mode)

    def launch_play_session(self):
        """Open a scenario for play."""
        from ui.dialogs.scenario_picker_dialog import ScenarioPickerDialog
        picker = ScenarioPickerDialog(Path("workspace"), parent=self)
        if picker.exec_() != ScenarioPickerDialog.Accepted:
            return
        map_path = picker.selected_map_path()
        if map_path:
            self._play_map(map_path, picker.selected_meta())

    def _play_map(self, map_path: Path, meta: dict | None = None):
        try:
            with open(map_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            tiles = data.get("tiles", [])
            if not tiles:
                QMessageBox.warning(self, "Play", "No tiles found in scenario.")
                return

            if meta is None:
                meta = data.get("meta", {})
            scenario_name = meta.get("map_name", map_path.parent.name)

            # Extract entities for setup dialog
            from core.engine.play_session import extract_entities_from_tiles
            all_entities, _ = extract_entities_from_tiles(tiles)
            players = [e for e in all_entities if e.entity_type == "player"]

            # Show setup dialog
            from ui.dialogs.session_setup_dialog import SessionSetupDialog
            setup = SessionSetupDialog(scenario_name, players, parent=self)
            if not setup.exec_():
                return

            from ui.dialogs.play_session_dialog import PlaySessionDialog
            dlg = PlaySessionDialog(
                tiles, scenario_name=scenario_name,
                role=setup.selected_role,
                selected_character=setup.selected_character,
                meta=meta,
                quests=data.get("quests", []),
                parent=self,
            )
            dlg.exec_()
        except Exception as exc:
            QMessageBox.critical(self, "Play Error", str(exc))

    def launch_game_creation(self):
        self.main_controller = MainController()
        self.main_controller.show()
        self.close()

    def launch_character_creator(self):
        self.char_window = CharacterCreationWindow()
        self.char_window.show()
        self.close()

    def launch_host_session(self):
        """Host a multiplayer session using the play view (not the map editor).

        Uses the same fast PlaySessionDialog as single-player, but
        starts a multiplayer session manager alongside it. This avoids
        the 25+ second map-editor load for large scenarios.
        """
        from ui.dialogs.scenario_picker_dialog import ScenarioPickerDialog
        picker = ScenarioPickerDialog(Path("workspace"), parent=self)
        if picker.exec_() != ScenarioPickerDialog.Accepted:
            return
        map_path = picker.selected_map_path()
        if not map_path:
            return

        # Ask for port
        from PyQt5.QtWidgets import QInputDialog
        port_default = self.settings.get("multiplayer_default_port", 8765)
        port, ok = QInputDialog.getInt(
            self, "Host Session", "Port:", port_default, 1024, 65535)
        if not ok:
            return

        self._host_play_map(map_path, picker.selected_meta(), port)

    def _host_play_map(self, map_path: Path, meta: dict | None, port: int):
        """Open play session with a WebSocket server running alongside."""
        try:
            with open(map_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            tiles = data.get("tiles", [])
            if not tiles:
                QMessageBox.warning(self, "Play", "No tiles found in scenario.")
                return

            if meta is None:
                meta = data.get("meta", {})
            scenario_name = meta.get("map_name", map_path.parent.name)

            # Build a Gamemaster with a World from tile data for the session
            from models.game_master import Gamemaster
            from models.world.world import World
            from core.engine.play_session import extract_entities_from_tiles
            all_entities, _ = extract_entities_from_tiles(tiles)

            # Determine grid dimensions from the tile data
            max_row = max((t.get("position", [0, 0])[0] for t in tiles), default=0) + 1
            max_col = max((t.get("position", [0, 0])[1] for t in tiles), default=0) + 1
            grid_type = meta.get("grid_type", "square")

            gm = Gamemaster()
            gm.world = World(
                world_version=1,
                width=max_col,
                height=max_row,
                tile_type=grid_type,
                description=scenario_name,
                map_data={},
                time_of_day="",
                weather_conditions="",
            )
            gm.world_tile_manager = gm.world.tile_manager

            for entity in all_entities:
                gm.add_entity(entity)
                pos = getattr(entity, "position", None)
                if pos:
                    try:
                        gm.world_tile_manager.place_entity(entity, pos[0], pos[1])
                    except Exception:
                        pass

            # Start multiplayer session manager
            from network.session_manager import SessionManager
            session_mgr = SessionManager(gamemaster=gm, settings=self.settings)
            session_mgr.host(port)
            join_addr = session_mgr.join_address or f"localhost:{port}"

            from core.engine.play_state import PlayerRole
            from ui.dialogs.play_session_dialog import PlaySessionDialog
            dlg = PlaySessionDialog(
                tiles, scenario_name=scenario_name,
                role=PlayerRole.DM,
                selected_character=None,
                meta=meta,
                quests=data.get("quests", []),
                parent=self,
            )
            # Wire multiplayer signals
            dlg.connect_session_manager(session_mgr)
            dlg.setWindowTitle(
                f"Hosting: {scenario_name} — {join_addr}")

            dlg.exec_()

            # Cleanup on close
            session_mgr.stop_hosting()

        except Exception as exc:
            QMessageBox.critical(self, "Host Error", str(exc))

    def launch_join_session(self):
        self.main_controller = MainController()
        if self.main_controller.map_editor is None:
            self.main_controller.start_new_map()
        self.main_controller.show()
        self.main_controller.map_editor._join_session()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Register bundled fonts (Cinzel display font for fantasy headings)
    from PyQt5.QtGui import QFontDatabase
    from pathlib import Path as _Path
    for _font_file in (_Path(__file__).parent / "assets" / "fonts").glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(_font_file))

    settings = SettingsManager()
    engine = ThemeEngine(settings)

    saved = settings.get("ui_theme", "tome")
    mode = ThemeMode.STONE if saved == "stone" else ThemeMode.TOME
    engine.apply(app, mode)

    # Initialize ViewDispatcher (central non-blocking effect router)
    from core.view_dispatcher import ViewDispatcher, EffectType
    view_dispatcher = ViewDispatcher(parent=app)
    ViewDispatcher._instance = view_dispatcher

    # Register audio worker on a persistent dedicated thread
    from core.audio.audio_worker import AudioWorker
    audio_worker = AudioWorker()
    view_dispatcher.register_worker(EffectType.AUDIO, audio_worker, threaded=True)

    # Initialize asset cache (LRU pixmap cache with background loading)
    from core.asset_cache import AssetCache
    asset_cache = AssetCache(parent=app)
    AssetCache._instance = asset_cache

    # Initialize sound system (AudioMixer is now a thin facade over ViewDispatcher)
    from core.audio.audio_mixer import AudioMixer
    audio_mixer = AudioMixer(parent=app)
    AudioMixer._instance = audio_mixer

    from core.audio.ui_sound_manager import UISoundManager
    sound_mgr = UISoundManager(settings_manager=settings)
    UISoundManager._instance = sound_mgr
    sound_mgr.set_theme(mode.value)

    from core.audio.sound_event_bridge import SoundEventBridge
    sound_bridge = SoundEventBridge(sound_manager=sound_mgr, viewer_entity_name="")
    SoundEventBridge._instance = sound_bridge
    sound_bridge.start()

    def _cleanup_sound():
        sound_bridge.stop()
        audio_mixer.stop_all()
        view_dispatcher.shutdown()
    app.aboutToQuit.connect(_cleanup_sound)

    launcher = LaunchDialog(settings, engine)
    launcher.show()

    # Voice model loads lazily on first use — no preloading needed.
    # Heavy torch imports block the GIL and freeze the UI even in a thread.

    if settings.get("show_tutorial", True):
        from ui.dialogs.tutorial_dialog import TutorialDialog
        TutorialDialog(settings, launcher).exec_()

    sys.exit(app.exec_())
