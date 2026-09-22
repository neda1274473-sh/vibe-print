# Phase 5 Design — Scale & Cloud

## Honest Scope: Real vs. Simulated

| Deliverable | What's Real | What's Simulated (Clearly Labeled) |
|-------------|-------------|-----------------------------------|
| **1. Persistent multi-tenant session storage** | Real SQLite persistence for `SessionStore`; real `user_id` column on all tables; real user-scoped queries | None — this is fully real against local SQLite |
| **2. Remote monitoring** | Real `get_server_status` MCP tool reporting real process metrics; real SSE transport configuration documented | No actual network exposure in tests (we document the transport flag, tests call the tool directly) |
| **3. Multi-user auth boundaries** | Real API-key-per-user scheme; real `user_id` filtering on every read; real rejection of cross-user access | API keys are stored in SQLite (not a separate auth provider); no TLS/OAuth |
| **4. Fleet / multi-printer** | Real multi-printer registry with independent state; real per-printer routing in `start_print` | Printers are `SimulatedPrinterMQTTClient` instances (same simulation as Phase 2.5) |
| **5. Cloud sync** | Real sync logic: incremental push/pull, conflict resolution via timestamp, idempotency | "Cloud" is a second local SQLite file standing in for remote; clearly labeled |

**What a real production deployment would still need:** Hosted PostgreSQL (instead of local SQLite), real TLS termination, real OAuth/SSO provider, real MQTT broker for printers, horizontal scaling with load balancer, backup/DR strategy. This phase proves the **logic**; infrastructure is out of scope.

---

## Deliverable 1: Persistent, Multi-Tenant-Ready Session Storage

### Current State

- `SessionStore` is an in-memory `Dict[str, AgentSession]` — sessions vanish on restart.
- `IterationTracker` already persists to SQLite — we extend that same database.

### Schema Migration

Add `user_id` to all existing tables. Use `"default"` as the default value for backward compatibility with Phase 2–4 data.

```sql
-- Migration: add user_id to existing tables
ALTER TABLE iterations ADD COLUMN user_id TEXT DEFAULT 'default';
ALTER TABLE workflow_metrics ADD COLUMN user_id TEXT DEFAULT 'default';
ALTER TABLE failure_events ADD COLUMN user_id TEXT DEFAULT 'default';

-- New table: agent_sessions (replaces in-memory dict)
CREATE TABLE agent_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    goal TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    current_step_index INTEGER DEFAULT 0,
    model_path TEXT,
    model_type TEXT,
    iteration_id TEXT,
    status TEXT DEFAULT 'active',  -- active, completed, failed
    data TEXT NOT NULL  -- JSON: plan, retry_counts, recovery_actions, messages, etc.
);

CREATE INDEX idx_sessions_user ON agent_sessions(user_id);
CREATE INDEX idx_sessions_status ON agent_sessions(status);
CREATE INDEX idx_sessions_created ON agent_sessions(created_at);

-- Add user_id indexes for analytics filtering
CREATE INDEX idx_metrics_user ON workflow_metrics(user_id);
CREATE INDEX idx_failures_user ON failure_events(user_id);
CREATE INDEX idx_iterations_user ON iterations(user_id);
```

### SessionStore Refactor

Replace the in-memory dict with SQLite-backed operations:

```python
class SessionStore:
    def __init__(self, tracker: Optional[IterationTracker] = None):
        self.tracker = tracker  # Uses same DB
        self._cache: Dict[str, AgentSession] = {}  # Optional hot cache

    def create(self, goal: str, user_id: str = "default") -> AgentSession:
        session = AgentSession(goal=goal)
        session.user_id = user_id
        # Persist immediately
        asyncio.run(self._persist(session))
        self._cache[session.session_id] = session
        return session

    def get(self, session_id: str, user_id: str = "default") -> Optional[AgentSession]:
        # Check cache first
        if session_id in self._cache:
            s = self._cache[session_id]
            if s.user_id == user_id:
                return s
            return None  # Wrong user
        # Load from DB with user_id filter
        return asyncio.run(self._load(session_id, user_id))

    def delete(self, session_id: str, user_id: str = "default") -> None:
        # Delete only if owned by user
        asyncio.run(self._delete(session_id, user_id))
        self._cache.pop(session_id, None)
```

### Backward Compatibility

- All existing methods on `IterationTracker` get an optional `user_id: str = "default"` parameter.
- All existing queries add `AND user_id = ?` with `"default"` as the default bind value.
- Phase 2–4 data (which has `user_id = 'default'`) remains visible and functional.

---

## Deliverable 2: Remote Monitoring

### Transport Configuration

