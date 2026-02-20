from pathlib import Path
from datetime import datetime
import shutil
from core.logger import app_logger


class BackupManager:
    """
    Manages creation and pruning of backup files for map data.

    :param backup_dir: Directory where backups are stored.
    :type backup_dir: str
    :param max_backups_per_map: Maximum number of backups to retain per map.
    :type max_backups_per_map: int
    """

    def __init__(self, backup_dir="../backup", max_backups_per_map=5):
        """
        Initialize the BackupManager.

        :param backup_dir: Path to the backup directory.
        :type backup_dir: str
        :param max_backups_per_map: Maximum number of backups to keep for each map.
        :type max_backups_per_map: int
        """
        self.backup_dir = Path(backup_dir).resolve()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.max_backups = max_backups_per_map

    def backup_map(self, map_path: Path):
        """
        Creates a timestamped backup of the given map file.

        :param map_path: Path to the map file to back up.
        :type map_path: Path
        """
        app_logger.debug(f"Backing up map: {map_path}")
        if not map_path.exists():
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"{map_path.stem}_{timestamp}.json"
        shutil.copy2(map_path, backup_file)

        self._prune_old_backups(map_path.stem)

    def _prune_old_backups(self, base_name: str):
        """
        Removes the oldest backups exceeding the configured limit for a given map.

        :param base_name: Base name of the map file (without timestamp).
        :type base_name: str
        """
        app_logger.debug(f"Pruning old backups for: {base_name}")
        backups = sorted(
            self.backup_dir.glob(f"{base_name}_*.json"),
            key=lambda p: p.stem,
            reverse=True
        )
        for old_backup in backups[self.max_backups:]:
            old_backup.unlink()
