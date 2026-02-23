"""CLI InputAdapter for interactive terminal play."""

from __future__ import annotations

from core.engine.input_adapter import InputAdapter
from core.engine.game_state import GameState, EntitySnapshot
from core.engine.actions.attack_action import AttackAction
from core.engine.actions.move_action import MoveAction
from core.engine.actions.end_turn_action import EndTurnAction
from models.flow.action.action import Action

import random


class CLIAdapter(InputAdapter):
    """Interactive terminal input adapter.

    Displays game state and prompts for action selection.
    """

    def __init__(self, entities_by_name: dict | None = None, rng: random.Random | None = None):
        self._entities = entities_by_name or {}
        self._rng = rng or random.Random()

    def choose_action(
        self,
        entity_name: str,
        game_state: GameState,
        available_actions: list[str],
    ) -> Action:
        self._display_state(game_state, entity_name)
        self._display_actions(available_actions)

        while True:
            choice = input(f"\n[{entity_name}] Choose action number: ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(available_actions):
                    action_type = available_actions[idx]
                    return self._build_action(action_type, entity_name, game_state)
            except (ValueError, IndexError):
                pass
            print(f"Invalid choice. Enter 1-{len(available_actions)}.")

    def choose_target(
        self,
        entity_name: str,
        game_state: GameState,
        valid_targets: list[str],
    ) -> str:
        print("\nChoose target:")
        for i, t in enumerate(valid_targets, 1):
            entity = game_state.get_entity(t)
            hp_info = f" (HP: {entity.hp}/{entity.max_hp})" if entity else ""
            print(f"  {i}. {t}{hp_info}")

        while True:
            choice = input("Target number: ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(valid_targets):
                    return valid_targets[idx]
            except (ValueError, IndexError):
                pass
            print(f"Invalid. Enter 1-{len(valid_targets)}.")

    def choose_movement(
        self,
        entity_name: str,
        game_state: GameState,
        valid_positions: list[tuple[int, int]],
    ) -> tuple[int, int]:
        print("\nEnter target position (x,y):")
        while True:
            choice = input("Position: ").strip()
            try:
                parts = choice.split(",")
                pos = (int(parts[0].strip()), int(parts[1].strip()))
                if pos in valid_positions or not valid_positions:
                    return pos
                print(f"Invalid position. Valid: {valid_positions[:10]}...")
            except (ValueError, IndexError):
                print("Enter as: x,y (e.g., 3,4)")

    def _display_state(self, state: GameState, perspective: str) -> None:
        me = state.get_entity(perspective)
        if me is None:
            return

        print(f"\n{'='*50}")
        print(f"  Round {state.round_number} - {me.name}'s Turn")
        print(f"{'='*50}")
        print(f"  HP: {me.hp}/{me.max_hp}  AC: {me.armor_class}  Pos: {me.position}")

        enemies = state.get_enemies_of(perspective)
        if enemies:
            print(f"\n  Enemies:")
            for e in enemies:
                dist = abs(e.position[0] - me.position[0]) + abs(e.position[1] - me.position[1])
                print(f"    {e.name}: HP {e.hp}/{e.max_hp}, AC {e.armor_class}, dist {dist}")

        allies = state.get_allies_of(perspective)
        if allies:
            print(f"\n  Allies:")
            for a in allies:
                print(f"    {a.name}: HP {a.hp}/{a.max_hp}")

    def _display_actions(self, actions: list[str]) -> None:
        print(f"\n  Actions:")
        for i, a in enumerate(actions, 1):
            print(f"    {i}. {a}")

    def _build_action(self, action_type: str, entity_name: str, state: GameState) -> Action:
        actor = self._entities.get(entity_name)
        if actor is None:
            class _Stub:
                name = entity_name
            actor = _Stub()

        if action_type == "ATTACK":
            enemies = state.get_enemies_of(entity_name)
            targets = [e.name for e in enemies if e.is_alive]
            if targets:
                target_name = self.choose_target(entity_name, state, targets)
                target = self._entities.get(target_name, None)
                if target:
                    return AttackAction(actor, target, rng=self._rng)
            return EndTurnAction(actor)

        if action_type == "MOVE":
            pos = self.choose_movement(entity_name, state, [])
            return MoveAction(actor, target_position=pos)

        return EndTurnAction(actor)
