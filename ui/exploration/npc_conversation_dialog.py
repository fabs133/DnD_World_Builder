"""RPG-style conversation dialog with branching dialogue graph and voice playback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
    QTextEdit, QWidget,
)
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal

from models.dialogue.dialogue_graph import DialogueGraph, DialogueNode

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_BTN_STYLE = (
    "text-align: left; padding: 8px 12px; font-size: 12px; "
    "background: #2a2a3a; color: #ddd; border: 1px solid #555; "
    "border-radius: 4px;"
)
_BTN_STYLE_FAREWELL = (
    "text-align: left; padding: 8px 12px; font-size: 12px; "
    "background: #3a2a2a; color: #ddd; border: 1px solid #555; "
    "border-radius: 4px;"
)
_BTN_STYLE_DISABLED = "text-align: left; padding: 8px 12px; color: #666;"


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
    """Branching dialogue with voice playback.

    Walks a :class:`DialogueGraph`, showing NPC text and available
    player response options at each node.  Supports flag-based
    conditions for dynamic option visibility.
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
        self._gen_workers: list[_VoiceGenWorker] = []
        self._subscribed = False

        # ── Graph state ──────────────────────────────────────────
        self._graph: DialogueGraph | None = getattr(entity, "dialogue_graph", None)
        self._current_node_id: str = ""
        self._flags: dict[str, bool] = dict(getattr(entity, "dialogue_flags", {}))
        self._visited_nodes: set[str] = set()

        # ── UI ───────────────────────────────────────────────────
        entity_name = getattr(entity, "name", "NPC")
        self.setWindowTitle(f"Talking to {entity_name}")
        self.resize(500, 500)

        layout = QVBoxLayout(self)

        self._chat_log = QTextEdit()
        self._chat_log.setReadOnly(True)
        self._chat_log.setStyleSheet("font-size: 13px;")
        layout.addWidget(self._chat_log, stretch=3)

        self._voice_status = QLabel("")
        self._voice_status.setStyleSheet("color: #888; font-style: italic;")
        self._voice_status.hide()
        layout.addWidget(self._voice_status)

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

        # Start conversation
        if self._graph:
            QTimer.singleShot(100, self._start_graph_conversation)
        else:
            # No graph at all — show a simple fallback
            self._add_npc_message("...")

    # ── Graph navigation ─────────────────────────────────────────

    def _start_graph_conversation(self) -> None:
        """Enter the graph's entry node."""
        self._navigate_to(self._graph.entry_node)

    def _navigate_to(self, node_id: str) -> None:
        """Move to a node: show NPC text, play voice, build options."""
        node = self._graph.get_node(node_id) if self._graph else None
        if node is None:
            return

        self._current_node_id = node_id
        self._visited_nodes.add(node_id)

        # Apply node-level flags
        self._flags.update(node.set_flags)

        # Show NPC text
        self._add_npc_message(node.text, node_id=node_id)

        if node.is_terminal:
            # Auto-close after a reading delay (scaled by text length)
            read_ms = max(2500, len(node.text) * 50)  # ~50ms per char, min 2.5s
            QTimer.singleShot(read_ms, self._on_close)
            return

        # Build option buttons
        self._build_options(node)

    def _build_options(self, node: DialogueNode) -> None:
        """Create choice buttons for the current node."""
        # Clear old buttons
        while self._choices_layout.count():
            item = self._choices_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Sort by priority (higher first)
        sorted_opts = sorted(node.options, key=lambda o: -o.priority)

        for opt in sorted_opts:
            if not opt.is_available(self._flags):
                continue

            # Check if target subtree is fully visited (nothing new)
            is_exhausted = self._is_subtree_visited(opt.next_node)

            btn = QPushButton(f"  {opt.text}")
            if is_exhausted:
                btn.setText(f"  {opt.text}  (nothing new)")
                btn.setStyleSheet(_BTN_STYLE_DISABLED)
                btn.setEnabled(False)
            else:
                target = self._graph.get_node(opt.next_node)
                is_farewell = target and target.is_terminal
                btn.setStyleSheet(_BTN_STYLE_FAREWELL if is_farewell else _BTN_STYLE)
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(
                    lambda checked, o=opt: self._on_option_clicked(o))

            self._choices_layout.addWidget(btn)

        self._choices_layout.addStretch()

        # Auto-scroll
        sb = self._chat_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_option_clicked(self, opt) -> None:
        """Player selected an option."""
        # Show player text
        self._add_player_message(opt.text)

        # Apply option flags
        self._flags.update(opt.set_flags)

        # Navigate to target node
        self._navigate_to(opt.next_node)

    def _is_subtree_visited(self, node_id: str,
                             _seen: set[str] | None = None) -> bool:
        """Check if a node and all its reachable descendants have been visited."""
        if _seen is None:
            _seen = set()
        if node_id in _seen:
            return True  # cycle — already checked, don't recurse
        _seen.add(node_id)
        if node_id not in self._visited_nodes:
            return False
        node = self._graph.get_node(node_id) if self._graph else None
        if node is None or node.is_terminal:
            return node_id in self._visited_nodes
        # Check all available options' targets
        for opt in node.options:
            if opt.is_available(self._flags):
                if not self._is_subtree_visited(opt.next_node, _seen):
                    return False
        return True

    # ── Chat log ─────────────────────────────────────────────────

    def _add_npc_message(self, text: str, node_id: str | None = None) -> None:
        name = getattr(self._entity, "name", "NPC")
        self._chat_log.append(
            f'<div style="margin: 4px 0;">'
            f'<b style="color: #e8c840;">{name}:</b> {text}</div>'
        )
        self._play_voice_line(text, node_id=node_id)

    def _add_player_message(self, text: str) -> None:
        self._chat_log.append(
            f'<div style="margin: 4px 0; text-align: right;">'
            f'<b style="color: #6090d0;">You:</b> <i>{text}</i></div>'
        )

    # ── Cleanup ──────────────────────────────────────────────────

    def _cleanup_worker(self, worker: _VoiceGenWorker) -> None:
        if worker in self._gen_workers:
            self._gen_workers.remove(worker)

    def _on_close(self) -> None:
        # Persist flags back to entity
        if hasattr(self._entity, "dialogue_flags"):
            self._entity.dialogue_flags.update(self._flags)

        if self._subscribed:
            try:
                from core.gameCreation.event_bus import EventBus
                from core.events import VOICE_LINE_READY
                EventBus.unsubscribe(VOICE_LINE_READY, self._on_voice_ready)
            except Exception:
                pass
        for worker in self._gen_workers:
            if worker.isRunning():
                worker.wait(2000)
        self._gen_workers.clear()
        self.conversation_ended.emit()
        self.accept()

    # ── Voice playback ───────────────────────────────────────────

    def _get_voice_profile(self):
        profile = getattr(self._entity, "voice_profile", None)
        if profile is None:
            return None
        if hasattr(profile, "is_voiced") and not profile.is_voiced:
            return None
        return profile

    def _play_voice_line(self, text: str, node_id: str | None = None) -> None:
        # 1. Check pre-generated files first (match by node_id or text)
        voice_dir = getattr(self._entity, "voice_lines_dir", None)
        if voice_dir:
            wav_path = self._find_voice_file(voice_dir, text, node_id)
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

    def _find_voice_file(
        self, voice_dir: str, text: str, node_id: str | None = None,
    ) -> Path | None:
        manifest_path = _PROJECT_ROOT / voice_dir / "manifest.json"
        if not manifest_path.exists():
            return None
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            lines = manifest.get("lines", {})

            # Try node_id match first (faster, more reliable)
            if node_id and node_id in lines:
                entry = lines[node_id]
                if entry.get("exists", False):
                    wav = _PROJECT_ROOT / voice_dir / entry["file"]
                    if wav.exists():
                        return wav

            # Fall back to text match
            for key, entry in lines.items():
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
