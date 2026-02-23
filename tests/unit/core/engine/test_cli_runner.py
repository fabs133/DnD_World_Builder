"""Tests for cli_runner.main() entry point."""

import pytest
from unittest.mock import patch, MagicMock

from core.engine.cli_runner import main, _on_round_start, _on_action_result
from core.engine.game_state import GameState, EntitySnapshot
from core.engine.action_executor import ActionResult
from core.engine.actions.end_turn_action import EndTurnAction


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_state():
    fighter = EntitySnapshot(
        name="Fighter", entity_type="player", hp=20, max_hp=20,
        armor_class=16, position=(0, 0), conditions=(), stats={},
        speed=30, faction="player", is_alive=True,
    )
    return GameState(
        round_number=1, current_entity_name="Fighter",
        entities=(fighter,), initiative_order=("Fighter",),
        world_width=5, world_height=5, tile_type="square",
    )


def _mock_session():
    session = MagicMock()
    session._gm.game_entities = []
    session._adapters = {}
    session._initiative.get_order.return_value = ["Fighter", "Goblin"]
    result = MagicMock()
    result.rounds_played = 3
    result.winner = "player"
    result.termination_reason = "player_victory"
    result.action_history = [MagicMock()]
    session.run.return_value = result
    return session


# ── Tests: callbacks ─────────────────────────────────────────────────────


class TestCallbacks:

    def test_on_round_start_prints_header(self, capsys):
        state = _make_state()
        _on_round_start(state)
        captured = capsys.readouterr()
        assert "ROUND 1" in captured.out

    def test_on_action_result_prints_log(self, capsys):
        class _Stub:
            name = "test"
        result = ActionResult(
            success=True,
            action=EndTurnAction(_Stub()),
            execution_log=["Fighter ended their turn"],
        )
        _on_action_result(result)
        captured = capsys.readouterr()
        assert "Fighter ended their turn" in captured.out

    def test_on_action_result_no_action(self, capsys):
        result = ActionResult(success=True, action=None)
        _on_action_result(result)
        captured = capsys.readouterr()
        assert captured.out == ""


# ── Tests: main() with --no-llm ──────────────────────────────────────────


class TestMainNoLLM:

    @patch("core.engine.cli_runner.build_demo_encounter")
    @patch("sys.argv", ["cli_runner", "--no-llm", "--seed", "42", "--max-rounds", "3"])
    def test_no_llm_flag_uses_heuristic(self, mock_build, capsys):
        """--no-llm flag passes use_heuristic=True to build_demo_encounter."""
        mock_build.return_value = _mock_session()

        main()

        mock_build.assert_called_once()
        _, kwargs = mock_build.call_args
        assert kwargs["use_heuristic"] is True
        assert kwargs["seed"] == 42
        assert kwargs["max_rounds"] == 3

    @patch("core.engine.cli_runner.build_demo_encounter")
    @patch("sys.argv", ["cli_runner", "--no-llm"])
    def test_no_llm_prints_completion(self, mock_build, capsys):
        """--no-llm runs the session and prints completion."""
        mock_build.return_value = _mock_session()

        main()

        captured = capsys.readouterr()
        assert "COMBAT COMPLETE" in captured.out
        assert "player" in captured.out


# ── Tests: main() with --no-ai ──────────────────────────────────────────


class TestMainNoAI:

    @patch("core.engine.cli_runner.build_demo_encounter")
    @patch("sys.argv", ["cli_runner", "--no-ai"])
    def test_no_ai_replaces_adapters_with_cli(self, mock_build, capsys):
        """--no-ai replaces all adapters with CLIAdapter instances."""
        session = _mock_session()
        session._adapters = {"Fighter": MagicMock(), "Goblin": MagicMock()}

        class FakeEntity:
            def __init__(self, name):
                self.name = name
        session._gm.game_entities = [FakeEntity("Fighter"), FakeEntity("Goblin")]
        mock_build.return_value = session

        main()

        # All adapters should have been replaced
        from core.engine.cli_adapter import CLIAdapter
        for name, adapter in session._adapters.items():
            assert isinstance(adapter, CLIAdapter)


# ── Tests: main() Ollama unavailable fallback ────────────────────────────


class TestMainOllamaFallback:

    @patch("core.engine.cli_runner.OllamaClient")
    @patch("core.engine.cli_runner.build_demo_encounter")
    @patch("sys.argv", ["cli_runner"])
    def test_ollama_unavailable_switches_to_heuristic(self, mock_build, mock_client_cls, capsys):
        """When Ollama isn't running, main() falls back to heuristic."""
        mock_client = MagicMock()
        mock_client.is_available.return_value = False
        mock_client_cls.return_value = mock_client
        mock_build.return_value = _mock_session()

        main()

        _, kwargs = mock_build.call_args
        assert kwargs["use_heuristic"] is True

        captured = capsys.readouterr()
        assert "heuristic" in captured.out.lower() or "WARNING" in captured.out

    @patch("core.engine.cli_runner.OllamaClient")
    @patch("core.engine.cli_runner.build_demo_encounter")
    @patch("sys.argv", ["cli_runner"])
    def test_ollama_available_uses_llm(self, mock_build, mock_client_cls, capsys):
        """When Ollama is running, main() uses LLM (use_heuristic=False)."""
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client_cls.return_value = mock_client
        mock_build.return_value = _mock_session()

        main()

        _, kwargs = mock_build.call_args
        assert kwargs["use_heuristic"] is False


# ── Tests: argument parsing ──────────────────────────────────────────────


class TestArgParsing:

    @patch("core.engine.cli_runner.build_demo_encounter")
    @patch("sys.argv", ["cli_runner", "--seed", "99", "--model", "llama3", "--max-rounds", "10"])
    def test_custom_args_passed_through(self, mock_build, capsys):
        """Custom CLI args are forwarded to build_demo_encounter."""
        mock_build.return_value = _mock_session()

        main()

        _, kwargs = mock_build.call_args
        assert kwargs["seed"] == 99
        assert kwargs["max_rounds"] == 10

        captured = capsys.readouterr()
        assert "Seed: 99" in captured.out
        assert "llama3" in captured.out
