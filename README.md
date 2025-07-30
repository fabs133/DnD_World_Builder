# DnD_World_Builder

# 🧙 DnD World Builder: A Tactical Map Editor & Scenario Logic Engine for 5e

A PyQt-powered tactical map editor and scenario manager for **Dungeons & Dragons 5e**. Design encounters, place entities, and create intricate event-driven logic using a flexible grid system and a visual trigger scripting engine.

---

## 🎯 Features

### 🧱 Tile-Based Map Editor

* **Grid Types:** Square and hex support.
* **Tile Attributes:** Editable overlays, terrain tags, notes, labels.
* **Entity Placement:** Add NPCs, monsters, traps, and items.
* **Contextual Editing:** Right-click tiles to configure properties and triggers.

### 👥 Entity & Encounter Management

* **Entity Modeling:** Based on `GameEntity` structure (stats, inventory, abilities).
* **Import System:** Import monsters and spells via local SRD-based JSON database.
* **Categorization:** Auto-classifies entities as `enemy`, `trap`, `NPC`, etc.

### ⚡ Trigger System

* **Events:** React to `ON_DAMAGE`, `ENTER_TILE`, `ON_TURN_START`, and more.
* **Conditions:** Pluggable logic (e.g. `SkillCheck`, `AlwaysTrue`, perception tests).
* **Reactions:** Apply in-game effects like `ApplyDamage`, `AlertGamemaster`, etc.
* **Chaining:** Link multiple triggers into logical flows.
* **Cooldowns:** Built-in support for trigger cooldowns and conditional gating.

### 🏠 Trigger Editor

* **Multi-View UI:** Visual graph editor + property pane + list view.
* **Reflection-Based:** Auto-detects arguments and generates UI components.
* **Safe Scripting:** Validates and previews logic before execution.

### 📦 Backup & Export

* **Auto-Backup:** Versioned backups with configurable history.
* **Export Bundles:** Generate ZIP archives containing maps, profiles, and media.
* **Manifest Metadata:** Export includes author, timestamp, and version info.

### 🧠 Turn System

* **Turn Scheduler:** Register callbacks and events per turn.
* **Game Loop Ready:** Compatible with combat rounds, timers, and status tracking.

---

## 📂 Project Structure (Core Modules)

| Module                | Description                                                       |
| --------------------- | ----------------------------------------------------------------- |
| `tiles_gui.py`        | GUI entry with grid selector, map loader, and editor launch.      |
| `main_controller.py`  | Central app controller handling scenario switching.               |
| `trigger.py`          | Trigger class with serialization, chaining, cooldowns.            |
| `event_bus.py`        | Global pub-sub system for triggering entity logic.                |
| `export_manager.py`   | Handles zipped export of map bundles and assets.                  |
| `backup_manager.py`   | Auto-generates timestamped backups of map files.                  |
| `settings_manager.py` | Manages persistent app config and user preferences.               |
| `db_init.py`          | Initializes SQLite tables for characters, enemies, world, spells. |
| `entity_importer.py`  | Pulls entity data from local database and maps to game entities.  |
| `rulebook_entity.py`  | Heuristic categorizer and converter for SRD monsters.             |
| `rulebook_spell.py`   | Parses SRD spell entries into usable game models.                 |

---

## 🛠️ Getting Started

### Prerequisites

* Python 3.8+
* PyQt5
* SQLite3

### Launch the Editor

```bash
python tiles_gui.py
```

---

## 📄 Importing Entities & Spells

* The app uses a **pre-populated** local SRD database located in `core/data/rulebook_json/`.
* Currently, **no automatic syncing or update detection** is implemented for SRD data. Manual updates are needed if the dataset changes.

---

## 📅 Exporting

* **Export** via `ExportManager` to a `.zip` containing:

  * `map.json`
  * Optional `media/` and `profiles/`
  * `manifest.json` with metadata

---

## 🔄 Planned Features

* Color picker for tile overlays
* Undo/Redo history
* Zoom & pan for maps
* Auto-save and backup-on-save
* Recent maps & map metadata view
* Drag-and-drop entity placement

---

## 🤖 Development Notes

* **Reflection-based UI:** Adding a new `Condition` or `Reaction` auto-generates editing UI via introspection.
* **Trigger Chains:** `Trigger.next_trigger` allows compound logic (ex: check perception → apply damage → alert GM).
* **Cool Feature:** The system inverts `SkillCheck` outcomes based on reaction type (e.g., success cancels damage).

---

## 📘 Documentation

Full documentation is available at [https://fabs133.github.io/DnD_World_Builder/](https://fabs133.github.io/DnD_World_Builder/).

## 📜 License

MIT License © 2025
