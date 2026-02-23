"""Tests for hardware profile detection and tier recommendation."""

from __future__ import annotations

import pytest

from core.system.hardware_profile import AITier, HardwareProfile


class TestHardwareProfileTierRecommendation:
    """Test the recommended_tier property with various hardware profiles."""

    def _profile(self, ram: float = 16, vram: float = 0, ollama: bool = True) -> HardwareProfile:
        return HardwareProfile(
            total_ram_gb=ram,
            gpu_name="Test GPU" if vram > 0 else "None",
            gpu_vram_gb=vram,
            cpu_name="Test CPU",
            cpu_cores=4,
            os_name="Test OS",
            ollama_available=ollama,
        )

    def test_full_llm_high_end(self):
        profile = self._profile(ram=32, vram=10)
        assert profile.recommended_tier == AITier.FULL_LLM

    def test_lite_llm_mid_gpu(self):
        profile = self._profile(ram=16, vram=6)
        assert profile.recommended_tier == AITier.LITE_LLM

    def test_lite_llm_cpu_only_enough_ram(self):
        profile = self._profile(ram=32, vram=0)
        assert profile.recommended_tier == AITier.LITE_LLM

    def test_enhanced_deterministic_low_ram(self):
        profile = self._profile(ram=8, vram=0)
        assert profile.recommended_tier == AITier.ENHANCED_DETERMINISTIC

    def test_basic_deterministic_minimal(self):
        profile = self._profile(ram=4, vram=0)
        assert profile.recommended_tier == AITier.BASIC_DETERMINISTIC

    def test_no_ollama_forces_deterministic(self):
        profile = self._profile(ram=32, vram=10, ollama=False)
        assert profile.recommended_tier == AITier.ENHANCED_DETERMINISTIC

    def test_no_ollama_low_ram(self):
        profile = self._profile(ram=4, vram=0, ollama=False)
        assert profile.recommended_tier == AITier.BASIC_DETERMINISTIC


class TestHardwareProfileSerialization:
    """Test to_dict output."""

    def test_to_dict(self):
        profile = HardwareProfile(
            total_ram_gb=16.0,
            gpu_name="RTX 3060",
            gpu_vram_gb=12.0,
            cpu_name="i7-12700",
            cpu_cores=12,
            os_name="Windows 11",
            ollama_available=True,
        )
        d = profile.to_dict()
        assert d["total_ram_gb"] == 16.0
        assert d["gpu_name"] == "RTX 3060"
        assert d["recommended_tier"] == "full_llm"
