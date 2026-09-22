"""Integration tests for MCP server tools."""

import json
import tempfile
from pathlib import Path

import pytest

from vibe_print.server import (
    suggest_model,
    estimate_print_time,
    check_printer_compatibility,
    get_printing_guide,
    generate_model,
    generate_from_description,
    analyze_model,
    scale_model,
    export_model,
    slice_model,
    validate_model,
    get_slicing_profiles,
    estimate_slicing,
    preview_gcode,
    repair_model,
    connect_printer,
    disconnect_printer,
    get_printer_status,
    start_print,
    pause_print,
    resume_print,
    cancel_print,
    connect_camera,
    capture_frame,
    get_camera_status,
    create_iteration,
    record_outcome,
    get_iteration_history,
    compare_iterations,
    get_improvement_recommendations,
    export_history,
    get_model_statistics,
    analyze_quality,
    SuggestModelInput,
    EstimatePrintTimeInput,
    CheckPrinterCompatibilityInput,
    GetPrintingGuideInput,
    GenerateModelInput,
    GenerateFromDescriptionInput,
    AnalyzeModelInput,
    ScaleModelInput,
    ExportModelInput,
    SliceModelInput,
    ValidateModelInput,
    GetSlicingProfilesInput,
    EstimateSlicingInput,
    PreviewGcodeInput,
    RepairModelInput,
    ConnectPrinterInput,
    DisconnectPrinterInput,
    GetPrinterStatusInput,
    StartPrintInput,
    PausePrintInput,
    ResumePrintInput,
    CancelPrintInput,
    ConnectCameraInput,
    CaptureFrameInput,
    GetCameraStatusInput,
    CreateIterationInput,
    RecordOutcomeInput,
    GetIterationHistoryInput,
    CompareIterationsInput,
    GetImprovementRecommendationsInput,
    ExportHistoryInput,
    GetModelStatisticsInput,
    AnalyzeQualityInput,
)


class TestWizardTools:
    def test_suggest_model(self):
        result = suggest_model(SuggestModelInput(description="I need a tube squeezer for a 65mm lotion bottle"))
        assert result["success"] is True
        assert result["count"] > 0
        assert any("tube_squeezer" in s["category"] for s in result["suggestions"])

    def test_estimate_print_time(self):
        result = estimate_print_time(EstimatePrintTimeInput(volume_cm3=10.0))
        assert result["success"] is True
        assert "estimate" in result
        assert result["estimate"]["estimated_time_minutes"] > 0

    def test_check_printer_compatibility(self):
        result = check_printer_compatibility(
            CheckPrinterCompatibilityInput(
                model_width_mm=50.0, model_depth_mm=30.0, model_height_mm=20.0
            )
        )
        assert result["success"] is True
        assert result["compatibility"]["compatible"] is True


    def test_get_printing_guide(self):
        result = get_printing_guide(GetPrintingGuideInput(category="tube_squeezer"))
        assert result["success"] is True
        assert "guide" in result


class TestGenerationTools:
    def test_generate_model_box(self, tmp_path):
        result = generate_model(
            GenerateModelInput(
                model_type="box",
                parameters={"width": 10, "height": 5, "depth": 3},
                output_name=str(tmp_path / "test_box"),
            )
        )
        assert result["success"] is True
        assert Path(result["model_path"]).exists()

    def test_generate_from_description(self, tmp_path):
        result = generate_from_description(
            GenerateFromDescriptionInput(
                description="tube squeezer for 65mm lotion bottle",
                material="PLA",
            )
        )
        assert result["success"] is True
        assert "model_path" in result
        assert Path(result["model_path"]).exists()

    def test_analyze_model(self, tmp_path):
        gen = generate_model(
            GenerateModelInput(
                model_type="box",
                parameters={"width": 10, "height": 5, "depth": 3},
                output_name=str(tmp_path / "analyze_test"),
            )
        )
        result = analyze_model(AnalyzeModelInput(model_path=gen["model_path"]))
        assert result["success"] is True
        mesh_info = result["analysis"]["mesh_info"]
        assert mesh_info["volume_cm3"] > 0
        assert mesh_info["is_watertight"] is True


    def test_scale_model(self, tmp_path):
        gen = generate_model(
            GenerateModelInput(
                model_type="box",
                parameters={"width": 10, "height": 5, "depth": 3},
                output_name=str(tmp_path / "scale_test"),
            )
        )
        result = scale_model(
            ScaleModelInput(model_path=gen["model_path"], scale_factor=0.5)
        )
        assert result["success"] is True
        assert Path(result["scaled_model_path"]).exists()

    def test_export_model(self, tmp_path):
        gen = generate_model(
            GenerateModelInput(
                model_type="box",
                parameters={"width": 10, "height": 5, "depth": 3},
                output_name=str(tmp_path / "export_test"),
            )
        )
        out = tmp_path / "exported.stl"
        result = export_model(
            ExportModelInput(model_path=gen["model_path"], output_path=str(out))
        )
        assert result["success"] is True
        assert out.exists()


