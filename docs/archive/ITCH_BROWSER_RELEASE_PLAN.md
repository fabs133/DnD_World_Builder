# Itch.io & Browser Release Plan

> **Goal:** Release D&D World Builder on itch.io as a desktop download, then build a browser demo to lower the barrier to entry.  
> **Philosophy:** "Try before you download" — browser demo converts to desktop users.

---

## Executive Summary

| Release | Timeline | Effort | Features |
|---------|----------|--------|----------|
| **Desktop on itch.io** | Week 1-2 | 3-4 days | 100% (full app) |
| **Browser demo** | Week 3-6 | 3-4 weeks | Combat only, deterministic AI |
| **Browser + WebLLM** | Week 6-8 | +1-2 weeks | Experimental AI toggle |
| **Full browser port** | TBD | 3-6 months | Only if demand warrants |

**Key Insight:** itch.io is not browser-only. Desktop releases are first-class citizens and much faster to ship.

---

## Part 1: Desktop Release on Itch.io

### 1.1 Overview

```
┌────────────────────────────────────────────────────────────┐
│                    ITCH.IO DESKTOP RELEASE                 │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Deliverables:                                             │
│  ├── DnD_World_Builder_Windows_v1.0.0.zip                 │
│  ├── DnD_World_Builder_Linux_v1.0.0.tar.gz                │
│  └── (Optional) DnD_World_Builder_Mac_v1.0.0.dmg          │
│                                                            │
│  User Flow:                                                │
│  1. Visit itch.io page                                     │
│  2. Download ZIP for their OS                              │
│  3. Extract and run                                        │
│  4. Play included demo scenario                            │
│  5. (Optional) Install Ollama for AI features              │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 1.2 PyInstaller Configuration

```python
# build/build_release.py

import PyInstaller.__main__
import shutil
import os
import platform
from pathlib import Path

VERSION = "1.0.0"
APP_NAME = "DnD_World_Builder"

def get_platform_suffix():
    system = platform.system()
    if system == "Windows":
        return "Windows"
    elif system == "Linux":
        return "Linux"
    elif system == "Darwin":
        return "Mac"
    return "Unknown"

def build():
    """Build the application with PyInstaller."""
    
    # Common options
    options = [
        'main.py',
        f'--name={APP_NAME}',
        '--onedir',  # Faster startup than --onefile
        '--windowed',  # No console window
        
        # Include assets
        '--add-data=assets;assets' if platform.system() == 'Windows' else '--add-data=assets:assets',
        '--add-data=scenarios;scenarios' if platform.system() == 'Windows' else '--add-data=scenarios:scenarios',
        
        # Icon
        '--icon=assets/icon.ico' if platform.system() == 'Windows' else '--icon=assets/icon.icns',
        
        # Exclude unnecessary modules
        '--exclude-module=pytest',
        '--exclude-module=sphinx',
        '--exclude-module=matplotlib',  # If not used
        '--exclude-module=tkinter',     # Using PyQt5
        
        # Hidden imports (if needed)
        '--hidden-import=PyQt5.sip',
    ]
    
    PyInstaller.__main__.run(options)
    
    # Create distribution archive
    dist_dir = Path('dist') / APP_NAME
    platform_suffix = get_platform_suffix()
    archive_name = f"{APP_NAME}_{platform_suffix}_v{VERSION}"
    
    if platform.system() == "Windows":
        shutil.make_archive(f'dist/{archive_name}', 'zip', 'dist', APP_NAME)
        print(f"Created: dist/{archive_name}.zip")
    else:
        shutil.make_archive(f'dist/{archive_name}', 'gztar', 'dist', APP_NAME)
        print(f"Created: dist/{archive_name}.tar.gz")

def create_readme():
    """Create README for the release."""
    readme = """# D&D World Builder

## Quick Start

1. Extract this archive
2. Run DnD_World_Builder.exe (Windows) or ./DnD_World_Builder (Linux/Mac)
3. Try the included "Goblin Ambush" scenario

## AI Features (Optional)

For AI-powered NPCs, install Ollama:

### Windows
1. Download from https://ollama.com/download
2. Run the installer
3. Open terminal and run: ollama pull phi3
4. Restart D&D World Builder

### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull phi3
```

### Mac
```bash
brew install ollama
ollama pull phi3
```

## Without Ollama

The app works without Ollama! NPCs will use "Smart Bot" mode which makes
decisions based on their D&D alignment. It's fast and still fun!

## Requirements

- Windows 10+ / Linux / macOS 10.15+
- 4GB RAM minimum
- 8GB+ RAM recommended for AI features
- GPU optional (AI runs on CPU too, just slower)

## Troubleshooting

### App won't start
- Windows: Install Visual C++ Redistributable
- Linux: Ensure libxcb is installed

### AI not working
- Make sure Ollama is running: `ollama serve`
- Check model is downloaded: `ollama list`

## Links

- Itch.io: [link]
- GitHub: [link]
- Discord: [link]

## License

MIT License - Free for personal and commercial use.
"""
    
    with open('dist/README.txt', 'w') as f:
        f.write(readme)

if __name__ == "__main__":
    build()
    create_readme()
