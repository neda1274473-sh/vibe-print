"""Tests for the custom exception hierarchy."""

import pytest

from vibe_print.exceptions import (
    VibePrintError,
    InputValidationError,
    ModelGenerationError,
    ModelScalingError,
    ModelValidationError,
    SlicingError,
    PrinterConnectionError,
    CameraConnectionError,
    CameraError,
    DatabaseError,
    ConfigurationError,
)


class TestVibePrintError:
    """Tests for the base exception class."""

    def test_basic_instantiation(self):
        exc = VibePrintError("Something went wrong")
        assert str(exc) == "Something went wrong"
        assert exc.message == "Something went wrong"
        assert exc.details == {}
        assert exc.error_code == "UNKNOWN_ERROR"

    def test_with_details(self):
        exc = VibePrintError("Bad input", details={"field": "width", "value": -5})
        assert exc.details == {"field": "width", "value": -5}

    def test_with_error_code(self):
        exc = VibePrintError("Bad input", error_code="CUSTOM_CODE")
        assert exc.error_code == "CUSTOM_CODE"

    def test_to_dict(self):
        exc = VibePrintError(
            "Bad input",
            error_code="CUSTOM_CODE",
            details={"field": "width"},
        )
        d = exc.to_dict()
        assert d["success"] is False
        assert d["error"]["message"] == "Bad input"
        assert d["error"]["code"] == "CUSTOM_CODE"
        assert d["error"]["details"] == {"field": "width"}

    def test_inheritance_from_exception(self):
        assert issubclass(VibePrintError, Exception)


class TestInputValidationError:
    """Tests for InputValidationError."""

    def test_instantiation(self):
        exc = InputValidationError("width must be positive", details={"width": -1})
        assert isinstance(exc, VibePrintError)
        assert exc.message == "width must be positive"
        assert exc.details == {"width": -1}

    def test_to_dict(self):
        exc = InputValidationError("invalid", details={"x": 1})
        d = exc.to_dict()
        assert d["success"] is False
        assert d["error"]["code"] == "INPUT_VALIDATION_FAILED"
        assert d["error"]["message"] == "invalid"
        assert d["error"]["details"] == {"x": 1}


class TestModelGenerationError:
    """Tests for ModelGenerationError."""

    def test_instantiation(self):
        exc = ModelGenerationError("CadQuery failed", details={"model_type": "box"})
        assert isinstance(exc, VibePrintError)
        assert "CadQuery" in exc.message


class TestModelScalingError:
    """Tests for ModelScalingError."""

    def test_instantiation(self):
        exc = ModelScalingError("Scale failed", details={"factor": 0})
        assert isinstance(exc, VibePrintError)


class TestModelValidationError:
    """Tests for ModelValidationError."""

    def test_instantiation(self):
        exc = ModelValidationError("Not watertight", details={"file": "model.stl"})
        assert isinstance(exc, VibePrintError)


class TestSlicingError:
    """Tests for SlicingError."""

    def test_instantiation(self):
        exc = SlicingError("Slicer not found", details={"path": "/usr/bin/slicer"})
        assert isinstance(exc, VibePrintError)


class TestPrinterConnectionError:
    """Tests for PrinterConnectionError."""

    def test_instantiation(self):
        exc = PrinterConnectionError("Timeout", details={"host": "192.168.1.100"})
        assert isinstance(exc, VibePrintError)


class TestCameraError:
    """Tests for CameraError."""

    def test_instantiation(self):
        exc = CameraError("RTSP timeout", details={"host": "192.168.1.100"})
        assert isinstance(exc, VibePrintError)


class TestDatabaseError:
    """Tests for DatabaseError."""

    def test_instantiation(self):
        exc = DatabaseError("Connection failed", details={"path": "/tmp/db.sqlite"})
        assert isinstance(exc, VibePrintError)


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_instantiation(self):
        exc = ConfigurationError("Missing VIBE_PRINTER_IP", details={"env": "VIBE_PRINTER_IP"})
        assert isinstance(exc, VibePrintError)


class TestExceptionHierarchy:
    """Tests that all exceptions properly inherit from VibePrintError."""

    ALL_EXCEPTIONS = [
        InputValidationError,
        ModelGenerationError,
        ModelScalingError,
        ModelValidationError,
        SlicingError,
        PrinterConnectionError,
        CameraError,
        DatabaseError,
        ConfigurationError,
    ]

    @pytest.mark.parametrize("exc_class", ALL_EXCEPTIONS)
    def test_all_inherit_from_vibe_print_error(self, exc_class):
        assert issubclass(exc_class, VibePrintError)

    @pytest.mark.parametrize("exc_class", ALL_EXCEPTIONS)
    def test_all_have_to_dict(self, exc_class):
        exc = exc_class("test message", details={"key": "value"})
        d = exc.to_dict()
        assert "success" in d
        assert "error" in d
        assert "code" in d["error"]
        assert "message" in d["error"]
        assert "details" in d["error"]
        assert d["error"]["message"] == "test message"
        assert d["error"]["details"] == {"key": "value"}
