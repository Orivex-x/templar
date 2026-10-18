"""
Templar structured logging system.

Provides centralized logging with support for multiple handlers,
log levels, and performance tracking.
"""

import sys
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from functools import wraps
import time

sys.dont_write_bytecode = True


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured data."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra context if provided
        if hasattr(record, "context") and record.context:
            log_data["context"] = record.context
        
        return json.dumps(log_data)


class Logger:
    """
    Central logger for the Templar framework.
    
    Supports multiple handlers, structured logging, and performance tracking.
    """
    
    _instance: Optional["Logger"] = None
    _loggers: Dict[str, logging.Logger] = {}
    
    def __init__(self, name: str = "templar", level: str = "INFO"):
        """
        Initialize logger.
        
        Args:
            name: Logger name
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.name = name
        self.level = getattr(logging, level.upper(), logging.INFO)
        self._setup_root_logger()
    
    @classmethod
    def get_instance(cls, name: str = "templar", level: str = "INFO") -> "Logger":
        """Get or create a singleton logger instance."""
        if cls._instance is None:
            cls._instance = cls(name, level)

        return cls._instance
    
    def _setup_root_logger(self) -> None:
        """Set up root logger configuration."""
        self.root_logger = logging.getLogger(self.name)
        self.root_logger.setLevel(self.level)
        
        # Prevent propagation to avoid duplicate logs
        self.root_logger.propagate = False
        
        # Clear existing handlers
        self.root_logger.handlers.clear()
        
        # Add default console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        self.root_logger.addHandler(console_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a named logger.
        
        Args:
            name: Logger name (typically module name)
            
        Returns:
            logging.Logger instance
        """
        if name not in self._loggers:
            logger = logging.getLogger(f"{self.name}.{name}")
            logger.setLevel(self.level)
            logger.add_file_handler = self.add_file_handler
            logger.add_handler = self.add_handler
            logger.set_templar_level = self.set_level
            self._loggers[name] = logger

        return self._loggers[name]

    def debug(self, *args, **kwargs) -> None:
        self.root_logger.debug(*args, **kwargs)

    def info(self, *args, **kwargs) -> None:
        self.root_logger.info(*args, **kwargs)

    def warning(self, *args, **kwargs) -> None:
        self.root_logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs) -> None:
        self.root_logger.error(*args, **kwargs)

    def critical(self, *args, **kwargs) -> None:
        self.root_logger.critical(*args, **kwargs)

    def exception(self, *args, **kwargs) -> None:
        self.root_logger.exception(*args, **kwargs)
    
    def add_file_handler(
        self,
        log_file: Path | str,
        level: str = "INFO",
        json_format: bool = False
    ) -> None:
        """
        Add a file handler to the logger.
        
        Args:
            log_file: Path to log file
            level: Log level for this handler
            json_format: Use JSON formatting if True
        """
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(log_file)
        handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        if json_format:
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        
        handler.setFormatter(formatter)
        self.root_logger.addHandler(handler)
    
    def add_handler(self, handler: logging.Handler, formatter: logging.Formatter = None) -> None:
        """
        Add a custom handler to the root logger.
        
        Args:
            handler: logging.Handler instance
            formatter: Optional formatter
        """
        if formatter:
            handler.setFormatter(formatter)
        self.root_logger.addHandler(handler)
    
    def set_level(self, level: str) -> None:
        """
        Set the log level.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        level_obj = getattr(logging, level.upper(), logging.INFO)
        self.root_logger.setLevel(level_obj)
        for handler in self.root_logger.handlers:
            handler.setLevel(level_obj)


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("Message")
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        logging.Logger instance
    """
    return Logger.get_instance().get_logger(name)


def log_execution_time(logger: logging.Logger = None, threshold_ms: float = 100):
    """
    Decorator to log function execution time.
    
    Args:
        logger: Optional logger instance (uses root if None)
        threshold_ms: Only log if execution time exceeds threshold
        
    Usage:
        @log_execution_time(threshold_ms=50)
        def my_function():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger or get_logger(func.__module__)
            
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            if elapsed_ms >= threshold_ms:
                _logger.debug(
                    f"{func.__name__} executed in {elapsed_ms:.2f}ms",
                    extra={"context": {"function": func.__name__, "elapsed_ms": elapsed_ms}}
                )
            
            return result

        return wrapper

    return decorator


def log_with_context(context: Dict[str, Any]):
    """
    Decorator to add context to logs.
    
    Args:
        context: Dictionary of context data
        
    Usage:
        @log_with_context({"user_id": 123})
        def process_user():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            extra = {"context": context}
            logger.info(f"Executing {func.__name__}", extra=extra)

            return func(*args, **kwargs)

        return wrapper

    return decorator


# Initialize default logger
DEFAULT_LOGGER = Logger.get_instance()
