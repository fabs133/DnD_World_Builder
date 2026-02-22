# MVP: Multiplayer Session Hosting/Joining

## Goal

Enable a DM to host a scenario session that players can join over a local network (LAN) or internet, allowing real-time collaborative play.

---

## Scope: What's IN the MVP

| Feature | Description |
|---------|-------------|
| Host Session | DM starts a session, gets a join code/address |
| Join Session | Player enters code/IP to connect |
| Player Roles | DM (full control) vs Player (character only) |
| Entity Binding | Player claims their character on join |
| Turn Sync | Current turn, initiative order synced |
| Map Sync | Tile state, entity positions synced |
| Action Broadcast | Actions propagate to all clients |
| Basic Chat | Text chat for table talk |

## What's OUT of MVP

- Voice/video chat (use Discord)
- Cloud hosting (LAN/direct IP only)
- Reconnection handling (restart required)
- Spectator mode
- Fog of war per-player
- Undo across network

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         DM (Host)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Gamemaster  │→ │ SessionHost │→ │ WebSocket Server    │  │
│  │ (authority) │  │             │  │ (asyncio + aiohttp) │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ↓               ↓               ↓
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Player 1      │ │   Player 2      │ │   Player 3      │
│ ┌─────────────┐ │ │ ┌─────────────┐ │ │ ┌─────────────┐ │
│ │SessionClient│ │ │ │SessionClient│ │ │ │SessionClient│ │
│ └─────────────┘ │ │ └─────────────┘ │ │ └─────────────┘ │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Protocol | WebSocket | Bidirectional, works through firewalls, async-friendly |
| Serialization | JSON | Human-readable, easy debugging, Python stdlib |
| Authority | Server-authoritative | DM's Gamemaster is source of truth |
| Threading | asyncio in background thread | Non-blocking UI, single event loop |
| Discovery | Manual IP + port (MVP) | Simple; mDNS/STUN later |

---

## Module Structure

```
network/
├── __init__.py
├── protocol.py          # Message types, serialization
├── session_host.py      # Server: accept connections, broadcast state
├── session_client.py    # Client: connect, send actions, receive state
├── sync.py              # State diffing and patching
└── ui/
    ├── host_dialog.py   # "Host Session" dialog
    ├── join_dialog.py   # "Join Session" dialog
    └── session_panel.py # Connected players, chat
```

---

## Message Protocol

### Message Envelope

```json
{
  "type": "ACTION_REQUEST",
  "seq": 42,
  "timestamp": "2026-02-22T12:00:00Z",
  "payload": { ... }
}
```

### Message Types

| Type | Direction | Payload | Description |
|------|-----------|---------|-------------|
| `HELLO` | C→S | `{player_name, version}` | Client introduces itself |
| `WELCOME` | S→C | `{session_id, player_id, entities}` | Server accepts client |
| `CLAIM_ENTITY` | C→S | `{entity_id}` | Player claims a character |
| `ENTITY_CLAIMED` | S→C | `{entity_id, player_id}` | Broadcast claim |
| `FULL_STATE` | S→C | `{world, entities, turn, round}` | Initial sync |
| `STATE_DELTA` | S→C | `{changes: [...]}` | Incremental update |
| `ACTION_REQUEST` | C→S | `{action_type, params}` | Player requests action |
| `ACTION_RESULT` | S→C | `{success, result, state_delta}` | Action outcome |
| `TURN_CHANGE` | S→C | `{current_entity, round}` | Turn advanced |
| `CHAT` | C↔S | `{sender, message}` | Chat message |
| `ERROR` | S→C | `{code, message}` | Error notification |
| `DISCONNECT` | C→S | `{}` | Graceful disconnect |

---

## Implementation Plan

### Phase 1: Protocol & Core (2-3 days)

**Checkpoint**: Can send/receive messages over WebSocket

1. **protocol.py** - Message types as dataclasses
   ```python
   @dataclass
   class Message:
       type: MessageType
       seq: int
       payload: dict
       
       def to_json(self) -> str: ...
       @classmethod
       def from_json(cls, data: str) -> Message: ...
   ```

2. **session_host.py** - WebSocket server
   ```python
   class SessionHost:
       def __init__(self, gamemaster: Gamemaster, port: int = 8765): ...
       async def start(self): ...
       async def stop(self): ...
       async def broadcast(self, msg: Message): ...
       def get_join_info(self) -> str:  # "192.168.1.5:8765"
   ```

3. **session_client.py** - WebSocket client
   ```python
   class SessionClient:
       def __init__(self, player_name: str): ...
       async def connect(self, host: str, port: int): ...
       async def disconnect(self): ...
       async def send(self, msg: Message): ...
       def on_message(self, callback: Callable): ...
   ```

