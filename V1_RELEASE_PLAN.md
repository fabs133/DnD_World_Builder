# v1 Release Plan — DnD World Builder

## Context

The project is feature-rich but has 6 known UI bugs, multiplayer Phases 3-5 unfinished, a barebones GitHub repo presentation, and zero build/release infrastructure. The goal is to reach a **presentable v1.0.0** state: bugs fixed, multiplayer complete, repo polished, and cross-platform artifacts (Windows/macOS/Linux) auto-built on git tag push.

---

## Phase 1: Fix Known UI Bugs

All bugs are documented in `NEXT_WORK_ITEMS.md` with root-cause analysis and exact fix locations. Each is independent.

### Bug 1 — Hex grid renders square tiles
- **File:** `ui/main_window.py` → `initialize_default_map()` (~line 303-329)
- **Fix:** Read `grid_type` from `self.settings.get("grid_type", "square")` instead of hardcoded `"square"`. Delete the duplicate tile-creation loop (lines 310-331) — `init_grid()` already creates all tiles.

### Bug 2 — Right-click context menu undiscoverable
- **File:** `ui/main_window.py` → `init_ui()` and `init_menu()`
- **Fix:** Add a hint label below the canvas: "Right-click any tile to edit attributes · Paint Mode: Left-click to paint". Add status bar message with shortcuts. Add Help → Tutorial menu action.

### Bug 3 — Tag checkboxes invisible on dark themes
- **File:** `ui/dialogs/tile_dialog.py` → `__init__()` tag loop (~line 101)
- **Fix:** Apply explicit `QCheckBox::indicator` stylesheet with visible border and purple checked fill. Add `tile_item.update()` call in `save_attributes()`.

### Bug 4a — Trigger nodes overlap in same graph column
- **File:** `ui/dialogs/trigger_editor/graph_view.py` → `build_graph()`
- **Fix:** Track `col_row_counter` dict, stack nodes vertically at `y = 40 + row_in_col * 120`. Update scene rect to fit.

### Bug 4b — Duplicate "Save Trigger" button
- **File:** `ui/dialogs/trigger_editor/property_editor.py` → `__init__()` (lines 67-75)
- **Fix:** Remove the internal button row. The dialog's Save button already calls `property_editor.save_trigger()`. Update any tests referencing `property_editor.save_btn`.

### Bug 5 — Stat block text obscured on dark mode
- **File:** `ui/dialogs/stat_block_dialog.py` → `__init__()`, `_build_html()`, `_css()`
- **Fix:** Set `browser.setStyleSheet(background-color: ...)`, wrap HTML in proper `<html><body>` with explicit background, add `background-color: transparent` to `.header h1`.

### Verification
- Run `pytest --timeout=60` — all 105 test files pass
- Manual check: open with hex grid selected → hex tiles render correctly
- Manual check: dark theme → checkboxes visible, stat block readable
- Manual check: trigger editor → nodes don't overlap, single Save button

---

## Phase 2: Complete Multiplayer (Phases 3-5)

### What Already Exists (Phases 1-2 ✅)
- `network/protocol.py` — MessageType enum, JSON envelope, PROTOCOL_VERSION
- `network/transport.py` + `websocket_transport.py` — Abstract + WebSocket + InMemory implementations
- `network/session_host.py` — Accepts connections, HELLO/WELCOME handshake, entity claims, chat broadcast. **`_handle_action_request` is a stub (pass)**
- `network/session_client.py` — Connects, handshake, FULL_STATE/STATE_DELTA application, entity claiming, `request_action()` method ready
- `network/event_bridge.py` — EventBridge (16 game events → delta broadcast, 100ms throttle) + TurnBridge
- `network/sync.py` — serialize_world, serialize_entity, compute_delta, apply_delta
- `network/session_manager.py` — Full Qt-threaded orchestrator with pyqtSignals, host/join/leave lifecycle, asyncio background thread
- `network/ui/host_dialog.py` — Port selector, LAN IP display, Start Hosting button
- `network/ui/join_dialog.py` — Host/port input, player name, Connect button
- `network/ui/session_panel.py` — Player list, entity claims, chat log+input, disconnect button
- `models/flow/action/action.py` — Abstract `Action` base with `validate()`, `execute()`, dice rolling, effect application
- `models/flow/action/action_validator.py` — `ActionValidator.validate(action, game_state)`

