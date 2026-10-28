# Templar

> **ALPHA - IN DEVELOPMENT**  
> Templar is currently in early alpha development. Core architectures and APIs are actively being refined as the framework progresses toward a stable 1.0 release. Feedback and contributions are welcome!

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](pyproject.toml)
[![codecov](https://codecov.io/gh/Orivex-x/templar/branch/master/graph/badge.svg)](https://codecov.io/gh/Orivex-x/templar)
[![Tests](https://github.com/Orivex-x/templar/actions/workflows/tests.yml/badge.svg?branch=master)](https://github.com/Orivex-x/templar/actions/workflows/tests.yml)
[![Status](https://img.shields.io/badge/status-alpha--in--development-orange)](#)

**Templar** is a Python-native web UI framework and full-stack application server designed to build reactive, robust web applications entirely in Python. Instead of relying on traditional template languages (like Jinja or Django templates) and context-switching between HTML and Python, Templar constructs clean view hierarchies using composable Python elements with dynamic request handling, an Active Record ORM, automated schema migrations, secure session authentication, and an interactive developer CLI.

---

## Quickstart (30 Seconds)

Generate and run a full-stack Templar project instantly:

```bash
# 1. Install Templar from source (not yet on PyPI)
git clone https://github.com/Orivex-x/templar.git
cd templar
pip install -e .

# 2. Create a new project workspace
templar create my-site
cd my-site

# 3. Start the live development server
templar run
```

Open `http://127.0.0.1:8000` in your browser. Your application is live!

---

## Key Features

- **Pure Python UI Tree:** Compose views using Python classes (`Div`, `Heading`, `Paragraph`, `Form`, `Card`, `Alert`, `Badge`, `Modal`) instead of detached template files.
- **Convention & Explicit Routing:** Automatic file-system routing (`templates/about.templar.py` -> `/about`, `templates/users/[username].templar.py` -> `/users/:username`) with optional explicit router support in `app.py`.
- **Integrated Active Record ORM:** Lightweight query builder, model definitions, multi-engine support (SQLite, PostgreSQL, MySQL), and transactional migrations (`templar migrate`).
- **Schema-Driven Forms & Validation:** Declarative form models with built-in email, length, regex validators, automated error reporting, and CSRF protection.
- **Built-in Authentication & Sessions:** Encrypted session cookies, password hashing (PBKDF2/bcrypt), role-based and permission-based access control.
- **Middleware Pipeline:** Extensible request/response lifecycle hooks with pre-configured security headers, rate limiting, and session verification.
- **Multi-Backend Caching:** Unified caching API supporting Memory, File, and Redis providers with automatic namespace isolation.
- **Interactive Developer CLI:** Rich terminal commands for route inspection (`templar routes`), config management (`templar config`), migrations (`templar migrate`), and live shell (`templar shell`).

---

## Code Example: Building a Templar Page

Views in Templar are pure Python files located in `templates/` that export a `render(**kwargs)` function:

```python
"""templates/index.templar.py"""

from templar.core.elements.Main import Main
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph
from templar.core.elements.Div import Div
from templar.core.components import Card, Badge, Alert

def render(**kwargs):
    request = kwargs.get("request")
    user = kwargs.get("user")
    
    return Main([
        Heading("Welcome to Templar", level=1),
        Paragraph("Build reactive web applications with pure Python."),
        
        Div([
            Card([
                Badge("Fast", variant="primary"),
                Heading("Native Python Components", level=3),
                Paragraph("No template compilation, no context-switching, just clean Python objects."),
            ], shadow=True),
            
            Card([
                Badge("Secure", variant="success"),
                Heading("Built-in Security", level=3),
                Paragraph("Automated CSRF protection, secure sessions, and request limits out of the box."),
            ], shadow=True),
        ], classes=["grid", "grid-cols-2", "gap-4"]),
    ], id="home-page")
```

---

## Database & Models Example

Define models and query records using Templar's Active Record ORM:

```python
# models/article.py
from templar.db.Models import Model

class Article(Model):
    _table = "articles"
    _fields = {
        "id": int,
        "title": str,
        "content": str,
        "is_published": bool,
    }
    __required_fields__ = ("title", "content")

# Query records
published = Article.objects().filter(is_published=True).order_by("id", "DESC").all()

# Create a record
article = Article(title="My First Post", content="Hello Templar!", is_published=True)
article.save()
```

---

## Forms & Validation Example

```python
# forms/contact.py
from templar.forms import Form, TextField, EmailField, TextAreaField, Required, Length

class ContactForm(Form):
    name = TextField("Your Name", required=True, validators=[Required(), Length(min_len=2)])
    email = EmailField("Email Address", required=True, validators=[Required()])
    message = TextAreaField("Message", required=True, validators=[Required(), Length(min_len=10)])

# Validate in your template:
form = ContactForm(data=request.form if request and request.method == "POST" else None)
if request and request.method == "POST" and form.validate():
    # Process valid submission
    pass
```

---

## Complete Documentation

Comprehensive guides and references are organized in the [`docs/`](docs/) directory:

### Getting Started
- **[Installation Guide](docs/getting-started/INSTALLATION.md)** – Prerequisites, pip setup, and optional extras (`[db]`, `[auth]`, `[cache]`, `[all]`).
- **[Quickstart Tutorial](docs/getting-started/QUICKSTART.md)** – Step-by-step tutorial building a complete application.
- **[Project Structure](docs/getting-started/PROJECT_STRUCTURE.md)** – Anatomy of a generated Templar project workspace.

### User Guides
- **[Components & Templates](docs/guides/COMPONENTS_AND_TEMPLATES.md)** – Core UI elements, pre-built components, custom components, and themes.
- **[Routing & URLs](docs/guides/ROUTING.md)** – File-based routing, dynamic route parameters, and explicit route definitions.
- **[Forms & Validation](docs/guides/FORMS.md)** – Form schemas, built-in field types, custom validators, and CSRF protection.
- **[Database & Models (ORM)](docs/guides/DATABASE_AND_MODELS.md)** – Database engines (SQLite/PostgreSQL/MySQL), Active Record models, and migrations.
- **[Authentication & Security](docs/guides/AUTHENTICATION.md)** – User model, password hashing, sessions, roles, and permissions.
- **[Middleware Pipeline](docs/guides/MIDDLEWARE.md)** – Request/response lifecycle hooks and custom middleware.
- **[Caching Guide](docs/guides/CACHING.md)** – Memory, File, and Redis cache backends and cache API usage.
- **[Configuration & Environments](docs/guides/CONFIGURATION.md)** – `templar.config.yml` schema, multi-environment profiles, and secret substitution.
- **[Testing Applications](docs/guides/TESTING.md)** – Testing templates, forms, routes, and models with `pytest`.
- **[CLI Reference](docs/guides/CLI_REFERENCE.md)** – Comprehensive CLI commands reference.

### Deployment & Production
- **[Production Deployment Guide](docs/deployment/DEPLOYMENT.md)** – Production configuration, Nginx reverse proxy, systemd, Docker, and TLS/SSL.

### Framework Development (Contributing)
- **[Contributing Guide](docs/development/CONTRIBUTING.md)** – Setting up editable development environments, running test suites, and building packages.
- **[Engine Architecture](docs/development/ARCHITECTURE.md)** – Internal architecture of `TemplarServer`, threading, HTTP framing, and compiler pipeline.

---

## Testing

Templar includes a comprehensive test suite with 187 unit and integration tests verifying ORM operations, HTTP framing, routing, security headers, and CLI workflows.

To run the full test suite locally:

```bash
pytest tests/ -v
```

Automated CI testing runs across Python 3.10, 3.11, and 3.12 on every push and pull request via [GitHub Actions](.github/workflows/tests.yml).

---

## License

Templar is open-source software licensed under the [MIT License](LICENSE).
