"""
Join Dialog
===========

Dialog that lets a player enter host address, port, and player name to
connect to a hosted multiplayer session.
"""

from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QSpinBox,
    QDialogButtonBox,
)


class JoinDialog(QDialog):
    """Dialog for connecting to a remote multiplayer session.

    :param settings: Optional :class:`~core.settings_manager.SettingsManager`
        used to pre-fill host, port, and player name from saved preferences.
    :param parent: Parent widget.
    """

    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Join Session")
        self.setMinimumWidth(320)

        layout = QFormLayout(self)

        # Host address
        self._host_input = QLineEdit()
        self._host_input.setPlaceholderText("192.168.1.x")
        if settings:
            last_host = settings.get("multiplayer_last_host", "")
            if last_host:
                self._host_input.setText(last_host)
        layout.addRow("Host Address:", self._host_input)

        # Port
        self._port_spin = QSpinBox()
        self._port_spin.setRange(1024, 65535)
        default_port = 8765
        if settings:
            default_port = settings.get("multiplayer_default_port", 8765)
        self._port_spin.setValue(default_port)
        layout.addRow("Port:", self._port_spin)

        # Player name
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Your Name")
        if settings:
            name = settings.get("multiplayer_player_name", "")
            if name:
                self._name_input.setText(name)
        layout.addRow("Player Name:", self._name_input)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Connect")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    @property
    def host(self) -> str:
        """The host address entered by the user."""
        return self._host_input.text().strip()

    @property
    def port(self) -> int:
        """The port number selected by the user."""
        return self._port_spin.value()

    @property
    def player_name(self) -> str:
        """The player name entered by the user (defaults to ``"Player"``)."""
        return self._name_input.text().strip() or "Player"
