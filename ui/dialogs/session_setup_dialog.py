"""Session setup dialog — role and character selection before play."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton,
    QButtonGroup, QPushButton, QListWidget, QListWidgetItem,
    QGroupBox, QWidget,
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from core.engine.play_state import PlayerRole


class SessionSetupDialog(QDialog):
    """Pre-game setup: pick role and pick character.

    Usage::

        dialog = SessionSetupDialog(scenario_name, player_entities, parent)
        if dialog.exec_():
            role = dialog.selected_role
            character = dialog.selected_character  # None for DM/Spectator
    """

    def __init__(self, scenario_name: str, player_entities: list,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Session Setup — {scenario_name}")
        self.setMinimumSize(480, 380)

        self._player_entities = player_entities

        self.selected_role: PlayerRole = PlayerRole.PLAYER
        self.selected_character = None

        self._init_ui(scenario_name)

    def _init_ui(self, scenario_name: str) -> None:
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(scenario_name)
        title.setFont(QFont("Cinzel", 16))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Choose how you want to play")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: gray; margin-bottom: 12px;")
        layout.addWidget(subtitle)

        # Role selection
        role_group = QGroupBox("Your Role")
        role_layout = QVBoxLayout(role_group)

        self._role_buttons = QButtonGroup(self)
        roles = [
            (PlayerRole.PLAYER, "Player",
             "Control a character. AI handles the rest."),
            (PlayerRole.DM, "Dungeon Master",
             "See everything. Control the flow. Observe or actively manage NPCs."),
            (PlayerRole.SPECTATOR, "Spectator",
             "Watch AI control all characters. Great for testing encounters."),
        ]

        for i, (role, name, desc) in enumerate(roles):
            radio = QRadioButton(name)
            radio.setStyleSheet("font-weight: bold; font-size: 13px;")
            if i == 0:
                radio.setChecked(True)
            self._role_buttons.addButton(radio, i)
            role_layout.addWidget(radio)
            desc_label = QLabel(desc)
            desc_label.setStyleSheet(
                "color: gray; font-size: 11px; margin-left: 24px; margin-bottom: 6px;"
            )
            desc_label.setWordWrap(True)
            role_layout.addWidget(desc_label)

        self._role_buttons.buttonClicked.connect(self._on_role_changed)
        layout.addWidget(role_group)

        # Character selection (Player role only)
        self._char_group = QGroupBox("Choose Your Character")
        char_layout = QVBoxLayout(self._char_group)

        self._char_list = QListWidget()
        for entity in self._player_entities:
            hp = getattr(entity, "hp", "?")
            max_hp = getattr(entity, "max_hp", None) or "?"
            text = f"{entity.name}  (HP: {hp}/{max_hp})"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, entity)
            self._char_list.addItem(item)

        if self._char_list.count() > 0:
            self._char_list.setCurrentRow(0)

        char_layout.addWidget(self._char_list)
        layout.addWidget(self._char_group)

        # Begin button
        self._begin_btn = QPushButton("Begin Session")
        self._begin_btn.setStyleSheet(
            "font-size: 14px; padding: 10px; font-weight: bold;"
        )
        self._begin_btn.clicked.connect(self._on_begin)
        layout.addWidget(self._begin_btn)

    def _on_role_changed(self, button) -> None:
        idx = self._role_buttons.id(button)
        roles = [PlayerRole.PLAYER, PlayerRole.DM, PlayerRole.SPECTATOR]
        self.selected_role = roles[idx]
        self._char_group.setVisible(self.selected_role == PlayerRole.PLAYER)

    def _on_begin(self) -> None:
        if self.selected_role == PlayerRole.PLAYER:
            item = self._char_list.currentItem()
            if item:
                self.selected_character = item.data(Qt.UserRole)
        self.accept()
