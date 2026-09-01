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
#     -o /tmp/pulse-bootstrap.sh && bash /tmp/pulse-bootstrap.sh [options]
#   bash bootstrap-devcontainer.sh --local [options]   # from inside an existing checkout —
#                                                       # used by this repo's own .devcontainer
#                                                       # and by docker/Dockerfile
#
# Download to a file and then run it — never `curl … | bash`. A pipeline reports its *last*
# command's status, so a failed download hands bash an empty stdin and the whole thing exits 0:
# the container comes up with nothing installed and the postCreateCommand claims success. Measured
# against a ref that did not exist: `curl -f` exits 22, the pipeline exits 0, the two-step form
# exits 22. That is not specific to a missing ref — a proxy error page or a network blip does the
# same.
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

# The network report, here rather than in bootstrap.sh's preflight. Neither container base image
# this flow targets ships a python3 (verified: not `ubuntu:24.04`, not
# `mcr.microsoft.com/devcontainers/base:ubuntu-24.04`), so that preflight skips itself — but by
# this line uv has installed one and `inv` runs on it. `inv setup` below is where nearly every
# download happens, so this is the useful place to know a host is blocked anyway.
#
# Advisory, like the preflight: it reports and the build continues.
if [ "${PULSE_SKIP_PREFLIGHT:-}" != "1" ]; then
  inv net.check --quick || true
fi

echo "PULSE_EXCLUDE_TAGS=${EXCLUDE_TAGS}"
# PULSE_ASSUME_YES: the deploy writer (tasks/deploy.py) asks before overwriting a destination it
# can't prove it wrote, and that prompt defaults to *no* with no terminal attached — so without
# this, a base image that ships its own copy of a file PULSE deploys would silently keep it, and
# the image would build "fine" while missing a dotfile. This is unattended provisioning: overwrite,
# and say so in the build log.
PULSE_ASSUME_YES=1 PULSE_EXCLUDE_TAGS="${EXCLUDE_TAGS}" inv setup
