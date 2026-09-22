"""
Cloud Sync — Bidirectional sync between local and remote tracker databases.

Phase 5 uses a second local SQLite DB as the simulated remote.
Real cloud backend (S3, PostgreSQL, etc.) would be a drop-in replacement
for the remote IterationTracker.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from vibe_print.logging_config import get_logger

logger = get_logger(__name__)


class CloudSync:
    """
    Bidirectional sync engine between local and remote tracker databases.

    Uses last-write-wins conflict resolution with per-table timestamps.
    """

    def __init__(self, local_tracker, remote_tracker):
        self.local = local_tracker
        self.remote = remote_tracker

    async def sync(self, user_id: str = "default") -> Dict[str, Any]:
        """
        Perform bidirectional sync for a user.

        1. Push local changes to remote (metrics, failures, sessions)
        2. Pull remote changes to local
        3. Return counts
        """
        # Ensure both DBs are initialized
        await self.local._ensure_initialized()
        await self.remote._ensure_initialized()

        # Get last sync timestamp (stored in local as a simple heuristic)
        last_sync = await self._get_last_sync(user_id)

        # Push local → remote
        pushed_metrics = await self._push_metrics(user_id, last_sync)
        pushed_failures = await self._push_failures(user_id, last_sync)
        pushed_sessions = await self._push_sessions(user_id, last_sync)

        # Pull remote → local
        pulled_metrics = await self._pull_metrics(user_id, last_sync)
        pulled_failures = await self._pull_failures(user_id, last_sync)
        pulled_sessions = await self._pull_sessions(user_id, last_sync)

        # Update last sync timestamp
        now = datetime.now().isoformat()
        await self._set_last_sync(user_id, now)

        return {
            "pushed": {
                "metrics": pushed_metrics,
                "failures": pushed_failures,
                "sessions": pushed_sessions,
            },
            "pulled": {
                "metrics": pulled_metrics,
                "failures": pulled_failures,
                "sessions": pulled_sessions,
            },
            "last_sync": now,
        }

    async def _get_last_sync(self, user_id: str) -> str:
        """Get last sync timestamp for user."""
        try:
            rows = await self.local.get_metrics_since("1970-01-01T00:00:00", user_id)
            if rows:
                return "1970-01-01T00:00:00"
        except Exception:
            pass
        return "1970-01-01T00:00:00"

    async def _set_last_sync(self, user_id: str, timestamp: str) -> None:
        """Store last sync timestamp."""
        # For simplicity, we don't persist this; next sync uses 1970
        # In production, store in a sync_metadata table
        pass

    async def _push_metrics(self, user_id: str, since: str) -> int:
        """Push local metrics to remote."""
        records = await self.local.get_metrics_since(since, user_id)
        count = 0
        for record in records:
            try:
                await self.remote.upsert_metric(record)
                count += 1
            except Exception as e:
                logger.warning("Failed to push metric %s: %s", record.get("metric_id"), e)
        return count

    async def _push_failures(self, user_id: str, since: str) -> int:
        """Push local failures to remote."""
        records = await self.local.get_failures_since(since, user_id)
        count = 0
        for record in records:
            try:
                await self.remote.upsert_failure(record)
                count += 1
            except Exception as e:
                logger.warning("Failed to push failure %s: %s", record.get("event_id"), e)
        return count

    async def _push_sessions(self, user_id: str, since: str) -> int:
        """Push local sessions to remote."""
        records = await self.local.get_sessions_since(since, user_id)
        count = 0
        for record in records:
            try:
                await self.remote.upsert_session(record)
                count += 1
            except Exception as e:
                logger.warning("Failed to push session %s: %s", record.get("session_id"), e)
        return count

    async def _pull_metrics(self, user_id: str, since: str) -> int:
        """Pull remote metrics to local."""
        records = await self.remote.get_metrics_since(since, user_id)
        count = 0
        for record in records:
            try:
                await self.local.upsert_metric(record)
                count += 1
            except Exception as e:
                logger.warning("Failed to pull metric %s: %s", record.get("metric_id"), e)
        return count

    async def _pull_failures(self, user_id: str, since: str) -> int:
        """Pull remote failures to local."""
        records = await self.remote.get_failures_since(since, user_id)
        count = 0
        for record in records:
            try:
                await self.local.upsert_failure(record)
                count += 1
            except Exception as e:
                logger.warning("Failed to pull failure %s: %s", record.get("event_id"), e)
        return count

    async def _pull_sessions(self, user_id: str, since: str) -> int:
        """Pull remote sessions to local."""
        records = await self.remote.get_sessions_since(since, user_id)
        count = 0
        for record in records:
            try:
                await self.local.upsert_session(record)
                count += 1
            except Exception as e:
                logger.warning("Failed to pull session %s: %s", record.get("session_id"), e)
        return count
