#!/usr/bin/env bash
set -euo pipefail

# One-line clone-and-install of PULSE onto a fresh Ubuntu machine. Clones a pinned ref, runs
# bootstrap.sh (uv + Python + invoke), then hands over to `inv setup` after asking.
#
# Usage — download, then run. Never `curl … | bash`:
#   curl -fsSL https://raw.githubusercontent.com/TheodoreAD/power-user-linux-setup/stable/install.sh \
#     -o /tmp/pulse-install.sh && bash /tmp/pulse-install.sh
#
# The reason that is two steps rather than a pipe is measured, and written up once in
# bootstrap-devcontainer.sh's header rather than restated here: a pipeline reports its *last*
# command's status, so a failed download hands bash an empty stdin and the whole thing exits 0
# claiming success. Two more consequences are specific to this script and are the reason it would
# want the same shape even if that one did not exist:
#
#   - bootstrap.sh asks whether to install repo-tasks, guarded on `[ -t 0 ]`. Piped, the question
#     is not merely skipped — setup.toml's default is taken silently and nobody learns a choice
#     existed.
#   - `inv setup` needs root, and util.ensure_sudo() collects it outside invoke, falling back to
#     `sudo -v` as a plain subprocess owning the real terminal. A pipe has no terminal to own, and
#     on a fresh machine there is no ~/.local/bin/askpass-zenity yet either — PULSE is what installs
#     it.
#
# The confirmation before `inv setup` follows the same reasoning as apt's: on by default, --yes to
# skip. This is the least reversible thing this repo does — apt packages, the login shell, GNOME
# settings — and a line pasted from a README should say so before it starts.
#
# Options:
#   --dir <path>            where to clone (default: ~/projects/power-user-linux-setup). This
#                           directory is permanent: see the note this script prints on the way out.
#   --ref <git-ref>         git ref to shallow-clone (default: stable, the tag that tracks tested
#                           commits). Use master for the newest work.
#   --repo-url <url|path>   clone from somewhere other than the canonical GitHub repo — a fork, a
#                           corporate mirror, or a local path. The CI smoke test uses this to
#                           install the commit under test rather than whatever is published.
#   --exclude-tags <tags>   comma-separated PULSE_EXCLUDE_TAGS for the `inv setup` run — e.g.
#                           gui,desktop,gnome for a headless box. See docs/configuration.md.
#   --bootstrap-only        stop after bootstrap.sh; print the `inv setup` command instead of
#                           running it.
#   --yes                   skip the confirmation before `inv setup`.
#   --help                  this text.

REPO_URL="https://github.com/TheodoreAD/power-user-linux-setup.git"

CLONE_DIR="${HOME}/projects/power-user-linux-setup"

# `stable` rather than `master`, and it is a tag rather than a branch — the same ref
# bootstrap-devcontainer.sh pins. Pinning is the point: it lets someone read this script today and
# run the same bytes tomorrow, which is the only thing that makes a pasted one-liner inspectable at
# all. The cost is that the tag has to be moved deliberately, and until it is, everything here
# resolves to whatever commit it currently names — so a new file is not reachable through the raw
# URL above until the tag moves past the commit that added it. `--ref master` gets the newest work.
REF="stable"
EXCLUDE_TAGS=""
BOOTSTRAP_ONLY=false
ASSUME_YES=false

# The header comment above *is* the help text — printed by stripping its leading `#`, so the two
# cannot drift apart. Line-range addressing would; this reads until the block ends.
usage() {
  awk 'NR<=3 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "${BASH_SOURCE[0]}"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --dir)
      CLONE_DIR="$2"
      shift 2
      ;;
    --ref)
      REF="$2"
      shift 2
      ;;
    --repo-url)
      REPO_URL="$2"
      shift 2
      ;;
    --exclude-tags)
      EXCLUDE_TAGS="$2"
      shift 2
      ;;
    --bootstrap-only)
      BOOTSTRAP_ONLY=true
      shift
      ;;
    --yes | -y)
      ASSUME_YES=true
      shift
      ;;
    --help | -h)
      usage
      exit 0
      ;;
    *)
      echo "install.sh: unknown option: $1" >&2
      echo "install.sh: run with --help for the options." >&2
      exit 1
      ;;
  esac
done

# git is needed before bootstrap.sh gets a chance to install it — the clone below *is* the step
# that would otherwise provide it. Everything else (uv, Python, invoke) bootstrap.sh handles.
if ! command -v git &> /dev/null; then
  if ! command -v apt-get &> /dev/null; then
    echo "install.sh: git is not installed and this is not an apt system — install git and re-run." >&2
    exit 1
  fi
  echo "Installing git..."
  if [ "$(id -u)" -eq 0 ]; then
    apt-get update && apt-get install -y git
  elif command -v sudo &> /dev/null; then
    sudo apt-get update && sudo apt-get install -y git
  else
    echo "install.sh: git is missing and there is no sudo to install it with." >&2
    exit 1
  fi
