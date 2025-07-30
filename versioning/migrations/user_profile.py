"""
Example migration script for user profile data.

This script defines migration functions that update user profile data between versions.
"""

def migrate_v0_to_v1(data):
    """
    Migrate user profile data from version 0 to version 1.

    Adds a default theme to the user preferences if it doesn't exist.

    :param dict data: The user profile data to migrate.
    :return: The migrated user profile data with version set to 1.
    :rtype: dict
    """
    # Example: Add a default theme preference
    data.setdefault("preferences", {})
    data["preferences"].setdefault("theme", "light")
    data["version"] = 1
    return data

def migrate_v1_to_v2(data):
    """
    Migrate user profile data from version 1 to version 2.

    Adds a new field for character reference or metadata.

    :param dict data: The user profile data to migrate.
    :return: The migrated user profile data with version set to 2.
    :rtype: dict
    """
    data.setdefault("metadata", {"notes": ""})
    data["version"] = 2
    return data
