# Multiplayer Implementation Plan — Phase 2 & Launcher

**Created:** 2026-02-22  
**Status:** In Progress  
**Depends on:** Phase 1 (Protocol, Transport, Core) ✅ Complete

---

## Phase 2: State Sync

### 2.1 Event Bridge (`network/event_bridge.py`) ✅ Done
- `EventBridge` class subscribing to 16 game events
- Throttled delta broadcasting (100ms batching)
- `TurnBridge` for turn-specific updates

### 2.2 Remaining Tasks

| Task | File | Description | Est. |
|------|------|-------------|------|
| Wire bridge to host | `session_host.py` | Create `EventBridge` + `TurnBridge` in `SessionHost.__init__`, start/stop with session | 30m |
| Add turn order to FULL_STATE | `session_host.py` | Include initiative order in initial sync | 15m |
| Handle TURN_CHANGE client-side | `session_client.py` | Update `turn_state`, emit callback | 15m |
| Tests | `test_event_bridge.py` | Mock EventBus, verify delta computation, throttling | 45m |
| Integration test | `test_state_sync.py` | 2 clients, DM moves entity, verify convergence | 30m |

### 2.3 Acceptance Criteria
- [ ] New player connects → receives complete world state
- [ ] DM moves entity → all players see movement within 200ms
- [ ] DM modifies tile → delta broadcast, clients update
- [ ] Test: 3 clients, 10 sequential changes, all states converge

---

## Phase 3: Launcher

### 3.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     DnD World Builder                           │
│  (Authoring Tool - DM only)                                     │
│  - Map editor, entity placement, trigger setup                  │
│  - Exports: .scenario files (JSON/ZIP with all assets)          │
│  - "Export for Play" button                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ .scenario file
┌─────────────────────────────────────────────────────────────────┐
│                     DnD Session Launcher                        │
│  (Runtime - DM + Players)                                       │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ Import       │  │ Character    │  │ Session              │   │
│  │ .scenario    │  │ Manager      │  │ Browser              │   │
│  │ .character   │  │ (create/load)│  │ (host/join)          │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Session View                            │  │
│  │  - Map renderer (read-only for players)                   │  │
│  │  - Entity panel (claimed characters)                      │  │
│  │  - Action bar (move, attack, ability, end turn)           │  │
│  │  - Chat / dice log                                        │  │
│  │  - Initiative tracker                                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Module Structure

```
launcher/
├── __init__.py
├── main.py                 # Entry point, QApplication
├── models/
│   ├── __init__.py
│   ├── scenario.py         # .scenario import/export
│   └── character.py        # .character import/export
├── ui/
│   ├── __init__.py
│   ├── main_window.py      # Launcher home screen
│   ├── host_dialog.py      # Host session (load scenario, set port)
│   ├── join_dialog.py      # Join session (IP, port, character)
│   ├── session_view.py     # In-game session UI
│   ├── map_widget.py       # Read-only map renderer
│   ├── action_bar.py       # Move/Attack/Ability/End Turn
│   └── chat_panel.py       # Chat + dice log
└── session/
    ├── __init__.py
    ├── dm_controller.py    # DM session logic
    └── player_controller.py # Player session logic
```

### 3.3 File Formats

| Format | Structure | Used By |
|--------|-----------|---------|
| `.scenario` | ZIP containing `world.json`, `entities.json`, `triggers.json`, `assets/` | Launcher imports, Builder exports |
| `.character` | JSON with stats, inventory, spells, portrait path | Players bring to sessions |
| `.session` | JSON save state mid-session (optional) | Launcher pause/resume |

#### `.scenario` ZIP Structure
```
my_dungeon.scenario/
├── manifest.json           # name, version, author, description
├── world.json              # serialized World (tiles, lore)
├── entities.json           # all GameEntity definitions
├── triggers.json           # trigger configurations
└── assets/
    ├── tiles/              # custom tile images
    ├── tokens/             # entity tokens
    └── audio/              # ambient sounds (optional)
```