### Phase 3: Player Actions Over Network

**3.1 Implement `_handle_action_request` in `session_host.py`**
- Validate it's the requesting player's turn (check `_entity_claims` → player owns acting entity, `turn_system.current_turn` matches)
- Validate action is legal via `ActionValidator.validate()`
- Execute via Gamemaster (triggers EventBridge → automatic STATE_DELTA broadcast)
- Send `ACTION_RESULT` back to requesting player (success/failure + reason)
- Add new protocol helpers: `make_action_result(success, result_data, error_msg=None)`

**3.2 Add `ACTION_RESULT` handling in `session_client.py`**
- Handle `MessageType.ACTION_RESULT` in `listen()` loop
- Fire registered callbacks for UI feedback (success toast / error message)

**3.3 Add `request_action` signal to `SessionManager`**
- New signal: `action_result_received = pyqtSignal(bool, str)` (success, message)
- New method: `request_action(action_type, params)` that calls `session_client.request_action()`
- Register `ACTION_RESULT` handler in `_start_joining()`

**3.4 Wire UI actions through network when in session**
- **File:** `ui/main_window.py` or interaction handlers
- When `session_manager.is_connected`: intercept entity move/attack actions → route through `session_manager.request_action()` instead of direct Gamemaster execution
- When NOT in session: existing direct execution unchanged
- Disable action buttons when it's not the player's turn

**Files to modify:**
- `network/session_host.py` — implement `_handle_action_request()`
- `network/session_client.py` — handle ACTION_RESULT in listen loop
- `network/session_manager.py` — add action_result signal + request_action method
- `network/protocol.py` — add `make_action_result()` helper
- `ui/main_window.py` — conditional routing of actions through network

**New tests:**
- `tests/unit/network/test_action_request.py` — host validates turn, rejects wrong player, executes legal action
- `tests/integration/test_networked_actions.py` — player moves entity over network, all clients see result

### Phase 4: Launcher UI Integration

**4.1 Add "Host Session" / "Join Session" to `entry_point.py` LaunchDialog**
- Add two new buttons: "Host Multiplayer Session" and "Join Multiplayer Session"
- Host flow: opens `HostDialog` → starts `MainController` with `SessionManager` in host mode
- Join flow: opens `JoinDialog` → starts `MainController` with `SessionManager` in client mode (limited UI, read-only map)

**4.2 Integrate SessionPanel into MainWindow**
- **File:** `ui/main_window.py`
- Add `SessionPanel` as a dockable right-side panel (hidden by default)
- Wire `SessionManager.signals` to `SessionPanel` methods:
  - `chat_received` → `session_panel.append_chat()`
  - `entity_claimed` → `session_panel.set_entity_claim()`
  - `player_connected` → `session_panel.add_player()`
  - `disconnected` → `session_panel.clear()`
- Wire `session_panel.chat_submitted` → `session_manager.send_chat()`
- Wire `session_panel.disconnect_requested` → `session_manager.stop_hosting()` or `session_manager.leave()`
- Show panel when session starts, hide when disconnected

**4.3 Session menu actions (already stubbed in main_window.py)**
- Wire existing Session → Host / Join / Disconnect menu actions to `SessionManager`

**Files to modify:**
- `entry_point.py` — add Host/Join buttons to LaunchDialog
- `ui/main_window.py` — add SessionPanel dock, wire signals, session menu handlers

### Phase 5: Polish & Error Handling

**5.1 Connection resilience**
- Timeout handling: show error dialog if connection takes >10s
- Mid-session disconnect: show "Connection lost" dialog, option to retry
- Host stops: notify all clients with error message before shutdown

