/**
 * D&D 5e combat mechanics — attack rolls, damage, and movement.
 *
 * Ported from: core/engine/actions/attack_action.py,
 *              core/engine/actions/move_action.py
 */

import type { Entity, GameState, LogEntry } from './types';

/**
 * Roll dice using a dice expression like "1d6", "2d8+3".
 */
export function rollDice(expr: string, rng: () => number): number {
  const match = expr.replace(/\s/g, '').match(/^(\d*)d(\d+)([+-]?\d*)$/);
  if (!match) return 0;
  const numDice = match[1] ? parseInt(match[1]) : 1;
  const sides = parseInt(match[2]);
  const modifier = match[3] ? parseInt(match[3]) : 0;
  let total = modifier;
  for (let i = 0; i < numDice; i++) {
    total += Math.floor(rng() * sides) + 1;
  }
  return total;
}

/**
 * Resolve a melee/ranged attack against a target.
 * Returns a log entry describing the result and mutates entity HP.
 */
export function resolveAttack(
  attacker: Entity,
  target: Entity,
  state: GameState,
  rng: () => number,
): LogEntry {
  const attackRoll = Math.floor(rng() * 20) + 1;
  const hit = attackRoll >= target.ac;

  if (hit) {
    const damage = rollDice('1d6', rng);
    const oldHp = target.hp;
    target.hp = Math.max(0, target.hp - damage);

    // Check if combat is over
    checkCombatEnd(state);

    return {
      round: state.round,
      actor: attacker.name,
      action: 'attack',
      target: target.name,
      result: `rolls ${attackRoll} vs AC ${target.ac} — hits for ${damage} damage (${oldHp} -> ${target.hp} HP)`,
    };
  }

  return {
    round: state.round,
    actor: attacker.name,
    action: 'attack',
    target: target.name,
    result: `rolls ${attackRoll} vs AC ${target.ac} — misses`,
  };
}

/**
 * Move an entity to a new position.
 */
export function resolveMove(
  entity: Entity,
  position: [number, number],
  state: GameState,
): LogEntry {
  const [oldX, oldY] = entity.position;
  entity.position = position;

  return {
    round: state.round,
    actor: entity.name,
    action: 'move',
    result: `moves from (${oldX},${oldY}) to (${position[0]},${position[1]})`,
  };
}

/**
 * Manhattan distance between two grid positions.
 */
export function distance(a: [number, number], b: [number, number]): number {
  return Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]);
}

/**
 * Chebyshev distance (8-directional adjacency check).
 */
export function chebyshev(a: [number, number], b: [number, number]): number {
  return Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
}

/**
 * Check if combat is over and update game phase accordingly.
 */
export function checkCombatEnd(state: GameState): void {
  let playersAlive = false;
  let enemiesAlive = false;

  for (const [, entity] of state.entities) {
    if (entity.hp <= 0) continue;
    if (entity.type === 'player') playersAlive = true;
    if (entity.type === 'enemy') enemiesAlive = true;
  }

  if (!playersAlive) state.phase = 'defeat';
  else if (!enemiesAlive) state.phase = 'victory';
}

/**
 * Get valid adjacent tiles (8-directional) within map bounds.
 */
export function getAdjacentTiles(
  pos: [number, number],
  mapSize: [number, number],
): [number, number][] {
  const [x, y] = pos;
  const candidates: [number, number][] = [
    [x - 1, y - 1], [x, y - 1], [x + 1, y - 1],
    [x - 1, y],                  [x + 1, y],
    [x - 1, y + 1], [x, y + 1], [x + 1, y + 1],
  ];
  return candidates.filter(
    ([cx, cy]) => cx >= 0 && cy >= 0 && cx < mapSize[0] && cy < mapSize[1],
  );
}

/**
 * Check if a tile is occupied by a living entity.
 */
export function isTileOccupied(
  pos: [number, number],
  state: GameState,
): boolean {
  for (const [, entity] of state.entities) {
    if (
      entity.hp > 0 &&
      entity.position[0] === pos[0] &&
      entity.position[1] === pos[1]
    ) {
      return true;
    }
  }
  return false;
}

/**
 * Check if a tile is blocking terrain.
 */
export function isTileBlocking(
  pos: [number, number],
  state: GameState,
): boolean {
  return state.terrain.some(
    (t) => t.blocking && t.position[0] === pos[0] && t.position[1] === pos[1],
  );
}
