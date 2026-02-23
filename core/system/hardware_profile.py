"""Auto-detect hardware capabilities and recommend an AI tier.

Uses only stdlib — no psutil or other external dependencies.
Safe on all platforms (returns sensible defaults on detection failure).
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum


class AITier(Enum):
    """AI capability tier based on detected hardware."""

    FULL_LLM = "full_llm"
    LITE_LLM = "lite_llm"
    ENHANCED_DETERMINISTIC = "enhanced_deterministic"
    BASIC_DETERMINISTIC = "basic_deterministic"


@dataclass(frozen=True)
class HardwareProfile:
    """Detected hardware capabilities."""

    total_ram_gb: float
    gpu_name: str
    gpu_vram_gb: float
    cpu_name: str
    cpu_cores: int
    os_name: str
    ollama_available: bool

    @property
    def recommended_tier(self) -> AITier:
        """Recommend an AI tier based on hardware."""
        if not self.ollama_available:
            if self.total_ram_gb >= 8:
                return AITier.ENHANCED_DETERMINISTIC
            return AITier.BASIC_DETERMINISTIC

        if self.gpu_vram_gb >= 8 and self.total_ram_gb >= 16:
            return AITier.FULL_LLM
        if self.gpu_vram_gb >= 4 and self.total_ram_gb >= 16:
            return AITier.LITE_LLM
        if self.total_ram_gb >= 16:
            return AITier.LITE_LLM
        if self.total_ram_gb >= 8:
            return AITier.ENHANCED_DETERMINISTIC
        return AITier.BASIC_DETERMINISTIC

    def to_dict(self) -> dict:
        return {
            "total_ram_gb": round(self.total_ram_gb, 1),
            "gpu_name": self.gpu_name,
            "gpu_vram_gb": round(self.gpu_vram_gb, 1),
            "cpu_name": self.cpu_name,
            "cpu_cores": self.cpu_cores,
            "os_name": self.os_name,
            "ollama_available": self.ollama_available,
            "recommended_tier": self.recommended_tier.value,
        }


def detect_hardware() -> HardwareProfile:
    """Detect current hardware capabilities.

    Safe on all platforms — returns sensible defaults on failure.
    """
    total_ram_gb = _detect_ram()
    gpu_name, gpu_vram_gb = _detect_gpu()
    cpu_name = platform.processor() or "Unknown"
    cpu_cores = os.cpu_count() or 1
    os_name = f"{platform.system()} {platform.release()}"
    ollama_available = shutil.which("ollama") is not None

    return HardwareProfile(
        total_ram_gb=total_ram_gb,
        gpu_name=gpu_name,
        gpu_vram_gb=gpu_vram_gb,
        cpu_name=cpu_name,
        cpu_cores=cpu_cores,
        os_name=os_name,
        ollama_available=ollama_available,
    )


def _detect_ram() -> float:
    """Detect total system RAM in GB. Returns 0.0 on failure."""
    system = platform.system()
    try:
        if system == "Windows":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return stat.ullTotalPhys / (1024**3)

        elif system == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        kb = int(line.split()[1])
                        return kb / (1024 * 1024)

        elif system == "Darwin":
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return int(result.stdout.strip()) / (1024**3)
    except Exception:
        pass
    return 0.0


def _detect_gpu() -> tuple[str, float]:
    """Detect GPU name and VRAM in GB. Returns ("None", 0.0) on failure."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(", ")
            name = parts[0].strip()
            vram_mb = float(parts[1].strip())
            return name, vram_mb / 1024
    except Exception:
        pass
    return ("None", 0.0)
