"""
Logging configuration for the application.
Provides structured logging with color formatting.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import settings


# Color codes for terminal output
class LogColors:
    """ANSI color codes for terminal output."""
    GREY = "\x1b[38;21m"
    BLUE = "\x1b[38;5;39m"
    YELLOW = "\x1b[38;5;226m"
    RED = "\x1b[38;5;196m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color coding for different log levels."""
    
    FORMATS = {
        logging.DEBUG: LogColors.GREY + "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s" + LogColors.RESET,
        logging.INFO: LogColors.BLUE + "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s" + LogColors.RESET,
        logging.WARNING: LogColors.YELLOW + "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s" + LogColors.RESET,
        logging.ERROR: LogColors.RED + "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s" + LogColors.RESET,
        logging.CRITICAL: LogColors.BOLD_RED + "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s" + LogColors.RESET,
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Setup logging configuration for the application.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                  If None, uses settings.LOG_LEVEL.
    """
    # Determine log level
    level = log_level or settings.LOG_LEVEL
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Console handler with color formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(ColoredFormatter())
    root_logger.addHandler(console_handler)
    
    # File handler (without colors)
    if settings.is_production or True:  # Always log to file
        log_file = log_dir / f"dce_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Log startup message
    root_logger.info(f"Logging initialized at {level.upper()} level")
    root_logger.info(f"Environment: {settings.ENV}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Name of the module (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)