```

### 1.3 Spec File for Fine Control

```spec
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
        ('../docs/QUICK_START.md', 'docs'),
    ],
    hiddenimports=[
        'PyQt5.sip',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'sphinx',
        'matplotlib',
        'tkinter',
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
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../assets/icon.ico',
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

### 1.4 Demo Scenario Bundle

Create a polished demo scenario that ships with the app:

```yaml
# scenarios/demo/goblin_ambush/scenario.yaml

meta:
  name: "Goblin Ambush"
  description: "A ruined temple, a goblin warband, and two adventurers caught in the middle."
  author: "D&D World Builder Team"
  version: "1.0"
  difficulty: "Easy"
  estimated_time: "10-15 minutes"
  
  # What this demo showcases
  showcases:
    - "Alignment-driven AI behavior"
    - "Initiative and turn order"
    - "Different enemy personalities"
    - "Combat resolution"

story:
  intro: |
    The ancient Temple of Solara lies in ruins, its once-gleaming spires now 
    crumbled and overgrown. Local villagers have reported goblin activity in 
    the area, and you've been hired to investigate.
    
    As you enter the main chamber, you hear chittering from the shadows...
    
  victory: |
    The last goblin falls. The temple is silent once more.
    Among the rubble, you find a curious amulet that pulses with faint light...
    
  defeat: |
    The world grows dark as you fall. The goblins cackle in triumph.
    Perhaps another adventurer will succeed where you failed...

map:
  size: [10, 10]
  tiles:
    # Difficult terrain (rubble)
    - type: difficult
      positions: [[4, 3], [4, 4], [5, 3], [5, 4]]
      
    # Blocking terrain (pillars)
    - type: blocking
      positions: [[3, 2], [3, 7], [6, 2], [6, 7]]

entities:
  players:
    - name: "Aldric the Bold"
      class: "Fighter"
      type: player
      hp: 28
      max_hp: 28
      ac: 16
      alignment: lawful_good
      position: [2, 5]
      personality:
        trait: "Never backs down from a fight"
        bond: "Sworn to protect the innocent"
        flaw: "Too stubborn to retreat"
      stats:
        strength: 16
        dexterity: 14
        constitution: 15
        
    - name: "Lyra Sparkweave"
      class: "Wizard"
      type: player
      hp: 14
      max_hp: 14
      ac: 12
      alignment: chaotic_good
      position: [2, 4]
      personality:
        trait: "Curious to a fault"
        bond: "Knowledge is worth any risk"
        flaw: "Overestimates her abilities"
      stats:
        intelligence: 17
        dexterity: 14
        constitution: 12
        
  enemies:
    - name: "Skritt"
      type: enemy
      subtype: "Goblin Scout"
      hp: 7
      max_hp: 7
      ac: 13
      alignment: neutral_evil
      position: [7, 3]
      personality:
        trait: "Twitchy and paranoid"
        bond: "Self-preservation above all"
        flaw: "Panics when outnumbered"
      voice_lines:
        - "Did you hear that?!"
        - "I'm not going first!"
        - "Every goblin for himself!"
        
    - name: "Gnar"
      type: enemy
      subtype: "Goblin Warrior"
      hp: 7
      max_hp: 7
      ac: 13
      alignment: neutral_evil
      position: [7, 7]
      personality:
        trait: "Follows the strong"
        bond: "Obeys the shaman"
        flaw: "No initiative without orders"
        
    - name: "Rotgut"
      type: enemy
      subtype: "Goblin Berserker"
      hp: 9
      max_hp: 9
      ac: 12
      alignment: chaotic_evil
      position: [8, 5]
      personality:
        trait: "Lives for violence"
        bond: "None - chaos is all"
        flaw: "Can't resist attacking the nearest target"
      voice_lines:
        - "HAHAHAHA!"
        - "BURN! BURN!"
        - "Pain is FUNNY!"
        
    - name: "Whisper"
      type: enemy
      subtype: "Goblin Shaman"
      hp: 12
      max_hp: 12
      ac: 11
      alignment: lawful_evil
      position: [9, 5]
      personality:
        trait: "Cunning and patient"
        bond: "The tribe must survive under MY leadership"
        flaw: "Views other goblins as expendable pawns"
      voice_lines:
        - "Minions, attack!"
        - "Your failure displeases me."
        - "I will remember this treachery..."

triggers:
  - name: "Shaman Commands"
    event: round_start
    condition: "round_number == 2"
    action:
      type: log_message
      message: "Whisper hisses commands to the other goblins..."
      
  - name: "Rotgut Frenzy"
    event: entity_damaged
    condition: "entity.name == 'Rotgut' and entity.hp < entity.max_hp * 0.5"
    action:
      type: log_message
      message: "Rotgut's eyes go wild with bloodlust! He cackles maniacally!"

win_conditions:
  - type: all_enemies_defeated
  
lose_conditions:
  - type: all_players_defeated
```

### 1.5 Itch.io Page Content

```markdown
# D&D World Builder

> Build and play D&D 5e scenarios with AI-powered NPCs

## 🎮 What is this?

D&D World Builder lets you create and play D&D scenarios where every NPC has 
a personality driven by the classic alignment system. Lawful Good paladins 
protect their allies. Chaotic Evil goblins betray their friends. No scripting 
required — it emerges from who they are.

**Perfect for solo players** who want to experience D&D without a full group.

---

## ✨ Features

### 🗺️ Scenario Builder
- Visual map editor with square and hex grids
- Drag-and-drop entity placement
- Trigger and event scripting
- Character creator with full stat blocks

### 🤖 AI-Powered NPCs
- **9 D&D alignments** from Lawful Good to Chaotic Evil
- **Emergent behavior** — a Neutral Evil mercenary WILL flee when wounded
- **Combat memory** — enemies remember who hurt their allies
- **Voice lines** — NPCs say things in character

### 🎯 Combat System
- D&D 5e initiative and turn order
- Action economy (action, bonus action, movement)
- Conditions, spells, and abilities
- Deterministic replay with seeds

### 💻 Works on Any Hardware
| Mode | Requirements | Experience |
|------|--------------|------------|
| Full AI | Ollama + GPU | Rich, creative NPC responses |
| Smart Bot | None | Instant, alignment-driven decisions |

**No GPU? No problem.** Smart Bot mode uses the alignment system to make 
decisions instantly. It's not "dumb AI" — it's fast AI that still plays 
in character.

---

## 📥 Download

- **Windows (64-bit)**: DnD_World_Builder_Windows_v1.0.0.zip (45 MB)
- **Linux (64-bit)**: DnD_World_Builder_Linux_v1.0.0.tar.gz (50 MB)
- **Mac**: Coming soon (or build from source)

### Quick Start

1. Download and extract
2. Run `DnD_World_Builder.exe`
3. Click "Play Demo Scenario"
4. Fight some goblins!

### AI Setup (Optional)

Want smarter AI? Install [Ollama](https://ollama.com):

```bash
# Windows: Download installer from ollama.com
# Linux/Mac:
curl -fsSL https://ollama.com/install.sh | sh
ollama pull phi3
```

Then restart the app. It will detect Ollama automatically.

---

## 🎬 Screenshots

[screenshot_map_editor.png]
*Build your dungeon with the visual map editor*

[screenshot_combat.png]
*Watch alignments drive NPC behavior*

[screenshot_personality.png]
*Set personality traits for every entity*

[screenshot_trigger.png]
*Create complex triggers and events*

---

## 🧪 Demo Scenario: Goblin Ambush

The included demo showcases the AI system:

- **Aldric (Lawful Good Fighter)**: Will move to protect Lyra when she's wounded
- **Lyra (Chaotic Good Wizard)**: Might do something dramatic and reckless
- **Skritt (Neutral Evil Goblin)**: Will flee when hurt
- **Rotgut (Chaotic Evil Goblin)**: Will ignore dying allies to attack randomly
- **Whisper (Lawful Evil Shaman)**: Will sacrifice minions as shields

Same stats. Different alignments. Different behavior.

---

## 🛠️ System Requirements

**Minimum:**
- OS: Windows 10 / Linux / macOS 10.15
- RAM: 4 GB
- Storage: 200 MB

**Recommended (for AI):**
- RAM: 16 GB
- GPU: Any with 4GB+ VRAM (for fastest AI)
- Ollama installed

---

## 🗺️ Roadmap

- [x] Core app release
- [x] AI personality system
- [ ] Browser demo (coming soon!)
- [ ] Multiplayer (in progress)
- [ ] More scenarios

---

## 💬 Community

- **Discord**: [link]
- **GitHub**: [link]
- **Bug reports**: GitHub Issues

---

## 📜 License

MIT License — free for personal and commercial use.

Made with ❤️ for solo D&D players everywhere.
```

### 1.6 Desktop Release Checklist

```markdown
## Pre-Release Checklist

### Build
- [ ] PyInstaller builds successfully on Windows
- [ ] PyInstaller builds successfully on Linux
- [ ] No console window appears (--windowed)
- [ ] App icon displays correctly
- [ ] All assets included in bundle

### Testing
- [ ] Fresh Windows VM: app starts
- [ ] Fresh Windows VM: demo scenario loads
- [ ] Fresh Windows VM: can complete combat
- [ ] App works without Ollama (deterministic mode)
- [ ] App detects Ollama when installed
- [ ] AI responds within reasonable time

### Content
- [ ] Demo scenario polished
- [ ] README.txt included
- [ ] Quick start guide included
- [ ] Ollama instructions clear

### Itch.io
- [ ] Page created
- [ ] Screenshots uploaded (4-6)
- [ ] Description complete
- [ ] Tags added (rpg, tabletop, dnd, ai, solo)
- [ ] Pricing set (free or pay-what-you-want)
- [ ] Download files uploaded
- [ ] Tested download + run cycle

### Post-Release
- [ ] Announce on relevant subreddits
- [ ] Tweet/social media
- [ ] Monitor for first bug reports
```

### 1.7 Effort Estimate

| Task | Time |
|------|------|
| PyInstaller setup + debugging | 1 day |
| Test on clean Windows VM | 0.5 day |
| Test on Linux (if available) | 0.5 day |
| Polish demo scenario | 0.5 day |
| Write README + setup instructions | 0.5 day |
| Create itch.io page | 0.5 day |
| Screenshots + presentation | 0.5 day |
| **Total** | **~4 days** |

---

## Part 2: Browser Demo

### 2.1 Philosophy

The browser demo is **NOT** a full port. It's a taste — enough to show the AI personality system works, with a clear call-to-action to download the full version.

```
┌────────────────────────────────────────────────────────────┐
│                    BROWSER DEMO SCOPE                      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  IN SCOPE:                                                 │
│  ✓ Single hardcoded scenario (Goblin Ambush)              │
│  ✓ 10x10 map with HTML5 Canvas                            │
│  ✓ 6 entities with alignments                              │
│  ✓ Turn-based combat (initiative, attack, damage)          │
│  ✓ Deterministic AI (EnhancedDeterministicAI port)        │
│  ✓ HP bars and combat log                                  │
│  ✓ "Download Full Version" CTA                             │
│                                                            │
│  OUT OF SCOPE:                                             │
│  ✗ Scenario editor                                         │
│  ✗ Character creator                                       │
│  ✗ Triggers/events                                         │
│  ✗ Spell system (simplified attacks only)                  │
│  ✗ Save/load                                               │
│  ✗ Multiplayer                                             │
│  ✗ LLM AI (optional WebLLM as experimental)               │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 2.2 Tech Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    BROWSER TECH STACK                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  BUILD:                                                     │
│  └── Vite (fast builds, good DX)                           │
│                                                             │
│  LANGUAGE:                                                  │
│  └── TypeScript (type safety, familiar to Python devs)     │
│                                                             │
│  UI:                                                        │
│  ├── Preact (3KB, React-compatible)                        │
│  │   OR                                                     │
│  └── Vanilla JS + Web Components (zero deps)               │
│                                                             │
│  RENDERING:                                                 │
│  ├── HTML5 Canvas (simple, sufficient for grid)            │
│  │   OR                                                     │
│  └── PixiJS (if we need animations later)                  │
│                                                             │
│  AI:                                                        │
│  ├── DeterministicAI (TypeScript port) — DEFAULT           │
│  └── WebLLM (experimental toggle for high-end)             │
│                                                             │
│  STATE:                                                     │
│  └── In-memory (no persistence for demo)                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Project Structure

```
browser-demo/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── src/
│   ├── main.ts                 # Entry point
│   ├── types.ts                # Core type definitions
│   │
│   ├── core/
│   │   ├── alignment.ts        # Alignment enum
│   │   ├── tactical-weights.ts # Weight calculations
│   │   ├── game-state.ts       # GameState class
│   │   ├── initiative.ts       # Initiative tracker
│   │   ├── combat.ts           # Damage, attacks, HP
│   │   └── game-session.ts     # Turn loop
│   │
│   ├── ai/
│   │   ├── deterministic-ai.ts # Port of EnhancedDeterministicAI
│   │   ├── voice-lines.ts      # Pre-written lines by alignment
│   │   └── webllm-adapter.ts   # Optional WebLLM (experimental)
│   │
│   ├── ui/
│   │   ├── canvas-renderer.ts  # Map rendering
│   │   ├── combat-log.ts       # Action log display
│   │   ├── entity-panel.ts     # HP bars, stats
│   │   ├── controls.ts         # Buttons, actions
│   │   └── styles.css          # Minimal styling
│   │
│   ├── scenarios/
│   │   └── goblin-ambush.ts    # Hardcoded demo scenario
│   │
│   └── utils/
│       └── random.ts           # Seeded RNG
│
├── public/
│   ├── favicon.ico
│   └── assets/
│       ├── sprites/            # Entity sprites
│       └── sounds/             # (optional) Audio
│
└── dist/                       # Build output
```

### 2.4 Core Types (TypeScript)

```typescript
// src/types.ts

export type Alignment = 
  | 'lawful_good' | 'neutral_good' | 'chaotic_good'
  | 'lawful_neutral' | 'true_neutral' | 'chaotic_neutral'
  | 'lawful_evil' | 'neutral_evil' | 'chaotic_evil';

export type EntityType = 'player' | 'enemy' | 'ally';

export interface TacticalWeights {
  aggression: number;      // 0-1
  allyProtection: number;  // 0-1
  mercy: number;           // 0-1
  selfSacrifice: number;   // 0-1
  targetPriority: number;  // 0 = weak, 1 = strong
  fleeThreshold: number;   // HP% to consider fleeing
  predictability: number;  // 0 = random, 1 = optimal
  honor: number;           // 0 = dirty, 1 = fair
}

export interface Personality {
  alignment: Alignment;
  trait: string;
  bond: string;
  flaw: string;
  weights: TacticalWeights;
  voiceLines: string[];
}

export interface Entity {
  id: string;
  name: string;
  type: EntityType;
  hp: number;
  maxHp: number;
  ac: number;
  position: [number, number];
  personality: Personality;
  conditions: string[];
}

export interface GameState {
  entities: Map<string, Entity>;
  initiativeOrder: string[];
  currentTurnIndex: number;
  round: number;
  log: LogEntry[];
  isComplete: boolean;
  winner: 'player' | 'enemy' | null;
}

export interface LogEntry {
  round: number;
  actor: string;
  message: string;
  type: 'action' | 'damage' | 'voice' | 'system';
}

export interface Action {
  type: 'attack' | 'move' | 'defend' | 'flee' | 'end_turn';
  actor: string;
  target?: string;
  position?: [number, number];
}
```

### 2.5 Deterministic AI (TypeScript Port)

```typescript
// src/ai/deterministic-ai.ts

import { Entity, GameState, Action, TacticalWeights, Alignment } from '../types';
import { SeededRandom } from '../utils/random';
import { getVoiceLines } from './voice-lines';

export class DeterministicAI {
  private rng: SeededRandom;
  
  constructor(seed: number = Date.now()) {
    this.rng = new SeededRandom(seed);
  }
  
  chooseAction(entity: Entity, state: GameState): Action {
    const weights = entity.personality.weights;
    
    // 1. FLEE CHECK
    if (this.shouldFlee(entity, weights)) {
      this.maybeVoiceLine(entity, 'flee', state);
      return { type: 'flee', actor: entity.id };
    }
    
    // 2. PROTECT ALLY
    const threatenedAlly = this.findThreatenedAlly(entity, state);
    if (threatenedAlly && this.rng.random() < weights.allyProtection) {
      this.maybeVoiceLine(entity, 'protect', state);
      return { 
        type: 'move', 
        actor: entity.id, 
        position: this.positionToProtect(entity, threatenedAlly, state)
      };
    }
    
    // 3. ATTACK
    const target = this.chooseTarget(entity, weights, state);
    if (target) {
      this.maybeVoiceLine(entity, 'attack', state);
      return { type: 'attack', actor: entity.id, target: target.id };
    }
    
    // 4. END TURN
    return { type: 'end_turn', actor: entity.id };
  }
  
  private shouldFlee(entity: Entity, weights: TacticalWeights): boolean {
    const hpPercent = entity.hp / entity.maxHp;
    if (hpPercent > weights.fleeThreshold) return false;
    
    // High self-sacrifice = less likely to flee
    if (this.rng.random() < weights.selfSacrifice) return false;
    
    return true;
  }
  
  private findThreatenedAlly(entity: Entity, state: GameState): Entity | null {
    for (const [_, other] of state.entities) {
      if (other.id === entity.id) continue;
      if (!this.areAllies(entity.type, other.type)) continue;
      
      const hpPercent = other.hp / other.maxHp;
      if (hpPercent < 0.5) return other;
    }
    return null;
  }
  
  private chooseTarget(
    entity: Entity, 
    weights: TacticalWeights, 
    state: GameState
  ): Entity | null {
    const enemies = Array.from(state.entities.values())
      .filter(e => !this.areAllies(entity.type, e.type) && e.hp > 0);
    
    if (enemies.length === 0) return null;
    
    // Unpredictable? Random target.
    if (this.rng.random() > weights.predictability) {
      return enemies[this.rng.randInt(0, enemies.length - 1)];
    }
    
    // Target priority: low = weak, high = strong
    if (weights.targetPriority < 0.4) {
      return enemies.reduce((a, b) => a.hp < b.hp ? a : b);
    } else if (weights.targetPriority > 0.6) {
      return enemies.reduce((a, b) => a.hp > b.hp ? a : b);
    }
    
    // Default: random
    return enemies[this.rng.randInt(0, enemies.length - 1)];
  }
  
  private areAllies(typeA: EntityType, typeB: EntityType): boolean {
    const playerTypes: EntityType[] = ['player', 'ally'];
    const enemyTypes: EntityType[] = ['enemy'];
    
    const aIsPlayer = playerTypes.includes(typeA);
    const bIsPlayer = playerTypes.includes(typeB);
    
    return aIsPlayer === bIsPlayer;
  }
  
  private maybeVoiceLine(entity: Entity, context: string, state: GameState): void {
    if (this.rng.random() > 0.3) return; // 30% chance
    
    const lines = entity.personality.voiceLines;
    if (lines.length === 0) return;
    
    const line = lines[this.rng.randInt(0, lines.length - 1)];
    state.log.push({
      round: state.round,
      actor: entity.name,
      message: `"${line}"`,
      type: 'voice'
    });
  }
  
  private positionToProtect(
    entity: Entity, 
    ally: Entity, 
    state: GameState
  ): [number, number] {
    // Simple: move adjacent to ally
    const [ax, ay] = ally.position;
    const candidates: [number, number][] = [
      [ax - 1, ay], [ax + 1, ay], [ax, ay - 1], [ax, ay + 1]
    ];
    
    // Filter valid positions
    const valid = candidates.filter(([x, y]) => {
      if (x < 0 || y < 0 || x > 9 || y > 9) return false;
      for (const [_, e] of state.entities) {
        if (e.position[0] === x && e.position[1] === y) return false;
      }
      return true;
    });
    
    return valid[0] || entity.position;
  }
}
```

### 2.6 Canvas Renderer

```typescript
// src/ui/canvas-renderer.ts

import { GameState, Entity } from '../types';

const TILE_SIZE = 48;
const COLORS = {
  grid: '#2a2a2a',
  gridLine: '#3a3a3a',
  player: '#4a9eff',
  enemy: '#ff4a4a',
  ally: '#4aff4a',
  highlight: 'rgba(255, 255, 0, 0.3)',
  currentTurn: 'rgba(255, 255, 255, 0.3)',
};

export class CanvasRenderer {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private mapSize: number;
  
  constructor(canvas: HTMLCanvasElement, mapSize: number = 10) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d')!;
    this.mapSize = mapSize;
    
    // Set canvas size
    this.canvas.width = mapSize * TILE_SIZE;
    this.canvas.height = mapSize * TILE_SIZE;
  }
  
  render(state: GameState, selectedEntity?: string): void {
    this.clear();
    this.drawGrid();
    this.drawEntities(state, selectedEntity);
    this.drawCurrentTurn(state);
  }
  
  private clear(): void {
    this.ctx.fillStyle = COLORS.grid;
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
  }
  
  private drawGrid(): void {
    this.ctx.strokeStyle = COLORS.gridLine;
    this.ctx.lineWidth = 1;
    
    for (let i = 0; i <= this.mapSize; i++) {
      // Vertical lines
      this.ctx.beginPath();
      this.ctx.moveTo(i * TILE_SIZE, 0);
      this.ctx.lineTo(i * TILE_SIZE, this.canvas.height);
      this.ctx.stroke();
      
      // Horizontal lines
      this.ctx.beginPath();
      this.ctx.moveTo(0, i * TILE_SIZE);
      this.ctx.lineTo(this.canvas.width, i * TILE_SIZE);
      this.ctx.stroke();
    }
  }
  
  private drawEntities(state: GameState, selectedEntity?: string): void {
    for (const [id, entity] of state.entities) {
      if (entity.hp <= 0) continue;
      
      const [x, y] = entity.position;
      const px = x * TILE_SIZE;
      const py = y * TILE_SIZE;
      
      // Selection highlight
      if (id === selectedEntity) {
        this.ctx.fillStyle = COLORS.highlight;
        this.ctx.fillRect(px, py, TILE_SIZE, TILE_SIZE);
      }
      
      // Entity circle
      const color = this.getEntityColor(entity);
      this.ctx.fillStyle = color;
      this.ctx.beginPath();
      this.ctx.arc(
        px + TILE_SIZE / 2, 
        py + TILE_SIZE / 2, 
        TILE_SIZE / 3, 
        0, 
        Math.PI * 2
      );
      this.ctx.fill();
      
      // HP bar
      this.drawHPBar(entity, px, py);
      
      // Name
      this.ctx.fillStyle = '#fff';
      this.ctx.font = '10px sans-serif';
      this.ctx.textAlign = 'center';
      this.ctx.fillText(
        entity.name.split(' ')[0], // First name only
        px + TILE_SIZE / 2, 
        py + TILE_SIZE - 4
      );
    }
  }
  
  private drawHPBar(entity: Entity, px: number, py: number): void {
    const barWidth = TILE_SIZE - 8;
    const barHeight = 4;
    const hpPercent = entity.hp / entity.maxHp;
    
    // Background
    this.ctx.fillStyle = '#333';
    this.ctx.fillRect(px + 4, py + 2, barWidth, barHeight);
    
    // HP fill
    const hpColor = hpPercent > 0.5 ? '#4a4' : hpPercent > 0.25 ? '#aa4' : '#a44';
    this.ctx.fillStyle = hpColor;
    this.ctx.fillRect(px + 4, py + 2, barWidth * hpPercent, barHeight);
  }
  
  private drawCurrentTurn(state: GameState): void {
    const currentId = state.initiativeOrder[state.currentTurnIndex];
    const current = state.entities.get(currentId);
    if (!current || current.hp <= 0) return;
    
    const [x, y] = current.position;
    const px = x * TILE_SIZE;
    const py = y * TILE_SIZE;
    
    this.ctx.strokeStyle = '#fff';
    this.ctx.lineWidth = 3;
    this.ctx.strokeRect(px + 2, py + 2, TILE_SIZE - 4, TILE_SIZE - 4);
  }
  
  private getEntityColor(entity: Entity): string {
    switch (entity.type) {
      case 'player': return COLORS.player;
      case 'enemy': return COLORS.enemy;
      case 'ally': return COLORS.ally;
      default: return '#888';
    }
  }
  
  // Get entity at canvas coordinates (for click handling)
  getEntityAt(canvasX: number, canvasY: number, state: GameState): Entity | null {
    const gridX = Math.floor(canvasX / TILE_SIZE);
    const gridY = Math.floor(canvasY / TILE_SIZE);
    
    for (const [_, entity] of state.entities) {
      if (entity.position[0] === gridX && entity.position[1] === gridY) {
        return entity;
      }
    }
    return null;
  }
}
```

### 2.7 WebLLM Integration (Experimental)

```typescript
// src/ai/webllm-adapter.ts

