# AI Personality System Unification

## Summary

The D&D alignment-based personality system has been unified and integrated into the game engine.

## What Changed

### 1. GameEntity Enhanced (`models/entities/game_entity.py`)
- Added `personality: EntityPersonality | None` attribute
- Added `position: tuple[int, int] | None` attribute  
- Added `hp`, `max_hp`, `conditions` for combat tracking
- Added helper methods: `take_damage()`, `heal()`, `is_alive`, `hp_percent`
- Personality now serializes/deserializes with entity

### 2. Personality System Unified
**Canonical location:** `models/ai/`
- `alignment.py` - The 9-alignment grid (LG → CE)
- `personality.py` - `EntityPersonality` with archetypes, will_do/wont_do, voice lines
- `tactical_weights.py` - Numerical behavior weights
- `prompt_builder.py` - `TacticalPromptBuilder` with combat memory, grudges

**Engine re-exports:** `core/engine/ai/`
- `personality.py` - Re-exports from `models/ai/` for convenience
- `prompt_builder.py` - Re-exports from `models/ai/`
- Includes legacy preset aliases (AGGRESSIVE, TACTICAL, etc.)

### 3. AIAdapter Updated (`core/engine/ai/ai_adapter.py`)
- Now uses `EntityPersonality` instead of simple `Personality`
- Reads personality from entity if available
- Combat memory tracks grudges across turns
- Target selection influenced by alignment (e.g., evil targets weak, good targets threats)
- Movement influenced by aggression level

## Usage

### Setting Personality on an Entity
```python
from models.entities.game_entity import GameEntity
from models.ai.personality import EntityPersonality
from models.ai.alignment import Alignment

# Create entity
goblin = GameEntity("Goblin Shaman", "enemy", stats={"hp": 12})

# Set alignment-based personality
goblin.set_personality(EntityPersonality(
    alignment=Alignment.LAWFUL_EVIL,
    trait="Cunning and patient",
    bond="The tribe must survive", 
    flaw="Overconfident in magic",
))

# Or use a preset
goblin.set_personality(EntityPersonality.goblin_shaman())
```

### The 9 Alignments
| Alignment | Archetype | Key Behavior |
|-----------|-----------|--------------|
| Lawful Good | Protector | Shields allies, fights with honor |
| Neutral Good | Benefactor | Helps those in need, flexible methods |
| Chaotic Good | Rebel | Dramatic heroics, rules be damned |
| Lawful Neutral | Soldier | Follows orders precisely |
| True Neutral | Pragmatist | Pure tactical optimization |
| Chaotic Neutral | Free Spirit | Unpredictable, follows whims |
| Lawful Evil | Tyrant | Uses minions as pawns, won't retreat |
| Neutral Evil | Mercenary | Cold, calculating, self-interested |
| Chaotic Evil | Agent of Chaos | Cruel, unpredictable, enjoys suffering |

### Tactical Weights
Each alignment generates tactical weights that influence AI decisions:
- `aggression` - Offensive vs defensive posture
- `ally_protection` - Shield others vs ignore them
- `mercy` - Spare fallen foes vs finish them
- `self_sacrifice` - Take hits for others vs preserve self
- `target_priority` - Threats first vs easy kills first
- `flee_threshold` - HP% at which to consider fleeing
- `honor` - Fair fight vs dirty tricks
- `coordination` - Group tactics vs solo plays
- `predictability` - Optimal moves vs surprising moves

### Combat Memory (Grudges)
The AIAdapter tracks combat events per entity:
```python
adapter.record_damage("Goblin", "Fighter", 15)  # Goblin remembers Fighter hurt them
adapter.record_kill("Fighter", "Goblin")  # Fighter's kill count increases
```

Grudge targets are prioritized in targeting decisions.

## Files Modified
- `models/entities/game_entity.py` - Added personality, position, HP tracking
- `core/engine/ai/ai_adapter.py` - Rewrote to use EntityPersonality
- `core/engine/ai/personality.py` - Now re-exports from models/ai/
- `core/engine/ai/prompt_builder.py` - Now re-exports from models/ai/
- `core/engine/ai/__init__.py` - Updated exports

## Files Added
- `tests/unit/models/entities/test_game_entity_personality.py`
- `tests/unit/core/engine/ai/test_personality.py` (updated)

## Next Steps
1. Run tests: `pytest tests/unit/models/ai tests/unit/core/engine/ai tests/unit/models/entities -v`
2. Create demo scenario with different alignments
3. Test with Ollama to see alignment-driven behavior in action
