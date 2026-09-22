"""Tests for the model scaler."""

from pathlib import Path

import pytest

from vibe_print.models.scaler import ModelScaler
from vibe_print.exceptions import InputValidationError, ModelScalingError


class TestModelScaler:
    """Tests for ModelScaler."""

    def test_scale_uniform_success(self, sample_stl_path: Path, temp_dir: Path):
        scaler = ModelScaler(output_dir=temp_dir)
        result = scaler.scale_uniform(sample_stl_path, scale_factor=2.0)

        assert result.success is True
        assert result.scaled_path.exists()
        assert result.scale_factor == 2.0
        assert result.uniform_scale is True

    def test_scale_uniform_half_size(self, sample_stl_path: Path, temp_dir: Path):
        scaler = ModelScaler(output_dir=temp_dir)
        result = scaler.scale_uniform(sample_stl_path, scale_factor=0.5)

        assert result.success is True
        assert result.scale_factor == 0.5

    def test_scale_uniform_invalid_factor_zero_raises(self, sample_stl_path: Path, temp_dir: Path):
        scaler = ModelScaler(output_dir=temp_dir)
        with pytest.raises(InputValidationError) as exc_info:
            scaler.scale_uniform(sample_stl_path, scale_factor=0)
        assert "scale_factor must be positive" in str(exc_info.value)

    def test_scale_uniform_invalid_factor_negative_raises(self, sample_stl_path: Path, temp_dir: Path):
        scaler = ModelScaler(output_dir=temp_dir)
        with pytest.raises(InputValidationError) as exc_info:
            scaler.scale_uniform(sample_stl_path, scale_factor=-1.5)
        assert "scale_factor must be positive" in str(exc_info.value)

    def test_scale_uniform_missing_file_raises(self, temp_dir: Path):
        scaler = ModelScaler(output_dir=temp_dir)
        with pytest.raises(FileNotFoundError):
            scaler.scale_uniform("/nonexistent/model.stl", scale_factor=2.0)

    def test_scale_result_to_dict(self, sample_stl_path: Path, temp_dir: Path):
        scaler = ModelScaler(output_dir=temp_dir)
        result = scaler.scale_uniform(sample_stl_path, scale_factor=1.5)

        d = result.to_dict()
        assert d["scale_factor"] == 1.5
        assert d["scale_percentage"] == 150.0
        assert d["uniform_scale"] is True
        assert "original_dimensions_mm" in d
        assert "scaled_dimensions_mm" in d

    def test_scale_result_to_json(self, sample_stl_path: Path, temp_dir: Path):
        scaler = ModelScaler(output_dir=temp_dir)
        result = scaler.scale_uniform(sample_stl_path, scale_factor=1.5)

        json_str = result.to_json()
        assert '"scale_factor": 1.5' in json_str
        assert '"scale_percentage": 150.0' in json_str

    def test_scale_to_dimension(self, sample_stl_path: Path, temp_dir: Path):
        scaler = ModelScaler(output_dir=temp_dir)
        result = scaler.scale_to_dimension(
            sample_stl_path,
            target_width=20.0,
            maintain_aspect_ratio=True,
        )
        assert result.success is True

    def test_scale_for_tube_squeezer(self, sample_stl_path: Path, temp_dir: Path):
        scaler = ModelScaler(output_dir=temp_dir)
        result = scaler.scale_for_tube_squeezer(
            sample_stl_path,
            original_tube_diameter_mm=25.0,
            target_tube_diameter_mm=65.0,
        )
        assert result.success is True
        assert any("Scaled from 25.0mm to 65.0mm" in s for s in result.adjustments_made)
