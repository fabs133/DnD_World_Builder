"""
Session Panel
=============

Dockable panel displayed during an active multiplayer session.  Shows
connection status, player list with claimed entities, a chat log with
input field, and a disconnect button.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QTextEdit,
    QLineEdit, QPushButton, QComboBox, QProgressBar,
)
from PyQt5.QtCore import Qt, pyqtSignal


class SessionPanel(QWidget):
    """Panel shown during an active multiplayer session.

    Displays connection status, a player list with claimed entities, a chat
    area (read-only log + input field), and a disconnect button.

    Signals:
        chat_submitted(str): Emitted when the user sends a chat message.
        disconnect_requested(): Emitted when the user clicks *Disconnect*.

    :param parent: Parent widget.
    """

    #: Emitted when the user sends a chat message (text).
    chat_submitted = pyqtSignal(str)
    #: Emitted when the user clicks the Disconnect button.
    disconnect_requested = pyqtSignal()
    #: Emitted when the user clicks Claim with a selected entity name.
    entity_claim_requested = pyqtSignal(str)
    #: Emitted when voice lines are ready to share over network.
    voice_lines_ready = pyqtSignal(dict)
    #: Emitted when user triggers a voice line from the soundboard.
    voice_line_play = pyqtSignal(str, str, str)  # player_name, cache_key, text

    def __init__(self, parent=None):
        super().__init__(parent)
        self._players = {}  # player_id -> (name, entity)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Status label
        self._status_label = QLabel("Not connected")
        self._status_label.setStyleSheet("font-weight: bold;")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        # Player list
        players_label = QLabel("Players:")
        players_label.setStyleSheet("font-size: 11px; color: gray;")
        layout.addWidget(players_label)

        self._player_list = QListWidget()
        self._player_list.setMaximumHeight(120)
        layout.addWidget(self._player_list)

        # Entity claim section
        claim_label = QLabel("Claim Entity:")
        claim_label.setStyleSheet("font-size: 11px; color: gray;")
        layout.addWidget(claim_label)

        claim_row = QHBoxLayout()
        self._entity_combo = QComboBox()
        self._entity_combo.setPlaceholderText("Select entity...")
        claim_row.addWidget(self._entity_combo)
        claim_btn = QPushButton("Claim")
        claim_btn.clicked.connect(self._on_claim_clicked)
        claim_row.addWidget(claim_btn)
        layout.addLayout(claim_row)

        # Chat area
        chat_label = QLabel("Chat:")
        chat_label.setStyleSheet("font-size: 11px; color: gray;")
        layout.addWidget(chat_label)

        self._chat_log = QTextEdit()
        self._chat_log.setReadOnly(True)
        layout.addWidget(self._chat_log)

        # Chat input
        chat_row = QHBoxLayout()
        self._chat_input = QLineEdit()
        self._chat_input.setPlaceholderText("Type a message...")
        self._chat_input.returnPressed.connect(self._send_chat)
        chat_row.addWidget(self._chat_input)

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self._send_chat)
        chat_row.addWidget(send_btn)
        layout.addLayout(chat_row)

        # Voice generation progress (hidden by default)
        self._voice_section = QWidget()
        voice_layout = QVBoxLayout(self._voice_section)
        voice_layout.setContentsMargins(0, 4, 0, 4)
        voice_label = QLabel("Voice Generation:")
        voice_label.setStyleSheet("font-size: 11px; color: gray;")
        voice_layout.addWidget(voice_label)
        self._voice_progress_bar = QProgressBar()
        self._voice_progress_bar.setFormat("%v/%m characters")
        self._voice_progress_bar.setFixedHeight(18)
        voice_layout.addWidget(self._voice_progress_bar)
        self._voice_status_label = QLabel("")
        self._voice_status_label.setStyleSheet("font-size: 10px; color: gray;")
        voice_layout.addWidget(self._voice_status_label)
        self._voice_section.hide()
        layout.addWidget(self._voice_section)

        # Voice setup button (visible only when Chatterbox is available)
        self._voice_setup_btn = QPushButton("Setup Voice")
        self._voice_setup_btn.setToolTip("Record your voice and create custom voice lines")
        self._voice_setup_btn.clicked.connect(self._on_voice_setup)
        self._voice_setup_btn.hide()  # shown after availability check
        layout.addWidget(self._voice_setup_btn)

        # Voice soundboard (populated after voice lines are shared)
        from network.ui.voice_soundboard_widget import VoiceSoundboardWidget
        self._soundboard = VoiceSoundboardWidget(parent=self)
        layout.addWidget(self._soundboard)

        # Disconnect button
        self._disconnect_btn = QPushButton("Disconnect")
        self._disconnect_btn.clicked.connect(self.disconnect_requested.emit)
        layout.addWidget(self._disconnect_btn)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_hosting(self, address: str):
        """Update the status label for host mode.

        :param address: The ``host:port`` string to display.
        :type address: str
        """
        self._status_label.setText(f"Hosting on {address}")

    def set_connected(self, session_id: str):
        """Update the status label for client mode.

        :param session_id: A session identifier to display.
        :type session_id: str
        """
        self._status_label.setText(f"Connected to session {session_id}")

    def add_player(self, player_id: str, name: str):
        """Add a player to the list.

        :param player_id: Unique player identifier.
        :type player_id: str
        :param name: Display name.
        :type name: str
        """
        self._players[player_id] = (name, None)
        self._rebuild_player_list()

    def remove_player(self, player_id: str):
        """Remove a player from the list.

        :param player_id: Unique player identifier.
        :type player_id: str
        """
        self._players.pop(player_id, None)
        self._rebuild_player_list()

    def set_entity_claim(self, entity_id: str, player_id: str):
        """Record that *player_id* has claimed *entity_id*.

        :param entity_id: The entity's unique identifier.
        :type entity_id: str
        :param player_id: The player who claimed it.
        :type player_id: str
        """
        if player_id in self._players:
            name = self._players[player_id][0]
            self._players[player_id] = (name, entity_id)
            self._rebuild_player_list()

    _MAX_CHAT_MESSAGES = 500

    def append_chat(self, sender: str, message: str):
        """Append a message to the chat log.

        :param sender: The display name of the sender.
        :type sender: str
        :param message: The chat text.
        :type message: str
        """
        self._chat_log.append(f"<b>{sender}:</b> {message}")
        # Trim oldest messages to prevent unbounded memory growth
        doc = self._chat_log.document()
        while doc.blockCount() > self._MAX_CHAT_MESSAGES:
            cursor = self._chat_log.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.select(cursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()  # remove the leftover newline

    def update_voice_progress(self, character_id: str, completed: int, total: int):
        """Update the voice generation progress display.

        :param character_id: Character being generated.
        :param completed: Lines completed.
        :param total: Total lines.
        """
        self._voice_section.show()
        self._voice_progress_bar.setMaximum(max(total, 1))
        self._voice_progress_bar.setValue(completed)
        self._voice_status_label.setText(f"Generating: {character_id} ({completed}/{total})")

    def set_voice_complete(self):
        """Mark voice generation as complete."""
        self._voice_status_label.setText("Voice generation complete")
        self._voice_progress_bar.setValue(self._voice_progress_bar.maximum())

    def set_available_entities(self, entities: list):
        """Populate the entity claim dropdown.

        :param entities: List of entity dicts (with ``name`` key) or strings.
        :type entities: list
        """
        self._entity_combo.clear()
        for entity in entities:
            if isinstance(entity, dict):
                name = entity.get("name", str(entity))
            else:
                name = str(entity)
            self._entity_combo.addItem(name)

    def clear(self):
        """Reset the panel to its initial state."""
        self._players.clear()
        self._player_list.clear()
        self._chat_log.clear()
        self._chat_input.clear()
        self._entity_combo.clear()
        self._voice_section.hide()
        self._voice_progress_bar.setValue(0)
        self._voice_status_label.setText("")
        self._status_label.setText("Not connected")

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _rebuild_player_list(self):
        self._player_list.clear()
        for pid, (name, entity) in self._players.items():
            text = name
            if entity:
                text += f"  [{entity}]"
            item = QListWidgetItem(text)
            self._player_list.addItem(item)

    def _on_claim_clicked(self):
        entity_name = self._entity_combo.currentText()
        if entity_name:
            self.entity_claim_requested.emit(entity_name)

    def _send_chat(self):
        text = self._chat_input.text().strip()
        if text:
            self.chat_submitted.emit(text)
            self._chat_input.clear()

    # ------------------------------------------------------------------
    # Voice line system
    # ------------------------------------------------------------------

    def enable_voice_setup(self, player_name: str = "Player") -> None:
        """Show the Setup Voice button (call after confirming Chatterbox available)."""
        self._player_name = player_name
        self._voice_setup_btn.show()
        self._soundboard.set_own_name(player_name)
        self._soundboard.voice_line_triggered.connect(
            lambda pn, ck, t: self.voice_line_play.emit(pn, ck, t))

    def _on_voice_setup(self) -> None:
        """Open the player voice setup dialog."""
        from ui.voice.player_voice_setup_dialog import PlayerVoiceSetupDialog
        name = getattr(self, "_player_name", "Player")
        dlg = PlayerVoiceSetupDialog(player_name=name, parent=self)
        dlg.voice_lines_ready.connect(self._on_voice_lines_ready)
        dlg.exec_()

    def _on_voice_lines_ready(self, data: dict) -> None:
        """Handle locally generated voice lines — update soundboard and share."""
        player_name = data.get("player_name", "Player")
        lines = data.get("lines", [])

        # Add to local soundboard
        self._soundboard.add_player_lines(player_name, lines)

        # Forward to network layer
        self.voice_lines_ready.emit(data)

    def add_remote_voice_lines(self, player_name: str, lines: list[dict]) -> None:
        """Add voice lines received from another player to the soundboard."""
        self._soundboard.add_player_lines(player_name, lines)