import { Entity, GameState, Action } from '../types';

// WebLLM types (simplified)
interface WebLLMEngine {
  reload(model: string): Promise<void>;
  generate(prompt: string): Promise<string>;
}

export class WebLLMAdapter {
  private engine: WebLLMEngine | null = null;
  private modelLoaded: boolean = false;
  private loading: boolean = false;
  
  async initialize(): Promise<boolean> {
    if (this.modelLoaded) return true;
    if (this.loading) return false;
    
    this.loading = true;
    
    try {
      // @ts-ignore - WebLLM loaded via CDN
      const { CreateWebWorkerMLCEngine } = await import(
        'https://cdn.jsdelivr.net/npm/@anthropic/web-llm@latest/dist/index.js'
      );
      
      this.engine = await CreateWebWorkerMLCEngine(
        new Worker(new URL('./webllm-worker.js', import.meta.url))
      );
      
      // Load a small model
      await this.engine.reload('Phi-3-mini-4k-instruct-q4f16_1-MLC');
      
      this.modelLoaded = true;
      this.loading = false;
      return true;
    } catch (e) {
      console.error('WebLLM failed to load:', e);
      this.loading = false;
      return false;
    }
  }
  
  async chooseAction(entity: Entity, state: GameState): Promise<Action> {
    if (!this.engine || !this.modelLoaded) {
      throw new Error('WebLLM not initialized');
    }
    
    const prompt = this.buildPrompt(entity, state);
    const response = await this.engine.generate(prompt);
    return this.parseResponse(response, entity);
  }
  
