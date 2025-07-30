System Architecture Overview
============================

.. contents::
   :local:
   :depth: 2

Overview
--------

The DnD Project is structured into modular components that interact through events, signals, and pluggable logic. The system is orchestrated by a main controller and supports map editing, trigger scripting, entity management, and serialization. This document outlines the major components and their interactions.

Architecture Diagram
--------------------

.. mermaid::

   graph TD
     MainController --> ScenarioOverview
     MainController --> MapEditor
     MapEditor --> TileManager
     MapEditor --> TriggerEditor
     TileManager --> Tile
     Tile --> TileEventEmitter
     TileManager --> Entity
     Entity -->|Fires| EventBus
     EventBus --> Trigger
     Trigger -->|Executes| Reaction
     Reaction -->|Modifies| Entity
     EventBus -->|Triggers| TurnManager
     TurnManager -->|Schedules| Trigger
     MapEditor -->|Uses| SettingsManager
     MapEditor -->|Uses| BackupManager
     MapEditor -->|Uses| ExportManager
     MapEditor -->|Imports| RulebookImporter
     RulebookImporter -->|Uses| APIHandler
     MapEditor -->|Logs| Logger

Component Breakdown
-------------------

**MainController**
   - Orchestrates window switching between overview and editor.
   - Holds shared `SettingsManager`.

**ScenarioOverview**
   - Entry screen for creating or loading maps.

**MapEditor**
   - Central workspace combining the tile grid, entity placement, and trigger editing.

**TileManager**
   - Maintains grid layout and state.
   - Manages `Tile` instances and embedded `Entities`.

**TileEventEmitter**
   - Emits signals for UI interactions like hover and click.
   - Bridges tiles and PyQt GUI.

**Entity**
   - Represents NPCs, monsters, traps, or objects.
   - Can emit events handled by the `EventBus`.

**EventBus**
   - Broadcasts events globally or by location.
   - Forwards to entities and triggers.

**Trigger System**
   - `Trigger` objects react to events.
   - Contain a `Condition` and `Reaction`.
   - Support chaining and cooldowns.

**TurnManager**
   - Advances game turns.
   - Dispatches delayed trigger events.

**TriggerEditor**
   - GUI for editing trigger logic.
   - Reflects dynamically from condition/reaction classes.

Support Modules
---------------

**SettingsManager**
   - Loads and saves user configuration.

**BackupManager**
   - Automatically backs up maps on change.

**ExportManager**
   - Zips maps and assets into a distributable bundle.

**Logger**
   - Centralized logging and log rotation.

**RulebookImporter**
   - Pulls monsters and spells from the 5e API.
   - Parses into in-world entities and objects.

**APIHandler**
   - HTTP client wrapper for 5e SRD content.

Extensibility
-------------

- **Plugin Architecture**: The trigger system is backed by registries for `Condition`, `Reaction`, and `Trigger` types.
- **Reflection-Based UI**: The Trigger Editor uses introspection to expose arguments and preview logic.
- **Serialization**: Maps, triggers, and entities are saved as JSON for easy modification or versioned migration.

