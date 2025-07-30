Runtime Data Flow
=================

.. contents::
   :local:
   :depth: 2

Overview
--------

This page outlines how runtime data flows through core components of the DnD Project. The system is split into layers for clarity:

- **User Interaction Flow** – GUI-driven events
- **Trigger & Reaction Flow** – Event-based logic execution
- **Data I/O Flow** – Map loading, saving, exporting
- **World & Entity State** – In-memory data interactions

User Interaction Flow
---------------------

.. mermaid::

   sequenceDiagram
     participant User
     participant MapEditor
     participant Entity
     participant EventBus
     participant Trigger

     User->>MapEditor: Clicks Tile
     MapEditor->>Entity: Fires ENTER_TILE event
     Entity->>EventBus: emit("ENTER_TILE", event_data)
     EventBus->>Trigger: check_and_react()
     Trigger->>Entity: Reaction applies effect

Trigger & Reaction Flow
-----------------------

.. mermaid::

   sequenceDiagram
     participant Trigger
     participant Condition
     participant Reaction
     participant TurnManager
     participant NextTrigger

     Trigger->>Condition: Evaluate with event_data
     alt Success (or fail for SkillCheck)
       Condition-->>Trigger: True
       Trigger->>Reaction: Execute(event_data)
       Reaction->>Entity/World: Modify state
       Reaction->>NextTrigger: Check and react (if chained)
     else Fail
       Condition-->>Trigger: False (abort)
     end
     Trigger->>TurnManager: Update cooldown

Data I/O Flow
-------------

.. mermaid::

   graph TD
     A[User Action] -->|Save| SaveSystem
     SaveSystem -->|Write| MapFile
     SaveSystem -->|Backup| BackupManager
     A2[AutoSave] --> SaveSystem
     B[Load Map] -->|Parse| JSON
     JSON -->|Rebuild| TileManager
     JSON -->|Rebuild| Entities
     ExportManager -->|Zip| ExportBundle
     ExportBundle --> Media
     ExportBundle --> Profiles
     ExportBundle --> Map

World & Entity State
--------------------

.. mermaid::

   graph TD
     MapEditor --> TileManager
     TileManager --> Tile
     Tile --> Entity
     Entity --> Stats
     Entity --> Inventory
     Entity --> Triggers
     EventBus -->|Updates| Entity
     Trigger -->|Modify| Tile
     Trigger -->|Modify| Entity
     Trigger -->|Modify| World
     TurnManager -->|Advances| Triggers
     TurnManager -->|Advances| Cooldowns

