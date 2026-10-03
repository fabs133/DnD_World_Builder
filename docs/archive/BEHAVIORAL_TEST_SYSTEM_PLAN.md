# Behavioral Test System — Implementation Plan

> **Goal:** Automated headless testing that validates AI behavior statistically across hundreds of runs, proving that alignment-based personalities work as intended.

---

## Executive Summary

| What | Why |
|------|-----|
| **Problem** | Can't manually test 9 alignments × N scenarios × M iterations |
| **Solution** | Headless test harness with mock AI for CI + real LLM for stress tests |
| **Key Insight** | Test *behavior statistically*, not just "did it run without errors" |
| **Hardware** | 8GB VRAM + 32GB RAM = can run dual LLMs for stress testing |

---

## Hardware Assessment

Based on your system specs:

| Resource | Total | Available | Notes |
|----------|-------|-----------|-------|
| VRAM | 8 GB | ~5.9 GB | After current 2.1GB usage |
| Shared GPU Memory | 16 GB | ~16 GB | Spillover if needed |
| System RAM | 32 GB | ~24 GB | Assuming 8GB for OS/apps |
| GPU Temp | 49°C | Plenty of headroom | Can run sustained load |

### Dual-LLM Configurations

| Configuration | Model A | Model B | Total VRAM | Viable? |
|--------------|---------|---------|------------|---------|
| Dual small | Phi-3 Mini (2.5GB) | Phi-3 Mini (2.5GB) | ~5GB | ✅ Yes |
| Small + medium | Gemma 2B (1.5GB) | Mistral 7B (4.5GB) | ~6GB | ✅ Yes |
| Dual medium | Qwen 2.5:3B (2GB) | Qwen 2.5:3B (2GB) | ~4GB | ✅ Yes |
| GPU + CPU | Phi-3 on GPU | Llama 3.2:3B on CPU | 2.5GB + RAM | ✅ Yes |

**Recommendation:** Two Phi-3 Mini instances OR one Phi-3 (GPU) + one Llama 3.2:3B (CPU)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BEHAVIORAL TEST SYSTEM                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│  │   FAST CI   │    │   FULL CI   │    │STRESS TEST  │                 │
│  │  (MockAI)   │    │ (MockAI)    │    │(2x Ollama)  │                 │
│  │   <1 min    │    │   ~2 min    │    │   ~1 hour   │                 │
│  │   10 runs   │    │  100 runs   │    │   50 runs   │                 │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                 │
│         │                  │                  │                         │
│         └──────────────────┼──────────────────┘                         │
│                            ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    BEHAVIORAL TEST HARNESS                       │   │
│  │  - Scenario loader (YAML)                                        │   │
│  │  - Parallel runner (mock) / Sequential (real LLM)                │   │
│  │  - Event tracking per entity per round                           │   │
│  └─────────────────────────────┬───────────────────────────────────┘   │
│                                ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    METRICS & ASSERTIONS                          │   │
│  │  - BehaviorStats per entity (aggregated across runs)             │   │
│  │  - Statistical assertions ("CE mercy < 20%")                     │   │
│  │  - Regression detection (compare to baseline)                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Test Modes

| Mode | AI Type | Runs | Speed | Use Case |
|------|---------|------|-------|----------|
| **Fast CI** | MockAI | 10 | <1 min | PR checks, quick validation |
| **Full CI** | MockAI | 100 | ~2 min | Merge to main, thorough check |
| **Stress Test** | Real LLM (1x) | 50 | ~30 min | Validate LLM integration |
| **Dual Stress** | Real LLM (2x) | 50 | ~1 hour | Full AI vs AI validation |
| **Nightly** | MockAI | 1000 | ~10 min | Edge case discovery |

---

## Directory Structure

