# D&D World Builder — itch.io & Browser Release Plan

> **Goal:** Distribute D&D World Builder on itch.io with both downloadable desktop app and browser-playable demo  
> **Last Updated:** February 2025  
> **Status:** Planning Complete

---

## Executive Summary

This plan covers two release targets:

1. **Desktop Release (itch.io downloads)** — Package the existing PyQt5 app for Windows/Linux distribution. Ready in ~1 week.

2. **Browser Demo** — A streamlined, combat-only experience that runs in any modern browser. Serves as "try before download." Ready in ~4-6 weeks.

**Why both?**
- Desktop = full features, best AI
- Browser = zero friction discovery, viral potential

---

## Part 1: Desktop Release on itch.io

### 1.1 Overview

itch.io is a major distribution platform for indie games — not just browser games. Many successful projects distribute downloadable executables here.

**What we're shipping:**
```
DnD_World_Builder_v1.0.0_Windows.zip
├── DnD_World_Builder.exe
├── _internal/                    # PyInstaller dependencies
├── assets/
├── scenarios/
│   └── goblin_ambush/           # Demo scenario
├── docs/
│   ├── QUICK_START.md
│   └── OLLAMA_SETUP.md
└── README.txt
```

### 1.2 PyInstaller Configuration

```python
# build/build_release.py

import PyInstaller.__main__
import shutil
import os
from pathlib import Path

VERSION = "1.0.0"
PROJECT_ROOT = Path(__file__).parent.parent

def build_windows():
    """Build Windows executable."""
    
    PyInstaller.__main__.run([
        str(PROJECT_ROOT / 'main.py'),
        '--name=DnD_World_Builder',
        '--onedir',                          # Directory bundle (faster startup)
        '--windowed',                        # No console window
        '--icon=assets/icons/app.ico',
        
        # Include data files
        '--add-data=assets;assets',
        '--add-data=scenarios;scenarios',
        '--add-data=docs/user;docs',
        
        # Include all model/engine code
        '--hidden-import=models',
        '--hidden-import=core',
        '--hidden-import=models.ai',
        '--hidden-import=core.engine',
        
        # Exclude dev dependencies
        '--exclude-module=pytest',
        '--exclude-module=sphinx',
        '--exclude-module=black',
        '--exclude-module=mypy',
        '--exclude-module=pylint',
        
        # Output
        f'--distpath=dist',
        '--workpath=build/temp',
        '--specpath=build',
        
        # Optimization
        '--noconfirm',
    ])
    
    # Create release archive
    dist_dir = PROJECT_ROOT / 'dist' / 'DnD_World_Builder'
    
    # Add README
    shutil.copy(
        PROJECT_ROOT / 'docs' / 'user' / 'QUICK_START.md',
        dist_dir / 'README.txt'
    )
    
    # Create ZIP
    archive_name = f'DnD_World_Builder_v{VERSION}_Windows'
    shutil.make_archive(
        str(PROJECT_ROOT / 'dist' / archive_name),
        'zip',
        str(dist_dir)
    )
    
    print(f"\n✅ Built: dist/{archive_name}.zip")
    print(f"   Size: {(PROJECT_ROOT / 'dist' / f'{archive_name}.zip').stat().st_size / 1024 / 1024:.1f} MB")


def build_linux():
    """Build Linux executable."""
    
    PyInstaller.__main__.run([
        str(PROJECT_ROOT / 'main.py'),
        '--name=dnd-world-builder',
        '--onedir',
        '--icon=assets/icons/app.png',
        
        '--add-data=assets:assets',
        '--add-data=scenarios:scenarios',
        '--add-data=docs/user:docs',
        
        '--hidden-import=models',
        '--hidden-import=core',
        
        '--exclude-module=pytest',
        '--exclude-module=sphinx',
        
        f'--distpath=dist',
        '--workpath=build/temp',
        '--specpath=build',
        '--noconfirm',
    ])
    
    # Create tarball
    archive_name = f'DnD_World_Builder_v{VERSION}_Linux'
    shutil.make_archive(
        str(PROJECT_ROOT / 'dist' / archive_name),
        'gztar',
        str(PROJECT_ROOT / 'dist' / 'dnd-world-builder')
    )
    
    print(f"\n✅ Built: dist/{archive_name}.tar.gz")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', choices=['windows', 'linux', 'all'], default='windows')
    args = parser.parse_args()
    
    if args.platform in ('windows', 'all'):
        build_windows()
    if args.platform in ('linux', 'all'):
        build_linux()
```

### 1.3 PyInstaller Spec File (Alternative)

```python
# build/DnD_World_Builder.spec

# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['../main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../assets', 'assets'),
        ('../scenarios', 'scenarios'),
        ('../docs/user', 'docs'),
    ],
    hiddenimports=[
        'models',
        'models.ai',
        'models.entities',
        'core',
        'core.engine',
        'core.engine.ai',
        'PyQt5.sip',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'sphinx',
        'black',
        'mypy',
        'pylint',
        'IPython',
        'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DnD_World_Builder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../assets/icons/app.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DnD_World_Builder',
)
```

