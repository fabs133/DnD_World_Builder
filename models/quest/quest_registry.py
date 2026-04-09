"""Quest definitions for the Shattered Realms scenario.

Each quest links to NPC dialogue flags set during conversation.
The quest tracker checks these flags to determine objective completion.
"""

from models.quest.quest import Quest, QuestObjective

SHATTERED_REALMS_QUESTS: list[Quest] = [
    Quest(
        quest_id="star_iron",
        title="Star-Iron for the Smith",
        description="Durin the Smith needs star-iron from the old dwarven forge in the crystal caves to craft weapons that can hurt the blight.",
        giver="Durin the Smith",
        objectives=[
            QuestObjective("Accept Durin's quest", "star_iron_quest_accepted"),
            QuestObjective("Find the forge directions from Brokk", "heard_forge_directions"),
        ],
        rewards={"gold": 50, "xp": 200},
    ),
    Quest(
        quest_id="lost_patrol",
        title="The Lost Patrol",
        description="Captain Thessa's patrol of five soldiers went into the swamp and never returned. Find them — alive or their insignias.",
        giver="Captain Thessa",
        objectives=[
            QuestObjective("Accept Thessa's patrol mission", "patrol_quest_accepted"),
            QuestObjective("Learn the soldiers' fate from Nessa", "heard_soldier_fate"),
        ],
        rewards={"gold": 30, "xp": 150},
    ),
    Quest(
        quest_id="moonpetal",
        title="Moonpetal Harvest",
        description="Elara the Herbalist can brew a potion to resist the Crown's corruption, but she needs moonpetal blossoms from near the spider nests.",
        giver="Elara the Herbalist",
        objectives=[
            QuestObjective("Accept Elara's quest for moonpetal blossoms", "moonpetal_quest_accepted"),
        ],
        rewards={"gold": 25, "xp": 100},
    ),
    Quest(
        quest_id="dawn_lotus",
        title="Dawn Lotus for the Ward",
        description="Sister Maren's chapel holds the last ward protecting the realm. She needs dawn lotus flowers from the frozen wastes to restore it.",
        giver="Sister Maren",
        objectives=[
            QuestObjective("Accept Maren's quest for dawn lotus", "dawn_lotus_quest_accepted"),
            QuestObjective("Learn where dawn lotus grows from Sigrid", "heard_dawn_lotus_location"),
        ],
        rewards={"gold": 40, "xp": 200},
    ),
    Quest(
        quest_id="bone_skull",
        title="The Bone Mound",
        description="Nessa the Witch can quiet the walking dead, but she needs the skull from whatever ancient thing is buried at the bottom of the bone mound.",
        giver="Nessa the Witch",
        objectives=[
            QuestObjective("Accept Nessa's bone mound quest", "bone_quest_accepted"),
        ],
        rewards={"gold": 35, "xp": 150},
    ),
    Quest(
        quest_id="ley_stone",
        title="The Ley Line Marker",
        description="Harlen the Cartographer has mapped the blight's spiral pattern. He needs you to check a standing stone at the summit to determine if the ley lines can be disrupted.",
        giver="Harlen the Cartographer",
        objectives=[
            QuestObjective("Accept Harlen's ley line quest", "ley_line_quest_accepted"),
        ],
        rewards={"gold": 30, "xp": 150},
    ),
    Quest(
        quest_id="frost_wyrm",
        title="The Frozen Lake",
        description="Sigrid Frostborn's warband found the source of the unnatural winter beneath the frozen lake. She needs help to reach and defeat the frost wyrm.",
        giver="Sigrid Frostborn",
        objectives=[
            QuestObjective("Accept Sigrid's wyrm quest", "wyrm_quest_accepted"),
        ],
        rewards={"gold": 60, "xp": 300},
    ),
    Quest(
        quest_id="break_the_crown",
        title="Break the Crown",
        description="The Crown of Fractures must be removed from Morvain's brow while he lives, then struck against the throne. End the blight once and for all.",
        giver="Ghost of King Aldric",
        objectives=[
            QuestObjective("Learn how to destroy the Crown", "crown_destruction_method"),
            QuestObjective("Learn the citadel layout from Kael", "heard_citadel_layout"),
        ],
        rewards={"xp": 500},
        prerequisite_flags=["heard_about_crown"],
    ),
]