fi

# Adopt, never clobber. The container bootstrap `rm -rf`s its clone because nothing there outlives
# the image; here the opposite holds, and destroying a checkout would take uncommitted work with it.
# An existing PULSE checkout is used exactly as it stands — no fetch, no checkout, no ref change —
# because this script's job is getting a machine started, not updating one that already is.
if [ -e "${CLONE_DIR}" ]; then
  if [ -d "${CLONE_DIR}/.git" ] && [ -f "${CLONE_DIR}/setup.toml" ] && [ -f "${CLONE_DIR}/bootstrap.sh" ]; then
    echo "Using the checkout already at ${CLONE_DIR}."
    echo "Left exactly as it is — not fetched, and not switched to ${REF}."
    echo "Run 'git pull' there yourself if you want it newer."
  else
    echo "install.sh: ${CLONE_DIR} already exists and is not a power-user-linux-setup checkout." >&2
    echo "install.sh: refusing to touch it. Pass --dir <path> to clone somewhere else." >&2
    exit 1
  fi
else
  # Naming the source rather than just the ref: with --repo-url this is the one line that says
  # whose code is about to run, which matters more for an installer than for a build script.
  echo "Cloning ${REPO_URL}@${REF} into ${CLONE_DIR}..."
  mkdir -p "$(dirname "${CLONE_DIR}")"
  git clone --branch "${REF}" --depth 1 "${REPO_URL}" "${CLONE_DIR}"
fi

cd "${CLONE_DIR}"

bash ./bootstrap.sh
# bootstrap.sh's own `export PATH=...` is scoped to that child process — re-export here so `inv`
# (installed into ~/.local/bin by bootstrap.sh via `uv tool install`) is callable below.
export PATH="${HOME}/.local/bin:${PATH}"

# An `[ … ] && x=y` one-liner would be the obvious spelling and would end the script: the AND-list
# returns the test's status, and a false test under `set -e` is a non-zero exit like any other.
if [ -n "${EXCLUDE_TAGS}" ]; then
  setup_cmd="PULSE_EXCLUDE_TAGS=${EXCLUDE_TAGS} inv setup"
else
  setup_cmd="inv setup"
fi

echo ""
echo "Bootstrap complete. The checkout is at:"
echo "  ${CLONE_DIR}"
echo ""
# Said here rather than only in the docs because this is the one moment the path is on screen and
# the person is looking at it. `spowse` is installed --editable against this directory and
# `deploy.status` compares the machine to it, so moving the checkout later breaks the command with
# a bare "No module named 'tasks'" — see plans/ and docs/tasks.md.
echo "Keep it there. PULSE's own tools resolve this path at run time rather than copying it:"
echo "the 'spowse' command is installed against it, and 'inv deploy.status' reports drift by"
echo "comparing your home directory to it. Moving it later breaks both."

if [ "${BOOTSTRAP_ONLY}" = true ]; then
  echo ""
  echo "Stopping here (--bootstrap-only). To finish:"
  echo "  cd ${CLONE_DIR} && ${setup_cmd}"
  exit 0
fi

if [ "${ASSUME_YES}" != true ]; then
  # No terminal and no --yes: refuse rather than proceed. This is the case a `curl … | bash` lands
  # in, and running a full machine setup unattended because the prompt could not be shown is the
  # silent-default failure this script exists to avoid.
  if [ ! -t 0 ]; then
    echo ""
    echo "install.sh: no terminal on stdin, so the confirmation cannot be shown." >&2
    echo "install.sh: download the script and run it (see --help), or pass --yes." >&2
    echo "install.sh: to finish by hand: cd ${CLONE_DIR} && ${setup_cmd}" >&2
    exit 1
  fi
  echo ""
  echo "Next is '${setup_cmd}', which installs apt packages, changes your login shell,"
  echo "writes dotfiles into your home directory, and applies GNOME settings. It asks for sudo."
  read -r -p "Run it now? [Y/n] " reply
  case "${reply}" in
    [nN]*)
      echo "Stopped. To finish later:"
      echo "  cd ${CLONE_DIR} && ${setup_cmd}"
      exit 0
      ;;
    *) ;;
  esac
fi

echo ""
if [ -n "${EXCLUDE_TAGS}" ]; then
  PULSE_EXCLUDE_TAGS="${EXCLUDE_TAGS}" inv setup
else
  inv setup
fi
