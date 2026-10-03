# D&D World Builder Roadmap

Last updated: 2026-10-03. This is the single source of truth for project status and
planning. Older planning documents are kept in [`docs/archive/`](docs/archive/) for history.

## Current status

| Area | Status | Notes |
|------|--------|-------|
| Desktop app (PyQt5) | Released | v1.0.0 (tags `v1.0.0-rc1`, `v1.0.0`) |
| Map editor, triggers, character creator | Done | Square and hex grids, visual trigger editor |
| Known UI bugs (v1 list) | Fixed | All six verified fixed in code |
| Multiplayer, phases 1-5 | Done | Protocol, sync, host-validated actions, UI, tests and README guide |
| Headless engine (`core/engine/`) | Wired into GUI and host | `Encounter` drives the GUI, the multiplayer host and the bridges |
| Initiative panel | Done | Populated from the Encounter menu; joined players see turn changes |
| Browser demo (`browser-demo/`) | Builds | Vite + Preact, not yet deployed |
| CI | Tests, coverage, mypy (advisory), ruff gate | Ruff checks syntax, undefined names, unused imports |

## What is done

### v1.0.0 release
- Packaged desktop release (PyInstaller spec bundles the SQLite DB, rulebook JSON and config).
- The six UI bugs from the old work-item list are fixed: hex grid, right-click hint and Help
  menu, checkbox styling, trigger node stacking, duplicate Save button, stat block dark mode.

### Multiplayer
- Phases 1-3: WebSocket protocol, event bridge and state sync, player action requests. The host
  validates `ACTION_REQUEST` in `network/session_host.py`.
- Phase 4: host and join dialogs, `SessionPanel` dock and Session menu in `ui/main_window.py`,
  connection state in the status bar.
- Phase 5: network tests (`tests/integration/`)
  and a Multiplayer Quick Start in the README. Cross-machine manual testing and a
  firewall/port-forwarding guide were not verified in this review.

### Headless engine (`core/engine/`)
- `GameSession`, `InitiativeTracker`, `ActionExecutor`, A* pathfinder.
- Heuristic AI and Ollama-backed AI with alignment personalities, plus a CLI runner.

### Repository hygiene (October 2026)
- Removed committed virtualenvs, generated docs output and stray files; applied ruff safe
  autofixes; fixed undefined names; added a ruff gate to CI.

## What is next

### Stage 3: unify the GUI and the headless engine (mostly done)
Done:
- `Encounter` (`core/engine/encounter.py`) is the single turn-order source for the GUI, the
  multiplayer host and the bridges.
- `ActionExecutor` now enforces `action.validate()`.
- GUI Encounter menu (Start, Next Turn, End) drives the initiative panel; one gamemaster is
  shared by the local panel and a hosted session.
- Joined clients receive `TURN_CHANGE` broadcasts and show the current turn and round.
- Entity tokens are drawn on the map (colored by player/enemy/npc/other, greyed when dead).
- AI-controlled enemy turns in the GUI: unclaimed enemies play automatically with the
  `HeuristicAIAdapter` (toggle: Encounter > Auto-play Enemy Turns). The Ollama/LLM adapter is not
  used in the GUI yet; only the heuristic AI is.
- The legacy `models/flow/turn_system.py` and `models/flow/combat_system.py` are removed.

Remaining follow-ups:
- Optional: use the Ollama/LLM adapter for enemy turns in the GUI (heuristic only for now).
- Then move on to the Stage 4 features below.

### Stage 4 (after Stage 3)
1. Fog of war: the `BLOCKS_VISION` tile tag and the pathfinder already exist; add visibility
   computation and rendering.
2. Player-only view in multiplayer: hosts send each player only what their characters can see.
3. Dice roller in chat.
4. Browser demo deployment: publish `browser-demo/` to GitHub Pages and/or itch.io. The
   archived itch.io plan describes packaging and a staged desktop-then-browser release.

### Backlog (from the README)
Drag-and-drop entity placement, map layers, distance measurement tool.

## Archived docs

Moved to [`docs/archive/`](docs/archive/) because they are outdated or superseded by this file:

- `NEXT_WORK_ITEMS.md`, `PROJECT_ASSESSMENT.md`, `V1_RELEASE_PLAN.md` (formerly in the repo root)
- `STATE.md`, `PROJECT_MASTER_PLAN.md`
- `MULTIPLAYER_PLAN.md`, `MVP_MULTIPLAYER.md`
- `ITCH_BROWSER_RELEASE_PLAN.md` (the more complete of two near-duplicate plans; the shorter
  `ITCHIO_BROWSER_RELEASE_PLAN.md` was removed)
- `AI_PERSONALITY_UNIFICATION.md`, `BEHAVIORAL_TEST_SYSTEM_PLAN.md`

User documentation stays in [`docs/user/`](docs/user/). The Sphinx site is built from `source/`
in CI and is not committed.
