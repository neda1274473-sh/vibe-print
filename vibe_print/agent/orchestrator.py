"""
Agent Orchestrator — Multi-step workflow planning, execution, and recovery.

Calls existing library modules directly; does NOT reimplement generation,
slicing, or analysis logic. All decision rules are explicit, testable code.
"""

import asyncio
import concurrent.futures
import json
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from vibe_print.agent.context import AgentSession, WorkflowStep, StepStatus
from vibe_print.exceptions import VibePrintError
from vibe_print.logging_config import get_logger
from vibe_print.generator.requirements import RequirementsParser, ObjectCategory
from vibe_print.generator.cad_generator import ParametricGenerator
from vibe_print.models.analyzer import ModelAnalyzer
from vibe_print.models.scaler import ModelScaler
from vibe_print.slicer.cli import get_slicer_cli, MockSlicerCLI
from vibe_print.slicer.parameters import SlicingParameters
from vibe_print.iteration.tracker import IterationTracker

logger = get_logger(__name__)


def _run_async(coro):
    """Safely run an async coroutine from either sync or async context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Decision-rule thresholds — explicit, documented, testable
# ---------------------------------------------------------------------------

MIN_WALL_MM = 0.8          # 2 × 0.4mm nozzle; below this = auto-adjust
MAX_PRINT_TIME_MIN = 240   # 4 hours; above this = suggest scale-down
MAX_FILAMENT_G = 200       # 200g; above this = suggest scale-down
REPAIR_MAX_RETRIES = 1
PARAM_ADJUST_MAX_RETRIES = 2
CATEGORY_FALLBACK_MAX_RETRIES = 1


# ---------------------------------------------------------------------------
# Session store
# ---------------------------------------------------------------------------

class SessionStore:
    """Persistent store for agent sessions backed by SQLite."""

    def __init__(self, tracker: Optional[IterationTracker] = None):
        self.tracker = tracker
        self._cache: Dict[str, AgentSession] = {}

    def create(self, goal: str, user_id: str = "default") -> AgentSession:
        session = AgentSession(goal=goal, user_id=user_id)
        self._cache[session.session_id] = session
        if self.tracker:
            _run_async(self.tracker.create_session(
                session_id=session.session_id,
                goal=goal,
                user_id=user_id,
                data=session.to_dict(),
            ))
        logger.info("Created agent session %s for goal: %s", session.session_id, goal)
        return session

    def get(self, session_id: str, user_id: str = "default") -> Optional[AgentSession]:
        # Check cache first
        if session_id in self._cache:
            s = self._cache[session_id]
            if s.user_id == user_id:
                return s
            return None
        # Load from persistent store
        if self.tracker:
            row = _run_async(self.tracker.get_session(session_id, user_id))
            if row:
                session = self._hydrate_session(row)
                self._cache[session_id] = session
                return session
        return None

    def delete(self, session_id: str, user_id: str = "default") -> None:
        self._cache.pop(session_id, None)
        if self.tracker:
            _run_async(self.tracker.delete_session(session_id, user_id))

    def list_active(self, user_id: str = "default") -> List[AgentSession]:
        """List active sessions for a user."""
        if self.tracker:
            rows = _run_async(self.tracker.list_sessions(user_id=user_id, status="active"))
            return [self._hydrate_session(r) for r in rows]
        return [s for s in self._cache.values() if s.user_id == user_id and s.status == "active"]

    def _hydrate_session(self, row: Dict[str, Any]) -> AgentSession:
        """Reconstruct AgentSession from DB row."""
        data = json.loads(row.get("data", "{}"))
        session = AgentSession(
            session_id=row["session_id"],
            user_id=row["user_id"],
            goal=row["goal"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            current_step_index=row.get("current_step_index", 0),
            model_path=row.get("model_path"),
            model_type=row.get("model_type"),
            iteration_id=row.get("iteration_id"),
        )
        # Restore plan, messages, recovery_actions from data
        if "plan" in data:
            session.plan = [
                WorkflowStep(
                    name=s["name"],
                    description=s["description"],
                    status=StepStatus(s.get("status", "pending")),
                    output=s.get("output"),
                    error=s.get("error"),
                    recovery_action=s.get("recovery_action"),
                    started_at=datetime.fromisoformat(s["started_at"]) if s.get("started_at") else None,
                    completed_at=datetime.fromisoformat(s["completed_at"]) if s.get("completed_at") else None,
                )
                for s in data["plan"]
            ]
        session.messages = data.get("messages", [])
        session.recovery_actions = data.get("recovery_actions", [])
        session.retry_counts = data.get("retry_counts", {})
        return session

    def _persist_session(self, session: AgentSession) -> None:
        """Persist session state to DB."""
        if self.tracker:
            asyncio.run(self.tracker.update_session(
                session_id=session.session_id,
                user_id=session.user_id,
                data=session.to_dict(),
                status=getattr(session, "status", "active"),
                current_step_index=session.current_step_index,
                model_path=session.model_path,
                model_type=session.model_type,
                iteration_id=session.iteration_id,
            ))


# ---------------------------------------------------------------------------
# Workflow planner
# ---------------------------------------------------------------------------

class WorkflowPlanner:
    """
    Builds a deterministic plan for a given goal.

    The plan is a sequence of WorkflowSteps with decision points encoded
    as conditional logic inside the executor, not as branching plan nodes.
    """

    DEFAULT_PLAN = [
        ("parse_requirements", "Parse natural language into structured requirements"),
        ("generate_model", "Generate 3D model from requirements"),
        ("analyze_model", "Analyze geometry: dimensions, volume, watertightness"),
        ("validate_model", "Validate printability: walls, overhangs, fit"),
        ("slice_model", "Slice to G-code / 3MF with quality profile"),
        ("create_iteration", "Record print-ready iteration in tracker"),
    ]

    def plan(self, goal: str) -> List[WorkflowStep]:
        """Create a workflow plan for the given goal."""
        steps = [
            WorkflowStep(name=name, description=desc)
            for name, desc in self.DEFAULT_PLAN
        ]
        logger.info("Planned %d steps for goal: %s", len(steps), goal)
        return steps


# ---------------------------------------------------------------------------
# Workflow executor
# ---------------------------------------------------------------------------

@dataclass
class ExecutorConfig:
    """Runtime configuration for the executor."""
    auto_repair: bool = True
    auto_adjust_params: bool = True
    max_print_time_minutes: int = MAX_PRINT_TIME_MIN
    max_filament_g: int = MAX_FILAMENT_G


class WorkflowExecutor:
    """
    Executes a workflow plan step by step, applying decision rules and recovery.

    Each step method receives the session and returns (success: bool, output: dict).
    On failure, recovery strategies are attempted with bounded retries.
    """

    def __init__(
        self,
        generator: Optional[ParametricGenerator] = None,
        analyzer: Optional[ModelAnalyzer] = None,
        scaler: Optional[ModelScaler] = None,
        tracker: Optional[IterationTracker] = None,
        config: Optional[ExecutorConfig] = None,
    ):
        self.generator = generator or ParametricGenerator()
        self.analyzer = analyzer or ModelAnalyzer()
        self.scaler = scaler or ModelScaler()
        self.tracker = tracker
        self.cfg = config or ExecutorConfig()
        self.slicer = get_slicer_cli()

    # ------------------------------------------------------------------
    # Metrics helpers
    # ------------------------------------------------------------------

    def _record_step_metric(
        self,
        session: AgentSession,
        step: WorkflowStep,
        ok: bool,
        output: Dict[str, Any],
        decision_rule: Optional[str] = None,
        recovery_strategy: Optional[str] = None,
        recovery_success: Optional[bool] = None,
    ) -> None:
        """Persist step metric to tracker if available."""
        if self.tracker is None:
            return

        category = None
        if session.requirements:
            category = session.requirements.category.value

        metadata: Dict[str, Any] = {}
        if step.name == "slice_model" and isinstance(output, dict):
            metadata["print_time_min"] = output.get("estimated_time_minutes")
            metadata["filament_g"] = output.get("estimated_filament_grams")
        if step.name == "analyze_model" and isinstance(output, dict):
            mesh_info = output.get("mesh_info", {})
            metadata["is_watertight"] = mesh_info.get("is_watertight")

        try:
            asyncio.run(self.tracker.record_metric(
                step_name=step.name,
                success=ok,
                started_at=step.started_at or datetime.now(),
                completed_at=step.completed_at or datetime.now(),
                session_id=session.session_id,
                iteration_id=session.iteration_id,
                category=category,
                error_message=step.error if isinstance(step.error, str) else None,
                decision_rule=decision_rule,
                recovery_strategy=recovery_strategy or step.recovery_action,
                recovery_success=recovery_success,
                metadata=metadata if metadata else None,
                user_id=session.user_id,
            ))
        except Exception as e:
            logger.warning("Failed to record step metric: %s", e)

    def _record_failure_event(
        self,
        session: AgentSession,
        step_name: str,
        failure_type: str,
        recovery_strategy: Optional[str] = None,
        recovery_success: Optional[bool] = None,
        retry_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist failure/recovery event to tracker if available."""
        if self.tracker is None:
            return

        category = None
        if session.requirements:
            category = session.requirements.category.value

        try:
            asyncio.run(self.tracker.record_failure(
                step_name=step_name,
                failure_type=failure_type,
                session_id=session.session_id,
                category=category,
                recovery_strategy=recovery_strategy,
                recovery_success=recovery_success,
                retry_count=retry_count,
                metadata=metadata,
                user_id=session.user_id,
            ))
        except Exception as e:
            logger.warning("Failed to record failure event: %s", e)

    def _update_category_perf(self, session: AgentSession, success: bool) -> None:
        """Update cached category performance after workflow completes."""
        if self.tracker is None or session.requirements is None:
            return

        category = session.requirements.category.value
        recovery_triggered = any(
            r.get("strategy") for r in session.recovery_actions
        )
        slicing_time = None
        if session.slicing_result:
            slicing_time = session.slicing_result.get("estimated_time_minutes")

        try:
            asyncio.run(self.tracker.update_category_performance(
                category=category,
                success=success,
                recovery_triggered=recovery_triggered,
                slicing_time_est_min=slicing_time,
            ))
        except Exception as e:
            logger.warning("Failed to update category performance: %s", e)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self, session: AgentSession) -> Dict[str, Any]:
        """Execute the session's plan to completion or failure."""
        logger.info("Starting workflow execution for session %s", session.session_id)

        while session.current_step_index < len(session.plan):
            step = session.current_step()
            if step is None:
                break

            step.status = StepStatus.RUNNING
            step.started_at = datetime.now()
            logger.info("Step %d/%d: %s", session.current_step_index + 1, len(session.plan), step.name)

            handler = getattr(self, f"_step_{step.name}", None)
            if handler is None:
                step.status = StepStatus.FAILED
                step.error = f"No handler for step '{step.name}'"
                step.completed_at = datetime.now()
                self._record_step_metric(session, step, False, {}, decision_rule="missing_handler")
                self._record_failure_event(session, step.name, "missing_handler")
                break

            try:
                ok, output = handler(session)
                step.output = output
                if ok:
                    # Don't overwrite a recovery status set by the handler
                    if step.status != StepStatus.RECOVERED:
                        step.status = StepStatus.OK
                else:
                    # Recovery was attempted inside handler; check if we should continue
                    if step.status not in (StepStatus.RECOVERED, StepStatus.NEEDS_CLARIFICATION):
                        step.status = StepStatus.FAILED
            except Exception as e:
                logger.exception("Step %s failed with exception", step.name)
                step.status = StepStatus.FAILED
                step.error = str(e)
                if isinstance(e, VibePrintError):
                    step.error = e.to_dict()

            step.completed_at = datetime.now()

            # Record metric for this step
            self._record_step_metric(
                session, step,
                ok=(step.status in (StepStatus.OK, StepStatus.RECOVERED)),
                output=step.output or {},
            )

            if step.status == StepStatus.FAILED:
                logger.warning("Workflow halted at step %s", step.name)
                break
            if step.status == StepStatus.NEEDS_CLARIFICATION:
                logger.info("Workflow paused for clarification at step %s", step.name)
                break

            session.current_step_index += 1

        result = self._build_result(session)
        self._update_category_perf(session, result["success"])
        return result

    def _build_result(self, session: AgentSession) -> Dict[str, Any]:
        """Build the final structured result."""
        failed_step = None
        for s in session.plan:
            if s.status == StepStatus.FAILED:
                failed_step = s
                break

        success = failed_step is None and session.current_step_index >= len(session.plan)

        result: Dict[str, Any] = {
            "success": success,
            "session_id": session.session_id,
            "goal": session.goal,
            "trace": [s.to_dict() for s in session.plan],
            "recovery_actions": session.recovery_actions,
            "messages": session.messages,
        }

        if success:
            result["final_model_path"] = session.model_path
            gcode = None
            if session.slicing_result:
                gcode = session.slicing_result.get("output_gcode") or session.slicing_result.get("gcode_path")
            result["final_gcode_path"] = gcode
            result["iteration_id"] = session.iteration_id
        else:
            if failed_step:
                result["error"] = {
                    "step": failed_step.name,
                    "message": failed_step.error,
                }
            else:
                result["error"] = {"message": "Workflow incomplete"}

        logger.info("Workflow result for session %s: success=%s", session.session_id, success)
        return result

    # ------------------------------------------------------------------
    # Step handlers
    # ------------------------------------------------------------------

    def _step_parse_requirements(self, session: AgentSession) -> tuple[bool, Dict[str, Any]]:
        """Parse the user's goal into structured requirements."""
        parser = RequirementsParser()
        requirements = parser.parse(session.goal)
        session.requirements = requirements

        output = {
            "category": requirements.category.value,
            "primary_dimension_mm": requirements.get_primary_dimension_mm(),
            "wall_thickness_mm": requirements.wall_thickness_mm,
        }

        # Decision Rule 4: Low-confidence routing
        if requirements.category == ObjectCategory.CUSTOM:
            session.add_message(
                "I couldn't determine the best model type from your description. "
                "Did you mean: box, cylinder, tube_squeezer, bracket, enclosure, spacer, or hook?"
            )
            self._record_failure_event(
                session, "parse_requirements", "custom_category",
                recovery_strategy=None, recovery_success=None,
            )
            return False, output

        return True, output

    def _step_generate_model(self, session: AgentSession) -> tuple[bool, Dict[str, Any]]:
        """Generate the 3D model from parsed requirements."""
        req = session.requirements
        if req is None:
            return False, {"error": "No requirements parsed"}

        try:
            result = self.generator.generate_from_description(
                description=session.goal,
                material="PLA",
                nozzle_diameter=0.4,
            )
        except Exception as e:
            # Category fallback recovery
            retries = session.increment_retry("generate_model")
            self._record_failure_event(
                session, "generate_model", "generation_failed",
                recovery_strategy="category_fallback", recovery_success=None,
                retry_count=retries,
            )
            if retries <= CATEGORY_FALLBACK_MAX_RETRIES:
                session.record_recovery("generate_model", "category_fallback", "retrying with box")
                logger.warning("Generation failed, falling back to box (retry %d)", retries)
                result = self.generator.generate("box", {"width": 50, "height": 30, "depth": 40}, "fallback")
                session.model_path = str(result)
                session.model_type = "box"
                self._record_failure_event(
                    session, "generate_model", "generation_failed",
                    recovery_strategy="category_fallback", recovery_success=True,
                    retry_count=retries,
                )
                return True, {"model_path": session.model_path, "model_type": "box", "recovery": "category_fallback"}
            self._record_failure_event(
                session, "generate_model", "generation_failed",
                recovery_strategy="category_fallback", recovery_success=False,
                retry_count=retries,
            )
            return False, {"error": str(e)}

        session.model_path = result["model_path"]
        session.model_type = result["model_type"]
        return True, result

    # ------------------------------------------------------------------
    # Multi-turn follow-up handling
    # ------------------------------------------------------------------

    def handle_follow_up(self, session: AgentSession, instruction: str) -> Dict[str, Any]:
        """
        Process a follow-up instruction in the context of an existing session.

        Supports narrow patterns (explicitly documented):
        - "make it X% bigger" / "scale up by X%"
        - "make it X% smaller" / "scale down by X%"
        - "scale it by N.Nx" / "scale by N.N"

        Does NOT support general conversational context (e.g. "make it nicer").
        """
        action, params = self._parse_follow_up(instruction)

        if action == "scale":
            return self._execute_scale_follow_up(session, params)

        return {
            "success": False,
            "error": (
                f"Follow-up instruction not understood: '{instruction}'. "
                "Supported patterns: 'make it X% bigger/smaller', 'scale by N.Nx'."
            ),
        }

    def _parse_follow_up(self, instruction: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse a follow-up instruction into (action, params).

        Returns ("scale", {"scale_factor": float}) for scale instructions.
        Returns ("unknown", {}) for anything else.
        """
        text = instruction.lower().strip()

        # Pattern: "make it X% bigger" / "scale up by X%"
        pct_bigger = re.search(r"(?:make it |scale up by )(\d+(?:\.\d+)?)%? bigger", text)
        if pct_bigger:
            pct = float(pct_bigger.group(1))
            return "scale", {"scale_factor": 1.0 + pct / 100.0}

        # Pattern: "make it X% smaller" / "scale down by X%"
        pct_smaller = re.search(r"(?:make it |scale down by )(\d+(?:\.\d+)?)%? smaller", text)
        if pct_smaller:
            pct = float(pct_smaller.group(1))
            return "scale", {"scale_factor": 1.0 - pct / 100.0}

        # Pattern: "scale it by N.Nx" / "scale by N.N"
        scale_by = re.search(r"scale (?:it )?by (\d+(?:\.\d+)?)x?", text)
        if scale_by:
            return "scale", {"scale_factor": float(scale_by.group(1))}

        # Pattern: "scale up by 1.5x"
        scale_up = re.search(r"scale up by (\d+(?:\.\d+)?)x?", text)
        if scale_up:
            return "scale", {"scale_factor": float(scale_up.group(1))}

        return "unknown", {}

    def _execute_scale_follow_up(
        self, session: AgentSession, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a scale follow-up using the stored model context."""
        if not session.model_path:
            return {
                "success": False,
                "error": "No model available in session to scale. Generate a model first.",
            }

        scale_factor = params["scale_factor"]
        if scale_factor <= 0:
            return {"success": False, "error": "Scale factor must be positive."}

        # Get original dimensions from stored analysis
        original_dims = None
        if session.analysis_result:
            original_dims = session.analysis_result.get("mesh_info", {}).get("dimensions_mm")

        try:
            scaled_path = self.scaler.scale_model(
                model_path=session.model_path,
                scale_factor=scale_factor,
            )
        except Exception as e:
            return {"success": False, "error": f"Scaling failed: {e}"}

        # Analyze the scaled model
        analysis = self.analyzer.analyze(str(scaled_path))
        session.model_path = str(scaled_path)
        session.analysis_result = analysis

        new_dims = analysis.get("mesh_info", {}).get("dimensions_mm", {})

        result: Dict[str, Any] = {
            "success": True,
            "action": "scale",
            "scale_factor": scale_factor,
            "new_model_path": str(scaled_path),
            "new_dimensions_mm": new_dims,
        }

        if original_dims:
            result["original_dimensions_mm"] = original_dims

        session.add_message(
            f"Model scaled by {scale_factor:.2f}x. "
            f"New dimensions: {new_dims}."
        )
        return result

    def _step_validate_model(self, session: AgentSession) -> tuple[bool, Dict[str, Any]]:
        """Validate printability. Auto-adjust parameters if walls are too thin."""
        if not session.model_path:
            return False, {"error": "No model path"}

        result = self.analyzer.analyze(session.model_path)
        session.validation_result = result

        mesh_info = result.get("mesh_info", {})
        issues: List[str] = []

        # Check watertightness
        if not mesh_info.get("is_watertight", False):
            issues.append("Model is not watertight")

        # Check volume
        vol = mesh_info.get("volume_cm3")
        if vol is None or vol <= 0:
            issues.append("Model has zero or negative volume")

        # Decision Rule 2: Thin-wall auto-adjust
        # We infer wall thickness from the smallest bounding-box dimension
        # relative to the overall size as a heuristic.
        dims = mesh_info.get("dimensions_mm", {})
        min_dim = min(dims.values()) if dims else 0
        if min_dim > 0 and min_dim < MIN_WALL_MM:
            retries = session.increment_retry("validate_model")
            if retries <= PARAM_ADJUST_MAX_RETRIES and self.cfg.auto_adjust_params:
                session.record_recovery("validate_model", "parameter_adjust", f"increasing wall thickness (retry {retries})")
                logger.warning("Thin walls detected (min_dim=%.2fmm), adjusting parameters (retry %d)", min_dim, retries)

                # Regenerate with thicker walls
                if session.requirements:
                    session.requirements.wall_thickness_mm += 1.0
                    try:
                        result = self.generator.generate_from_description(
                            description=session.goal,
                            material="PLA",
                            nozzle_diameter=0.4,
                        )
                        session.model_path = result["model_path"]
                        session.model_type = result["model_type"]
                        # Re-analyze
                        result = self.analyzer.analyze(session.model_path)
                        session.validation_result = result
                        mesh_info = result.get("mesh_info", {})
                        dims = mesh_info.get("dimensions_mm", {})
                        min_dim = min(dims.values()) if dims else 0
                        if min_dim >= MIN_WALL_MM:
                            session.plan[session.current_step_index].status = StepStatus.RECOVERED
                            session.plan[session.current_step_index].recovery_action = "parameter_adjust"
                            session.add_message(f"Wall thickness increased to {session.requirements.wall_thickness_mm:.1f}mm and model regenerated.")
                            return True, result
                    except Exception as e:
                        issues.append(f"Regeneration failed: {e}")

            issues.append(f"Wall thickness below printable minimum ({MIN_WALL_MM}mm) after {retries} adjustment(s)")

        valid = len(issues) == 0
        output = {"valid": valid, "issues": issues, "analysis": result}
        if not valid:
            session.add_message("Validation issues: " + "; ".join(issues))
            return False, output
        return True, output

    def _step_slice_model(self, session: AgentSession) -> tuple[bool, Dict[str, Any]]:
        """Slice the model. Warn if print time or filament is excessive."""
        if not session.model_path:
            return False, {"error": "No model path"}

        layer_height = 0.20  # standard quality
        params = SlicingParameters(layer_height=layer_height)

        try:
            result = asyncio.run(self.slicer.slice_model(
                Path(session.model_path),
                params,
                export_gcode=True,
                export_3mf=True,
            ))
        except Exception as e:
            return False, {"error": str(e)}

        result_dict = result.to_dict() if hasattr(result, "to_dict") else result
        result_dict["mode"] = "MOCK" if isinstance(self.slicer, MockSlicerCLI) else "REAL"
        session.slicing_result = result_dict

        # Decision Rule 3: Excessive print time / filament
        print_time = result_dict.get("estimated_time_minutes", 0) or 0
        filament_g = result_dict.get("estimated_filament_grams", 0) or 0

        if print_time > self.cfg.max_print_time_minutes:
            session.add_message(
                f"Estimated print time ({print_time:.0f} min) exceeds threshold "
                f"({self.cfg.max_print_time_minutes} min). Consider scaling down the model."
            )
        if filament_g > self.cfg.max_filament_g:
            session.add_message(
                f"Estimated filament use ({filament_g:.0f}g) exceeds threshold "
                f"({self.cfg.max_filament_g}g). Consider scaling down the model."
            )

        return True, result_dict

    def _step_create_iteration(self, session: AgentSession) -> tuple[bool, Dict[str, Any]]:
        """Record a print-ready iteration in the tracker."""
        if not session.model_path:
            return False, {"error": "No model path"}

        if self.tracker is None:
            # Tracker not available — skip but don't fail
            session.add_message("Iteration tracker not available; skipping persistence.")
            return True, {"skipped": True, "reason": "tracker_not_configured"}

        try:
            iteration = asyncio.run(self.tracker.create_iteration(
                model_name=session.requirements.name if session.requirements else "unknown",
                model_path=session.model_path,
                scale_factor=1.0,
                preset_name="standard",
            ))
            session.iteration_id = iteration.iteration_id
            return True, {"iteration_id": iteration.iteration_id}
        except Exception as e:
            return False, {"error": str(e)}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _repair_mesh(self, model_path: str) -> Optional[Path]:
        """Attempt to repair a non-manifold mesh. Returns path to repaired file or None."""
        try:
            import trimesh
            mesh = trimesh.load(model_path, force="mesh")
            if hasattr(mesh, "fill_holes"):
                mesh.fill_holes()
            out = Path(model_path).with_suffix(".repaired.stl")
            mesh.export(out)
            return out
        except Exception as e:
            logger.warning("Mesh repair failed: %s", e)
            return None

    def _step_analyze_model(self, session: AgentSession) -> tuple[bool, Dict[str, Any]]:
        """Analyze the generated model. Auto-repair if not watertight."""
        if not session.model_path:
            return False, {"error": "No model path"}

        result = self.analyzer.analyze(session.model_path)
        session.analysis_result = result

        mesh_info = result.get("mesh_info", {})
        is_watertight = mesh_info.get("is_watertight", False)

        # Decision Rule 1: Non-watertight auto-repair
        if not is_watertight and self.cfg.auto_repair:
            retries = session.increment_retry("analyze_model")
            self._record_failure_event(
                session, "analyze_model", "not_watertight",
                recovery_strategy="repair_model", recovery_success=None,
                retry_count=retries,
            )
            if retries <= REPAIR_MAX_RETRIES:
                session.record_recovery("analyze_model", "repair_model", "attempting repair")
                logger.warning("Model not watertight, attempting repair (retry %d)", retries)

                repaired_path = self._repair_mesh(session.model_path)
                if repaired_path:
                    # Re-analyze the repaired model
                    result = self.analyzer.analyze(str(repaired_path))
                    session.analysis_result = result
                    mesh_info = result.get("mesh_info", {})
                    is_watertight = mesh_info.get("is_watertight", False)

                    if is_watertight:
                        session.model_path = str(repaired_path)
                        session.plan[session.current_step_index].status = StepStatus.RECOVERED
                        session.plan[session.current_step_index].recovery_action = "repair_model"
                        session.add_message("Model was repaired and is now watertight.")
                        self._record_failure_event(
                            session, "analyze_model", "not_watertight",
                            recovery_strategy="repair_model", recovery_success=True,
                            retry_count=retries,
                        )
                        return True, result
                    else:
                        session.record_recovery("analyze_model", "repair_model", "still not watertight")
                        self._record_failure_event(
                            session, "analyze_model", "not_watertight",
                            recovery_strategy="repair_model", recovery_success=False,
                            retry_count=retries,
                        )

            # Repair exhausted or disabled
            session.add_message("Model could not be made watertight after repair attempt.")
            return False, result

        return True, result
