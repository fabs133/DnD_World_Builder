"""Hardware detection integration tests."""

from __future__ import annotations

import pytest

from core.system.hardware_profile import (
    AITier,
    HardwareProfile,
    detect_hardware,
)


class TestDetectHardware:
    def test_detect_hardware_succeeds(self):
        """detect_hardware() returns a valid HardwareProfile on any machine."""
        profile = detect_hardware()
        assert isinstance(profile, HardwareProfile)
        assert profile.cpu_cores >= 1
        assert profile.os_name != ""
        assert isinstance(profile.ollama_available, bool)

    def test_recommended_tier_is_valid(self):
        """recommended_tier returns a valid AITier."""
        profile = detect_hardware()
        tier = profile.recommended_tier
        assert isinstance(tier, AITier)
        assert tier in list(AITier)

    def test_to_dict_roundtrip(self):
        """HardwareProfile.to_dict() produces a valid dict."""
        profile = detect_hardware()
        d = profile.to_dict()
        assert isinstance(d, dict)
        assert "total_ram_gb" in d
        assert "gpu_name" in d
        assert "cpu_name" in d
        assert "cpu_cores" in d
        assert "os_name" in d
        assert "ollama_available" in d
        assert "recommended_tier" in d
        # Verify types
        assert isinstance(d["total_ram_gb"], (int, float))
        assert isinstance(d["cpu_cores"], int)
        assert isinstance(d["ollama_available"], bool)


class TestHardwareProfileTiers:
    """Test tier recommendation logic with known profiles."""

    def test_high_end_gpu_recommends_full_llm(self):
        profile = HardwareProfile(
            total_ram_gb=32.0,
            gpu_name="RTX 4090",
            gpu_vram_gb=24.0,
            cpu_name="i9",
            cpu_cores=16,
            os_name="Windows 11",
            ollama_available=True,
        )
        assert profile.recommended_tier == AITier.FULL_LLM

    def test_no_ollama_no_gpu_recommends_basic(self):
        profile = HardwareProfile(
            total_ram_gb=4.0,
            gpu_name="None",
            gpu_vram_gb=0.0,
            cpu_name="Atom",
            cpu_cores=2,
            os_name="Linux",
            ollama_available=False,
        )
        assert profile.recommended_tier == AITier.BASIC_DETERMINISTIC

    def test_no_ollama_8gb_ram_recommends_enhanced(self):
        profile = HardwareProfile(
            total_ram_gb=8.0,
            gpu_name="None",
            gpu_vram_gb=0.0,
            cpu_name="i5",
            cpu_cores=4,
            os_name="Windows",
            ollama_available=False,
        )
        assert profile.recommended_tier == AITier.ENHANCED_DETERMINISTIC

    def test_ollama_16gb_ram_recommends_lite(self):
        profile = HardwareProfile(
            total_ram_gb=16.0,
            gpu_name="None",
            gpu_vram_gb=0.0,
            cpu_name="i7",
            cpu_cores=8,
            os_name="macOS",
            ollama_available=True,
        )
        assert profile.recommended_tier == AITier.LITE_LLM
