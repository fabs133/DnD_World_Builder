"""Generate the 'Hollow Crown' demo scenario.

Creates workspace/hollow_crown/map.json -- a 25x25 square-grid scenario
showcasing NPCs with voice profiles, zones, triggers, and varied terrain.

Usage:
    python tools/create_demo_scenario.py

Idempotent: produces identical output on every run (fixed timestamp,
deterministic voice_ids, no random elements).
"""

import hashlib
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Section 1 — Constants
# ---------------------------------------------------------------------------

WORKSPACE = Path(__file__).resolve().parent.parent / "workspace" / "hollow_crown"
OUTPUT = WORKSPACE / "map.json"

ROWS = 25
COLS = 25

FIXED_TIMESTAMP = "2026-01-01T00:00:00"
VOICE_SEED_PREFIX = "core/audio/voice_seeds/"

# Dice-to-int conversion (expected average, rounded down)
# 1d4->2  1d6->3  1d8->4  1d10->5  1d12->6  2d4->5  2d6->7  2d8->9  3d8->13

# Overlay colours per region
COLOR_MILLHAVEN = "#c4a35a"
COLOR_FOREST = "#1a472a"
COLOR_GREENREACH = "#8fbc8f"
COLOR_ASHENMERE = "#8b7d6b"
COLOR_APPROACH = "#696969"
COLOR_CITADEL = "#2d1b2e"
COLOR_ROAD = "#b8860b"

# ---------------------------------------------------------------------------
# Section 2 — Helper functions
# ---------------------------------------------------------------------------


def _voice_id(name: str) -> str:
    """Deterministic 12-char hex id from entity name."""
    return hashlib.md5(name.encode()).hexdigest()[:12]


def make_voice_profile(preset_name: str, entity_name: str,
                       pitch_description: str = "",
                       exaggeration: float = 0.5,
                       speed_factor: float = 1.0) -> dict:
    return {
        "voice_id": _voice_id(entity_name),
        "source_type": "preset",
        "reference_audio": f"{VOICE_SEED_PREFIX}{preset_name}.wav",
        "preset_name": preset_name,
        "exaggeration": exaggeration,
        "speed_factor": speed_factor,
        "cfg_weight": 0.5,
        "language": "en",
        "pitch_description": pitch_description,
    }


def make_entity(name: str, entity_type: str, *,
                stats: dict | None = None,
                hp: int = 10, max_hp: int | None = None,
                voice_preset: str | None = None,
                pitch_description: str = "",
                exaggeration: float = 0.5,
                speed_factor: float = 1.0,
                dialogue_lines: dict | None = None,
                inventory: list | None = None,
                triggers: list | None = None,
                conditions: list | None = None,
                position: tuple | None = None) -> dict:
    data: dict = {
        "name": name,
        "entity_type": entity_type,
        "stats": stats or {},
        "inventory": inventory or [],
        "triggers": triggers or [],
        "hp": hp,
        "max_hp": max_hp if max_hp is not None else hp,
        "conditions": conditions or [],
    }
    if position:
        data["position"] = list(position)
    if voice_preset:
        data["voice_profile"] = make_voice_profile(
            voice_preset, name, pitch_description, exaggeration, speed_factor)
    if dialogue_lines:
        data["dialogue_lines"] = dialogue_lines
    return data


def make_zone(zone_id: str, label: str, *,
              description: str | None = None,
              connections: list | None = None,
              locked: bool = False, lock_dc: int = 15,
              tags: list | None = None,
              placements: list | None = None) -> dict:
    data: dict = {
        "zone_id": zone_id,
        "label": label,
        "description": description,
        "background_image": None,
        "connections": connections or [],
        "locked": locked,
        "lock_dc": lock_dc,
        "tags": tags or [],
        "encounter_template_id": None,
    }
    if placements:
        data["placements"] = placements
    return data


def make_placement(entity_dict: dict, depth: int = 3,
                   x_percent: float = 0.5,
                   interaction_types: list | None = None) -> dict:
    return {
        "entity": entity_dict,
        "depth": depth,
        "x_percent": x_percent,
        "interaction_radius": 40,
        "interaction_types": interaction_types or ["inspect"],
    }


def make_trigger(event_type: str, label: str,
                 condition: dict, reaction: dict,
                 next_trigger: dict | None = None) -> dict:
    return {
        "event_type": event_type,
        "label": label,
        "condition": condition,
        "reaction": reaction,
        "next_trigger": next_trigger,
    }


# --- condition / reaction builders ---

def always_true() -> dict:
    return {"type": "AlwaysTrue", "args": {"type": "AlwaysTrue"}}


def perception_check(dc: int) -> dict:
    return {"type": "PerceptionCheck", "args": {"type": "PerceptionCheck", "dc": dc}}


def skill_check(skill: str, dc: int) -> dict:
    return {"type": "SkillCheck", "skill": skill, "dc": dc}


def alert_gm(message: str) -> dict:
    return {"type": "AlertGamemaster", "args": {"type": "AlertGamemaster", "message": message}}


def apply_damage(damage_type: str, amount: int) -> dict:
    return {"type": "ApplyDamage", "args": {"type": "ApplyDamage", "damage_type": damage_type, "amount": amount}}


def make_tile(row: int, col: int, *,
              terrain: str = "GRASS",
              tags: list | None = None,
              user_label: str | None = None,
              note: str | None = None,
              overlay_color: str | None = None,
              entities: list | None = None,
              triggers: list | None = None,
              zones: list | None = None,
              movement_cost: int = 5,
              elevation: int = 0) -> dict:
    data: dict = {
        "tile_id": f"{row}_{col}",
        "position": [row, col],
        "terrain": terrain,
        "tags": tags or [],
        "user_label": user_label,
        "note": note,
        "overlay_color": overlay_color,
        "last_updated": None,
        "entities": entities or [],
        "triggers": triggers or [],
    }
    if movement_cost != 5:
        data["movement_cost"] = movement_cost
    if elevation != 0:
        data["elevation"] = elevation
    if zones:
        data["zones"] = zones
    return data


# ---------------------------------------------------------------------------
# Section 3 — NPC, monster, and object definitions
# ---------------------------------------------------------------------------

# ── Millhaven NPCs ────────────────────────────────────────────────────────

