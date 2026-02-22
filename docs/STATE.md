# DnD World Builder - Project State

> Last Updated: 2026-02-22

## Overview

DnD World Builder is a PyQt-based desktop application for creating and running D&D 5e scenarios. It provides a visual map editor, entity management, combat/turn system, and trigger-based events.

## Architecture

```
DnD_World_Builder/
├── core/               # Infrastructure (logging, settings, themes, audio)
├── domain/specs/       # NEW: Specification Pattern for D&D rules (partial)
├── models/             # Domain models
│   ├── entities/       # GameEntity, characters, monsters
│   ├── flow/           # Turn system, combat, actions, reactions
│   ├── tiles/          # Tile types and behaviors
│   └── world/          # World state, lore, tile manager
├── ui/                 # PyQt interface
│   ├── dialogs/        # Modal dialogs (tile editor, triggers, stat blocks)
│   ├── panels/         # Dockable panels
│   └── main_window.py  # Main application window
├── registries/         # Data registries (items, spells, etc.)
└── tests/              # Test suite
```

## Core Systems

| System | Status | Description |
|--------|--------|-------------|
| **Map Editor** | ✅ Working | Square/hex grids, tile painting, terrain types |
| **Tile System** | ✅ Working | Terrain, tags, triggers per tile |
| **Entity System** | ✅ Working | Players, NPCs, enemies with stats |
| **Turn System** | ✅ Working | Initiative, round tracking, scheduled events |
| **Combat System** | ✅ Working | Attack resolution, damage, conditions |
| **Trigger System** | ✅ Working | Event-based triggers with conditions/reactions |
| **EventBus** | ✅ Working | Pub/sub for game events |
| **Specification Pattern** | 🔄 Partial | Rules as composable, testable specs |
| **Multiplayer** | ❌ Not Started | Session hosting/joining |

## Recent Work (Specification Pattern)

Added `domain/specs/` module implementing:
- **base.py**: Core Specification pattern with SpecResult, composable specs (&, |, ~)
- **checks.py**: Skill checks, saving throws, contested rolls
- **movement.py**: Movement, terrain, range specs (not yet saved locally)
- **entity.py**: Conditions, HP, resources, actions (not yet saved locally)
- **triggers.py**: Event-based trigger evaluation (not yet saved locally)
- **registry.py**: Rule catalog with metadata (not yet saved locally)
- **builder.py**: Visual rule creation via masks (not yet saved locally)
- **ruleset.py**: Active rule configuration per scenario (not yet saved locally)
- **pack.py**: Shareable rule bundles (not yet saved locally)
- **repository.py**: GitHub-based community sharing (not yet saved locally)

## Known Issues (from NEXT_WORK_ITEMS.md)

1. Hex grid selection renders square tiles
2. Right-click tile editing undiscoverable
3. Tag checkboxes invisible in dark themes
4. Trigger editor node overlap
5. Stat block text obscured in dark mode

## Key Dependencies

- Python 3.10+
- PyQt5/6
- SQLite (dnd_database.db)
- qt-material (theming)

## Data Flow

```
User Action → EventBus → TurnSystem/CombatSystem → Gamemaster → World State
                              ↓
                    Specification Evaluation (NEW)
                              ↓
                    SpecResult → UI Feedback
```

## Next Priority: Multiplayer Sessions

Enable multiple players to connect to a hosted scenario, with the DM controlling the session and players controlling their characters in real-time.
