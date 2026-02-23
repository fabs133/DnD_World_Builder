/**
 * Core game types for D&D World Builder browser demo.
 *
 * Ported from: models/ai/alignment.py, models/ai/tactical_weights.py,
 *              models/entities/game_entity.py, core/engine/game_state.py
 */

export type Alignment =
  | 'lawful_good' | 'neutral_good' | 'chaotic_good'
  | 'lawful_neutral' | 'true_neutral' | 'chaotic_neutral'
  | 'lawful_evil' | 'neutral_evil' | 'chaotic_evil';

export interface TacticalWeights {
  coordination: number;
  predictability: number;
  allyProtection: number;
  mercy: number;
  selfSacrifice: number;
  targetPriority: number;
  honor: number;
  aggression: number;
  fleeThreshold: number;
}

export interface TerrainTile {
  position: [number, number];
  type: string;
  blocking: boolean;
  movementCost: number;
}

export interface Entity {
  id: string;
  name: string;
  type: 'player' | 'enemy';
  hp: number;
  maxHp: number;
  ac: number;
  dex: number;
  speed: number;
  position: [number, number];
  alignment: Alignment;
  initiative?: number;
}

export interface GameState {
  entities: Map<string, Entity>;
  terrain: TerrainTile[];
  turnOrder: string[];
  currentTurnIndex: number;
  round: number;
  log: LogEntry[];
  phase: 'setup' | 'combat' | 'victory' | 'defeat';
  mapSize: [number, number];
}

export interface LogEntry {
  round: number;
  actor: string;
  action: string;
  target?: string;
  result: string;
  voiceLine?: string;
}

export type ActionType = 'attack' | 'move' | 'defend' | 'flee' | 'end_turn';

export interface Action {
  type: ActionType;
  actor: string;
  target?: string;
  position?: [number, number];
}

export interface ScenarioDefinition {
  name: string;
  description: string;
  mapSize: [number, number];
  maxRounds: number;
  terrain: TerrainTile[];
  entities: Omit<Entity, 'initiative'>[];
}
