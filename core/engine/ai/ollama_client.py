"""Synchronous HTTP client for local Ollama API."""

from __future__ import annotations

from dataclasses import dataclass

import requests


@dataclass
class OllamaConfig:
    """Configuration for the Ollama HTTP client."""

    base_url: str = "http://localhost:11434"
    model: str = "phi3"
    temperature: float = 0.7
    max_tokens: int = 256
    timeout: int = 30


class OllamaClient:
    """Sync client for Ollama /api/generate endpoint.

    Uses requests.Session for connection pooling. No new deps required.
    """

    def __init__(self, config: OllamaConfig | None = None):
        self._config = config or OllamaConfig()
        self._session = requests.Session()

    def generate(self, prompt: str, system: str = "") -> str:
        """Send prompt to Ollama, return response text."""
        resp = self._session.post(
            f"{self._config.base_url}/api/generate",
            json={
                "model": self._config.model,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": {
                    "temperature": self._config.temperature,
                    "num_predict": self._config.max_tokens,
                },
            },
            timeout=self._config.timeout,
        )
        resp.raise_for_status()
        return resp.json()["response"]

    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            resp = self._session.get(
                f"{self._config.base_url}/api/tags", timeout=5
            )
            return resp.status_code == 200
        except requests.ConnectionError:
            return False

    def close(self) -> None:
        """Close the session."""
        self._session.close()