**5.2 Player experience**
- Show "Waiting for your turn..." overlay when it's another player's turn
- Disable map editing tools for players (read-only view)
- Entity claim UI: dropdown in SessionPanel showing available (unclaimed) entities

**5.3 Documentation**
- Add "Multiplayer" section to README.md with setup instructions
- Add firewall/port forwarding note

**5.4 Tests**
- `tests/integration/test_full_multiplayer_flow.py` — DM hosts, 2 players join, claim entities, take turns, chat, disconnect
- Verify existing 105 test files still pass (no regressions)

---

## Phase 3: Repo Polish

### 3.1 Add LICENSE file
- **Create:** `LICENSE` at project root (MIT, matching README claim)

### 3.2 Update README.md
- Fix entry point: `python tiles_gui.py` → `python entry_point.py`
- Fix Python version: `3.8+` → `3.11+`
- Update "Planned Features" section (color picker, undo/redo, zoom/pan already done — replace with current roadmap)
- Add multiplayer section with quick-start instructions
- Add screenshots/GIF section (placeholder for now)
- Add "Installation" section with `pip install -r requirements.txt`
- Fix data path: `core/data/rulebook_json/` → `core/data_/rulebook_json/`

### 3.3 Separate dependencies
- **Create:** `requirements-dev.txt` with test/dev dependencies
- **Update:** `requirements.txt` to runtime-only

### 3.4 Add `pyproject.toml`
- Modern Python packaging metadata
- Project name, version (`1.0.0`), description, author, license
- `[tool.pytest.ini_options]` — timeout, asyncio_mode
- `[tool.ruff]` — basic linting config

### 3.5 Update CI workflow
- **File:** `.github/workflows/ci.yml`
- Use `requirements-dev.txt` for test deps
- Add `pytest-cov` with coverage report (informational, no gate for v1)
- Update `actions/checkout` from v3 to v4

### 3.6 Add `.python-version`
- Pin `3.11` for pyenv/asdf users

---

## Phase 4: Build Pipeline & Release Artifacts

### 4.1 Create PyInstaller spec
- **Create:** `dnd_world_builder.spec` at project root
- Entry point: `entry_point.py`
- Bundle data: `core/data_/rulebook_json/`, `dnd_database.db`, `config/` template
- Include `qt-material` theme XMLs from site-packages
- Hidden imports: `aiohttp`, `PyQt5.sip`
- Single-directory output (not one-file — faster startup, easier debugging)

### 4.2 Create release workflow
- **Create:** `.github/workflows/release.yml`
- **Trigger:** `on: push: tags: ['v*']` (tag-based)
- **Matrix build:** windows-latest, macos-latest, ubuntu-latest
- **Final job:** Create GitHub Release with all 3 artifacts via `softprops/action-gh-release@v2`

### 4.3 Platform notes
- **Windows:** PyInstaller natively, `.zip` output
- **macOS:** `.app` bundle, no code signing for v1 (Gatekeeper workaround noted)
- **Linux:** directory bundle as `.tar.gz`, requires X11 libs
- **Python version:** No impact on end users — PyInstaller bundles the interpreter

---

## Execution Order

| Step | Phase | Description | Depends On |
|------|-------|-------------|------------|
| 1 | 1 | Fix all 6 UI bugs | — |
| 2 | 1 | Run full test suite, fix any regressions | Step 1 |
| 3 | 2 | Multiplayer Phase 3: action request handling | Step 2 |
| 4 | 2 | Multiplayer Phase 4: launcher + SessionPanel integration | Step 3 |
| 5 | 2 | Multiplayer Phase 5: error handling, polish, tests | Step 4 |
| 6 | 3 | Repo polish: LICENSE, README, pyproject.toml, deps | Step 2 (parallel with Steps 3-5) |
| 7 | 4 | Create PyInstaller spec, test locally | Step 5 + Step 6 |
| 8 | 4 | Create release workflow, test with dry-run tag | Step 7 |
| 9 | — | Final test pass, tag `v1.0.0`, verify release artifacts | Step 8 |
