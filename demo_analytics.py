import asyncio
import tempfile
from pathlib import Path
from vibe_print.agent.orchestrator import WorkflowPlanner, WorkflowExecutor, SessionStore
from vibe_print.iteration.tracker import IterationTracker

with tempfile.TemporaryDirectory() as tmpdir:
    db_path = Path(tmpdir) / "demo.db"
    tracker = IterationTracker(db_path=db_path)
    asyncio.run(tracker.initialize())

    store = SessionStore()
    planner = WorkflowPlanner()
    executor = WorkflowExecutor(tracker=tracker)

    # Run 2 successful workflows
    for i in range(2):
        session = store.create("tube squeezer for 65mm bottle")
        session.plan = planner.plan("tube squeezer for 65mm bottle")
        result = executor.run(session)
        print("Workflow %d: success=%s" % (i + 1, result["success"]))

    # Run 1 failed workflow
    session = store.create("something weird")
    session.plan = planner.plan("something weird")
    result = executor.run(session)
    print("Workflow 3: success=%s" % result["success"])

    # Get analytics
    analytics = asyncio.run(tracker.get_print_analytics())
    print()
    print("=== SUMMARY ===")
    print(analytics["summary"])
    print()
    print("=== STATS ===")
    import json
    print(json.dumps(analytics["stats"], indent=2))
