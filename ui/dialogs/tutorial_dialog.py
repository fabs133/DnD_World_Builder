from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QCheckBox, QPushButton
from PyQt5.QtCore import Qt, QTimer


class TutorialDialog(QDialog):
    """
    A startup tutorial dialog shown on first launch (or until dismissed permanently).

    The user can check "Don't show again" to suppress future appearances.
    The setting is persisted via the SettingsManager passed in.
    """

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Welcome to DnD World Builder")
        self.setFixedWidth(500)
        # WA_DeleteOnClose removed — caused crash when dialog was moved
        # before clicking "Get Started" (segfault from deletion during
        # active mouse event processing)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        welcome = QLabel(
            "<h2>Welcome to DnD World Builder!</h2>"
            "<p>Here is a quick overview to get you started:</p>"
            "<ul>"
            "<li><b>Game Creation</b> — Build battle maps on a square or hex grid. "
            "Right-click any tile to set terrain, tags, a background image, "
            "ambient audio, and triggers.</li>"
            "<li><b>Tile Tags</b> — Assign properties such as <i>Blocks Movement</i>, "
            "<i>Blocks Vision</i>, <i>Trap Zone</i>, and <i>Start Zone</i>. "
            "Only one <i>Start Zone</i> is allowed per scenario.</li>"
            "<li><b>Triggers</b> — Open the Trigger Editor from a tile's dialog to "
            "build event chains visually. Connect triggers in sequence using the "
            "graph view.</li>"
            "<li><b>Character Creator</b> — Create D&amp;D 5e characters with "
            "auto-calculated saving throws, skill modifiers, and D&amp;D 5e "
            "standard conditions.</li>"
            "<li><b>Theme</b> — Switch between dark and light colour schemes from "
            "the launcher at any time.</li>"
            "</ul>"
            "<p><i>Tip: You can re-open this guide via <b>Help &rarr; Tutorial</b>.</i></p>"
        )
        welcome.setWordWrap(True)
        welcome.setTextFormat(Qt.RichText)
        layout.addWidget(welcome)

        self._no_show_cb = QCheckBox("Don't show this again on startup")
        layout.addWidget(self._no_show_cb)

        btn = QPushButton("Get Started")
        btn.setDefault(True)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

    def accept(self):
        if self._no_show_cb.isChecked():
            self.settings.set("show_tutorial", False)
        # Defer to next event loop tick — prevents crash if accept
        # fires during an active mouse move/drag event.
        QTimer.singleShot(0, lambda: super(TutorialDialog, self).accept())
