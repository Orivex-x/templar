"""
Templar custom exception hierarchy.

Provides specific exception types for better error handling and debugging.
"""

import sys

sys.dont_write_bytecode = True


class TemplarException(Exception):
    """Base exception for all Templar framework errors."""
    
    error_code: str = "ERR_000"
    message: str = "An error occurred in Templar"
    
    def __init__(self, message: str = None, error_code: str = None, **context):
        """
        Initialize TemplarException.
        
        Args:
            message: Custom error message
            error_code: Unique error code identifier
            **context: Additional context for debugging
        """
        self.error_code = error_code or self.error_code
        self.message = message or self.message

        if "context" in context and len(context) == 1 and isinstance(context["context"], dict):
            self.context = context["context"]
        else:
            self.context = context
        
        full_message = f"[{self.error_code}] {self.message}"

        if self.context:
            full_message += f" | Context: {self.context}"
        
        super().__init__(full_message)


# Configuration Errors
class ConfigError(TemplarException):
    """Base configuration error."""
    error_code = "ERR_100"
    message = "Configuration error"


class ConfigMissingError(ConfigError):
    """The required configuration key is missing."""
    error_code = "ERR_101"
    message = "Required configuration key is missing"


class ConfigInvalidError(ConfigError):
    """Configuration value is invalid."""
    error_code = "ERR_102"
    message = "Configuration value is invalid"


class ConfigFileNotFoundError(ConfigError):
    """Configuration file not found."""
    error_code = "ERR_103"
    message = "Configuration file not found"


# Template Errors
class TemplateError(TemplarException):
    """Base template error."""
    error_code = "ERR_200"
    message = "Template error"


class TemplateNotFoundError(TemplateError):
    """Template file not found."""
    error_code = "ERR_201"
    message = "Template file not found"


class TemplateRenderError(TemplateError):
    """The error occurred during template rendering."""
    error_code = "ERR_202"
    message = "Error occurred during template rendering"


class TemplateParseError(TemplateError):
    """Error parsing template syntax."""
    error_code = "ERR_203"
    message = "Error parsing template syntax"


class TemplateSyntaxError(TemplateError):
    """Invalid template syntax."""
    error_code = "ERR_204"
    message = "Invalid template syntax"


# Routing Errors
class RoutingError(TemplarException):
    """Base routing error."""
    error_code = "ERR_300"
    message = "Routing error"


class RouteNotFoundError(RoutingError):
    """Requested route not found."""
    error_code = "ERR_301"
    message = "Requested route not found"


class InvalidRoutePatternError(RoutingError):
    """Invalid route pattern."""
    error_code = "ERR_302"
    message = "Invalid route pattern"


class DuplicateRouteError(RoutingError):
    """Route pattern already registered."""
    error_code = "ERR_303"
    message = "Route pattern already registered"


class AmbiguousRouteError(RoutingError):
    """Multiple routes match the request."""
    error_code = "ERR_304"
    message = "Multiple routes match the request"


# Database Errors
class DatabaseError(TemplarException):
    """Base database error."""
    error_code = "ERR_400"
    message = "Database error"


class DatabaseConnectionError(DatabaseError):
    """Failed to connect to database."""
    error_code = "ERR_401"
    message = "Failed to connect to database"


class DatabaseQueryError(DatabaseError):
    """Error executing database query."""
    error_code = "ERR_402"
    message = "Error executing database query"


class DatabaseTransactionError(DatabaseError):
    """Error in database transaction."""
    error_code = "ERR_403"
    message = "Error in database transaction"


class ModelNotFoundError(DatabaseError):
    """Model record not found."""
    error_code = "ERR_404"
    message = "Model record not found"


class InvalidModelError(DatabaseError):
    """Invalid model definition."""
    error_code = "ERR_405"
    message = "Invalid model definition"


# Validation Errors
class ValidationError(TemplarException):
    """Base validation error."""
    error_code = "ERR_500"
    message = "Validation error"


