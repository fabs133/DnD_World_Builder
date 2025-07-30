Trigger System Overview
=======================

.. contents::
   :local:
   :depth: 2

Concept
-------

Triggers are logic units that respond to in-game events. They consist of:

- **Event type** (e.g., `ENTER_TILE`, `ON_DAMAGE`)
- **Condition** (e.g., always true, perception check)
- **Reaction** (e.g., apply damage, spawn trap)
- Optional **Chaining** to further triggers
- Optional **Cooldowns** to prevent overfiring

Each trigger listens for events dispatched via the `EventBus`.

Trigger Flow Diagram
--------------------

.. mermaid::

   graph TD
     Event[Game Event: ENTER_TILE] -->|dispatch| Trigger1
     Trigger1 -->|Condition| ConditionCheck[PerceptionCheck]
     ConditionCheck -->|Fails| End1[Do Nothing]
     ConditionCheck -->|Succeeds| Reaction1[ApplyDamage]
     Reaction1 --> Reaction2[AlertGamemaster]
     Reaction2 -->|Optional| NextTrigger

Trigger Structure
-----------------

**Trigger Components:**

- **Event Type:** A string identifier (e.g., `"ENTER_TILE"`).
- **Condition:** A callable, such as:
  - `AlwaysTrue` – always passes.
  - `PerceptionCheck` – simulates a skill roll using `character_stats`.
  - `SkillCheck` – supports DC, stat-based success/failure.
- **Reaction:** A callable or class with an `execute()` method. Examples:
  - `ApplyDamage`
  - `AlertGamemaster`
  - `MoveEntity`, `RevealArea`, `SpawnEntity`
- **Chaining:** A trigger can define a `next_trigger`, which is conditionally or automatically fired.
- **Cooldown:** Prevents reactivation for a number of turns (via `TurnManager`).

Condition Evaluation
--------------------

.. note::

   For `SkillCheck` and `PerceptionCheck`, the logic is inverted:

   - If the check **fails**, the reaction is **triggered**.
   - This is useful for traps: players failing to notice one may take damage.

Trigger JSON Structure
----------------------

.. note::

    The trigger system uses a JSON structure to define triggers, making it easy to create, modify, and serialize them.
    The JSON structure for a trigger includes the event type, label, condition, reaction, and optional chaining and cooldowns. 
    This allows for flexible and dynamic trigger definitions that can be easily modified or extended.

**Example:**

```python
    {
    "event_type": "ENTER_TILE",
    "label": "Trap Trigger",
    "condition": {
        "type": "SkillCheck",
        "skill": "Perception",
        "dc": 12
    },
    "reaction": {
        "type": "ApplyDamage",
        "args": {
        "amount": 5
        }
    },
    "next_trigger": {
        "event_type": "CHAIN",
        "condition": {
        "type": "AlwaysTrue"
        },
        "reaction": {
        "type": "AlertGamemaster",
        "args": {
            "message": "Trap sprung!"
        }
        }
    }
    }
```
