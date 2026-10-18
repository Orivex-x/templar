"""Unit tests for Logger module."""

import pytest
import logging
from pathlib import Path
from templar.core.Logger import Logger, get_logger, log_execution_time, log_with_context


@pytest.mark.unit
class TestLogger:
    """Tests for Logger class."""
    
    def test_logger_singleton(self):
        """Test that Logger is a singleton."""
        logger1 = Logger.get_instance()
        logger2 = Logger.get_instance()

        assert logger1 is logger2
    
    def test_get_named_logger(self):
        """Test getting a named logger."""
        logger = get_logger("test_module")

        assert logger is not None
        assert isinstance(logger, logging.Logger)
    
    def test_get_named_logger_caching(self):
        """Test that named loggers are cached."""
        logger1 = get_logger("cached_module")
        logger2 = get_logger("cached_module")

        assert logger1 is logger2
    
    def test_logger_set_level(self):
        """Test setting logger level."""
        logger = Logger.get_instance()
        logger.set_level("DEBUG")

        assert logger.root_logger.level == logging.DEBUG
        
        logger.set_level("WARNING")

        assert logger.root_logger.level == logging.WARNING
    
    def test_logger_add_file_handler(self, tmp_path):
        """Test adding file handler."""
        log_file = tmp_path / "test.log"
        logger = Logger.get_instance()
        logger.add_file_handler(log_file)
        
        # Check that handler was added
        assert any(isinstance(h, logging.FileHandler) for h in logger.root_logger.handlers)
    
    def test_execution_time_decorator(self):
        """Test execution time logging decorator."""
        logger = get_logger("test")
        
        @log_execution_time(logger=logger, threshold_ms=0)
        def slow_function():
            return 42
        
        result = slow_function()

        assert result == 42
    
    def test_context_decorator(self):
        """Test context logging decorator."""
        @log_with_context({"request_id": "123"})
        def process():
            return "done"
        
        result = process()

        assert result == "done"
