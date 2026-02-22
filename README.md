# DnD_World_Builder

# DnD World Builder: A Tactical Map Editor & Scenario Logic Engine for 5e

[![CI](https://github.com/fabs133/DnD_World_Builder/actions/workflows/ci.yml/badge.svg)](https://github.com/fabs133/DnD_World_Builder/actions)
[![Release](https://img.shields.io/github/v/release/fabs133/DnD_World_Builder)](https://github.com/fabs133/DnD_World_Builder/releases/latest)
[![Docs](https://github.com/fabs133/DnD_World_Builder/actions/workflows/docs.yml/badge.svg)](https://fabs133.github.io/DnD_World_Builder/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)

A PyQt-powered tactical map editor and scenario manager for **Dungeons & Dragons 5e**. Design encounters, place entities, and create intricate event-driven logic using a flexible grid system and a visual trigger scripting engine.

---

## Download

Pre-built binaries are available for all major platforms — no Python installation required.

| Platform | Download |
|----------|----------|
| **Windows** | [DnD-World-Builder-Windows.zip](https://github.com/fabs133/DnD_World_Builder/releases/latest/download/DnD-World-Builder-Windows.zip) |
| **macOS** | [DnD-World-Builder-macOS.tar.gz](https://github.com/fabs133/DnD_World_Builder/releases/latest/download/DnD-World-Builder-macOS.tar.gz) |
| **Linux** | [DnD-World-Builder-Linux.tar.gz](https://github.com/fabs133/DnD_World_Builder/releases/latest/download/DnD-World-Builder-Linux.tar.gz) |

> **Note:** On macOS, you may need to right-click and select "Open" the first time to bypass Gatekeeper (the app is not code-signed). On Linux, ensure X11 libraries are available (`libxcb-xinerama0`, `libxkbcommon-x11-0`).

See all releases on the [Releases page](https://github.com/fabs133/DnD_World_Builder/releases).

---

## Features

### Tile-Based Map Editor

* **Grid Types:** Square and hex support.
* **Tile Attributes:** Editable overlays, terrain tags, notes, labels, background images, ambient audio.
* **Entity Placement:** Add NPCs, monsters, traps, and items directly onto the map.
* **Contextual Editing:** Right-click tiles to configure properties and triggers.
* **Color Paint Mode:** Left-click to paint terrain colors across tiles.
* **Zoom & Pan:** Scroll to zoom, middle-click to pan across large maps.

### Entity & Encounter Management

* **Entity Modeling:** Based on `GameEntity` structure (stats, inventory, abilities, triggers).
* **Stat Blocks:** Professional HTML-rendered stat blocks with theme-aware styling.
* **Import System:** Import monsters and spells via local SRD-based JSON database.
* **Categorization:** Auto-classifies entities as `Player`, `Enemy`, `NPC`, or `Trap`.

### Trigger System

* **Events:** React to `ON_DAMAGE`, `ENTER_TILE`, `ON_TURN_START`, and more.
* **Conditions:** Pluggable logic (e.g. `SkillCheck`, `AlwaysTrue`, perception tests).
* **Reactions:** Apply in-game effects like `ApplyDamage`, `AlertGamemaster`, `PlaySound`.
* **Chaining:** Link multiple triggers into logical flows.
* **Cooldowns:** Built-in support for trigger cooldowns and conditional gating.

### Visual Trigger Editor

* **Multi-View UI:** Visual graph editor + property pane + list view.
* **Drag-Connect Wiring:** BFS-based layout with drag-to-connect node linking.
* **Reflection-Based:** Auto-detects arguments and generates UI components.

### Character Creator

* **6-Tab Interface:** Race, class, abilities, skills, equipment, and summary.
* **Point-Buy Validation:** Enforces D&D 5e point-buy rules for ability scores.
* **SRD Integration:** Pulls data from local D&D 5e rulebook JSON database.

### Backup & Export

* **Undo/Redo:** Full command-pattern undo/redo via `QUndoStack`.
* **Auto-Save:** Versioned backups with configurable history.
* **Export Bundles:** Generate ZIP archives containing maps, profiles, and media.
* **Manifest Metadata:** Export includes author, timestamp, and version info.

### Multiplayer (LAN / Direct IP)

* **Host/Join Sessions:** DM hosts a session, players join via IP and port.
* **Real-Time Sync:** Map state, entity positions, and turns sync across all clients.
* **Entity Claiming:** Players claim their characters on join.
* **Chat:** Built-in text chat for table talk.

### Theming

* **19 Themes:** Dark and light variants via qt-material (amber, blue, cyan, green, pink, purple, red, teal, yellow).

---

## Installation

### Prerequisites

* Python 3.11+
* pip

### Quick Start

```bash
# Clone the repository
git clone https://github.com/fabs133/DnD_World_Builder.git
cd DnD_World_Builder

# Install runtime dependencies
pip install -r requirements.txt

# Launch the application
python entry_point.py
```

### For Development

```bash
# Install all dependencies (runtime + testing + linting)
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with coverage
pytest --cov
```

---

## Project Structure

| Module | Description |
|--------|-------------|
| `entry_point.py` | Application launcher with theme selector and mode selection. |
| `core/gameCreation/` | Game logic: triggers, events, main controller. |
| `core/characterCreation/` | Character creator UI and logic. |
| `core/settings_manager.py` | Persistent app config with versioned migrations. |
| `core/data_/rulebook_json/` | Local SRD JSON database (25 files, monsters, spells, classes, etc.). |
| `models/` | Domain models: tiles, entities, game state, flow (combat, turns, actions). |
| `domain/specs/` | D&D 5e specification pattern for rules validation. |
| `ui/` | PyQt5 UI: main window, dialogs, panels, interactions, commands. |
| `network/` | Multiplayer: WebSocket protocol, session host/client, state sync. |
| `registries/` | Condition, reaction, and trigger registries. |
| `tests/` | 105 test files (~9,000 lines): unit + integration tests. |

---

## Multiplayer Quick Start

### Hosting (DM)

1. Launch the app and click **Open Game Creation**
2. Go to **Session > Host Session**
3. Choose a port (default: 8765) and click **Start Hosting**
4. Share your IP address and port with players

### Joining (Player)

1. Launch the app and click **Open Game Creation**
2. Go to **Session > Join Session**
3. Enter the DM's IP address and port
4. Enter your player name and click **Connect**
5. Claim your character from the available entities

> **Note:** For internet play, the host may need to configure port forwarding on their router for the chosen port. For LAN play, no extra configuration is needed.

---

## Importing Entities & Spells

* The app uses a **pre-populated** local SRD database located in `core/data_/rulebook_json/`.
* Contains 25 JSON files with D&D 5e monsters, spells, classes, abilities, and equipment.
* Currently, **no automatic syncing** is implemented for SRD data. Manual updates needed if the dataset changes.

---

## Exporting

**Export** via the Export menu to a `.zip` containing:

* `map.json` — serialized map with all tile and entity data
* `media/` — custom images and audio files
* `profiles/` — character profile data
* `manifest.json` — metadata (author, timestamp, version)

---

## Roadmap

See [V1_RELEASE_PLAN.md](V1_RELEASE_PLAN.md) for the full v1.0.0 release plan.

**Current priorities:**
* Fog of War / vision system
* Initiative tracker panel
* Drag & drop entity placement
* Map layers system
* Distance measurement tool

---

## Development Notes

* **Reflection-based UI:** Adding a new `Condition` or `Reaction` auto-generates editing UI via introspection.
* **Trigger Chains:** `Trigger.next_trigger` allows compound logic (e.g., check perception -> apply damage -> alert GM).
* **Command Pattern:** All map edits go through `QUndoStack` for full undo/redo support.
* **Event Bus:** Singleton pub/sub system decouples game logic from UI rendering.

---

## Documentation

Full documentation is available at [https://fabs133.github.io/DnD_World_Builder/](https://fabs133.github.io/DnD_World_Builder/).

## License

MIT License - see [LICENSE](LICENSE) for details.

[Sponsor this project](https://www.paypal.com/donate/?hosted_button_id=35ZCGB3LQJJXJ)
