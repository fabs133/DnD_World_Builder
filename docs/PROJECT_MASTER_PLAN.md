# D&D World Builder — Master Project Plan

> **Version:** 1.0.0 (Released)
> **Last Updated:** February 2026
> **Status:** Phase 1 complete, Demo & Validation phase in progress

---

## Executive Summary

D&D World Builder is a desktop application for building and playing D&D 5e scenarios with AI-powered NPCs. The unique value proposition is **alignment-driven AI** — NPCs behave according to the classic D&D alignment grid (Lawful Good → Chaotic Evil), creating emergent storytelling without scripting.

**Target Users:**
- Solo D&D players who can't find groups
- DMs who want to prototype encounters
- D&D fans who want AI companions that role-play

**Core Differentiator:** "Same scenario, 9 different goblin personalities, no scripting required."

---

## Current State

### What's Complete (v1.0.0)

| Feature | Status | Notes |
|---------|--------|-------|
| Map Editor | ✅ | Square/hex grids, terrain types |
| Entity Management | ✅ | Players, enemies, NPCs, traps |
| Stat Block System | ✅ | D&D 5e stats, custom attributes |
| Trigger/Event System | ✅ | Visual scripting, conditions |
| Character Creator | ✅ | Classes, races, backgrounds |
| Undo/Redo | ✅ | Full history |
| Auto-save | ✅ | Crash recovery |
| ZIP Export | ✅ | Portable scenarios |
| Multiplayer (Phase 1-2) | ✅ | WebSocket, state sync, chat |
| Test Suite | ✅ | 808 tests passing |

### What's In Progress

| Feature | Status | Notes |
|---------|--------|-------|
| Demo Scenario ("Goblin Ambush") | 🔄 | Scenario YAML + loader + CLI runner |
| Low-Spec Hardware Detection | 🔄 | Auto-detect GPU/RAM, recommend AI tier |

### Changes Since Last Update

| Component | Status | Notes |
|-----------|--------|-------|
| AI Personality System | ✅ | 9 alignment profiles, 6 entity presets, TacticalWeights |
| Behavioral Test Harness | ✅ | MockAIAdapter (312 lines), BehavioralTestHarness, AlignmentAssertions |
| Headless Game Engine | ✅ | GameSession, InitiativeTracker, ActionExecutor, GameState snapshots |
| Ollama Integration | ✅ | OllamaClient, AIAdapter with retry loop, CombatMemory, TacticalPromptBuilder |
| Behavioral Tests | ✅ | 11 test classes covering all 9 alignments + contrast tests |
| Integration Tests | ✅ | AI combat, demo encounter, headless combat tests |
| PyInstaller Packaging | ✅ | dnd_world_builder.spec for cross-platform builds |

### What's Planned

| Feature | Priority | Notes |
|---------|----------|-------|
| Demo Scenario ("Goblin Ambush") | High | Showcase AI personalities |
| Low-Spec Optimization | High | Accessibility for all hardware |
| itch.io Desktop Release | High | Distribution |
| Browser Demo | Medium | Try-before-download |
| Content Pipeline | Low | Marketing automation |
| Personality Import/Export | Low | Community features |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         D&D WORLD BUILDER                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │   UI (PyQt5)    │  │  Game Engine    │  │   AI System     │         │
│  │                 │  │                 │  │                 │         │
│  │ • Map Editor    │  │ • GameSession   │  │ • Alignment     │         │
│  │ • Entity Panel  │  │ • Initiative    │  │ • Personality   │         │
│  │ • Stat Blocks   │  │ • Actions       │  │ • TacticalAI    │         │
│  │ • Triggers      │  │ • Combat        │  │ • Ollama Client │         │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘         │
│           │                    │                    │                   │
│           └────────────────────┼────────────────────┘                   │
│                                ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         CORE MODELS                              │   │
│  │  • GameEntity (with Personality)                                 │   │
│  │  • World, Tiles, Terrain                                         │   │
│  │  • Actions, Spells, Conditions                                   │   │
│  │  • Triggers, Events                                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## AI Personality System

### The Alignment Grid

Every entity can have a D&D alignment that drives its tactical decisions:

```
           LAWFUL          NEUTRAL         CHAOTIC
         ┌─────────────┬─────────────┬─────────────┐
   GOOD  │ Protector   │ Benefactor  │ Rebel       │
         │ Shields     │ Helps those │ Dramatic    │
         │ allies,     │ in need,    │ heroics,    │
         │ fights fair │ flexible    │ rules be    │
         │             │             │ damned      │
         ├─────────────┼─────────────┼─────────────┤
NEUTRAL  │ Soldier     │ Pragmatist  │ Free Spirit │
         │ Follows     │ Whatever    │ Follows     │
         │ orders      │ works       │ whims       │
         ├─────────────┼─────────────┼─────────────┤
   EVIL  │ Tyrant      │ Mercenary   │ Agent of    │
         │ Uses pawns, │ Cold,       │ Chaos       │
         │ won't       │ calculating,│ Cruel,      │
         │ retreat     │ self-first  │ burns it    │
         │             │             │ all         │
         └─────────────┴─────────────┴─────────────┘
```