def _marta_ironbrew() -> dict:
    return make_entity("Marta Ironbrew", "npc",
        stats={"str": 10, "dex": 10, "con": 12, "int": 11, "wis": 14, "cha": 13, "ac": 10},
        hp=15, voice_preset="barkeep",
        pitch_description="Warm, hearty woman in her 40s",
        dialogue_lines={
            "greeting": [
                "Welcome to the Crossed Antlers. What'll it be?",
                "Another brave soul looking for work, eh?",
            ],
            "shop": [
                "Ale's two coppers, stew's five. Best in Millhaven.",
            ],
            "quest": [
                "You've seen the notice board? That blight's killing us.",
                "Captain Aldric posted that bounty himself. He's at the guard post.",
                "Talk to Edda if you want to know how bad it really is.",
            ],
            "lore": [
                "Strange folk been passing through lately. City types.",
                "The forest wasn't always this way. Started a few months back.",
            ],
            "farewell": [
                "Safe travels. And come back alive, yeah?",
            ],
        })


def _voss_the_peddler() -> dict:
    return make_entity("Voss the Peddler", "npc",
        stats={"str": 8, "dex": 14, "con": 10, "int": 13, "wis": 12, "cha": 15, "ac": 12},
        hp=12, voice_preset="roguish_trickster",
        pitch_description="Quick, sly voice with a slight rasp",
        dialogue_lines={
            "greeting": [
                "Psst. Looking for something special?",
                "Voss has what you need. For a price.",
            ],
            "shop": [
                "Healing potions, rope, torches — basics, basics.",
                "I might have something rarer, if you've got the coin.",
            ],
            "quest": [
                "The forest? I know paths even the druids forgot.",
                "Information isn't free, friend. Fifty gold and I'll mark your map.",
            ],
            "lore": [
                "Seen some guild types heading north. Ashenmere money.",
                "Word is something valuable is buried in that old citadel.",
            ],
            "farewell": [
                "Pleasure doing business. Or not. Your loss.",
            ],
        })


def _edda_thornfield() -> dict:
    return make_entity("Edda Thornfield", "npc",
        stats={"str": 9, "dex": 8, "con": 10, "int": 10, "wis": 13, "cha": 11, "ac": 10},
        hp=8, voice_preset="mystic_elder",
        pitch_description="Worried, elderly farmer's voice",
        exaggeration=0.4, speed_factor=0.85,
        dialogue_lines={
            "greeting": [
                "Oh, thank the gods. Are you the ones answering the bounty?",
            ],
            "quest": [
                "My fields are dying. The crops turn black overnight.",
                "It started when that purple haze crept out of the forest.",
                "Please, you have to stop whatever's causing this.",
            ],
            "lore": [
                "My grandmother told stories of the old citadel. Nothing good.",
                "She said a king once ruled from there. A cruel one.",
            ],
            "farewell": [
                "Be careful out there. The forest isn't what it used to be.",
            ],
        })


def _captain_aldric() -> dict:
    return make_entity("Captain Aldric", "npc",
        stats={"str": 16, "dex": 12, "con": 14, "int": 11, "wis": 13, "cha": 14, "ac": 16},
        hp=30, voice_preset="grizzled_veteran",
        pitch_description="Deep, commanding military voice",
        dialogue_lines={
            "greeting": [
                "You here about the blight bounty?",
                "Good. We need capable hands.",
            ],
            "quest": [
                "The Thornveil is off limits normally. Wolves, worse.",
                "But this blight is spreading. Fields are dying.",
                "Take this writ. Show it at the forest gate.",
                "Something's driving the beasts mad. Be ready for a fight.",
            ],
            "lore": [
                "Old Valdris citadel is deep in the forest. Abandoned for centuries.",
                "Whatever's causing this, it's coming from that direction.",
            ],
            "farewell": [
                "Bring proof you've dealt with the source, and the reward is yours.",
            ],
        })


def _guard_holt() -> dict:
    return make_entity("Guard Holt", "npc",
        stats={"str": 14, "dex": 11, "con": 13, "int": 10, "wis": 11, "cha": 10, "ac": 14},
        hp=18, voice_preset="grizzled_veteran",
        pitch_description="Tired guard, mid-30s",
        speed_factor=0.95,
        dialogue_lines={
            "greeting": [
                "Halt. State your business.",
                "Looking for the captain? He's inside.",
            ],
            "quest": [
                "Captain's been posting bounties all week. The blight's got everyone on edge.",
            ],
            "farewell": [
                "Move along.",
            ],
        })


# ── Forest NPCs ───────────────────────────────────────────────────────────

def _thessaly() -> dict:
    return make_entity("Thessaly", "npc",
        stats={"str": 8, "dex": 12, "con": 10, "int": 16, "wis": 18, "cha": 14, "ac": 12},
        hp=20, voice_preset="ethereal",
        pitch_description="Airy, fading voice — a dying druid",
        exaggeration=0.6, speed_factor=0.85,
        dialogue_lines={
            "greeting": [
                "You... you shouldn't be here. The forest is dying.",
            ],
            "quest": [
                "The corruption flows from the old Valdris citadel.",
                "But it didn't start on its own. Someone brought something there.",
                "Something that was never meant to be worn.",
                "A crown. An ancient, terrible crown.",
            ],
            "lore": [
                "I've been trying to hold back the blight. But I'm failing.",
                "The wards I placed are crumbling. Whatever powers the Crown grows stronger.",
                "If you go to Valdris, look for the chapel. It's the one place the Crown's influence hasn't reached.",
            ],
            "farewell": [
                "Go. Stop this. Before there's nothing left to save.",
            ],
        })


# ── Greenreach NPCs ───────────────────────────────────────────────────────

def _old_renn() -> dict:
    return make_entity("Old Renn", "npc",
        stats={"str": 10, "dex": 9, "con": 11, "int": 10, "wis": 14, "cha": 11, "ac": 10},
        hp=10, voice_preset="grizzled_veteran",
        pitch_description="Weathered shepherd, slow and cautious",
        speed_factor=0.9,
        dialogue_lines={
            "greeting": [
                "Travellers, eh? Haven't seen many this way lately.",
            ],
            "quest": [
                "The sheep won't graze near the forest edge anymore.",
                "Smart animals. Smarter than some folk.",
            ],
            "lore": [
                "Seen riders from Ashenmere heading north. Guild banners.",
                "Something's rotten in that city. Mark my words.",
            ],
            "farewell": [
                "Watch the skies. And the ground, for that matter.",
            ],
        })


# ── Ashenmere NPCs ────────────────────────────────────────────────────────

def _archivist_sera() -> dict:
    return make_entity("Archivist Sera", "npc",
        stats={"str": 8, "dex": 10, "con": 10, "int": 18, "wis": 15, "cha": 12, "ac": 10},
        hp=12, voice_preset="scholar",
        pitch_description="Precise, nervous academic",
        exaggeration=0.2, speed_factor=1.05,
        dialogue_lines={
            "greeting": [
                "The archive is open for research. Please be quiet.",
            ],
            "quest": [
                "The Hollow Crown? Yes, I've found references.",
                "An artefact of the old kingdom. It was supposed to be destroyed.",
                "Someone has been asking about it. Someone from the guild.",
            ],
            "lore": [
                "The Crown was forged to bind the land to the ruler's will.",
                "But it corrupts. Every king who wore it went mad.",
                "The last one — they called him the Hollow King — nearly destroyed everything.",
            ],
            "farewell": [
                "Be careful with this knowledge. Some people don't want it shared.",
            ],
        })


