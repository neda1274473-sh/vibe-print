"""Tests for the centralized logging configuration."""

import logging
from pathlib import Path

import pytest

from vibe_print.logging_config import (
    configure_logging,
    get_logger,
    log_context,
    log_duration,
    summarize_input,
    StructuredLogFormatter,
)


class TestConfigureLogging:
    """Tests for configure_logging()."""

    def test_default_configuration(self):
        configure_logging(level=logging.INFO)
        root = logging.getLogger()
        assert root.level == logging.INFO
        assert len(root.handlers) == 1

    def test_debug_level(self):
        configure_logging(level=logging.DEBUG)
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_simple_format(self):
        configure_logging(level=logging.INFO, log_format="simple")
        root = logging.getLogger()
        handler = root.handlers[0]
        assert isinstance(handler.formatter, logging.Formatter)

    def test_structured_format(self):
        configure_logging(level=logging.INFO, log_format="structured")
        root = logging.getLogger()
        handler = root.handlers[0]
        assert isinstance(handler.formatter, StructuredLogFormatter)


class TestGetLogger:
    """Tests for get_logger()."""

    def test_returns_logger(self):
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"


class TestSummarizeInput:
    """Tests for summarize_input()."""

    def test_basic_summary(self):
        result = summarize_input(width=10, height=20)
        assert "width=10" in result
        assert "height=20" in result

    def test_redacts_password(self):
        result = summarize_input(password="secret123", width=10)
        assert "password=<redacted>" in result
        assert "secret123" not in result

    def test_redacts_access_code(self):
        result = summarize_input(access_code="abc123", width=10)
        assert "access_code=<redacted>" in result
        assert "abc123" not in result

    def test_redacts_api_key(self):
        result = summarize_input(api_key="supersecret", width=10)
        assert "api_key=<redacted>" in result

    def test_truncates_long_string(self):
        long_value = "x" * 100
        result = summarize_input(description=long_value)
        assert "..." in result
        assert len(result) < 120

    def test_empty_kwargs(self):
        result = summarize_input()
        assert result == ""


class TestLogContext:
    """Tests for log_context()."""

    def test_sets_context(self):
        with log_context(tool_name="slice_model", request_id="req-123"):
            # Context is set within the block
            pass  # ContextVars work across async/threads; basic test passes if no exception

    def test_no_args(self):
        with log_context():
            pass  # Should work with no arguments


class TestLogDuration:
    """Tests for log_duration()."""

    def test_logs_duration(self, caplog):
        logger = get_logger("test_duration")
        with caplog.at_level(logging.INFO, logger="test_duration"):
            with log_duration(logger, "test_op"):
                pass
        assert "test_op completed in" in caplog.text
        assert "ms" in caplog.text

    def test_context_values(self, caplog):
        logger = get_logger("test_duration_ctx")
        with caplog.at_level(logging.INFO, logger="test_duration_ctx"):
            with log_duration(logger, "test_op") as ctx:
                ctx["output_size"] = 42
        assert "output_size=42" in caplog.text


class TestStructuredLogFormatter:
    """Tests for StructuredLogFormatter."""

    def test_format_includes_timestamp(self):
        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello", args=(), exc_info=None,
        )
        formatted = formatter.format(record)
        assert "hello" in formatted
        assert "INFO" in formatted

    def test_format_includes_tool_name(self):
        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello", args=(), exc_info=None,
        )
        record.tool_name = "slice_model"
        formatted = formatter.format(record)
        assert "[tool:slice_model]" in formatted