### Behavioral Expectations by Alignment

| Alignment | Flee Rate | Mercy Rate | Protect Allies | Betrayal | Predictability |
|-----------|-----------|------------|----------------|----------|----------------|
| Lawful Good | <20% | >70% | >60% | <5% | High |
| Neutral Good | <30% | >60% | >50% | <10% | Medium |
| Chaotic Good | <20% | >50% | >40% | <10% | Low |
| Lawful Neutral | <30% | 40-60% | 30-50% | <15% | High |
| True Neutral | 30-50% | 40-60% | 30-50% | <20% | Medium |
| Chaotic Neutral | 30-50% | 30-50% | 20-40% | <30% | Low |
| Lawful Evil | <20% | <30% | <30% | <20% | High |
| Neutral Evil | >40% | <20% | <30% | 20-40% | Medium |
| Chaotic Evil | <30% | <20% | <30% | >20% | Low |

### Implementation Files

| File | Purpose |
|------|---------|
| `models/ai/alignment.py` | Alignment enum, parsing, tactical weight generation |
| `models/ai/personality.py` | EntityPersonality, archetypes, will_do/wont_do |
| `models/ai/tactical_weights.py` | Numerical weights for AI decisions |
| `models/ai/prompt_builder.py` | TacticalPromptBuilder, CombatMemory |
| `core/engine/ai/ai_adapter.py` | LLM-powered AI player |
| `core/engine/ai/ollama_client.py` | Ollama HTTP client |

### Integration with GameEntity

```python
from models.entities.game_entity import GameEntity
from models.ai.personality import EntityPersonality
from models.ai.alignment import Alignment

# Create entity with personality
goblin = GameEntity("Goblin Shaman", "enemy", stats={"hp": 12})
goblin.set_personality(EntityPersonality(
    alignment=Alignment.LAWFUL_EVIL,
    trait="Cunning and patient",
    bond="The tribe must survive",
    flaw="Overconfident in magic",
))

# Or use presets
grunt = GameEntity("Goblin Grunt", "enemy", stats={"hp": 7})
grunt.set_personality(EntityPersonality.goblin_grunt())
```

---

## Behavioral Test System

### Purpose

Validate that AI actually behaves according to alignment through statistical testing.

### Test Modes

| Mode | AI Type | Runs | Speed | Use Case |
|------|---------|------|-------|----------|
| Fast CI | MockAI | 10 | <1 min | PR checks |
| Full CI | MockAI | 100 | ~2 min | Merge to main |
| Stress Test | Real LLM | 50 | ~1 hour | Full validation |

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| BehaviorEvent | `stats.py` | Enum of trackable events |
| EntityRunStats | `stats.py` | Per-entity per-run metrics |
| BehaviorStats | `stats.py` | Aggregated stats across runs |
| MockAIAdapter | `mock_ai.py` | Deterministic AI for fast testing |
| BehavioralTestHarness | `harness.py` | Orchestrates N runs |
| AlignmentAssertions | `assertions.py` | Pre-built behavioral checks |
| OllamaPool | `llm_pool.py` | Dual-LLM stress testing |

### Example Test

```python
@behavioral_test(runs=100)
class TestChaoticEvilBehavior:
    scenario = "goblin_ambush"
    entity_filter = lambda e: e.alignment == Alignment.CHAOTIC_EVIL
    
    def test_low_mercy(self, stats: BehaviorStats):
        assert stats.mercy_rate < 0.2, f"CE showed mercy {stats.mercy_rate:.0%}"
    
    def test_unpredictable(self, stats: BehaviorStats):
        assert stats.target_entropy > 0.4, "CE is too predictable"
```

### Full Documentation

See: `docs/BEHAVIORAL_TEST_SYSTEM_PLAN.md`

---

## Low-Spec Optimization

### Hardware Tiers

