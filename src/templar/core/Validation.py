"""Input validation and sanitization utilities."""

import sys
import re
import html
from typing import Any, Optional

from templar.core.Exceptions import (
    InvalidInputError,
    InvalidEmailError,
    InvalidURLError,
    LengthValidationError,
)

sys.dont_write_bytecode = True


class Sanitizer:
    """Input sanitization utilities."""
    
    @staticmethod
    def html_escape(value: str) -> str:
        """
        Escape HTML special characters.
        
        Args:
            value: String to escape
            
        Returns:
            HTML-escaped string
        """
        return html.escape(value)
    
    @staticmethod
    def strip_tags(value: str) -> str:
        """
        Remove HTML tags from string.
        
        Args:
            value: String with potential HTML
            
        Returns:
            String without HTML tags
        """
        return re.sub(r'<[^>]+>', '', value)
    
    @staticmethod
    def normalize_whitespace(value: str) -> str:
        """
        Normalize whitespace (remove extra spaces, newlines).
        
        Args:
            value: String to normalize
            
        Returns:
            Normalized string
        """
        return ' '.join(value.split())
    
    @staticmethod
    def remove_null_bytes(value: str) -> str:
        """
        Remove null bytes from string.
        
        Args:
            value: String to sanitize
            
        Returns:
            String without null bytes
        """
        return value.replace('\x00', '')


class InputValidator:
    """Input validation utilities."""
    
    EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    )
    
    URL_PATTERN = re.compile(
        r"^https?://[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*(?:/.*)?$"
    )
    
    PHONE_PATTERN = re.compile(
        r"^\+?1?\d{9,15}$"
    )
    
    IPV4_PATTERN = re.compile(
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    )
    
    @staticmethod
    def is_email(value: str) -> bool:
        """
        Validate an email address format.
        
        Args:
            value: Email address
            
        Returns:
            True if a valid email format
        """
        if not value or len(value) > 254:
            return False

        return bool(InputValidator.EMAIL_PATTERN.match(str(value)))
    
    @staticmethod
    def is_url(value: str) -> bool:
        """
        Validate URL format.
        
        Args:
            value: URL
            
        Returns:
            True if valid URL
        """
        if not value:
            return False

        return bool(InputValidator.URL_PATTERN.match(str(value)))
    
    @staticmethod
    def is_phone(value: str) -> bool:
        """
        Validate a phone number format.
        
        Args:
            value: Phone number
            
        Returns:
            True if a valid phone format
        """
        if not value:
            return False

        return bool(InputValidator.PHONE_PATTERN.match(str(value).replace('-', '').replace(' ', '').replace('(', '').replace(')', '')))
    
    @staticmethod
    def is_ipv4(value: str) -> bool:
        """
        Validate IPv4 address.
        
        Args:
            value: IP address
            
        Returns:
            True if valid IPv4
        """
        if not value:
            return False

        return bool(InputValidator.IPV4_PATTERN.match(str(value)))
    
    @staticmethod
    def is_length(value: str, min_length: int = 0, max_length: int = None) -> bool:
        """
        Validate string length.
        
        Args:
            value: String to check
            min_length: Minimum length
            max_length: Maximum length
            
        Returns:
            True if length is valid
        """
        length = len(str(value)) if value else 0
        
        if length < min_length:
            return False

        if max_length is not None and length > max_length:
            return False
        
        return True
    
    @staticmethod
    def is_alphanumeric(value: str) -> bool:
        """
        Check if the string is alphanumeric.
        
        Args:
            value: String to check
            
        Returns:
            True if alphanumeric
        """
        return str(value).isalnum()
    
    @staticmethod
    def is_numeric(value: Any) -> bool:
        """
        Check if the value is numeric.
        
        Args:
            value: Value to check
            
        Returns:
            True if numeric
        """
        try:
            float(value)

            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_integer(value: Any) -> bool:
        """
        Check if the value is an integer.
        
        Args:
            value: Value to check
            
        Returns:
            True if integer
        """
        try:
            int(value)

            return str(value).isdigit() or (str(value).startswith('-') and str(value)[1:].isdigit())
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_boolean(value: Any) -> bool:
        """
        Check if the value is boolean-like.
        
        Args:
            value: Value to check
            
        Returns:
            True if boolean or boolean-like string
        """
        if isinstance(value, bool):
            return True

        if str(value).lower() in ('true', 'false', '1', '0', 'yes', 'no', 'on', 'off'):
            return True

        return False


class InputTypeConverter:
    """Convert input to specific types with validation."""
    
    @staticmethod
    def to_int(value: Any, default: int = 0) -> int:
        """Convert to integer."""
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def to_float(value: Any, default: float = 0.0) -> float:
        """Convert to float."""
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def to_bool(value: Any, default: bool = False) -> bool:
        """Convert to boolean."""
        if isinstance(value, bool):
            return value

        if str(value).lower() in ('true', '1', 'yes', 'on'):
            return True

        if str(value).lower() in ('false', '0', 'no', 'off'):
            return False

        return default
    
    @staticmethod
    def to_string(value: Any, default: str = "") -> str:
        """Convert to string."""
        if value is None:
            return default

        return str(value)
    
    @staticmethod
    def to_list(value: Any, separator: str = ',', default: list = None) -> list:
        """Convert string to list."""
        if isinstance(value, list):
            return value

        if isinstance(value, str):
            return [x.strip() for x in value.split(separator)]

        return default or []


class PasswordValidator:
    """Password strength validation."""
    
    @staticmethod
    def is_strong(password: str, min_length: int = 8) -> tuple[bool, list[str]]:
        """
        Validate password strength.
        
        Args:
            password: Password to validate
            min_length: Minimum length
            
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        if len(password) < min_length:
            issues.append(f"Password must be at least {min_length} characters")
        
        if not re.search(r'[a-z]', password):
            issues.append("Password must contain lowercase letters")
        
        if not re.search(r'[A-Z]', password):
            issues.append("Password must contain uppercase letters")
        
        if not re.search(r'[0-9]', password):
            issues.append("Password must contain numbers")
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?]', password):
            issues.append("Password must contain special characters")
        
        return len(issues) == 0, issues


class SQLInjectionDetector:
    """Detect potential SQL injection attempts."""
    
    SQL_KEYWORDS = [
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE',
        'ALTER', 'EXEC', 'EXECUTE', '--', '/*', '*/', 'UNION', 'FROM', 'WHERE'
    ]
    
    @staticmethod
    def is_suspicious(value: str) -> bool:
        """
        Detect potential SQL injection.
        
        Args:
            value: Input to check
            
        Returns:
            True if suspicious patterns are found
        """
        value_upper = value.upper()
        
        for keyword in SQLInjectionDetector.SQL_KEYWORDS:
            if keyword in value_upper:
                return True
        
        # Check for common SQL injection patterns
        if any(pattern in value for pattern in ["';", '";', "' OR", '" OR', "' AND", '" AND']):
            return True
        
        return False
