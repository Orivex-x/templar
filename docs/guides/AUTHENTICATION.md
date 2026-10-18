# Authentication Guide

## User Model

```python
from templar.auth.User import User
from templar.auth import PasswordManager
from templar.auth.Permission import Permission, Role

# Create user
user = User(
    username="alice",
    email="alice@example.com",
    password_hash=PasswordManager.hash_password("secure_password"),
    roles=[Role.USER],
    permissions=[Permission.VIEW_PROFILE, Permission.EDIT_PROFILE]
)
user.save()
```

To add application-specific fields, subclass `User`. The subclass keeps the
full authentication schema and creates its own table by default:

```python
class Account(User):
    display_name: str
```

`Account` includes the inherited username, email, password hash, activity,
role, permission, and timestamp fields. Model imports are side-effect free;
the table is created when the model is first queried or saved using the
application's configured database.

For a pre-existing user table created by an older Templar version, run the
tracked compatibility upgrade before serving traffic:

```sh
templar migrate user-schema
```

It enforces required identity fields and unique identities. On SQLite it also
preserves existing user-defined indexes and triggers.

For a custom top-level user model, target that model explicitly so its own
table receives a separately tracked upgrade:

```sh
templar migrate user-schema --model myapp.models:Account
```

## Password Hashing

```python
from templar.auth import PasswordManager

# Hash password
hashed = PasswordManager.hash_password("my_password")

# Verify password
is_valid = PasswordManager.verify_password("my_password", hashed)
```

## Authentication

```python
from templar.auth import Auth

auth = Auth(secret_key=config.session_secret)

# Authenticate during a request. `session` is the request's server-side session.
if auth.authenticate(username, password, load_user_by_username, session=request.session):
    # The user is available on the following request after middleware loads it.
    pass
else:
    # Invalid credentials
    pass

# Check authentication in a template/controller request.
if auth.is_authenticated(request):
    pass

# Logout
auth.logout(request.session)
```

## Permissions & Roles

```python
# `request` is the Templar request context passed to render().
if auth.has_role(request, "admin"):
    pass

# Check permission
if auth.has_permission(request, "admin:manage_users"):
    pass
```

## Middleware Integration

```python
# Application callbacks cannot be declared in YAML. Register a loader when
# constructing the server (or call server.set_user_loader(...) before start()).
from templar.TemplarServer import TemplarServer

def load_user_by_id(user_id):
    return User.objects().filter(id=user_id).first()

server = TemplarServer(
    config=config,
    output=output,
    user_loader=load_user_by_id,
)
```

The loader may return a user dictionary, a `User`/model object with `to_dict()`,
or `None`. A dictionary must contain the same `id` as the session lookup and
may provide roles/permissions as either JSON arrays or `list[str]`; malformed
claims fail closed. Templar's built-in auth middleware rejects inactive
accounts and attaches a safe public dictionary to `request.user`; it never
stores the current user on a shared `Auth` object.

## Pre-built Forms

```python
from templar.forms import LoginForm, RegistrationForm

# Login form
login_form = LoginForm(data=request.form)
if login_form.validate():
    # Authenticate
    pass

# Registration form
reg_form = RegistrationForm(data=request.form)
if reg_form.validate():
    # Create user
    user = User(
        username=reg_form.username.value,
        email=reg_form.email.value,
        password_hash=PasswordManager.hash_password(reg_form.password.value)
    )
    user.save()
```
