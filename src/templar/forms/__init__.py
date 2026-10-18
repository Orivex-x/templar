"""Forms package."""

from templar.forms.Validators import (
    Validator,
    Required,
    Length,
    Email,
    URL,
    Regex,
    Range,
    OneOf,
    Custom,
)

from templar.forms.Fields import (
    Field,
    TextField,
    EmailField,
    PasswordField,
    IntegerField,
    TextAreaField,
    SelectField,
    CheckboxField,
    DateField,
)

from templar.forms.Form import (
    Form,
    LoginForm,
    RegistrationForm,
)

__all__ = [
    # Validators
    "Validator",
    "Required",
    "Length",
    "Email",
    "URL",
    "Regex",
    "Range",
    "OneOf",
    "Custom",
    # Fields
    "Field",
    "TextField",
    "EmailField",
    "PasswordField",
    "IntegerField",
    "TextAreaField",
    "SelectField",
    "CheckboxField",
    "DateField",
    # Forms
    "Form",
    "LoginForm",
    "RegistrationForm",
]
