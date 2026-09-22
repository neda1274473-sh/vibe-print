# Phase 4 Design — Observability & Data

## Existing Schema (IterationTracker)

```sql
CREATE TABLE iterations (
    iteration_id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    model_path TEXT,
    created_at TEXT NOT NULL,
    data TEXT NOT NULL          -- JSON blob: PrintIteration serialized
);
CREATE INDEX idx_model_name ON iterations(model_name);
CREATE INDEX idx_created_at ON iterations(created_at);
```

- **Storage**: SQLite via `aiosqlite`, path from `config.database_path` (`~/.vibe-print/prints.db`).
- **Scope**: Per-print-iteration records (outcomes, quality scores, defects).
- **Limitation**: No per-step timing, no durable failure/recovery history across sessions, no category-level aggregates.

---

## New Tables (same database file)

All three tables live in the **same SQLite file** (`~/.vibe-print/prints.db`) because they are logically part of the same observability surface and share the `iteration_id` / `category` foreign concepts. No separate file is needed.

### 1. `workflow_metrics` — Step & Tool Instrumentation

Records every workflow step execution and every instrumented MCP tool call.

```sql
CREATE TABLE IF NOT EXISTS workflow_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,                    -- Agent session ID (NULL for direct tool calls)
    iteration_id TEXT,                  -- Links to iterations.iteration_id (NULL until create_iteration)
    step_name TEXT NOT NULL,            -- e.g. "parse_requirements", "generate_model", "slice_model"
    category TEXT,                      -- Model category if known at execution time
    started_at TEXT NOT NULL,           -- ISO-8601 datetime
    completed_at TEXT,                  -- ISO-8601 datetime
    duration_ms INTEGER,                -- computed from started_at / completed_at
    success INTEGER NOT NULL CHECK (success IN (0, 1)),
    error_message TEXT,                 -- populated when success = 0
    decision_rule TEXT,                 -- e.g. "thin_wall_auto_adjust", "non_watertight_repair", "excessive_print_time"
    recovery_strategy TEXT,             -- e.g. "repair_model", "parameter_adjust", "category_fallback"
    recovery_success INTEGER CHECK (recovery_success IN (0, 1)),  -- NULL if no recovery attempted
    metadata TEXT                       -- JSON blob: extra context (e.g. {"print_time_min": 120, "filament_g": 250})
);

CREATE INDEX IF NOT EXISTS idx_metrics_session ON workflow_metrics(session_id);
CREATE INDEX IF NOT EXISTS idx_metrics_step ON workflow_metrics(step_name);
CREATE INDEX IF NOT EXISTS idx_metrics_category ON workflow_metrics(category);
CREATE INDEX IF NOT EXISTS idx_metrics_started ON workflow_metrics(started_at);
```

**Rationale for columns:**
- `session_id` + `step_name` lets us reconstruct a full workflow trace across sessions.
- `category` enables per-category aggregation (success rate by category, avg slicing time by category).
- `decision_rule` + `recovery_strategy` capture *which* rule fired and *which* recovery was attempted, satisfying the "where applicable" requirement.
- `metadata` is a flexible JSON column for step-specific context (e.g. slicer estimates, wall thickness values) without schema churn.

### 2. `failure_events` — Durable Failure & Recovery Dataset

Every failure and recovery action that currently lives only in `AgentSession.recovery_actions` (in-memory, gone after the call) is persisted here.

```sql
CREATE TABLE IF NOT EXISTS failure_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    step_name TEXT NOT NULL,
    category TEXT,
    failure_type TEXT NOT NULL,         -- e.g. "not_watertight", "thin_walls", "generation_failed", "custom_category"
    recovery_strategy TEXT,             -- NULL if no recovery was attempted
    recovery_success INTEGER CHECK (recovery_success IN (0, 1)),  -- NULL if no recovery
    retry_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    metadata TEXT                       -- JSON: e.g. {"min_dim_mm": 0.5, "target_wall_mm": 2.0}
);

CREATE INDEX IF NOT EXISTS idx_failures_session ON failure_events(session_id);
CREATE INDEX IF NOT EXISTS idx_failures_category ON failure_events(category);
CREATE INDEX IF NOT EXISTS idx_failures_type ON failure_events(failure_type);
CREATE INDEX IF NOT EXISTS idx_failures_strategy ON failure_events(recovery_strategy);
CREATE INDEX IF NOT EXISTS idx_failures_created ON failure_events(created_at);
```