```
core/testing/
├── __init__.py
├── behavioral/
│   ├── __init__.py
│   ├── stats.py              # BehaviorEvent, EntityRunStats, BehaviorStats
│   ├── mock_ai.py            # MockAIAdapter (deterministic, fast)
│   ├── harness.py            # BehavioralTestHarness, ScenarioConfig, HarnessConfig
│   ├── assertions.py         # BehaviorAssertion, AlignmentAssertions
│   ├── llm_pool.py           # OllamaPool, DualLLMAdapterFactory
│   ├── stress_runner.py      # CLI for stress tests
│   └── reporter.py           # Report generation (future)
└── scenarios/
    ├── __init__.py
    ├── goblin_ambush.yaml
    ├── party_defense.yaml
    └── alignment_matrix.yaml

tests/behavioral/
├── conftest.py               # Fixtures (quick_harness, thorough_harness)
├── test_alignments.py        # Per-alignment behavioral tests
├── test_combat_flow.py       # Combat mechanics validation
└── test_regression.py        # Compare to baseline metrics
```

---

## Component Specifications

### 1. BehaviorEvent Enum (`stats.py`)

Trackable events during combat:

```python
class BehaviorEvent(Enum):
    # Combat
    ATTACKED = auto()
    DEALT_DAMAGE = auto()
    TOOK_DAMAGE = auto()
    KILLED_ENEMY = auto()
    DIED = auto()
    
    # Target selection
    TARGETED_WEAKEST = auto()
    TARGETED_STRONGEST = auto()
    TARGETED_NEAREST = auto()
    TARGETED_GRUDGE = auto()
    TARGETED_RANDOM = auto()
    
    # Ally interaction
    ALLY_THREATENED = auto()          # Opportunity arose
    PROTECTED_ALLY = auto()           # Moved to shield
    HEALED_ALLY = auto()
    IGNORED_DYING_ALLY = auto()
    SACRIFICED_FOR_ALLY = auto()      # Took hit meant for ally
    BETRAYED_ALLY = auto()            # Attacked or abandoned
    
    # Self-preservation
    CONSIDERED_FLEEING = auto()       # HP below threshold
    FLED_COMBAT = auto()
    STAYED_DESPITE_DANGER = auto()
    
    # Mercy
    COULD_EXECUTE_DOWNED = auto()     # Opportunity arose
    EXECUTED_DOWNED = auto()
    SPARED_DOWNED = auto()
    
    # Honor
    ATTACKED_FLEEING = auto()
    ACCEPTED_SURRENDER = auto()
    USED_DIRTY_TRICK = auto()
    FOUGHT_HONORABLY = auto()
    
    # Coordination
    FOCUS_FIRED = auto()              # Same target as ally
    BROKE_FORMATION = auto()
    FOLLOWED_ORDERS = auto()
    
    # Chaos/Unpredictability
    CHANGED_TARGET_MID_COMBAT = auto()
    DID_SOMETHING_SUBOPTIMAL = auto()
    CACKLED = auto()                  # Voice line triggered
```

### 2. EntityRunStats (`stats.py`)

Stats for a single entity in a single run:

```python
@dataclass
class EntityRunStats:
    entity_name: str
    alignment: str
    run_id: int
    seed: int
    
    events: list[tuple[int, BehaviorEvent, dict]]  # (round, event, metadata)
    
    damage_dealt: int = 0
    damage_taken: int = 0
    healing_done: int = 0
    kills: int = 0
    died: bool = False
    rounds_survived: int = 0
    final_hp_percent: float = 0.0
    
    def record(self, round_num: int, event: BehaviorEvent, **metadata) -> None
    def count(self, event: BehaviorEvent) -> int
    def has(self, event: BehaviorEvent) -> bool
```

### 3. BehaviorStats (`stats.py`)

Aggregated stats for one entity across N runs:

```python
@dataclass
class BehaviorStats:
    entity_name: str
    alignment: str
    runs: list[EntityRunStats]
    
    # Properties (computed)
    run_count: int
    survival_rate: float
    avg_damage_dealt: float
    avg_kills: float
    flee_rate: float           # FLED / CONSIDERED_FLEEING
    mercy_rate: float          # SPARED / COULD_EXECUTE
    protect_rate: float        # PROTECTED / ALLY_THREATENED
    betrayal_rate: float       # BETRAYED / ALLY_THREATENED
    target_entropy: float      # Measure of target randomness (0-1)
    
    # Methods
    def total(self, event: BehaviorEvent) -> int
    def rate(self, event: BehaviorEvent, opportunity: BehaviorEvent) -> float
    def to_dict(self) -> dict
```

