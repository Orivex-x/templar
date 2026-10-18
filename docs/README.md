# Templar Documentation

Welcome to the documentation for **Templar**, a Python-native web UI framework and full-stack application server designed for building modern, reactive web applications entirely in Python.

---

## Getting Started

If you are new to Templar, start here to set up your environment and create your first project:

- **[Installation](getting-started/INSTALLATION.md)** – Prerequisites, package installation, and optional dependency extras.
- **[Quickstart Guide](getting-started/QUICKSTART.md)** – Build your first Templar web application in under 5 minutes.
- **[Project Structure](getting-started/PROJECT_STRUCTURE.md)** – Anatomy of a Templar application workspace.

---

## User Guides

Comprehensive guides covering every feature and subsystem for building full-stack applications:

- **[Components & Templates](guides/COMPONENTS_AND_TEMPLATES.md)** – Pure-Python UI construction, built-in components (`Card`, `Alert`, `Badge`, `Modal`), custom reusable elements, and styling.
- **[Routing & URLs](guides/ROUTING.md)** – Dynamic file-based routing (`*.templar.py`), route parameters, explicit router configuration, and redirects.
- **[Forms & Validation](guides/FORMS.md)** – Schema-driven form definitions, built-in field types, custom validators, and automated CSRF protection.
- **[Database & Models (ORM)](guides/DATABASE_AND_MODELS.md)** – Database configuration (SQLite, PostgreSQL, MySQL), Active Record models, querying, and schema migrations.
- **[Authentication & Security](guides/AUTHENTICATION.md)** – User accounts, password hashing, session management, roles, and permission-based access control.
- **[Middleware Pipeline](guides/MIDDLEWARE.md)** – Request/response lifecycle hooks, custom middleware, and built-in security middleware.
- **[Caching](guides/CACHING.md)** – Memory, File, and Redis cache backends, cache operations, and performance optimization.
- **[Configuration & Environments](guides/CONFIGURATION.md)** – YAML configuration schema, multi-environment profiles (`dev`, `prod`, `test`), and secret interpolation (`${ENV_VAR}`).
- **[Testing Applications](guides/TESTING.md)** – Writing unit and integration tests for templates, forms, routes, and models with `pytest`.
- **[CLI Reference](guides/CLI_REFERENCE.md)** – Complete reference for all `templar` command-line tools.

---

## Deployment & Production

Learn how to configure, secure, and deploy Templar applications to production environments:

- **[Production Deployment Guide](deployment/DEPLOYMENT.md)** – Production configuration checklist, Nginx reverse proxy setup, systemd service management, Docker containers, and TLS/SSL.

---

## Framework Development & Contributing

Documentation for contributing to the Templar framework itself:

- **[Contributing Guide](development/CONTRIBUTING.md)** – Setting up editable development environments, running the test suite, code standards, and package release procedures.
- **[Engine Architecture](development/ARCHITECTURE.md)** – Internal architecture of `TemplarServer`, the threaded request pipeline, HTTP framing rules, and component compiler.
