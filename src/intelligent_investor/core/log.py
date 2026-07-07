# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Logging configuration using loguru.
Provides flexible logging with console and file output, rotation, retention, and compression.
"""
import logging
import sys
from pathlib import Path
from types import FrameType

from loguru import logger

from intelligent_investor.core.config import config

# Log format constants
APP_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[name]}</cyan>:<cyan>{function}</cyan>:"
    "<cyan>{line}</cyan> - <level>{message}</level>\n"
)

INTERCEPTED_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:"
    "<cyan>{line}</cyan> - <level>{message}</level>\n"
)


class InterceptHandler(logging.Handler):
    """
    Intercept standard logging messages and redirect them to loguru.
    This allows Flask and other libraries using standard logging to use loguru.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame: FrameType | None = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


class LoggerManager:
    """
    Manages application logging using loguru.

    Features:
    - Console and/or file logging
    - Log rotation (default 10MB)
    - Log retention (default 7 days)
    - Log compression (zip)
    - Configurable log level
    - Contextual logging with class/function/line information
    - Intercepts Flask and standard library logging
    """

    def __init__(
        self,
        level: str = "INFO",
        console: bool = True,
        file: str | None = None,
        rotation: str = "10 MB",
        retention: str = "7 days",
        compression: str = "zip",
    ) -> None:
        """
        Initialize the logger manager.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            console: Enable console logging (stdout)
            file: Log file path (None to disable file logging)
            rotation: Log rotation size (e.g., "10 MB", "100 MB", "1 GB")
            retention: Log retention period (e.g., "7 days", "1 week", "1 month")
            compression: Compression format for rotated logs ("zip", "gz", "bz2", "xz")
        """
        self.level = level.upper()
        self.console = console
        self.file = file
        self.rotation = rotation
        self.retention = retention
        self.compression = compression

        # Remove default logger
        logger.remove()

        # Configure logger
        self._configure_logger()

        # Intercept standard logging
        self._intercept_standard_logging()

    def _configure_logger(self) -> None:
        """Configure loguru logger based on settings."""

        def format_record(record) -> str:
            format_map: dict[bool, str] = {
                True: APP_LOG_FORMAT,
                False: INTERCEPTED_LOG_FORMAT,
            }
            return format_map["name" in record["extra"]]

        handlers = []

        if self.console:
            handlers.append(
                {
                    "sink": sys.stdout,
                    "format": format_record,
                    "level": self.level,
                    "colorize": True,
                }
            )

        if self.file:
            log_path: Path = Path(self.file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            handlers.append(
                {
                    "sink": self.file,
                    "format": format_record,
                    "level": self.level,
                    "rotation": self.rotation,
                    "retention": self.retention,
                    "compression": self.compression,
                    "enqueue": True,  # Thread-safe logging
                }
            )

        for handler_config in handlers:
            logger.add(**handler_config)  # type: ignore[arg-type]

    def _intercept_standard_logging(self) -> None:
        """Intercept standard library logging and redirect to loguru."""
        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

        for logger_name in ["werkzeug", "flask.app"]:
            log = logging.getLogger(name=logger_name)
            log.handlers = [InterceptHandler()]
            log.propagate = False

    @staticmethod
    def get_logger(name: str):
        """
        Get a logger instance with a specific name (typically class name).

        Args:
            name: Logger name (usually __name__ or class name)

        Returns:
            Logger instance bound with the name

        Usage:
            class MyService:
                def __init__(self):
                    self.logger = LoggerManager.get_logger(self.__class__.__name__)

                def my_method(self):
                    self.logger.info("Processing data")
        """
        return logger.bind(name=name)


def setup_logging() -> LoggerManager:
    """
    Setup application logging from config.yaml settings.

    Should be called once at application startup.

    Returns:
        LoggerManager instance

    Usage:
        from core.log import setup_logging

        setup_logging()
    """
    log_cfg = config.log
    return LoggerManager(
        level=log_cfg.level,
        console=log_cfg.console,
        file=log_cfg.file,
        rotation=log_cfg.rotation,
        retention=log_cfg.retention,
        compression=log_cfg.compression,
    )