### 4. MockAIAdapter (`mock_ai.py`)

Deterministic AI that follows alignment weights directly:

```python
class MockAIAdapter(InputAdapter):
    """No LLM calls. Uses tactical weights + RNG for decisions.
    Fast enough for 1000s of runs in CI."""
    
    def __init__(
        self,
        entities_by_name: dict[str, Any],
        rng: random.Random | None = None,
        stats_collector: dict[str, EntityRunStats] | None = None,
        round_number_fn: callable = lambda: 1,
    )
    
    def choose_action(self, entity_name, game_state, available_actions) -> Action
    
    # Decision tree:
    # 1. Check flee (HP < flee_threshold × random)
    # 2. Check protect ally (ally_protection × random)
    # 3. Check execute downed (mercy × random)
    # 4. Standard attack with target selection
```

### 5. ScenarioConfig (`harness.py`)

```python
@dataclass
class ScenarioConfig:
    name: str
    description: str = ""
    
    entities: list[dict]  # {"name", "type", "hp", "alignment", "trait", ...}
    map_size: tuple[int, int] = (10, 10)
    terrain: dict[tuple[int, int], str] = field(default_factory=dict)
    max_rounds: int = 20
    
    @classmethod
    def from_yaml(cls, path: str) -> ScenarioConfig
```

Example YAML:
```yaml
name: goblin_ambush
description: "2 adventurers vs 4 goblins in a ruined temple"

entities:
  - name: Fighter
    type: player
    hp: 28
    alignment: lawful_good
    position: [2, 5]
    trait: "Protects the weak"
    
  - name: Wizard
    type: player
    hp: 14
    alignment: chaotic_good
    position: [3, 5]
    
  - name: Goblin_1
    type: enemy
    hp: 7
    alignment: neutral_evil
    position: [7, 3]
    
  - name: Goblin_2
    type: enemy
    hp: 7
    alignment: neutral_evil
    position: [7, 7]
    
  - name: Goblin_3
    type: enemy
    hp: 7
    alignment: chaotic_evil
    position: [8, 5]
    trait: "Cackles maniacally"
    
  - name: Shaman
    type: enemy
    hp: 12
    alignment: lawful_evil
    position: [9, 5]
    trait: "Commands the others"

map_size: [10, 10]
max_rounds: 15
```

### 6. HarnessConfig (`harness.py`)

```python
@dataclass
class HarnessConfig:
    runs: int = 100
    seed_start: int = 1
    parallel_workers: int = 4        # For mock AI
    use_real_ai: bool = False
    ollama_models: list[str] = field(default_factory=lambda: ["phi3"])
    timeout_per_run: int = 60
```

### 7. BehavioralTestHarness (`harness.py`)

```python
class BehavioralTestHarness:
    def __init__(
        self,
        scenario: ScenarioConfig,
        config: HarnessConfig | None = None,
        adapter_factory: Callable | None = None,
    )
    
    def run(self) -> HarnessResult
    
    # Internal:
    def _run_parallel(self) -> tuple[int, int]      # Mock AI
    def _run_sequential(self) -> tuple[int, int]    # Real AI
    def _run_single(self, seed: int, run_id: int) -> None
    def _create_entity(self, cfg: dict, rng) -> GameEntity
    def _create_default_adapters(self, ...) -> dict[str, InputAdapter]
```

### 8. HarnessResult (`harness.py`)

```python
@dataclass
class HarnessResult:
    scenario_name: str
    config: HarnessConfig
    stats_by_entity: dict[str, BehaviorStats]
    total_runs: int
    successful_runs: int
    failed_runs: int
    total_time_seconds: float
    runs_per_second: float
    
    def get_alignment_stats(self, alignment: str) -> list[BehaviorStats]
```

### 9. BehaviorAssertion (`assertions.py`)

