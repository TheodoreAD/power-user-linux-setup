#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_TOML="${SCRIPT_DIR}/setup.toml"

# Read Python versions from setup.toml.
UV_PYTHON_DEFAULT=$(grep '^\s*uv_python_default\s*=' "${SETUP_TOML}" | sed 's/.*"\(.*\)".*/\1/')
UV_PYTHON_EXTRA=$(grep '^\s*uv_python_extra\s*=' "${SETUP_TOML}" | grep -o '"[^"]*"' | tr -d '"')
UV_PYTHON_SET_DEFAULT=$(grep '^\s*uv_python_set_default\s*=' "${SETUP_TOML}" | grep -o 'true\|false')

if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    UV_NO_MODIFY_PATH=1 curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="${HOME}/.local/bin:${PATH}"
else
    echo "uv already installed: $(uv --version)"
fi

echo "Installing Python ${UV_PYTHON_DEFAULT}..."
if [ "${UV_PYTHON_SET_DEFAULT:-true}" = "false" ]; then
    uv python install "${UV_PYTHON_DEFAULT}"
else
    uv python install "${UV_PYTHON_DEFAULT}" --default
fi

for version in ${UV_PYTHON_EXTRA}; do
    echo "Installing Python ${version}..."
    uv python install "${version}"
done

echo "Installing invoke (Python ${UV_PYTHON_DEFAULT})..."
uv tool install --python "${UV_PYTHON_DEFAULT}" --force invoke --with python-dotenv

echo ""
echo "Bootstrap complete. Run 'inv --list' to see available tasks."
