"""
Centralized logging configuration for Vibe Print.

All modules should import `get_logger()` and use the returned logger.
Logs include structured context: tool name, input summary, timestamp, duration.
"""

import logging
import sys
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Dict, Generator, Optional

# Context variables for per-request logging context
_tool_name: ContextVar[Optional[str]] = ContextVar("tool_name", default=None)
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class StructuredLogFormatter(logging.Formatter):
    """
    JSON-like structured formatter for production deployments.
    Falls back to a readable single-line format for development.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Build the base message
        parts = [
            f"{self.formatTime(record)}",
            f"[{record.levelname}]",
            f"[{record.name}]",
        ]

        # Add context if available
        tool = getattr(record, "tool_name", None) or _tool_name.get(None)
        req_id = getattr(record, "request_id", None) or _request_id.get(None)
        duration_ms = getattr(record, "duration_ms", None)

        if req_id:
            parts.append(f"[req:{req_id}]")
        if tool:
            parts.append(f"[tool:{tool}]")
        if duration_ms is not None:
            parts.append(f"[{duration_ms:.1f}ms]")

        parts.append(record.getMessage())

        # Add exception info if present
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            parts.append(f"\n{exc_text}")

        return " ".join(parts)

    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        """ISO-8601 style timestamp."""
        from datetime import datetime, timezone

        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def configure_logging(
    level: int = logging.INFO,
    log_format: str = "structured",
) -> None:
    """
    Configure root logging for Vibe Print.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR).
        log_format: "structured" for production, "simple" for development.
    """
    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers to avoid duplicates on reconfigure
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if log_format == "structured":
        handler.setFormatter(StructuredLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("paho.mqtt.client").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a module."""
    return logging.getLogger(name)


@contextmanager
def log_context(
    tool_name: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Generator[None, None, None]:
    """
    Set logging context for the current async task or thread.

    Usage:
        with log_context(tool_name="slice_model", request_id="abc123"):
            logger.info("Starting slice")
    """
    tokens = []
    if tool_name is not None:
        tokens.append(_tool_name.set(tool_name))
    if request_id is not None:
        tokens.append(_request_id.set(request_id))
    try:
        yield
    finally:
        for token in tokens:
            token.var.reset(token)


@contextmanager
def log_duration(
    logger: logging.Logger,
    operation: str,
    level: int = logging.INFO,
) -> Generator[Dict[str, Any], None, None]:
    """
    Context manager that logs the duration of an operation.

    Usage:
        with log_duration(logger, "slice_model") as ctx:
            result = do_work()
            ctx["output_size"] = len(result)
    """
    start = time.perf_counter()
    context: Dict[str, Any] = {}
    try:
        yield context
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        extra = {"duration_ms": elapsed_ms}
        context_str = " ".join(f"{k}={v}" for k, v in context.items())
        msg = f"{operation} completed in {elapsed_ms:.1f}ms"
        if context_str:
            msg += f" | {context_str}"
        logger.log(level, msg, extra=extra)


def summarize_input(**kwargs: Any) -> str:
    """
    Create a short, safe summary of tool inputs for logging.

    Truncates long strings and redacts sensitive values.
    """
    parts = []
    for key, value in kwargs.items():
        if key in ("access_code", "password", "token", "api_key"):
            parts.append(f"{key}=<redacted>")
        elif isinstance(value, str) and len(value) > 80:
            parts.append(f"{key}={value[:77]}...")
        else:
            parts.append(f"{key}={value}")
    return " | ".join(parts)