```python
class BehaviorAssertion:
    def __init__(
        self,
        name: str,
        check: Callable[[BehaviorStats], bool],
        message: Callable[[BehaviorStats], str],
    )
    
    def __call__(self, stats: BehaviorStats) -> tuple[bool, str]
```

### 10. AlignmentAssertions (`assertions.py`)

Pre-built assertions for each alignment:

```python
class AlignmentAssertions:
    @staticmethod
    def chaotic_evil() -> list[BehaviorAssertion]:
        return [
            BehaviorAssertion("ce_low_mercy", lambda s: s.mercy_rate < 0.2, ...),
            BehaviorAssertion("ce_unpredictable", lambda s: s.target_entropy > 0.4, ...),
            BehaviorAssertion("ce_ignores_allies", lambda s: s.protect_rate < 0.3, ...),
        ]
    
    @staticmethod
    def lawful_good() -> list[BehaviorAssertion]:
        return [
            BehaviorAssertion("lg_protects_allies", lambda s: s.protect_rate > 0.6, ...),
            BehaviorAssertion("lg_shows_mercy", lambda s: s.mercy_rate > 0.7, ...),
            BehaviorAssertion("lg_no_betrayal", lambda s: s.betrayal_rate < 0.05, ...),
        ]
    
    @staticmethod
    def neutral_evil() -> list[BehaviorAssertion]:
        return [
            BehaviorAssertion("ne_flees_when_hurt", lambda s: s.flee_rate > 0.4, ...),
            BehaviorAssertion("ne_targets_weak", lambda s: ..., ...),
            BehaviorAssertion("ne_self_interested", lambda s: s.protect_rate < 0.3, ...),
        ]
    
    @staticmethod
    def for_alignment(alignment: str) -> list[BehaviorAssertion]
```

### 11. OllamaPool (`llm_pool.py`)

```python
class OllamaPool:
    """Manages multiple Ollama instances for stress testing."""
    
    DEFAULT_PORT = 11434
    SECONDARY_PORT = 11435
    
    def start_single(self, model: str = "phi3") -> ModelInstance
    def start_dual_gpu(self, model_a: str, model_b: str) -> tuple[ModelInstance, ModelInstance]
    def start_gpu_plus_cpu(self, gpu_model: str, cpu_model: str) -> tuple[ModelInstance, ModelInstance]
    def shutdown(self) -> None
```

### 12. DualLLMAdapterFactory (`llm_pool.py`)

```python
class DualLLMAdapterFactory:
    """Assigns different models to different factions."""
    
    def __init__(self, model_a: ModelInstance, model_b: ModelInstance)
    
    def __call__(self, entities_by_name, rng, run_stats) -> dict[str, AIAdapter]:
        # Player faction → Model A
        # Enemy faction → Model B
```

---

## Behavioral Thresholds by Alignment

| Alignment | Flee Rate | Mercy Rate | Protect Rate | Betrayal | Target Entropy |
|-----------|-----------|------------|--------------|----------|----------------|
| Lawful Good | <20% | >70% | >60% | <5% | Low |
| Neutral Good | <30% | >60% | >50% | <10% | Low |
| Chaotic Good | <20% | >50% | >40% | <10% | Medium |
| Lawful Neutral | <30% | 40-60% | 30-50% | <15% | Low |
| True Neutral | 30-50% | 40-60% | 30-50% | <20% | Medium |
| Chaotic Neutral | 30-50% | 30-50% | 20-40% | <30% | High |
| Lawful Evil | <20% | <30% | <30% | <20% | Low |
| Neutral Evil | >40% | <20% | <30% | 20-40% | Medium |
| Chaotic Evil | <30% | <20% | <30% | >20% | High |

---

## Pytest Integration

### Fixtures (`tests/behavioral/conftest.py`)

