from pathlib import Path

try:
    from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
    from PyQt5.QtCore import QUrl
    _HAS_MULTIMEDIA = True
except ImportError:
    _HAS_MULTIMEDIA = False


class AudioPlayer:
    """
    Singleton audio player for the application.

    Wraps Qt's QMediaPlayer to provide simple play/stop functionality.
    Falls back to a no-op if PyQt5.QtMultimedia is not available.
    """

    _instance = None

    @classmethod
    def instance(cls):
        """
        Return the singleton AudioPlayer instance, creating it on first call.

        :return: The AudioPlayer singleton.
        :rtype: AudioPlayer
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if _HAS_MULTIMEDIA:
            self._player = QMediaPlayer()
        else:
            self._player = None

    def play(self, file_path):
        """
        Play an audio file.

        :param file_path: Path to the audio file to play.
        :type file_path: str or Path
        """
        if not self._player:
            print(f"[AudioPlayer] Cannot play — QtMultimedia not available: {file_path}")
            return

        path = Path(file_path)
        if not path.exists():
            print(f"[AudioPlayer] File not found: {file_path}")
            return

        url = QUrl.fromLocalFile(str(path.resolve()))
        content = QMediaContent(url)
        self._player.setMedia(content)
        self._player.play()
        print(f"[AudioPlayer] Playing: {file_path}")

    def stop(self):
        """Stop any currently playing audio."""
        if self._player:
            self._player.stop()
            print("[AudioPlayer] Stopped.")

    def is_playing(self):
        """
        Check if audio is currently playing.

        :return: True if audio is playing, False otherwise.
        :rtype: bool
        """
        if not self._player:
            return False
        return self._player.state() == QMediaPlayer.PlayingState
