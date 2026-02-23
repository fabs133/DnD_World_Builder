"""AI mode configuration based on hardware capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from core.system.hardware_profile import AITier, HardwareProfile, detect_hardware


class AIMode(Enum):
    """User-selectable AI mode."""

    AUTO = "auto"
    FULL_LLM = "full_llm"
    LITE_LLM = "lite_llm"
    DETERMINISTIC = "deterministic"
    OFF = "off"


@dataclass
class ModelConfig:
    """Configuration for a specific LLM model."""

    name: str
    max_tokens: int = 256
    temperature: float = 0.7
    context_window: int = 2048
    estimated_vram_gb: float = 4.0

    @classmethod
    def phi3_mini(cls) -> ModelConfig:
        return cls(name="phi3", max_tokens=256, estimated_vram_gb=2.5)

    @classmethod
    def mistral_7b(cls) -> ModelConfig:
        return cls(name="mistral:7b", max_tokens=512, estimated_vram_gb=5.0)

    @classmethod
    def gemma_2b(cls) -> ModelConfig:
        return cls(name="gemma:2b", max_tokens=256, estimated_vram_gb=1.5)

    @classmethod
    def tinyllama(cls) -> ModelConfig:
        return cls(name="tinyllama", max_tokens=128, estimated_vram_gb=1.0)


@dataclass
class AIConfig:
    """Complete AI configuration for a session."""

    mode: AIMode = AIMode.AUTO
    model: ModelConfig | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout: int = 30
    max_retries: int = 3
    hardware: HardwareProfile | None = None

    def resolve(self) -> AIConfig:
        """Resolve AUTO mode by detecting hardware and selecting a model.

        Returns a new AIConfig with concrete mode and model selections.
        Non-AUTO modes are returned unchanged.
        """
        if self.mode != AIMode.AUTO:
            return self

        hw = self.hardware or detect_hardware()
        tier = hw.recommended_tier

        if tier == AITier.FULL_LLM:
            model = ModelConfig.mistral_7b() if hw.gpu_vram_gb >= 6 else ModelConfig.phi3_mini()
            return AIConfig(
                mode=AIMode.FULL_LLM,
                model=model,
                ollama_base_url=self.ollama_base_url,
                ollama_timeout=self.ollama_timeout,
                max_retries=self.max_retries,
                hardware=hw,
            )

        if tier == AITier.LITE_LLM:
            model = ModelConfig.gemma_2b() if hw.gpu_vram_gb < 4 else ModelConfig.phi3_mini()
            return AIConfig(
                mode=AIMode.LITE_LLM,
                model=model,
                ollama_base_url=self.ollama_base_url,
                ollama_timeout=self.ollama_timeout,
                max_retries=self.max_retries,
                hardware=hw,
            )

        return AIConfig(
            mode=AIMode.DETERMINISTIC,
            hardware=hw,
            ollama_base_url=self.ollama_base_url,
            ollama_timeout=self.ollama_timeout,
            max_retries=self.max_retries,
        )

    @classmethod
    def host_delegated(cls) -> AIConfig:
        """Config for multiplayer guest delegating AI to host."""
        return cls(mode=AIMode.OFF)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "mode": self.mode.value,
            "ollama_base_url": self.ollama_base_url,
            "ollama_timeout": self.ollama_timeout,
            "max_retries": self.max_retries,
        }
        if self.model:
            result["model"] = {
                "name": self.model.name,
                "max_tokens": self.model.max_tokens,
                "temperature": self.model.temperature,
                "estimated_vram_gb": self.model.estimated_vram_gb,
            }
        if self.hardware:
            result["hardware"] = self.hardware.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AIConfig:
        mode = AIMode(data.get("mode", "auto"))
        model = None
        if "model" in data:
            m = data["model"]
            model = ModelConfig(
                name=m["name"],
                max_tokens=m.get("max_tokens", 256),
                temperature=m.get("temperature", 0.7),
                estimated_vram_gb=m.get("estimated_vram_gb", 4.0),
            )
        return cls(
            mode=mode,
            model=model,
            ollama_base_url=data.get("ollama_base_url", "http://localhost:11434"),
            ollama_timeout=data.get("ollama_timeout", 30),
            max_retries=data.get("max_retries", 3),
        )
