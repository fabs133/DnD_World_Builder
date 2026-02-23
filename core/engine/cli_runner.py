"""Entry point for running a game from the command line.

Usage:
    python -m core.engine.cli_runner [--seed SEED] [--model MODEL] [--no-ai] [--no-llm] [--max-rounds N]
"""

from __future__ import annotations

import argparse
import sys

from core.engine.scenarios.demo_encounter import build_demo_encounter
from core.engine.cli_adapter import CLIAdapter
from core.engine.ai.ollama_client import OllamaClient, OllamaConfig
from core.engine.ai.heuristic_adapter import HeuristicAIAdapter
from core.engine.game_state import GameState
from core.engine.action_executor import ActionResult


def _on_round_start(state: GameState) -> None:
    print(f"\n{'#'*50}")
    print(f"  ROUND {state.round_number}")
    print(f"{'#'*50}")


def _on_action_result(result: ActionResult) -> None:
    if result.action is None:
        return
    for line in result.execution_log:
        print(f"  >> {line}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DnD World Builder - Headless Combat Runner"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--model", default="phi3", help="Ollama model name")
    parser.add_argument("--max-rounds", type=int, default=20, help="Maximum rounds")
    parser.add_argument(
        "--no-ai", action="store_true",
        help="All entities use CLI input (no Ollama)",
    )
    parser.add_argument(
        "--no-llm", action="store_true",
        help="Use deterministic heuristic AI instead of Ollama",
    )
    args = parser.parse_args()

    print("DnD World Builder - Headless Combat Demo")
    print(f"Seed: {args.seed}, Model: {args.model}, Max rounds: {args.max_rounds}")
    print()

    config = OllamaConfig(model=args.model)
    use_heuristic = args.no_llm

    if not args.no_ai and not use_heuristic:
        client = OllamaClient(config)
        if not client.is_available():
            print("WARNING: Ollama is not running at", config.base_url)
            print("Switching to deterministic heuristic AI.")
            print()
            use_heuristic = True

    session = build_demo_encounter(
        seed=args.seed,
        max_rounds=args.max_rounds,
        ollama_config=config,
        use_heuristic=use_heuristic,
    )

    if args.no_ai:
        entities_by_name = {e.name: e for e in session._gm.game_entities}
        cli = CLIAdapter(entities_by_name=entities_by_name)
        for name in session._adapters:
            session._adapters[name] = cli

    session.on_round_start = _on_round_start
    session.on_action_result = _on_action_result
    session.setup()

    print("\nInitiative order:", ", ".join(session._initiative.get_order()))
    print()

    result = session.run()

    print(f"\n{'='*50}")
    print(f"  COMBAT COMPLETE")
    print(f"{'='*50}")
    print(f"  Rounds: {result.rounds_played}")
    print(f"  Winner: {result.winner or 'Draw'}")
    print(f"  Reason: {result.termination_reason}")
    print(f"  Actions taken: {len(result.action_history)}")


if __name__ == "__main__":
    main()
