#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Everything below this line is a download. On a corporate network some of them fail and the
# error arrives from whatever tool happened to make the request — `curl: (7)`, or a uv resolver
# error three screens down — with no indication of which host was blocked or what to do. So ask
# first, with the machine's own python3 (no dependencies, works on 3.10, see tasks/netdoctor.py),
# and print the diagnosis before the failure rather than after it.
#
# Advisory on purpose: a probe is not authoritative about a network that might allow the real
# request through a route it can't see, and refusing to bootstrap on its say-so would be worse
# than a confusing error. Skip it entirely with PULSE_SKIP_PREFLIGHT=1.
if [ "${PULSE_SKIP_PREFLIGHT:-}" != "1" ] && command -v python3 &> /dev/null; then
  if ! python3 "${SCRIPT_DIR}/tasks/netdoctor.py" --quick --timeout 3; then
    echo ""
    echo "Continuing anyway — the report above is advisory. Ctrl-C now if you'd rather fix it first."
    sleep 5
  fi
fi

if command -v apt-get &> /dev/null; then
  missing=()
  command -v curl &> /dev/null || missing+=(curl)
  command -v gpg &> /dev/null || missing+=(gnupg)
  command -v sudo &> /dev/null || missing+=(sudo)
  # git: `uv tool install 'repo-tasks @ git+https://…'` below shells out to it, and so does every
  # `git-clone` package later. A stock ubuntu:24.04 base has no git, so docker/Dockerfile's bake
  # died here with uv's "Git executable not found" — after a two-minute Python download.
  command -v git &> /dev/null || missing+=(git)
  dpkg -s ca-certificates &> /dev/null 2>&1 || missing+=(ca-certificates)

  if [ ${#missing[@]} -gt 0 ]; then
    echo "Installing OS prerequisites: ${missing[*]}..."
    if [ "$(id -u)" -eq 0 ]; then
      apt-get update && apt-get install -y "${missing[@]}"
    elif command -v sudo &> /dev/null; then
      sudo apt-get update && sudo apt-get install -y "${missing[@]}"
    else
      echo "Missing: ${missing[*]}, and no sudo available to install them." >&2
      echo "Install manually (as root, or with sudo already configured) and re-run." >&2
      exit 1
    fi
  fi
fi

SETUP_TOML="${SCRIPT_DIR}/setup.toml"

# Read Python versions from setup.toml.
UV_PYTHON_DEFAULT=$(grep '^\s*uv_python_default\s*=' "${SETUP_TOML}" | sed 's/.*"\(.*\)".*/\1/')
UV_PYTHON_EXTRA=$(grep '^\s*uv_python_extra\s*=' "${SETUP_TOML}" | grep -o '"[^"]*"' | tr -d '"')
UV_PYTHON_SET_DEFAULT=$(grep '^\s*uv_python_set_default\s*=' "${SETUP_TOML}" | grep -o 'true\|false')

# Whether to install the shared repo-tasks tool (brings inv/invoke with it) or bare invoke —
# unattended default from setup.toml's [settings], overridable per run with --repo-tasks/
# --invoke-only, or by answering the interactive prompt below when run from a terminal.
INSTALL_REPO_TASKS=$(grep '^\s*install_repo_tasks\s*=' "${SETUP_TOML}" | grep -o 'true\|false')
INSTALL_REPO_TASKS="${INSTALL_REPO_TASKS:-true}"

FORCE_INSTALL_REPO_TASKS=""
for arg in "$@"; do
  case "${arg}" in
    --invoke-only) FORCE_INSTALL_REPO_TASKS=false ;;
    --repo-tasks) FORCE_INSTALL_REPO_TASKS=true ;;
  esac
done

if ! command -v uv &> /dev/null; then
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

if [ -n "${FORCE_INSTALL_REPO_TASKS}" ]; then
  INSTALL_REPO_TASKS="${FORCE_INSTALL_REPO_TASKS}"
elif [ -t 0 ]; then
  default_prompt="Y/n"
  [ "${INSTALL_REPO_TASKS}" = "false" ] && default_prompt="y/N"
  echo ""
  echo "This machine can install the shared repo-tasks tool alongside invoke — one daily-driver"
  echo "task runner every repo in the personal repo family shares (not a per-repo pinned"
  echo "dependency). Skip this if you only want PULSE's own machine setup."
  read -r -p "Install repo-tasks? [${default_prompt}] " reply
  case "${reply}" in
    [yY]*) INSTALL_REPO_TASKS=true ;;
    [nN]*) INSTALL_REPO_TASKS=false ;;
    *) ;; # keep setup.toml's default
  esac
fi

if [ "${INSTALL_REPO_TASKS}" = "true" ]; then
  echo "Installing repo-tasks, which brings inv/invoke with it (Python ${UV_PYTHON_DEFAULT})..."
  uv tool install --python "${UV_PYTHON_DEFAULT}" --force --with-executables-from invoke \
    'repo-tasks @ git+https://github.com/TheodoreAD/repo-tasks'
else
  echo "Installing invoke (Python ${UV_PYTHON_DEFAULT})..."
  uv tool install --python "${UV_PYTHON_DEFAULT}" --force invoke --with python-dotenv
fi

echo ""
echo "Bootstrap complete. Run 'inv --list' to see available tasks."
