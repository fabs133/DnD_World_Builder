"""Global voice settings dialog — configure TTS engine, cache, and defaults."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QCheckBox, QGroupBox,
    QProgressBar,
)
from PyQt5.QtCore import Qt

from core.voice.voice_adapter import VoiceAdapter


class VoiceSettingsDialog(QDialog):
    """Global voice configuration dialog accessed from Tools > Voice Settings."""

    def __init__(self, settings_manager=None, parent=None):
        super().__init__(parent)
        self._settings = settings_manager
        self._adapter = VoiceAdapter.instance()
        self.setWindowTitle("Voice Settings")
        self.resize(420, 400)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ── Check if available, show install prompt if not ──────
        available = self._adapter.is_available()
        if not available:
            self._build_install_ui(layout)
            return

        hw = self._adapter.hardware_tier()
        loaded = self._adapter.is_model_loaded()

        # ── Status ──────────────────────────────────────────────
        status_group = QGroupBox("Engine Status")
        status_layout = QFormLayout(status_group)

        hw_label = QLabel(f"{hw.upper()}")
        hw_label.setStyleSheet(
            f"color: {'#4a4' if hw == 'gpu' else '#aa4' if hw == 'cpu' else '#a44'}; "
            "font-weight: bold;")
        status_layout.addRow("Hardware:", hw_label)

        status_label = QLabel("Available" if available else "Not available (install chatterbox-tts)")
        status_label.setStyleSheet(f"color: {'#4a4' if available else '#a44'};")
        status_layout.addRow("Chatterbox:", status_label)

        model_label = QLabel("Loaded" if loaded else "Not loaded")
        status_layout.addRow("Model:", model_label)

        if available and not loaded:
            load_btn = QPushButton("Load Model Now")
            self._load_progress = QProgressBar()
            self._load_progress.setRange(0, 100)
            self._load_progress.hide()
            load_btn.clicked.connect(self._load_model)
            status_layout.addRow(load_btn)
            status_layout.addRow(self._load_progress)

        layout.addWidget(status_group)

        # ── General Settings ────────────────────────────────────
        general_group = QGroupBox("General")
        general_layout = QFormLayout(general_group)

        self._voice_enabled = QCheckBox("Enable voice playback")
        self._voice_enabled.setChecked(
            self._get_setting("voice_enabled", True))
        general_layout.addRow(self._voice_enabled)

        self._default_model = QComboBox()
        self._default_model.addItems(["standard", "turbo"])
        self._default_model.setCurrentText(
            self._get_setting("voice_model", "standard"))
        general_layout.addRow("Default Model:", self._default_model)

        layout.addWidget(general_group)

        # ── Cache Settings ──────────────────────────────────────
        cache_group = QGroupBox("Cache")
        cache_layout = QFormLayout(cache_group)

        stats = self._adapter.cache_stats()
        entries = stats.get("entries", 0)
        size_mb = stats.get("size_mb", 0)
        cache_info = QLabel(f"{entries} entries, {size_mb:.1f} MB")
        cache_layout.addRow("Current:", cache_info)

        self._max_cache = QSpinBox()
        self._max_cache.setRange(100, 5000)
        self._max_cache.setSuffix(" MB")
        self._max_cache.setValue(
            self._get_setting("voice_cache_max_mb", 500))
        cache_layout.addRow("Max Size:", self._max_cache)

        clear_btn = QPushButton("Clear Voice Cache")
        clear_btn.clicked.connect(self._clear_cache)
        cache_layout.addRow(clear_btn)
        self._cache_info = cache_info

        layout.addWidget(cache_group)

        # ── Buttons ─────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _build_install_ui(self, layout) -> None:
        """Show install prompt when Chatterbox is not available."""
        layout.addStretch()

        icon = QLabel("Voice")
        icon.setStyleSheet("font-size: 18px; font-weight: bold;")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        msg = QLabel("Voice generation is not available.\nInstall Chatterbox TTS to enable it.")
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet("font-size: 13px; margin: 10px;")
        layout.addWidget(msg)

        from ui.extensions_panel import ChatterboxExtensionCard
        card = ChatterboxExtensionCard()
        layout.addWidget(card)

        layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

    def _get_setting(self, key: str, default):
        if self._settings:
            return self._settings.get(key, default)
        return default

    def _load_model(self) -> None:
        self._load_progress.show()
        self._load_progress.setValue(10)

        def on_progress(stage: str, pct: float):
            self._load_progress.setValue(int(pct * 100))

        ok = self._adapter.load_model(on_progress)
        self._load_progress.setValue(100 if ok else 0)

    def _clear_cache(self) -> None:
        self._adapter.clear_cache()
        self._cache_info.setText("0 entries, 0.0 MB")

    def _save(self) -> None:
        if self._settings:
            self._settings.set("voice_enabled", self._voice_enabled.isChecked())
            self._settings.set("voice_model", self._default_model.currentText())
            self._settings.set("voice_cache_max_mb", self._max_cache.value())
        self.accept()