class InvalidInputError(ValidationError):
    """Invalid user input."""
    error_code = "ERR_501"
    message = "Invalid user input"


class RequiredFieldError(ValidationError):
    """The required field is missing."""
    error_code = "ERR_502"
    message = "Required field is missing"


class InvalidEmailError(ValidationError):
    """Invalid email address."""
    error_code = "ERR_503"
    message = "Invalid email address"


class InvalidURLError(ValidationError):
    """Invalid URL."""
    error_code = "ERR_504"
    message = "Invalid URL"


class LengthValidationError(ValidationError):
    """Input length validation failed."""
    error_code = "ERR_505"
    message = "Input length validation failed"


# Authentication/Authorization Errors
class AuthError(TemplarException):
    """Base authentication/authorization error."""
    error_code = "ERR_600"
    message = "Authentication error"


class AuthenticationFailedError(AuthError):
    """Authentication failed."""
    error_code = "ERR_601"
    message = "Authentication failed"


class InvalidCredentialsError(AuthError):
    """Invalid username or password."""
    error_code = "ERR_602"
    message = "Invalid username or password"


class UnauthorizedError(AuthError):
    """User is not authorized for this action."""
    error_code = "ERR_603"
    message = "User is not authorized for this action"


class InvalidTokenError(AuthError):
    """Session token is invalid or expired."""
    error_code = "ERR_604"
    message = "Session token is invalid or expired"


class PermissionDeniedError(AuthError):
    """User lacks required permissions."""
    error_code = "ERR_605"
    message = "User lacks required permissions"


# Cache Errors
class CacheError(TemplarException):
    """Base cache error."""
    error_code = "ERR_700"
    message = "Cache error"


class CacheConnectionError(CacheError):
    """Failed to connect to the cache backend."""
    error_code = "ERR_701"
    message = "Failed to connect to cache backend"


class CacheKeyError(CacheError):
    """Invalid cache key."""
    error_code = "ERR_702"
    message = "Invalid cache key"


# Deployment Errors
class DeploymentError(TemplarException):
    """Base deployment error."""
    error_code = "ERR_800"
    message = "Deployment error"


class SSLCertificateMissingError(DeploymentError):
    """SSL certificate file not found."""
    error_code = "ERR_801"
    message = "SSL certificate file not found"


class SSLKeyMissingError(DeploymentError):
    """SSL private key file not found."""
    error_code = "ERR_802"
    message = "SSL private key file not found"


class InvalidSSLCertificateError(DeploymentError):
    """SSL certificate is invalid."""
    error_code = "ERR_803"
    message = "SSL certificate is invalid"


class DeploymentConfigurationError(DeploymentError):
    """Invalid deployment configuration."""
    error_code = "ERR_804"
    message = "Invalid deployment configuration"


# Element/Component Errors
class ElementError(TemplarException):
    """Base element/component error."""
    error_code = "ERR_900"
    message = "Element error"


class InvalidElementError(ElementError):
    """Invalid element definition."""
    error_code = "ERR_901"
    message = "Invalid element definition"


class InvalidPropsError(ElementError):
    """Invalid element properties."""
    error_code = "ERR_902"
    message = "Invalid element properties"


class ChildrenRenderError(ElementError):
    """Error rendering element children."""
    error_code = "ERR_903"
    message = "Error rendering element children"


# CLI Errors
class CLIError(TemplarException):
    """Base CLI error."""
    error_code = "ERR_1000"
    message = "CLI error"


class CommandNotFoundError(CLIError):
    """CLI command not found."""
    error_code = "ERR_1001"
    message = "CLI command not found"


class InvalidCommandArgumentsError(CLIError):
    """Invalid command arguments."""
    error_code = "ERR_1002"
    message = "Invalid command arguments"


class CommandExecutionError(CLIError):
    """Error executing CLI command."""
    error_code = "ERR_1003"
    message = "Error executing CLI command"
