"""Form field definitions."""

import sys
from typing import Any, List, Optional, Union
from abc import ABC, abstractmethod

from templar.forms.Validators import Validator, Required
from templar.core.elements.Element import Element
from templar.core.elements.Input import Input
from templar.core.elements.Textarea import Textarea
from templar.core.elements.Select import Select
from templar.core.elements.Label import Label
from templar.core.elements.Span import Span
from templar.core.elements.Div import Div

sys.dont_write_bytecode = True


class Field(ABC):
    """Base form field class."""
    
    def __init__(
        self,
        name: str = None,
        label: str = None,
        required: bool = False,
        validators: List[Validator] = None,
        default: Any = None,
        help_text: str = None,
        placeholder: str = None,
        css_class: str = "form-field"
    ):
        """
        Initialize field.
        
        Args:
            name: Field name
            label: Display label
            required: Whether field is required
            validators: List of validators
            default: Default value
            help_text: Help text
            placeholder: Placeholder text
            css_class: CSS class
        """
        self.name = name
        self.label = label or (name.replace("_", " ").title() if name else "")
        self.required = required
        self.validators = validators or []
        self.default = default
        self.help_text = help_text
        self.placeholder = placeholder
        self.css_class = css_class
        self.value = None
        self.errors: List[str] = []
        
        # Add Required validator if field is required
        if required and not any(isinstance(v, Required) for v in self.validators):
            self.validators.insert(0, Required())
    
    def validate(self) -> bool:
        """
        Validate field value.
        
        Returns:
            True if valid, False otherwise
        """
        self.errors = []
        
        for validator in self.validators:
            if not validator.validate(self.value):
                self.errors.append(validator.message)
        
        return len(self.errors) == 0
    
    @abstractmethod
    def render_input(self) -> Element:
        """Render field input element."""
        pass
    
    def render(self) -> Element:
        """Render a complete field with label and errors."""
        elements = []
        
        # Label
        if self.label:
            label_elem = Label(
                self.label,
                for_attr=f"{self.name}-input",
                classes=[f"{self.css_class}__label"]
            )
            elements.append(label_elem)
        
        # Input
        input_elem = self.render_input()
        elements.append(input_elem)
        
        # Help text
        if self.help_text:
            help_elem = Span(
                self.help_text,
                classes=[f"{self.css_class}__help"]
            )
            elements.append(help_elem)
        
        # Errors
        if self.errors:
            for error in self.errors:
                error_elem = Span(
                    error,
                    classes=[f"{self.css_class}__error"]
                )
                elements.append(error_elem)
        
        # Wrapper
        return Div(
            elements,
            classes=[
                self.css_class,
                f"{self.css_class}--{'error' if self.errors else 'valid'}"
            ]
        )


class TextField(Field):
    """Text input field."""
    
    def __init__(self, *args, max_length: int = None, **kwargs):
        """
        Initialize text field.
        
        Args:
            max_length: Maximum length
        """
        self.max_length = max_length
        super().__init__(*args, **kwargs)
    
    def render_input(self) -> Element:
        """Render text input."""
        props = {
            "id": f"{self.name}-input",
            "type": "text",
            "name": self.name,
            "value": self.value or self.default or "",
            "placeholder": self.placeholder or "",
        }
        
        if self.max_length:
            props["maxlength"] = self.max_length
        
        if self.required:
            props["required"] = "required"
        
        return Input(**props, classes=[f"{self.css_class}__input"])


class EmailField(Field):
    """Email input field."""
    
    def render_input(self) -> Element:
        """Render email input."""
        return Input(
            id=f"{self.name}-input",
            type="email",
            name=self.name,
            value=self.value or self.default or "",
            placeholder=self.placeholder or "",
            required="required" if self.required else None,
            classes=[f"{self.css_class}__input"]
        )


class PasswordField(Field):
    """Password input field."""
    
    def render_input(self) -> Element:
        """Render password input."""
        return Input(
            id=f"{self.name}-input",
            type="password",
            name=self.name,
            value=self.value or "",
            placeholder=self.placeholder or "",
            required="required" if self.required else None,
            classes=[f"{self.css_class}__input"]
        )


class IntegerField(Field):
    """Integer input field."""
    
    def render_input(self) -> Element:
        """Render number input."""
        return Input(
            id=f"{self.name}-input",
            type="number",
            name=self.name,
            value=str(self.value or self.default or ""),
            placeholder=self.placeholder or "",
            required="required" if self.required else None,
            classes=[f"{self.css_class}__input"]
        )


class TextAreaField(Field):
    """Multi-line text field."""
    
    def __init__(self, *args, rows: int = 4, **kwargs):
        """
        Initialize the textarea field.
        
        Args:
            rows: Number of rows
        """
        self.rows = rows
        super().__init__(*args, **kwargs)
    
    def render_input(self) -> Element:
        """Render textarea."""
        return Textarea(
            self.value or self.default or "",
            id=f"{self.name}-input",
            name=self.name,
            rows=self.rows,
            placeholder=self.placeholder or "",
            required="required" if self.required else None,
            classes=[f"{self.css_class}__input"]
        )


class SelectField(Field):
    """Dropdown select fields."""
    
    def __init__(self, *args, choices: List[tuple] = None, options: List[Any] = None, **kwargs):
        """
        Initialize a select field.
        
        Args:
            choices: List of (value, label) tuples
        """
        values = choices if choices is not None else options or []
        self.choices = [
            choice if isinstance(choice, tuple) else (choice, choice)
            for choice in values
        ]
        super().__init__(*args, **kwargs)
    
    def render_input(self) -> Element:
        """Render select element."""
        options = [
            {"value": value, "label": label}
            for value, label in self.choices
        ]
        
        return Select(
            options,
            id=f"{self.name}-input",
            name=self.name,
            value=self.value or self.default or "",
            required="required" if self.required else None,
            classes=[f"{self.css_class}__input"]
        )


class CheckboxField(Field):
    """Checkbox field."""
    
    def render_input(self) -> Element:
        """Render checkbox."""
        return Input(
            id=f"{self.name}-input",
            type="checkbox",
            name=self.name,
            value=self.value or self.default or "",
            checked="checked" if self.value else None,
            classes=[f"{self.css_class}__input"]
        )


class DateField(Field):
    """Date input field."""
    
    def render_input(self) -> Element:
        """Render date input."""
        return Input(
            id=f"{self.name}-input",
            type="date",
            name=self.name,
            value=self.value or self.default or "",
            required="required" if self.required else None,
            classes=[f"{self.css_class}__input"]
        )