  private buildPrompt(entity: Entity, state: GameState): string {
    const { alignment, trait, flaw } = entity.personality;
    const hpPercent = Math.round((entity.hp / entity.maxHp) * 100);
    
    const enemies = Array.from(state.entities.values())
      .filter(e => e.type === 'enemy' && e.hp > 0)
      .map(e => `${e.name}(${e.hp}hp)`)
      .join(', ');
    
    return `You: ${entity.name}, ${alignment}
HP: ${hpPercent}%
Trait: ${trait}
Flaw: ${flaw}
Enemies: ${enemies}

Pick ONE action: ATTACK <target>, MOVE, DEFEND, or FLEE.
Reply with just the action.`;
  }
  
  private parseResponse(response: string, entity: Entity): Action {
    const clean = response.trim().toUpperCase();
    
    if (clean.startsWith('ATTACK')) {
      const target = clean.replace('ATTACK', '').trim();
      return { type: 'attack', actor: entity.id, target };
    }
    if (clean.includes('FLEE')) {
      return { type: 'flee', actor: entity.id };
    }
    if (clean.includes('DEFEND')) {
      return { type: 'defend', actor: entity.id };
    }
    
    return { type: 'end_turn', actor: entity.id };
  }
  
  isAvailable(): boolean {
    return this.modelLoaded;
  }
  
