"""Tests for the model analyzer."""

from pathlib import Path

import pytest

from vibe_print.models.analyzer import ModelAnalyzer
from vibe_print.exceptions import ModelValidationError


class TestModelAnalyzer:
    """Tests for ModelAnalyzer."""

    def test_analyze_missing_file_raises(self):
        analyzer = ModelAnalyzer()
        with pytest.raises(ModelValidationError) as exc_info:
            analyzer.analyze("/nonexistent/path/model.stl")
        assert "not found" in str(exc_info.value).lower()

    def test_analyze_placeholder_stl(self, sample_stl_path: Path):
        analyzer = ModelAnalyzer()
        result = analyzer.analyze(str(sample_stl_path))

        assert result["file_path"] == str(sample_stl_path)
        assert "is_valid" in result
        assert "issues" in result
        assert "recommendations" in result
        assert "mesh_info" in result

        mesh_info = result["mesh_info"]
        assert mesh_info["vertices"] == 4
        assert mesh_info["faces"] == 4
        assert mesh_info["is_watertight"] is True

    def test_validate_for_printing_valid(self, sample_stl_path: Path):
        analyzer = ModelAnalyzer()
        result = analyzer.validate_for_printing(str(sample_stl_path))

        assert "is_valid" in result
        assert "issues" in result
        assert "mesh_info" in result

    def test_validate_for_printing_bed_size_check(self, sample_stl_path: Path):
        analyzer = ModelAnalyzer()
        # Use very small bed to force bed_size issue
        result = analyzer.validate_for_printing(
            str(sample_stl_path),
            printer_bed_size=(1.0, 1.0, 1.0),
        )
        assert result["is_valid"] is False
        bed_size_issues = [i for i in result["issues"] if i["type"] == "bed_size"]
        assert len(bed_size_issues) > 0

    def test_analyze_with_custom_nozzle(self, sample_stl_path: Path):
        analyzer = ModelAnalyzer()
        result = analyzer.analyze(
            str(sample_stl_path),
            nozzle_diameter=0.6,
            max_overhang_angle=50.0,
            min_wall_thickness=1.2,
        )
        assert "mesh_info" in result

    def test_analyze_returns_file_size(self, sample_stl_path: Path):
        analyzer = ModelAnalyzer()
        result = analyzer.analyze(str(sample_stl_path))
        assert "file_size_mb" in result
        assert isinstance(result["file_size_mb"], float)
