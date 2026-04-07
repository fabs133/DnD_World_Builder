"""Chatterbox TTS wrapper with graceful degradation.

All chatterbox imports are guarded. Returns None when unavailable.
"""

from __future__ import annotations

import logging
import threading
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from core.voice.voice_profile import VoiceProfile

logger = logging.getLogger(__name__)


# Configurable trim duration (set by VoiceSettingsWidget)
_TRIM_SECONDS: float = 0.05


def _postprocess_audio(samples, sample_rate: int = 24000):
    """Clean up TTS output: remove hum, filter noise, normalize."""
    import numpy as np

    # 1. Hard-trim warm-up hum (user-configurable via _TRIM_SECONDS)
    trim_samples = int(sample_rate * _TRIM_SECONDS)
    if len(samples) > trim_samples * 2:
        samples = samples[trim_samples:]

    # 2. Simple high-pass filter (~80Hz cutoff) to remove low-frequency drone
    # Using a first-order RC high-pass: y[n] = alpha * (y[n-1] + x[n] - x[n-1])
    rc = 1.0 / (2.0 * 3.14159 * 80.0)
    dt = 1.0 / sample_rate
    alpha = rc / (rc + dt)
    filtered = np.zeros_like(samples)
    filtered[0] = samples[0]
    for i in range(1, len(samples)):
        filtered[i] = alpha * (filtered[i - 1] + samples[i] - samples[i - 1])
    samples = filtered

    # 3. Trim leading silence (speech onset detection)
    threshold = 0.02
    above = np.where(np.abs(samples) > threshold)[0]
    if len(above) > 0:
        start = max(0, above[0] - int(sample_rate * 0.01))
        samples = samples[start:]

    # 4. Trim trailing silence
    above = np.where(np.abs(samples) > threshold)[0]
    if len(above) > 0:
        end = min(len(samples), above[-1] + int(sample_rate * 0.05))
        samples = samples[:end]

    # 5. Normalize peak to 0.90
    peak = np.abs(samples).max()
    if peak > 0.01:
        samples = samples * (0.90 / peak)

    # 6. Fade-in (50ms) and fade-out (30ms)
    fade_in = int(sample_rate * 0.05)
    if len(samples) > fade_in:
        samples[:fade_in] *= np.linspace(0.0, 1.0, fade_in, dtype=np.float32)
    fade_out = int(sample_rate * 0.03)
    if len(samples) > fade_out:
        samples[-fade_out:] *= np.linspace(1.0, 0.0, fade_out, dtype=np.float32)

    return samples


class HardwareTier(Enum):
    GPU = "gpu"
    CPU = "cpu"
    NONE = "none"


