# Installation Guide

This guide covers installing the Templar framework and configuring environment requirements for application development.

---

## Prerequisites

- **Python:** Version `3.10`, `3.11`, or `3.12`
- **Package Manager:** `pip` (or `uv` / `poetry`)
- **Supported Operating Systems:** Linux, macOS, Windows

---

## Standard Installation (from Source)

> **Note:** Templar is currently in alpha development and is not yet published on PyPI. Install it directly from source.

Clone the repository and install Templar into your Python virtual environment:

```bash
# Clone the repository
git clone https://github.com/Orivex-x/templar.git
cd templar

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install Templar from source
pip install -e .
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
pip install -e ".[db]"

# Authentication & cryptography helpers (bcrypt, cryptography)
pip install -e ".[auth]"

# Cache backends (redis)
pip install -e ".[cache]"

# Development & test tooling (pytest, pytest-cov, black, ruff)
pip install -e ".[dev]"

# Install all optional extras
pip install -e ".[all]"
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
