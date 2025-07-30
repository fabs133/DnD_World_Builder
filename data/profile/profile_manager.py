import json
from pathlib import Path
from versioning.updater import Updater
from versioning.update_registry import update_registry
from utils.backup import create_backup
from core.logger import AppLogger

logger = AppLogger().get_logger()
updater = Updater(update_registry)

class UserProfile:
    """
    Represents a user profile containing character data and preferences.

    :cvar int VERSION: The current version of the user profile schema.
    :ivar str name: The name of the user profile.
    :ivar int profile_version: The version of the profile data.
    :ivar dict data: The profile data, including characters, current character, and preferences.
    """
    VERSION = 1

    def __init__(self, name, profile_version, data=None):
        """
        Initialize a UserProfile instance.

        :param name: The name of the user profile.
        :type name: str
        :param profile_version: The version of the profile data.
        :type profile_version: int
        :param data: The profile data. If None, a default structure is used.
        :type data: dict, optional
        """
        self.name = name
        self.profile_version = profile_version
        self.data = data or {
            "characters": [],
            "current_character": None,
            "preferences": {}
        }

    def get_characters(self):
        """
        Get the list of characters in the profile.

        :return: A list of character data.
        :rtype: list
        """
        return self.data["characters"]

    def get_current_character(self):
        """
        Get the currently selected character.

        :return: The current character, or None if not set.
        :rtype: object or None
        """
        return self.data["current_character"]

    def set_preference(self, key, value):
        """
        Set a user preference.

        :param key: The preference key.
        :type key: str
        :param value: The value to set for the preference.
        :type value: object
        """
        self.data["preferences"][key] = value

    def get_preference(self, key, default=None):
        """
        Get a user preference.

        :param key: The preference key.
        :type key: str
        :param default: The value to return if the preference is not set.
        :type default: object, optional
        :return: The value of the preference, or the default if not set.
        :rtype: object
        """
        return self.data["preferences"].get(key, default)

    def save(self, path):
        """
        Save the profile data to a file.

        :param path: The file path to save the profile data.
        :type path: str
        """
        with open(path, 'w') as f:
            json.dump(self.data, f, indent=4)

    @staticmethod
    def load_user_profile(path):
        """
        Load a user profile from a file, updating if necessary.

        :param path: The file path to load the profile from.
        :type path: str
        :return: The loaded (and possibly updated) user profile.
        :rtype: UserProfile
        """
        with open(path) as f:
            data = json.load(f)

        version = data.get("version", 0)

        if version < UserProfile.VERSION:
            logger.info(f"Profile out of date: v{version}")
            create_backup(path)
            data, new_version = updater.update("UserProfile", data, version)
            with open(path, "w") as f_out:
                json.dump(data, f_out, indent=2)
            logger.info(f"Profile updated to v{new_version}")

        return UserProfile.from_dict(data)

    @staticmethod
    def from_dict(data: dict):
        """
        Instantiate a UserProfile from a dict loaded from JSON.

        Assumes ``data["version"]`` is the profile version.
        The ``name`` field isn’t stored in the JSON, so we leave it as None.

        :param data: The dictionary containing profile data.
        :type data: dict
        :return: The instantiated user profile.
        :rtype: UserProfile
        """
        version = data.get("version")
        # name isn’t in the JSON payload, so default to None (or pull from data if you later store it)
        return UserProfile(name=None, profile_version=version, data=data)

    @staticmethod
    def load(path, name):
        """
        Load a user profile from a file with a given name.

        :param path: The file path to load the profile from.
        :type path: str
        :param name: The name to assign to the loaded profile.
        :type name: str
        :return: The loaded user profile.
        :rtype: UserProfile
        """
        with open(path, 'r') as f:
            data = json.load(f)
        return UserProfile(name, data)
