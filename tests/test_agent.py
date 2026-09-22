"""
Agent orchestration end-to-end tests.

Covers:
1. Clean path: full workflow from goal to print-ready
2. Recovery path: non-watertight model → auto-repair → success
3. Honest failure: repair exhausted → clear failure report
4. Low-confidence routing: CUSTOM category → clarification
5. run_print_workflow MCP tool integration
"""

import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import trimesh

from vibe_print.agent.orchestrator import (
    WorkflowPlanner,
    WorkflowExecutor,
    SessionStore,
    ExecutorConfig,
    MIN_WALL_MM,
)
from vibe_print.agent.context import AgentSession, StepStatus
from vibe_print.generator.cad_generator import ParametricGenerator
from vibe_print.models.analyzer import ModelAnalyzer
from vibe_print.iteration.tracker import IterationTracker


class TestCleanPath:
    """Scenario 1: Tube squeezer goal, no failures, full success."""

    def test_tube_squeezer_workflow(self):
        store = SessionStore()
        planner = WorkflowPlanner()
        executor = WorkflowExecutor()

        goal = "make me a tube squeezer for a 65mm lotion bottle"
        session = store.create(goal)
        session.plan = planner.plan(goal)

        result = executor.run(session)

        assert result["success"] is True
        assert result["goal"] == goal
        assert result["final_model_path"] is not None
        assert result["final_gcode_path"] is not None
        assert Path(result["final_model_path"]).exists()

        # Trace should show all steps OK
        trace = result["trace"]
        assert len(trace) == 6
        for step in trace:
            assert step["status"] == "ok"

        # No recovery actions on clean path
        assert result["recovery_actions"] == []

    def test_workflow_mcp_tool(self):
        """Test via the actual server tool function."""
        from vibe_print.server import run_print_workflow, RunPrintWorkflowInput

        inp = RunPrintWorkflowInput(
            goal="tube squeezer for 65mm lotion bottle",
            auto_repair=True,
            auto_adjust_params=True,
        )
        result = run_print_workflow(inp)

        assert result["success"] is True
        assert "trace" in result
        assert result["final_model_path"] is not None


class TestRecoveryPath:
    """Scenario 2: Non-watertight model → real auto-repair → success."""

    def test_repair_non_watertight_model(self, tmp_path):
        # Create a mesh with a hole (non-watertight) — real broken fixture
        box = trimesh.creation.box(extents=[10, 10, 10])
        box.faces = box.faces[:-1]
        broken_path = tmp_path / "broken.stl"
        box.export(broken_path)

        # Verify it's broken
        analyzer = ModelAnalyzer()
        analysis = analyzer.analyze(str(broken_path))
        assert analysis["mesh_info"]["is_watertight"] is False

        # Run workflow starting from analyze step by injecting the broken model
        store = SessionStore()
        planner = WorkflowPlanner()
        executor = WorkflowExecutor()

        # NO MONKEYPATCH — use the real _repair_mesh which calls trimesh.fill_holes()
        session = store.create("test broken model")
        session.plan = planner.plan("test broken model")
        session.model_path = str(broken_path)
        session.requirements = None  # Skip parse/generate

        # Jump to analyze step (index 2)
        session.current_step_index = 2
        result = executor.run(session)

        # Should recover and succeed via real trimesh repair
        assert result["success"] is True
        analyze_step = [s for s in result["trace"] if s["name"] == "analyze_model"][0]
        assert analyze_step["status"] == "recovered"
        assert analyze_step["recovery_action"] == "repair_model"
        assert len(result["recovery_actions"]) >= 1

        # Verify the repaired model file actually exists and is watertight
        repaired_path = Path(result["final_model_path"])
        assert repaired_path.exists()
        repaired_analysis = analyzer.analyze(str(repaired_path))
        assert repaired_analysis["mesh_info"]["is_watertight"] is True


class TestHonestFailure:
    """Scenario 3: Repair fails → agent reports failure clearly with what was tried."""

    def test_repair_fails_reports_failure(self, tmp_path):
        # Create a non-watertight mesh (open box)
        box = trimesh.creation.box(extents=[10, 10, 10])
        box.faces = box.faces[:-2]  # Remove two faces to create holes
        bad_path = tmp_path / "bad.stl"
        box.export(bad_path)

        store = SessionStore()
        planner = WorkflowPlanner()
        executor = WorkflowExecutor(config=ExecutorConfig(auto_repair=True))

        # Monkeypatch _repair_mesh to simulate a repair that doesn't fix watertightness
        original_repair = executor._repair_mesh
        def fake_repair(path):
            # Return a path but don't actually fix the mesh — copy the same broken mesh
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
        assert result["error"]["step"] == "analyze_model"
        assert "watertight" in str(result["error"]["message"]).lower() or "repair" in str(result).lower()

        # Must show recovery was attempted
        assert len(result["recovery_actions"]) >= 1
        assert any("repair_model" in str(r) for r in result["recovery_actions"])


