"""Voice configuration for a game entity.

Pure Python — no Qt dependency.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VoiceProfile:
    """Per-entity voice configuration for TTS generation.

    Normal settings:
        exaggeration: Emotion intensity 0.0–1.0 (0=calm, 1=dramatic).
        speed_factor: Post-processing speed 0.7–1.3.
        cfg_weight: Voice similarity to reference 0.0–1.0.

    Advanced settings (Chatterbox sampling):
        temperature: Naturalness vs randomness 0.1–1.5.
        top_p: Nucleus sampling threshold 0.5–1.0.
        min_p: Minimum token probability 0.0–0.2.
        repetition_penalty: Anti-repetition strength 1.0–2.0.
    """

    voice_id: str = ""
    source_type: str = "none"  # "preset", "recorded", "uploaded", "none"
    reference_audio: Optional[str] = None
    preset_name: Optional[str] = None

    # Normal settings
    exaggeration: float = 0.5
    speed_factor: float = 1.0
    cfg_weight: float = 0.5
    language: str = "en"
    pitch_description: str = ""

    # Advanced settings
    temperature: float = 0.8
    top_p: float = 1.0
    min_p: float = 0.05
    repetition_penalty: float = 1.2

    # Effects
    apply_effects: bool = True

    def __post_init__(self):
        if not self.voice_id:
            self.voice_id = uuid.uuid4().hex[:12]

    @property
    def is_voiced(self) -> bool:
        """True if this profile has a voice source configured."""
        return self.source_type != "none" and self.reference_audio is not None

    def to_dict(self) -> dict:
        return {
            "voice_id": self.voice_id,
            "source_type": self.source_type,
            "reference_audio": self.reference_audio,
            "preset_name": self.preset_name,
            "exaggeration": self.exaggeration,
            "speed_factor": self.speed_factor,
            "cfg_weight": self.cfg_weight,
            "language": self.language,
            "pitch_description": self.pitch_description,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "min_p": self.min_p,
            "repetition_penalty": self.repetition_penalty,
            "apply_effects": self.apply_effects,
        }

    @staticmethod
    def deterministic_voice_id(entity_name: str, preset_name: str) -> str:
        """Stable voice_id from entity + preset — same inputs always give same ID."""
        raw = f"{entity_name}|{preset_name}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    @classmethod
    def from_dict(cls, data: dict) -> VoiceProfile:
        return cls(
            voice_id=data.get("voice_id", ""),
            source_type=data.get("source_type", "none"),
            reference_audio=data.get("reference_audio"),
            preset_name=data.get("preset_name"),
            exaggeration=data.get("exaggeration", 0.5),
            speed_factor=data.get("speed_factor", 1.0),
            cfg_weight=data.get("cfg_weight", 0.5),
            language=data.get("language", "en"),
            pitch_description=data.get("pitch_description", ""),
            temperature=data.get("temperature", 0.8),
            top_p=data.get("top_p", 1.0),
            min_p=data.get("min_p", 0.05),
            repetition_penalty=data.get("repetition_penalty", 1.2),
            apply_effects=data.get("apply_effects", True),
        )