  isLoading(): boolean {
    return this.loading;
  }
}
```

### 2.8 Main Game Loop

```typescript
// src/main.ts

import { CanvasRenderer } from './ui/canvas-renderer';
import { DeterministicAI } from './ai/deterministic-ai';
import { WebLLMAdapter } from './ai/webllm-adapter';
import { createGoblinAmbushScenario } from './scenarios/goblin-ambush';
import { GameSession } from './core/game-session';
import { GameState, Entity } from './types';

class BrowserDemo {
  private canvas: HTMLCanvasElement;
  private renderer: CanvasRenderer;
  private session: GameSession;
  private deterministicAI: DeterministicAI;
  private webLLM: WebLLMAdapter;
  private useWebLLM: boolean = false;
  
  constructor() {
    this.canvas = document.getElementById('game-canvas') as HTMLCanvasElement;
    this.renderer = new CanvasRenderer(this.canvas, 10);
    this.deterministicAI = new DeterministicAI();
    this.webLLM = new WebLLMAdapter();
    
    const scenario = createGoblinAmbushScenario();
    this.session = new GameSession(scenario);
    
    this.setupEventListeners();
    this.render();
  }
  
  private setupEventListeners(): void {
    // Canvas click
    this.canvas.addEventListener('click', (e) => this.handleCanvasClick(e));
    
    // Buttons
    document.getElementById('btn-attack')?.addEventListener('click', () => this.playerAttack());
    document.getElementById('btn-end-turn')?.addEventListener('click', () => this.endPlayerTurn());
    document.getElementById('btn-restart')?.addEventListener('click', () => this.restart());
    
    // WebLLM toggle
    document.getElementById('toggle-webllm')?.addEventListener('change', (e) => {
      this.useWebLLM = (e.target as HTMLInputElement).checked;
      if (this.useWebLLM) {
        this.initWebLLM();
      }
    });
  }
  
