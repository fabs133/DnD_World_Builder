"""CLI demo runner: Goblin Ambush scenario with alignment-driven AI.

Usage:
    python scripts/run_demo.py                          # MockAI (instant, deterministic)
    python scripts/run_demo.py --mode ollama            # LLM-backed AI
    python scripts/run_demo.py --seed 123 --max-rounds 30
    python scripts/run_demo.py --scenario path/to/custom.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.engine.scenarios.scenario_loader import ScenarioLoader  # noqa: E402
from core.engine.game_state import GameState  # noqa: E402
from core.engine.action_executor import ActionResult  # noqa: E402
from core.engine.ai.ollama_client import OllamaClient, OllamaConfig  # noqa: E402

DEFAULT_SCENARIO = PROJECT_ROOT / "scenarios" / "goblin_ambush.yaml"

# Entity type icons
_PLAYER_TYPES = {"player", "ally", "companion"}


def _hp_bar(hp: int, max_hp: int, width: int = 20) -> str:
    """Render an ASCII HP bar like [########------]."""
    if max_hp <= 0:
        return "-" * width
    filled = int(hp / max_hp * width)
    return "#" * filled + "-" * (width - filled)


def _format_entity_table(state: GameState) -> str:
    """Format all entity HP/status for display."""
    lines = []
    for e in sorted(state.entities, key=lambda x: x.entity_type):
        icon = "[HERO]" if e.entity_type.lower() in _PLAYER_TYPES else "[FOE] "
        bar = _hp_bar(e.hp, e.max_hp)
        status = "DEAD" if not e.is_alive else f"{e.hp}/{e.max_hp}"
        lines.append(f"  {icon} {e.name:15s} [{bar}] {status}")
    return "\n".join(lines)


def _on_round_start(state: GameState) -> None:
    print(f"\n{'=' * 60}")
    print(f"  ROUND {state.round_number}")
    print(f"{'=' * 60}")
    print(_format_entity_table(state))
    print()


def _on_turn_start(state: GameState, entity_name: str) -> None:
    entity = None
    for e in state.entities:
        if e.name == entity_name:
            entity = e
            break
    if entity and entity.is_alive:
        print(f"  --- {entity_name}'s Turn (HP: {entity.hp}/{entity.max_hp}) ---")


def _on_action_result(result: ActionResult) -> None:
    if result.action is None:
        return
    for line in result.execution_log:
        print(f"    >> {line}")


def main() -> None:
    parser = argparse.ArgumentParser(description="D&D World Builder - Demo Runner")
    parser.add_argument(
        "--scenario",
        type=str,
        default=str(DEFAULT_SCENARIO),
        help="Path to scenario YAML file",
    )
    parser.add_argument(
        "--mode",
        choices=["mock", "ollama"],
        default="mock",
        help="AI mode: mock (instant, deterministic) or ollama (LLM-backed)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--max-rounds", type=int, default=None, help="Max combat rounds")
    parser.add_argument("--model", default="phi3", help="Ollama model name")
    args = parser.parse_args()

    # Load scenario
    loader = ScenarioLoader(args.scenario)

    print(f"\n{'#' * 60}")
    print(f"  D&D World Builder - {loader.name}")
    print(f"  {loader.description}")
    print(f"{'#' * 60}")
    print(f"  Mode: {args.mode.upper()}, Seed: {args.seed}")

    # Check Ollama availability
    ollama_cfg = None
    if args.mode == "ollama":
        ollama_cfg = OllamaConfig(model=args.model)
        client = OllamaClient(ollama_cfg)
        if not client.is_available():
            print(f"\n  WARNING: Ollama not available at {ollama_cfg.base_url}")
            print("  Falling back to MockAI mode.\n")
            args.mode = "mock"
            ollama_cfg = None
        else:
            print(f"  Ollama model: {args.model}")

    # Build and run session
    session = loader.build_session(
        mode=args.mode,
        seed=args.seed,
        max_rounds=args.max_rounds,
        ollama_config=ollama_cfg,
        on_round_start=_on_round_start,
        on_turn_start=_on_turn_start,
        on_action_result=_on_action_result,
    )

    session.setup()

    # Print initiative order
    init_order = session._initiative.get_order()
    print(f"\n  Initiative Order: {', '.join(init_order)}")

    result = session.run()

    # Final summary
    print(f"\n{'=' * 60}")
    print(f"  COMBAT COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Rounds played: {result.rounds_played}")
    print(f"  Winner: {result.winner or 'Draw'}")
    print(f"  Reason: {result.termination_reason}")
    print(f"  Total actions: {len(result.action_history)}")

    # Entity summary
    print(f"\n  --- Final Status ---")
    print(_format_entity_table(result.final_state))

    print(f"\n  Run behavioral tests for detailed alignment stats:")
    print(f"    pytest tests/behavioral/ -v")
    print()


if __name__ == "__main__":
    main()
