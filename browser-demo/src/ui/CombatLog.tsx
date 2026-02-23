import { useRef, useEffect } from 'preact/hooks';
import type { LogEntry } from '../core/types';

interface Props {
  entries: LogEntry[];
}

export function CombatLog({ entries }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [entries.length]);

  return (
    <div class="combat-log" ref={containerRef}>
      <h3>Combat Log</h3>
      {entries.length === 0 && <p class="empty-log">Combat begins...</p>}
      {entries.map((entry, i) => (
        <div key={i} class={`log-entry action-${entry.action}`}>
          <span class="log-round">R{entry.round}</span>
          <span class="log-actor">{entry.actor}</span>
          <span class="log-result">{entry.result}</span>
          {entry.voiceLine && (
            <span class="log-voice">"{entry.voiceLine}"</span>
          )}
        </div>
      ))}
    </div>
  );
}
