/**
 * Game session orchestrator — manages rounds, turns, and state.
 *
 * Ported from: core/engine/game_session.py (GameSession)
 */

import type {
  Entity,
  GameState,
  Action,
  LogEntry,
  ScenarioDefinition,
} from './types';
import { rollInitiative } from './initiative';
import { resolveAttack, resolveMove, checkCombatEnd } from './combat';

export class GameSession {
  state: GameState;
  private rng: () => number;
  private maxRounds: number;

  constructor(scenario: ScenarioDefinition, seed?: number) {
    this.rng = seed !== undefined ? this.createSeededRng(seed) : Math.random;
    this.maxRounds = scenario.maxRounds;

    // Deep-clone entities so the original scenario is not mutated
    const entities = new Map<string, Entity>();
    for (const def of scenario.entities) {
      entities.set(def.id, { ...def });
    }

    // Roll initiative
    const entityList = Array.from(entities.values());
    const turnOrder = rollInitiative(entityList, this.rng);

    this.state = {
      entities,
      terrain: [...scenario.terrain],
      turnOrder,
      currentTurnIndex: 0,
      round: 1,
      log: [],
      phase: 'combat',
      mapSize: scenario.mapSize,
    };
  }

  /** The entity whose turn it currently is. */
  getCurrentEntity(): Entity | undefined {
    const id = this.state.turnOrder[this.state.currentTurnIndex];
    return id ? this.state.entities.get(id) : undefined;
  }

  /** True if the current turn belongs to a player-controlled entity. */
  isPlayerTurn(): boolean {
    const entity = this.getCurrentEntity();
    return entity?.type === 'player' && entity.hp > 0;
  }

  /** Execute a player or AI action and add the result to the log. */
  executeAction(action: Action, voiceLine?: string): LogEntry | null {
    if (this.state.phase !== 'combat') return null;

    const actor = this.state.entities.get(action.actor);
    if (!actor || actor.hp <= 0) return null;

    let logEntry: LogEntry;

    switch (action.type) {
      case 'attack': {
        if (!action.target) return null;
        const target = this.state.entities.get(action.target);
        if (!target || target.hp <= 0) return null;
        logEntry = resolveAttack(actor, target, this.state, this.rng);
        break;
      }
      case 'move':
      case 'flee': {
        if (!action.position) return null;
        logEntry = resolveMove(actor, action.position, this.state);
        if (action.type === 'flee') {
          logEntry.action = 'flee';
          logEntry.result = `flees to (${action.position[0]},${action.position[1]})`;
        }
        break;
      }
      case 'defend': {
        logEntry = {
          round: this.state.round,
          actor: actor.name,
          action: 'defend',
          result: 'takes a defensive stance',
        };
        break;
      }
      case 'end_turn':
      default: {
        logEntry = {
          round: this.state.round,
          actor: actor.name,
          action: 'end_turn',
          result: 'ends their turn',
        };
        break;
      }
    }

    if (voiceLine) {
      logEntry.voiceLine = voiceLine;
    }

    this.state.log.push(logEntry);
    this.advanceTurn();
    return logEntry;
  }

  /** Advance to the next living entity's turn. */
  private advanceTurn(): void {
    if (this.state.phase !== 'combat') return;

    // Check for combat end after action
    checkCombatEnd(this.state);
    if (this.state.phase !== 'combat') return;

    // Skip dead entities
    let attempts = 0;
    const maxAttempts = this.state.turnOrder.length + 1;

    do {
      this.state.currentTurnIndex++;
      if (this.state.currentTurnIndex >= this.state.turnOrder.length) {
        this.state.currentTurnIndex = 0;
        this.state.round++;

        if (this.state.round > this.maxRounds) {
          this.state.phase = 'defeat';
          return;
        }
      }
      attempts++;
    } while (
      attempts < maxAttempts &&
      this.isCurrentEntityDead()
    );
  }

  private isCurrentEntityDead(): boolean {
    const entity = this.getCurrentEntity();
    return entity !== undefined && entity.hp <= 0;
  }

  private createSeededRng(seed: number): () => number {
    let s = seed;
    return () => {
      s = (s * 1103515245 + 12345) & 0x7fffffff;
      return s / 0x7fffffff;
    };
  }
}
