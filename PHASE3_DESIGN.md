# Phase 3 Design — Intelligent Agent Orchestration Layer

## 1. Planner Approach: Deterministic State Machine

**Rationale**: The 3D-print workflow is a linear pipeline with well-known decision points. A rule-based state machine is simpler, faster, fully testable, and requires no additional LLM calls. An LLM-based planner would add latency, cost, and non-determinism for a problem that has a clear correct sequence.

**Workflow States** (for a "generate and prepare" goal):

```
PARSE_REQUIREMENTS
  → GENERATE_MODEL
  → ANALYZE_MODEL
      [not watertight] → REPAIR_MODEL → ANALYZE_MODEL (retry 1)
      [still bad] → FAIL with explanation
  → VALIDATE_MODEL
      [thin walls] → ADJUST_PARAMETERS → GENERATE_MODEL (retry ≤2)
      [other issues] → SURFACE_TO_USER with recommendation
  → SLICE_MODEL
      [print time > 4h or filament > 200g] → SUGGEST_SCALE_DOWN
  → CREATE_ITERATION
  → DONE
```

Each state transition is an explicit function with documented trigger conditions.

## 2. Context Store Structure

```python
@dataclass
class AgentSession:
    session_id: str
    goal: str
    current_plan: List[WorkflowStep]
    current_step_index: int
    retry_counts: Dict[str, int]  # step_name → retries used
    recovery_actions: List[Dict[str, Any]]

    # Artifact references (populated as workflow progresses)
    requirements: Optional[ModelRequirements]
    model_path: Optional[str]
    model_type: Optional[str]
    analysis_result: Optional[Dict[str, Any]]
    validation_result: Optional[Dict[str, Any]]
    slicing_result: Optional[Dict[str, Any]]
    iteration_id: Optional[str]
```

Sessions are held in-memory in a `SessionStore` dict. Multi-turn within one session is supported; cross-session persistence is out of scope for Phase 3.

## 3. Decision Rules (Explicit, Testable)

### Rule 1: Non-Watertight Auto-Repair
- **Trigger**: `analyze_model` returns `mesh_info.is_watertight == false`
- **Action**: Call `repair_model`, then `analyze_model` again
- **Max retries**: 1
- **Failure**: Report "Model could not be made watertight after repair attempt"

### Rule 2: Thin-Wall Auto-Adjust
- **Trigger**: `validate_model` reports wall thickness below `MIN_WALL_MM = 0.8` (2× nozzle diameter for 0.4mm nozzle)
- **Action**: Increase `wall_thickness_mm` by 1.0mm, regenerate with same category
- **Max retries**: 2
- **Failure**: Report "Wall thickness could not be brought to printable minimum"

### Rule 3: Excessive Print Time / Filament
- **Trigger**: `slice_model` reports `estimated_print_time_minutes > 240` (4h) OR `filament_used_g > 200`
- **Action**: Suggest scaling to 80% and ask user confirmation (do not auto-scale without consent)
- **No retry limit** — this is a user decision point, not a failure

### Rule 4: Low-Confidence Routing
- **Trigger**: `generate_from_description` routes to `ObjectCategory.CUSTOM` (no keywords matched)
- **Action**: Return clarifying question: "I couldn't determine the best model type. Did you mean: box, cylinder, tube_squeezer, bracket, enclosure, spacer, or hook?"
- **No retry** — waits for user clarification

## 4. Recovery Strategies

| Strategy | When Used | Max Retries | Fallback |
|----------|-----------|-------------|----------|
| repair-and-retry | Non-watertight mesh | 1 | Fail with trace |
| parameter-fallback | Thin walls, bad dimensions | 2 | Fail with trace |
| category-fallback | Generation fails with chosen category | 1 | Try `box` as generic fallback |

All recovery attempts are logged via `logging_config` and appended to the session's `recovery_actions` list.

## 5. New MCP Tool: `run_print_workflow`

**Input**: `goal: str` (natural language), optional `auto_repair: bool = True`, `max_print_time_minutes: int = 240`

**Output**: Structured execution trace:
```json
{
  "success": true,
  "trace": [
    {"step": "parse_requirements", "status": "ok", "output": {...}},
    {"step": "generate_model", "status": "ok", "output": {...}},
    {"step": "analyze_model", "status": "recovered", "recovery": "repair_model", "output": {...}}
  ],
  "final_model_path": "...",
  "final_gcode_path": "...",
  "iteration_id": "...",
  "session_id": "..."
}
```

If any step fails and recovery is exhausted, `success: false` with full `trace` and `error` explaining what was tried.

## 6. Files to Create / Modify

| File | Action |
|------|--------|
| `vibe_print/agent/__init__.py` | New package init |
| `vibe_print/agent/orchestrator.py` | New — WorkflowPlanner, WorkflowExecutor, SessionStore, decision rules |
| `vibe_print/agent/context.py` | New — AgentSession dataclass and session management |
| `vibe_print/server.py` | Add `run_print_workflow` tool + `RunPrintWorkflowInput` schema |
| `tests/test_agent.py` | New — End-to-end tests for clean, recovery, and honest-failure paths |
| `PHASE3_SUMMARY.md` | Final report |

## 7. Test Scenarios

1. **Clean path**: "make me a tube squeezer for a 65mm lotion bottle" → full workflow succeeds
2. **Recovery path**: Generate a model that is non-watertight (we'll simulate by creating a broken mesh) → agent repairs and succeeds
3. **Honest failure**: Engineer a scenario where repair fails twice → agent reports failure with full trace
