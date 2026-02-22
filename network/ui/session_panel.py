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
    QLineEdit, QPushButton,
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

    def append_chat(self, sender: str, message: str):
        """Append a message to the chat log.

        :param sender: The display name of the sender.
        :type sender: str
        :param message: The chat text.
        :type message: str
        """
        self._chat_log.append(f"<b>{sender}:</b> {message}")

    def clear(self):
        """Reset the panel to its initial state."""
        self._players.clear()
        self._player_list.clear()
        self._chat_log.clear()
        self._chat_input.clear()
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

    def _send_chat(self):
        text = self._chat_input.text().strip()
        if text:
            self.chat_submitted.emit(text)
            self._chat_input.clear()
