"""
Phase 4: Observability & Data — Analytics, metrics, and failure dataset tests.

Covers:
1. Metrics are recorded during workflow execution
2. Failure/recovery events are persisted durably
3. get_print_analytics returns real aggregates matching recorded data
4. Empty-state response when no data exists
5. Category performance tracking over time
"""

import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import trimesh

from vibe_print.agent.orchestrator import (
    WorkflowPlanner,
    WorkflowExecutor,
    SessionStore,
    ExecutorConfig,
)
from vibe_print.iteration.tracker import IterationTracker


@pytest.fixture
def tracker():
    """Provide a fresh tracker with temp database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        t = IterationTracker(db_path=db_path)
        asyncio.run(t.initialize())
        yield t


class TestMetricsRecording:
    """Verify that workflow steps record metrics to the tracker."""

    def test_clean_path_records_metrics(self, tracker):
        """A successful workflow should record metrics for each step."""
        store = SessionStore()
        planner = WorkflowPlanner()
        executor = WorkflowExecutor(tracker=tracker)

        goal = "make me a tube squeezer for a 65mm lotion bottle"
        session = store.create(goal)
        session.plan = planner.plan(goal)

        result = executor.run(session)
        assert result["success"] is True

        # Verify metrics were recorded
        metrics = asyncio.run(tracker.get_print_analytics())
        assert metrics["success"] is True
        assert metrics["stats"] is not None
        overall = metrics["stats"]["overall"]
        assert overall["total_workflows"] >= 1
        assert overall["successful_workflows"] >= 1

        # Should have step latency data
        latency = metrics["stats"]["step_latency"]
        step_names = {s["step_name"] for s in latency}
        assert "slice_model" in step_names or "create_iteration" in step_names

    def test_recovery_path_records_failure_event(self, tracker, tmp_path):
        """A recovery path should record both the failure and the recovery success."""
        # Create a mesh with a hole (non-watertight)
        box = trimesh.creation.box(extents=[10, 10, 10])
        box.faces = box.faces[:-1]
        broken_path = tmp_path / "broken.stl"
        box.export(broken_path)

        store = SessionStore()
        planner = WorkflowPlanner()
        executor = WorkflowExecutor(tracker=tracker)

        session = store.create("test broken model")
        session.plan = planner.plan("test broken model")
        session.model_path = str(broken_path)
        session.requirements = None
        session.current_step_index = 2

        result = executor.run(session)
        assert result["success"] is True

        # Verify failure event was recorded
        metrics = asyncio.run(tracker.get_print_analytics())
        assert metrics["stats"] is not None
        failure_ranking = metrics["stats"]["failure_ranking"]
        assert any(
            f["failure_type"] == "not_watertight" for f in failure_ranking
        ), f"Expected 'not_watertight' in failure ranking, got: {failure_ranking}"

        recovery_ranking = metrics["stats"]["recovery_ranking"]
        assert any(
            r["recovery_strategy"] == "repair_model" for r in recovery_ranking
        ), f"Expected 'repair_model' in recovery ranking, got: {recovery_ranking}"

    def test_honest_failure_records_failure_event(self, tracker, tmp_path):
        """A failed workflow should record the failure event."""
        box = trimesh.creation.box(extents=[10, 10, 10])
        box.faces = box.faces[:-2]
        bad_path = tmp_path / "bad.stl"
        box.export(bad_path)

        store = SessionStore()
        planner = WorkflowPlanner()
        executor = WorkflowExecutor(tracker=tracker, config=ExecutorConfig(auto_repair=True))

        # Monkeypatch _repair_mesh to simulate a repair that doesn't fix watertightness
        def fake_repair(path):
            out = Path(path).with_suffix(".repaired.stl")
            import shutil
            shutil.copy2(path, out)
            return out
        executor._repair_mesh = fake_repair

        session = store.create("unrepairable model")
        session.plan = planner.plan("unrepairable model")
        session.model_path = str(bad_path)
        session.requirements = None
        session.current_step_index = 2

        result = executor.run(session)
        assert result["success"] is False

        # Verify failure event was recorded with recovery_success=False
        metrics = asyncio.run(tracker.get_print_analytics())
        assert metrics["stats"] is not None
        recovery_ranking = metrics["stats"]["recovery_ranking"]
        repair_entry = next(
            (r for r in recovery_ranking if r["recovery_strategy"] == "repair_model"), None
        )
        assert repair_entry is not None
        assert repair_entry["success_rate"] == 0.0

    def test_custom_category_records_failure(self, tracker):
        """Low-confidence routing should record a custom_category failure."""
        store = SessionStore()
        planner = WorkflowPlanner()
        executor = WorkflowExecutor(tracker=tracker)

        goal = "something weird and undefined"
        session = store.create(goal)
        session.plan = planner.plan(goal)

        result = executor.run(session)
        assert result["success"] is False

        metrics = asyncio.run(tracker.get_print_analytics())
        assert metrics["stats"] is not None
        failure_ranking = metrics["stats"]["failure_ranking"]
        assert any(
            f["failure_type"] == "custom_category" for f in failure_ranking
        ), f"Expected 'custom_category' in failure ranking, got: {failure_ranking}"


class TestPrintAnalytics:
    """Verify get_print_analytics computes correct aggregates."""

    def test_analytics_matches_recorded_data(self, tracker):
        """Run multiple workflows and verify analytics numbers match."""
        store = SessionStore()
        planner = WorkflowPlanner()
        executor = WorkflowExecutor(tracker=tracker)

        # Run 2 successful workflows
        for _ in range(2):
            session = store.create("tube squeezer for 65mm bottle")
            session.plan = planner.plan("tube squeezer for 65mm bottle")
            result = executor.run(session)
            assert result["success"] is True

        # Run 1 failed workflow (custom category)
        session = store.create("something weird")
        session.plan = planner.plan("something weird")
        result = executor.run(session)
        assert result["success"] is False

        metrics = asyncio.run(tracker.get_print_analytics())
        assert metrics["success"] is True
        stats = metrics["stats"]

        # Overall: at least 3 workflows
        assert stats["overall"]["total_workflows"] >= 3

        # By category: tube_squeezer should have success_rate = 1.0
        tube_stats = next(
            (c for c in stats["by_category"] if c["category"] == "tube_squeezer"), None
        )
        assert tube_stats is not None
        assert tube_stats["successful_runs"] >= 2
        assert tube_stats["success_rate"] == 1.0

        # Summary string should be human-readable
        assert "tube_squeezer" in metrics["summary"]
        assert "%" in metrics["summary"] or "success rate" in metrics["summary"]

    def test_analytics_empty_state(self, tracker):
        """Fresh database should return clear empty-state response."""
        metrics = asyncio.run(tracker.get_print_analytics())
        assert metrics["success"] is True
        assert metrics["stats"] is None
        assert "No workflow data" in metrics["summary"]

    def test_analytics_date_filtering(self, tracker):
        """Date filters should correctly include/exclude data."""
        store = SessionStore()
        planner = WorkflowPlanner()
        executor = WorkflowExecutor(tracker=tracker)

        session = store.create("tube squeezer for 65mm bottle")
        session.plan = planner.plan("tube squeezer for 65mm bottle")
        executor.run(session)

        # Filter with future date range — should be empty
        future = (datetime.now() + timedelta(days=1)).isoformat()
        far_future = (datetime.now() + timedelta(days=2)).isoformat()
        metrics = asyncio.run(tracker.get_print_analytics(date_from=future, date_to=far_future))
        assert metrics["stats"] is None or metrics["stats"]["overall"]["total_workflows"] == 0

        # Filter with past date range — should include data
        past = (datetime.now() - timedelta(days=1)).isoformat()
        metrics = asyncio.run(tracker.get_print_analytics(date_from=past))
        assert metrics["stats"] is not None
        assert metrics["stats"]["overall"]["total_workflows"] >= 1

    def test_analytics_category_filter(self, tracker):
        """Category filter should narrow results to that category."""
        store = SessionStore()
        planner = WorkflowPlanner()
        executor = WorkflowExecutor(tracker=tracker)

        # Run tube_squeezer workflow
        session = store.create("tube squeezer for 65mm bottle")
        session.plan = planner.plan("tube squeezer for 65mm bottle")
        executor.run(session)

        # Filter by tube_squeezer
        metrics = asyncio.run(tracker.get_print_analytics(category="tube_squeezer"))
        assert metrics["stats"] is not None
        assert any(c["category"] == "tube_squeezer" for c in metrics["stats"]["by_category"])

        # Filter by non-existent category
        metrics = asyncio.run(tracker.get_print_analytics(category="nonexistent"))
        assert metrics["stats"] is None or metrics["stats"]["overall"]["total_workflows"] == 0


class TestCategoryPerformance:
    """Verify category_performance cache is updated correctly."""

    def test_category_performance_aggregates(self, tracker):
        """Multiple runs should update category performance aggregates."""
        store = SessionStore()
        planner = WorkflowPlanner()
        executor = WorkflowExecutor(tracker=tracker)

        # Run 3 successful tube_squeezer workflows
        for _ in range(3):
            session = store.create("tube squeezer for 65mm bottle")
            session.plan = planner.plan("tube squeezer for 65mm bottle")
            result = executor.run(session)
            assert result["success"] is True

        # Check category_performance table directly
        async def check():
            import aiosqlite
            async with aiosqlite.connect(tracker.db_path) as db:
                async with db.execute(
                    "SELECT total_runs, successful_runs, failed_runs FROM category_performance WHERE category = ?",
                    ("tube_squeezer",),
                ) as cursor:
                    row = await cursor.fetchone()
                    assert row is not None
                    assert row[0] == 3  # total_runs
                    assert row[1] == 3  # successful_runs
                    assert row[2] == 0  # failed_runs

        asyncio.run(check())

    def test_category_performance_with_recovery(self, tracker, tmp_path):
        """Recovery triggers should increment recovery count."""
        box = trimesh.creation.box(extents=[10, 10, 10])
        box.faces = box.faces[:-1]
        broken_path = tmp_path / "broken.stl"
        box.export(broken_path)

        store = SessionStore()
        planner = WorkflowPlanner()
        executor = WorkflowExecutor(tracker=tracker)

        session = store.create("test broken model")
        session.plan = planner.plan("test broken model")
        session.model_path = str(broken_path)
        # Set requirements with a known category so category_performance is updated
        from vibe_print.generator.requirements import RequirementsParser
        session.requirements = RequirementsParser().parse("a box")
        session.current_step_index = 2

        result = executor.run(session)
        assert result["success"] is True

        # Check recovery trigger count
        async def check():
            import aiosqlite
            async with aiosqlite.connect(tracker.db_path) as db:
                async with db.execute(
                    "SELECT total_recovery_triggers FROM category_performance WHERE category = ?",
                    ("box",),
                ) as cursor:
                    row = await cursor.fetchone()
                    assert row is not None
                    assert row[0] >= 1

        asyncio.run(check())


class TestMCPAnalyticsTool:
    """Verify get_print_analytics MCP tool integration."""

    def test_mcp_tool_empty_state(self, tracker):
        """MCP tool should return empty state for fresh database."""
        from vibe_print.server import get_print_analytics, GetPrintAnalyticsInput

        # Temporarily override the server's tracker
        from vibe_print import server as server_mod
        original_tracker = server_mod._tracker
        server_mod._tracker = tracker

        try:
            inp = GetPrintAnalyticsInput()
            result = get_print_analytics(inp)
            assert result["success"] is True
            assert result["stats"] is None
            assert "No workflow data" in result["summary"]
        finally:
            server_mod._tracker = original_tracker

    def test_mcp_tool_with_data(self, tracker):
        """MCP tool should return real analytics after workflows run."""
        from vibe_print.server import (
            get_print_analytics, GetPrintAnalyticsInput,
            run_print_workflow, RunPrintWorkflowInput,
        )
        from vibe_print import server as server_mod

        original_tracker = server_mod._tracker
        original_store = server_mod._agent_store
        original_planner = server_mod._agent_planner
        original_executor = server_mod._agent_executor
        server_mod._tracker = tracker
        server_mod._agent_store = None
        server_mod._agent_planner = None
        server_mod._agent_executor = None

        try:
            # Run a workflow
            inp = RunPrintWorkflowInput(goal="tube squeezer for 65mm lotion bottle")
            wf_result = run_print_workflow(inp)
            assert wf_result["success"] is True

            # Query analytics
            analytics = get_print_analytics(GetPrintAnalyticsInput())
            assert analytics["success"] is True
            assert analytics["stats"] is not None
            assert analytics["stats"]["overall"]["total_workflows"] >= 1
            assert "tube_squeezer" in analytics["summary"]
        finally:
            server_mod._tracker = original_tracker
            server_mod._agent_store = original_store
            server_mod._agent_planner = original_planner
            server_mod._agent_executor = original_executor


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
