"""Background worker thread for installing Chatterbox TTS via pip."""

from __future__ import annotations

from PyQt5.QtCore import QThread, pyqtSignal


class VoiceInstallWorker(QThread):
    """Runs pip install chatterbox-tts in the background.

    Signals:
        progress(str, int): (message, percent 0-100)
        finished(bool, str): (success, detail_message)
    """

    progress = pyqtSignal(str, int)
    finished = pyqtSignal(bool, str)

    def run(self):
        try:
            from core.voice.voice_setup import install_chatterbox

            line_count = 0

            def on_output(line: str):
                nonlocal line_count
                line_count += 1
                # Estimate progress from pip output patterns
                pct = min(90, line_count * 3)
                if "Downloading" in line:
                    pct = min(60, pct)
                    self.progress.emit(f"Downloading: {line.split()[-1][:40]}", pct)
                elif "Installing" in line:
                    self.progress.emit("Installing packages...", 75)
                elif "Successfully" in line:
                    self.progress.emit("Finalizing...", 90)
                else:
                    self.progress.emit(line[:60], pct)

            self.progress.emit("Starting installation...", 5)
            success, message = install_chatterbox(on_output=on_output)
            self.progress.emit("Done" if success else "Failed", 100 if success else 0)
            self.finished.emit(success, message)

        except Exception as e:
            self.finished.emit(False, f"Worker error: {e}")


class VoiceVerifyWorker(QThread):
    """Runs model load + test generation in the background.

    Signals:
        progress(str): status message
        finished(bool, str): (success, detail_message)
    """

    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def run(self):
        try:
            from core.voice.voice_setup import verify_chatterbox

            self.progress.emit("Loading model...")
            success, message = verify_chatterbox()
            self.finished.emit(success, message)

        except Exception as e:
            self.finished.emit(False, f"Verify error: {e}")
