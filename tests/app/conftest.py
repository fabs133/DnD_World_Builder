"""Shared fixtures for app-level tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.testing import (
    BehavioralTestHarness,
    ScenarioConfig,
    HarnessConfig,
    HarnessResult,
)

SCENARIOS_DIR = Path(__file__).resolve().parents[2] / "scenarios"


@pytest.fixture
def goblin_ambush_yaml() -> Path:
    """Path to the goblin ambush scenario YAML."""
    return SCENARIOS_DIR / "goblin_ambush.yaml"


@pytest.fixture
def goblin_ambush_config(goblin_ambush_yaml: Path) -> ScenarioConfig:
    """Load the goblin ambush scenario config."""
    return ScenarioConfig.from_yaml(str(goblin_ambush_yaml))


@pytest.fixture
def quick_harness_config() -> HarnessConfig:
    """Config for fast smoke tests: few runs, no parallelism."""
    return HarnessConfig(
        runs=5,
        seed_start=1,
        parallel_workers=1,
        use_real_ai=False,
        timeout_per_run=30,
    )


@pytest.fixture
def medium_harness_config() -> HarnessConfig:
    """Config for medium tests: moderate runs."""
    return HarnessConfig(
        runs=10,
        seed_start=1,
        parallel_workers=2,
        use_real_ai=False,
        timeout_per_run=30,
    )


def run_scenario(
    config: ScenarioConfig,
    harness_config: HarnessConfig | None = None,
) -> HarnessResult:
    """Helper to run a scenario with the behavioral harness."""
    if harness_config is None:
        harness_config = HarnessConfig(runs=5, seed_start=1, parallel_workers=1)
    harness = BehavioralTestHarness(config, harness_config)
    return harness.run()