### 1.4 User Documentation

```markdown
<!-- docs/user/QUICK_START.md -->

# D&D World Builder — Quick Start

## First Launch

1. **Windows:** Double-click `DnD_World_Builder.exe`
2. **Linux:** Run `./dnd-world-builder` in terminal

## Try the Demo Scenario

1. Click **File → Open Scenario**
2. Select `scenarios/goblin_ambush/scenario.json`
3. Click **Play** to start combat

## AI Modes

| Mode | Requirements | What You Get |
|------|--------------|--------------|
| **Smart Bot** (Default) | Nothing | Instant AI that follows D&D alignments |
| **Full AI** | Ollama installed | Creative, LLM-powered NPC behavior |

Smart Bot works great out of the box! For the full AI experience, see `OLLAMA_SETUP.md`.

## Basic Controls

- **Left-click** on map: Select tile
- **Right-click** on entity: Open context menu
- **Mouse wheel**: Zoom
- **Middle-drag**: Pan

## Getting Help

- In-app: **Help → Documentation**
- Report bugs: [GitHub Issues](https://github.com/...)
- Community: [Discord](https://discord.gg/...)
```

```markdown
<!-- docs/user/OLLAMA_SETUP.md -->

# Setting Up Ollama for Full AI

## What is Ollama?

Ollama runs AI models locally on your computer. With Ollama, NPCs can:
- Generate creative tactical decisions
- React dynamically to combat situations
- Have unique voice lines

Without Ollama, the game uses "Smart Bot" mode — still fun, just more predictable!

## Installation

### Windows

1. Download from [ollama.ai](https://ollama.ai)
2. Run the installer
3. Open Command Prompt and run:
   ```
   ollama pull phi3
   ```
4. Wait for the download (~2GB)

### Linux

```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull phi3
```

## Verify It Works

1. Run `ollama serve` in a terminal (keep it open)
2. Launch D&D World Builder
3. Go to **Settings → AI**
4. Select **Full AI** mode
5. Status should show "Connected"

## Recommended Models

| Your Hardware | Recommended Model | Command |
|---------------|-------------------|---------|
| RTX 3060+ | Mistral 7B | `ollama pull mistral` |
| GTX 1060+ | Phi-3 | `ollama pull phi3` |
| CPU only, 16GB+ RAM | Gemma 2B | `ollama pull gemma:2b` |
| CPU only, 8GB RAM | Use Smart Bot mode | — |

## Troubleshooting

**"Connection refused"**
→ Make sure `ollama serve` is running

**"Model not found"**
→ Run `ollama pull phi3` first

**AI is slow (>10 seconds)**
→ Try a smaller model or use Smart Bot mode
```

### 1.5 itch.io Page Content

```markdown
# D&D World Builder

**Build and play D&D 5e scenarios with AI-powered NPCs!**

Every NPC has a D&D alignment that shapes their behavior:
- **Lawful Good** paladins protect wounded allies
- **Chaotic Evil** goblins betray their friends
- **Neutral Evil** mercenaries flee when hurt

Same encounter. Nine different personalities. Zero scripting required.

---

## Features

🗺️ **Visual Scenario Builder**
- Drag-and-drop map editor
- Square or hex grids
- Terrain types (difficult, blocking, hazards)

👹 **Entity Management**
- Players, enemies, NPCs, traps
- Full D&D 5e stat blocks
- Custom attributes and inventories

⚔️ **Combat System**
- D&D 5e initiative and actions
- Melee, ranged, and spell attacks
- Conditions and status effects

🤖 **AI-Powered NPCs**
- 9 alignment personalities
- Tactical decision-making
- Combat memory and grudges
- Works offline!

🎭 **Trigger System**
- Visual scripting for events
- Traps, ambushes, reinforcements
- No coding required

---

## AI Modes

| Mode | What You Need | Experience |
|------|---------------|------------|
| **Smart Bot** | Nothing! | Instant, alignment-driven decisions |
| **Full AI** | [Ollama](https://ollama.ai) (free) | Creative, LLM-powered behavior |

**Smart Bot works great out of the box.** For the richest experience, install Ollama (included instructions).

---

## System Requirements

**Minimum:**
- Windows 10 / Linux (64-bit)
- 4GB RAM
- 500MB disk space

**Recommended (for Full AI):**
- 16GB RAM
- NVIDIA GPU with 6GB+ VRAM
- Ollama installed

---

## Download

- **Windows (64-bit):** `DnD_World_Builder_v1.0.0_Windows.zip`
- **Linux (64-bit):** `DnD_World_Builder_v1.0.0_Linux.tar.gz`

---

## Screenshots

[screenshot_map_editor.png]
*Build your battle maps with terrain and entities*

[screenshot_combat.png]
*Watch AI-driven combat unfold*

[screenshot_alignment.png]
*Set NPC alignments with the familiar D&D grid*

[screenshot_triggers.png]
*Create dynamic events with visual scripting*

---

## Included Demo Scenario

**"The Ruined Temple Ambush"**
- 2 adventurers vs 4 goblins
- See how different alignments behave
- Trap triggers and tactical terrain

---

## Links

- 🐛 [Report Bugs](https://github.com/.../issues)
- 💬 [Discord Community](https://discord.gg/...)
- 📖 [Documentation](https://...)
- ⭐ [Source Code](https://github.com/...)

---

## Credits

Made with ❤️ for solo D&D players everywhere.

*D&D World Builder is not affiliated with Wizards of the Coast.*
```

