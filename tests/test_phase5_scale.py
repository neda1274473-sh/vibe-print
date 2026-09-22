"""
Phase 5 tests — Scale & Cloud: multi-tenancy, session persistence,
remote monitoring, and cloud sync.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest

from vibe_print.agent.context import AgentSession, WorkflowStep, StepStatus
from vibe_print.agent.orchestrator import SessionStore, WorkflowPlanner, WorkflowExecutor, ExecutorConfig
from vibe_print.agent.cloud_sync import CloudSync
from vibe_print.iteration.tracker import IterationTracker


@pytest.fixture
def temp_db():
    """Provide a temporary database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    p = Path(path)
    yield p
    p.unlink(missing_ok=True)


@pytest.fixture
def tracker(temp_db):
    """Provide an initialized tracker."""
    t = IterationTracker(db_path=temp_db)
    asyncio.run(t.initialize())
    return t


# ------------------------------------------------------------------
# Deliverable 1: Persistent multi-tenant session storage
# ------------------------------------------------------------------

class TestSessionPersistence:
    """Sessions survive process restarts and are keyed by user_id."""

    def test_create_and_get_session(self, tracker):
        store = SessionStore(tracker=tracker)
        session = store.create(goal="test goal", user_id="alice")
        assert session.user_id == "alice"
        assert session.goal == "test goal"

        # Retrieve from DB
        loaded = store.get(session.session_id, user_id="alice")
        assert loaded is not None
        assert loaded.goal == "test goal"
        assert loaded.user_id == "alice"

    def test_session_isolation(self, tracker):
        store = SessionStore(tracker=tracker)
        s1 = store.create(goal="alice goal", user_id="alice")
        s2 = store.create(goal="bob goal", user_id="bob")

        # Alice cannot see Bob's session
        assert store.get(s2.session_id, user_id="alice") is None
        # Bob cannot see Alice's session
        assert store.get(s1.session_id, user_id="bob") is None

    def test_list_active_sessions(self, tracker):
        store = SessionStore(tracker=tracker)
        s1 = store.create(goal="g1", user_id="alice")
        s2 = store.create(goal="g2", user_id="alice")
        store.create(goal="g3", user_id="bob")

        active = store.list_active(user_id="alice")
        assert len(active) == 2
        ids = {s.session_id for s in active}
        assert s1.session_id in ids
        assert s2.session_id in ids

    def test_delete_session(self, tracker):
        store = SessionStore(tracker=tracker)
        s = store.create(goal="to delete", user_id="alice")
        store.delete(s.session_id, user_id="alice")
        assert store.get(s.session_id, user_id="alice") is None

    def test_session_survives_store_recreation(self, tracker):
        store1 = SessionStore(tracker=tracker)
        s = store1.create(goal="persistent", user_id="alice")
        sid = s.session_id

        # Simulate process restart: new SessionStore instance
        store2 = SessionStore(tracker=tracker)
        loaded = store2.get(sid, user_id="alice")
        assert loaded is not None
        assert loaded.goal == "persistent"

    def test_session_hydration_restores_plan(self, tracker):
        store = SessionStore(tracker=tracker)
        s = store.create(goal="hydration test", user_id="alice")
        s.plan = [
            WorkflowStep(name="step1", description="d1", status=StepStatus.OK),
            WorkflowStep(name="step2", description="d2", status=StepStatus.FAILED),
        ]
        s.current_step_index = 1
        s.status = "failed"
        store._persist_session(s)

        # Reload
        loaded = store.get(s.session_id, user_id="alice")
        assert loaded is not None
        assert len(loaded.plan) == 2
        assert loaded.plan[0].name == "step1"
        assert loaded.plan[0].status == StepStatus.OK
        assert loaded.plan[1].status == StepStatus.FAILED
        assert loaded.current_step_index == 1
        assert loaded.status == "failed"


# ------------------------------------------------------------------
# Deliverable 2: Remote monitoring (get_server_status)
# ------------------------------------------------------------------

class TestRemoteMonitoring:
    """Server status tool returns health and runtime info."""

    def test_get_server_status(self):
        from vibe_print.server import get_server_status, GetServerStatusInput
        result = get_server_status(GetServerStatusInput())
        assert result["success"] is True
        assert "uptime_seconds" in result
        assert result["uptime_seconds"] >= 0
        assert "db_connected" in result
        assert "active_sessions" in result
        assert "total_sessions_today" in result
        assert result["transport"] == "stdio"
        assert result["version"] == "5.0.0"


# ------------------------------------------------------------------
# Deliverable 3: Multi-user auth
# ------------------------------------------------------------------

