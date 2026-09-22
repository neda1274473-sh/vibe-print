"""
Pre-hardware verification Part 2 — runs requests 3 and 4 through the full pipeline.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from vibe_print.agent.orchestrator import SessionStore, WorkflowPlanner, WorkflowExecutor, ExecutorConfig
from vibe_print.generator.requirements import RequirementsParser
from vibe_print.models.analyzer import ModelAnalyzer
from vibe_print.slicer.cli import get_slicer_cli

REQUESTS = [
    "I want a small open box, 50x30x20mm, to organize screws on my desk",
    "A hook that can hold a coat, mounted on a wall",
]


def run_request(goal: str, idx: int):
    print(f"\n{'='*70}")
    print(f"REQUEST #{idx + 1}")
    print(f"Input: {goal!r}")
    print(f"{'='*70}")

    parser = RequirementsParser()
    requirements = parser.parse(goal)

    print(f"\n--- Parsed Requirements ---")
    print(f"  Category: {requirements.category.value}")
    print(f"  Name: {requirements.name}")
    print(f"  Description: {requirements.description}")
    print(f"  Target dimensions: {requirements.target_dimensions}")
    print(f"  Primary dimension (mm): {requirements.get_primary_dimension_mm()}")
    print(f"  Wall thickness (mm): {requirements.wall_thickness_mm}")
    print(f"  Needs strength: {requirements.needs_strength}")
    print(f"  Needs flexibility: {requirements.needs_flexibility}")
    print(f"  Fit type: {requirements.fit_type.value}")
    print(f"  Reference object: {requirements.reference_object}")
    print(f"  Extracted numbers: {requirements.extracted_numbers}")

    store = SessionStore()
    planner = WorkflowPlanner()
    executor = WorkflowExecutor()
    executor.cfg = ExecutorConfig(
        auto_repair=True,
        auto_adjust_params=True,
        max_print_time_minutes=240,
        max_filament_g=200,
    )

    session = store.create(goal)
    session.plan = planner.plan(goal)
    result = executor.run(session)

    print(f"\n--- Workflow Result ---")
    print(f"  Success: {result.get('success')}")
    print(f"  Session ID: {result.get('session_id')}")
    if result.get('error'):
        print(f"  Error: {result.get('error')}")

    model_path = session.model_path
    print(f"\n--- Generated Model ---")
    print(f"  Model path: {model_path}")
    print(f"  Model type: {session.model_type}")

    if model_path and Path(model_path).exists():
        size = Path(model_path).stat().st_size
        print(f"  File size: {size} bytes")

        analyzer = ModelAnalyzer()
        analysis = analyzer.analyze(model_path)
        print(f"\n--- Model Analysis ---")
        print(f"  Analysis: {json.dumps(analysis, indent=2, default=str)}")
    else:
        print(f"  File does not exist (model generation may have failed or used fallback)")
        analysis = None

    print(f"\n--- Validation ---")
    if session.validation_result:
        mesh_info = session.validation_result.get("mesh_info", {})
        is_watertight = mesh_info.get("is_watertight", False)
        vol = mesh_info.get("volume_cm3")
        print(f"  Watertight: {is_watertight}")
        print(f"  Volume (cm³): {vol}")
        issues = []
        if not is_watertight:
            issues.append("Model is not watertight")
        if vol is None or vol <= 0:
            issues.append("Model has zero or negative volume")
        print(f"  Issues: {issues if issues else 'None'}")
        print(f"  Valid: {len(issues) == 0}")
    else:
        print(f"  No validation result available")

    print(f"\n--- Slicing ---")
    if session.slicing_result:
        sr = session.slicing_result
        print(f"  Mode: {sr.get('mode', 'unknown')}")
        print(f"  Estimated time (min): {sr.get('estimated_time_minutes')}")
        print(f"  Estimated filament (g): {sr.get('estimated_filament_grams')}")
        print(f"  G-code path: {sr.get('output_gcode') or sr.get('gcode_path')}")
        print(f"  3MF path: {sr.get('output_3mf')}")
    else:
        print(f"  No slicing result available")

    print(f"\n--- Recovery Actions ---")
    if session.recovery_actions:
        for ra in session.recovery_actions:
            print(f"  {ra}")
    else:
        print(f"  None")

    print(f"\n--- Messages ---")
    if session.messages:
        for msg in session.messages:
            print(f"  {msg}")
    else:
        print(f"  None")

    print(f"\n--- Workflow Trace ---")
    for step in session.plan:
        print(f"  {step.name}: {step.status.value}")
        if step.error:
            print(f"    Error: {step.error}")
        if step.recovery_action:
            print(f"    Recovery: {step.recovery_action}")

    return {
        "goal": goal,
        "requirements": requirements.to_dict(),
        "model_path": model_path,
        "model_type": session.model_type,
        "analysis": analysis,
        "validation": session.validation_result,
        "slicing": session.slicing_result,
        "recovery_actions": session.recovery_actions,
        "messages": session.messages,
        "trace": [s.to_dict() for s in session.plan],
        "workflow_success": result.get("success"),
        "workflow_error": result.get("error"),
    }


def main():
    results = []
    for idx, goal in enumerate(REQUESTS):
        try:
            result = run_request(goal, idx)
            results.append(result)
        except Exception as e:
            print(f"\n!!! EXCEPTION for request #{idx + 1}: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "goal": goal,
                "exception": str(e),
                "traceback": traceback.format_exc(),
            })

    out_path = Path("verification_part2_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n\nRaw results saved to: {out_path}")


if __name__ == "__main__":
    main()