  private async initWebLLM(): Promise<void> {
    const status = document.getElementById('ai-status');
    if (status) status.textContent = 'Loading AI model...';
    
    const success = await this.webLLM.initialize();
    
    if (status) {
      status.textContent = success ? 'AI Ready' : 'AI Failed - Using Smart Bot';
    }
    
    if (!success) {
      (document.getElementById('toggle-webllm') as HTMLInputElement).checked = false;
      this.useWebLLM = false;
    }
  }
  
  private render(): void {
    const state = this.session.getState();
    this.renderer.render(state);
    this.updateUI(state);
  }
  
  private updateUI(state: GameState): void {
    // Update combat log
    const logDiv = document.getElementById('combat-log');
    if (logDiv) {
      logDiv.innerHTML = state.log
        .slice(-10)
        .map(entry => `<div class="log-${entry.type}">[${entry.actor}] ${entry.message}</div>`)
        .join('');
      logDiv.scrollTop = logDiv.scrollHeight;
    }
    
    // Update turn indicator
    const turnDiv = document.getElementById('current-turn');
    if (turnDiv) {
      const current = state.entities.get(state.initiativeOrder[state.currentTurnIndex]);
      turnDiv.textContent = current ? `${current.name}'s Turn` : '';
    }
    
    // Check game over
    if (state.isComplete) {
      this.showGameOver(state);
    }
  }
  