class TestMultiUserAuth:
    """API key auth with per-user rate limiting."""

    def test_default_user_exists(self, tracker):
        user = asyncio.run(tracker.authenticate("default-key"))
        assert user is not None
        assert user["user_id"] == "default"

    def test_invalid_api_key(self, tracker):
        user = asyncio.run(tracker.authenticate("bad-key"))
        assert user is None

    def test_create_and_authenticate_user(self, tracker):
        asyncio.run(tracker.create_user("alice", "alice-secret-key"))
        user = asyncio.run(tracker.authenticate("alice-secret-key"))
        assert user is not None
        assert user["user_id"] == "alice"
        assert user["role"] == "user"

    def test_sync_rejects_invalid_key(self):
        from vibe_print.server import sync_to_cloud, SyncToCloudInput
        result = sync_to_cloud(SyncToCloudInput(api_key="invalid-key"))
        assert result["success"] is False
        assert "Invalid API key" in result["error"]["message"]


# ------------------------------------------------------------------
# Deliverable 5: Cloud sync
# ------------------------------------------------------------------

class TestCloudSync:
    """Bidirectional sync between local and remote trackers."""

    def test_sync_pushes_and_pulls(self, tracker):
        # Create a second tracker as "remote"
        fd, remote_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        remote_db = Path(remote_path)
        remote_tracker = IterationTracker(db_path=remote_db)
        asyncio.run(remote_tracker.initialize())

        sync = CloudSync(local_tracker=tracker, remote_tracker=remote_tracker)

        # Record some local data
        asyncio.run(tracker.record_metric(
            step_name="generate_model",
            success=True,
            started_at=__import__("datetime").datetime.now(),
            user_id="alice",
        ))

        # Sync
        result = asyncio.run(sync.sync(user_id="alice"))
        assert result["pushed"]["metrics"] >= 1
        assert result["last_sync"] is not None

        # Verify remote has the data
        remote_metrics = asyncio.run(remote_tracker.get_metrics_since(
            "1970-01-01T00:00:00", user_id="alice"
        ))
        assert len(remote_metrics) >= 1

        remote_db.unlink(missing_ok=True)

    def test_sync_isolation(self, tracker):
        fd, remote_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        remote_db = Path(remote_path)
        remote_tracker = IterationTracker(db_path=remote_db)
        asyncio.run(remote_tracker.initialize())

        sync = CloudSync(local_tracker=tracker, remote_tracker=remote_tracker)

        # Alice's data
        asyncio.run(tracker.record_metric(
            step_name="generate_model",
            success=True,
            started_at=__import__("datetime").datetime.now(),
            user_id="alice",
        ))

        # Sync only alice
        asyncio.run(sync.sync(user_id="alice"))

        # Bob should see nothing on remote
        remote_metrics = asyncio.run(remote_tracker.get_metrics_since(
            "1970-01-01T00:00:00", user_id="bob"
        ))
        assert len(remote_metrics) == 0

        remote_db.unlink(missing_ok=True)


# ------------------------------------------------------------------
# Integration: WorkflowExecutor with persistent SessionStore
# ------------------------------------------------------------------

class TestWorkflowWithPersistence:
    """End-to-end: workflow runs, metrics recorded, sessions persisted."""

    def test_workflow_persists_session(self, tracker):
        store = SessionStore(tracker=tracker)
        planner = WorkflowPlanner()
        executor = WorkflowExecutor(tracker=tracker)

        session = store.create(goal="box for storing pens", user_id="alice")
        session.plan = planner.plan(session.goal)
        result = executor.run(session)

        # Session should be persisted with final status
        loaded = store.get(session.session_id, user_id="alice")
        assert loaded is not None
        # Status should reflect completion or failure
        assert loaded.status in ("active", "completed", "failed")

    def test_metrics_recorded_with_user_id(self, tracker):
        store = SessionStore(tracker=tracker)
        planner = WorkflowPlanner()
        executor = WorkflowExecutor(tracker=tracker)

        session = store.create(goal="small bracket", user_id="bob")
        session.plan = planner.plan(session.goal)
        executor.run(session)

        # Check metrics have user_id
        metrics = asyncio.run(tracker.get_metrics_since(
            "1970-01-01T00:00:00", user_id="bob"
        ))
        assert len(metrics) > 0
        for m in metrics:
            assert m["user_id"] == "bob"


# ------------------------------------------------------------------
# Empty-state tests
# ------------------------------------------------------------------

class TestEmptyState:
    """Clean database returns sensible defaults."""

    def test_list_active_empty(self, tracker):
        store = SessionStore(tracker=tracker)
        assert store.list_active(user_id="nobody") == []

    def test_get_nonexistent_session(self, tracker):
        store = SessionStore(tracker=tracker)
        assert store.get("nonexistent", user_id="alice") is None

    def test_count_sessions_today_empty(self, tracker):
        count = asyncio.run(tracker.count_sessions_today(user_id="newuser"))
        assert count == 0