**Acceptance Criteria**:
- [ ] Host starts server, prints join address
- [ ] Client connects, sends HELLO
- [ ] Server responds with WELCOME
- [ ] Bidirectional message flow works

---

### Phase 2: State Synchronization (2-3 days)

**Checkpoint**: Client receives and displays game state

1. **sync.py** - State serialization
   ```python
   def serialize_world(world: World) -> dict: ...
   def serialize_entity(entity: GameEntity) -> dict: ...
   def apply_delta(state: dict, delta: dict) -> dict: ...
   ```

2. **SessionHost** additions:
   - On client connect → send FULL_STATE
   - On state change → compute and send STATE_DELTA
   - Subscribe to EventBus for game events

3. **SessionClient** additions:
   - Apply FULL_STATE to local view
   - Apply STATE_DELTA incrementally
   - Emit local events for UI updates

**Acceptance Criteria**:
- [ ] Client sees initial map and entities
- [ ] DM moves entity → client sees movement
- [ ] Turn advances → client sees turn change

---

### Phase 3: Player Actions (2-3 days)

**Checkpoint**: Players can take actions on their turn

1. **Action flow**:
   ```
   Player clicks "Move" → SessionClient sends ACTION_REQUEST
   → SessionHost receives → Validates (is it their turn? legal move?)
   → Gamemaster executes → STATE_DELTA broadcast
   → All clients update
   ```

2. **SessionHost** additions:
   ```python
   async def handle_action_request(self, client_id: str, payload: dict):
       # Validate it's this player's turn
       # Validate action is legal
       # Execute via Gamemaster
       # Broadcast result
   ```

3. **UI integration**:
   - Existing action buttons check `session_client.is_my_turn()`
   - Actions route through SessionClient instead of direct execution

**Acceptance Criteria**:
- [ ] Player can move their character on their turn
- [ ] Player cannot act on others' turns (rejected)
- [ ] All players see the action result

---

### Phase 4: UI Integration (2 days)

**Checkpoint**: Full user experience for hosting/joining

1. **host_dialog.py**:
   - Port selection (default 8765)
   - "Start Hosting" button
   - Display join address
   - QR code for mobile (optional)

2. **join_dialog.py**:
   - Host address input
   - Player name input
   - "Connect" button
   - Error display

3. **session_panel.py** (dockable):
   - Connected players list
   - Entity assignments
   - Chat widget
   - "End Session" / "Disconnect" button

4. **main_window.py** integration:
   - Menu: Session → Host / Join / Disconnect
   - Status bar shows connection state

**Acceptance Criteria**:
- [ ] DM can host from menu
- [ ] Player can join via dialog
- [ ] Chat works
- [ ] Players appear in panel

---

### Phase 5: Polish & Testing (2 days)

1. **Error handling**:
   - Connection timeout
   - Invalid messages
   - Player disconnects mid-turn

2. **Testing**:
   - Unit tests for protocol
   - Integration test: host + 2 clients
   - Manual test on separate machines

3. **Documentation**:
   - README section on multiplayer
   - Firewall/port forwarding guide

**Acceptance Criteria**:
- [ ] Graceful error messages
- [ ] Tests pass
- [ ] Can run session across network

---

## Estimated Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 1: Protocol | 2-3 days | 3 days |
| Phase 2: Sync | 2-3 days | 6 days |
| Phase 3: Actions | 2-3 days | 9 days |
| Phase 4: UI | 2 days | 11 days |
| Phase 5: Polish | 2 days | 13 days |

**Total: ~2 weeks** for a working MVP

---

## Technical Notes

### Dependencies to Add

```
aiohttp>=3.9.0      # WebSocket server/client
qasync>=0.27.0      # asyncio + Qt integration
```

### Threading Model

```python
# In main_window.py
from qasync import QEventLoop

app = QApplication(sys.argv)
loop = QEventLoop(app)
asyncio.set_event_loop(loop)

# Session runs in this loop
with loop:
    loop.run_forever()
```

### Security (Post-MVP)

- Session passwords
- TLS for internet play
- Rate limiting
- Input validation

---

## Success Metrics

1. **Functional**: DM and 3 players complete a 30-minute session
2. **Performance**: <100ms action latency on LAN
3. **Stability**: No crashes during 1-hour session
4. **UX**: Players can join in <30 seconds

---

## Open Questions (Resolve Before Starting)

1. **Entity ownership**: Can DM reassign entities mid-session?
2. **Partial control**: Can players control NPCs temporarily?
3. **Save/Load**: Does session state persist if host restarts?
4. **Version mismatch**: Require exact version match?

---

## Next Steps

1. Create `network/` directory structure
2. Implement Phase 1 protocol
3. Write test harness for local WebSocket testing
4. Integrate with existing Gamemaster