def _guildmaster_torven() -> dict:
    return make_entity("Guildmaster Torven", "npc",
        stats={"str": 12, "dex": 10, "con": 12, "int": 16, "wis": 11, "cha": 16, "ac": 14},
        hp=25, voice_preset="warlord",
        pitch_description="Commanding, smooth — hides cruelty behind politeness",
        exaggeration=0.8, speed_factor=0.95,
        dialogue_lines={
            "greeting": [
                "Adventurers. How fortunate. I have a proposition.",
            ],
            "shop": [
                "The manticore bounty pays 200 gold. Generous, no?",
            ],
            "quest": [
                "A Razorclaw Manticore on the east road. Killing our caravans.",
                "Deal with it and the guild will remember your service.",
            ],
            "lore": [
                "Valdris? Ancient ruin. Nothing of interest.",
                "The blight is a natural phenomenon. It will pass.",
            ],
            "combat": [
                "You think you can threaten ME? In MY city?",
                "Guards! Seize them!",
            ],
        })


def _innkeeper_bram() -> dict:
    return make_entity("Innkeeper Bram", "npc",
        stats={"str": 12, "dex": 10, "con": 13, "int": 10, "wis": 12, "cha": 13, "ac": 10},
        hp=15, voice_preset="barkeep",
        pitch_description="Friendly, burly innkeeper",
        dialogue_lines={
            "greeting": [
                "Welcome to the Iron Flagon! Best beds in Ashenmere.",
            ],
            "shop": [
                "Room's ten silver a night. Includes breakfast.",
                "We've got ale, wine, and something stronger if you need it.",
            ],
            "lore": [
                "The guildmaster's been throwing money around lately.",
                "Hiring mercenaries, buying supplies. For what, nobody knows.",
            ],
            "farewell": [
                "Rest well. You look like you need it.",
            ],
        })


def _commander_vex() -> dict:
    return make_entity("Commander Vex", "npc",
        stats={"str": 15, "dex": 12, "con": 14, "int": 11, "wis": 10, "cha": 13, "ac": 16},
        hp=28, voice_preset="grizzled_veteran",
        pitch_description="Stern city guard commander",
        dialogue_lines={
            "greeting": [
                "State your business in Ashenmere.",
            ],
            "quest": [
                "The city is safe. That's all you need to know.",
                "If you have a complaint, file it with the clerk.",
            ],
            "lore": [
                "The guildmaster is a respected citizen. I'd watch your tongue.",
            ],
            "farewell": [
                "Don't cause trouble in my city.",
            ],
        })


def _lira_the_courier() -> dict:
    return make_entity("Lira the Courier", "npc",
        stats={"str": 10, "dex": 14, "con": 11, "int": 12, "wis": 10, "cha": 12, "ac": 12},
        hp=0, max_hp=14, voice_preset="young_adventurer",
        pitch_description="Young woman — found dead on the road",
        conditions=["dead"],
        dialogue_lines={
            "lore": [
                "(A courier's satchel lies beside the body. The seal on the letter bears a crown entwined with thorns.)",
            ],
        })


# ── Approach NPCs ─────────────────────────────────────────────────────────

def _deserter_kael() -> dict:
    return make_entity("Deserter Kael", "npc",
        stats={"str": 13, "dex": 14, "con": 12, "int": 11, "wis": 12, "cha": 10, "ac": 13},
        hp=18, voice_preset="roguish_trickster",
        pitch_description="Nervous, furtive ex-soldier",
        exaggeration=0.6, speed_factor=1.1,
        dialogue_lines={
            "greeting": [
                "Don't — don't attack! I'm not with them anymore.",
            ],
            "quest": [
                "I was guild muscle. Torven sent us to guard the citadel.",
                "But what's in there... it's not natural. I ran.",
                "The main hall is trapped. Use the side corridor if you value your skin.",
            ],
            "lore": [
                "There's a man in there. Calls himself Lord Castellan.",
                "The Crown is doing something to him. He's not... right.",
                "The chapel is safe though. Old wards still hold.",
            ],
            "farewell": [
                "I'm heading south. Far south. Good luck.",
            ],
        })


# ── Citadel enemies ───────────────────────────────────────────────────────

def _lord_castellan_morvain() -> dict:
    return make_entity("Lord Castellan Morvain", "enemy",
        stats={
            "hp": 120, "max_hp": 120, "ac": 18, "speed": 30,
            "str": 18, "dex": 12, "con": 16, "int": 14, "wis": 10, "cha": 16,
            "level": 8,
        },
        hp=120, max_hp=120,
        voice_preset="warlord",
        pitch_description="Booming, unhinged — power corrupted",
        exaggeration=0.8, speed_factor=0.95,
        dialogue_lines={
            "greeting": [
                "Ah. More insects come to challenge the inevitable.",
            ],
            "combat": [
                "The Crown is mine! The forest, the land — ALL MINE!",
                "You cannot stop what has already begun!",
                "KNEEL before the true ruler of these lands!",
                "The blight is just the beginning.",
            ],
            "lore": [
                "Torven was a fool. A useful one, but a fool nonetheless.",
                "The Crown chose ME. Do you understand? It called to me across centuries.",
            ],
        })


def _corrupted_guard(index: int) -> dict:
    return make_entity(f"Corrupted Guard {index}", "enemy",
        stats={"str": 14, "dex": 11, "con": 13, "int": 8, "wis": 8, "cha": 8, "ac": 16, "speed": 30},
        hp=18, voice_preset="grizzled_veteran",
        pitch_description="Monotone, hollow — mind-controlled",
        exaggeration=0.3, speed_factor=0.9,
        dialogue_lines={
            "combat": [
                "Serve... the Crown...",
                "No one... leaves...",
            ],
        })


# ── SRD monster encounters ────────────────────────────────────────────────

def _wolf() -> dict:
    return make_entity("Blighted Wolf", "enemy",
        stats={"str": 12, "dex": 15, "con": 12, "int": 3, "wis": 12, "cha": 6, "ac": 13, "speed": 40},
        hp=11)


def _giant_spider() -> dict:
    return make_entity("Giant Spider", "enemy",
        stats={"str": 14, "dex": 16, "con": 12, "int": 2, "wis": 11, "cha": 4, "ac": 14, "speed": 30},
        hp=26)


def _manticore() -> dict:
    return make_entity("Razorclaw Manticore", "enemy",
        stats={"str": 17, "dex": 16, "con": 17, "int": 7, "wis": 12, "cha": 8, "ac": 14, "speed": 30},
        hp=68)


