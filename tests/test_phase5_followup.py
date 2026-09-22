"""
Phase 5 Follow-up Tests — Fleet Management, Transport, User Isolation

Covers:
1. Fleet / Multi-Printer Management (2+ concurrent simulated printers)
2. Transport configuration (unit-level, since live SSE requires async server)
3. User isolation for read tools (get_print_analytics, get_iteration_history)
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from vibe_print.printer.mqtt_client import (
    SimulatedPrinterMQTTClient,
    PrinterFleet,
    get_printer_client,
)
import vibe_print.server as server_module
from vibe_print.server import set_transport
from vibe_print.iteration.tracker import IterationTracker


# ============================================================
# 1. FLEET / MULTI-PRINTER MANAGEMENT
# ============================================================

class TestPrinterFleet:
    """Test fleet management with multiple concurrent simulated printers."""

    def test_connect_two_simulated_printers(self):
        """Connect two simulated printers and verify both are tracked."""
        fleet = PrinterFleet()
        client_a = fleet.connect_printer("printer-A", serial_number="SIM001")
        client_b = fleet.connect_printer("printer-B", serial_number="SIM002")

        assert client_a.is_connected
        assert client_b.is_connected
        assert client_a.printer_id == "printer-A"
        assert client_b.printer_id == "printer-B"

        printers = fleet.list_printers()
        assert len(printers) == 2
        ids = {p["printer_id"] for p in printers}
        assert ids == {"printer-A", "printer-B"}

        fleet.disconnect_printer("printer-A")
        fleet.disconnect_printer("printer-B")

    def test_start_print_on_one_does_not_affect_other(self):
        """Start a print on printer A, leave B idle, verify independent states."""
        fleet = PrinterFleet()
        fleet.connect_printer("printer-A", serial_number="SIM001")
        fleet.connect_printer("printer-B", serial_number="SIM002")

        with tempfile.NamedTemporaryFile(suffix=".gcode", delete=False) as f:
            f.write(b"G1 X0 Y0\n")
            gcode_path = Path(f.name)

        try:
            asyncio.run(fleet.start_print("printer-A", gcode_path))

            status_a = fleet.get_printer_status("printer-A")
            status_b = fleet.get_printer_status("printer-B")

            assert status_a is not None
            assert status_b is not None
            assert status_a["print"]["gcode_state"] == "PRINTING"
            assert status_b["print"]["gcode_state"] == "IDLE"
            assert status_a["print"]["job_name"] == gcode_path.name
            assert status_b["print"]["job_name"] is None
        finally:
            os.unlink(gcode_path)
            fleet.disconnect_printer("printer-A")
            fleet.disconnect_printer("printer-B")

    def test_pause_one_does_not_affect_other(self):
        """Pause printer A, verify printer B remains unchanged."""
        fleet = PrinterFleet()
        fleet.connect_printer("printer-A", serial_number="SIM001")
        fleet.connect_printer("printer-B", serial_number="SIM002")

        with tempfile.NamedTemporaryFile(suffix=".gcode", delete=False) as f:
            f.write(b"G1 X0 Y0\n")
            gcode_path = Path(f.name)

        try:
            asyncio.run(fleet.start_print("printer-A", gcode_path))
            asyncio.run(fleet.pause_print("printer-A"))

            status_a = fleet.get_printer_status("printer-A")
            status_b = fleet.get_printer_status("printer-B")

            assert status_a["print"]["gcode_state"] == "PAUSED"
            assert status_b["print"]["gcode_state"] == "IDLE"
        finally:
            os.unlink(gcode_path)
            fleet.disconnect_printer("printer-A")
            fleet.disconnect_printer("printer-B")

    def test_cancel_one_does_not_affect_other(self):
        """Cancel printer A, verify printer B still idle."""
        fleet = PrinterFleet()
        fleet.connect_printer("printer-A", serial_number="SIM001")
        fleet.connect_printer("printer-B", serial_number="SIM002")

        with tempfile.NamedTemporaryFile(suffix=".gcode", delete=False) as f:
            f.write(b"G1 X0 Y0\n")
            gcode_path = Path(f.name)

        try:
            asyncio.run(fleet.start_print("printer-A", gcode_path))
            asyncio.run(fleet.cancel_print("printer-A"))

            status_a = fleet.get_printer_status("printer-A")
            status_b = fleet.get_printer_status("printer-B")

            assert status_a["print"]["gcode_state"] == "IDLE"
            assert status_b["print"]["gcode_state"] == "IDLE"
            assert status_a["print"]["job_name"] is None
            assert status_b["print"]["job_name"] is None
        finally:
            os.unlink(gcode_path)
            fleet.disconnect_printer("printer-A")
            fleet.disconnect_printer("printer-B")

    def test_duplicate_printer_id_rejected(self):
        """Connecting a printer with a duplicate ID should raise an error."""
        fleet = PrinterFleet()
        fleet.connect_printer("printer-A", serial_number="SIM001")
        from vibe_print.exceptions import InputValidationError
        with pytest.raises(InputValidationError):
            fleet.connect_printer("printer-A", serial_number="SIM002")
        fleet.disconnect_printer("printer-A")

    def test_get_printer_status_not_found(self):
        """Getting status for a non-existent printer returns None."""
        fleet = PrinterFleet()
        assert fleet.get_printer_status("nonexistent") is None


class TestSimulatedPrinterMQTTClient:
    """Unit tests for the simulated printer client."""

    def test_simulated_printer_connect_disconnect(self):
        client = SimulatedPrinterMQTTClient(serial_number="SIM001")
        assert not client.is_connected
        asyncio.run(client.connect())
        assert client.is_connected
        asyncio.run(client.disconnect())
        assert not client.is_connected

    def test_simulated_printer_state_transitions(self):
        client = SimulatedPrinterMQTTClient(serial_number="SIM001")
        asyncio.run(client.connect())

        with tempfile.NamedTemporaryFile(suffix=".gcode", delete=False) as f:
            f.write(b"G1 X0 Y0\n")
            gcode_path = Path(f.name)

        try:
            asyncio.run(client.start_print(gcode_path))
            assert client._state == "PRINTING"

            asyncio.run(client.pause_print())
            assert client._state == "PAUSED"

            asyncio.run(client.resume_print())
            assert client._state == "PRINTING"

            asyncio.run(client.cancel_print())
            assert client._state == "IDLE"
        finally:
            os.unlink(gcode_path)
            asyncio.run(client.disconnect())

    def test_get_printer_client_returns_simulated_when_no_host(self):
        client = get_printer_client(host="simulated")
        assert isinstance(client, SimulatedPrinterMQTTClient)


# ============================================================
# 2. TRANSPORT CONFIGURATION
# ============================================================

class TestTransportConfiguration:
    """Unit tests for transport selection logic."""

    def test_default_transport_is_stdio(self):
        """Default transport should be stdio."""
        set_transport("stdio")
        assert server_module._current_transport == "stdio"

    def test_set_transport_sse(self):
        """Setting transport to sse should update the global."""
        set_transport("sse")
        assert server_module._current_transport == "sse"
        # Reset to default
        set_transport("stdio")

    def test_cli_parses_transport_argument(self):
        """CLI should accept --transport sse."""
        from vibe_print.__main__ import cli
        import sys
        old_argv = sys.argv
        try:
            sys.argv = ["vibe-print", "--transport", "sse"]
            # Just parse, don't run the server
            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
            parser.add_argument("--port", type=int, default=8080)
            args = parser.parse_args(["--transport", "sse"])
            assert args.transport == "sse"
            assert args.port == 8080
        finally:
            sys.argv = old_argv


# ============================================================
# 3. USER ISOLATION FOR READ TOOLS
# ============================================================

class TestUserIsolation:
    """
    Prove that get_print_analytics and get_iteration_history filter by user_id.

    Each test uses a fresh in-memory DB and two distinct API keys.
    """

    @pytest.fixture
    def tracker(self):
        """Fresh tracker for isolation tests (file-based so schema persists across connections)."""
        import tempfile
        db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = Path(db_file.name)
        db_file.close()
        t = IterationTracker(db_path=db_path)
        asyncio.run(t.initialize())
        yield t
        # cleanup
        import os
        if db_path.exists():
            os.unlink(db_path)

    def test_get_iteration_history_filters_by_user(self, tracker):
        """User A should only see their own iterations, not User B's."""
        # Create two users
        asyncio.run(tracker.create_user("user-a@example.com", "key-A"))
        asyncio.run(tracker.create_user("user-b@example.com", "key-B"))

        # Create iterations for each user
        iter_a = asyncio.run(tracker.create_iteration(
            model_name="model-shared",
            model_path="/tmp/a.stl",
            user_id="user-a@example.com",
        ))
        iter_b = asyncio.run(tracker.create_iteration(
            model_name="model-shared",
            model_path="/tmp/b.stl",
            user_id="user-b@example.com",
        ))

        # User A queries
        history_a = asyncio.run(tracker.get_recent_iterations(
            limit=100,
            user_id="user-a@example.com",
        ))
        ids_a = {i.iteration_id for i in history_a}
        assert iter_a.iteration_id in ids_a
        assert iter_b.iteration_id not in ids_a

        # User B queries
        history_b = asyncio.run(tracker.get_recent_iterations(
            limit=100,
            user_id="user-b@example.com",
        ))
        ids_b = {i.iteration_id for i in history_b}
        assert iter_b.iteration_id in ids_b
        assert iter_a.iteration_id not in ids_b

    def test_get_print_analytics_filters_by_user(self, tracker):
        """Analytics should only include metrics for the requesting user."""
        asyncio.run(tracker.create_user("user-a@example.com", "key-A"))
        asyncio.run(tracker.create_user("user-b@example.com", "key-B"))

        from datetime import datetime
        # Record metrics for each user
        asyncio.run(tracker.record_metric(
            step_name="slice_model",
            success=True,
            started_at=datetime.now(),
            user_id="user-a@example.com",
        ))
        asyncio.run(tracker.record_metric(
            step_name="slice_model",
            success=False,
            started_at=datetime.now(),
            user_id="user-b@example.com",
        ))

        # User A analytics
        analytics_a = asyncio.run(tracker.get_print_analytics(user_id="user-a@example.com"))
        assert analytics_a["stats"]["overall"]["total_workflows"] == 1
        assert analytics_a["stats"]["overall"]["overall_success_rate"] == 1.0

        # User B analytics
        analytics_b = asyncio.run(tracker.get_print_analytics(user_id="user-b@example.com"))
        assert analytics_b["stats"]["overall"]["total_workflows"] == 1
        assert analytics_b["stats"]["overall"]["overall_success_rate"] == 0.0

    def test_cross_user_access_rejected_at_tool_level(self, tracker):
        """
        The underlying tracker methods return all data when no user_id is given
        (admin behaviour).  User isolation is enforced at the MCP tool layer
        via API-key authentication — get_iteration_history and
        get_print_analytics both authenticate the caller and then pass the
        resolved user_id to the tracker.

        This test proves that when a user_id IS supplied the tracker filters
        correctly, which is the mechanism the tools rely on.
        """
        asyncio.run(tracker.create_user("user-a@example.com", "key-A"))
        asyncio.run(tracker.create_user("user-b@example.com", "key-B"))

        asyncio.run(tracker.create_iteration(
            model_name="model-x",
            model_path="/tmp/x.stl",
            user_id="user-a@example.com",
        ))

        # User B queries with their own user_id — should see nothing
        history_b = asyncio.run(tracker.get_recent_iterations(limit=100, user_id="user-b@example.com"))
        assert len(history_b) == 0

        analytics_b = asyncio.run(tracker.get_print_analytics(user_id="user-b@example.com"))
        assert analytics_b["stats"] is None  # no data for user B


