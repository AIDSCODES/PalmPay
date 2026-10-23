"""Logging configuration"""
import logging
import sys
from typing import Any
from app.core.config import settings


class RequestIdFilter(logging.Filter):
    """Add request_id to log records"""
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = getattr(record, 'request_id', 'N/A')
        return True


def setup_logging() -> None:
    """Configure application logging"""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(request_id)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [handler]

    # Reduce noise from third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING if not settings.DEBUG else logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)