def _brown_bear() -> dict:
    return make_entity("Blighted Bear", "enemy",
        stats={"str": 19, "dex": 10, "con": 16, "int": 2, "wis": 13, "cha": 7, "ac": 11, "speed": 40},
        hp=34)


def _awakened_tree() -> dict:
    return make_entity("Blighted Tree", "enemy",
        stats={"str": 19, "dex": 6, "con": 15, "int": 10, "wis": 10, "cha": 7, "ac": 13, "speed": 20},
        hp=59)


def _wight() -> dict:
    return make_entity("Fallen Knight", "enemy",
        stats={"str": 15, "dex": 14, "con": 16, "int": 10, "wis": 13, "cha": 15, "ac": 14, "speed": 30},
        hp=45)


# ── Interactable objects ──────────────────────────────────────────────────

def _quest_board() -> dict:
    return make_entity("Quest Board", "object", hp=999, max_hp=999,
        stats={}, dialogue_lines={
            "lore": [
                "BOUNTY POSTED: A blight spreads from the Thornveil Forest. "
                "Reward offered for eliminating the source. Report to "
                "Captain Aldric at the Guard Post for details and authorization.",
            ],
        })


def _supply_crate() -> dict:
    return make_entity("Supply Crate", "object", hp=999, max_hp=999,
        inventory=["Torch", "50 ft. Rope", "Rations (3 days)", "Healer's Kit"])


def _shrine_inscription() -> dict:
    return make_entity("Shrine Inscription", "object", hp=999, max_hp=999,
        dialogue_lines={
            "lore": [
                "The inscription reads: 'I have cities but no houses, "
                "forests but no trees, water but no fish. What am I?' "
                "(Answer: A map)",
            ],
        })


def _healing_herb_patch() -> dict:
    return make_entity("Healing Herb Patch", "object", hp=999, max_hp=999,
        inventory=["Healing Herb", "Healing Herb"])


def _couriers_satchel() -> dict:
    return make_entity("Courier's Satchel", "object", hp=999, max_hp=999,
        dialogue_lines={
            "lore": [
                "The letter reads: 'Lord Castellan — The Crown is nearly "
                "attuned. The forest will be ours within the month. Continue "
                "the ritual. The guild's resources are at your disposal. "
                "— T.' (The letter is signed with a single 'T' — Torven.)",
            ],
        })


def _ancient_sword() -> dict:
    return make_entity("Ancient Sword", "object", hp=999, max_hp=999,
        inventory=["Longsword +1"],
        dialogue_lines={
            "lore": [
                "A finely crafted longsword rests in a stone alcove. "
                "It glows faintly when brought near the throne room.",
            ],
        })


def _alchemy_kit() -> dict:
    return make_entity("Alchemy Kit", "object", hp=999, max_hp=999,
        inventory=["Potion of Resistance (Necrotic)", "Potion of Healing"])


def _ward_stone() -> dict:
    return make_entity("Ward Stone", "object", hp=999, max_hp=999,
        dialogue_lines={
            "lore": [
                "A smooth white stone set into the chapel floor, engraved "
                "with protective runes. It hums with warm energy.",
            ],
        })


def _region_map_obj() -> dict:
    return make_entity("Region Map", "object", hp=999, max_hp=999,
        dialogue_lines={
            "lore": [
                "A large map of the region pinned behind the captain's desk. "
                "The Thornveil Forest is marked with red ink. An arrow points "
                "north toward the Valdris Citadel with the note: 'Source?'",
            ],
        })


def _trade_route_map() -> dict:
    return make_entity("Trade Route Map", "object", hp=999, max_hp=999,
        dialogue_lines={
            "lore": [
                "Maps on the wall show standard trade routes — and one "
                "marked path leading deep into the Thornveil Forest, circled "
                "in red ink. The destination is labelled 'V.C.'",
            ],
        })


def _locked_desk() -> dict:
    return make_entity("Locked Desk", "object", hp=999, max_hp=999,
        dialogue_lines={
            "lore": [
                "A heavy oak desk with an iron lock. Inside: ledgers showing "
                "large payments to 'L.C.M.' and a wax-sealed letter referencing "
                "'the Crown ritual'.",
            ],
        })


def _crown_chronicles() -> dict:
    return make_entity("Crown Chronicles", "object", hp=999, max_hp=999,
        dialogue_lines={
            "lore": [
                "A leather-bound book with the royal seal of the old kingdom. "
                "It chronicles the forging of the Hollow Crown and each ruler "
                "who wore it. Every entry ends the same way: madness, then ruin.",
            ],
        })


def _weapon_rack() -> dict:
    return make_entity("Weapon Rack", "object", hp=999, max_hp=999,
        inventory=["Shield +1"],
        dialogue_lines={
            "lore": [
                "Battered weapon racks line the walls. Most weapons are rusted, "
                "but one shield still gleams — enchanted, perhaps.",
            ],
        })


# ---------------------------------------------------------------------------
# Section 4 — Zone definitions
# ---------------------------------------------------------------------------

def _crossed_antlers_zones() -> list:
    """Zones for the Crossed Antlers tavern tile (2,7)."""
    return [
        make_zone("ca_entrance", "Entrance",
            description="Heavy oak doors open into the warmth of the tavern. "
                        "The smell of roasting meat and woodsmoke fills the air.",
            connections=["ca_main_hall"],
            tags=["indoor", "tavern"]),
        make_zone("ca_main_hall", "Main Hall",
            description="A smoky common room with low beams. The fire crackles "
                        "in the hearth. Several patrons nurse their drinks at "
                        "rough-hewn tables.",
            connections=["ca_entrance", "ca_back_room"],
            tags=["indoor", "tavern"],
            placements=[
                make_placement(_marta_ironbrew(), depth=3, x_percent=0.70,
                               interaction_types=["inspect", "trade"]),
                make_placement(_edda_thornfield(), depth=3, x_percent=0.25,
                               interaction_types=["inspect"]),
                make_placement(_voss_the_peddler(), depth=2, x_percent=0.40,
                               interaction_types=["inspect", "trade"]),
                make_placement(_quest_board(), depth=3, x_percent=0.90,
                               interaction_types=["inspect", "read"]),
            ]),
        make_zone("ca_back_room", "Back Room",
            description="A cramped storeroom with barrels stacked to the ceiling. "
                        "A trapdoor in the floor catches your eye.",
            connections=["ca_main_hall"],
            tags=["indoor", "storage"],
            placements=[
                make_placement(_supply_crate(), depth=3, x_percent=0.50,
                               interaction_types=["inspect", "open"]),
            ]),
    ]


