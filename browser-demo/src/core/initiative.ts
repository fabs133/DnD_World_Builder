/**
 * D&D 5e initiative tracker with deterministic tiebreaking.
 *
 * Ported from: core/engine/initiative.py
 */

import type { Entity } from './types';

interface InitiativeEntry {
  entityId: string;
  roll: number;
  dexModifier: number;
  tiebreaker: number;
}

/**
 * Roll initiative for all entities and return their IDs in turn order.
 *
 * Sorting: primary by roll desc, secondary by dex modifier desc,
 * tertiary by random tiebreaker desc — matches the Python implementation.
 */
export function rollInitiative(
  entities: Entity[],
  rng: () => number,
): string[] {
  const entries: InitiativeEntry[] = entities.map((e) => {
    const dexMod = Math.floor((e.dex - 10) / 2);
    const roll = Math.floor(rng() * 20) + 1 + dexMod;
    const tiebreaker = Math.floor(rng() * 1000) + 1;
    return {
      entityId: e.id,
      roll,
      dexModifier: dexMod,
      tiebreaker,
    };
  });

  entries.sort((a, b) => {
    if (b.roll !== a.roll) return b.roll - a.roll;
    if (b.dexModifier !== a.dexModifier) return b.dexModifier - a.dexModifier;
    return b.tiebreaker - a.tiebreaker;
  });

  return entries.map((e) => e.entityId);
}
