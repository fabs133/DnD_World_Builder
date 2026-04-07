"""Generate synthesized sound effects for all placeholder slots.

Replaces silent .wav placeholders with audible synthesized sounds.
These are development placeholders, not production audio.

Usage: python tools/generate_placeholder_sounds.py
"""

import wave
import struct
import math
import random
from pathlib import Path

SFX_ROOT = Path(__file__).parent.parent / "core" / "audio" / "sfx"
SAMPLE_RATE = 44100


def _samples(duration_ms, sr=SAMPLE_RATE):
    return int(sr * duration_ms / 1000)


def generate_sine(duration_ms, freq, volume=0.5, attack_ms=5, decay_ms=50):
    n = _samples(duration_ms)
    attack = _samples(attack_ms)
    decay = _samples(decay_ms)
    data = []
    for i in range(n):
        t = i / SAMPLE_RATE
        env = 1.0
        if i < attack:
            env = i / max(attack, 1)
        elif i > n - decay:
            env = (n - i) / max(decay, 1)
        sample = math.sin(2 * math.pi * freq * t) * volume * env
        data.append(int(max(-1, min(1, sample)) * 32767))
    return struct.pack(f"<{len(data)}h", *data)


def generate_noise_burst(duration_ms, volume=0.3, attack_ms=2, decay_ms=100):
    n = _samples(duration_ms)
    attack = _samples(attack_ms)
    decay = _samples(decay_ms)
    rng = random.Random(42)
    data = []
    for i in range(n):
        env = 1.0
        if i < attack:
            env = i / max(attack, 1)
        elif i > n - decay:
            env = (n - i) / max(decay, 1)
        sample = (rng.random() * 2 - 1) * volume * env
        data.append(int(max(-1, min(1, sample)) * 32767))
    return struct.pack(f"<{len(data)}h", *data)


def generate_click(duration_ms=30, freq=800):
    return generate_sine(duration_ms, freq, 0.4, 1, duration_ms - 2)


def generate_dice_roll(duration_ms=400):
    n = _samples(duration_ms)
    rng = random.Random(7)
    data = []
    for i in range(n):
        t = i / SAMPLE_RATE
        env = max(0, 1 - i / n)
        clicks = sum(math.sin(2 * math.pi * rng.uniform(300, 2000) * t)
                     for _ in range(3)) / 3
        sample = clicks * 0.3 * env
        data.append(int(max(-1, min(1, sample)) * 32767))
    return struct.pack(f"<{len(data)}h", *data)


