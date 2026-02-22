"""
Host Dialog
===========

Dialog that lets the DM choose a port and start hosting a multiplayer session.
Displays the machine's LAN IP address so players know where to connect.
"""

import socket

from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QSpinBox, QLabel,
    QDialogButtonBox,
)


def _get_local_ip() -> str:
    """Detect this machine's LAN IP via a UDP probe to ``8.8.8.8``.

    :return: The local IP address, or ``"127.0.0.1"`` on failure.
    :rtype: str
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class HostDialog(QDialog):
    """Dialog for configuring and starting a hosted multiplayer session.

    :param settings: Optional :class:`~core.settings_manager.SettingsManager`
        used to pre-fill the default port.
    :param parent: Parent widget.
    """

    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Host Session")
        self.setMinimumWidth(320)

        layout = QFormLayout(self)

        # Port
        self._port_spin = QSpinBox()
        self._port_spin.setRange(1024, 65535)
        default_port = 8765
        if settings:
            default_port = settings.get("multiplayer_default_port", 8765)
        self._port_spin.setValue(default_port)
        layout.addRow("Port:", self._port_spin)

        # Local IP display
        ip_label = QLabel(_get_local_ip())
        ip_label.setStyleSheet("color: gray;")
        layout.addRow("Your IP:", ip_label)

        info = QLabel("Players will connect to your IP and port above.")
        info.setStyleSheet("color: gray; font-style: italic;")
        info.setWordWrap(True)
        layout.addRow(info)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Start Hosting")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    @property
    def port(self) -> int:
        """The port number selected by the user."""
        return self._port_spin.value()
