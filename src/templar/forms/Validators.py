"""Form field validators."""

import sys
import re
from typing import Any, Optional, Callable
from abc import ABC, abstractmethod

sys.dont_write_bytecode = True


class Validator(ABC):
    """Base validator class."""
    
    def __init__(self, message: str = None):
        """
        Initialize validator.
        
        Args:
            message: Custom error message
        """
        self.message = message or self.default_message
    
    @property
    def default_message(self) -> str:
        """Default error message."""
        return "Validation failed"
    
    @abstractmethod
    def validate(self, value: Any) -> bool:
        """
        Validate value.
        
        Args:
            value: Value to validate
            
        Returns:
            True if valid, False otherwise
        """
        pass


class Required(Validator):
    """Validates that field is not empty."""
    
    @property
    def default_message(self) -> str:
        return "This field is required"
    
    def validate(self, value: Any) -> bool:
        """Check that value is not empty."""
        return value is not None and str(value).strip() != ""


class Length(Validator):
    """Validates string length."""
    
    def __init__(self, min: int = 0, max: int = None, message: str = None):
        """
        Initialize length validator.
        
        Args:
            min: Minimum length
            max: Maximum length
            message: Custom error message
        """
        self.min = min
        self.max = max
        super().__init__(message)
    
    @property
    def default_message(self) -> str:
        if self.max:
            return f"Length must be between {self.min} and {self.max}"

        return f"Length must be at least {self.min}"
    
    def validate(self, value: Any) -> bool:
        """Check string length."""
        value_str = str(value) if value else ""
        length = len(value_str)
        
        if length < self.min:
            return False

        if self.max and length > self.max:
            return False
        
        return True


class Email(Validator):
    """Validates an email address format."""
    
    EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    )
    
    @property
    def default_message(self) -> str:
        return "Invalid email address"
    
    def validate(self, value: Any) -> bool:
        """Check email format."""
        return bool(self.EMAIL_PATTERN.match(str(value)))


class URL(Validator):
    """Validates URL format."""
    
    URL_PATTERN = re.compile(
        r"^https?://[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*(?:/.*)?$"
    )
    
    @property
    def default_message(self) -> str:
        return "Invalid URL"
    
    def validate(self, value: Any) -> bool:
        """Check URL format."""
        return bool(self.URL_PATTERN.match(str(value)))


class Regex(Validator):
    """Validates against a regex pattern."""
    
    def __init__(self, pattern: str, message: str = None):
        """
        Initialize regex validator.
        
        Args:
            pattern: Regex pattern
            message: Custom error message
        """
        self.pattern = re.compile(pattern)
        super().__init__(message)
    
    @property
    def default_message(self) -> str:
        return f"Must match pattern: {self.pattern.pattern}"
    
    def validate(self, value: Any) -> bool:
        """Check against pattern."""
        return bool(self.pattern.match(str(value)))


class Range(Validator):
    """Validates numeric range."""
    
    def __init__(self, min: float = None, max: float = None, message: str = None):
        """
        Initialize range validator.
        
        Args:
            min: Minimum value
            max: Maximum value
            message: Custom error message
        """
        self.min = min
        self.max = max
        super().__init__(message)
    
    @property
    def default_message(self) -> str:
        if self.min is not None and self.max is not None:
            return f"Must be between {self.min} and {self.max}"
        elif self.min is not None:
            return f"Must be at least {self.min}"
        else:
            return f"Must be at most {self.max}"
    
    def validate(self, value: Any) -> bool:
        """Check numeric range."""
        try:
            num = float(value)

            if self.min is not None and num < self.min:
                return False

            if self.max is not None and num > self.max:
                return False

            return True
        except (ValueError, TypeError):
            return False


class OneOf(Validator):
    """Validates that value is one of the allowed options."""
    
    def __init__(self, options: list, message: str = None):
        """
        Initialize choice validator.
        
        Args:
            options: List of allowed values
            message: Custom error message
        """
        self.options = options
        super().__init__(message)
    
    @property
    def default_message(self) -> str:
        return f"Must be one of: {', '.join(str(o) for o in self.options)}"
    
    def validate(self, value: Any) -> bool:
        """Check if value is in options."""
        return value in self.options


class Custom(Validator):
    """Validates using custom function."""
    
    def __init__(self, func: Callable, message: str = None):
        """
        Initialize custom validator.
        
        Args:
            func: Validation function (returns bool)
            message: Custom error message
        """
        self.func = func
        super().__init__(message)
    
    @property
    def default_message(self) -> str:
        return "Validation failed"
    
    def validate(self, value: Any) -> bool:
        """Run a custom validation function."""
        try:
            return self.func(value)
        except Exception:
            return False
