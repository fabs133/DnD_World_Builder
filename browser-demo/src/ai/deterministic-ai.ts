/**
 * Deterministic rule-based AI driven by alignment tactical weights.
 *
 * Ported from: core/engine/ai/heuristic_adapter.py (HeuristicAIAdapter)
 *
 * Decision pipeline (evaluated top-to-bottom):
 *   1. Flee    — if hp_ratio < weights.fleeThreshold, move away from enemies
 *   2. Attack  — if an enemy is adjacent (Chebyshev <= 1), attack weakest
 *   3. Advance — move toward nearest enemy
 *   4. End turn
 */

import type { Entity, GameState, Action } from '../core/types';
import { getWeightsForAlignment } from '../core/alignment';
import {
  chebyshev,
  distance,
  getAdjacentTiles,
  isTileOccupied,
  isTileBlocking,
} from '../core/combat';
import { VOICE_LINES } from './voice-lines';

export class DeterministicAI {
  private rng: () => number;

  constructor(seed?: number) {
    this.rng = seed !== undefined ? this.createSeededRng(seed) : Math.random;
  }

  chooseAction(entity: Entity, state: GameState): Action {
    const weights = getWeightsForAlignment(entity.alignment);
    const hpRatio = entity.hp / entity.maxHp;

    const enemies = this.getEnemies(entity, state);
    const adjacent = enemies.filter(
      (e) => chebyshev(entity.position, e.position) <= 1,
    );

    // 1. Flee
    if (hpRatio < weights.fleeThreshold && enemies.length > 0) {
      const fleePos = this.positionAwayFrom(entity, enemies, state);
      if (fleePos) {
        return { type: 'flee', actor: entity.id, position: fleePos };
      }
    }

    // 2. Attack adjacent enemy (pick weakest)
    if (adjacent.length > 0) {
      const target = adjacent.reduce((a, b) => (a.hp < b.hp ? a : b));
      return { type: 'attack', actor: entity.id, target: target.id };
    }

    // 3. Advance toward nearest enemy
    if (enemies.length > 0) {
      const advancePos = this.positionToward(entity, enemies, state);
      if (advancePos) {
        return { type: 'move', actor: entity.id, position: advancePos };
      }
    }

    // 4. Fallback
    return { type: 'end_turn', actor: entity.id };
  }

  getVoiceLine(entity: Entity): string | undefined {
    if (this.rng() > 0.3) return undefined;
    const lines = VOICE_LINES[entity.alignment] || [];
    if (lines.length === 0) return undefined;
    return lines[Math.floor(this.rng() * lines.length)];
  }

  // -------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------

  private getEnemies(entity: Entity, state: GameState): Entity[] {
    const result: Entity[] = [];
    for (const [, e] of state.entities) {
      if (e.id === entity.id || e.hp <= 0) continue;
      if (e.type !== entity.type) result.push(e);
    }
    return result;
  }

  private positionToward(
    entity: Entity,
    enemies: Entity[],
    state: GameState,
  ): [number, number] | null {
    const nearest = enemies.reduce((a, b) =>
      distance(entity.position, a.position) <=
      distance(entity.position, b.position)
        ? a
        : b,
    );
    const tiles = getAdjacentTiles(entity.position, state.mapSize);
    const valid = tiles.filter(
      (t) => !isTileOccupied(t, state) && !isTileBlocking(t, state),
    );
    if (valid.length === 0) return null;
    return valid.reduce((best, t) =>
      distance(t, nearest.position) < distance(best, nearest.position)
        ? t
        : best,
    );
  }

  private positionAwayFrom(
    entity: Entity,
    enemies: Entity[],
    state: GameState,
  ): [number, number] | null {
    const tiles = getAdjacentTiles(entity.position, state.mapSize);
    const valid = tiles.filter(
      (t) => !isTileOccupied(t, state) && !isTileBlocking(t, state),
    );
    if (valid.length === 0) return null;

    // Maximize minimum distance to any enemy
    return valid.reduce((best, t) => {
      const tMin = Math.min(...enemies.map((e) => distance(t, e.position)));
      const bMin = Math.min(...enemies.map((e) => distance(best, e.position)));
      return tMin > bMin ? t : best;
    });
  }

  private createSeededRng(seed: number): () => number {
    let s = seed;
    return () => {
      s = (s * 1103515245 + 12345) & 0x7fffffff;
      return s / 0x7fffffff;
    };
  }
}
