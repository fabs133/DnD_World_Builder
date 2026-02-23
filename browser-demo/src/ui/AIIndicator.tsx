interface Props {
  mode: 'deterministic' | 'webllm';
  loading: boolean;
  progress: number;
  onEnableWebLLM: () => void;
}

export function AIIndicator({
  mode,
  loading,
  progress,
  onEnableWebLLM,
}: Props) {
  return (
    <div class="ai-indicator">
      {mode === 'deterministic' && !loading && (
        <>
          <span class="ai-badge smart-bot">Smart Bot</span>
          <button onClick={onEnableWebLLM} class="btn btn-small">
            Try Full AI
          </button>
        </>
      )}

      {loading && (
        <>
          <span class="ai-badge loading">Loading AI...</span>
          <progress value={progress} max={1} />
          <span class="progress-text">{Math.round(progress * 100)}%</span>
        </>
      )}

      {mode === 'webllm' && !loading && (
        <span class="ai-badge full-ai">Full AI</span>
      )}
    </div>
  );
}
