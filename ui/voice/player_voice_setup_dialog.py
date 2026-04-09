"""Dialog for players to record their voice, write lines, and generate audio."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QProgressBar, QGroupBox, QScrollArea, QFrame, QWidget,
)
from PyQt5.QtCore import pyqtSignal, Qt, QThread

from core.voice.player_voice_lines import (
    PlayerVoiceLine, PlayerVoiceLineSet,
    VOICE_LINE_CATEGORIES, PLAYER_VOICE_LINE_PRESETS,
    MAX_VOICE_LINES, default_voice_lines,
)

_STYLE = (
    "QDialog { background: #1e1c18; }"
    "QLabel { color: #e0d8c8; }"
    "QGroupBox { color: #e8c840; font-weight: bold;"
    "  border: 1px solid rgba(200,170,100,60); border-radius: 6px;"
    "  margin-top: 8px; padding-top: 14px; }"
    "QGroupBox::title { padding: 0 6px; }"
    "QLineEdit { background: rgba(40,38,34,200); color: #e0d8c8;"
    "  border: 1px solid rgba(200,170,100,40); padding: 4px; }"
    "QComboBox { background: rgba(40,38,34,200); color: #e0d8c8;"
    "  border: 1px solid rgba(200,170,100,40); padding: 2px 4px; }"
    "QPushButton { background: rgba(60,55,45,200); color: #e0d8c8;"
    "  border: 1px solid rgba(200,170,100,60); border-radius: 4px;"
    "  padding: 5px 12px; }"
    "QPushButton:hover { background: rgba(100,90,60,200); }"
    "QPushButton:disabled { color: #605848; }"
    "QProgressBar { border: 1px solid rgba(200,170,100,40);"
    "  border-radius: 3px; text-align: center; }"
    "QProgressBar::chunk { background: #4caf50; }"
)


class _GenWorker(QThread):
    """Background thread for batch voice generation."""

    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(list)      # list of (bytes|None)
    error = pyqtSignal(str)

    def __init__(self, adapter, texts: list[str], profile, parent=None):
        super().__init__(parent)
        self._adapter = adapter
        self._texts = texts
        self._profile = profile

    def run(self):
        try:
            results = self._adapter.generate_batch(
                self._texts, self._profile,
                on_progress=lambda cur, tot: self.progress.emit(cur, tot),
            )
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class PlayerVoiceSetupDialog(QDialog):
    """Modal dialog for recording voice, writing lines, and generating audio.

    Signals
    -------
    voice_lines_ready(dict)
        Emitted when "Share with Party" is clicked. Payload contains
        the sharing data: ``{player_name, lines: [{text, category,
        cache_key, audio_base64, size_bytes}]}``.
    """

    voice_lines_ready = pyqtSignal(dict)

    def __init__(self, player_name: str = "Player",
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._player_name = player_name
        self._line_set = PlayerVoiceLineSet(
            player_name=player_name,
            lines=default_voice_lines(),
        )
        self._generated_audio: list[bytes | None] = []
        self._gen_worker: Optional[_GenWorker] = None

        self.setWindowTitle("Setup Your Voice")
        self.setMinimumSize(480, 560)
        self.setStyleSheet(_STYLE)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Step 1: Record voice ──
        rec_group = QGroupBox("Step 1: Record Your Voice")
        rec_layout = QVBoxLayout(rec_group)
        rec_layout.addWidget(QLabel(
            "Record 3-10 seconds of your voice as a reference clip."
            " This will be used to clone your voice for the lines below."))

        try:
            from ui.voice.voice_recorder_widget import VoiceRecorderWidget
            self._recorder = VoiceRecorderWidget()
            self._recorder.recording_saved.connect(self._on_recording_saved)
            rec_layout.addWidget(self._recorder)
        except ImportError:
            self._recorder = None
            rec_layout.addWidget(QLabel(
                "(sounddevice not installed — recording unavailable)"))

        layout.addWidget(rec_group)

        # ── Step 2: Voice lines list ──
        lines_group = QGroupBox("Step 2: Voice Lines")
        lines_layout = QVBoxLayout(lines_group)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMaximumHeight(220)
        self._lines_container = QWidget()
        self._lines_layout = QVBoxLayout(self._lines_container)
        self._lines_layout.setContentsMargins(0, 0, 0, 0)
        self._lines_layout.setSpacing(4)
        scroll.setWidget(self._lines_container)
        lines_layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add Line")
        add_btn.clicked.connect(self._add_line_row)
        btn_row.addWidget(add_btn)
        reset_btn = QPushButton("Reset Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        btn_row.addWidget(reset_btn)
        self._line_count_label = QLabel()
        btn_row.addWidget(self._line_count_label)
        btn_row.addStretch()
        lines_layout.addLayout(btn_row)

        layout.addWidget(lines_group)

        # ── Step 3: Generate & share ──
        gen_group = QGroupBox("Step 3: Generate & Share")
        gen_layout = QVBoxLayout(gen_group)

        self._progress = QProgressBar()
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        self._progress.hide()
        gen_layout.addWidget(self._progress)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #a09880; font-size: 11px;")
        gen_layout.addWidget(self._status_label)

        gen_btn_row = QHBoxLayout()
        self._generate_btn = QPushButton("Generate All")
        self._generate_btn.clicked.connect(self._on_generate)
        gen_btn_row.addWidget(self._generate_btn)

        self._share_btn = QPushButton("Share with Party")
        self._share_btn.setEnabled(False)
        self._share_btn.setStyleSheet(
            "QPushButton { color: #e8c840; font-weight: bold; }"
            "QPushButton:disabled { color: #605848; font-weight: normal; }")
        self._share_btn.clicked.connect(self._on_share)
        gen_btn_row.addWidget(self._share_btn)

        gen_btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        gen_btn_row.addWidget(close_btn)
        gen_layout.addLayout(gen_btn_row)

        layout.addWidget(gen_group)

        # Populate initial lines
        self._rebuild_line_rows()

    # ── Recording ─────────────────────────────────────────────────

    def _on_recording_saved(self, path: str) -> None:
        self._line_set.reference_audio_path = path
        self._status_label.setText(f"Reference audio saved: {Path(path).name}")

    # ── Line list management ──────────────────────────────────────

    def _rebuild_line_rows(self) -> None:
        while self._lines_layout.count():
            item = self._lines_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, line in enumerate(self._line_set.lines):
            self._add_line_widget(i, line)
        self._update_count()

    def _add_line_widget(self, idx: int, line: PlayerVoiceLine) -> None:
        row = QHBoxLayout()
        container = QWidget()
        container.setLayout(row)

        cat = QComboBox()
        cat.addItems(VOICE_LINE_CATEGORIES)
        if line.category in VOICE_LINE_CATEGORIES:
            cat.setCurrentText(line.category)
        cat.setFixedWidth(110)
        cat.currentTextChanged.connect(
            lambda text, i=idx: self._update_line_category(i, text))
        row.addWidget(cat)

        text_edit = QLineEdit(line.text)
        text_edit.setPlaceholderText("Enter voice line text...")
        text_edit.textChanged.connect(
            lambda text, i=idx: self._update_line_text(i, text))
        row.addWidget(text_edit)

        remove_btn = QPushButton("X")
        remove_btn.setFixedWidth(28)
        remove_btn.clicked.connect(lambda _, i=idx: self._remove_line(i))
        row.addWidget(remove_btn)

        self._lines_layout.addWidget(container)

    def _add_line_row(self) -> None:
        if len(self._line_set.lines) >= MAX_VOICE_LINES:
            self._status_label.setText(f"Maximum {MAX_VOICE_LINES} lines reached.")
            return
        self._line_set.lines.append(PlayerVoiceLine(text="", category="custom"))
        self._rebuild_line_rows()

    def _remove_line(self, idx: int) -> None:
        if 0 <= idx < len(self._line_set.lines):
            self._line_set.lines.pop(idx)
            self._rebuild_line_rows()

    def _update_line_text(self, idx: int, text: str) -> None:
        if 0 <= idx < len(self._line_set.lines):
            self._line_set.lines[idx] = PlayerVoiceLine(
                text=text,
                category=self._line_set.lines[idx].category,
            )

    def _update_line_category(self, idx: int, category: str) -> None:
        if 0 <= idx < len(self._line_set.lines):
            self._line_set.lines[idx] = PlayerVoiceLine(
                text=self._line_set.lines[idx].text,
                category=category,
            )

    def _reset_defaults(self) -> None:
        self._line_set.lines = default_voice_lines()
        self._rebuild_line_rows()

    def _update_count(self) -> None:
        n = len(self._line_set.lines)
        self._line_count_label.setText(f"{n}/{MAX_VOICE_LINES} lines")

    # ── Generation ────────────────────────────────────────────────

    def _on_generate(self) -> None:
        # Filter empty lines
        valid_lines = [l for l in self._line_set.lines if l.text.strip()]
        if not valid_lines:
            self._status_label.setText("Add at least one voice line.")
            return

        if not self._line_set.reference_audio_path:
            self._status_label.setText(
                "Record your voice first (Step 1) before generating.")
            return

        try:
            from core.voice.voice_adapter import VoiceAdapter
            adapter = VoiceAdapter.instance()
            if not adapter.is_available():
                self._status_label.setText(
                    "Chatterbox TTS not available. Install it in Voice Settings.")
                return
        except Exception as e:
            self._status_label.setText(f"Voice engine error: {e}")
            return

        # Build profile from reference audio
        from core.voice.voice_profile import VoiceProfile
        import uuid
        profile = VoiceProfile(
            voice_id=uuid.uuid4().hex[:12],
            source_type="recorded",
            reference_audio=self._line_set.reference_audio_path,
            preset_name=None,
            exaggeration=0.4,
            speed_factor=1.0,
            cfg_weight=0.5,
            language="en",
            pitch_description="player",
            temperature=0.8,
            top_p=0.95,
            min_p=0.05,
            repetition_penalty=1.2,
            apply_effects=False,
        )

        texts = [l.text for l in valid_lines]
        self._generate_btn.setEnabled(False)
        self._share_btn.setEnabled(False)
        self._progress.setRange(0, len(texts))
        self._progress.setValue(0)
        self._progress.show()
        self._status_label.setText("Generating voice lines...")

        self._gen_worker = _GenWorker(adapter, texts, profile, self)
        self._gen_worker.progress.connect(self._on_gen_progress)
        self._gen_worker.finished.connect(
            lambda results: self._on_gen_finished(results, valid_lines, profile))
        self._gen_worker.error.connect(self._on_gen_error)
        self._gen_worker.start()

    def _on_gen_progress(self, current: int, total: int) -> None:
        self._progress.setValue(current)
        self._status_label.setText(f"Generating... {current}/{total}")

    def _on_gen_finished(self, results: list, valid_lines: list,
                         profile) -> None:
        from core.voice.voice_cache import VoiceCache
        self._generated_audio = results
        self._generate_btn.setEnabled(True)

        # Compute cache keys and store in cache
        success = 0
        for i, (line, audio) in enumerate(zip(valid_lines, results)):
            if audio:
                key = VoiceCache.compute_cache_key(
                    profile.voice_id, line.text,
                    profile.exaggeration, profile.speed_factor, profile.cfg_weight)
                line.cache_key = key

                # Store in local cache
                try:
                    cache = VoiceCache(Path("assets/voice_cache"))
                    cache.put(key, audio, self._player_name, line.text)
                except Exception:
                    pass
                success += 1

        self._line_set.generated = True
        self._share_btn.setEnabled(success > 0)
        self._status_label.setText(
            f"Generated {success}/{len(valid_lines)} lines successfully.")
        self._progress.hide()

    def _on_gen_error(self, msg: str) -> None:
        self._generate_btn.setEnabled(True)
        self._status_label.setText(f"Generation error: {msg}")
        self._progress.hide()

    # ── Sharing ───────────────────────────────────────────────────

    def _on_share(self) -> None:
        valid = [
            (line, audio)
            for line, audio in zip(self._line_set.lines, self._generated_audio)
            if audio and line.cache_key
        ]
        if not valid:
            self._status_label.setText("No generated lines to share.")
            return

        share_lines = []
        for line, audio in valid:
            share_lines.append({
                "text": line.text,
                "category": line.category,
                "cache_key": line.cache_key,
                "audio_base64": base64.b64encode(audio).decode("ascii"),
                "size_bytes": len(audio),
            })

        self.voice_lines_ready.emit({
            "player_name": self._player_name,
            "lines": share_lines,
        })
        self._line_set.shared = True
        self._share_btn.setEnabled(False)
        self._status_label.setText(
            f"Shared {len(share_lines)} voice lines with the party!")

    # ── Public API ────────────────────────────────────────────────

    def get_line_set(self) -> PlayerVoiceLineSet:
        return self._line_set
