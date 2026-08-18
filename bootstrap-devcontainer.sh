#!/usr/bin/env bash
set -euo pipefail

# Distributable entrypoint for layering PULSE's curated CLI tooling onto an existing dev
# container base image, without cloning/maintaining a full checkout yourself. See
# docs/dev-container.md, "Recommended: devcontainer.json + postCreateCommand" for the
# devcontainer.json this is meant to be curled by (pinned to a `stable` git ref CI only moves
# forward on a green smoke-test — see .github/workflows/devcontainer.yml).
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/TheodoreAD/power-user-linux-setup/stable/bootstrap-devcontainer.sh \
#     | bash -s -- [options]
#   bash bootstrap-devcontainer.sh --local [options]   # from inside an existing checkout —
#                                                       # used by this repo's own .devcontainer
#                                                       # and by docker/Dockerfile
#
# Options:
#   --exclude-tags <tags>   comma-separated PULSE_EXCLUDE_TAGS. Default: resolved after
#                           bootstrapping via `inv devcontainer.print-exclude-tags` — the single
#                           source of truth is CONTAINER_EXCLUDE_TAGS in tasks/devcontainer.py,
#                           not a second copy hardcoded here.
#   --ref <git-ref>         git ref to shallow-clone (default: stable). Ignored with --local.
#   --local                 skip cloning; assume already inside a checkout at this script's own
#                           directory.

REPO_URL="https://github.com/TheodoreAD/power-user-linux-setup.git"
CLONE_DIR="${HOME}/.local/share/pulse-devcontainer-src"

REF="stable"
EXCLUDE_TAGS=""
LOCAL=false

while [ $# -gt 0 ]; do
  case "$1" in
    --exclude-tags)
      EXCLUDE_TAGS="$2"
      shift 2
      ;;
    --ref)
      REF="$2"
      shift 2
      ;;
    --local)
      LOCAL=true
      shift
      ;;
    *)
      echo "bootstrap-devcontainer.sh: unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if [ "${LOCAL}" = true ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "${SCRIPT_DIR}"
else
  echo "Cloning power-user-linux-setup@${REF} into ${CLONE_DIR}..."
  rm -rf "${CLONE_DIR}"
  git clone --branch "${REF}" --depth 1 "${REPO_URL}" "${CLONE_DIR}"
  cd "${CLONE_DIR}"
fi

bash ./bootstrap.sh
# bootstrap.sh's own `export PATH=...` is scoped to that child process — re-export here so `inv`
# (installed into ~/.local/bin by bootstrap.sh via `uv tool install`) is callable below.
export PATH="${HOME}/.local/bin:${PATH}"

if [ -z "${EXCLUDE_TAGS}" ]; then
  EXCLUDE_TAGS="$(inv devcontainer.print-exclude-tags)"
fi

echo "PULSE_EXCLUDE_TAGS=${EXCLUDE_TAGS}"
PULSE_EXCLUDE_TAGS="${EXCLUDE_TAGS}" inv setup