**Why a separate table from `workflow_metrics`?**
- A single workflow step can generate **multiple** failure events (e.g. repair attempted, still not watertight, then parameter adjust attempted). `workflow_metrics` has one row per step; `failure_events` has one row per failure/recovery occurrence.
- Cross-session queries like "which categories fail watertightness most often" are cleaner against a dedicated failure table.
- The task explicitly calls for a "failure dataset" that is "durable and queryably across sessions" — a dedicated table makes this intent explicit.

### 3. `category_performance` — Cached Aggregates

Materialized aggregates per category, updated after each workflow run. This avoids recomputing expensive aggregates on every `get_print_analytics` call.

```sql
CREATE TABLE IF NOT EXISTS category_performance (
    category TEXT PRIMARY KEY,
    total_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    total_recovery_triggers INTEGER DEFAULT 0,
    total_slicing_time_est_min REAL DEFAULT 0.0,  -- sum of all slicing estimates
    slicing_count INTEGER DEFAULT 0,              -- count of slicing metrics rows
    last_updated TEXT NOT NULL
);
```

**Why a separate table instead of pure on-the-fly aggregation?**
- `get_print_analytics` may be called frequently by MCP clients. Computing `AVG(duration_ms)` and `COUNT(*)` across thousands of rows on every call is fine for now, but caching category-level aggregates is cheap and makes the system more responsive.
- The table is **updated incrementally** after each workflow run, not rebuilt from scratch.
- If the table is ever out of sync, `get_print_analytics` can fall back to computing from `workflow_metrics` directly.

---

## Instrumentation Points

### WorkflowExecutor (6 steps)

Instrumentation is added **inside `WorkflowExecutor.run()`**, wrapping each step handler call. A new `_MetricsRecorder` helper class (inside `orchestrator.py`) handles the actual DB writes via the existing `IterationTracker` connection.

```python
# Inside WorkflowExecutor.run() — before/after each step
step.started_at = datetime.now()
# ... handler execution ...
step.completed_at = datetime.now()
# Record metric
self._record_step_metric(session, step, ok, output)
```

Per-step decision-rule mapping:

| Step | Decision Rule | Recovery Strategy | When Recorded |
|------|--------------|-------------------|---------------|
| `parse_requirements` | `low_confidence_routing` | — | When `category == CUSTOM` |
| `generate_model` | `generation_failure` | `category_fallback` | When generation raises + fallback succeeds |
| `analyze_model` | `non_watertight` | `repair_model` | When `is_watertight == False` |
| `validate_model` | `thin_walls` | `parameter_adjust` | When `min_dim < MIN_WALL_MM` |
| `slice_model` | `excessive_print_time` | — | When `print_time > MAX_PRINT_TIME_MIN` |
| `slice_model` | `excessive_filament` | — | When `filament_g > MAX_FILAMENT_G` |
| `create_iteration` | — | — | Always (no decision rule) |

### Core MCP Tools (3 tools)

Instrumentation is added as a decorator `@_record_tool_metric` on the server-side tool functions:

| Tool | What is Recorded |
|------|-----------------|
| `generate_model` | `step_name="generate_model"`, `success`, `duration_ms`, `category` from input |
| `analyze_model` | `step_name="analyze_model"`, `success`, `duration_ms`, `is_watertight` in metadata |
| `slice_model` | `step_name="slice_model"`, `success`, `duration_ms`, `print_time_min`, `filament_g` in metadata |

These write to the **same** `workflow_metrics` table with `session_id = NULL` (since they are direct tool calls, not part of an agent workflow).

---

## Failure Event Persistence

After each step handler returns (or raises), `WorkflowExecutor` checks the step outcome and writes to `failure_events`:

