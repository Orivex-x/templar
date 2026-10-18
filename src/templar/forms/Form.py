"""Form class and form handling."""

import copy
import sys
from typing import Dict, Any, List

from templar.core.elements.Div import Div
from templar.core.elements.Form import Form as FormElement
from templar.core.elements.Button import Button
from templar.core.elements.Input import Input
from templar.forms.Fields import Field

sys.dont_write_bytecode = True


class Form:
    """
    Base form class.
    
    Subclass this to create forms with validation and rendering.
    
    Usage:
        class LoginForm(Form):
            username = TextField(required=True)
            password = PasswordField(required=True)
        
        form = LoginForm()
        form.validate()
        html = form.render()
    """
    
    def __init__(self, data: Dict[str, Any] = None, **kwargs):
        """
        Initialize form.
        
        Args:
            data: Dictionary of form data
            **kwargs: Field overrides
        """
        self.data = data or {}
        self.errors: Dict[str, List[str]] = {}
        self.is_valid = False
        
        self.fields: Dict[str, Field] = {}
        declared_fields: Dict[str, Field] = {}

        # Preserve declaration order across inherited form classes.
        for base in reversed(self.__class__.__mro__):
            for attr_name, attr in vars(base).items():
                if isinstance(attr, Field):
                    declared_fields[attr_name] = attr

        # Built-in forms and programmatic forms may declare fields on self.
        for attr_name, attr in vars(self).items():
            if isinstance(attr, Field):
                declared_fields[attr_name] = attr

        for field_name, declared_field in declared_fields.items():
            field = copy.deepcopy(declared_field)
            field.name = field_name

            if not field.label:
                field.label = field_name.replace("_", " ").title()

            self.fields[field_name] = field
            setattr(self, field_name, field)
        
        # Set values from data
        for field_name, field in self.fields.items():
            if field_name in self.data:
                field.value = self.data[field_name]
    
    def validate(self) -> bool:
        """
        Validate all form fields.
        
        Returns:
            True if all fields are valid
        """
        self.errors = {}
        self.is_valid = True
        
        for field_name, field in self.fields.items():
            if not field.validate():
                self.errors[field_name] = field.errors
                self.is_valid = False
        
        return self.is_valid
    
    def get_field(self, name: str):
        """Get field by name."""
        return self.fields.get(name)
    
    def get_data(self) -> Dict[str, Any]:
        """Get form data from all fields."""
        return {
            field_name: field.value
            for field_name, field in self.fields.items()
        }
    
    def render(
        self,
        submit_text: str = "Submit",
        method: str = "POST",
        action: str = "#",
        css_class: str = "form",
        csrf_token: str = None,
    ) -> FormElement:
        """
        Render form as an HTML element.
        
        Args:
            submit_text: Button text
            method: Form method (GET, POST)
            action: Form action
            css_class: CSS class for form
            
        Returns:
            Form element with all fields
        """
        field_elements = [
            field.render()
            for field in self.fields.values()
        ]
        if csrf_token:
            field_elements.insert(0, Input(type="hidden", name="csrf_token", value=csrf_token))
        
        # Add submit button
        submit_button = Button(
            submit_text,
            type="submit",
            id="form-submit",
            classes=["form__submit"]
        )
        
        field_elements.append(submit_button)
        
        return FormElement(
            field_elements,
            method=method,
            action=action,
            classes=[css_class]
        )
    
    def render_fields(self) -> List:
        """Render just the fields (without form wrapper)."""
        return [field.render() for field in self.fields.values()]


# Common form patterns

class LoginForm(Form):
    """Pre-built login form."""
    
    def __init__(self, data: Dict[str, Any] = None, **kwargs):
        from templar.forms.Fields import TextField, PasswordField
        from templar.forms.Validators import Required, Email
        
        self.username = TextField(
            label="Username or Email",
            required=True,
            validators=[Required()],
            placeholder="Enter username or email"
        )
        self.password = PasswordField(
            label="Password",
            required=True,
            validators=[Required()],
            placeholder="Enter password"
        )
        
        super().__init__(data, **kwargs)


class RegistrationForm(Form):
    """Pre-built registration form."""
    
    def __init__(self, data: Dict[str, Any] = None, **kwargs):
        from templar.forms.Fields import TextField, EmailField, PasswordField
        from templar.forms.Validators import Required, Email, Length
        
        self.username = TextField(
            label="Username",
            required=True,
            validators=[Required(), Length(3, 20)],
            placeholder="Choose a username"
        )
        self.email = EmailField(
            label="Email Address",
            required=True,
            validators=[Required(), Email()],
            placeholder="Enter your email"
        )
        self.password = PasswordField(
            label="Password",
            required=True,
            validators=[Required(), Length(8)],
            placeholder="Create a password"
        )
        self.password_confirm = PasswordField(
            label="Confirm Password",
            required=True,
            validators=[Required()],
            placeholder="Confirm password"
        )
        
        super().__init__(data, **kwargs)
    
    def validate(self) -> bool:
        """Override to check the password match."""
        is_valid = super().validate()
        
        password = self.fields["password"].value
        password_confirm = self.fields["password_confirm"].value

        if password and password_confirm:
            if password != password_confirm:
                if "password_confirm" not in self.errors:
                    self.errors["password_confirm"] = []

                self.errors["password_confirm"].append("Passwords do not match")
                is_valid = False

        self.is_valid = is_valid

        return is_valid
