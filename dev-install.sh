#!/usr/bin/env bash
# Set up Templar for local development using the src/ package layout.
# Usage: ./dev-install.sh [--test]

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
RUN_TESTS=false

if [[ "${1:-}" == "--test" ]]; then
    RUN_TESTS=true
elif [[ -n "${1:-}" ]]; then
    echo "Usage: $0 [--test]" >&2
    exit 2
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Python executable not found: $PYTHON_BIN" >&2
    echo "Set PYTHON_BIN to a Python 3.10+ executable and try again." >&2
    exit 1
fi

if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
    echo "Templar requires Python 3.10 or newer." >&2
    exit 1
fi

cd "$PROJECT_DIR"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    echo "Creating virtual environment: $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

echo "Installing Templar in editable development mode..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -e ".[dev]"

echo
echo "Development environment is ready."
echo "Activate it with: source \"$VENV_DIR/bin/activate\""
echo "Run the CLI with:  $VENV_DIR/bin/templar --help"

if [[ "$RUN_TESTS" == true ]]; then
    echo
    echo "Running tests..."
    "$VENV_DIR/bin/python" -m pytest -q
fi