def _guard_post_zones() -> list:
    """Zones for the Guard Post tile (3,8)."""
    return [
        make_zone("gp_main", "Guard Post",
            description="A sturdy stone building with weapon racks on the walls. "
                        "A large map of the region is pinned behind the captain's desk.",
            tags=["indoor", "military"],
            placements=[
                make_placement(_captain_aldric(), depth=3, x_percent=0.60,
                               interaction_types=["inspect"]),
                make_placement(_guard_holt(), depth=3, x_percent=0.20,
                               interaction_types=["inspect"]),
                make_placement(_region_map_obj(), depth=1, x_percent=0.50,
                               interaction_types=["inspect", "read"]),
            ]),
    ]


def _druids_clearing_zones() -> list:
    """Zones for the Druid's Clearing tile (7,10)."""
    return [
        make_zone("dc_clearing", "Druid's Clearing",
            description="A small clearing where the blight hasn't fully taken hold. "
                        "Faintly glowing runes are carved into the standing stones. "
                        "A figure in tattered green robes leans against the largest stone.",
            tags=["outdoor", "sacred"],
            placements=[
                make_placement(_thessaly(), depth=2, x_percent=0.50,
                               interaction_types=["inspect"]),
                make_placement(_healing_herb_patch(), depth=3, x_percent=0.80,
                               interaction_types=["inspect", "pickup"]),
            ]),
    ]


def _scholars_archive_zones() -> list:
    """Zones for the Scholar's Archive tile (14,9)."""
    return [
        make_zone("sa_reading_room", "Reading Room",
            description="Floor-to-ceiling shelves packed with scrolls and books. "
                        "Dust motes dance in the light from tall windows. The "
                        "archivist hunches over a massive tome.",
            connections=["sa_vault"],
            tags=["indoor", "library"],
            placements=[
                make_placement(_archivist_sera(), depth=3, x_percent=0.40,
                               interaction_types=["inspect"]),
            ]),
        make_zone("sa_vault", "Restricted Vault",
            description="Ancient texts behind iron bars. One shelf holds a "
                        "leather-bound book with the royal seal of the old kingdom.",
            connections=["sa_reading_room"],
            locked=True, lock_dc=20,
            tags=["indoor", "secure"],
            placements=[
                make_placement(_crown_chronicles(), depth=2, x_percent=0.50,
                               interaction_types=["inspect", "read"]),
            ]),
    ]


def _guild_hall_zones() -> list:
    """Zones for the Merchant Guild Hall tile (14,11)."""
    return [
        make_zone("gh_hall", "Guild Hall",
            description="Opulent marble floors, gilded columns. The wealth of "
                        "Ashenmere is on full display. Merchants and clerks bustle "
                        "between offices.",
            connections=["gh_office"],
            tags=["indoor", "wealthy"]),
        make_zone("gh_office", "Guildmaster's Office",
            description="A private office with heavy curtains and a locked desk. "
                        "Maps on the wall show trade routes — and one marked path "
                        "leading to the Thornveil Forest.",
            connections=["gh_hall"],
            tags=["indoor", "wealthy", "suspicious"],
            placements=[
                make_placement(_guildmaster_torven(), depth=3, x_percent=0.50,
                               interaction_types=["inspect"]),
                make_placement(_locked_desk(), depth=3, x_percent=0.80,
                               interaction_types=["inspect", "pick_lock"]),
                make_placement(_trade_route_map(), depth=1, x_percent=0.40,
                               interaction_types=["inspect"]),
            ]),
    ]


def _iron_flagon_zones() -> list:
    """Zones for the Iron Flagon tile (15,8)."""
    return [
        make_zone("if_common", "Common Room",
            description="A bustling inn with a roaring fireplace. The smell of "
                        "roasted meat and fresh bread fills the air. Travellers "
                        "and locals share tables and stories.",
            tags=["indoor", "tavern", "safe_rest"],
            placements=[
                make_placement(_innkeeper_bram(), depth=3, x_percent=0.60,
                               interaction_types=["inspect", "trade"]),
            ]),
    ]


def _barracks_zones() -> list:
    """Zones for the Ashenmere Barracks tile (15,12)."""
    return [
        make_zone("ab_main", "Barracks",
            description="Rows of bunks and weapon racks. City guards sharpen "
                        "blades and play dice. The commander watches from a "
                        "raised platform.",
            tags=["indoor", "military"],
            placements=[
                make_placement(_commander_vex(), depth=3, x_percent=0.50,
                               interaction_types=["inspect"]),
            ]),
    ]


def _corridor_zones() -> list:
    """Zones for the Citadel Corridors tile (21,10)."""
    return [
        make_zone("cc_entry", "Entry Corridor",
            description="Crumbling stone walls covered in blackened vines. "
                        "The air tastes of rot. Pressure plates are barely "
                        "visible beneath the dust.",
            connections=["cc_deep"],
            tags=["indoor", "dungeon", "trapped"]),
        make_zone("cc_deep", "Deep Corridor",
            description="The vines are thicker here, pulsing with a faint "
                        "purple light. The walls seem to breathe.",
            connections=["cc_entry"],
            tags=["indoor", "dungeon", "trapped"]),
    ]


def _guard_quarters_zones() -> list:
    """Zones for the Citadel Guard Quarters tile (22,11)."""
    return [
        make_zone("gq_main", "Guard Quarters",
            description="Bunks and weapon racks. Three soldiers sit in unnatural "
                        "stillness, their eyes glowing faintly purple. They don't "
                        "react until you enter.",
            tags=["indoor", "dungeon", "hostile"],
            placements=[
                make_placement(_corrupted_guard(1), depth=3, x_percent=0.25,
                               interaction_types=["inspect"]),
                make_placement(_corrupted_guard(2), depth=3, x_percent=0.50,
                               interaction_types=["inspect"]),
                make_placement(_corrupted_guard(3), depth=3, x_percent=0.75,
                               interaction_types=["inspect"]),
                make_placement(_weapon_rack(), depth=1, x_percent=0.90,
                               interaction_types=["inspect", "search"]),
            ]),
    ]


def _chapel_zones() -> list:
    """Zones for the Citadel Chapel tile (23,9)."""
    return [
        make_zone("ch_main", "Chapel",
            description="A small chapel bathed in warm light. The oppressive "
                        "atmosphere of the citadel doesn't reach here. Ancient "
                        "protective runes glow softly on the walls.",
            tags=["indoor", "sacred", "safe_rest"],
            placements=[
                make_placement(_ward_stone(), depth=2, x_percent=0.50,
                               interaction_types=["inspect", "use"]),
            ]),
    ]


# ---------------------------------------------------------------------------
# Section 5 — Trigger definitions
# ---------------------------------------------------------------------------

