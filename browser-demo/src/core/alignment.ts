/**
 * D&D Alignment system — maps alignment to tactical behavior weights.
 *
 * Ported from: models/ai/alignment.py (Alignment.to_tactical_weights)
 *              models/ai/personality.py (ALIGNMENT_BEHAVIORS)
 */

import type { Alignment, TacticalWeights } from './types';

export interface AlignmentInfo {
  name: string;
  archetype: string;
  tagline: string;
}

export const ALIGNMENT_INFO: Record<Alignment, AlignmentInfo> = {
  lawful_good: {
    name: 'Lawful Good',
    archetype: 'Protector',
    tagline: 'I will follow the code and shield the innocent.',
  },
  neutral_good: {
    name: 'Neutral Good',
    archetype: 'Benefactor',
    tagline: 'I help those in need, my way.',
  },
  chaotic_good: {
    name: 'Chaotic Good',
    archetype: 'Rebel',
    tagline: "Rules be damned, I'm doing the right thing.",
  },
  lawful_neutral: {
    name: 'Lawful Neutral',
    archetype: 'Soldier',
    tagline: 'Orders are orders.',
  },
  true_neutral: {
    name: 'True Neutral',
    archetype: 'Pragmatist',
    tagline: 'Whatever works.',
  },
  chaotic_neutral: {
    name: 'Chaotic Neutral',
    archetype: 'Free Spirit',
    tagline: "Don't fence me in.",
  },
  lawful_evil: {
    name: 'Lawful Evil',
    archetype: 'Tyrant',
    tagline: 'Power through dominion.',
  },
  neutral_evil: {
    name: 'Neutral Evil',
    archetype: 'Mercenary',
    tagline: 'Nothing personal, just business.',
  },
  chaotic_evil: {
    name: 'Chaotic Evil',
    archetype: 'Agent of Chaos',
    tagline: 'Watch it all burn.',
  },
};

/**
 * Convert an alignment to tactical behavior weights.
 *
 * Mirrors the Python `Alignment.to_tactical_weights()` method exactly —
 * same base values, same axis adjustments, same special-case overrides.
 */
export function getWeightsForAlignment(alignment: Alignment): TacticalWeights {
  const base: TacticalWeights = {
    coordination: 0.5,
    predictability: 0.5,
    allyProtection: 0.5,
    mercy: 0.5,
    selfSacrifice: 0.5,
    targetPriority: 0.5,
    honor: 0.5,
    aggression: 0.5,
    fleeThreshold: 0.3,
  };

  // Law/Chaos axis
  if (alignment.startsWith('lawful')) {
    base.coordination = 0.8;
    base.predictability = 0.8;
    base.honor = 0.75;
    base.fleeThreshold = 0.2;
  } else if (alignment.startsWith('chaotic')) {
    base.coordination = 0.2;
    base.predictability = 0.2;
    base.honor = 0.3;
    base.fleeThreshold = 0.4;
  }

  // Good/Evil axis
  if (alignment.endsWith('good')) {
    base.allyProtection = 0.85;
    base.mercy = 0.8;
    base.selfSacrifice = 0.7;
    base.targetPriority = 0.75;
    base.aggression = 0.4;
  } else if (alignment.endsWith('evil')) {
    base.allyProtection = 0.2;
    base.mercy = 0.1;
    base.selfSacrifice = 0.1;
    base.targetPriority = 0.25;
    base.aggression = 0.7;
  }

  // Special cases (exact match with Python)
  if (alignment === 'lawful_evil') {
    base.allyProtection = 0.1;
    base.fleeThreshold = 0.1;
    base.aggression = 0.6;
  }

  if (alignment === 'chaotic_evil') {
    base.mercy = 0.0;
    base.predictability = 0.1;
    base.aggression = 0.85;
  }

  if (alignment === 'chaotic_good') {
    base.selfSacrifice = 0.8;
    base.aggression = 0.6;
    base.fleeThreshold = 0.15;
  }

  return base;
}