| Tier | Example Hardware | AI Mode | Response Time |
|------|------------------|---------|---------------|
| High | RTX 3080, 32GB RAM | Full LLM (Mistral 7B) | <1s |
| Mid | RTX 3060, 16GB RAM | Full LLM (Phi-3) | 1-2s |
| Low GPU | GTX 1060, 16GB RAM | Lite LLM (Gemma 2B) | 2-4s |
| CPU Good | Ryzen 5, 32GB RAM | Lite LLM (Phi-3 mini) | 5-15s |
| CPU Modest | i5 laptop, 16GB RAM | Lite LLM (TinyLlama) | 15-30s |
| Minimal | Old laptop, 8GB RAM | Deterministic | Instant |

### AI Capability Tiers

```
TIER 1: Full LLM              "Tactical genius"
├── Rich personality prompts
├── Combat memory & grudges
├── Creative voice lines
└── Response time: <2s

TIER 2: Lite LLM              "Smart but brief"
├── Simplified prompts (fewer tokens)
├── No voice line generation
├── Basic personality influence
└── Response time: 5-15s

TIER 3: Enhanced Deterministic "Alignment-driven bot"
├── MockAI with full tactical weights
├── Pre-written voice lines
├── No LLM calls at all
└── Response time: instant

TIER 4: Basic Deterministic   "Simple bot"
├── Basic attack/defend/flee logic
├── No personality flavor
└── Response time: instant
```

### Key Principle

**No player is locked out.** Everyone gets alignment-driven AI — it just runs differently under the hood.

### Implementation Files

| File | Purpose |
|------|---------|
| `core/system/hardware_profile.py` | Auto-detect GPU, RAM, recommend tier |
| `core/system/ai_config.py` | AIConfig, ModelConfig, AIMode enum |
| `core/engine/ai/lite_prompt_builder.py` | Reduced-token prompts |
| `core/engine/ai/enhanced_deterministic.py` | Smart non-LLM AI |
| `core/engine/ai/response_cache.py` | Cache similar situations |
| `core/engine/ai/batch_processor.py` | Pre-compute AI turns |

### Multiplayer: Host Delegation

Low-spec players can have the host compute their AI decisions:

```python
# Guest marks entities as host-delegated
config = AIConfig.host_delegated()

# When entity's turn comes:
# 1. Guest sends DelegatedAIRequest to host
# 2. Host computes using their AI
# 3. Host sends DelegatedAIResponse back
# 4. Guest applies the action
```

---

## Demo Scenario: "Ruined Temple Ambush"

### Setup

- **Map:** 7x7 grid
- **Players:** Fighter (28 HP, Lawful Good), Wizard (14 HP, Chaotic Good)
- **Enemies:** 3 Goblin Grunts (7 HP each, Neutral Evil), 1 Goblin Shaman (12 HP, Lawful Evil)
- **Terrain:** Rubble (difficult), Pillars (blocking)
- **Trigger:** Pressure plate trap

### What It Demonstrates

1. Initiative rolling with DEX tiebreakers
2. Movement with terrain costs
3. Melee/ranged attacks
4. Spell casting (Shaman)
5. Conditions (poisoned from trap)
6. **Alignment-driven behavior:**
   - NE goblins flee when wounded
   - LE shaman uses grunts as shields
   - LG fighter protects wizard
   - CG wizard takes dramatic risks

---

## Content & Marketing

### Meme Voice Lines

| Meme | Context | Line |
|------|---------|------|
| Isengard | Ally captured | "They're taking the {ally} to {location}!" |
| Wilhelm Scream | Death from height | *Sound effect* |
| Geronimo | Reckless charge | "GERONIMO!" |
| Arrow to the knee | Leg injury | "I used to be an adventurer..." |
| Skyrim guard | Lawful entity | "Stop! You violated the law!" |

### Content Pipeline (Future)

```
tools/content/
├── analyze_feature.py      # Extract feature info from git
├── generate_script.py      # LLM suggests video script
├── plan_scenes.py          # Map script to captures
├── capture_gameplay.py     # Headless recording
├── generate_tts.py         # Narration
└── assemble_video.py       # FFmpeg composition
```

**Status:** Planned for after manual video creation validates the format.

### Outreach Strategy

1. **Create demo video** showing alignment-driven combat
2. **Post to solo D&D communities** (Reddit, Discord)
3. **Reach out to D&D YouTubers** (smaller channels first)
4. **Lead with differentiator:** "AI companions that role-play their alignment"

---

## Development Roadmap

### Phase 1: AI Foundation (COMPLETE)

| Task | Status | Owner |
|------|--------|-------|
| Unify personality systems | ✅ | Claude |
| Integrate personality into GameEntity | ✅ | Claude |
| Behavioral test system plan | ✅ | Claude |
| Implement MockAIAdapter | ✅ | Claude Code |
| Implement BehavioralTestHarness | ✅ | Claude Code |
| Test with Ollama end-to-end | ⏳ | — |