FastMCP supports SSE/HTTP via `mcp.run(transport="sse")`. We document this in `README.md` and add a CLI flag:

```bash
python -m vibe_print --transport sse --port 8080
```

The server code checks for env vars:
- `VIBE_MCP_TRANSPORT` — `"stdio"` (default) or `"sse"`
- `VIBE_MCP_PORT` — port for SSE mode

### New MCP Tool: `get_server_status`

```python
class GetServerStatusInput(BaseModel):
    pass  # No input needed

@mcp.tool()
def get_server_status(input: GetServerStatusInput) -> Dict[str, Any]:
    return {
        "success": True,
        "uptime_seconds": time.time() - _start_time,
        "active_sessions": len(_agent_store.list_active()),
        "total_sessions_today": _tracker.count_sessions_today(),
        "db_connected": _tracker.is_initialized(),
        "transport": _current_transport,
        "version": "5.0.0",
    }
```

All values are real — `uptime_seconds` from process start time, `active_sessions` from the (now persistent) session store, `db_connected` from a lightweight ping query.

---

## Deliverable 3: Multi-User Auth Boundaries

### API Key Scheme

Simple but real: each user has an API key stored in a new `users` table. The key is checked at the tool-call boundary.

```sql
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    api_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    role TEXT DEFAULT 'user'  -- user, admin
);

-- Default user for backward compatibility
INSERT INTO users (user_id, api_key, created_at) VALUES ('default', 'default-key', datetime('now'));
```

### Auth Middleware

Since MCP tools are plain Python functions decorated with `@mcp.tool()`, we add an auth wrapper:

```python
def require_auth(fn):
    """Decorator: extract API key from input, validate, inject user_id."""
    @functools.wraps(fn)
    def wrapper(input):
        api_key = getattr(input, 'api_key', None) or 'default-key'
        user = _authenticate(api_key)
        if user is None:
            return {"success": False, "error": "Invalid API key"}
        # Inject user_id into the input for downstream use
        input._user_id = user["user_id"]
        return fn(input)
    return wrapper
```

All tools that access user data accept an optional `api_key` field in their input schema. Tools that don't need user isolation (e.g., `suggest_model`) don't require it.

### User Isolation Enforcement

Every read query in `IterationTracker` and `SessionStore` filters by `user_id`:

```sql
-- Before (Phase 4)
SELECT * FROM workflow_metrics WHERE session_id = ?

-- After (Phase 5)
SELECT * FROM workflow_metrics WHERE session_id = ? AND user_id = ?
```

Cross-user access attempts return `None` / empty results / error, not silent leakage.

---

## Deliverable 4: Fleet / Multi-Printer Management

### Printer Registry

A new `PrinterRegistry` class manages multiple printer connections:

```python
class PrinterRegistry:
    def __init__(self):
        self._printers: Dict[str, PrinterMQTTClient] = {}
        self._printer_configs: Dict[str, Dict[str, Any]] = {}

    def register(self, printer_id: str, host: str, access_code: str, serial: str) -> PrinterMQTTClient:
        client = get_printer_client(host=host, access_code=access_code, serial_number=serial)
        self._printers[printer_id] = client
        self._printer_configs[printer_id] = {"host": host, "serial": serial}
        return client

    def get(self, printer_id: str) -> Optional[PrinterMQTTClient]:
        return self._printers.get(printer_id)

    def list_printers(self) -> List[Dict[str, Any]]:
        return [
            {
                "printer_id": pid,
                "connected": p.is_connected,
                "config": self._printer_configs[pid],
                "last_status": p.get_last_report(),
            }
            for pid, p in self._printers.items()
        ]

    async def get_status(self, printer_id: str) -> Optional[Dict[str, Any]]:
        client = self._printers.get(printer_id)
        if client:
            return await client.get_status()
        return None
```

### MCP Tools

```python
class ListPrintersInput(BaseModel):
    api_key: Optional[str] = None

class GetPrinterStatusInput(BaseModel):
    printer_id: str
    api_key: Optional[str] = None

class StartPrintInput(BaseModel):
    printer_id: str
    model_path: str
    api_key: Optional[str] = None
```

`start_print` now requires `printer_id` instead of using a global default.

### Simulated Printers

In test mode, we register multiple `SimulatedPrinterMQTTClient` instances with independent state:

```python
registry = PrinterRegistry()
registry.register("printer-a", "simulated", "SIM-A", "SIM001")
registry.register("printer-b", "simulated", "SIM-B", "SIM002")

# Each has independent state
status_a = await registry.get_status("printer-a")  # IDLE
status_b = await registry.get_status("printer-b")  # IDLE
```

---

## Deliverable 5: Cloud Sync

### Sync Target

