"""RPG-style conversation dialog for NPC interaction with voice playback."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QWidget, QSizePolicy,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Map dialogue categories to player-facing choice labels
_CHOICE_LABELS = {
    "lore":     "Tell me about this place.",
    "quest":    "Do you have any work for me?",
    "trade":    "What do you have for sale?",
    "combat":   "I'm looking for a fight.",
    "search":   "Let me take a closer look.",
    "farewell": None,  # handled specially
}


class _VoiceGenWorker(QThread):
    """Background thread for on-the-fly voice generation."""

    finished = pyqtSignal(str, bytes)
    failed = pyqtSignal(str)

    def __init__(self, engine, text, profile, ref_path, cache_key):
        super().__init__()
        self._engine = engine
        self._text = text
        self._profile = profile
        self._ref_path = ref_path
        self._cache_key = cache_key

    def run(self):
        try:
            result = self._engine.generate(self._text, self._profile, self._ref_path)
            if result:
                self.finished.emit(self._cache_key, result)
            else:
                self.failed.emit(self._cache_key)
        except Exception:
            self.failed.emit(self._cache_key)


class NpcConversationDialog(QDialog):
    """RPG-style dialogue with clickable choices and voice playback.

    Signals:
        conversation_ended(): Dialog closed.
    """

    conversation_ended = pyqtSignal()

    def __init__(
        self,
        entity: Any,
        zone_context: dict | None = None,
        ai_adapter: Any = None,
        voice_engine: Any = None,
        voice_cache: Any = None,
        parent=None,
    ):
        super().__init__(parent)
        self._entity = entity
        self._zone_context = zone_context or {}
        self._ai_adapter = ai_adapter
        self._voice_engine = voice_engine
        self._voice_cache = voice_cache
        self._pending_cache_key: str = ""
        self._gen_workers: list[_VoiceGenWorker] = []  # prevent GC while running
        self._subscribed = False

        # Track which line index we're on per category
        self._line_index: dict[str, int] = {}

        entity_name = getattr(entity, "name", "NPC")
        self.setWindowTitle(f"Talking to {entity_name}")
        self.resize(500, 450)

        layout = QVBoxLayout(self)

        # Chat history
        self._chat_log = QTextEdit()
        self._chat_log.setReadOnly(True)
        self._chat_log.setStyleSheet("font-size: 13px;")
        layout.addWidget(self._chat_log, stretch=3)

        # Voice status indicator
        self._voice_status = QLabel("")
        self._voice_status.setStyleSheet("color: #888; font-style: italic;")
        self._voice_status.hide()
        layout.addWidget(self._voice_status)

        # Choice buttons area
        self._choices_widget = QWidget()
        self._choices_layout = QVBoxLayout(self._choices_widget)
        self._choices_layout.setContentsMargins(4, 4, 4, 4)
        self._choices_layout.setSpacing(4)
        layout.addWidget(self._choices_widget, stretch=1)

        # Subscribe to voice events
        try:
            from core.gameCreation.event_bus import EventBus
            from core.events import VOICE_LINE_READY
            EventBus.subscribe(VOICE_LINE_READY, self._on_voice_ready)
            self._subscribed = True
        except Exception:
            pass

        # Start conversation with greeting (delay voice so Qt media player is ready)
        from PyQt5.QtCore import QTimer
        self._show_greeting_text()
        QTimer.singleShot(500, self._play_greeting_voice)

    # ─── Dialogue flow ──────────────────────────────────────────

    def _get_dialogue(self) -> dict[str, list[str]]:
        return getattr(self._entity, "dialogue_lines", {})

    def _show_greeting_text(self) -> None:
        """Show first NPC greeting and choices (no voice yet)."""
        dialogue = self._get_dialogue()
        greetings = dialogue.get("greeting", ["Greetings, traveler."])
        self._greeting_line = greetings[0] if greetings else "Greetings, traveler."
        name = getattr(self._entity, "name", "NPC")
        self._chat_log.append(
            f'<div style="margin: 4px 0;">'
            f'<b style="color: #e8c840;">{name}:</b> {self._greeting_line}</div>'
        )
        self._show_choices()

    def _play_greeting_voice(self) -> None:
        """Play the greeting voice line after dialog is visible."""
        if self._greeting_line:
            self._play_voice_line(self._greeting_line)

    def _show_choices(self) -> None:
        """Build choice buttons from available dialogue categories."""
        # Clear old choices
        while self._choices_layout.count():
            item = self._choices_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        dialogue = self._get_dialogue()

        # Add category choices
        for category, label in _CHOICE_LABELS.items():
            if category == "farewell":
                continue  # added separately at the end
            lines = dialogue.get(category, [])
            if not lines:
                continue
            # Check if there are unread lines
            idx = self._line_index.get(category, 0)
            if idx >= len(lines):
                # All lines exhausted — show greyed out
                btn = QPushButton(f"  {label}  (nothing new)")
                btn.setEnabled(False)
                btn.setStyleSheet("text-align: left; padding: 6px; color: #888;")
            else:
                btn = QPushButton(f"  {label}")
                btn.setStyleSheet(
                    "text-align: left; padding: 6px; font-size: 12px; "
                    "background: #2a2a3a; color: #ddd; border: 1px solid #555; "
                    "border-radius: 4px;"
                )
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda checked, c=category: self._on_choice(c))
            self._choices_layout.addWidget(btn)

        # Always add farewell
        farewell_btn = QPushButton("  Goodbye.")
        farewell_btn.setStyleSheet(
            "text-align: left; padding: 6px; font-size: 12px; "
            "background: #3a2a2a; color: #ddd; border: 1px solid #555; "
            "border-radius: 4px;"
        )
        farewell_btn.setCursor(Qt.PointingHandCursor)
        farewell_btn.clicked.connect(self._on_farewell)
        self._choices_layout.addWidget(farewell_btn)

        # Push buttons to top
        self._choices_layout.addStretch()

    def _on_choice(self, category: str) -> None:
        """Player picked a dialogue category."""
        dialogue = self._get_dialogue()
        lines = dialogue.get(category, [])
        idx = self._line_index.get(category, 0)

        if idx >= len(lines):
            return

        # Show player's choice text
        label = _CHOICE_LABELS.get(category, category.title())
        self._add_player_message(label)

        # Deliver NPC lines one at a time (show next unread line)
        self._add_npc_message(lines[idx])
        self._line_index[category] = idx + 1

        # If there are more lines in this category, offer "Tell me more" + other choices
        self._show_choices()

        # Auto-scroll to bottom
        scrollbar = self._chat_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_farewell(self) -> None:
        """Player says goodbye."""
        self._add_player_message("Goodbye.")
        dialogue = self._get_dialogue()
        farewells = dialogue.get("farewell", [])
        if farewells:
            import random
            self._add_npc_message(random.choice(farewells))
        else:
            self._add_npc_message("Farewell, traveler.")
        self._on_close()

    def _cleanup_worker(self, worker: _VoiceGenWorker) -> None:
        """Remove finished worker from the list."""
        if worker in self._gen_workers:
            self._gen_workers.remove(worker)

    def _on_close(self) -> None:
        if self._subscribed:
            try:
                from core.gameCreation.event_bus import EventBus
                from core.events import VOICE_LINE_READY
                EventBus.unsubscribe(VOICE_LINE_READY, self._on_voice_ready)
            except Exception:
                pass
        # Wait for any running workers before closing
        for worker in self._gen_workers:
            if worker.isRunning():
                worker.wait(2000)
        self._gen_workers.clear()
        self.conversation_ended.emit()
        self.accept()

    # ─── Chat log ───────────────────────────────────────────────

    def _add_npc_message(self, text: str) -> None:
        name = getattr(self._entity, "name", "NPC")
        self._chat_log.append(
            f'<div style="margin: 4px 0;">'
            f'<b style="color: #e8c840;">{name}:</b> {text}</div>'
        )
        self._play_voice_line(text)

    def _add_player_message(self, text: str) -> None:
        self._chat_log.append(
            f'<div style="margin: 4px 0; text-align: right;">'
            f'<b style="color: #6090d0;">You:</b> <i>{text}</i></div>'
        )

    # ─── Voice playback ─────────────────────────────────────────

    def _get_voice_profile(self):
        profile = getattr(self._entity, "voice_profile", None)
        if profile is None:
            return None
        if hasattr(profile, "is_voiced") and not profile.is_voiced:
            return None
        return profile

    def _play_voice_line(self, text: str) -> None:
        # 1. Check pre-generated files first (no profile needed)
        voice_dir = getattr(self._entity, "voice_lines_dir", None)
        if voice_dir:
            wav_path = self._find_voice_file(voice_dir, text)
            if wav_path:
                self._play_audio(wav_path)
                return

        # 2. Need a voice profile for cache/on-the-fly
        profile = self._get_voice_profile()
        if not profile:
            return

        from core.voice.voice_cache import VoiceCache
        cache_key = VoiceCache.compute_cache_key(
            profile.voice_id, text,
            profile.exaggeration, profile.speed_factor, profile.cfg_weight,
        )

        # 3. Check runtime cache
        if self._voice_cache:
            cached = self._voice_cache.get(cache_key)
            if cached:
                self._play_audio(Path(cached))
                return

        # 4. Generate on-the-fly (only if engine passed)
        if self._voice_engine:
            self._pending_cache_key = cache_key
            self._voice_status.setText("Generating voice...")
            self._voice_status.show()

            ref_path = None
            if profile.reference_audio:
                ref_path = Path(profile.reference_audio)
                if not ref_path.is_absolute():
                    ref_path = _PROJECT_ROOT / ref_path
                if not ref_path.exists():
                    ref_path = None

            worker = _VoiceGenWorker(
                self._voice_engine, text, profile, ref_path, cache_key,
            )
            worker.finished.connect(self._on_gen_finished)
            worker.failed.connect(self._on_gen_failed)
            worker.finished.connect(lambda *_: self._cleanup_worker(worker))
            worker.failed.connect(lambda *_: self._cleanup_worker(worker))
            self._gen_workers.append(worker)
            worker.start()

    def _find_voice_file(self, voice_dir: str, text: str) -> Path | None:
        manifest_path = _PROJECT_ROOT / voice_dir / "manifest.json"
        if not manifest_path.exists():
            return None
        try:
            import json
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for key, entry in manifest.get("lines", {}).items():
                if entry.get("text") == text and entry.get("exists", False):
                    wav = _PROJECT_ROOT / voice_dir / entry["file"]
                    if wav.exists():
                        return wav
        except Exception:
            pass
        return None

    def _on_gen_finished(self, cache_key: str, audio_data: bytes) -> None:
        self._voice_status.hide()
        if cache_key != self._pending_cache_key:
            return
        if self._voice_cache:
            entity_name = getattr(self._entity, "name", "NPC")
            self._voice_cache.put(cache_key, audio_data, entity_name, "")
        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".wav"))
        tmp.write_bytes(audio_data)
        self._play_audio(tmp)

    def _on_gen_failed(self, cache_key: str) -> None:
        self._voice_status.setText("Voice generation failed")

    def _on_voice_ready(self, data: dict) -> None:
        entity_name = getattr(self._entity, "name", "")
        if data.get("entity_name") != entity_name:
            return
        if data.get("cache_key") != self._pending_cache_key:
            return
        if self._voice_cache:
            cached = self._voice_cache.get(data["cache_key"])
            if cached:
                self._voice_status.hide()
                self._play_audio(Path(cached))

    def _play_audio(self, path: Path) -> None:
        try:
            from core.audio_player import AudioPlayer
            from core.audio.audio_mixer import AudioChannel
            AudioPlayer.instance().play(str(path.resolve()), channel=AudioChannel.VOICE)
        except Exception:
            pass
