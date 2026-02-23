/**
 * Alignment-specific combat voice lines.
 *
 * Ported from: models/ai/personality.py (ALIGNMENT_BEHAVIORS[...]["voice_lines"])
 */

import type { Alignment } from '../core/types';

export const VOICE_LINES: Record<Alignment, string[]> = {
  lawful_good: [
    'Stand behind me!',
    'For honor and justice!',
    "I won't let them hurt you.",
    'We fight as one!',
  ],
  neutral_good: [
    'Let me help.',
    "There's always another way.",
    "We don't have to kill them.",
    "The mission can wait — people first.",
  ],
  chaotic_good: [
    'Come and get me, ugly!',
    "I don't care about the odds!",
    'No one gets left behind!',
    'Your rules mean nothing here!',
  ],
  lawful_neutral: [
    'Holding position.',
    'Awaiting orders.',
    'Confirmed. Executing.',
    'The mission comes first.',
  ],
  true_neutral: [
    "This isn't personal.",
    "The math doesn't work.",
    "I'm out.",
    'Interesting proposition...',
  ],
  chaotic_neutral: [
    'Ooh, shiny!',
    'I wonder what happens if...',
    "Boring. Let's try something else.",
    'Sure, why not?',
  ],
  lawful_evil: [
    'You will kneel.',
    'Minions! Protect me!',
    'Your failure will be punished.',
    'I am inevitable.',
  ],
  neutral_evil: [
    'Nothing personal.',
    "The contract didn't cover this.",
    "I'm not dying for you.",
    'Pleasure doing business.',
  ],
  chaotic_evil: [
    'Hehehehe...',
    'BURN!',
    'Pain is hilarious!',
    'Nobody tells ME what to do!',
    'Watch this!',
  ],
};