### 1.6 Desktop Release Timeline

| Task | Effort | Day |
|------|--------|-----|
| Create app icon (ico/png) | 0.5 day | 1 |
| Set up PyInstaller config | 0.5 day | 1 |
| Test build on clean Windows VM | 0.5 day | 2 |
| Fix any missing dependencies | 0.5 day | 2 |
| Create user documentation | 0.5 day | 3 |
| Bundle demo scenario | 0.25 day | 3 |
| Create itch.io page | 0.5 day | 3 |
| Take screenshots | 0.25 day | 3 |
| Linux build (optional) | 0.5 day | 4 |
| Upload and test downloads | 0.25 day | 4 |
| **Total** | **~4 days** | |

---

## Part 2: Browser Demo

### 2.1 Strategy

The browser demo is a **funnel to desktop downloads**, not a standalone product.

**Philosophy:**
- Show the magic (alignment-driven AI)
- Don't replicate the full app
- Make them want more
- Clear CTA: "Download for the full experience"

### 2.2 Scope Definition

**IN SCOPE (Browser Demo):**
```
✅ Single scenario: "Goblin Ambush"
✅ 7x7 map with HTML5 Canvas
✅ 6 entities (2 players, 4 goblins)
✅ Turn-based combat (initiative, attack, move)
✅ Deterministic AI with alignment personalities
✅ Basic HP bars and combat log
✅ Restart button
✅ Optional: WebLLM for "Full AI" mode
```

**OUT OF SCOPE (Browser Demo):**
```
❌ Scenario editor
❌ Character creator
❌ Trigger/event system
❌ Spell system (beyond basic attack)
❌ Save/load
❌ Multiplayer
❌ Custom scenarios
❌ Full stat blocks
```

**Why this scope?**
- Demonstrates core value (alignment AI)
- Achievable in 4-6 weeks
- Doesn't compete with desktop (just teases it)

### 2.3 Tech Stack

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        BROWSER DEMO ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │    Vite     │  │  TypeScript │  │   Preact    │  │   Canvas    │   │
│  │  (Build)    │  │   (Logic)   │  │    (UI)     │  │   (Map)     │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     GAME CORE (TypeScript)                       │   │
│  │  ├── types.ts           # Entity, GameState, Action              │   │
│  │  ├── alignment.ts       # Port of models/ai/alignment.py         │   │
│  │  ├── tactical-weights.ts # Port of tactical_weights.py           │   │
│  │  ├── deterministic-ai.ts # Port of enhanced_deterministic.py     │   │
│  │  ├── initiative.ts      # Turn order                             │   │
│  │  ├── combat.ts          # Damage, attacks                        │   │
│  │  └── game-session.ts    # Main loop                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     AI OPTIONS                                   │   │
│  │  ├── DeterministicAI    # Always available, instant              │   │
│  │  └── WebLLMAI           # Optional, requires WebGPU              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why this stack?**

