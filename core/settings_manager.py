import os
import json
from core.logger import app_logger

CONFIG_VERSION = 1
"""
The current configuration version. Used for migration.
"""

DEFAULT_SETTINGS = {
    "grid_type": "square",
    "default_rows": 25,
    "default_cols": 25,
    "grid_size": 50,
    "theme": "dark_teal.xml",
    "last_profile_used": None,
    "recent_files": [],
    "auto_save_enabled": True,
    "auto_save_interval_seconds": 300,
}
"""
Default settings for the application.
"""


class SettingsManager:
    """
    Manages application settings, including loading, saving, and migrating configuration files.

    :param path: Path to the settings JSON file.
    :type path: str
    """

    def __init__(self, path="config/settings.json"):
        """
        Initialize the SettingsManager.

        :param path: Path to the settings JSON file.
        :type path: str
        """
        self.path = path
        self.settings = {}
        self._ensure_config_integrity()

    def _ensure_config_integrity(self):
        """
        Ensure the configuration file exists and is valid.
        If not, create a default configuration file.
        Handles loading and error recovery.
        """
        if not os.path.exists(self.path):
            app_logger.info(f"[Settings] No config found at {self.path}. Creating default config.")
            self.settings = DEFAULT_SETTINGS.copy()
            self.save_settings()
        else:
            try:
                with open(self.path, "r") as f:
                    self.settings = json.load(f)

                if "config_version" not in self.settings:
                    app_logger.warning("[Settings] Config version missing. Assuming version 0.")
                    self.settings["config_version"] = 0

                self._migrate_if_needed()

            except (json.JSONDecodeError, IOError) as e:
                app_logger.error(f"[Settings] Error loading config: {e}")
                app_logger.info("[Settings] Resetting to default config.")
                self.settings = DEFAULT_SETTINGS.copy()
                self.save_settings()

    def _migrate_if_needed(self):
        """
        Migrate the configuration file to the latest version if needed.
        """
        current_version = self.settings.get("config_version", 0)

        if current_version < CONFIG_VERSION:
            app_logger.info(f"[Settings] Migrating config from version {current_version} to {CONFIG_VERSION}")

            if current_version == 0:
                # Example: In v1, we added grid_size
                if "grid_size" not in self.settings:
                    self.settings["grid_size"] = 50
                current_version = 1

            # Future migrations go here...

            self.settings["config_version"] = CONFIG_VERSION
            self.save_settings()

    def get(self, key, default=None):
        """
        Get a setting value.

        :param key: The setting key.
        :type key: str
        :param default: The default value if the key is not found.
        :type default: Any
        :return: The value of the setting or default.
        """
        return self.settings.get(key, default)

    def set(self, key, value):
        """
        Set a setting value and save the configuration.

        :param key: The setting key.
        :type key: str
        :param value: The value to set.
        :type value: Any
        """
        self.settings[key] = value
        self.save_settings()

    def save_settings(self):
        """
        Save the current settings to the configuration file.
        """
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.settings, f, indent=4)

    def __getitem__(self, key):
        """
        Get a setting value using dictionary-style access.

        :param key: The setting key.
        :type key: str
        :return: The value of the setting or None.
        """
        return self.settings.get(key)

    def __setitem__(self, key, value):
        """
        Set a setting value using dictionary-style access.

        :param key: The setting key.
        :type key: str
        :param value: The value to set.
        :type value: Any
        """
        self.set(key, value)