class VoiceEngine:
    """Singleton wrapper around Chatterbox TTS."""

    _instance: Optional[VoiceEngine] = None
    _lock = threading.Lock()

    @classmethod
    def instance(cls) -> VoiceEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        if cls._instance:
            cls._instance.unload_model()
        cls._instance = None

    def __init__(self, model_variant: str = "turbo"):
        self._model_variant = model_variant
        self._model = None
        self._tier: HardwareTier | None = None
        self._load_lock = threading.Lock()

    def detect_hardware(self) -> HardwareTier:
        if self._tier is not None:
            return self._tier

        try:
            import chatterbox  # noqa: F401
        except ImportError:
            logger.info("Chatterbox not installed — voice system disabled")
            self._tier = HardwareTier.NONE
            return self._tier

        try:
            import torch
            if torch.cuda.is_available():
                self._tier = HardwareTier.GPU
            else:
                self._tier = HardwareTier.CPU
        except ImportError:
            self._tier = HardwareTier.CPU

        logger.info(f"Voice hardware tier: {self._tier.value}")
        return self._tier

    def load_model(self, on_progress: Callable[[str, float], None] | None = None) -> bool:
        with self._load_lock:
            if self._model is not None:
                return True

            tier = self.detect_hardware()
            if tier == HardwareTier.NONE:
                return False

            try:
                if on_progress:
                    on_progress("loading", 0.0)

                device = "cuda" if tier == HardwareTier.GPU else "cpu"

                if self._model_variant == "turbo":
                    try:
                        from chatterbox.tts_turbo import ChatterboxTurboTTS
                        self._model = ChatterboxTurboTTS.from_pretrained(device=device)
                        logger.info(f"Chatterbox Turbo model loaded on {device}")
                    except (ImportError, Exception) as e:
                        logger.warning(f"Turbo model unavailable ({e}), falling back to standard")
                        from chatterbox.tts import ChatterboxTTS
                        self._model = ChatterboxTTS.from_pretrained(device=device)
                        logger.info(f"Chatterbox standard model loaded on {device}")
                        self._model_variant = "standard"
                else:
                    from chatterbox.tts import ChatterboxTTS
                    self._model = ChatterboxTTS.from_pretrained(device=device)
                    logger.info(f"Chatterbox standard model loaded on {device}")

                if on_progress:
                    on_progress("ready", 1.0)

                return True
            except Exception as e:
                logger.error(f"Failed to load Chatterbox model: {e}")
                self._tier = HardwareTier.NONE
                return False

    def generate(
        self,
        text: str,
        profile: VoiceProfile,
        reference_audio_path: Path | None = None,
    ) -> bytes | None:
        if self.detect_hardware() == HardwareTier.NONE:
            return None

        if self._model is None:
            if not self.load_model():
                return None

        try:
            ref_path = reference_audio_path
            if ref_path is None and profile.reference_audio:
                ref_path = Path(profile.reference_audio)

            if self._model_variant == "turbo":
                # Turbo ignores exaggeration/cfg_weight/min_p — use its
                # own defaults and only pass params it actually uses.
                kwargs: dict[str, Any] = {
                    "text": text,
                    "temperature": getattr(profile, "temperature", 0.8),
                    "top_p": getattr(profile, "top_p", 0.95),
                    "repetition_penalty": getattr(profile, "repetition_penalty", 1.35),
                }
            else:
                kwargs: dict[str, Any] = {
                    "text": text,
                    "exaggeration": profile.exaggeration,
                    "cfg_weight": profile.cfg_weight,
                    "temperature": getattr(profile, "temperature", 0.8),
                    "top_p": getattr(profile, "top_p", 1.0),
                    "min_p": getattr(profile, "min_p", 0.05),
                    "repetition_penalty": getattr(profile, "repetition_penalty", 1.2),
                }
            if ref_path and ref_path.exists():
                kwargs["audio_prompt_path"] = str(ref_path)

            wav = self._model.generate(**kwargs)

            if wav is None:
                return None

            # Convert to numpy float32
            import io
            import wave
            import numpy as np

            if hasattr(wav, "cpu"):  # torch.Tensor
                wav = wav.cpu().numpy()
            if isinstance(wav, np.ndarray):
                samples = wav.flatten().astype(np.float32)
            else:
                return wav  # already bytes

            # Post-process: trim silence, normalize, fade-in
            samples = _postprocess_audio(samples, self.get_sample_rate())

            # Apply character-specific audio effects (reverb, chorus, etc.)
            if getattr(profile, 'apply_effects', True):
                from core.voice.voice_effects import apply_voice_effects
                samples = apply_voice_effects(
                    samples, self.get_sample_rate(), profile.preset_name)

            # Encode as 16-bit PCM WAV
            pcm = (samples * 32767).astype(np.int16).tobytes()
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.get_sample_rate())
                wf.writeframes(pcm)
            return buf.getvalue()

        except Exception as e:
            logger.error(f"Voice generation failed: {e}")
            return None

    def get_sample_rate(self) -> int:
        return 24000

    def unload_model(self) -> None:
        self._model = None
        logger.info("Chatterbox model unloaded")
