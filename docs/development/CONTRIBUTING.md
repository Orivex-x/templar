# Contributing to Templar

Thank you for contributing to Templar! This guide covers setting up a local development environment, running test suites, code quality guidelines, and building release packages.

---

## 1. Prerequisites

- Python `3.10`, `3.11`, or `3.12`
- Git
- Optional services (when testing specific cache/database backends): Redis, PostgreSQL, MySQL

---

## 2. Setting Up Local Development

Clone the repository and install the editable package with all development dependencies:

```bash
# macOS / Linux
./dev-install.sh
source .venv/bin/activate

# Windows (PowerShell)
.\dev-install.ps1
```

The setup script creates a dedicated `.venv` virtual environment and runs `pip install -e ".[dev]"`.

---

## 3. Running Tests and Quality Checks

Run the automated test suite with `pytest`:

```bash
# Run all unit and integration tests
pytest -v

# Run with test coverage report
pytest --cov=templar --cov-report=term-missing

# Run focused subsystem tests
pytest tests/unit/test_config.py -v
pytest tests/integration/test_http_server.py -v
```

### Static Sanity Checks
```bash
# Bytecode compilation verification
python -m compileall -q src
```

---

## 4. Code Standards & Architecture Guidelines

1. **Clean Package Layout:** All distributable source code resides in `src/templar/`.
2. **Skeleton Integrity:** Starter files in `src/templar/skeleton/` must remain clean and free of local development artifacts or test databases.
3. **Thread Safety:** `TemplarServer` is multi-threaded. Scoped mutable request state must reside on request contexts, never on framework singletons.
4. **Strict HTTP Framing:** Templar strictly rejects invalid `Transfer-Encoding` headers, duplicate `Content-Length`/`Host` headers, and enforces request body size limits.

---

## 5. Building Distribution Packages

To build and verify source distributions and wheels:

```bash
# Install packaging tools
python -m pip install --upgrade build twine

# Build package artifacts
python -m build

# Validate metadata and artifacts
twine check dist/*
```