def _build_triggers() -> dict:
    """Return {(row,col): [trigger_dicts]} for all triggered tiles."""
    triggers = {}

    def _add(row, col, trig):
        triggers.setdefault((row, col), []).append(trig)

    # ── Millhaven ──────────────────────────────────────────────────────
    _add(2, 7, make_trigger("ENTER_TILE", "millhaven_arrival",
        always_true(),
        alert_gm("The party arrives in Millhaven. The Crossed Antlers tavern "
                  "stands before you, its sign creaking in the wind. A notice "
                  "board by the door is covered in postings.")))

    # ── Thornveil Forest ───────────────────────────────────────────────
    _add(6, 9, make_trigger("ENTER_TILE", "wolf_ambush",
        always_true(),
        alert_gm("Four wolves emerge from the undergrowth, their eyes wild "
                  "and tinged with purple. They attack without hesitation. "
                  "Roll initiative!")))

    _add(7, 8, make_trigger("ENTER_TILE", "shrine_riddle",
        always_true(),
        alert_gm("A ruined shrine stands among the trees. An inscription on "
                  "the central stone reads: 'I have cities but no houses, "
                  "forests but no trees, water but no fish. What am I?' "
                  "(Answer: A map)")))

    _add(7, 8, make_trigger("ENTER_TILE", "shrine_search",
        perception_check(12),
        alert_gm("You notice a loose stone at the base of the shrine. Behind "
                  "it: a Potion of Healing and 15 gold pieces.")))

    _add(8, 9, make_trigger("ENTER_TILE", "bridge_perception",
        perception_check(14),
        alert_gm("You notice the bridge planks are partially sawn through. "
                  "You can cross carefully (DEX check) or find another way.")))

    _add(8, 9, make_trigger("ENTER_TILE", "bridge_collapse",
        always_true(),
        apply_damage("bludgeoning", 7)))

    _add(8, 9, make_trigger("ENTER_TILE", "spider_ambush",
        always_true(),
        alert_gm("The crash attracts two giant spiders from beneath the bridge! "
                  "Roll initiative!")))

    # ── Greenreach ─────────────────────────────────────────────────────
    # (peaceful — no combat triggers, just atmosphere)

    # ── Ashenmere ──────────────────────────────────────────────────────
    _add(16, 9, make_trigger("ENTER_TILE", "manticore_attack",
        always_true(),
        alert_gm("A massive manticore swoops from a rocky outcropping east of "
                  "the road, its tail barbs already raised! Roll initiative!")))

    _add(16, 10, make_trigger("ENTER_TILE", "courier_body",
        always_true(),
        alert_gm("You find a courier's body half-hidden in the rocks beside "
                  "the road. A sealed letter in her satchel bears a crown "
                  "entwined with thorns.")))

    # ── Valdris Approach ───────────────────────────────────────────────
    _add(18, 10, make_trigger("ENTER_TILE", "fallen_knight",
        always_true(),
        alert_gm("A figure in rusted armour rises from the blighted ground. "
                  "The Fallen Knight's eyes burn with cold fire. Roll initiative!")))

    # ── Valdris Citadel ────────────────────────────────────────────────
    _add(21, 10, make_trigger("ENTER_TILE", "corridor_trap_spot",
        perception_check(15),
        alert_gm("You spot a pressure plate just in time and step around it.")))

    _add(21, 10, make_trigger("ENTER_TILE", "corridor_trap_damage",
        always_true(),
        apply_damage("piercing", 4)))

    _add(22, 11, make_trigger("ENTER_TILE", "poison_dart_dodge",
        perception_check(13),
        alert_gm("You dodge the poison darts shooting from the walls!")))

    _add(22, 11, make_trigger("ENTER_TILE", "poison_dart_hit",
        always_true(),
        apply_damage("poison", 4)))

    _add(23, 9, make_trigger("ENTER_TILE", "chapel_ward",
        always_true(),
        alert_gm("The ward stone glows with warm light. The oppressive "
                  "atmosphere lifts. You feel safe here — this is a place "
                  "of rest, protected from the Crown's influence. "
                  "You may take a long rest.")))

    _add(23, 10, make_trigger("ENTER_TILE", "boss_entry",
        always_true(),
        alert_gm("Lord Castellan Morvain sits on the ancient throne, the "
                  "Hollow Crown pulsing with dark energy on his brow. "
                  "Thorned vines spread from the Crown across the chamber "
                  "floor. He rises slowly. 'Ah. More insects come to "
                  "challenge the inevitable.' Roll initiative!")))

    return triggers


# ---------------------------------------------------------------------------
# Section 6 — Map tile builder
# ---------------------------------------------------------------------------

# Region boundary helpers

def _in_millhaven(r, c):
    """Rows 0-4, Cols 6-10 (town core)."""
    return 0 <= r <= 4 and 6 <= c <= 10

def _in_forest(r, c):
    """Rows 5-9, ragged shape centred on cols 7-10."""
    if r == 5 and c == 9:
        return True
    if r == 6 and 8 <= c <= 10:
        return True
    if r == 7 and 7 <= c <= 10:
        return True
    if r == 8 and 7 <= c <= 10:
        return True
    if r == 9 and 8 <= c <= 10:
        return True
    return False

def _in_greenreach(r, c):
    """Rows 10-11, Cols 8-10."""
    return 10 <= r <= 11 and 8 <= c <= 10

def _in_ashenmere(r, c):
    """Rows 12-16, Cols 7-12."""
    return 12 <= r <= 16 and 7 <= c <= 12

def _in_approach(r, c):
    """Rows 17-19, Cols 9-10."""
    return 17 <= r <= 19 and 9 <= c <= 10

def _in_citadel(r, c):
    """Rows 20-24, Cols 8-12."""
    return 20 <= r <= 24 and 8 <= c <= 12

def _is_road(r, c):
    """Road tiles connecting regions (not already in a region)."""
    roads = {(4, 9), (11, 9), (17, 9), (17, 10), (19, 9), (19, 10)}
    return (r, c) in roads

def _is_citadel_wall(r, c):
    """Outer wall of Valdris Citadel."""
    if r == 24 and 8 <= c <= 12:
        return True
    if 20 <= r <= 24 and c in (8, 12):
        return True
    return False


def _entity_map() -> dict:
    """Return {(row,col): [entity_dicts]} for tiles with free-standing entities."""
    entities = {}

    def _add(row, col, ent):
        entities.setdefault((row, col), []).append(ent)

    # Forest combat encounters
    _add(6, 9, _wolf())
    _add(6, 9, _wolf())
    _add(6, 9, _wolf())
    _add(6, 9, _wolf())
    _add(8, 9, _giant_spider())
    _add(8, 9, _giant_spider())

    # Greenreach NPC
    _add(10, 9, _old_renn())

    # Ashenmere subquest
    _add(16, 9, _manticore())
    _add(16, 10, _lira_the_courier())
    _add(16, 10, _couriers_satchel())

    # Approach
    _add(17, 10, _deserter_kael())
    _add(18, 10, _wight())
    _add(18, 10, _brown_bear())
    _add(18, 10, _brown_bear())
    _add(18, 10, _awakened_tree())

    # Citadel
    _add(22, 9, _alchemy_kit())
    _add(22, 10, _ancient_sword())
    _add(23, 10, _lord_castellan_morvain())

    return entities


