import json
import logging

import pytest

from app.config.settings import Settings
from app.observability.logging import (
    JSONFormatter,
    configure_logging,
    get_logger,
)


def test_json_formatter_outputs_structured_context() -> None:
    record = logging.LogRecord(
        name="sentinel_ai.api",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Query completed.",
        args=(),
        exc_info=None,
    )

    record.event = "query_completed"
    record.thread_id = "logging-test-thread"
    record.trace_id = "trace-logging-001"
    record.duration_ms = 123.45

    payload = json.loads(
        JSONFormatter().format(
            record
        )
    )

    assert payload["level"] == "INFO"
    assert payload["logger"] == "sentinel_ai.api"
    assert payload["message"] == "Query completed."
    assert payload["event"] == "query_completed"
    assert payload["thread_id"] == "logging-test-thread"
    assert payload["trace_id"] == "trace-logging-001"
    assert payload["duration_ms"] == 123.45
    assert payload["timestamp"]


def test_configure_logging_uses_configured_level() -> None:
    logger = logging.getLogger(
        "sentinel_ai"
    )

    original_handlers = list(
        logger.handlers
    )
    original_level = logger.level
    original_propagate = logger.propagate

    try:
        logger.handlers.clear()

        configured = configure_logging(
            Settings(
                _env_file=None,
                log_level="DEBUG",
            )
        )

        assert configured is logger
        assert configured.level == logging.DEBUG
        assert configured.propagate is False
        assert len(configured.handlers) == 1
        assert configured.handlers[0].level == logging.DEBUG
        assert isinstance(
            configured.handlers[0].formatter,
            JSONFormatter,
        )
    finally:
        logger.handlers.clear()
        logger.handlers.extend(
            original_handlers
        )
        logger.setLevel(
            original_level
        )
        logger.propagate = original_propagate


def test_get_logger_uses_sentinel_namespace() -> None:
    logger = get_logger(
        "api"
    )

    assert logger.name == "sentinel_ai.api"


def test_get_logger_rejects_blank_name() -> None:
    with pytest.raises(
        ValueError,
        match="Logger name cannot be blank",
    ):
        get_logger(
            "   "
        )