1. **Failure detected** (handler returns `ok=False` or raises):
   - Insert row with `failure_type` inferred from error message / step context.
   - `recovery_strategy = NULL`, `recovery_success = NULL`.

2. **Recovery attempted** (handler sets `StepStatus.RECOVERED`):
   - Insert row with `failure_type` and `recovery_strategy`.
   - `recovery_success = 1`.

3. **Recovery failed** (handler returns `ok=False` after recovery attempt):
   - Insert row with `failure_type` and `recovery_strategy`.
   - `recovery_success = 0`.

The `failure_type` values are normalized:
- `not_watertight`
- `thin_walls`
- `generation_failed`
- `custom_category`
- `slicing_failed`
- `iteration_creation_failed`

---

## Analytics Computation (`get_print_analytics`)

### Input Schema
```python
class GetPrintAnalyticsInput(BaseModel):
    category: Optional[str] = Field(None, description="Filter by model category")
    date_from: Optional[str] = Field(None, description="ISO date filter start")
    date_to: Optional[str] = Field(None, description="ISO date filter end")
```

### Output Schema
```python
{
    "success": True,
    "summary": "human-readable summary string",
    "stats": {
        "overall": {
            "total_workflows": int,
            "successful_workflows": int,
            "failed_workflows": int,
            "overall_success_rate": float,
        },
        "by_category": [
            {
                "category": str,
                "total_runs": int,
                "successful_runs": int,
                "failed_runs": int,
                "success_rate": float,
                "avg_iterations_to_success": float,  # from recovery retry counts
                "avg_slicing_time_est_min": float,
                "recovery_trigger_rate": float,  # recoveries / total_runs
                "most_common_failure": str,
                "most_common_failure_count": int,
            }
        ],
        "failure_ranking": [
            {"failure_type": str, "count": int, "top_category": str}
        ],
        "recovery_ranking": [
            {"recovery_strategy": str, "count": int, "success_rate": float}
        ],
        "step_latency": [
            {"step_name": str, "avg_duration_ms": float, "count": int}
        ],
    }
}
```

### Empty State
If no data exists, return:
```python
{
    "success": True,
    "summary": "No workflow data recorded yet. Run some print workflows to see analytics.",
    "stats": None,
}
```

---

## Category Performance Tracking

**Decision**: Expose as part of `get_print_analytics` (not a separate tool).

**Rationale**: The analytics output already includes per-category performance (`success_rate`, `avg_slicing_time_est_min`, `recovery_trigger_rate`). A separate tool would duplicate the same data and add cognitive overhead for MCP clients. If the dataset grows large enough to warrant a dedicated endpoint, that can be added in Phase 5 without breaking the API.

---

## Files to Modify / Create

| File | Action | Description |
|------|--------|-------------|
| `vibe_print/iteration/tracker.py` | **Modify** | Add new table creation in `initialize()`, add `record_metric()`, `record_failure()`, `get_print_analytics()`, `_update_category_performance()` methods |
| `vibe_print/agent/orchestrator.py` | **Modify** | Add `_MetricsRecorder` helper, instrument `run()` and each step handler, persist failure events |
| `vibe_print/server.py` | **Modify** | Add `@_record_tool_metric` decorator, instrument `generate_model`, `analyze_model`, `slice_model`, add `get_print_analytics` MCP tool |
| `tests/test_analytics.py` | **Create** | Tests for analytics computation, empty state, workflow→analytics consistency |
| `PHASE4_SUMMARY.md` | **Create** | Final report |

---

## Test Plan

1. **Empty state**: Call `get_print_analytics` on fresh DB → assert empty-state response.
2. **Clean workflow**: Run tube-squeezer workflow → assert `total_workflows=1`, `success_rate=1.0`, `recovery_actions=[]`.
3. **Recovery workflow**: Run workflow with non-watertight model → assert `recovery_trigger_rate > 0`, `failure_ranking` contains `not_watertight`.
4. **Failed workflow**: Run workflow that fails outright → assert `failed_workflows=1`, `success_rate < 1.0`.
5. **Category filter**: Run workflows for different categories, filter by one → assert only that category's stats.
6. **Existing tests**: Run full test suite → assert all 194 pass.
