"""Unit tests for Exception classes."""

import pytest
from templar.core.Exceptions import (
    TemplarException,
    ConfigMissingError,
    TemplateNotFoundError,
    RouteNotFoundError,
    DatabaseQueryError,
    ValidationError,
    AuthenticationFailedError,
    UnauthorizedError,
)


@pytest.mark.unit
class TestExceptions:
    """Tests for custom exception hierarchy."""
    
    def test_base_exception(self):
        """Test base TemplarException."""
        exc = TemplarException("Test error", error_code="ERR_TEST")

        assert exc.error_code == "ERR_TEST"
        assert exc.message == "Test error"
        assert "[ERR_TEST]" in str(exc)
    
    def test_exception_with_context(self):
        """Test exception with context."""
        context = {"user_id": 123, "action": "delete"}
        exc = TemplarException("Test error", context=context)

        assert exc.context == context
        assert "Context:" in str(exc)
    
    def test_config_missing_error(self):
        """Test ConfigMissingError."""
        exc = ConfigMissingError("session_secret")

        assert exc.error_code == "ERR_101"
        assert "session_secret" in str(exc)
    
    def test_template_not_found_error(self):
        """Test TemplateNotFoundError."""
        exc = TemplateNotFoundError("index.templar.py", template_name="index")

        assert exc.error_code == "ERR_201"
    
    def test_route_not_found_error(self):
        """Test RouteNotFoundError."""
        exc = RouteNotFoundError("/invalid", path="/invalid")

        assert exc.error_code == "ERR_301"
    
    def test_database_query_error(self):
        """Test DatabaseQueryError."""
        exc = DatabaseQueryError("SELECT failed", query="SELECT * FROM users")

        assert exc.error_code == "ERR_402"
    
    def test_validation_error(self):
        """Test ValidationError."""
        exc = ValidationError("Invalid email", field="email")

        assert exc.error_code == "ERR_500"
    
    def test_authentication_failed_error(self):
        """Test AuthenticationFailedError."""
        exc = AuthenticationFailedError("Invalid credentials")

        assert exc.error_code == "ERR_601"
    
    def test_unauthorized_error(self):
        """Test UnauthorizedError."""
        exc = UnauthorizedError("Admin access required")

        assert exc.error_code == "ERR_603"
    
    def test_exception_inheritance(self):
        """Test that exceptions inherit from base."""
        exc = ConfigMissingError("test")

        assert isinstance(exc, TemplarException)
        assert isinstance(exc, Exception)
