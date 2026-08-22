#!/usr/bin/env bash
set -euo pipefail

# CI's equivalent of `inv dev-env.setup` after a fresh clone — the one place a raw `uv` call is
# unavoidable, since there's no `inv` to bootstrap with yet. `uv run` syncs this repo's own .venv
# (dependency-groups.dev keeps repo-tasks/invoke as a per-repo dev dependency here, unchanged —
# see plans/2026-08-20-runtime-dev-venv-split.md's Design §2) and then runs `inv dev-env.setup`
# inside it, which — via repo-tasks' venv.py registering GITHUB_PATH — also adds .venv/bin to
# PATH for the rest of the job. Every CI step after this one is a bare `inv <task>` call, not a
# raw uv/venv-activation command sprinkled into the workflow.

command -v uv > /dev/null 2>&1 || {
  echo "uv not found on PATH — install uv first" >&2
  exit 1
}
uv run inv dev-env.setup