  private handleCanvasClick(e: MouseEvent): void {
    const rect = this.canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const entity = this.renderer.getEntityAt(x, y, this.session.getState());
    if (entity) {
      console.log('Selected:', entity.name);
      // Could show entity details
    }
  }
  
  private async playerAttack(): Promise<void> {
    const state = this.session.getState();
    const current = state.entities.get(state.initiativeOrder[state.currentTurnIndex]);
    
    if (!current || current.type !== 'player') return;
    
    // For demo: attack first enemy
    const enemy = Array.from(state.entities.values())
      .find(e => e.type === 'enemy' && e.hp > 0);
    
    if (enemy) {
      this.session.executeAction({ type: 'attack', actor: current.id, target: enemy.id });
      this.render();
      await this.processAITurns();
    }
  }
  
  private async endPlayerTurn(): Promise<void> {
    const state = this.session.getState();
    const current = state.entities.get(state.initiativeOrder[state.currentTurnIndex]);
    
    if (!current || current.type !== 'player') return;
    
    this.session.executeAction({ type: 'end_turn', actor: current.id });
    this.render();
    await this.processAITurns();
  }
  
  private async processAITurns(): Promise<void> {
    while (true) {
      const state = this.session.getState();
      if (state.isComplete) break;
      
      const current = state.entities.get(state.initiativeOrder[state.currentTurnIndex]);
      if (!current || current.type === 'player') break;
      if (current.hp <= 0) {
        this.session.nextTurn();
        this.render();
        continue;
      }
      
      // AI decision
      let action;
      if (this.useWebLLM && this.webLLM.isAvailable()) {
        action = await this.webLLM.chooseAction(current, state);
      } else {
        action = this.deterministicAI.chooseAction(current, state);
      }
      
      // Small delay for visual feedback
      await new Promise(resolve => setTimeout(resolve, 500));
      
      this.session.executeAction(action);
      this.render();
    }
  }
  
  private restart(): void {
    const scenario = createGoblinAmbushScenario();
    this.session = new GameSession(scenario);
    this.render();
    
    // Hide game over modal
    const modal = document.getElementById('game-over-modal');
    if (modal) modal.style.display = 'none';
  }
  
  private showGameOver(state: GameState): void {
    const modal = document.getElementById('game-over-modal');
    const title = document.getElementById('game-over-title');
    
    if (modal && title) {
      title.textContent = state.winner === 'player' ? 'Victory!' : 'Defeat!';
      modal.style.display = 'flex';
    }
  }
}

// Initialize
new BrowserDemo();
```

### 2.9 HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>D&D World Builder - Demo</title>
  <link rel="stylesheet" href="/src/ui/styles.css">
</head>
<body>
  <div class="container">
    <header>
      <h1>D&D World Builder</h1>
      <p class="subtitle">Goblin Ambush — Demo Scenario</p>
    </header>
    
    <main>
      <div class="game-area">
        <canvas id="game-canvas"></canvas>
        
        <div class="sidebar">
          <div id="current-turn" class="turn-indicator">Loading...</div>
          
          <div class="controls">
            <button id="btn-attack" class="btn btn-primary">Attack</button>
            <button id="btn-end-turn" class="btn">End Turn</button>
          </div>
          
          <div class="ai-toggle">
            <label>
              <input type="checkbox" id="toggle-webllm">
              <span>Use AI (Experimental)</span>
            </label>
            <div id="ai-status" class="ai-status">Smart Bot Mode</div>
          </div>
          
          <div id="combat-log" class="combat-log"></div>
        </div>
      </div>
    </main>
    
    <footer>
      <p>
        This is a demo. 
        <a href="https://itch.io/..." class="cta">Download the full version</a> 
        for scenario editing, more features, and richer AI!
      </p>
    </footer>
    
    <!-- Game Over Modal -->
    <div id="game-over-modal" class="modal" style="display: none;">
      <div class="modal-content">
        <h2 id="game-over-title">Victory!</h2>
        <p>The alignment-based AI drove every decision.</p>
        <p>Want more? <a href="https://itch.io/...">Download the full version!</a></p>
        <button id="btn-restart" class="btn btn-primary">Play Again</button>
      </div>
    </div>
  </div>
  
  <script type="module" src="/src/main.ts"></script>
</body>
</html>
```

