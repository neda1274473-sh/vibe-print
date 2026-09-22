"""
Custom exception hierarchy for Vibe Print.

All errors returned to MCP clients follow a structured format.
Never expose raw tracebacks to clients.
"""

from typing import Any, Dict, Optional


class VibePrintError(Exception):
    """Base exception for all Vibe Print errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a structured dict for MCP responses."""
        return {
            "success": False,
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
            },
        }


# -----------------------------------------------------------------------------
# Model / Generation errors
# -----------------------------------------------------------------------------


class ModelGenerationError(VibePrintError):
    """Failed to generate a 3D model."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="MODEL_GENERATION_FAILED", details=details)


class ModelValidationError(VibePrintError):
    """Model failed validation (non-manifold, too large, etc.)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="MODEL_VALIDATION_FAILED", details=details)


class ModelScalingError(VibePrintError):
    """Failed to scale a model."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="MODEL_SCALING_FAILED", details=details)


# -----------------------------------------------------------------------------
# Slicer errors
# -----------------------------------------------------------------------------


class SlicingError(VibePrintError):
    """Slicer CLI invocation or parsing failed."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="SLICING_FAILED", details=details)


class SlicerNotFoundError(VibePrintError):
    """Slicer executable not found or not configured."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="SLICER_NOT_FOUND", details=details)


# -----------------------------------------------------------------------------
# Printer / MQTT errors
# -----------------------------------------------------------------------------


class PrinterConnectionError(VibePrintError):
    """Could not connect to printer via MQTT."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="PRINTER_CONNECTION_FAILED", details=details)


class PrinterCommandError(VibePrintError):
    """Printer rejected or failed to execute a command."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="PRINTER_COMMAND_FAILED", details=details)


class PrinterNotReadyError(VibePrintError):
    """Printer is not in a state that accepts the requested command."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="PRINTER_NOT_READY", details=details)


# -----------------------------------------------------------------------------
# Camera errors
# -----------------------------------------------------------------------------


class CameraConnectionError(VibePrintError):
    """Could not connect to camera stream."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="CAMERA_CONNECTION_FAILED", details=details)


# Backwards compatibility alias
CameraError = CameraConnectionError


class CameraCaptureError(VibePrintError):
    """Failed to capture a frame from the camera."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="CAMERA_CAPTURE_FAILED", details=details)


class ImageAnalysisError(VibePrintError):
    """Failed to analyze a captured image."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="IMAGE_ANALYSIS_FAILED", details=details)


# -----------------------------------------------------------------------------
# Configuration / Input errors
# -----------------------------------------------------------------------------


class ConfigurationError(VibePrintError):
    """Invalid or missing configuration."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="CONFIGURATION_ERROR", details=details)


class InputValidationError(VibePrintError):
    """User input failed validation beyond Pydantic."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="INPUT_VALIDATION_FAILED", details=details)


# -----------------------------------------------------------------------------
# Workflow / State errors
# -----------------------------------------------------------------------------


class WorkflowStateError(VibePrintError):
    """Workflow is in an invalid state for the requested operation."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="WORKFLOW_STATE_ERROR", details=details)


class DatabaseError(VibePrintError):
    """Database operation failed."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="DATABASE_ERROR", details=details)


# -----------------------------------------------------------------------------
# Utility helpers
# -----------------------------------------------------------------------------


def format_error_response(error: Exception) -> Dict[str, Any]:
    """
    Convert any exception into a standardized MCP error response.

    If the exception is a VibePrintError, use its structured format.
    Otherwise, wrap it generically (hiding raw tracebacks).
    """
    if isinstance(error, VibePrintError):
        return error.to_dict()

    return {
        "success": False,
        "error": {
            "code": "INTERNAL_ERROR",
            "message": str(error),
            "details": {},
        },
    }
