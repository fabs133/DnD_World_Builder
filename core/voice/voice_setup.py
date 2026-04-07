"""Voice system detection and setup — adapted from agent-workflow preflight pattern.

Pure Python, no Qt dependency. Detects Chatterbox availability, hardware tier,
and provides install/verify functionality.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class VoiceSetupState(Enum):
    """Current state of the voice system."""
    READY = "ready"              # Chatterbox + torch + CUDA all working
    READY_CPU = "ready_cpu"      # Works but CPU only (slow)
    MISSING_PACKAGE = "missing"  # chatterbox-tts not installed
    TORCH_MISSING = "no_torch"   # torch not installed
    IMPORT_ERROR = "error"       # Installed but import fails


def detect_voice_system() -> tuple[VoiceSetupState, str]:
    """Detect the current state of the voice system.

    Returns (state, detail_message).
    """
    # 1. Check if chatterbox is importable
    try:
        from chatterbox.tts import ChatterboxTTS  # noqa: F401
    except ImportError:
        return VoiceSetupState.MISSING_PACKAGE, "chatterbox-tts is not installed"
    except Exception as e:
        return VoiceSetupState.IMPORT_ERROR, f"Import error: {e}"

    # 2. Check torch
    try:
        import torch
    except ImportError:
        return VoiceSetupState.TORCH_MISSING, "PyTorch is not installed"

    # 3. Check CUDA
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        return VoiceSetupState.READY, f"GPU: {gpu_name} ({vram:.1f} GB VRAM)"
    else:
        return VoiceSetupState.READY_CPU, "CPU only (no CUDA GPU detected)"


def get_installed_version() -> str | None:
    """Return the installed chatterbox-tts version, or None."""
    try:
        import importlib.metadata
        return importlib.metadata.version("chatterbox-tts")
    except Exception:
        return None


def install_chatterbox(
    on_output: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Install chatterbox-tts via pip in the current Python environment.

    Args:
        on_output: Callback receiving each line of pip output.

    Returns (success, message).
    """
    cmd = [sys.executable, "-m", "pip", "install", "chatterbox-tts"]

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        output_lines = []
        for line in process.stdout:
            line = line.rstrip()
            output_lines.append(line)
            if on_output:
                on_output(line)

        process.wait()

        if process.returncode == 0:
            # Verify the install worked
            state, detail = detect_voice_system()
            if state in (VoiceSetupState.READY, VoiceSetupState.READY_CPU):
                return True, f"Installed successfully. {detail}"
            else:
                return False, f"Installed but: {detail}"
        else:
            last_lines = "\n".join(output_lines[-5:])
            return False, f"pip failed (exit {process.returncode}):\n{last_lines}"

    except Exception as e:
        return False, f"Install error: {e}"


def verify_chatterbox() -> tuple[bool, str]:
    """Load the model and generate a test utterance.

    Returns (success, message).
    """
    state, detail = detect_voice_system()
    if state not in (VoiceSetupState.READY, VoiceSetupState.READY_CPU):
        return False, f"Not ready: {detail}"

    try:
        from chatterbox.tts import ChatterboxTTS
        import time

        device = "cuda" if state == VoiceSetupState.READY else "cpu"
        logger.info(f"Verification: loading model on {device}...")
        model = ChatterboxTTS.from_pretrained(device=device)

        logger.info("Verification: generating test audio...")
        start = time.time()
        wav = model.generate("Hello, this is a test.")
        elapsed = time.time() - start

        if wav is not None:
            return True, f"Verified OK ({elapsed:.1f}s on {device})"
        else:
            return False, "Generation returned None"

    except Exception as e:
        return False, f"Verification failed: {e}"