def generate_bell(duration_ms=700, freq=440):
    return generate_sine(duration_ms, freq, 0.4, 2, duration_ms // 2)


def generate_sweep(duration_ms, start_freq, end_freq, volume=0.4):
    n = _samples(duration_ms)
    decay = _samples(max(50, duration_ms // 3))
    data = []
    for i in range(n):
        t = i / SAMPLE_RATE
        frac = i / max(n - 1, 1)
        freq = start_freq + (end_freq - start_freq) * frac
        env = 1.0 if i < n - decay else (n - i) / max(decay, 1)
        sample = math.sin(2 * math.pi * freq * t) * volume * env
        data.append(int(max(-1, min(1, sample)) * 32767))
    return struct.pack(f"<{len(data)}h", *data)


def generate_two_tone(duration_ms, freq1, freq2):
    half = duration_ms // 2
    return generate_sine(half, freq1, 0.4, 2, 20) + generate_sine(half, freq2, 0.4, 2, half - 10)


def write_wav(path, audio_data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(audio_data)


TOME = {
    "click.wav": lambda: generate_click(30, 600),
    "panel_open.wav": lambda: generate_sweep(200, 400, 800, 0.2),
    "panel_close.wav": lambda: generate_sweep(150, 800, 400, 0.2),
    "tab_switch.wav": lambda: generate_click(50, 500),
    "zone_enter.wav": lambda: generate_sweep(300, 300, 600, 0.3),
    "hover.wav": lambda: generate_click(15, 1000),
    "save.wav": lambda: generate_two_tone(200, 500, 700),
    "undo.wav": lambda: generate_sweep(150, 600, 400, 0.2),
    "error.wav": lambda: generate_two_tone(200, 400, 300),
    "npc_talk.wav": lambda: generate_click(80, 350),
    "locked.wav": lambda: generate_noise_burst(200, 0.2, 5, 150),
    "item_get.wav": lambda: generate_two_tone(200, 600, 900),
}

STONE = {
    "click.wav": lambda: generate_noise_burst(80, 0.3, 2, 60),
    "attack_01.wav": lambda: generate_noise_burst(200, 0.5, 2, 150),
    "attack_02.wav": lambda: generate_noise_burst(220, 0.5, 3, 160),
    "attack_03.wav": lambda: generate_noise_burst(180, 0.5, 2, 140),
    "attack_ranged.wav": lambda: generate_sweep(250, 800, 200, 0.3),
    "spell_01.wav": lambda: generate_sweep(300, 200, 1200, 0.3),
    "spell_02.wav": lambda: generate_sweep(320, 250, 1000, 0.3),
    "spell_03.wav": lambda: generate_sweep(280, 180, 1100, 0.3),
    "end_turn.wav": lambda: generate_click(150, 300),
    "dice_01.wav": lambda: generate_dice_roll(400),
    "dice_02.wav": lambda: generate_dice_roll(450),
    "dice_03.wav": lambda: generate_dice_roll(380),
    "damage_dealt_01.wav": lambda: generate_noise_burst(150, 0.4, 2, 100),
    "damage_dealt_02.wav": lambda: generate_noise_burst(170, 0.4, 3, 110),
    "damage_dealt_03.wav": lambda: generate_noise_burst(140, 0.4, 2, 90),
    "damage_taken_01.wav": lambda: generate_noise_burst(200, 0.5, 2, 150),
    "damage_taken_02.wav": lambda: generate_noise_burst(220, 0.5, 3, 160),
    "enemy_down_01.wav": lambda: generate_sweep(400, 500, 100, 0.3),
    "enemy_down_02.wav": lambda: generate_sweep(420, 480, 80, 0.3),
    "crit.wav": lambda: generate_two_tone(300, 800, 1200),
    "miss_01.wav": lambda: generate_sweep(200, 600, 300, 0.15),
    "miss_02.wav": lambda: generate_sweep(180, 550, 280, 0.15),
}

SHARED = {
    "combat_start.wav": lambda: generate_sweep(800, 100, 600, 0.5),
    "victory.wav": lambda: generate_two_tone(600, 400, 800),
    "defeat.wav": lambda: generate_sweep(800, 400, 80, 0.4),
    "initiative.wav": lambda: generate_dice_roll(600),
    "round_bell.wav": lambda: generate_bell(700, 440),
    "your_turn.wav": lambda: generate_two_tone(150, 800, 1200),
    "targeted.wav": lambda: generate_two_tone(400, 200, 150),
    "reaction.wav": lambda: generate_click(150, 900),
    "concentration.wav": lambda: generate_sweep(300, 600, 400, 0.2),
    "low_hp_warning.wav": lambda: generate_two_tone(500, 200, 180),
    "lock_in.wav": lambda: generate_click(100, 500),
    "level_up.wav": lambda: generate_sweep(500, 300, 1200, 0.4),
    "notification.wav": lambda: generate_two_tone(200, 600, 800),
}

AMBIENT = {
    "tavern.wav": lambda: generate_sine(2000, 120, 0.05, 100, 100),
    "forest.wav": lambda: generate_sine(2000, 80, 0.04, 100, 100),
    "dungeon.wav": lambda: generate_sine(2000, 60, 0.03, 100, 100),
    "cave.wav": lambda: generate_sine(2000, 50, 0.03, 100, 100),
    "combat_tension.wav": lambda: generate_sine(2000, 100, 0.05, 100, 100),
    "night.wav": lambda: generate_sine(2000, 70, 0.03, 100, 100),
}


def main():
    total = 0
    for subdir, sounds in [("tome", TOME), ("stone", STONE), ("shared", SHARED), ("ambient", AMBIENT)]:
        for filename, gen in sounds.items():
            write_wav(SFX_ROOT / subdir / filename, gen())
            total += 1
    print(f"Generated {total} sound files.")


if __name__ == "__main__":
    main()
