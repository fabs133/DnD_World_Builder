import { useState, useCallback } from 'preact/hooks';
import type { Action } from '../core/types';
import { GameSession } from '../core/game-session';
import { GOBLIN_AMBUSH } from '../scenarios/goblin-ambush';
import { DeterministicAI } from '../ai/deterministic-ai';
import { MapCanvas } from './MapCanvas';
import { EntityPanel } from './EntityPanel';
import { CombatLog } from './CombatLog';
import { ActionButtons } from './ActionButtons';
import { AIIndicator } from './AIIndicator';

type AIMode = 'deterministic' | 'webllm';

function createGame() {
  return new GameSession(GOBLIN_AMBUSH);
}

export function App() {
  const [game, setGame] = useState(createGame);
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [aiMode] = useState<AIMode>('deterministic');
  const [aiProcessing, setAiProcessing] = useState(false);
  const [webllmLoading] = useState(false);
  const [webllmProgress] = useState(0);

  const [ai] = useState(() => new DeterministicAI());

  const forceUpdate = useCallback(() => {
    // Trigger re-render by creating a new wrapper referencing the same session
    setGame((g) => Object.assign(Object.create(Object.getPrototypeOf(g)), g));
  }, []);

  const processAITurns = useCallback(
    async (session: GameSession) => {
      setAiProcessing(true);

      while (
        !session.isPlayerTurn() &&
        session.state.phase === 'combat'
      ) {
        const entity = session.getCurrentEntity();
        if (!entity) break;

        const action = ai.chooseAction(entity, session.state);
        const voiceLine = ai.getVoiceLine(entity);
        session.executeAction(action, voiceLine);
        forceUpdate();

        // Small delay for readability
        await new Promise((r) => setTimeout(r, 400));
      }

      setAiProcessing(false);
    },
    [ai, forceUpdate],
  );

  const handlePlayerAction = useCallback(
    async (action: Action) => {
      if (aiProcessing) return;
      game.executeAction(action);
      forceUpdate();
      await processAITurns(game);
    },
    [game, aiProcessing, forceUpdate, processAITurns],
  );

  const handleRestart = useCallback(() => {
    const newGame = createGame();
    setGame(newGame);
    setSelectedEntity(null);
    setAiProcessing(false);
  }, []);

  const handleEnableWebLLM = useCallback(() => {
    alert(
      'WebLLM requires a browser with WebGPU support and downloads a ~2GB model. ' +
        'This feature is experimental — using Smart Bot mode for now.',
    );
  }, []);

  const currentEntity = game.getCurrentEntity();

  return (
    <div class="app">
      <header>
        <h1>D&D World Builder — Demo</h1>
        <AIIndicator
          mode={aiMode}
          loading={webllmLoading}
          progress={webllmProgress}
          onEnableWebLLM={handleEnableWebLLM}
        />
      </header>

      <main>
        <div class="map-area">
          <MapCanvas
            state={game.state}
            selectedEntity={selectedEntity}
            onSelectEntity={setSelectedEntity}
          />
          <div class="round-indicator">
            Round {game.state.round}
            {currentEntity && game.state.phase === 'combat' && (
              <> — {currentEntity.name}'s turn</>
            )}
          </div>
        </div>

        <aside class="sidebar">
          <EntityPanel
            entity={
              selectedEntity
                ? game.state.entities.get(selectedEntity)
                : currentEntity
            }
          />

          {game.isPlayerTurn() &&
            game.state.phase === 'combat' &&
            !aiProcessing &&
            currentEntity && (
              <ActionButtons
                entity={currentEntity}
                state={game.state}
                onAction={handlePlayerAction}
              />
            )}

          {aiProcessing && game.state.phase === 'combat' && (
            <div class="ai-thinking">
              <p>AI is thinking...</p>
            </div>
          )}

          {game.state.phase !== 'combat' && (
            <div class="game-over">
              <h2>
                {game.state.phase === 'victory'
                  ? 'Victory!'
                  : 'Defeat'}
              </h2>
              <p>
                {game.state.phase === 'victory'
                  ? 'The adventurers have prevailed!'
                  : 'The adventurers have fallen...'}
              </p>
              <button class="btn btn-restart" onClick={handleRestart}>
                Play Again
              </button>
            </div>
          )}
        </aside>
      </main>

      <CombatLog entries={game.state.log} />

      <footer>
        <p>
          This is a demo.{' '}
          <a
            href="https://github.com/fabs133/DnD_World_Builder/releases"
            target="_blank"
            rel="noopener"
          >
            Download the full version
          </a>{' '}
          for scenario editing, more features, and richer AI.
        </p>
      </footer>
    </div>
  );
}
