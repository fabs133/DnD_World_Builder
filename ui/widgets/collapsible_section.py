"""Collapsible section widget — clickable header that toggles content visibility."""

from __future__ import annotations

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QSizePolicy
from PyQt5.QtCore import Qt


class CollapsibleSection(QWidget):
    """A section with a clickable header that collapses/expands its content.

    Args:
        title: Header text.
        content_widget: The widget to show/hide.
        initially_open: Whether the section starts expanded.
    """

    def __init__(self, title: str, content_widget: QWidget,
                 initially_open: bool = True, parent: QWidget | None = None):
        super().__init__(parent)
        self._content = content_widget
        self._title = title
        self._open = initially_open

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header button — styled via themeRole, no hardcoded colors
        self._header = QPushButton(self._header_text())
        self._header.setProperty("themeRole", "ghost")
        self._header.clicked.connect(self.toggle)
        layout.addWidget(self._header)

        # Content
        layout.addWidget(self._content)
        self._content.setVisible(self._open)

    def _header_text(self) -> str:
        arrow = "\u25bc" if self._open else "\u25b6"
        return f"{arrow} {self._title}"

    def toggle(self) -> None:
        """Toggle the section open/closed."""
        self._open = not self._open
        self._content.setVisible(self._open)
        self._header.setText(self._header_text())

    def set_open(self, open_: bool) -> None:
        """Programmatically set the section state."""
        if self._open != open_:
            self.toggle()

    def set_title(self, title: str) -> None:
        """Change the section header text dynamically."""
        self._title = title
        self._header.setText(self._header_text())

    @property
    def is_open(self) -> bool:
        return self._open
