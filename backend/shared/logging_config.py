"""
PCB Builder - Structured Logging Configuration
Uses structlog for structured, JSON-formatted logging with correlation IDs.
"""

import logging
import sys
import uuid
from typing import Any

import structlog
from structlog.processors import JSONRenderer


def add_correlation_id(logger, method_name, event_dict):
    """Add correlation_id to log entries if available."""
    from contextvars import ContextVar
    _correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
    cid = _correlation_id.get()
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict


def configure_logging():
    """Configure structured logging for production."""
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.ExtraAdder(),
        add_correlation_id,
        structlog.processors.dict_tracebacks,
    ]

    structlog.configure(
        processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)

    # Reduce noise from third-party libs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return structlog.get_logger()


logger = configure_logging()
