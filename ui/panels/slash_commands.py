"""Slash command engine for the Quick Search panel.

Pure Python — no Qt dependency. Parses ``/command args`` input,
provides tab-completion suggestions, and dispatches to registered handlers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class SlashCommand:
    """A registered slash command."""
    name: str
    description: str
    handler: Callable[[str], str | None]  # receives args string, returns status msg
    arg_hint: str = ""                     # e.g. "row,col" or "<text>"


class SlashCommandEngine:
    """Registry and dispatcher for ``/`` prefixed commands."""

    def __init__(self):
        self._commands: dict[str, SlashCommand] = {}

    def register(
        self,
        name: str,
        description: str,
        handler: Callable[[str], str | None],
        arg_hint: str = "",
    ) -> None:
        self._commands[name.lower()] = SlashCommand(
            name=name.lower(),
            description=description,
            handler=handler,
            arg_hint=arg_hint,
        )

    def parse(self, text: str) -> tuple[str, str] | None:
        """Parse ``/command args`` text. Returns (command, args) or None."""
        text = text.strip()
        if not text.startswith("/"):
            return None
        parts = text[1:].split(None, 1)
        if not parts:
            return None
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        if cmd in self._commands:
            return (cmd, args)
        return None

    def get_completions(self, partial: str) -> list[SlashCommand]:
        """Return commands matching the partial input (after ``/``)."""
        partial = partial.lstrip("/").lower()
        if not partial:
            return list(self._commands.values())
        return [
            cmd for name, cmd in self._commands.items()
            if name.startswith(partial)
        ]

    def execute(self, text: str) -> str | None:
        """Parse and execute a slash command. Returns status message or None."""
        parsed = self.parse(text)
        if not parsed:
            return f"Unknown command: {text}"
        cmd_name, args = parsed
        cmd = self._commands[cmd_name]
        try:
            return cmd.handler(args)
        except Exception as e:
            return f"Error: {e}"

    @property
    def commands(self) -> dict[str, SlashCommand]:
        return dict(self._commands)