### Phase 2: Demo & Validation (Current)

| Task | Priority | Effort |
|------|----------|--------|
| Build "Goblin Ambush" scenario | High | 1 day |
| Run AI vs AI combat | High | 0.5 day |
| Record demo video | High | 1 day |
| Show to 3-5 D&D players | High | — |
| Iterate based on feedback | High | — |

### Phase 3: Release

| Task | Priority | Effort |
|------|----------|--------|
| PyInstaller packaging | ✅ | Done (dnd_world_builder.spec) |
| itch.io page setup | High | 0.5 day |
| Desktop release (Windows) | High | 0.5 day |
| Browser demo (optional) | Medium | 3 weeks |

### Phase 4: Polish (Based on Feedback)

| Task | Priority | Effort |
|------|----------|--------|
| Low-spec optimizations | Based on demand | 1 week |
| Personality import/export | Based on demand | 3 days |
| Additional scenarios | Based on demand | Ongoing |
| Full browser port | If demo popular | 3-6 months |

---

## File Structure Reference

```
DnD_World_Builder/
├── core/
│   ├── engine/
│   │   ├── ai/
│   │   │   ├── ai_adapter.py          # LLM-powered AI
│   │   │   ├── ollama_client.py       # Ollama HTTP client
│   │   │   ├── personality.py         # Re-exports from models/ai
│   │   │   ├── prompt_builder.py      # Re-exports from models/ai
│   │   │   ├── action_parser.py       # Parse LLM → Action
│   │   │   └── enhanced_deterministic.py  # Smart non-LLM AI (planned)
│   │   ├── game_session.py            # Headless orchestrator
│   │   ├── game_state.py              # Immutable snapshots
│   │   ├── initiative.py              # D&D initiative tracker
│   │   └── action_executor.py         # Validates + executes actions
│   ├── system/
│   │   ├── hardware_profile.py        # Auto-detect GPU, RAM, recommend tier
│   │   └── ai_config.py               # AI mode configuration
│   └── testing/
│       ├── behavioral/
│       │   ├── stats.py               # BehaviorEvent, BehaviorStats
│       │   ├── mock_ai.py             # Deterministic test AI
│       │   ├── harness.py             # Test harness
│       │   └── assertions.py          # Behavioral assertions
│       └── scenarios/
│           └── goblin_ambush.yaml
├── models/
│   ├── ai/
│   │   ├── alignment.py               # Alignment grid
│   │   ├── personality.py             # EntityPersonality
│   │   ├── tactical_weights.py        # Numerical weights
│   │   └── prompt_builder.py          # TacticalPromptBuilder
│   └── entities/
│       └── game_entity.py             # Now includes personality
├── tests/
│   ├── unit/
│   │   └── models/ai/                 # Existing tests
│   └── behavioral/
│       ├── conftest.py                # Fixtures: quick/thorough harness, scenarios
│       └── test_alignments.py         # 11 test classes for all 9 alignments
└── docs/
    ├── AI_PERSONALITY_UNIFICATION.md
    ├── BEHAVIORAL_TEST_SYSTEM_PLAN.md
    └── PROJECT_MASTER_PLAN.md         # This file
```

---

## Success Metrics

### Technical

- [ ] 100% of alignment behavioral tests pass
- [ ] AI response time <2s on mid-tier hardware
- [ ] Deterministic mode works on 8GB RAM laptop
- [ ] Zero crashes in 1-hour stress test

### User Validation

- [ ] 3+ D&D players say "the AI feels like it has personality"
- [ ] Demo video gets shared in D&D communities
- [ ] At least one content creator interested

### Release

- [ ] Desktop app downloadable from itch.io
- [ ] Works out-of-box without Ollama (deterministic mode)
- [ ] Clear instructions for Ollama setup

---

## Open Questions

1. **Should we support Mac?** — Requires a Mac to build. Defer unless requested.
2. **Should browser demo include scenario editor?** — Probably not (too much work).
3. **How to handle Ollama model downloads?** — In-app downloader or instructions?
4. **Pricing on itch.io?** — Recommend "Pay what you want" with $0 minimum.

---

## Quick Reference: Commands

```bash
# Run all tests
pytest tests/ -v

# Run AI tests specifically
pytest tests/unit/models/ai tests/unit/core/engine/ai -v

# Run behavioral tests (when implemented)
pytest tests/behavioral/ -v

# Stress test with Ollama (when implemented)
python -m core.testing.behavioral.stress_runner \
    scenarios/goblin_ambush.yaml --runs 50 --mode dual_gpu

# Build for Windows (when implemented)
python build_release.py --platform windows
```

---

*This document is the single source of truth for the D&D World Builder project.*
