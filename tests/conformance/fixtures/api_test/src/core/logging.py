"""Core logging module using structlog for structured JSON/console logging."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

import structlog
from structlog.stdlib import ProcessorFormatter

from src.core.config import settings

if TYPE_CHECKING:
    from collections.abc import Callable

    from structlog.types import Processor, WrappedLogger


def get_log_level(log_level: str) -> int:
    """Convert log level string to logging level constant.

    Args:
        log_level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        Logging level constant.

    Raises:
        ValueError: If log_level is not a valid Python logging level.
    """
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    normalized = log_level.lower()
    if normalized not in level_map:
        valid_levels = ", ".join(level_map.keys())
        raise ValueError(
            f"Invalid log level '{log_level}'. "
            f"Expected one of: {valid_levels}"
        )
    return level_map[normalized]


def get_processor_pipeline() -> list[Processor]:
    """Build the structlog processor pipeline.

    Returns:
        List of processors for structlog configuration.
    """
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.PATHNAME,
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]

    if settings.log_format == "json":
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        # Console format with colorization
        renderer = structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.RichTracebackFormatter(),
        )

    return shared_processors + [renderer]


def setup_logging() -> None:
    """Configure structlog and stdlib logging.

    This function sets up the structlog processor pipeline and wraps
    stdlib logging so that logs from third-party libraries (uvicorn,
    SQLAlchemy, etc.) also pass through structlog.
    """
    log_level = get_log_level(settings.log_level)

    # Build the processor pipeline
    processors = get_processor_pipeline()

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use structlog's ProcessorFormatter
    # This ensures third-party library logs pass through structlog
    formatter = ProcessorFormatter(
        processor=processors[-1],  # Use the final renderer
        foreign_pre_chain=[
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.PATHNAME,
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Also configure uvicorn and sqlalchemy loggers explicitly
    # to ensure they use our formatter
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy"):
        logging.getLogger(logger_name).setLevel(log_level)


def get_logger(name: str | None = None) -> WrappedLogger:
    """Get a bound structlog logger instance.

    Args:
        name: Optional logger name. If None, uses 'app' as default.

    Returns:
        A structlog logger instance.
    """
    logger_name = name if name else "app"
    return structlog.get_logger(logger_name)
