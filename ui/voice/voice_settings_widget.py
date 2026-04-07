"""Reusable voice settings widget — embeddable in entity editor, character creator, etc."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QComboBox, QSlider, QFileDialog, QGroupBox,
    QCheckBox, QRadioButton, QButtonGroup, QStackedWidget,
)
from PyQt5.QtCore import Qt, pyqtSignal

from core.voice.voice_profile import VoiceProfile
from core.voice.voice_adapter import VoiceAdapter
from ui.voice.voice_preview_player import VoicePreviewPlayer
from ui.voice.voice_recorder_widget import VoiceRecorderWidget


class _LabeledSlider(QWidget):
    """Slider with min/max labels and current value display."""
    valueChanged = pyqtSignal(float)

    def __init__(self, label: str, min_val: float, max_val: float,
                 default: float, step: float = 0.05,
                 left_label: str = "", right_label: str = "",
                 parent=None):
        super().__init__(parent)
        self._min = min_val
        self._max = max_val
        self._step = step

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        # Title + value
        top = QHBoxLayout()
        top.addWidget(QLabel(label))
        top.addStretch()
        self._value_label = QLabel(f"{default:.2f}")
        self._value_label.setStyleSheet("color: #aaa; font-size: 10px;")
        top.addWidget(self._value_label)
        layout.addLayout(top)

        # Slider
        self._slider = QSlider(Qt.Horizontal)
        steps = int((max_val - min_val) / step)
        self._slider.setRange(0, steps)
        self._slider.setValue(int((default - min_val) / step))
        self._slider.valueChanged.connect(self._on_changed)
        layout.addWidget(self._slider)

        # Labels
        if left_label or right_label:
            labels = QHBoxLayout()
            labels.addWidget(QLabel(left_label))
            labels.addStretch()
            labels.addWidget(QLabel(right_label))
            for i in range(labels.count()):
                w = labels.itemAt(i).widget()
                if w:
                    w.setStyleSheet("color: #777; font-size: 9px;")
            layout.addLayout(labels)

    def _on_changed(self, pos: int) -> None:
        val = self._min + pos * self._step
        self._value_label.setText(f"{val:.2f}")
        self.valueChanged.emit(val)

    def value(self) -> float:
        return self._min + self._slider.value() * self._step

    def set_value(self, val: float) -> None:
        pos = int((val - self._min) / self._step)
        self._slider.blockSignals(True)
        self._slider.setValue(max(0, min(self._slider.maximum(), pos)))
        self._slider.blockSignals(False)
        self._value_label.setText(f"{val:.2f}")


class VoiceSettingsWidget(QWidget):
    """Reusable voice configuration panel.

    Signals:
        profile_changed(): Emitted when any setting changes.
    """

    profile_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._adapter = VoiceAdapter.instance()
        self._preview_text = "Greetings, traveler. How can I help you?"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # ── Preset picker ───────────────────────────────────────
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Voice Preset:"))
        self._preset_combo = QComboBox()
        self._preset_combo.addItem("(none)", "")
        for preset in self._adapter.list_presets():
            self._preset_combo.addItem(
                f"{preset.name} — {preset.description[:30]}",
                preset.preset_id,
            )
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        preset_row.addWidget(self._preset_combo, stretch=1)
        layout.addLayout(preset_row)

        # ── Reference audio source ──────────────────────────────
        layout.addWidget(QLabel("Reference Audio:"))

        # Source mode selector: Browse | Record
        mode_row = QHBoxLayout()
        self._source_group = QButtonGroup(self)
        self._browse_radio = QRadioButton("Browse File")
        self._record_radio = QRadioButton("Record")
        self._browse_radio.setChecked(True)
        self._source_group.addButton(self._browse_radio, 0)
        self._source_group.addButton(self._record_radio, 1)
        mode_row.addWidget(self._browse_radio)
        mode_row.addWidget(self._record_radio)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # Stacked widget for browse vs record panels
        self._source_stack = QStackedWidget()

        # Page 0: Browse panel (existing behavior)
        browse_page = QWidget()
        browse_layout = QHBoxLayout(browse_page)
        browse_layout.setContentsMargins(0, 0, 0, 0)
        self._ref_label = QLabel("(none)")
        self._ref_label.setStyleSheet("color: #aaa; font-size: 10px;")
        self._ref_label.setWordWrap(True)
        browse_layout.addWidget(self._ref_label, stretch=1)
        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(30)
        browse_btn.setToolTip("Browse for reference audio file")
        browse_btn.clicked.connect(self._browse_reference)
        browse_layout.addWidget(browse_btn)
        clear_btn = QPushButton("X")
        clear_btn.setFixedWidth(24)
        clear_btn.setToolTip("Clear reference audio")
        clear_btn.clicked.connect(self._clear_reference)
        browse_layout.addWidget(clear_btn)
        self._source_stack.addWidget(browse_page)

        # Page 1: Record panel
        self._recorder = VoiceRecorderWidget()
        self._recorder.recording_saved.connect(self._on_recording_saved)
        self._recorder.recording_cleared.connect(self._on_recording_cleared)
        self._source_stack.addWidget(self._recorder)

        self._source_group.buttonClicked.connect(self._on_source_mode_changed)
        layout.addWidget(self._source_stack)
        self._reference_audio: str | None = None

        # ── Normal sliders ──────────────────────────────────────
        self._emotion = _LabeledSlider(
            "Emotion Intensity", 0.0, 1.0, 0.5,
            left_label="Calm", right_label="Dramatic")
        self._emotion.valueChanged.connect(lambda _: self.profile_changed.emit())
        layout.addWidget(self._emotion)

        self._similarity = _LabeledSlider(
            "Voice Similarity", 0.0, 1.0, 0.5,
            left_label="Creative", right_label="Faithful")
        self._similarity.valueChanged.connect(lambda _: self.profile_changed.emit())
        layout.addWidget(self._similarity)

        self._speed = _LabeledSlider(
            "Speed", 0.7, 1.3, 1.0, step=0.05,
            left_label="Slow", right_label="Fast")
        self._speed.valueChanged.connect(lambda _: self.profile_changed.emit())
        layout.addWidget(self._speed)

        self._trim = _LabeledSlider(
            "Warm-up Trim", 0.0, 1.0, 0.35, step=0.05,
            left_label="0ms", right_label="1000ms")
        layout.addWidget(self._trim)

        # ── Preview ─────────────────────────────────────────────
        layout.addWidget(QLabel("Preview Text:"))
        from PyQt5.QtWidgets import QTextEdit
        self._preview_input = QTextEdit()
        self._preview_input.setMaximumHeight(50)
        self._preview_input.setPlaceholderText("Type text to preview...")
        self._preview_input.setPlainText(self._preview_text)
        layout.addWidget(self._preview_input)

        self._preview = VoicePreviewPlayer()
        self._preview.set_adapter(self._adapter)
        self._preview._play_btn.clicked.disconnect()
        self._preview._play_btn.clicked.connect(self._do_preview)
        layout.addWidget(self._preview)

        # ── Advanced toggle ─────────────────────────────────────
        self._adv_toggle = QCheckBox("Advanced Settings")
        self._adv_toggle.toggled.connect(self._toggle_advanced)
        layout.addWidget(self._adv_toggle)

        self._adv_group = QWidget()
        adv_layout = QVBoxLayout(self._adv_group)
        adv_layout.setContentsMargins(0, 0, 0, 0)

        self._temperature = _LabeledSlider(
            "Temperature", 0.1, 1.5, 0.8, step=0.05,
            left_label="Precise", right_label="Random")
        self._temperature.valueChanged.connect(lambda _: self.profile_changed.emit())
        adv_layout.addWidget(self._temperature)

        self._top_p = _LabeledSlider(
            "Top-P Sampling", 0.5, 1.0, 1.0, step=0.05)
        self._top_p.valueChanged.connect(lambda _: self.profile_changed.emit())
        adv_layout.addWidget(self._top_p)

        self._min_p = _LabeledSlider(
            "Min-P Threshold", 0.0, 0.2, 0.05, step=0.01)
        self._min_p.valueChanged.connect(lambda _: self.profile_changed.emit())
        adv_layout.addWidget(self._min_p)

        self._rep_penalty = _LabeledSlider(
            "Repetition Penalty", 1.0, 2.0, 1.2, step=0.1)
        self._rep_penalty.valueChanged.connect(lambda _: self.profile_changed.emit())
        adv_layout.addWidget(self._rep_penalty)

        self._adv_group.hide()
        layout.addWidget(self._adv_group)

        # ── Status ──────────────────────────────────────────────
        hw = self._adapter.hardware_tier()
        status_text = f"Voice: {'Available' if self._adapter.is_available() else 'Not available'} ({hw})"
        self._hw_label = QLabel(status_text)
        self._hw_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self._hw_label)

    # ─── Preset ─────────────────────────────────────────────────

    def _on_preset_changed(self, index: int) -> None:
        preset_id = self._preset_combo.currentData()
        if not preset_id:
            return
        preset = self._adapter.get_preset(preset_id)
        if preset:
            self._emotion.set_value(preset.default_exaggeration)
            self._similarity.set_value(preset.default_cfg_weight)
            self._speed.set_value(preset.default_speed)
            if preset.reference_audio_filename:
                from pathlib import Path
                ref = f"core/audio/voice_seeds/{preset.reference_audio_filename}"
                self._reference_audio = ref
                self._ref_label.setText(preset.reference_audio_filename)
            self.profile_changed.emit()

    # ─── Source mode ──────────────────────────────────────────────

    def _on_source_mode_changed(self) -> None:
        idx = self._source_group.checkedId()
        self._source_stack.setCurrentIndex(idx)

    def _on_recording_saved(self, path: str) -> None:
        self._reference_audio = path
        self.profile_changed.emit()

    def _on_recording_cleared(self) -> None:
        self._reference_audio = None
        self.profile_changed.emit()

    # ─── Reference audio ────────────────────────────────────────

    def _browse_reference(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Voice Reference Audio", "",
            "Audio Files (*.wav *.mp3 *.ogg)")
        if path:
            self._reference_audio = path
            from pathlib import Path
            self._ref_label.setText(Path(path).name)
            self.profile_changed.emit()

    def _clear_reference(self) -> None:
        self._reference_audio = None
        self._ref_label.setText("(none)")
        self.profile_changed.emit()

    # ─── Advanced toggle ────────────────────────────────────────

    def _toggle_advanced(self, checked: bool) -> None:
        self._adv_group.setVisible(checked)

    # ─── Preview ────────────────────────────────────────────────

    def set_preview_text(self, text: str) -> None:
        """Set the text used for voice preview."""
        self._preview_text = text
        if hasattr(self, "_preview_input"):
            self._preview_input.setPlainText(text)

    def _do_preview(self) -> None:
        text = self._preview_input.toPlainText().strip() if hasattr(self, "_preview_input") else self._preview_text
        if not text:
            text = "Hello, this is a voice test."
        # Apply trim setting to the engine's post-processor
        trim_sec = self._trim.value()
        try:
            from core.voice import voice_engine
            voice_engine._TRIM_SECONDS = trim_sec
        except Exception:
            pass
        profile = self.get_profile()
        self._preview.preview(text, profile)

    # ─── Profile I/O ────────────────────────────────────────────

    def get_profile(self) -> VoiceProfile:
        """Build a VoiceProfile from the current widget state."""
        preset_id = self._preset_combo.currentData() or ""
        # If recorder has unsaved audio, save it now
        if (self._record_radio.isChecked()
                and self._recorder.has_recording()
                and not self._recorder.saved_path()):
            save_path = VoiceAdapter.recording_path("recording")
            self._recorder.save_recording(save_path)
            self._reference_audio = str(save_path)
        source_type = "preset" if preset_id else ("recorded" if self._reference_audio else "none")
        return VoiceProfile(
            source_type=source_type,
            preset_name=preset_id or None,
            reference_audio=self._reference_audio,
            exaggeration=self._emotion.value(),
            speed_factor=self._speed.value(),
            cfg_weight=self._similarity.value(),
            temperature=self._temperature.value(),
            top_p=self._top_p.value(),
            min_p=self._min_p.value(),
            repetition_penalty=self._rep_penalty.value(),
        )

    def set_profile(self, profile: VoiceProfile) -> None:
        """Load a VoiceProfile into the widget."""
        # Preset
        if profile.preset_name:
            for i in range(self._preset_combo.count()):
                if self._preset_combo.itemData(i) == profile.preset_name:
                    self._preset_combo.setCurrentIndex(i)
                    break

        # Reference audio — select the right source mode
        self._reference_audio = profile.reference_audio
        if profile.source_type == "recorded" and profile.reference_audio:
            self._record_radio.setChecked(True)
            self._source_stack.setCurrentIndex(1)
            self._recorder.load_existing(profile.reference_audio)
        elif profile.reference_audio:
            self._browse_radio.setChecked(True)
            self._source_stack.setCurrentIndex(0)
            from pathlib import Path
            self._ref_label.setText(Path(profile.reference_audio).name)
        else:
            self._browse_radio.setChecked(True)
            self._source_stack.setCurrentIndex(0)
            self._ref_label.setText("(none)")

        # Sliders
        self._emotion.set_value(profile.exaggeration)
        self._similarity.set_value(profile.cfg_weight)
        self._speed.set_value(profile.speed_factor)
        self._temperature.set_value(profile.temperature)
        self._top_p.set_value(profile.top_p)
        self._min_p.set_value(profile.min_p)
        self._rep_penalty.set_value(profile.repetition_penalty)