| Choice | Reason |
|--------|--------|
| Vite | Fast builds, excellent TS support, tiny output |
| TypeScript | Type safety for game logic, catches bugs |
| Preact | React API, 3KB size (vs React's 40KB) |
| Canvas 2D | Simple, performant, no WebGL complexity |
| No Pyodide | Avoids 10-20MB WASM bundle, faster load |

### 2.4 Directory Structure

```
browser-demo/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── src/
│   ├── main.ts                  # Entry point
│   ├── core/
│   │   ├── types.ts             # Game types
│   │   ├── alignment.ts         # Alignment system
│   │   ├── tactical-weights.ts  # AI weights
│   │   ├── initiative.ts        # Turn order
│   │   ├── combat.ts            # Damage calculation
│   │   └── game-session.ts      # Main game loop
│   ├── ai/
│   │   ├── deterministic-ai.ts  # Default AI
│   │   ├── webllm-ai.ts         # Optional LLM AI
│   │   └── voice-lines.ts       # Pre-written lines
│   ├── ui/
│   │   ├── App.tsx              # Main component
│   │   ├── MapCanvas.tsx        # Map renderer
│   │   ├── EntityPanel.tsx      # Selected entity info
│   │   ├── CombatLog.tsx        # Action history
│   │   ├── ActionButtons.tsx    # Player actions
│   │   └── AIIndicator.tsx      # AI mode display
│   ├── scenarios/
│   │   └── goblin-ambush.ts     # Hardcoded scenario
│   └── assets/
│       ├── sprites/             # Entity images
│       └── tiles/               # Terrain tiles
├── public/
│   └── favicon.ico
└── dist/                        # Build output (deploy this)
```

### 2.5 Core Types

```typescript
// src/core/types.ts

export type Alignment =
  | 'lawful_good' | 'neutral_good' | 'chaotic_good'
  | 'lawful_neutral' | 'true_neutral' | 'chaotic_neutral'
  | 'lawful_evil' | 'neutral_evil' | 'chaotic_evil';

export interface TacticalWeights {
  aggression: number;      // 0-1
  allyProtection: number;  // 0-1
  mercy: number;           // 0-1
  selfSacrifice: number;   // 0-1
  targetPriority: number;  // 0-1 (0=weak, 1=strong)
  fleeThreshold: number;   // 0-1 (HP%)
  predictability: number;  // 0-1
  honor: number;           // 0-1
}

export interface Entity {
  id: string;
  name: string;
  type: 'player' | 'enemy';
  hp: number;
  maxHp: number;
  ac: number;
  position: [number, number];
  alignment: Alignment;
  initiative?: number;
}

export interface GameState {
  entities: Map<string, Entity>;
  turnOrder: string[];
  currentTurnIndex: number;
  round: number;
  log: LogEntry[];
  phase: 'setup' | 'combat' | 'victory' | 'defeat';
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
```

### 2.6 Alignment System (TypeScript Port)

```typescript
// src/core/alignment.ts

import { Alignment, TacticalWeights } from './types';

export const ALIGNMENT_INFO: Record<Alignment, {
  name: string;
  archetype: string;
  tagline: string;
}> = {
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
    tagline: 'Rules be damned, I\'m doing the right thing.',
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
    tagline: 'Don\'t fence me in.',
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

export function getWeightsForAlignment(alignment: Alignment): TacticalWeights {
  const base: TacticalWeights = {
    aggression: 0.5,
    allyProtection: 0.5,
    mercy: 0.5,
    selfSacrifice: 0.5,
    targetPriority: 0.5,
    fleeThreshold: 0.3,
    predictability: 0.5,
    honor: 0.5,
  };
  
  // Law/Chaos axis
  if (alignment.startsWith('lawful')) {
    base.predictability = 0.8;
    base.honor = 0.75;
    base.fleeThreshold = 0.2;
  } else if (alignment.startsWith('chaotic')) {
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
  
  // Special cases
  if (alignment === 'chaotic_evil') {
    base.mercy = 0.0;
    base.predictability = 0.1;
    base.aggression = 0.85;
  }
  
  if (alignment === 'lawful_evil') {
    base.allyProtection = 0.1; // Uses pawns
    base.fleeThreshold = 0.1;  // Won't retreat
  }
  
  return base;
}
```

### 2.7 Deterministic AI (TypeScript Port)

```typescript
// src/ai/deterministic-ai.ts

import { Entity, GameState, Action, TacticalWeights } from '../core/types';
import { getWeightsForAlignment } from '../core/alignment';
import { VOICE_LINES } from './voice-lines';

export class DeterministicAI {
  private rng: () => number;
  
  constructor(seed?: number) {
    // Simple seeded RNG
    this.rng = seed !== undefined 
      ? this.createSeededRng(seed)
      : Math.random;
  }
  
  chooseAction(entity: Entity, state: GameState): Action {
    const weights = getWeightsForAlignment(entity.alignment);
    
    // 1. Check flee
    if (this.shouldFlee(entity, weights)) {
      return { type: 'flee', actor: entity.id };
    }
    
    // 2. Check protect ally
    const threatenedAlly = this.findThreatenedAlly(entity, state, weights);
    if (threatenedAlly && this.rng() < weights.allyProtection) {
      return {
        type: 'move',
        actor: entity.id,
        position: this.getProtectPosition(entity, threatenedAlly, state),
      };
    }
    
    // 3. Attack
    const target = this.chooseTarget(entity, state, weights);
    if (target) {
      return {
        type: 'attack',
        actor: entity.id,
        target: target.id,
      };
    }
    
    return { type: 'end_turn', actor: entity.id };
  }
  
  getVoiceLine(entity: Entity, action: Action): string | undefined {
    if (this.rng() > 0.3) return undefined; // 30% chance
    
    const lines = VOICE_LINES[entity.alignment] || [];
    if (lines.length === 0) return undefined;
    
    return lines[Math.floor(this.rng() * lines.length)];
  }
  
  private shouldFlee(entity: Entity, weights: TacticalWeights): boolean {
    const hpPercent = entity.hp / entity.maxHp;
    if (hpPercent > weights.fleeThreshold) return false;
    
    // Self-sacrifice might override
    if (this.rng() < weights.selfSacrifice) return false;
    
    return this.rng() < (weights.fleeThreshold - hpPercent + 0.3);
  }
  
  private findThreatenedAlly(
    entity: Entity,
    state: GameState,
    weights: TacticalWeights
  ): Entity | null {
    if (weights.allyProtection < 0.3) return null;
    
    for (const [, other] of state.entities) {
      if (other.id === entity.id) continue;
      if (other.type !== entity.type) continue;
      if (other.hp / other.maxHp < 0.5) {
        return other;
      }
    }
    return null;
  }
  
  private chooseTarget(
    entity: Entity,
    state: GameState,
    weights: TacticalWeights
  ): Entity | null {
    const enemies = Array.from(state.entities.values())
      .filter(e => e.type !== entity.type && e.hp > 0);
    
    if (enemies.length === 0) return null;
    
    // Unpredictable? Random target.
    if (this.rng() > weights.predictability) {
      return enemies[Math.floor(this.rng() * enemies.length)];
    }
    
    // Target priority
    if (weights.targetPriority < 0.4) {
      // Target weakest
      return enemies.reduce((a, b) => a.hp < b.hp ? a : b);
    } else if (weights.targetPriority > 0.6) {
      // Target strongest
      return enemies.reduce((a, b) => a.hp > b.hp ? a : b);
    } else {
      // Target nearest
      return this.findNearest(entity, enemies);
    }
  }
  
  private findNearest(from: Entity, targets: Entity[]): Entity {
    return targets.reduce((nearest, t) => {
      const distA = this.distance(from.position, nearest.position);
      const distB = this.distance(from.position, t.position);
      return distB < distA ? t : nearest;
    });
  }
  
  private distance(a: [number, number], b: [number, number]): number {
    return Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]);
  }
  
  private getProtectPosition(
    entity: Entity,
    ally: Entity,
    state: GameState
  ): [number, number] {
    // Move adjacent to ally
    const [ax, ay] = ally.position;
    const candidates: [number, number][] = [
      [ax - 1, ay], [ax + 1, ay], [ax, ay - 1], [ax, ay + 1]
    ];
    
    // Find unoccupied position closest to current
    const valid = candidates.filter(([x, y]) => {
      if (x < 0 || y < 0 || x > 6 || y > 6) return false;
      for (const [, e] of state.entities) {
        if (e.position[0] === x && e.position[1] === y) return false;
      }
      return true;
    });
    
    if (valid.length === 0) return entity.position;
    return this.findNearest({ ...entity, position: entity.position }, 
      valid.map(p => ({ position: p } as Entity))).position as [number, number];
  }
  
  private createSeededRng(seed: number): () => number {
    return () => {
      seed = (seed * 1103515245 + 12345) & 0x7fffffff;
      return seed / 0x7fffffff;
    };
  }
}
```

### 2.8 Voice Lines

```typescript
// src/ai/voice-lines.ts

import { Alignment } from '../core/types';

export const VOICE_LINES: Partial<Record<Alignment, string[]>> = {
  lawful_good: [
    "Stand behind me!",
    "For honor!",
    "I won't let them hurt you.",
    "Justice will prevail!",
  ],
  chaotic_good: [
    "Come and get me!",
    "No one gets left behind!",
    "CHARGE!",
    "Rules? What rules?",
  ],
  lawful_evil: [
    "You will kneel.",
    "Minions, attack!",
    "Your failure displeases me.",
    "I am inevitable.",
  ],
  neutral_evil: [
    "Nothing personal.",
    "I'm not dying for you.",
    "The contract didn't cover this.",
    "Pleasure doing business.",
  ],
  chaotic_evil: [
    "Hehehehe...",
    "BURN!",
    "Pain is hilarious!",
    "Watch this!",
    "Nobody tells ME what to do!",
  ],
  true_neutral: [
    "Logical.",
    "Proceeding.",
    "The math doesn't work.",
    "Interesting.",
  ],
};
```

### 2.9 WebLLM Integration (Optional)

```typescript
// src/ai/webllm-ai.ts

import { Entity, GameState, Action } from '../core/types';
import { ALIGNMENT_INFO, getWeightsForAlignment } from '../core/alignment';

// WebLLM types (simplified)
interface WebLLMEngine {
  chat(messages: { role: string; content: string }[]): Promise<string>;
}

export class WebLLMAI {
  private engine: WebLLMEngine | null = null;
  private loading = false;
  private loadError: string | null = null;
  
  async initialize(
    onProgress?: (progress: number, status: string) => void
  ): Promise<boolean> {
    if (this.engine) return true;
    if (this.loading) return false;
    
    this.loading = true;
    
    try {
      // Dynamic import - only load if needed
      const { CreateMLCEngine } = await import('@mlc-ai/web-llm');
      
      this.engine = await CreateMLCEngine('Phi-3-mini-4k-instruct-q4f16_1-MLC', {
        initProgressCallback: (report) => {
          onProgress?.(report.progress, report.text);
        },
      });
      
      this.loading = false;
      return true;
    } catch (error) {
      this.loadError = error instanceof Error ? error.message : 'Unknown error';
      this.loading = false;
      return false;
    }
  }
  
  isAvailable(): boolean {
    return this.engine !== null;
  }
  
  isLoading(): boolean {
    return this.loading;
  }
  
  getError(): string | null {
    return this.loadError;
  }
  
  async chooseAction(entity: Entity, state: GameState): Promise<Action> {
    if (!this.engine) {
      throw new Error('WebLLM not initialized');
    }
    
    const prompt = this.buildPrompt(entity, state);
    
    const response = await this.engine.chat([
      { role: 'system', content: this.getSystemPrompt(entity) },
      { role: 'user', content: prompt },
    ]);
    
    return this.parseResponse(response, entity, state);
  }
  
  private getSystemPrompt(entity: Entity): string {
    const info = ALIGNMENT_INFO[entity.alignment];
    const weights = getWeightsForAlignment(entity.alignment);
    
    const traits: string[] = [];
    if (weights.aggression > 0.7) traits.push('aggressive');
    if (weights.allyProtection > 0.7) traits.push('protective');
    if (weights.mercy < 0.3) traits.push('ruthless');
    if (weights.fleeThreshold > 0.5) traits.push('cautious');
    
    return `You are a ${info.name} ${info.archetype}. "${info.tagline}"
Style: ${traits.join(', ') || 'balanced'}
Reply with ONLY: ACTION: <attack|move|defend|flee> TARGET: <name or none>`;
  }
  
  private buildPrompt(entity: Entity, state: GameState): string {
    const enemies = Array.from(state.entities.values())
      .filter(e => e.type !== entity.type && e.hp > 0)
      .map(e => `${e.name}(${e.hp}hp)`)
      .join(', ');
    
    const allies = Array.from(state.entities.values())
      .filter(e => e.type === entity.type && e.id !== entity.id && e.hp > 0)
      .map(e => `${e.name}(${e.hp}hp)`)
      .join(', ') || 'none';
    
    return `You: ${entity.name}, ${entity.hp}/${entity.maxHp}hp
Enemies: ${enemies}
Allies: ${allies}
Choose ONE action.`;
  }
  
  private parseResponse(response: string, entity: Entity, state: GameState): Action {
    // Parse "ACTION: attack TARGET: Goblin_1"
    const actionMatch = response.match(/ACTION:\s*(\w+)/i);
    const targetMatch = response.match(/TARGET:\s*(\w+)/i);
    
    const actionType = actionMatch?.[1]?.toLowerCase();
    const targetName = targetMatch?.[1];
    
    if (actionType === 'attack' && targetName) {
      const target = Array.from(state.entities.values())
        .find(e => e.name.toLowerCase().includes(targetName.toLowerCase()));
      if (target) {
        return { type: 'attack', actor: entity.id, target: target.id };
      }
    }
    
    if (actionType === 'flee') {
      return { type: 'flee', actor: entity.id };
    }
    
    if (actionType === 'defend') {
      return { type: 'defend', actor: entity.id };
    }
    
    // Default to end turn
    return { type: 'end_turn', actor: entity.id };
  }
}

// Check if WebGPU is available
export function isWebGPUAvailable(): boolean {
  return 'gpu' in navigator;
}
```

### 2.10 UI Components

```tsx
// src/ui/App.tsx

import { useState, useEffect } from 'preact/hooks';
import { GameSession } from '../core/game-session';
import { GOBLIN_AMBUSH } from '../scenarios/goblin-ambush';
import { DeterministicAI } from '../ai/deterministic-ai';
import { WebLLMAI, isWebGPUAvailable } from '../ai/webllm-ai';
import { MapCanvas } from './MapCanvas';
import { EntityPanel } from './EntityPanel';
import { CombatLog } from './CombatLog';
import { ActionButtons } from './ActionButtons';
import { AIIndicator } from './AIIndicator';

type AIMode = 'deterministic' | 'webllm';

export function App() {
  const [game, setGame] = useState(() => new GameSession(GOBLIN_AMBUSH));
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [aiMode, setAiMode] = useState<AIMode>('deterministic');
  const [webllm, setWebllm] = useState<WebLLMAI | null>(null);
  const [webllmLoading, setWebllmLoading] = useState(false);
  const [webllmProgress, setWebllmProgress] = useState(0);
  
  const deterministicAI = useState(() => new DeterministicAI())[0];
  
  const handleEnableWebLLM = async () => {
    if (!isWebGPUAvailable()) {
      alert('WebGPU is not available in your browser. Using Smart Bot mode.');
      return;
    }
    
    setWebllmLoading(true);
    const ai = new WebLLMAI();
    const success = await ai.initialize((progress, status) => {
      setWebllmProgress(progress);
      console.log(status);
    });
    
    if (success) {
      setWebllm(ai);
      setAiMode('webllm');
    } else {
      alert(`Failed to load AI model: ${ai.getError()}`);
    }
    setWebllmLoading(false);
  };
  
  const handleRestart = () => {
    setGame(new GameSession(GOBLIN_AMBUSH));
    setSelectedEntity(null);
  };
  
  const handlePlayerAction = async (action: Action) => {
    game.executeAction(action);
    setGame({ ...game }); // Force re-render
    
    // Process AI turns
    while (!game.isPlayerTurn() && game.state.phase === 'combat') {
      const entity = game.getCurrentEntity();
      if (!entity) break;
      
      let aiAction;
      if (aiMode === 'webllm' && webllm?.isAvailable()) {
        aiAction = await webllm.chooseAction(entity, game.state);
      } else {
        aiAction = deterministicAI.chooseAction(entity, game.state);
      }
      
      const voiceLine = deterministicAI.getVoiceLine(entity, aiAction);
      game.executeAction(aiAction, voiceLine);
      setGame({ ...game });
      
      // Small delay for readability
      await new Promise(r => setTimeout(r, 500));
    }
  };
  
  return (
    <div class="app">
      <header>
        <h1>D&D World Builder — Demo</h1>
        <AIIndicator 
          mode={aiMode} 
          loading={webllmLoading}
          progress={webllmProgress}
          onEnableWebLLM={handleEnableWebLLM}
        />
      </header>
      
      <main>
        <MapCanvas 
          state={game.state}
          selectedEntity={selectedEntity}
          onSelectEntity={setSelectedEntity}
        />
        
        <aside>
          <EntityPanel 
            entity={selectedEntity ? game.state.entities.get(selectedEntity) : null}
          />
          
          {game.isPlayerTurn() && game.state.phase === 'combat' && (
            <ActionButtons
              entity={game.getCurrentEntity()!}
              state={game.state}
              onAction={handlePlayerAction}
            />
          )}
          
          {game.state.phase !== 'combat' && (
            <div class="game-over">
              <h2>{game.state.phase === 'victory' ? '🎉 Victory!' : '💀 Defeat'}</h2>
              <button onClick={handleRestart}>Play Again</button>
            </div>
          )}
        </aside>
      </main>
      
      <CombatLog entries={game.state.log} />
      
      <footer>
        <p>
          This is a demo. <a href="#download">Download the full version</a> for 
          scenario editing, more features, and richer AI.
        </p>
      </footer>
    </div>
  );
}
```

### 2.11 Map Renderer

```tsx
// src/ui/MapCanvas.tsx

import { useRef, useEffect } from 'preact/hooks';
import { GameState, Entity } from '../core/types';
import { ALIGNMENT_INFO } from '../core/alignment';

const TILE_SIZE = 64;
const MAP_SIZE = 7;

const ENTITY_COLORS: Record<string, string> = {
  player: '#4a9eff',
  enemy: '#ff4a4a',
};

interface Props {
  state: GameState;
  selectedEntity: string | null;
  onSelectEntity: (id: string | null) => void;
}

export function MapCanvas({ state, selectedEntity, onSelectEntity }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d')!;
    
    // Clear
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Draw grid
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    for (let x = 0; x <= MAP_SIZE; x++) {
      ctx.beginPath();
      ctx.moveTo(x * TILE_SIZE, 0);
      ctx.lineTo(x * TILE_SIZE, MAP_SIZE * TILE_SIZE);
      ctx.stroke();
    }
    for (let y = 0; y <= MAP_SIZE; y++) {
      ctx.beginPath();
      ctx.moveTo(0, y * TILE_SIZE);
      ctx.lineTo(MAP_SIZE * TILE_SIZE, y * TILE_SIZE);
      ctx.stroke();
    }
    
    // Draw entities
    for (const [id, entity] of state.entities) {
      if (entity.hp <= 0) continue;
      
      const [x, y] = entity.position;
      const px = x * TILE_SIZE + TILE_SIZE / 2;
      const py = y * TILE_SIZE + TILE_SIZE / 2;
      
      // Entity circle
      ctx.beginPath();
      ctx.arc(px, py, TILE_SIZE * 0.35, 0, Math.PI * 2);
      ctx.fillStyle = ENTITY_COLORS[entity.type] || '#888';
      ctx.fill();
      
      // Selection ring
      if (id === selectedEntity) {
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 3;
        ctx.stroke();
      }
      
      // Current turn indicator
      if (state.turnOrder[state.currentTurnIndex] === id) {
        ctx.strokeStyle = '#ffd700';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.arc(px, py, TILE_SIZE * 0.42, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);
      }
      
      // Name
      ctx.fillStyle = '#fff';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(entity.name, px, py + TILE_SIZE * 0.55);
      
      // HP bar
      const hpPercent = entity.hp / entity.maxHp;
      const barWidth = TILE_SIZE * 0.6;
      const barHeight = 4;
      const barX = px - barWidth / 2;
      const barY = py - TILE_SIZE * 0.45;
      
      ctx.fillStyle = '#333';
      ctx.fillRect(barX, barY, barWidth, barHeight);
      ctx.fillStyle = hpPercent > 0.5 ? '#4ade80' : hpPercent > 0.25 ? '#fbbf24' : '#ef4444';
      ctx.fillRect(barX, barY, barWidth * hpPercent, barHeight);
    }
    
  }, [state, selectedEntity]);
  
  const handleClick = (e: MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left) / TILE_SIZE);
    const y = Math.floor((e.clientY - rect.top) / TILE_SIZE);
    
    // Find entity at position
    for (const [id, entity] of state.entities) {
      if (entity.position[0] === x && entity.position[1] === y && entity.hp > 0) {
        onSelectEntity(id);
        return;
      }
    }
    
    onSelectEntity(null);
  };
  
  return (
    <canvas
      ref={canvasRef}
      width={MAP_SIZE * TILE_SIZE}
      height={MAP_SIZE * TILE_SIZE}
      onClick={handleClick}
      class="map-canvas"
    />
  );
}
```

### 2.12 Build Configuration

```typescript
// vite.config.ts

import { defineConfig } from 'vite';
import preact from '@preact/preset-vite';

export default defineConfig({
  plugins: [preact()],
  base: './', // Relative paths for itch.io
  build: {
    outDir: 'dist',
    assetsInlineLimit: 4096,
    rollupOptions: {
      output: {
        manualChunks: {
          // Keep WebLLM separate (only loaded if needed)
          webllm: ['@mlc-ai/web-llm'],
        },
      },
    },
  },
});
```

```json
// package.json

{
  "name": "dnd-world-builder-demo",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "preact": "^10.19.0"
  },
  "devDependencies": {
    "@preact/preset-vite": "^2.8.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0"
  },
  "optionalDependencies": {
    "@mlc-ai/web-llm": "^0.2.0"
  }
}
```

### 2.13 Performance Warnings UI

```tsx
// src/ui/AIIndicator.tsx

interface Props {
  mode: 'deterministic' | 'webllm';
  loading: boolean;
  progress: number;
  onEnableWebLLM: () => void;
}

export function AIIndicator({ mode, loading, progress, onEnableWebLLM }: Props) {
  return (
    <div class="ai-indicator">
      {mode === 'deterministic' && !loading && (
        <>
          <span class="ai-badge smart-bot">🤖 Smart Bot</span>
          <button onClick={onEnableWebLLM} class="enable-ai-btn">
            Try Full AI (experimental)
          </button>
          <div class="ai-tooltip">
            Smart Bot uses alignment-based decision making.
            Fast and works everywhere!
          </div>
        </>
      )}
      
      {loading && (
        <>
          <span class="ai-badge loading">⏳ Loading AI...</span>
          <progress value={progress} max={1} />
          <span class="progress-text">{Math.round(progress * 100)}%</span>
          <div class="ai-tooltip">
            Downloading AI model (~2GB). This only happens once.
          </div>
        </>
      )}
      
      {mode === 'webllm' && !loading && (
        <>
          <span class="ai-badge full-ai">✨ Full AI</span>
          <div class="ai-tooltip">
            Using WebLLM for creative AI responses.
            May take 5-15 seconds per turn.
          </div>
        </>
      )}
    </div>
  );
}
```

### 2.14 Browser Demo Timeline

| Week | Tasks |
|------|-------|
| **1** | Project setup, core types, alignment system |
| **2** | Initiative, combat, game session |
| **3** | Deterministic AI, voice lines |
| **4** | Canvas renderer, basic UI |
| **5** | Polish UI, combat log, entity panel |
| **6** | WebLLM integration (optional), testing |
| **Buffer** | Bug fixes, itch.io embedding |

**Total: 5-6 weeks**

### 2.15 itch.io Embedding

```html
<!-- In itch.io game page settings -->
<!-- Viewport size: 1024x768 -->
<!-- Frame options: Allow fullscreen -->

<!-- The dist/index.html will be loaded in an iframe -->
```

---

## Part 3: Deployment Checklist

### Desktop Release Checklist

- [ ] App icon created (ico, png)
- [ ] PyInstaller config tested
- [ ] Build on clean Windows VM
- [ ] Test all features in built exe
- [ ] Demo scenario included
- [ ] User docs written
- [ ] Screenshots captured
- [ ] itch.io page created
- [ ] Upload Windows build
- [ ] Upload Linux build (optional)
- [ ] Test download and install
- [ ] Announce release

### Browser Demo Checklist

- [ ] All core logic ported to TypeScript
- [ ] Deterministic AI working
- [ ] Canvas rendering working
- [ ] UI components complete
- [ ] WebLLM integration working (optional)
- [ ] Performance acceptable
- [ ] Mobile touch support (optional)
- [ ] Build output <5MB (excluding WebLLM)
- [ ] Test in Chrome, Firefox, Safari, Edge
- [ ] itch.io embedding tested
- [ ] CTA to desktop version prominent
- [ ] Announce demo availability

---

## Part 4: Success Metrics

### Desktop

- [ ] Downloadable and runs on Windows 10/11
- [ ] Works without Ollama (Smart Bot mode)
- [ ] Demo scenario playable
- [ ] At least 10 downloads in first week

### Browser Demo

- [ ] Loads in <3 seconds
- [ ] Combat playable without errors
- [ ] AI makes alignment-appropriate decisions
- [ ] At least 50% of players click "Download full version"
- [ ] Works on mobile (stretch goal)

---

## Quick Reference

### Build Desktop

```bash
cd DnD_World_Builder
python build/build_release.py --platform windows
# Output: dist/DnD_World_Builder_v1.0.0_Windows.zip
```

### Build Browser Demo

```bash
cd browser-demo
npm install
npm run build
# Output: dist/ (upload to itch.io)
```

### Test Browser Locally

```bash
cd browser-demo
npm run dev
# Open http://localhost:5173
```

---

*This document covers the complete itch.io release strategy for D&D World Builder.*