class TestPreparationTools:
    def test_slice_model_mock(self, tmp_path):
        gen = generate_model(
            GenerateModelInput(
                model_type="box",
                parameters={"width": 10, "height": 5, "depth": 3},
                output_name=str(tmp_path / "slice_test"),
            )
        )
        result = slice_model(
            SliceModelInput(
                model_path=gen["model_path"],
                quality="standard",
                export_gcode=True,
                export_3mf=False,
            )
        )
        assert result["success"] is True
        assert "result" in result
        # Should be in mock mode since PrusaSlicer is not available
        assert result["result"]["mode"] == "MOCK"

    def test_validate_model(self, tmp_path):
        gen = generate_model(
            GenerateModelInput(
                model_type="box",
                parameters={"width": 10, "height": 5, "depth": 3},
                output_name=str(tmp_path / "validate_test"),
            )
        )
        result = validate_model(ValidateModelInput(model_path=gen["model_path"]))
        assert result["success"] is True
        assert result["valid"] is True
        assert len(result["issues"]) == 0

    def test_get_slicing_profiles(self):
        result = get_slicing_profiles(GetSlicingProfilesInput())
        assert result["success"] is True
        assert len(result["profiles"]) == 4

    def test_estimate_slicing(self, tmp_path):
        gen = generate_model(
            GenerateModelInput(
                model_type="box",
                parameters={"width": 10, "height": 5, "depth": 3},
                output_name=str(tmp_path / "est_test"),
            )
        )
        result = estimate_slicing(
            EstimateSlicingInput(model_path=gen["model_path"])
        )
        assert result["success"] is True
        assert result["estimated_slicing_time_sec"] > 0

    def test_preview_gcode(self, tmp_path):
        gcode = tmp_path / "test.gcode"
        gcode.write_text("G1 X10 Y20\nG1 X30 Y40\nM104 S200\n")
        result = preview_gcode(PreviewGcodeInput(gcode_path=str(gcode), max_lines=2))
        assert result["success"] is True
        assert len(result["lines"]) == 2

    def test_repair_model_already_good(self, tmp_path):
        gen = generate_model(
            GenerateModelInput(
                model_type="box",
                parameters={"width": 10, "height": 5, "depth": 3},
                output_name=str(tmp_path / "repair_test"),
            )
        )
        result = repair_model(RepairModelInput(model_path=gen["model_path"]))
        assert result["success"] is True
        assert result["repaired"] is False


class TestPrinterTools:
    def test_connect_printer_simulation(self):
        result = connect_printer(ConnectPrinterInput())
        assert result["success"] is True
        assert result["mode"] == "SIMULATION"

    def test_get_printer_status_not_connected(self):
        # Ensure no global printer state from previous tests
        import vibe_print.server as srv
        srv._printer = None
        result = get_printer_status(GetPrinterStatusInput())
        assert result["success"] is False
        assert "not connected" in result["error"]["message"].lower()

    def test_printer_lifecycle(self):
        connect_printer(ConnectPrinterInput())
        result = get_printer_status(GetPrinterStatusInput())
        assert result["success"] is True
        assert "status" in result
        disconnect_printer(DisconnectPrinterInput())


