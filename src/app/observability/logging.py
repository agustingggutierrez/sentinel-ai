import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.config.settings import Settings

_LOGGER_NAMESPACE = "sentinel_ai"

_CONTEXT_FIELDS = (
    "event",
    "thread_id",
    "trace_id",
    "duration_ms",
    "error_code",
    "llm_provider",
    "app_env",
)


class JSONFormatter(logging.Formatter):
    """Render SentinelAI log records as structured JSON."""

    def format(
        self,
        record: logging.LogRecord,
    ) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(
                UTC
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field in _CONTEXT_FIELDS:
            value = getattr(
                record,
                field,
                None,
            )

            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = (
                self.formatException(
                    record.exc_info
                )
            )

        return json.dumps(
            payload,
            ensure_ascii=False,
            default=str,
        )


def configure_logging(
    settings: Settings,
) -> logging.Logger:
    """Configure the SentinelAI application logger."""

    logger = logging.getLogger(
        _LOGGER_NAMESPACE
    )

    logger.setLevel(
        settings.log_level
    )

    logger.propagate = False

    if logger.handlers:
        for handler in logger.handlers:
            handler.setLevel(
                settings.log_level
            )

        return logger

    handler = logging.StreamHandler()

    handler.setLevel(
        settings.log_level
    )

    handler.setFormatter(
        JSONFormatter()
    )

    logger.addHandler(
        handler
    )

    return logger


def get_logger(
    name: str,
) -> logging.Logger:
    """Return a namespaced SentinelAI logger."""

    normalized_name = name.strip()

    if not normalized_name:
        raise ValueError(
            "Logger name cannot be blank."
        )

    return logging.getLogger(
        f"{_LOGGER_NAMESPACE}.{normalized_name}"
    )