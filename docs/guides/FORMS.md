# Form Handling Guide

## Basic Forms

Create a custom form:

```python
from templar.forms import Form, TextField, EmailField, PasswordField
from templar.forms import Required, Length, Email

class LoginForm(Form):
    username = TextField(
        label="Username",
        required=True,
        validators=[Required(), Length(3, 20)]
    )
    password = PasswordField(
        label="Password",
        required=True,
        validators=[Required(), Length(8)]
    )
```

## Form Validation

```python
# Create form with data
form = LoginForm(data=request.form)

# Validate
if form.validate():
    # Valid - process data
    username = form.get_field("username").value
else:
    # Invalid - show errors
    errors = form.errors
    # errors["username"] = ["Length must be at least 3"]
```

## Rendering Forms

```python
from templar.core.elements.Div import Div

# Render full form
form_element = form.render(
    submit_text="Login",
    action="/login",
    method="POST",
    csrf_token=request.csrf_token(),
)

# Or render fields individually
for field in form.render_fields():
    print(field)
```

When `csrf_enabled` is true (the default), include `request.csrf_token()` in
every state-changing form. Templar validates this session-bound token on POST
requests; JSON clients may instead send it in the `X-CSRF-Token` header.

## Pre-built Forms

### LoginForm

```python
from templar.forms import LoginForm

form = LoginForm(data=request.form)
if form.validate():
    # Authenticate user
    pass
```

### RegistrationForm

```python
from templar.forms import RegistrationForm

form = RegistrationForm(data=request.form)
if form.validate():
    # Create user
    user = User(
        username=form.get_field("username").value,
        email=form.get_field("email").value,
        password_hash=hash_password(form.get_field("password").value)
    )
    user.save()
```

## Custom Validators

```python
from templar.forms import Validators

class UniqueUsernameValidator(Validators.Validator):
    def validate(self, value):
        return User.objects().filter(username=value).count() == 0
    
    @property
    def default_message(self):
        return "Username already taken"
```

## Field Types

- `TextField` - Single line text
- `EmailField` - Email with validation
- `PasswordField` - Password input
- `IntegerField` - Number input
- `TextAreaField` - Multi-line text
- `SelectField` - Dropdown
- `CheckboxField` - Checkbox
- `DateField` - Date picker

## Styling Forms

Forms use BEM-style CSS classes:

```css
.form-field { }
.form-field__label { }
.form-field__input { }
.form-field__help { }
.form-field__error { }
.form-field--error { }
.form-field--valid { }
```

Customize CSS class:

```python
field = TextField(css_class="custom-field")
```