```python
@pytest.fixture
def quick_harness():
    """Fast harness for CI (10 runs, mock AI)."""
    def _create(scenario: ScenarioConfig):
        config = HarnessConfig(runs=10, parallel_workers=4)
        return BehavioralTestHarness(scenario, config)
    return _create

@pytest.fixture
def thorough_harness():
    """Thorough harness (100 runs, mock AI)."""
    def _create(scenario: ScenarioConfig):
        config = HarnessConfig(runs=100, parallel_workers=4)
        return BehavioralTestHarness(scenario, config)
    return _create

@pytest.fixture
def goblin_ambush_scenario():
    return ScenarioConfig(
        name="goblin_ambush",
        entities=[
            {"name": "Fighter", "type": "player", "hp": 28, "alignment": "lawful_good"},
            {"name": "Wizard", "type": "player", "hp": 14, "alignment": "chaotic_good"},
            {"name": "Goblin_1", "type": "enemy", "hp": 7, "alignment": "neutral_evil"},
            {"name": "Goblin_2", "type": "enemy", "hp": 7, "alignment": "neutral_evil"},
            {"name": "Goblin_3", "type": "enemy", "hp": 7, "alignment": "chaotic_evil"},
            {"name": "Shaman", "type": "enemy", "hp": 12, "alignment": "lawful_evil"},
        ],
        max_rounds=15,
    )
```

### Example Test (`tests/behavioral/test_alignments.py`)

```python
class TestChaoticEvil:
    """Chaotic Evil should be unpredictable and merciless."""
    
    def test_behavioral_profile(self, quick_harness, goblin_ambush_scenario):
        harness = quick_harness(goblin_ambush_scenario)
        result = harness.run()
        
        ce_stats = result.get_alignment_stats("chaotic_evil")
        for stats in ce_stats:
            for assertion in AlignmentAssertions.chaotic_evil():
                passed, msg = assertion(stats)
                assert passed, f"{stats.entity_name}: {msg}"


class TestLawfulGood:
    """Lawful Good should protect allies and show mercy."""
    
    def test_behavioral_profile(self, quick_harness, goblin_ambush_scenario):
        harness = quick_harness(goblin_ambush_scenario)
        result = harness.run()
        
        lg_stats = result.get_alignment_stats("lawful_good")
        for stats in lg_stats:
            for assertion in AlignmentAssertions.lawful_good():
                passed, msg = assertion(stats)
                assert passed, f"{stats.entity_name}: {msg}"
```

---

## CI Configuration

### GitHub Actions (`.github/workflows/behavioral_tests.yml`)

```yaml
name: Behavioral Tests

on:
  push:
    paths:
      - 'models/ai/**'
      - 'core/engine/ai/**'
      - 'core/testing/**'
  pull_request:
    paths:
      - 'models/ai/**'
      - 'core/engine/ai/**'
      - 'core/testing/**'

jobs:
  fast:
    name: Fast Behavioral Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e ".[test]"
      - name: Run fast behavioral tests
        run: pytest tests/behavioral/ -m "not slow" -v --tb=short
  
  thorough:
    name: Thorough Behavioral Tests
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e ".[test]"
      - name: Run thorough behavioral tests
        run: pytest tests/behavioral/ -v --tb=short
```

---

## Stress Test CLI Usage

