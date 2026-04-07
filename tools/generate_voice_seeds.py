"""Generate synthetic voice seed files for Chatterbox TTS archetypes.

Creates 10 .wav files in core/audio/voice_seeds/.
These are development placeholders with harmonic content.

Usage: python tools/generate_voice_seeds.py
"""

import wave
import struct
import math
import random
from pathlib import Path

SEED_DIR = Path(__file__).parent.parent / "core" / "audio" / "voice_seeds"
SAMPLE_RATE = 22050
DURATION_SEC = 5.0

ARCHETYPES = {
    "grizzled_veteran": {"fundamental": 90, "harmonics": [1.0, 0.8, 0.6, 0.5, 0.3], "noise": 0.15},
    "mystic_elder": {"fundamental": 120, "harmonics": [1.0, 0.4, 0.3, 0.1], "noise": 0.05},
    "roguish_trickster": {"fundamental": 180, "harmonics": [1.0, 0.6, 0.5, 0.4, 0.2], "noise": 0.08},
    "warlord": {"fundamental": 75, "harmonics": [1.0, 0.9, 0.7, 0.6, 0.5, 0.3], "noise": 0.2},
    "scholar": {"fundamental": 150, "harmonics": [1.0, 0.3, 0.2, 0.1], "noise": 0.03},
    "barkeep": {"fundamental": 130, "harmonics": [1.0, 0.5, 0.4, 0.3, 0.2], "noise": 0.1},
    "ethereal": {"fundamental": 250, "harmonics": [1.0, 0.2, 0.1], "noise": 0.02},
    "narrator": {"fundamental": 160, "harmonics": [1.0, 0.4, 0.3, 0.2, 0.1], "noise": 0.04},
    "creepy_whisper": {"fundamental": 200, "harmonics": [0.3, 0.2, 0.1], "noise": 0.4},
    "young_adventurer": {"fundamental": 220, "harmonics": [1.0, 0.5, 0.3, 0.2], "noise": 0.06},
}


def generate_voice_seed(params):
    n_frames = int(SAMPLE_RATE * DURATION_SEC)
    fundamental = params["fundamental"]
    harmonics = params["harmonics"]
    noise_level = params["noise"]
    rng = random.Random(fundamental)

    data = []
    for i in range(n_frames):
        t = i / SAMPLE_RATE
        # Harmonic content
        sample = 0.0
        for h_idx, amplitude in enumerate(harmonics):
            freq = fundamental * (h_idx + 1)
            sample += math.sin(2 * math.pi * freq * t) * amplitude
        # Normalize
        sample /= sum(harmonics) if harmonics else 1
        # Add noise
        sample += (rng.random() * 2 - 1) * noise_level
        # Amplitude modulation (simulate speech rhythm)
        mod = 0.5 + 0.5 * math.sin(2 * math.pi * 3.5 * t)  # ~3.5 Hz syllable rate
        sample *= mod * 0.4
        data.append(int(max(-1, min(1, sample)) * 32767))

    return struct.pack(f"<{len(data)}h", *data)


def main():
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    for name, params in ARCHETYPES.items():
        path = SEED_DIR / f"{name}.wav"
        audio = generate_voice_seed(params)
        with wave.open(str(path), "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(SAMPLE_RATE)
            f.writeframes(audio)
        print(f"  Generated: {name}.wav")
    print(f"\nGenerated {len(ARCHETYPES)} voice seed files.")


if __name__ == "__main__":
    main()
