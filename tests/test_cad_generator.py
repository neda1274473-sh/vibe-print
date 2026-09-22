"""Tests for the parametric CAD generator."""

from pathlib import Path

import pytest

from vibe_print.generator.cad_generator import ParametricGenerator
from vibe_print.exceptions import ModelGenerationError, InputValidationError


class TestParametricGenerator:
    """Tests for ParametricGenerator."""

    def test_generate_box_success(self, temp_dir: Path):
        gen = ParametricGenerator()
        result = gen.generate(
            model_type="box",
            parameters={"width": 10, "height": 20, "depth": 30},
            output_name="test_box",
        )
        assert Path(result).exists()
        assert Path(result).suffix == ".stl"

    def test_generate_cylinder_success(self, temp_dir: Path):
        gen = ParametricGenerator()
        result = gen.generate(
            model_type="cylinder",
            parameters={"diameter": 10, "height": 20},
            output_name="test_cylinder",
        )
        assert Path(result).exists()

    def test_generate_tube_squeezer_success(self, temp_dir: Path):
        gen = ParametricGenerator()
        result = gen.generate(
            model_type="tube_squeezer",
            parameters={"tube_diameter": 25, "wall_thickness": 2},
            output_name="test_squeezer",
        )
        assert Path(result).exists()

    def test_invalid_model_type_raises(self):
        gen = ParametricGenerator()
        with pytest.raises(ModelGenerationError):
            gen.generate(model_type="", parameters={"width": 10})

    def test_none_model_type_raises(self):
        gen = ParametricGenerator()
        with pytest.raises(ModelGenerationError):
            gen.generate(model_type=None, parameters={"width": 10})  # type: ignore

    def test_empty_parameters_raises(self):
        gen = ParametricGenerator()
        with pytest.raises(ModelGenerationError):
            gen.generate(model_type="box", parameters={})

    def test_none_parameters_raises(self):
        gen = ParametricGenerator()
        with pytest.raises(ModelGenerationError):
            gen.generate(model_type="box", parameters=None)  # type: ignore

    def test_missing_required_params_raises(self):
        gen = ParametricGenerator()
        with pytest.raises(ModelGenerationError) as exc_info:
            gen.generate(model_type="box", parameters={"width": 10})  # missing height, depth
        assert "Missing required parameters" in str(exc_info.value)
        assert "height" in str(exc_info.value)
        assert "depth" in str(exc_info.value)

    def test_generate_from_description_success(self, temp_dir: Path):
        gen = ParametricGenerator()
        result = gen.generate_from_description(
            description="A small box for holding paperclips",
            material="PLA",
            nozzle_diameter=0.4,
        )
        assert "model_path" in result
        assert Path(result["model_path"]).exists()

    def test_generate_from_description_empty_raises(self):
        gen = ParametricGenerator()
        with pytest.raises(ModelGenerationError):
            gen.generate_from_description(description="")

    def test_generate_from_description_none_raises(self):
        gen = ParametricGenerator()
        with pytest.raises(ModelGenerationError):
            gen.generate_from_description(description=None)  # type: ignore

    # ------------------------------------------------------------------
    # New category generators (Part 2)
    # ------------------------------------------------------------------
    def test_generate_cup_holder_success(self, temp_dir: Path):
        gen = ParametricGenerator()
        result = gen.generate(
            model_type="cup_holder",
            parameters={"diameter": 80, "height": 64, "wall_thickness": 2.5, "base_thickness": 3.0},
            output_name="test_cup_holder",
        )
        assert Path(result).exists()
        assert Path(result).suffix == ".stl"

    def test_generate_phone_stand_success(self, temp_dir: Path):
        gen = ParametricGenerator()
        result = gen.generate(
            model_type="phone_stand",
            parameters={"width": 70, "depth": 42, "height": 35, "angle": 60, "lip_height": 5, "wall_thickness": 3.0},
            output_name="test_phone_stand",
        )
        assert Path(result).exists()
        assert Path(result).suffix == ".stl"

    def test_generate_keychain_success(self, temp_dir: Path):
        gen = ParametricGenerator()
        result = gen.generate(
            model_type="keychain",
            parameters={"width": 40, "height": 24, "thickness": 3.0, "hole_diameter": 5.0},
            output_name="test_keychain",
        )
        assert Path(result).exists()
        assert Path(result).suffix == ".stl"

    def test_generate_cable_clip_success(self, temp_dir: Path):
        gen = ParametricGenerator()
        result = gen.generate(
            model_type="cable_clip",
            parameters={"cable_diameter": 6, "clip_width": 18, "wall_thickness": 2.5, "mount_hole_diameter": 3.5},
            output_name="test_cable_clip",
        )
        assert Path(result).exists()
        assert Path(result).suffix == ".stl"

    def test_generate_from_description_cup_holder(self, temp_dir: Path):
        gen = ParametricGenerator()
        result = gen.generate_from_description(
            description="cup holder for car",
            material="PLA",
            nozzle_diameter=0.4,
        )
        assert result["model_type"] == "cup_holder"
        assert "model_path" in result
        assert Path(result["model_path"]).exists()

    def test_generate_from_description_phone_stand(self, temp_dir: Path):
        gen = ParametricGenerator()
        result = gen.generate_from_description(
            description="phone stand for desk",
            material="PLA",
            nozzle_diameter=0.4,
        )
        assert result["model_type"] == "phone_stand"
        assert "model_path" in result
        assert Path(result["model_path"]).exists()

    def test_generate_from_description_keychain(self, temp_dir: Path):
        gen = ParametricGenerator()
        result = gen.generate_from_description(
            description="keychain with my name",
            material="PLA",
            nozzle_diameter=0.4,
        )
        assert result["model_type"] == "keychain"
        assert "model_path" in result
        assert Path(result["model_path"]).exists()

    def test_generate_from_description_cable_clip(self, temp_dir: Path):
        gen = ParametricGenerator()
        result = gen.generate_from_description(
            description="cable clip for desk",
            material="PLA",
            nozzle_diameter=0.4,
        )
        assert result["model_type"] == "cable_clip"
        assert "model_path" in result
        assert Path(result["model_path"]).exists()

    def test_generate_from_description_clarification_gear(self, temp_dir: Path):
        """Audit fix: 'gear' should return custom with clarification, not silently generate a box."""
        gen = ParametricGenerator()
        result = gen.generate_from_description(
            description="gear",
            material="PLA",
            nozzle_diameter=0.4,
        )
        # It falls back to box but the requirements show clarification_needed
        assert result["requirements"]["clarification_needed"] is True
        assert result["requirements"]["category"] == "custom"

    def test_generate_from_description_clarification_puzzle(self, temp_dir: Path):
        """Audit fix: 'puzzle piece' should return custom with clarification."""
        gen = ParametricGenerator()
        result = gen.generate_from_description(
            description="puzzle piece",
            material="PLA",
            nozzle_diameter=0.4,
        )
        assert result["requirements"]["clarification_needed"] is True
        assert result["requirements"]["category"] == "custom"
