"""Shared pytest fixtures for Vibe Print tests."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir() -> Path:
    """Provide a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def sample_stl_path(temp_dir: Path) -> Path:
    """Create a minimal valid ASCII STL file for testing."""
    path = temp_dir / "sample.stl"
    stl_content = """solid sample
  facet normal 0 0 0
    outer loop
      vertex 0 0 0
      vertex 10 0 0
      vertex 5 10 0
    endloop
  endfacet
  facet normal 0 0 0
    outer loop
      vertex 0 0 0
      vertex 5 10 0
      vertex 5 5 10
    endloop
  endfacet
  facet normal 0 0 0
    outer loop
      vertex 10 0 0
      vertex 5 10 0
      vertex 5 5 10
    endloop
  endfacet
  facet normal 0 0 0
    outer loop
      vertex 0 0 0
      vertex 10 0 0
      vertex 5 5 10
    endloop
  endfacet
endsolid sample
"""
    path.write_text(stl_content, encoding="utf-8")
    return path


@pytest.fixture
def sample_3mf_path(temp_dir: Path) -> Path:
    """Create a dummy 3MF file for testing (not a real 3MF, just a placeholder)."""
    path = temp_dir / "sample.3mf"
    path.write_bytes(b"PK\x03\x04")  # ZIP magic bytes (3MF is a ZIP container)
    return path
