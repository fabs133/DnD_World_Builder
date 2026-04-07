"""Built-in voice archetype presets."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from core.voice.voice_profile import VoiceProfile


@dataclass
class VoicePreset:
    """A named voice archetype with default parameters."""

    preset_id: str
    name: str
    description: str
    reference_audio_filename: Optional[str] = None
    default_exaggeration: float = 0.5
    default_speed: float = 1.0
    default_cfg_weight: float = 0.5
    suggested_for: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_voice_profile(self) -> VoiceProfile:
        ref_audio = None
        if self.reference_audio_filename:
            seeds_dir = Path(__file__).resolve().parent.parent / "audio" / "voice_seeds"
            ref_audio = str(seeds_dir / self.reference_audio_filename)
        return VoiceProfile(
            source_type="preset" if ref_audio else "none",
            reference_audio=ref_audio,
            preset_name=self.preset_id,
            exaggeration=self.default_exaggeration,
            speed_factor=self.default_speed,
            cfg_weight=self.default_cfg_weight,
        )


VOICE_PRESETS: Dict[str, VoicePreset] = {}


def register_preset(preset: VoicePreset) -> None:
    VOICE_PRESETS[preset.preset_id] = preset


def get_preset(preset_id: str) -> Optional[VoicePreset]:
    return VOICE_PRESETS.get(preset_id)


def list_presets() -> List[VoicePreset]:
    return list(VOICE_PRESETS.values())


def get_presets_for_entity_type(entity_type: str) -> List[VoicePreset]:
    return [p for p in VOICE_PRESETS.values() if entity_type in p.suggested_for]


def auto_select_preset(
    entity_name: str,
    entity_type: str = "",
    gender: str = "",
    role: str = "",
) -> Optional[VoicePreset]:
    """Auto-select a voice preset based on entity tags.

    Matches by: gender > role/type > fallback.
    """
    gender = gender.lower().strip()
    role = role.lower().strip()
    etype = entity_type.lower().strip()

    # Collect candidates matching role/type
    candidates = get_presets_for_entity_type(role) if role else []
    if not candidates:
        candidates = get_presets_for_entity_type(etype)

    # Filter by gender tag if specified
    if gender and candidates:
        gendered = [p for p in candidates if gender in p.tags]
        if gendered:
            candidates = gendered

    # If no role match, filter all presets by gender
    if not candidates and gender:
        candidates = [p for p in VOICE_PRESETS.values() if gender in p.tags]

    # Fallback: pick by gender alone
    if not candidates:
        if gender == "female":
            return get_preset("elder_woman")
        return get_preset("narrator")

    return candidates[0]


# ── Built-in Presets ─────────────────────────────────────────────────────
#
# Presets with reference_audio_filename use Chatterbox voice cloning from
# the referenced seed in core/audio/voice_seeds/.  Presets without a
# reference fall back to Chatterbox's default voice with parameter tuning.

# --- Male voices (cloned from LibriVox recordings) -----------------------

register_preset(VoicePreset(
    preset_id="grizzled_veteran", name="Grizzled Veteran",
    description="Deep, weathered, slow. Guards, blacksmiths, old soldiers.",
    reference_audio_filename="old_soldier.wav",
    default_exaggeration=0.3, default_speed=0.9,
    suggested_for=["guard", "blacksmith", "soldier"],
    tags=["deep", "male", "old", "serious"],
))

register_preset(VoicePreset(
    preset_id="warlord", name="Warlord",
    description="Commanding, booming, aggressive. Bosses, generals, orc chiefs.",
    reference_audio_filename="old_soldier.wav",
    default_exaggeration=0.8, default_speed=0.9, default_cfg_weight=0.3,
    suggested_for=["boss", "general", "orc"],
    tags=["commanding", "loud", "aggressive"],
))

register_preset(VoicePreset(
    preset_id="narrator", name="Narrator",
    description="Neutral, clear, authoritative. DM narration, system voice.",
    reference_audio_filename="narrator_male.wav",
    default_exaggeration=0.3, default_speed=1.0,
    suggested_for=["narrator", "dm", "system"],
    tags=["neutral", "clear", "authoritative", "male"],
))

register_preset(VoicePreset(
    preset_id="roguish_trickster", name="Roguish Trickster",
    description="Quick, sly storytelling. Thieves, merchants, bards, travellers.",
    reference_audio_filename="sly_merchant.wav",
    default_exaggeration=0.6, default_speed=1.1,
    suggested_for=["thief", "merchant", "bard", "traveller"],
    tags=["quick", "sly", "male", "storytelling"],
))

register_preset(VoicePreset(
    preset_id="barkeep", name="Barkeep",
    description="Warm, hearty, friendly. Innkeepers, farmers, common folk.",
    reference_audio_filename="sly_merchant.wav",
    default_exaggeration=0.4, default_speed=1.0,
    suggested_for=["innkeeper", "farmer", "barkeep"],
    tags=["warm", "hearty", "friendly", "male"],
))

register_preset(VoicePreset(
    preset_id="scholar", name="Scholar",
    description="Precise, articulate. Wizards, librarians, scribes.",
    reference_audio_filename="narrator_male.wav",
    default_exaggeration=0.2, default_speed=1.05,
    suggested_for=["wizard", "librarian", "scribe"],
    tags=["precise", "intellectual", "male"],
))

register_preset(VoicePreset(
    preset_id="young_adventurer", name="Young Adventurer",
    description="Eager, bright, energetic. Apprentices, young NPCs.",
    reference_audio_filename="narrator_male.wav",
    default_exaggeration=0.6, default_speed=1.15,
    suggested_for=["apprentice", "youth", "squire"],
    tags=["eager", "bright", "young", "male"],
))

register_preset(VoicePreset(
    preset_id="gruff_merchant", name="Gruff Merchant",
    description="Rough, direct, impatient. Miners, dockworkers, grumpy shopkeeps.",
    reference_audio_filename="old_soldier.wav",
    default_exaggeration=0.5, default_speed=1.05,
    suggested_for=["miner", "dockworker", "shopkeep"],
    tags=["male", "gruff", "impatient"],
))

register_preset(VoicePreset(
    preset_id="sly_traveller", name="Sly Traveller",
    description="Smooth, unhurried, slightly amused. Spies, informants, gamblers.",
    reference_audio_filename="sly_merchant.wav",
    default_exaggeration=0.7, default_speed=0.95, default_cfg_weight=0.3,
    suggested_for=["spy", "informant", "gambler"],
    tags=["male", "smooth", "sly"],
))

# --- Female / character voices (cloned from LibriVox) --------------------

register_preset(VoicePreset(
    preset_id="elder_woman", name="Elder Woman",
    description="Aged, caring, stern. Nuns, witches, caretakers, healers.",
    reference_audio_filename="elder_woman.wav",
    default_exaggeration=0.4, default_speed=0.9,
    suggested_for=["nun", "witch", "caretaker", "healer", "herbalist"],
    tags=["female", "old", "caring", "stern"],
))

register_preset(VoicePreset(
    preset_id="warm_woman", name="Warm Woman",
    description="Friendly, lively, slightly faster. Barkeeps, merchants, innkeepers.",
    reference_audio_filename="elder_woman.wav",
    default_exaggeration=0.5, default_speed=1.05,
    suggested_for=["barkeep", "innkeeper", "merchant"],
    tags=["female", "warm", "friendly"],
))

register_preset(VoicePreset(
    preset_id="stern_woman", name="Stern Woman",
    description="Commanding, deliberate, intense. Warriors, captains, guards.",
    reference_audio_filename="elder_woman.wav",
    default_exaggeration=0.6, default_speed=0.85, default_cfg_weight=0.3,
    suggested_for=["warrior", "captain", "guard", "soldier"],
    tags=["female", "commanding", "stern"],
))

register_preset(VoicePreset(
    preset_id="mystic_seer", name="Mystic Seer",
    description="Accented, mystical, prophetic. Seers, oracles, fortune tellers.",
    reference_audio_filename="mystic_seer.wav",
    default_exaggeration=0.7, default_speed=0.85, default_cfg_weight=0.3,
    suggested_for=["seer", "oracle", "fortune_teller", "prophet"],
    tags=["mystical", "accented", "prophetic"],
))

register_preset(VoicePreset(
    preset_id="mystic_elder", name="Mystic Elder",
    description="Soft, measured, wise. Sages, clerics, elven elders.",
    reference_audio_filename="mystic_seer.wav",
    default_exaggeration=0.4, default_speed=0.85,
    suggested_for=["sage", "cleric", "elder"],
    tags=["soft", "wise", "calm"],
))

# --- Stylized voices (parameter-tuned, no reference) --------------------

register_preset(VoicePreset(
    preset_id="ethereal", name="Ethereal",
    description="Airy, otherworldly, melodic. Druids, fey creatures, spirits.",
    default_exaggeration=0.7, default_speed=0.8, default_cfg_weight=0.3,
    suggested_for=["druid", "fey", "spirit"],
    tags=["airy", "otherworldly", "melodic"],
))

register_preset(VoicePreset(
    preset_id="creepy_whisper", name="Creepy Whisper",
    description="Hushed, unsettling. Liches, warlocks, undead.",
    default_exaggeration=0.8, default_speed=0.75, default_cfg_weight=0.3,
    suggested_for=["lich", "warlock", "undead"],
    tags=["hushed", "creepy", "unsettling"],
))