def _zone_map() -> dict:
    """Return {(row,col): [zone_dicts]} for tiles with interior zones."""
    return {
        (2, 7): _crossed_antlers_zones(),
        (3, 8): _guard_post_zones(),
        (7, 10): _druids_clearing_zones(),
        (14, 9): _scholars_archive_zones(),
        (14, 11): _guild_hall_zones(),
        (15, 8): _iron_flagon_zones(),
        (15, 12): _barracks_zones(),
        (21, 10): _corridor_zones(),
        (22, 11): _guard_quarters_zones(),
        (23, 9): _chapel_zones(),
    }


# Key tile metadata: (row, col) -> (label, note)
_TILE_LABELS: dict[tuple, tuple] = {
    # Millhaven
    (0, 7): ("South Gate", "The southern entry to Millhaven. Wooden palisade walls frame the road."),
    (0, 8): ("South Gate", "The southern entry to Millhaven. A weathered signpost reads 'Millhaven'."),
    (1, 7): ("Stables", "A modest stable where travellers can board or rent horses."),
    (1, 8): ("Millhaven Road", "A dirt road leading into town."),
    (2, 7): ("The Crossed Antlers", "The main tavern of Millhaven. A warm glow spills from the windows."),
    (2, 8): ("Market Row", "A short lane with merchant stalls."),
    (3, 6): ("General Store", "Basic adventuring supplies at fair prices."),
    (3, 7): ("Town Square", "The central gathering area of Millhaven. A well stands in the centre."),
    (3, 8): ("Guard Post", "Captain Aldric's headquarters. A sturdy stone building."),
    (3, 9): ("Millhaven Chapel", "A small chapel dedicated to the harvest gods."),
    (4, 9): ("North Road", "The road north out of Millhaven, toward the Thornveil Forest."),

    # Thornveil Forest
    (5, 9): ("Forest Edge", "The tree line begins. Sunlight still filters through healthy canopy."),
    (6, 9): ("Wolf Den", "Torn earth and claw marks. The wolves here are not behaving normally."),
    (6, 10): ("Forest Path", "A narrow trail winding through the trees."),
    (7, 8): ("Ruined Shrine", "An ancient shrine half-swallowed by roots. Inscriptions remain legible."),
    (7, 9): ("Forest Trail", "The path continues north. The trees grow darker."),
    (7, 10): ("Druid's Clearing", "A small clearing with standing stones. Faint runes glow on the rocks."),
    (8, 9): ("Blighted Crossing", "A rope bridge spans a shallow ravine. The planks look questionable."),
    (8, 10): ("Dense Undergrowth", "Thick brambles. Movement here is slow."),
    (9, 8): ("Deep Forest", "The trees are blackened. A faint purple haze hangs in the air."),
    (9, 9): ("Deep Forest", "Blighted trees creak ominously. Dead animals litter the ground."),
    (9, 10): ("Deep Forest", "The corruption is thick here. Even the soil feels wrong."),

    # Greenreach
    (10, 8): ("Greenreach West", "Open pastureland stretching to the horizon."),
    (10, 9): ("Shepherd's Camp", "Old Renn tends his dwindling flock here. A safe place to rest."),
    (10, 10): ("Greenreach East", "Grassland dotted with wildflowers. Peaceful, for now."),
    (11, 9): ("North Pasture", "The grass thins toward Ashenmere. Wagon ruts mark the road."),

    # Ashenmere
    (12, 7): ("City Outskirts (W)", "The western edge of Ashenmere. Low buildings, laundry lines."),
    (12, 8): ("City Outskirts", "Modest homes and workshops."),
    (12, 9): ("South Gate", "The main southern entrance to Ashenmere. Guards check travellers."),
    (12, 10): ("City Outskirts", "A cobbled road leads into the city centre."),
    (12, 11): ("City Outskirts (E)", "Eastern residential district."),
    (12, 12): ("City Outskirts (E)", "The city wall curves northeast."),
    (13, 7): ("Residential", "Quiet streets. Shuttered windows."),
    (13, 8): ("Market District", "Stalls and shops line a wide avenue."),
    (13, 9): ("Central Avenue", "The main thoroughfare of Ashenmere. Busy with foot traffic."),
    (13, 10): ("Fountain Square", "A large fountain at the city's crossroads."),
    (13, 11): ("Merchant Row", "Wealthy merchant establishments."),
    (13, 12): ("Eastern Quarter", "Quiet residential area near the eastern wall."),
    (14, 9): ("Scholar's Archive", "A tall stone building filled with ancient texts."),
    (14, 11): ("Merchant Guild Hall", "An opulent hall displaying Ashenmere's wealth."),
    (15, 8): ("The Iron Flagon", "Ashenmere's finest inn. Good food, warm beds, cold ale."),
    (15, 12): ("Ashenmere Barracks", "The city guard's headquarters. Well-armed soldiers patrol."),
    (16, 7): ("North Wall (W)", "The northern city wall. A gate leads toward Valdris."),
    (16, 8): ("North Wall", "Fortified wall segment."),
    (16, 9): ("North Gate", "The gate toward the Valdris road. A manticore was spotted nearby."),
    (16, 10): ("East Road", "A road east of the gate. A courier lies dead in the rocks."),
    (16, 11): ("North Wall", "Fortified wall segment."),
    (16, 12): ("North Wall (E)", "The northeast corner of the city wall."),

    # Valdris Approach
    (17, 9): ("Blighted Road", "The road north. Trees are dead. The ground is grey."),
    (17, 10): ("Deserter's Camp", "A hasty campsite. Someone fled here recently."),
    (18, 10): ("Fallen Knight", "A blighted clearing. Something stirs in the dead earth."),
    (19, 9): ("Citadel Approach", "The road ends at a looming fortress."),
    (19, 10): ("Citadel Approach", "Crumbling walls visible ahead. The air hums with power."),

    # Valdris Citadel
    (20, 9): ("Citadel Entrance (W)", "The western side of the shattered entry hall."),
    (20, 10): ("Citadel Entrance", "The main entrance. Massive doors hang from broken hinges."),
    (20, 11): ("Citadel Entrance (E)", "The eastern side of the entry hall."),
    (21, 10): ("Corridors", "Trapped corridors winding deeper into the citadel."),
    (22, 9): ("Alchemy Lab", "A ransacked laboratory. Some potions remain intact."),
    (22, 10): ("Armoury", "An old armoury. A sword glows faintly in an alcove."),
    (22, 11): ("Guard Quarters", "Barracks. Corrupted soldiers wait in silence."),
    (23, 9): ("Chapel", "A safe haven. The Crown's corruption cannot reach here."),
    (23, 10): ("Throne Room", "The heart of the citadel. The Hollow Crown pulses with dark energy."),
}


