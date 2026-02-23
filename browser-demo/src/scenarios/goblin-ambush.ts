/**
 * "Ruined Temple Ambush" — the demo scenario.
 *
 * Ported from: scenarios/goblin_ambush.yaml
 */

import type { ScenarioDefinition } from '../core/types';

export const GOBLIN_AMBUSH: ScenarioDefinition = {
  name: 'Ruined Temple Ambush',
  description:
    'Two adventurers stumble into a goblin ambush in a crumbling dungeon temple. ' +
    'The goblins use the pillars for cover while the shaman directs from behind.',
  mapSize: [7, 7],
  maxRounds: 20,
  terrain: [
    // Rubble (difficult terrain, movement cost 2)
    { position: [2, 3], type: 'rubble', blocking: false, movementCost: 2 },
    { position: [3, 2], type: 'rubble', blocking: false, movementCost: 2 },
    { position: [4, 4], type: 'rubble', blocking: false, movementCost: 2 },
    // Pillars (blocking)
    { position: [1, 1], type: 'pillar', blocking: true, movementCost: 1 },
    { position: [5, 1], type: 'pillar', blocking: true, movementCost: 1 },
    { position: [1, 5], type: 'pillar', blocking: true, movementCost: 1 },
    { position: [5, 5], type: 'pillar', blocking: true, movementCost: 1 },
    // Trap
    { position: [3, 3], type: 'trap', blocking: false, movementCost: 1 },
  ],
  entities: [
    // Players
    {
      id: 'fighter',
      name: 'Fighter',
      type: 'player',
      hp: 28,
      maxHp: 28,
      ac: 16,
      dex: 12,
      speed: 30,
      position: [1, 6],
      alignment: 'lawful_good',
    },
    {
      id: 'wizard',
      name: 'Wizard',
      type: 'player',
      hp: 14,
      maxHp: 14,
      ac: 11,
      dex: 14,
      speed: 30,
      position: [2, 6],
      alignment: 'chaotic_good',
    },
    // Enemies
    {
      id: 'goblin_1',
      name: 'Goblin 1',
      type: 'enemy',
      hp: 7,
      maxHp: 7,
      ac: 13,
      dex: 14,
      speed: 30,
      position: [5, 1],
      alignment: 'neutral_evil',
    },
    {
      id: 'goblin_2',
      name: 'Goblin 2',
      type: 'enemy',
      hp: 7,
      maxHp: 7,
      ac: 13,
      dex: 14,
      speed: 30,
      position: [1, 2],
      alignment: 'neutral_evil',
    },
    {
      id: 'goblin_3',
      name: 'Goblin 3',
      type: 'enemy',
      hp: 7,
      maxHp: 7,
      ac: 13,
      dex: 14,
      speed: 30,
      position: [6, 3],
      alignment: 'neutral_evil',
    },
    {
      id: 'shaman',
      name: 'Shaman',
      type: 'enemy',
      hp: 12,
      maxHp: 12,
      ac: 14,
      dex: 12,
      speed: 30,
      position: [3, 0],
      alignment: 'lawful_evil',
    },
  ],
};
