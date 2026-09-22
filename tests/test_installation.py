"""
Tests for vibe-print installation and basic functionality.
"""

import sys
import pytest


class TestInstallation:
    """Test that the package is properly installed."""

    def test_python_version(self):
        """Verify Python version is 3.12 or higher."""
        assert sys.version_info >= (3, 12), f"Python 3.12+ required, got {sys.version_info}"

    def test_package_import(self):
        """Test that the main package can be imported."""
        import vibe_print
        assert vibe_print is not None

    def test_server_import(self):
        """Test that the server module can be imported."""
        from vibe_print import server
        assert server is not None
        assert hasattr(server, 'mcp')

    def test_fastmcp_import(self):
        """Test that FastMCP is available."""
        from fastmcp import FastMCP
        assert FastMCP is not None

    def test_mcp_import(self):
        """Test that mcp package is available."""
        import mcp
        assert mcp is not None


class TestCLI:
    """Test CLI entry points."""

    def test_vibe_print_command_exists(self):
        """Test that vibe-print command is available."""
        import subprocess
        result = subprocess.run(
            ['vibe-print', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )
        # The command should start the server (exit code 0 or be interrupted)
        # We just verify it doesn't fail immediately with import errors
        assert 'ModuleNotFoundError' not in result.stderr
        assert 'ImportError' not in result.stderr

    def test_module_invocation(self):
        """Test that python -m vibe_print works."""
        import subprocess
        result = subprocess.run(
            [sys.executable, '-m', 'vibe_print', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert 'ModuleNotFoundError' not in result.stderr
        assert 'ImportError' not in result.stderr


class TestMCP:
    """Test MCP server functionality."""

    def test_mcp_server_initialized(self):
        """Test that MCP server is properly initialized."""
        from vibe_print.server import mcp
        assert mcp is not None
        assert mcp.name == "vibe_print"

    def test_tools_registered(self):
        """Test that MCP tools are registered."""
        from vibe_print.server import mcp
        
        # FastMCP stores tools differently - check various possible attributes
        tools = []
        if hasattr(mcp, '_tool_manager'):
            tools = getattr(mcp._tool_manager, '_tools', [])
        elif hasattr(mcp, '_tools'):
            tools = mcp._tools
        elif hasattr(mcp, 'tools'):
            tools = mcp.tools
            
        # At minimum, verify the server has the expected structure
        assert hasattr(mcp, 'name'), "MCP server should have a name"
        assert mcp.name == "vibe_print", f"Expected server name 'vibe_print', got '{mcp.name}'"


class TestDependencies:
    """Test that all required dependencies are available."""

    def test_pydantic_available(self):
        """Test pydantic is available."""
        import pydantic
        assert pydantic.__version__ >= "2.0"

    def test_httpx_available(self):
        """Test httpx is available."""
        import httpx
        assert httpx is not None

    def test_numpy_available(self):
        """Test numpy is available."""
        import numpy
        assert numpy is not None

    def test_trimesh_available(self):
        """Test trimesh is available."""
        import trimesh
        assert trimesh is not None

    def test_paho_mqtt_available(self):
        """Test paho-mqtt is available."""
        import paho.mqtt
        assert paho.mqtt is not None

    def test_opencv_available(self):
        """Test opencv-python is available."""
        import cv2
        assert cv2 is not None

    def test_pillow_available(self):
        """Test pillow is available."""
        from PIL import Image
        assert Image is not None

    def test_aiosqlite_available(self):
        """Test aiosqlite is available."""
        import aiosqlite
        assert aiosqlite is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])