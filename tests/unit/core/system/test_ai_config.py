"""Tests for AI configuration and mode resolution."""

from __future__ import annotations

import pytest

from core.system.ai_config import AIConfig, AIMode, ModelConfig
from core.system.hardware_profile import AITier, HardwareProfile


def _hw(ram: float = 16, vram: float = 0, ollama: bool = True) -> HardwareProfile:
    return HardwareProfile(
        total_ram_gb=ram,
        gpu_name="Test GPU" if vram > 0 else "None",
        gpu_vram_gb=vram,
        cpu_name="Test CPU",
        cpu_cores=4,
        os_name="Test OS",
        ollama_available=ollama,
    )


class TestAIConfigResolve:
    """Test AUTO mode resolution based on hardware."""

    def test_full_llm_with_high_vram(self):
        config = AIConfig(mode=AIMode.AUTO, hardware=_hw(ram=32, vram=8))
        resolved = config.resolve()
        assert resolved.mode == AIMode.FULL_LLM
        assert resolved.model is not None
        assert resolved.model.name == "mistral:7b"

    def test_lite_llm_selects_phi3_for_mid_vram(self):
        config = AIConfig(mode=AIMode.AUTO, hardware=_hw(ram=32, vram=5))
        resolved = config.resolve()
        assert resolved.mode == AIMode.LITE_LLM
        assert resolved.model.name == "phi3"

    def test_lite_llm_with_mid_hardware(self):
        config = AIConfig(mode=AIMode.AUTO, hardware=_hw(ram=16, vram=4))
        resolved = config.resolve()
        assert resolved.mode == AIMode.LITE_LLM

    def test_deterministic_without_ollama(self):
        config = AIConfig(mode=AIMode.AUTO, hardware=_hw(ram=32, vram=10, ollama=False))
        resolved = config.resolve()
        assert resolved.mode == AIMode.DETERMINISTIC

    def test_non_auto_passes_through(self):
        config = AIConfig(mode=AIMode.FULL_LLM)
        resolved = config.resolve()
        assert resolved is config  # same object

    def test_host_delegated(self):
        config = AIConfig.host_delegated()
        assert config.mode == AIMode.OFF


class TestModelConfigPresets:
    """Test model configuration presets."""

    def test_phi3_mini(self):
        m = ModelConfig.phi3_mini()
        assert m.name == "phi3"
        assert m.estimated_vram_gb == 2.5

    def test_mistral_7b(self):
        m = ModelConfig.mistral_7b()
        assert m.name == "mistral:7b"
        assert m.estimated_vram_gb == 5.0

    def test_gemma_2b(self):
        m = ModelConfig.gemma_2b()
        assert m.name == "gemma:2b"

    def test_tinyllama(self):
        m = ModelConfig.tinyllama()
        assert m.name == "tinyllama"


class TestAIConfigSerialization:
    """Test to_dict / from_dict roundtrip."""

    def test_roundtrip(self):
        original = AIConfig(
            mode=AIMode.FULL_LLM,
            model=ModelConfig.mistral_7b(),
            ollama_base_url="http://localhost:11434",
            max_retries=5,
        )
        data = original.to_dict()
        restored = AIConfig.from_dict(data)
        assert restored.mode == original.mode
        assert restored.model.name == original.model.name
        assert restored.max_retries == original.max_retries

    def test_from_dict_minimal(self):
        config = AIConfig.from_dict({"mode": "deterministic"})
        assert config.mode == AIMode.DETERMINISTIC
        assert config.model is None
