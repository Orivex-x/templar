# Installation Guide

This guide covers installing the Templar framework and configuring environment requirements for application development.

---

## Prerequisites

- **Python:** Version `3.10`, `3.11`, or `3.12`
- **Package Manager:** `pip` (or `uv` / `poetry`)
- **Supported Operating Systems:** Linux, macOS, Windows

---

## Standard Installation

Install Templar from PyPI or your package repository into your Python virtual environment:

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install Templar
pip install templar
```

Verify that the CLI is accessible:

```bash
templar --help
```

---

## Optional Dependency Extras

Templar includes optional dependency bundles for specific backend providers:

```bash
# Database drivers (psycopg2-binary, pymysql, etc.)
pip install "templar[db]"

# Authentication & cryptography helpers (bcrypt, cryptography)
pip install "templar[auth]"

# Cache backends (redis)
pip install "templar[cache]"

# Development & test tooling (pytest, pytest-cov, black, ruff)
pip install "templar[dev]"

# Install all optional extras
pip install "templar[all]"
```

---

## Shell Autocompletion

Templar provides automatic shell tab completion for Bash, zsh, Fish, and PowerShell:

```bash
# Install completion for your current shell
templar install-completion --shell bash   # or zsh, fish, powershell
```

Reload your shell or source your shell profile to activate command completion.

---

## Next Steps

Now that Templar is installed, proceed to:
- **[Quickstart Guide](QUICKSTART.md)** to generate and run your first project.
- **[Project Structure](PROJECT_STRUCTURE.md)** to understand the workspace layout.