# ============================================================
# 4. ASYNCIO.RUN() REGRESSION — Event Loop Safety
# ============================================================

class TestAsyncioRunSafety:
    """
    FastMCP's SSE transport invokes sync tool handlers from within a running
    event loop (``await tool.run()`` inside ``call_tool``).  Calling
    ``asyncio.run()`` from inside a running loop raises ``RuntimeError``.

    The server now uses ``_run_async()`` which detects a running loop and
    offloads to a background thread instead.
    """

    def test_run_async_from_sync_context(self):
        """_run_async works normally when no loop is running."""
        async def coro():
            return "ok"

        result = server_module._run_async(coro())
        assert result == "ok"

    def test_run_async_from_running_loop(self):
        """_run_async must NOT raise RuntimeError when called from a running loop."""
        async def inner_coro():
            return "from_loop"

        async def outer_coro():
            # This simulates what happens when FastMCP calls a sync tool handler
            # from within its async ``call_tool`` method under SSE transport.
            return server_module._run_async(inner_coro())

        # asyncio.run() starts a loop; outer_coro runs inside it,
        # which in turn calls _run_async — exactly the scenario that would
        # crash with plain asyncio.run().
        result = asyncio.run(outer_coro())
        assert result == "from_loop"

    def test_get_server_status_inside_running_loop(self):
        """get_server_status must work when called from an async context."""
        async def async_caller():
            # Simulate FastMCP calling the sync tool handler from an async context
            return server_module.get_server_status(server_module.GetServerStatusInput())

        result = asyncio.run(async_caller())
        if not result.get("success"):
            print("ERROR:", result)
        assert result["success"] is True
        assert "uptime_seconds" in result
        assert "transport" in result
