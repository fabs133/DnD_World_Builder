"""Tests for the Ollama HTTP client."""

import pytest
from unittest.mock import MagicMock, patch
from core.engine.ai.ollama_client import OllamaClient, OllamaConfig


class TestOllamaClient:
    def test_generate_success(self):
        client = OllamaClient(OllamaConfig(base_url="http://fake:11434"))
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "ACTION: ATTACK TARGET: Goblin"}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "post", return_value=mock_resp) as mock_post:
            result = client.generate("test prompt", system="system")

        assert result == "ACTION: ATTACK TARGET: Goblin"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "test prompt" in str(call_kwargs)

    def test_generate_sends_correct_payload(self):
        config = OllamaConfig(model="mistral", temperature=0.5, max_tokens=128)
        client = OllamaClient(config)
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "test"}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "post", return_value=mock_resp) as mock_post:
            client.generate("prompt", system="sys")

        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "mistral"
        assert payload["stream"] is False
        assert payload["options"]["temperature"] == 0.5
        assert payload["options"]["num_predict"] == 128

    def test_is_available_true(self):
        client = OllamaClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch.object(client._session, "get", return_value=mock_resp):
            assert client.is_available() is True

    def test_is_available_false_on_connection_error(self):
        import requests
        client = OllamaClient()

        with patch.object(client._session, "get", side_effect=requests.ConnectionError):
            assert client.is_available() is False

    def test_generate_raises_on_http_error(self):
        import requests
        client = OllamaClient()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("500")

        with patch.object(client._session, "post", return_value=mock_resp):
            with pytest.raises(requests.HTTPError):
                client.generate("prompt")

    def test_default_config(self):
        config = OllamaConfig()
        assert config.base_url == "http://localhost:11434"
        assert config.model == "phi3"
        assert config.temperature == 0.7