class TestCameraTools:
    def test_connect_camera_simulation(self):
        result = connect_camera(ConnectCameraInput())
        assert result["success"] is True

    def test_get_camera_status_not_connected(self):
        import vibe_print.server as srv
        srv._camera = None
        result = get_camera_status(GetCameraStatusInput())
        assert result["success"] is True
        assert result["connected"] is False

    def test_capture_frame_simulation(self):
        connect_camera(ConnectCameraInput())
        result = capture_frame(CaptureFrameInput())
        assert result["success"] is True
        assert result["width"] == 640


class TestIterationTools:
    def test_create_and_record(self, tmp_path):
        gen = generate_model(
            GenerateModelInput(
                model_type="box",
                parameters={"width": 10, "height": 5, "depth": 3},
                output_name=str(tmp_path / "iter_test"),
            )
        )
        result = create_iteration(
            CreateIterationInput(
                model_name="test_box",
                model_path=gen["model_path"],
                scale_factor=1.0,
            )
        )
        assert result["success"] is True
        iteration_id = result["iteration"]["iteration_id"]

        record = record_outcome(
            RecordOutcomeInput(
                iteration_id=iteration_id,
                status="success",
                quality_score=85.0,
                notes="Good print",
            )
        )
        assert record["success"] is True
        assert record["iteration"]["status"] == "success"

    def test_get_iteration_history(self):
        result = get_iteration_history(GetIterationHistoryInput(limit=5))
        assert result["success"] is True
        assert "iterations" in result

    def test_get_model_statistics(self):
        result = get_model_statistics(GetModelStatisticsInput(model_name="test_box"))
        assert result["success"] is True
        assert "statistics" in result

    def test_export_history(self, tmp_path):
        out = tmp_path / "history.json"
        result = export_history(ExportHistoryInput(output_path=str(out)))
        assert result["success"] is True
        assert Path(result["export_path"]).exists()


class TestEndToEndTubeSqueezer:
    def test_full_pipeline(self, tmp_path):
        """End-to-end: description -> generation -> analysis -> slicing."""
        # 1. Generate from description
        gen = generate_from_description(
            GenerateFromDescriptionInput(
                description="tube squeezer for 65mm lotion bottle",
                material="PLA",
            )
        )
        assert gen["success"] is True
        model_path = gen["model_path"]
        assert Path(model_path).exists()

        # 2. Analyze
        analysis = analyze_model(AnalyzeModelInput(model_path=model_path))
        assert analysis["success"] is True
        mesh_info = analysis["analysis"]["mesh_info"]
        assert mesh_info["volume_cm3"] > 0
        assert mesh_info["is_watertight"] is True


        # 3. Validate
        validation = validate_model(ValidateModelInput(model_path=model_path))
        assert validation["success"] is True
        assert validation["valid"] is True

        # 4. Slice (mock mode expected)
        slicing = slice_model(
            SliceModelInput(
                model_path=model_path,
                quality="standard",
                export_gcode=True,
                export_3mf=False,
            )
        )
        assert slicing["success"] is True
        assert slicing["result"]["mode"] == "MOCK"
        assert slicing["result"]["output_gcode"] is not None


        # 5. Create iteration
        iteration = create_iteration(
            CreateIterationInput(
                model_name="tube_squeezer_65mm",
                model_path=model_path,
                scale_factor=1.0,
                preset_name="standard",
            )
        )
        assert iteration["success"] is True
        iteration_id = iteration["iteration"]["iteration_id"]

        # 6. Record outcome
        record = record_outcome(
            RecordOutcomeInput(
                iteration_id=iteration_id,
                status="success",
                quality_score=90.0,
                notes="Excellent fit for 65mm bottle",
            )
        )
        assert record["success"] is True

        # 7. Analyze quality (simulation mode)
        quality = analyze_quality(
            AnalyzeQualityInput(iteration_id=iteration_id)
        )
        assert quality["success"] is True
        assert quality["mode"] == "SIMULATION"
        assert quality["quality_score"] == 90.0


