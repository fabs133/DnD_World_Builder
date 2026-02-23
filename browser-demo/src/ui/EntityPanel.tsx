import type { Entity } from '../core/types';
import { ALIGNMENT_INFO } from '../core/alignment';

interface Props {
  entity: Entity | null | undefined;
}

export function EntityPanel({ entity }: Props) {
  if (!entity) {
    return (
      <div class="entity-panel empty">
        <p>Click an entity on the map to view details.</p>
      </div>
    );
  }

  const info = ALIGNMENT_INFO[entity.alignment];
  const hpPct = Math.round((entity.hp / entity.maxHp) * 100);

  return (
    <div class="entity-panel">
      <h3>
        <span class={`entity-dot ${entity.type}`} />
        {entity.name}
      </h3>
      <div class="stat-grid">
        <div class="stat">
          <label>HP</label>
          <span>
            {entity.hp}/{entity.maxHp} ({hpPct}%)
          </span>
        </div>
        <div class="stat">
          <label>AC</label>
          <span>{entity.ac}</span>
        </div>
        <div class="stat">
          <label>DEX</label>
          <span>{entity.dex}</span>
        </div>
      </div>
      <div class="alignment-badge">
        <strong>{info.name}</strong> — {info.archetype}
      </div>
      <p class="tagline">"{info.tagline}"</p>
    </div>
  );
}