def build_tiles() -> list:
    """Build all 625 tiles for the 25x25 grid."""
    trigger_map = _build_triggers()
    entity_map = _entity_map()
    zone_map = _zone_map()

    tiles = []
    for r in range(ROWS):
        for c in range(COLS):
            key = (r, c)
            label_info = _TILE_LABELS.get(key)
            label = label_info[0] if label_info else None
            note = label_info[1] if label_info else None
            entities = entity_map.get(key, [])
            trigs = trigger_map.get(key, [])
            zones = zone_map.get(key, [])

            # Determine terrain and properties
            if _is_citadel_wall(r, c):
                tiles.append(make_tile(r, c,
                    terrain="WALL",
                    tags=["BLOCKS_MOVEMENT", "BLOCKS_VISION"],
                    user_label="Citadel Wall",
                    note="Massive stone walls, impenetrable.",
                    overlay_color=COLOR_CITADEL))

            elif _in_citadel(r, c):
                tags = []
                if key == (23, 10):
                    note = (note or "") + " BOSS ENCOUNTER."
                tiles.append(make_tile(r, c,
                    terrain="FLOOR",
                    tags=tags,
                    user_label=label,
                    note=note,
                    overlay_color=COLOR_CITADEL,
                    entities=entities, triggers=trigs, zones=zones,
                    elevation=1))

            elif _in_approach(r, c):
                tiles.append(make_tile(r, c,
                    terrain="GRASS",
                    user_label=label,
                    note=note,
                    overlay_color=COLOR_APPROACH,
                    entities=entities, triggers=trigs, zones=zones))

            elif _in_ashenmere(r, c):
                tags = []
                tiles.append(make_tile(r, c,
                    terrain="FLOOR",
                    tags=tags,
                    user_label=label,
                    note=note,
                    overlay_color=COLOR_ASHENMERE,
                    entities=entities, triggers=trigs, zones=zones))

            elif _in_greenreach(r, c):
                tiles.append(make_tile(r, c,
                    terrain="GRASS",
                    user_label=label,
                    note=note,
                    overlay_color=COLOR_GREENREACH,
                    entities=entities, triggers=trigs, zones=zones))

            elif _in_forest(r, c):
                mc = 10 if r >= 8 else 5
                tiles.append(make_tile(r, c,
                    terrain="GRASS",
                    user_label=label,
                    note=note,
                    overlay_color=COLOR_FOREST,
                    entities=entities, triggers=trigs, zones=zones,
                    movement_cost=mc))

            elif _in_millhaven(r, c):
                tags = []
                if key == (2, 7):
                    tags.append("START_ZONE")
                tiles.append(make_tile(r, c,
                    terrain="FLOOR",
                    tags=tags,
                    user_label=label,
                    note=note,
                    overlay_color=COLOR_MILLHAVEN,
                    entities=entities, triggers=trigs, zones=zones))

            elif _is_road(r, c):
                tiles.append(make_tile(r, c,
                    terrain="FLOOR",
                    user_label=label or "Road",
                    note=note,
                    overlay_color=COLOR_ROAD,
                    entities=entities, triggers=trigs))

            else:
                # Background tile
                tiles.append(make_tile(r, c))

    return tiles


# ---------------------------------------------------------------------------
# Section 7 — Validation and main
# ---------------------------------------------------------------------------

def validate(map_data: dict) -> list:
    """Return a list of error strings. Empty list means valid."""
    errors = []

    tiles = map_data["tiles"]
    if len(tiles) != ROWS * COLS:
        errors.append(f"Expected {ROWS * COLS} tiles, got {len(tiles)}")

    start_zones = [t for t in tiles if "START_ZONE" in t.get("tags", [])]
    if not start_zones:
        errors.append("No START_ZONE tile found")

    for t in tiles:
        for e in t.get("entities", []):
            if not e.get("name"):
                errors.append(f"Entity without name on tile {t['tile_id']}")
        for z in t.get("zones", []):
            if not z.get("zone_id"):
                errors.append(f"Zone without zone_id on tile {t['tile_id']}")
            if not z.get("label"):
                errors.append(f"Zone without label on tile {t['tile_id']}")

    # Check trigger labels are unique
    all_labels = []
    for t in tiles:
        for trig in t.get("triggers", []):
            lbl = trig.get("label", "")
            if lbl in all_labels:
                errors.append(f"Duplicate trigger label: {lbl}")
            all_labels.append(lbl)

    # Check zone connections reference valid zone_ids within same tile
    for t in tiles:
        zone_ids = {z["zone_id"] for z in t.get("zones", [])}
        for z in t.get("zones", []):
            for conn in z.get("connections", []):
                if conn not in zone_ids:
                    errors.append(
                        f"Zone '{z['zone_id']}' on tile {t['tile_id']} "
                        f"connects to unknown zone '{conn}'")

    return errors


def main():
    tiles = build_tiles()

    map_data = {
        "version": "1.0",
        "meta": {
            "map_name": "The Hollow Crown",
            "author": "DnD World Builder Demo",
            "created": FIXED_TIMESTAMP,
            "grid_type": "square",
            "rows": ROWS,
            "cols": COLS,
        },
        "tiles": tiles,
        "entities": [],
    }

    errors = validate(map_data)
    if errors:
        print(f"\nVALIDATION FAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        raise SystemExit(1)

    WORKSPACE.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(map_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Summary
    total_entities = sum(len(t.get("entities", [])) for t in tiles)
    total_zones = sum(len(t.get("zones", [])) for t in tiles)
    total_triggers = sum(len(t.get("triggers", [])) for t in tiles)
    total_placements = sum(
        len(z.get("placements", []))
        for t in tiles for z in t.get("zones", []))
    labelled = sum(1 for t in tiles if t.get("user_label"))

    print(f"Scenario saved to {OUTPUT}")
    print(f"  Grid:        {ROWS}x{COLS} ({len(tiles)} tiles)")
    print(f"  Labelled:    {labelled} tiles")
    print(f"  Entities:    {total_entities} (on tiles)")
    print(f"  Zones:       {total_zones} (with {total_placements} placements)")
    print(f"  Triggers:    {total_triggers}")
    print(f"  Validation:  PASSED")


if __name__ == "__main__":
    main()
