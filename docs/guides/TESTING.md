# Testing Guide

This guide covers testing practices and patterns for applications built with the Templar framework.

## Project Test Structure

A standard test structure for a Templar application:

```text
my-app/
├── app.py
├── templates/
│   ├── index.templar.py
│   └── user.templar.py
├── forms/
│   └── contact.py
├── models/
│   └── item.py
└── tests/
    ├── conftest.py              # Shared fixtures and setup
    ├── test_templates.py        # Template rendering tests
    ├── test_forms.py            # Form validation tests
    ├── test_routes.py           # Route resolution tests
    └── test_models.py           # Database model tests
```

---

## Testing Templates and Components

Templar templates export a `render()` function that returns UI elements (such as `Div`, `Heading`, or `Paragraph`). You can test templates directly by invoking `render()` with mock contexts or arguments:

```python
import pytest
from templates.index import render

def test_index_page_guest():
    element = render(request=None, user=None)
    html = str(element)
    assert "Welcome to Templar!" in html
    assert "Guest" in html

def test_index_page_authenticated_user():
    user = {"username": "alice"}
    element = render(request=None, user=user)
    html = str(element)
    assert "Hello, alice!" in html
```

---

## Testing Forms and Validation

Forms can be instantiated with dictionary payloads to verify field validation, constraints, and error messages:

```python
from templar.forms import Form, TextField, EmailField, Required, Length

class ContactForm(Form):
    name = TextField(label="Name", required=True, validators=[Required(), Length(min_len=2)])
    email = EmailField(label="Email", required=True, validators=[Required()])

def test_contact_form_valid():
    form = ContactForm(data={"name": "Alice", "email": "alice@example.com"})
    assert form.validate() is True
    assert len(form.errors) == 0

def test_contact_form_invalid_email():
    form = ContactForm(data={"name": "Alice", "email": "not-an-email"})
    assert form.validate() is False
    assert "email" in form.errors
```

---

## Testing Routes and Resolution

Explicit routes and path parameter parsing can be verified using the `Router`:

```python
from templar.Config import Config
from templar.Router import Router

def test_route_resolution():
    config = Config()
    router = Router(config)
    router.add("/profile/{username}", "user_profile")

    route, params = router.match("/profile/johndoe")
    assert route == "user_profile"
    assert params["username"] == "johndoe"
```

---

## Testing Database Models

Active record models and queries can be tested using an in-memory SQLite database or test database fixtures:

```python
import pytest
from templar.db.Database import Database
from templar.auth.User import User

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    db = Database(engine="sqlite", uri=":memory:")
    db.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    monkeypatch.setattr("templar.db.Database.get_default", lambda: db)
    return db

def test_user_creation_and_query():
    user = User(username="alice", email="alice@example.com", password_hash="hashed_secret")
    user.save()

    retrieved = User.objects().filter(username="alice").first()
    assert retrieved is not None
    assert retrieved["email"] == "alice@example.com"
```

---

## Running the Test Suite

Execute tests using `pytest` from your project root:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=. --cov-report=term-missing
```

---

## Continuous Integration (CI)

For automated testing in CI pipelines, projects can run `pytest` against pull requests and commits. Example GitHub Actions workflow (`.github/workflows/tests.yml`):

```yaml
name: Tests

on:
  push:
    branches: [ master, main ]
  pull_request:
    branches: [ master, main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run pytest
        run: |
          pytest tests/ -v
```
