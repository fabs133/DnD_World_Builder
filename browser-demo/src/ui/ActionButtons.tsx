import type { Entity, GameState, Action } from '../core/types';
import { chebyshev } from '../core/combat';

interface Props {
  entity: Entity;
  state: GameState;
  onAction: (action: Action) => void;
}

export function ActionButtons({ entity, state, onAction }: Props) {
  // Find attackable enemies (adjacent, Chebyshev <= 1)
  const enemies: Entity[] = [];
  for (const [, e] of state.entities) {
    if (e.type !== entity.type && e.hp > 0) {
      if (chebyshev(entity.position, e.position) <= 1) {
        enemies.push(e);
      }
    }
  }

  return (
    <div class="action-buttons">
      <h3>Actions — {entity.name}</h3>

      {enemies.length > 0 && (
        <div class="attack-targets">
          <label>Attack:</label>
          {enemies.map((target) => (
            <button
              key={target.id}
              class="btn btn-attack"
              onClick={() =>
                onAction({
                  type: 'attack',
                  actor: entity.id,
                  target: target.id,
                })
              }
            >
              {target.name} ({target.hp} HP)
            </button>
          ))}
        </div>
      )}

      {enemies.length === 0 && (
        <p class="no-targets">No enemies in melee range.</p>
      )}

      <div class="other-actions">
        <button
          class="btn btn-defend"
          onClick={() =>
            onAction({ type: 'defend', actor: entity.id })
          }
        >
          Defend
        </button>
        <button
          class="btn btn-end"
          onClick={() =>
            onAction({ type: 'end_turn', actor: entity.id })
          }
        >
          End Turn
        </button>
      </div>
    </div>
  );
}
