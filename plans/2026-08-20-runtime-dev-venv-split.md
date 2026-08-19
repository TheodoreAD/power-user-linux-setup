---
status: idea
updated: 2026-08-20
---

# Guarding the runtime/dev-venv split

## Context

The two lifecycles the user asked about **already exist by design**, verified empirically today, not
just asserted:

- **Dev lifecycle** (contributing to this repo): `inv dev-env.setup` → `uv sync` (creates `.venv/`
  from `pyproject.toml`'s `dependency-groups.dev` — `pytest`, `ruff`, `basedpyright`, `repo-tasks`,
  `invoke`) + `direnv allow`. `inv quality.precommit`/`pytest` from there on, same as every other
  repo in the `repo-tasks` family now (`docs/claude-code.md`, `tests/README.md`, `CONTRIBUTING.md`
  already document this).
- **Runtime lifecycle** (an actual PULSE user setting up/updating their machine): `./bootstrap.sh`
  installs `uv`, a Python version, and `invoke` as an **isolated `uv tool`**
  (`uv tool install
  --python ... --force invoke --with python-dotenv`) — never `uv sync`, never
  touches this repo's own `pyproject.toml` dependency groups at all. `inv <task>` from the repo root
  then works because invoke's own task-loading walks up from `cwd` and imports `tasks/` directly off
  the filesystem — no packaging/install step needed for `tasks` itself.
  `[project] dependencies = []` in `pyproject.toml` codifies that the package has zero runtime deps
  of its own; every actual machine-setup task shells out to OS tools (`apt`, `systemctl`,
  `gsettings`, ...), not Python packages.
- The one place dev-only tooling could leak into the runtime import graph is `tasks/__init__.py`'s
  `from repo_tasks import dev_env, docs, quality` — wrapped in a `try/except ImportError`
  specifically so a machine with no `uv sync` ever run still gets a working `inv --list` (those
  three collections just don't show up).

**Verified today**, not assumed: ran the real, already-machine-wide `uv tool`-installed `invoke`
binary (`~/.local/share/uv/tools/invoke/bin/inv` — the exact one `bootstrap.sh` installs, isolated
from this repo's own `.venv`) directly against this checkout's `tasks/` tree, with `uv sync` never
having been run for that binary's own environment. `inv --list` exits `0`, lists every core task
collection (apt/gnome/wsl/ssh/...), and correctly omits `quality`/`dev-env`/`docs` (`repo_tasks`
isn't resolvable there). This is exactly the invariant "users can run as they do today, directly
after bootstrap" depends on, and it holds right now.

**What's actually missing isn't the split itself — it's a guardrail that it stays true:**

1. **Nothing automated verifies this.** `docker/Dockerfile` exercises the real end-to-end bootstrap
   path (`bootstrap-devcontainer.sh --local` → `bootstrap.sh` → `inv setup`, no `uv sync` anywhere)
   but is explicitly commented "not built by CI... for local iteration" — a human has to remember to
   run it. `.github/workflows/devcontainer.yml` is `workflow_dispatch`-only (deliberately, per
   existing project notes). **There is currently no CI workflow running `pytest`/`inv quality.check`
   at all** — `.github/workflows/` has exactly two jobs, and both are docs-publish-only
   (`publish_on_push.yml`). A future change that adds one unconditional top-level import of a
   dev-only package into any core task module — or otherwise makes a runtime task depend on
   something `uv sync` provides — would go undetected until a real user's bootstrap actually broke.
2. **No test exercises `tasks/__init__.py` itself.** Every existing test imports a submodule
   directly (`from tasks import ai`, `from tasks import util`, ...), bypassing the package's own
   `__init__.py` — and with it, the `try/except ImportError` that's the actual load-bearing code for
   "runtime doesn't need `repo_tasks`." Zero coverage on the one function that matters most here.
3. **`pyproject.toml`'s `dependencies = []` has no comment.** A future contributor or agent
   unfamiliar with this design could reasonably read an empty list as an oversight and "fix" it by
   adding a package there instead of to `dependency-groups.dev`, silently reintroducing a runtime
   coupling — exactly the kind of mistake nothing here would currently catch (see point 1).

## Open questions

- **Verification mechanism**: a lightweight CI job that mirrors `bootstrap.sh`'s exact invocation
  shape (`uv tool install invoke`, no `uv sync`, then `inv --list` + maybe a couple of
  `PULSE_DRY_RUN=1` dry-run smoke tasks) — fast, no Docker, but only catches import-time breakage
  and whatever the smoke tasks happen to touch. Or: promote `docker/Dockerfile`'s already-real,
  already-written zero-install build into an actual CI-gated job — heavier (needs a container, root,
  real `apt` access) but exercises the literal real path end to end, no invented parallel mechanism.
  `[NEEDS CLARIFICATION: which one, or both — lightweight job on every push, Docker build on a
  slower cadence?]`
- **This repo currently has zero CI running `pytest`/`inv quality.check` at all.** Is standing up
  the _first_ test/quality CI workflow in scope here (the runtime-guardrail job could ride in the
  same new workflow, landing both gaps at once), or is that an adjacent-but-separate ask worth its
  own plan? `[NEEDS CLARIFICATION]`
- **How to unit-test `tasks/__init__.py`'s fallback branch**: mock `repo_tasks` as unimportable
  (e.g. `monkeypatch.setitem(sys.modules, "repo_tasks", None)` before a fresh import of `tasks`) vs.
  extracting the try/except into a small, directly-testable helper function. Real design choice, not
  resolved yet.

## Recommended direction

Rough, not prescriptive — pending the open questions above:

1. Add a CI job mirroring `bootstrap.sh`'s real invocation shape (no `uv sync`,
   `uv tool install
   invoke`, then `inv --list` + a small set of dry-run smoke tasks) as the fast,
   always-on guardrail; treat `docker/Dockerfile`'s full build as a separate, heavier check
   (possibly the thing that finally turns `devcontainer.yml`'s dispatch-only trigger into something
   with a real automated companion — same open question flagged in `CLAUDE.md` about that workflow
   already).
2. Add a `tests/test_tasks_init.py` covering: `tasks.namespace` builds successfully and contains
   every expected top-level collection name, and a second test asserting the graceful-degrade branch
   actually degrades gracefully when `repo_tasks` can't be imported.
3. Add the missing one-line comment to `pyproject.toml`'s `dependencies = []`, pointing at wherever
   the fuller rationale ends up living.
4. Write the "two lifecycles" design up as prose in `contributing/<topic>.md` (same shape as
   `contributing/verify.md`/`contributing/cli-allowlist.md`) — why `dependencies = []`, why `tasks`
   needs no install to be invoke-discoverable, why `dependency-groups.dev` carries what it does, and
   exactly what invariant the new CI job(s) in (1) exist to protect. `CONTRIBUTING.md`'s "Design
   notes" section gets a pointer to it.
