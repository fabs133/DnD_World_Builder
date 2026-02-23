import { useRef, useEffect } from 'preact/hooks';
import type { GameState } from '../core/types';

const TILE_SIZE = 64;

const TERRAIN_COLORS: Record<string, string> = {
  rubble: '#3a3528',
  pillar: '#555555',
  trap: '#4a2020',
};

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
  const [mapW, mapH] = state.mapSize;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;

    // Background
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Terrain tiles
    for (const tile of state.terrain) {
      const [tx, ty] = tile.position;
      const color = TERRAIN_COLORS[tile.type] ?? '#2a2a2a';
      ctx.fillStyle = color;
      ctx.fillRect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE);

      // Trap indicator
      if (tile.type === 'trap') {
        ctx.fillStyle = '#ff444444';
        ctx.font = `${TILE_SIZE * 0.4}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(
          '!',
          tx * TILE_SIZE + TILE_SIZE / 2,
          ty * TILE_SIZE + TILE_SIZE / 2,
        );
      }

      // Pillar indicator
      if (tile.type === 'pillar') {
        ctx.fillStyle = '#777';
        ctx.beginPath();
        ctx.arc(
          tx * TILE_SIZE + TILE_SIZE / 2,
          ty * TILE_SIZE + TILE_SIZE / 2,
          TILE_SIZE * 0.3,
          0,
          Math.PI * 2,
        );
        ctx.fill();
      }
    }

    // Grid lines
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    for (let x = 0; x <= mapW; x++) {
      ctx.beginPath();
      ctx.moveTo(x * TILE_SIZE, 0);
      ctx.lineTo(x * TILE_SIZE, mapH * TILE_SIZE);
      ctx.stroke();
    }
    for (let y = 0; y <= mapH; y++) {
      ctx.beginPath();
      ctx.moveTo(0, y * TILE_SIZE);
      ctx.lineTo(mapW * TILE_SIZE, y * TILE_SIZE);
      ctx.stroke();
    }

    // Entities
    for (const [id, entity] of state.entities) {
      if (entity.hp <= 0) continue;

      const [x, y] = entity.position;
      const px = x * TILE_SIZE + TILE_SIZE / 2;
      const py = y * TILE_SIZE + TILE_SIZE / 2;

      // Entity circle
      ctx.beginPath();
      ctx.arc(px, py, TILE_SIZE * 0.35, 0, Math.PI * 2);
      ctx.fillStyle = ENTITY_COLORS[entity.type] ?? '#888';
      ctx.fill();

      // Selection ring
      if (id === selectedEntity) {
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 3;
        ctx.stroke();
      }

      // Current turn indicator
      if (state.turnOrder[state.currentTurnIndex] === id) {
        ctx.save();
        ctx.strokeStyle = '#ffd700';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.arc(px, py, TILE_SIZE * 0.42, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
      }

      // Name label
      ctx.fillStyle = '#fff';
      ctx.font = '11px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText(entity.name, px, py + TILE_SIZE * 0.38);

      // HP bar
      const hpPct = entity.hp / entity.maxHp;
      const barW = TILE_SIZE * 0.6;
      const barH = 4;
      const barX = px - barW / 2;
      const barY = py - TILE_SIZE * 0.45;

      ctx.fillStyle = '#333';
      ctx.fillRect(barX, barY, barW, barH);
      ctx.fillStyle =
        hpPct > 0.5 ? '#4ade80' : hpPct > 0.25 ? '#fbbf24' : '#ef4444';
      ctx.fillRect(barX, barY, barW * hpPct, barH);
    }
  }, [state, selectedEntity, mapW, mapH]);

  const handleClick = (e: MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left) / TILE_SIZE);
    const y = Math.floor((e.clientY - rect.top) / TILE_SIZE);

    for (const [id, entity] of state.entities) {
      if (
        entity.position[0] === x &&
        entity.position[1] === y &&
        entity.hp > 0
      ) {
        onSelectEntity(id);
        return;
      }
    }
    onSelectEntity(null);
  };

  return (
    <canvas
      ref={canvasRef}
      width={mapW * TILE_SIZE}
      height={mapH * TILE_SIZE}
      onClick={handleClick}
      class="map-canvas"
    />
  );
}
