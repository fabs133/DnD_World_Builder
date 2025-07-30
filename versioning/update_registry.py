from versioning.migrations import user_profile, settings, map_data

#: Registry mapping data types to their migration functions by version.
#: 
#: The structure is:
#: 
#: .. code-block:: python
#: 
#:     {
#:         "DataType": {
#:             version_number: migration_function_or_None,
#:             ...
#:         },
#:         ...
#:     }
#: 
#: Each migration function should accept the old data format and return the new format.
update_registry = {
    "UserProfile": {
        0: user_profile.migrate_v0_to_v1,
        1: user_profile.migrate_v1_to_v2,
    },
    "Settings": {
        0: None,
    },
    "Map": {
        0: None,
    }
}
