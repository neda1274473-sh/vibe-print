"""Tests for the tube squeezer generator."""

from pathlib import Path

import pytest

from vibe_print.generator.tube_squeezer import TubeSqueezerGenerator
from vibe_print.exceptions import InputValidationError, ModelGenerationError


class TestTubeSqueezerGenerator:
    """Tests for TubeSqueezerGenerator."""

    def test_generate_success(self, temp_dir: Path):
        gen = TubeSqueezerGenerator()
        result = gen.generate(
            tube_diameter=25.0,
            wall_thickness=2.0,
            width=40.0,
            output_name="test_squeezer",
        )
        assert Path(result).exists()
        assert Path(result).suffix == ".stl"

    def test_generate_default_parameters(self, temp_dir: Path):
        gen = TubeSqueezerGenerator()
        result = gen.generate(tube_diameter=30.0)
        assert Path(result).exists()

    def test_invalid_tube_diameter_zero_raises(self):
        gen = TubeSqueezerGenerator()
        with pytest.raises(InputValidationError) as exc_info:
            gen.generate(tube_diameter=0)
        assert "tube_diameter must be positive" in str(exc_info.value)

    def test_invalid_tube_diameter_negative_raises(self):
        gen = TubeSqueezerGenerator()
        with pytest.raises(InputValidationError) as exc_info:
            gen.generate(tube_diameter=-5)
        assert "tube_diameter must be positive" in str(exc_info.value)

    def test_invalid_wall_thickness_zero_raises(self):
        gen = TubeSqueezerGenerator()
        with pytest.raises(InputValidationError) as exc_info:
            gen.generate(tube_diameter=25, wall_thickness=0)
        assert "wall_thickness must be positive" in str(exc_info.value)

    def test_invalid_wall_thickness_negative_raises(self):
        gen = TubeSqueezerGenerator()
        with pytest.raises(InputValidationError) as exc_info:
            gen.generate(tube_diameter=25, wall_thickness=-1)
        assert "wall_thickness must be positive" in str(exc_info.value)

    def test_invalid_width_zero_raises(self):
        gen = TubeSqueezerGenerator()
        with pytest.raises(InputValidationError) as exc_info:
            gen.generate(tube_diameter=25, width=0)
        assert "width must be positive" in str(exc_info.value)

    def test_invalid_width_negative_raises(self):
        gen = TubeSqueezerGenerator()
        with pytest.raises(InputValidationError) as exc_info:
            gen.generate(tube_diameter=25, width=-10)
        assert "width must be positive" in str(exc_info.value)

    def test_invalid_clearance_negative_raises(self):
        gen = TubeSqueezerGenerator()
        with pytest.raises(InputValidationError) as exc_info:
            gen.generate(tube_diameter=25, clearance=-0.1)
        assert "clearance must be non-negative" in str(exc_info.value)

    def test_clearance_zero_is_valid(self, temp_dir: Path):
        gen = TubeSqueezerGenerator()
        result = gen.generate(tube_diameter=25, clearance=0)
        assert Path(result).exists()
