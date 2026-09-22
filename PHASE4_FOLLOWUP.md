# Phase 4 Follow-Up — Workflow vs. Step-Level Counting Bug Fix

## Root Cause (Confirmed in Code)

In `IterationTracker.get_print_analytics()`, the aggregation queries for `overall` and `by_category` were counting **rows** from `workflow_metrics` (which is step-level: 6 rows per workflow) instead of counting **distinct sessions** (workflows).

**Before (buggy):**

```sql
-- Overall: counted rows, not sessions
SELECT COUNT(DISTINCT session_id) as total_sessions,
       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_steps,  -- BUG: counts steps
       SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_steps       -- BUG: counts steps
FROM workflow_metrics

-- Per-category: counted rows, not sessions
SELECT category,
       COUNT(*) as total_runs,                                              -- BUG: counts steps
       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_runs,   -- BUG: counts steps
       SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_runs        -- BUG: counts steps
FROM workflow_metrics
GROUP BY category
```

This produced impossible numbers like `successful_workflows: 12` when only 3 workflows ran (2 successful × 6 steps = 12 successful step rows).

**After (fixed):**

```sql
-- Overall: count distinct sessions, classify by whether any step failed
WITH session_status AS (
    SELECT session_id,
           MAX(CASE WHEN success = 0 THEN 1 ELSE 0 END) as has_failure
    FROM workflow_metrics
    GROUP BY session_id
)
SELECT COUNT(*) as total_sessions,
       SUM(CASE WHEN has_failure = 0 THEN 1 ELSE 0 END) as successful_sessions,
       SUM(CASE WHEN has_failure = 1 THEN 1 ELSE 0 END) as failed_sessions
FROM session_status

-- Per-category: count distinct sessions per category
WITH category_session_status AS (
    SELECT category, session_id,
           MAX(CASE WHEN success = 0 THEN 1 ELSE 0 END) as has_failure
    FROM workflow_metrics
    GROUP BY category, session_id
)
SELECT category,
       COUNT(*) as total_sessions,
       SUM(CASE WHEN has_failure = 0 THEN 1 ELSE 0 END) as successful_sessions,
       SUM(CASE WHEN has_failure = 1 THEN 1 ELSE 0 END) as failed_sessions
FROM category_session_status
GROUP BY category
```

Recovery trigger count also fixed to use `COUNT(DISTINCT session_id)` instead of `COUNT(*)`.

## Corrected Real Output (from re-run)

Same scenario: 2 successful `tube_squeezer` workflows + 1 failed `custom` workflow.

```
Workflow 1: success=True
Workflow 2: success=True
Workflow 3: success=False

=== SUMMARY ===
Overall: 3 workflow(s), 67% step success rate. custom: 0% success rate over 1 run(s), most common issue: custom_category (1 occurrence(s)). tube_squeezer: 100% success rate over 2 run(s), avg 7.5 min slicing time.

=== STATS ===
{
  "overall": {
    "total_workflows": 3,
    "successful_workflows": 2,
    "failed_workflows": 1,
    "overall_success_rate": 0.667
  },
  "by_category": [
    {
      "category": "custom",
      "total_runs": 1,
      "successful_runs": 0,
      "failed_runs": 1,
      "success_rate": 0.0,
      "avg_slicing_time_est_min": null,
      "recovery_trigger_rate": 0.0,
      "most_common_failure": "custom_category",
      "most_common_failure_count": 1
    },
    {
      "category": "tube_squeezer",
      "total_runs": 2,
      "successful_runs": 2,
      "failed_runs": 0,
      "success_rate": 1.0,
      "avg_slicing_time_est_min": 7.5,
      "recovery_trigger_rate": 0.0,
      "most_common_failure": null,
      "most_common_failure_count": 0
    }
  ],
  "failure_ranking": [
    {
      "failure_type": "custom_category",
      "count": 1,
      "top_category": "custom"
    }
  ],
  "recovery_ranking": [],
  "step_latency": [
    {"step_name": "generate_model", "avg_duration_ms": 986.5, "count": 2},
    {"step_name": "analyze_model", "avg_duration_ms": 23.5, "count": 2},
    {"step_name": "validate_model", "avg_duration_ms": 22.0, "count": 2},
    {"step_name": "create_iteration", "avg_duration_ms": 10.5, "count": 2},
    {"step_name": "slice_model", "avg_duration_ms": 7.5, "count": 2},
    {"step_name": "parse_requirements", "avg_duration_ms": 6.3, "count": 3}
  ]
}
```

**Invariants now hold:**
- `successful_workflows + failed_workflows == total_workflows` → `2 + 1 == 3` ✓
- `by_category[].total_runs` sums to `total_workflows` → `1 + 2 == 3` ✓
- `step_latency[].count` correctly shows step-level counts (e.g., `parse_requirements: 3` for 3 workflows) ✓

## New Regression Test

Added `TestCountingInvariant.test_workflow_counts_invariant` in `tests/test_phase4_analytics.py`:

```python
class TestCountingInvariant:
    """Regression: workflow counts must be internally consistent."""

    def test_workflow_counts_invariant(self, tracker):
        """
        successful_workflows + failed_workflows must equal total_workflows
        at both overall and per-category level.
        """
        store = SessionStore()
        planner = WorkflowPlanner()
        executor = WorkflowExecutor(tracker=tracker)

        # Run 3 successful tube_squeezer workflows
        for _ in range(3):
            session = store.create("tube squeezer for 65mm bottle")
            session.plan = planner.plan("tube squeezer for 65mm bottle")
            result = executor.run(session)
            assert result["success"] is True

        # Run 1 failed custom workflow
        session = store.create("something weird")
        session.plan = planner.plan("something weird")
        result = executor.run(session)
        assert result["success"] is False

        metrics = asyncio.run(tracker.get_print_analytics())
        assert metrics["success"] is True
        stats = metrics["stats"]

        # Overall invariant
        overall = stats["overall"]
        assert overall["successful_workflows"] + overall["failed_workflows"] == overall["total_workflows"]
        assert overall["total_workflows"] == 4  # 3 successful + 1 failed

        # Per-category invariant
        category_totals = 0
        for cat in stats["by_category"]:
            assert cat["successful_runs"] + cat["failed_runs"] == cat["total_runs"]
            category_totals += cat["total_runs"]

        # Sum of category totals should equal total workflows
        assert category_totals == overall["total_workflows"]

        # Specific category checks
        tube = next(c for c in stats["by_category"] if c["category"] == "tube_squeezer")
        assert tube["total_runs"] == 3
        assert tube["successful_runs"] == 3
        assert tube["failed_runs"] == 0

        custom = next(c for c in stats["by_category"] if c["category"] == "custom")
        assert custom["total_runs"] == 1
        assert custom["successful_runs"] == 0
        assert custom["failed_runs"] == 1
```

**Test result:** `207 passed` (206 existing + 1 new regression test).

## Files Changed

| File | Change |
|------|--------|
| `vibe_print/iteration/tracker.py` | Fixed aggregation queries in `get_print_analytics()` to count distinct sessions instead of rows |
| `tests/test_phase4_analytics.py` | Added `TestCountingInvariant` regression test class |
| `PHASE4_SUMMARY.md` | Updated example output to reflect corrected numbers |

## What Was NOT Changed

- Schema (`workflow_metrics`, `failure_events`, `category_performance`) — unchanged
- Instrumentation points in `WorkflowExecutor` and MCP tools — unchanged
- Generation, CadQuery, routing, or agent decision/recovery logic — unchanged