A second SQLite database file acts as "the cloud":

```python
cloud_tracker = IterationTracker(db_path=Path("cloud_sync.db"))
```

Same schema, same code — just a different file path. This is clearly labeled as simulation in all docs and logs.

### Sync Logic

```python
class CloudSync:
    def __init__(self, local_tracker: IterationTracker, remote_tracker: IterationTracker):
        self.local = local_tracker
        self.remote = remote_tracker
        self._last_sync_at: Optional[datetime] = None

    async def push(self, user_id: str = "default") -> Dict[str, int]:
        """Push local changes to remote since last sync."""
        since = self._last_sync_at.isoformat() if self._last_sync_at else "1970-01-01"

        # Get local records modified since last sync
        local_metrics = await self.local.get_metrics_since(since, user_id)
        local_failures = await self.local.get_failures_since(since, user_id)
        local_sessions = await self.local.get_sessions_since(since, user_id)

        # Upsert to remote (idempotent: same primary keys)
        for record in local_metrics:
            await self.remote.upsert_metric(record)
        for record in local_failures:
            await self.remote.upsert_failure(record)
        for record in local_sessions:
            await self.remote.upsert_session(record)

        self._last_sync_at = datetime.now()
        return {"metrics_pushed": len(local_metrics), "failures_pushed": len(local_failures), "sessions_pushed": len(local_sessions)}

    async def pull(self, user_id: str = "default") -> Dict[str, int]:
        """Pull remote changes to local since last sync."""
        since = self._last_sync_at.isoformat() if self._last_sync_at else "1970-01-01"

        remote_metrics = await self.remote.get_metrics_since(since, user_id)
        remote_failures = await self.remote.get_failures_since(since, user_id)
        remote_sessions = await self.remote.get_sessions_since(since, user_id)

        # Upsert to local
        for record in remote_metrics:
            await self.local.upsert_metric(record)
        for record in remote_failures:
            await self.local.upsert_failure(record)
        for record in remote_sessions:
            await self.local.upsert_session(record)

        self._last_sync_at = datetime.now()
        return {"metrics_pulled": len(remote_metrics), "failures_pulled": len(remote_failures), "sessions_pulled": len(remote_sessions)}

    async def sync(self, user_id: str = "default") -> Dict[str, Any]:
        """Bidirectional sync: push then pull."""
        push_result = await self.push(user_id)
        pull_result = await self.pull(user_id)
        return {"push": push_result, "pull": pull_result}
```

### Conflict Resolution

Records are keyed by primary key (`metric_id`, `event_id`, `session_id`). The `updated_at` / `created_at` timestamp determines the winner in case of conflict. Since we use `INSERT OR REPLACE` (SQLite upsert), the last write wins — acceptable for this phase. A production system would need vector clocks or CRDTs.

### What Would Change for Real Cloud

To point at a real hosted database:
1. Replace `remote_tracker = IterationTracker(db_path=...)` with a connection string to PostgreSQL/Cloud SQL
2. Use `asyncpg` instead of `aiosqlite` for the remote connection
3. Add TLS certificate configuration
4. The sync logic itself (`push`/`pull`/`sync`) remains unchanged — it's database-agnostic

---

## Test Plan

### Deliverable 1 Tests
- `test_session_persistence`: Create session, destroy store, create new store with same DB, verify session is readable
- `test_session_restart`: Simulate server restart by re-instantiating `SessionStore` with same tracker

### Deliverable 2 Tests
- `test_get_server_status`: Verify all fields are real values (not placeholders)
- `test_server_status_db_connected`: Verify `db_connected` reflects actual DB state

### Deliverable 3 Tests (Mandatory)
- `test_user_a_cannot_see_user_b_sessions`: Create session as user A, try to read as user B, assert failure
- `test_user_a_cannot_see_user_b_analytics`: Record metrics as user A, query analytics as user B, assert empty
- `test_invalid_api_key_rejected`: Call tool with bad API key, assert error response
- `test_cross_user_access_rejected`: Attempt to access another user's iteration, assert clear error

### Deliverable 4 Tests
- `test_multi_printer_registry`: Register 2 printers, verify both listed independently
- `test_printer_state_independence`: Set one printer to "printing", verify other still "idle"
- `test_start_print_routes_to_specific_printer`: Call `start_print` with printer_id, verify correct printer receives command

### Deliverable 5 Tests
- `test_sync_round_trip`: Create local data, sync to remote, wipe local, sync back, verify data matches
- `test_sync_incremental`: Sync once, add more data, sync again, verify only new data transferred
- `test_sync_idempotent`: Sync twice without changes, verify no duplicates

### Regression Tests
- All 207 existing tests must pass unmodified