#### `.character` JSON Schema
```json
{
  "version": "1.0",
  "name": "Aragorn",
  "class": "Ranger",
  "level": 5,
  "race": "Human",
  "stats": {
    "STR": 16, "DEX": 14, "CON": 14,
    "INT": 10, "WIS": 14, "CHA": 12
  },
  "hp": { "current": 45, "max": 45 },
  "ac": 15,
  "speed": 30,
  "skills": { "Perception": 5, "Stealth": 4 },
  "inventory": [],
  "spells": [],
  "portrait": "aragorn.png"
}
```

### 3.4 Launcher Tasks (Ordered)

| # | Task | File(s) | Est. |
|---|------|---------|------|
| 1 | Scenario export in Builder | `ui/menu.py`, `models/scenario_exporter.py` | 1h |
| 2 | Scenario loader | `launcher/models/scenario.py` | 45m |
| 3 | Character format | `launcher/models/character.py` | 30m |
| 4 | Main window | `launcher/ui/main_window.py` | 1h |
| 5 | Host dialog | `launcher/ui/host_dialog.py` | 45m |
| 6 | Join dialog | `launcher/ui/join_dialog.py` | 45m |
| 7 | Map widget | `launcher/ui/map_widget.py` | 1.5h |
| 8 | Action bar | `launcher/ui/action_bar.py` | 1h |
| 9 | Chat panel | `launcher/ui/chat_panel.py` | 45m |
| 10 | Session view | `launcher/ui/session_view.py` | 1h |
| 11 | DM controller | `launcher/session/dm_controller.py` | 1.5h |
| 12 | Player controller | `launcher/session/player_controller.py` | 1.5h |
| 13 | Entry point | `launcher/main.py` | 30m |

---

## Execution Order

### Week 1: Phase 2 Completion + Scenario Export

| Day | Tasks |
|-----|-------|
| 1 | Wire EventBridge to SessionHost, add turn order to FULL_STATE |
| 2 | Client-side turn handling, write test_event_bridge.py |
| 3 | Integration tests (test_state_sync.py), bug fixes |
| 4 | Scenario export format, add "Export for Play" to Builder menu |
| 5 | Scenario loader, character format |

### Week 2: Launcher UI

| Day | Tasks |
|-----|-------|
| 1 | Main window, host dialog |
| 2 | Join dialog, basic session view |
| 3 | Map widget (reuse TileMapWidget code) |
| 4 | Action bar, chat panel |
| 5 | Wire session view to controllers |

### Week 3: Integration & Polish

| Day | Tasks |
|-----|-------|
| 1 | DM controller wiring |
| 2 | Player controller wiring |
| 3 | End-to-end testing (DM + 2 players) |
| 4 | Bug fixes, error handling |
| 5 | Documentation, README |

---

## Dependencies

### Python Packages (already installed)
- PyQt5/PyQt6 — UI
- websockets — Real network transport (Phase 4)
- asyncio — Async networking

### New Dependencies (if needed)
- None for MVP

---

## Testing Strategy

### Unit Tests
- `test_event_bridge.py` — EventBridge throttling, delta computation
- `test_scenario.py` — Export/import roundtrip
- `test_character.py` — Character serialization

### Integration Tests
- `test_state_sync.py` — Multi-client state convergence
- `test_launcher_session.py` — Host/join flow with InMemoryTransport

### Manual Testing
- DM hosts scenario, 2 players join on same machine
- Complete combat encounter with movement, attacks, turn cycling
- Chat functionality
- Disconnect/reconnect handling

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Qt event loop + asyncio conflict | Use `qasync` or run network in separate thread |
| Large scenario files slow to sync | Compress assets, lazy-load tiles |
| Player desync | Periodic full-state checksum, force resync if mismatch |
| Action validation edge cases | Log all rejected actions, review patterns |

---

## Open Questions

1. **WebSocket vs TCP?** — WebSocket easier for firewall traversal, using `websockets` library
2. **LAN discovery?** — Use UDP broadcast for "Find Games" feature (post-MVP)
3. **Save mid-session?** — Export session state to `.session` file (post-MVP)
4. **Voice chat?** — Out of scope, use Discord/external

---

## Next Steps

1. Complete Phase 2 remaining tasks
2. Create `launcher/` directory structure
3. Implement scenario export in Builder
4. Build launcher main window
