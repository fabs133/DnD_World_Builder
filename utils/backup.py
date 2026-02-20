import shutil
import os
from core.logger import app_logger


def create_backup(path):
    """
    Create a backup of the specified file.

    Copies the file at the given path to a new file with a `.bak` extension appended.

    :param path: The path to the file to back up.
    :type path: str
    :raises FileNotFoundError: If the specified file does not exist.
    :return: The path to the created backup file.
    :rtype: str
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Cannot backup: {path} not found")
    
    backup_path = f"{path}.bak"
    shutil.copy2(path, backup_path)
    app_logger.info(f"Backup created: {backup_path}")
    return backup_path
