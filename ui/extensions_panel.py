"""Extension card for Chatterbox TTS — install, verify, status display."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QFrame,
)
from PyQt5.QtCore import Qt


class ChatterboxExtensionCard(QFrame):
    """Card widget showing Chatterbox TTS status with install/verify controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet(
            "ChatterboxExtensionCard { border: 1px solid #555; "
            "border-radius: 6px; padding: 8px; }")
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Title
        title = QLabel("Chatterbox TTS")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title)

        desc = QLabel("AI voice generation for NPCs and player characters.")
        desc.setStyleSheet("color: #888; font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Status row
        status_row = QHBoxLayout()
        self._status_dot = QLabel("\u25cf")  # ●
        self._status_dot.setStyleSheet("font-size: 16px; color: #888;")
        status_row.addWidget(self._status_dot)
        self._status_label = QLabel("Checking...")
        self._status_label.setStyleSheet("font-size: 11px;")
        status_row.addWidget(self._status_label, stretch=1)
        layout.addLayout(status_row)

        # Requirements
        req = QLabel("Requires: ~2 GB disk space, NVIDIA GPU recommended")
        req.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(req)

        # Progress bar (hidden by default)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setFixedHeight(16)
        self._progress.hide()
        layout.addWidget(self._progress)

        self._progress_label = QLabel("")
        self._progress_label.setStyleSheet("color: #aaa; font-size: 10px;")
        self._progress_label.hide()
        layout.addWidget(self._progress_label)

        # Buttons
        btn_row = QHBoxLayout()
        self._install_btn = QPushButton("Install")
        self._install_btn.clicked.connect(self._on_install)
        btn_row.addWidget(self._install_btn)

        self._verify_btn = QPushButton("Verify")
        self._verify_btn.clicked.connect(self._on_verify)
        btn_row.addWidget(self._verify_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Deferred detection in background thread — torch imports block the GIL
        self._set_status("#888", "Checking...")
        import threading
        def _bg_detect():
            try:
                from core.voice.voice_setup import detect_voice_system, VoiceSetupState, get_installed_version
                state, detail = detect_voice_system()
                version = get_installed_version()
                # Schedule UI update on main thread
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._apply_detection(state, detail, version))
            except Exception as e:
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._set_status("#c44", f"Error: {e}"))
        threading.Thread(target=_bg_detect, daemon=True).start()

    def _apply_detection(self, state, detail, version) -> None:
        """Apply detection results to UI (called on main thread)."""
        from core.voice.voice_setup import VoiceSetupState
        try:
            if state == VoiceSetupState.READY:
                self._set_status("green", f"Ready (GPU) — v{version or '?'}")
                self._set_detail(detail)
                self._install_btn.setText("Reinstall")
                self._verify_btn.setEnabled(True)
            elif state == VoiceSetupState.READY_CPU:
                self._set_status("#cc0", f"Ready (CPU only) — v{version or '?'}")
                self._set_detail(detail)
                self._install_btn.setText("Reinstall")
                self._verify_btn.setEnabled(True)
            elif state == VoiceSetupState.MISSING_PACKAGE:
                self._set_status("#888", "Not installed")
                self._install_btn.setText("Install")
                self._verify_btn.setEnabled(False)
            elif state == VoiceSetupState.TORCH_MISSING:
                self._set_status("#c80", "PyTorch missing")
                self._install_btn.setText("Install")
                self._verify_btn.setEnabled(False)
            else:
                self._set_status("#c44", f"Error: {detail}")
                self._install_btn.setText("Retry Install")
                self._verify_btn.setEnabled(False)
        except Exception as e:
            self._set_status("#c44", f"Detection error: {e}")

    def _set_status(self, color: str, text: str) -> None:
        self._status_dot.setStyleSheet(f"font-size: 16px; color: {color};")
        self._status_label.setText(text)

    def _set_detail(self, text: str) -> None:
        self._progress_label.setText(text)
        self._progress_label.show()

    def _on_install(self) -> None:
        from core.voice.voice_installer import VoiceInstallWorker

        self._install_btn.setEnabled(False)
        self._verify_btn.setEnabled(False)
        self._progress.show()
        self._progress_label.show()
        self._progress.setValue(0)
        self._set_status("#88f", "Installing...")

        self._worker = VoiceInstallWorker()
        self._worker.progress.connect(self._on_install_progress)
        self._worker.finished.connect(self._on_install_finished)
        self._worker.start()

    def _on_install_progress(self, msg: str, pct: int) -> None:
        self._progress.setValue(pct)
        self._progress_label.setText(msg)

    def _on_install_finished(self, success: bool, message: str) -> None:
        self._install_btn.setEnabled(True)
        self._progress.hide()

        if success:
            self._progress_label.setText(message)
            self._detect()  # Refresh status
        else:
            self._set_status("#c44", "Install failed")
            self._progress_label.setText(message)

    def _on_verify(self) -> None:
        from core.voice.voice_installer import VoiceVerifyWorker

        self._verify_btn.setEnabled(False)
        self._set_status("#88f", "Verifying...")
        self._progress_label.setText("Loading model and generating test audio...")
        self._progress_label.show()

        self._worker = VoiceVerifyWorker()
        self._worker.progress.connect(lambda msg: self._progress_label.setText(msg))
        self._worker.finished.connect(self._on_verify_finished)
        self._worker.start()

    def _on_verify_finished(self, success: bool, message: str) -> None:
        self._verify_btn.setEnabled(True)
        self._progress_label.setText(message)
        if success:
            self._set_status("#4a4", f"Verified — {message}")
        else:
            self._set_status("#c44", f"Verification failed")