class TestLowConfidenceRouting:
    """Scenario 4: CUSTOM category → workflow pauses for clarification."""

    def test_custom_category_asks_clarification(self):
        store = SessionStore()
        planner = WorkflowPlanner()
        executor = WorkflowExecutor()

        goal = "something weird and undefined"
        session = store.create(goal)
        session.plan = planner.plan(goal)

        result = executor.run(session)

        # Should stop at parse_requirements with needs_clarification
        assert result["success"] is False
        parse_step = result["trace"][0]
        assert parse_step["name"] == "parse_requirements"
        assert parse_step["status"] == "failed"
        assert "clarification" in str(result["messages"]).lower() or "couldn't determine" in str(result["messages"]).lower()


class TestDecisionRules:
    """Unit tests for individual decision rules."""

    def test_excessive_print_time_warning(self, tmp_path):
        """Decision Rule 3: Large model triggers print-time warning."""
        # Generate a box and monkeypatch the slicer to return excessive estimates
        gen = ParametricGenerator()
        large_path = gen.generate("box", {"width": 50, "height": 50, "depth": 50}, "large")

        store = SessionStore()
        planner = WorkflowPlanner()
        executor = WorkflowExecutor(
            config=ExecutorConfig(max_print_time_minutes=30, max_filament_g=50)
        )

        # Monkeypatch slicer to return high estimates
        class HighEstimateSlicer:
            async def slice_model(self, *args, **kwargs):
                from vibe_print.slicer.cli import SliceResult
                return SliceResult(
                    success=True,
                    input_model=large_path,
                    output_gcode=tmp_path / "test.gcode",
                    estimated_time_seconds=7200,  # 120 min
                    estimated_filament_grams=300,  # 300g
                )
        executor.slicer = HighEstimateSlicer()

        session = store.create("large box")
        session.plan = planner.plan("large box")
        session.model_path = str(large_path)
        session.requirements = None

        # Jump to slice step
        session.current_step_index = 4
        result = executor.run(session)

        assert result["success"] is True
        # Should have warning messages about print time or filament
        assert any("exceeds" in m for m in result["messages"])

    def test_category_fallback_on_generation_failure(self):
        """Category fallback recovery when generation fails."""
        store = SessionStore()
        planner = WorkflowPlanner()

        # Use a generator that will fail on first call
        class FailingGenerator:
            def generate_from_description(self, **kwargs):
                raise RuntimeError("Simulated generation failure")

            def generate(self, model_type, parameters, output_name=None):
                from pathlib import Path
                p = Path("fallback.stl")
                p.write_text("mock")
                return p

        executor = WorkflowExecutor(generator=FailingGenerator())

        session = store.create("something that fails")
        session.plan = planner.plan("something that fails")
        # Must set requirements so generate_model doesn't bail early
        from vibe_print.generator.requirements import RequirementsParser
        session.requirements = RequirementsParser().parse("a box")

        # Jump to generate step
        session.current_step_index = 1
        result = executor.run(session)

        # Should have attempted category fallback
        assert len(result["recovery_actions"]) >= 1
        assert any("category_fallback" in str(r) for r in result["recovery_actions"])