### 2.10 Browser Demo Effort Estimate

| Task | Days |
|------|------|
| Project setup (Vite + TS) | 0.5 |
| Core types | 0.5 |
| Alignment + weights | 0.5 |
| GameState + GameSession | 1 |
| Initiative | 0.5 |
| Combat (damage, attacks) | 1 |
| DeterministicAI port | 2 |
| Canvas renderer | 2 |
| UI (log, controls, HP) | 1.5 |
| Hardcode Goblin Ambush | 0.5 |
| Polish + testing | 2 |
| WebLLM integration (optional) | 2 |
| **Total (without WebLLM)** | **~12 days (~2.5 weeks)** |
| **Total (with WebLLM)** | **~14 days (~3 weeks)** |

---

## Part 3: Deployment

### 3.1 Hosting Options

| Option | Cost | Ease | Notes |
|--------|------|------|-------|
| **itch.io embed** | Free | Easy | Just upload HTML5 build |
| GitHub Pages | Free | Easy | Good for demo |
| Netlify | Free | Easy | Good CI/CD |
| Vercel | Free | Easy | Great for Vite |
| Cloudflare Pages | Free | Easy | Fast global CDN |

**Recommendation:** Build with Vite, deploy to Netlify or itch.io embed.

### 3.2 Build Configuration

```typescript
// vite.config.ts

import { defineConfig } from 'vite';

export default defineConfig({
  base: './', // Relative paths for itch.io
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    // Optimize for size
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
      },
    },
  },
  // Dev server
  server: {
    port: 3000,
  },
});
```

### 3.3 itch.io HTML5 Upload

1. Build: `npm run build`
2. Zip contents of `dist/` folder
3. Upload to itch.io as "HTML" type
4. Set viewport size (960 × 640 recommended)
5. Check "Mobile friendly" if applicable
6. Enable "SharedArrayBuffer" if using WebLLM

---

## Part 4: Timeline & Milestones

```
WEEK 1-2: Desktop Release
├── Day 1-2: PyInstaller packaging
├── Day 3: Testing on clean VMs
├── Day 4: Itch.io page setup
└── Day 5: Launch & announce

WEEK 3-4: Browser Demo Core
├── Day 1: Project setup
├── Day 2-3: Core game logic port
├── Day 4-5: DeterministicAI port
├── Day 6-7: Canvas renderer
└── Day 8: Combat system

WEEK 5: Browser Demo Polish
├── Day 1-2: UI (log, controls)
├── Day 3: Goblin Ambush scenario
├── Day 4: Testing & polish
└── Day 5: Deploy to itch.io

WEEK 6 (Optional): WebLLM
├── Day 1-2: WebLLM integration
├── Day 3: Testing
└── Day 4: Deploy update

DECISION POINT (End of Week 6):
├── Review analytics & feedback
├── If browser popular → invest more
└── If desktop dominant → focus on features
```

---

## Part 5: Success Metrics

### Desktop Release
- [ ] 100+ downloads in first week
- [ ] <5% refund/complaint rate
- [ ] At least 3 positive comments
- [ ] App runs on 90%+ of systems

### Browser Demo
- [ ] Average session >3 minutes
- [ ] >10% click-through to download CTA
- [ ] Works on Chrome, Firefox, Safari
- [ ] Load time <5 seconds

### Combined
- [ ] Total conversions (demo → download) >5%
- [ ] Discord/community growth
- [ ] At least 1 content creator tries it

---

## Appendix: Performance Warnings for Users

### Browser Demo Load Screen

```
╔════════════════════════════════════════════════════════════╗
║               CHECKING YOUR BROWSER...                      ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  ✓ Modern browser detected                                 ║
║  ✓ WebGL supported                                         ║
║  ⚠ WebGPU not available                                    ║
║                                                            ║
║  ─────────────────────────────────────────────────────────║
║                                                            ║
║  AI MODE: Smart Bot                                        ║
║                                                            ║
║  NPCs will make instant decisions based on their D&D       ║
║  alignment. Chaotic Evil enemies may betray their allies!  ║
║                                                            ║
║  For richer AI with creative responses, download the       ║
║  desktop version with Ollama support.                      ║
║                                                            ║
║                    [START DEMO]                            ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

### WebLLM Warning (If Enabled)

```
╔════════════════════════════════════════════════════════════╗
║               EXPERIMENTAL AI MODE                          ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  You're enabling browser-based AI. This will:              ║
║                                                            ║
║  • Download a ~2GB model (one time)                        ║
║  • Use significant RAM/GPU memory                          ║
║  • Take 5-30 seconds per AI decision                       ║
║                                                            ║
║  Recommended: Modern GPU with 4GB+ VRAM                    ║
║                                                            ║
║  Not working? The desktop version with Ollama is faster!   ║
║                                                            ║
║        [CONTINUE ANYWAY]    [USE SMART BOT]               ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

---

## Related Documents

- `docs/PROJECT_MASTER_PLAN.md` — Overall project roadmap
- `docs/BEHAVIORAL_TEST_SYSTEM_PLAN.md` — AI testing infrastructure
- `docs/AI_PERSONALITY_UNIFICATION.md` — Alignment system details