```bash
# Single model stress test
python -m core.testing.behavioral.stress_runner \
    core/testing/scenarios/goblin_ambush.yaml \
    --runs 50 \
    --mode single \
    --model-a phi3 \
    --output stress_report_single.json

# Dual GPU stress test (two small models)
python -m core.testing.behavioral.stress_runner \
    core/testing/scenarios/goblin_ambush.yaml \
    --runs 50 \
    --mode dual_gpu \
    --model-a phi3 \
    --model-b phi3 \
    --output stress_report_dual.json

# GPU + CPU stress test (one on GPU, one on RAM)
python -m core.testing.behavioral.stress_runner \
    core/testing/scenarios/goblin_ambush.yaml \
    --runs 50 \
    --mode gpu_cpu \
    --model-a phi3 \
    --model-b llama3.2:3b \
    --output stress_report_hybrid.json
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (2 days)

| Task | File | Effort |
|------|------|--------|
| BehaviorEvent enum | `stats.py` | 0.25 day |
| EntityRunStats dataclass | `stats.py` | 0.25 day |
| BehaviorStats dataclass | `stats.py` | 0.5 day |
| MockAIAdapter | `mock_ai.py` | 1 day |

**Checkpoint:** Can run 100 mock battles and collect stats.

### Phase 2: Test Harness (1.5 days)

| Task | File | Effort |
|------|------|--------|
| ScenarioConfig + YAML loading | `harness.py` | 0.25 day |
| HarnessConfig | `harness.py` | 0.25 day |
| BehavioralTestHarness | `harness.py` | 0.75 day |
| HarnessResult | `harness.py` | 0.25 day |

**Checkpoint:** Can run `harness.run()` and get aggregated results.

### Phase 3: Assertions (0.5 day)

| Task | File | Effort |
|------|------|--------|
| BehaviorAssertion class | `assertions.py` | 0.25 day |
| AlignmentAssertions (all 9) | `assertions.py` | 0.25 day |

**Checkpoint:** Can assert "CE mercy < 20%" and get pass/fail.

### Phase 4: Dual-LLM Support (1 day)

| Task | File | Effort |
|------|------|--------|
| ModelInstance dataclass | `llm_pool.py` | 0.1 day |
| OllamaPool (single, dual_gpu, gpu_cpu) | `llm_pool.py` | 0.5 day |
| DualLLMAdapterFactory | `llm_pool.py` | 0.2 day |
| Stress runner CLI | `stress_runner.py` | 0.2 day |

**Checkpoint:** Can run `python -m core.testing.behavioral.stress_runner --mode dual_gpu`.

### Phase 5: Pytest Integration (0.5 day)

| Task | File | Effort |
|------|------|--------|
| Fixtures | `conftest.py` | 0.25 day |
| First test classes | `test_alignments.py` | 0.25 day |

**Checkpoint:** `pytest tests/behavioral/` passes.

### Phase 6: Scenarios & Polish (0.5 day)

| Task | File | Effort |
|------|------|--------|
| goblin_ambush.yaml | `scenarios/` | 0.1 day |
| party_defense.yaml | `scenarios/` | 0.1 day |
| alignment_matrix.yaml (all 9) | `scenarios/` | 0.2 day |
| CI workflow | `.github/workflows/` | 0.1 day |

**Checkpoint:** CI runs behavioral tests on every PR to AI code.

---

## Total Effort

| Phase | Days |
|-------|------|
| Phase 1: Core Infrastructure | 2.0 |
| Phase 2: Test Harness | 1.5 |
| Phase 3: Assertions | 0.5 |
| Phase 4: Dual-LLM Support | 1.0 |
| Phase 5: Pytest Integration | 0.5 |
| Phase 6: Scenarios & Polish | 0.5 |
| **Total** | **~6 days** |

---

## Success Criteria

After implementation, you should be able to:

1. **Run fast CI in <1 minute** with 10 runs per scenario
2. **Run thorough CI in ~2 minutes** with 100 runs per scenario
3. **See behavioral metrics** like:
   ```
   Goblin_3 (chaotic_evil):
     Survival: 45%
     Avg damage: 8.2
     Flee rate: 12%
     Mercy rate: 8%
     Protect rate: 5%
     Target entropy: 0.72
   ```
4. **Catch regressions** like "flee rate dropped from 60% to 20%"
5. **Run stress tests with real LLMs** on your local machine
6. **Prove statistically** that alignment affects behavior

---

## Open Questions

1. **Should MockAI match LLM behavior exactly?** 
   - No — MockAI validates the weights work; stress tests validate LLMs follow prompts.

2. **How to handle non-determinism in real LLM tests?**
   - Use wider thresholds (e.g., "mercy 10-30%" instead of "<20%").
   - Run more iterations.
   - Track variance, not just mean.

3. **Should we save run replays for debugging?**
   - Future enhancement: serialize action log for failed runs.

4. **How to visualize results?**
   - Future enhancement: HTML report with charts.

---

## Next Steps

1. Claude Code runs existing tests to verify current state
2. Implement Phase 1 (stats.py, mock_ai.py)
3. Implement Phase 2 (harness.py)
4. First end-to-end test
5. Iterate