class TestMultiTurnContext:
    """Scenario 5: Follow-up instructions use stored session context."""

    def _get_dims_from_bounds(self, analysis: Dict[str, Any]) -> Dict[str, float]:
        """Compute dimensions from analyzer bounds_mm output."""
        bounds = analysis.get("mesh_info", {}).get("bounds_mm", [])
        if len(bounds) == 2:
            return {
                "width": bounds[1][0] - bounds[0][0],
                "height": bounds[1][1] - bounds[0][1],
                "depth": bounds[1][2] - bounds[0][2],
            }
        return {}

    def test_scale_follow_up_20_percent_bigger(self):
        """
        Turn 1: Generate a model.
        Turn 2: "make it 20% bigger" — should scale the SAME model using stored context.
        """
        store = SessionStore()
        planner = WorkflowPlanner()
        executor = WorkflowExecutor()

        # Turn 1: Initial workflow — use a goal that generates successfully
        goal = "make me a tube squeezer for a 65mm lotion bottle"
        session = store.create(goal)
        session.plan = planner.plan(goal)
        result = executor.run(session)

        assert result["success"] is True
        original_path = result["final_model_path"]
        assert original_path is not None
        assert Path(original_path).exists()

        # Get original dimensions from bounds
        analyzer = ModelAnalyzer()
        original_analysis = analyzer.analyze(original_path)
        original_dims = self._get_dims_from_bounds(original_analysis)
        assert original_dims, "Could not extract dimensions from analysis"

        # Turn 2: Follow-up instruction
        follow_up = "make it 20% bigger"
        follow_result = executor.handle_follow_up(session, follow_up)

        assert follow_result["success"] is True
        assert follow_result["action"] == "scale"
        assert follow_result["scale_factor"] == pytest.approx(1.2, rel=1e-3)

        # Verify new model path
        new_path = follow_result["new_model_path"]
        assert new_path is not None
        assert Path(new_path).exists()

        # Verify dimensions increased by ~1.2x
        new_analysis = analyzer.analyze(new_path)
        new_dims = self._get_dims_from_bounds(new_analysis)

        for axis in ["width", "height", "depth"]:
            if axis in original_dims and axis in new_dims:
                expected = original_dims[axis] * 1.2
                assert new_dims[axis] == pytest.approx(expected, rel=0.05)

        # Verify session was updated
        assert session.model_path == new_path
        assert session.analysis_result is not None

    def test_scale_follow_up_via_mcp_tool(self):
        """Test follow-up via the actual server MCP tool."""
        from vibe_print.server import run_print_workflow, handle_follow_up
        from vibe_print.server import RunPrintWorkflowInput, FollowUpInput

        # Turn 1: Run workflow
        inp = RunPrintWorkflowInput(goal="tube squeezer for 65mm lotion bottle")
        result = run_print_workflow(inp)
        assert result["success"] is True, f"Workflow failed: {result.get('error')}"
        session_id = result["session_id"]

        # Turn 2: Follow-up via MCP tool
        follow = FollowUpInput(session_id=session_id, instruction="scale it by 1.5x")
        follow_result = handle_follow_up(follow)

        assert follow_result["success"] is True, f"Follow-up failed: {follow_result.get('error')}"
        assert follow_result["action"] == "scale"
        assert follow_result["scale_factor"] == pytest.approx(1.5, rel=1e-3)
        assert Path(follow_result["new_model_path"]).exists()

    def test_unsupported_follow_up_pattern(self):
        """Unsupported follow-up returns clear error."""
        store = SessionStore()
        planner = WorkflowPlanner()
        executor = WorkflowExecutor()

        session = store.create("box")
        session.plan = planner.plan("box")
        # Generate a model first
        gen = ParametricGenerator()
        path = gen.generate("box", {"width": 10, "height": 10, "depth": 10}, "test")
        session.model_path = str(path)

        result = executor.handle_follow_up(session, "make it nicer")
        assert result["success"] is False
        assert "not understood" in result["error"]

    def test_follow_up_no_model_fails(self):
        """Follow-up without a model in session returns clear error."""
        store = SessionStore()
        executor = WorkflowExecutor()

        session = store.create("box")
        result = executor.handle_follow_up(session, "make it 20% bigger")
        assert result["success"] is False
        assert "No model available" in result["error"]


class TestSessionStore:
    """Unit tests for session management."""

    def test_create_and_retrieve_session(self):
        store = SessionStore()
        session = store.create("test goal")
        assert session.session_id is not None
        assert store.get(session.session_id) is session

    def test_delete_session(self):
        store = SessionStore()
        session = store.create("test goal")
        store.delete(session.session_id)
        assert store.get(session.session_id) is None

    def test_session_retry_tracking(self):
        session = AgentSession()
        assert session.get_retry_count("foo") == 0
        session.increment_retry("foo")
        assert session.get_retry_count("foo") == 1
        session.increment_retry("foo")
        assert session.get_retry_count("foo") == 2

    def test_session_recovery_recording(self):
        session = AgentSession()
        session.record_recovery("analyze", "repair", "success")
        assert len(session.recovery_actions) == 1
        assert session.recovery_actions[0]["step"] == "analyze"
