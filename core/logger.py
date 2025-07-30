import logging
from pathlib import Path
from datetime import datetime
import os
import glob

class AppLogger:
    """
    Application logger that manages log file creation, rotation, and formatting.

    :param log_dir: Directory where log files are stored. Defaults to "logs".
    :type log_dir: str or Path
    :param level: Logging level. Defaults to logging.INFO.
    :type level: int
    :param max_logs: Maximum number of log files to keep. Older logs are deleted.
    :type max_logs: int
    """

    def __init__(self, log_dir="logs", level=logging.INFO, max_logs=5):
        """
        Initialize the AppLogger.

        :param log_dir: Directory where log files are stored. Defaults to "logs".
        :type log_dir: str or Path
        :param level: Logging level. Defaults to logging.INFO.
        :type level: int
        :param max_logs: Maximum number of log files to keep. Older logs are deleted.
        :type max_logs: int
        """
        self.log_dir = Path(log_dir)
        self.max_logs = max_logs
        self.log_dir.mkdir(exist_ok=True)

        # prune before creating a new file
        self._prune_old_logs()

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_path = self.log_dir / f"log_{timestamp}.log"

        # ensure the file exists immediately (so prune tests see it)
        log_path.touch(exist_ok=True)

        # build a dedicated logger instance
        self.logger = logging.getLogger(f"DnDAppLogger_{timestamp}")
        self.logger.setLevel(level)
        self.logger.propagate = False

        # attach a FileHandler directly
        handler = logging.FileHandler(log_path, encoding="utf-8")
        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(fmt)
        self.logger.addHandler(handler)

    def _prune_old_logs(self):
        """
        Keep only the most recent `max_logs` log files in the log directory.

        Deletes the oldest log files if the number of log files exceeds `max_logs`.
        """
        log_files = sorted(
            glob.glob(str(self.log_dir / "log_*.log")),
            key=os.path.getmtime
        )
        while len(log_files) > self.max_logs:
            old_log = log_files.pop(0)
            try:
                os.remove(old_log)
            except Exception as e:
                print(f"Warning: Failed to delete old log {old_log}: {e}")

    def get_logger(self):
        """
        Get the configured logger instance.

        :return: The logger instance.
        :rtype: logging.Logger
        """
        return self.logger

app_logger = AppLogger().get_logger()
