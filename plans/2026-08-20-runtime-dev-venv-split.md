---
status: in-progress
updated: 2026-08-22
depends_on: [repo-tasks, scaffoldapy]
---

**2026-08-22 implementation progress:**

- **§1 verification, resolved**: confirmed hands-on (sandboxed via `UV_TOOL_DIR`/`UV_TOOL_BIN_DIR`,
  no real machine state touched) that `uv tool install` does not expose a dependency's own console
  scripts by default — same limitation pipx historically had via `--include-deps`. The fix is
  `--with-executables-from invoke` on every install command (confirmed against a real throwaway test
  package), not hand-mirroring invoke's entry points as `[project.scripts]` — simpler and survives
  an invoke version bump for free.
- **§1 landed** in `repo-tasks` (`4c57e06`): `invoke`/`python-dotenv` are now real `dependencies`;
  `inv repo-tasks.{update,status,version,stamp}` implemented (nested `repo_tasks` collection,
  dashified to `repo-tasks.*`); `inv configure` now also stamps `bootstrap-repo-tasks.sh`.
  `repo-tasks.update` falls back to the default branch (no tag exists yet — repo-tasks hasn't cut
  its first release) rather than failing.
- **§2 landed** in PULSE (`08bc143`): `bootstrap.sh` defaults to installing `repo-tasks` instead of
  bare `invoke`; unattended default reads `setup.toml`'s `[settings] install_repo_tasks` (an
  existing top-level table already grep-read by this script for the `uv_python_*` keys, used as-is
  rather than inventing a separate `[bootstrap]` table as first sketched below); interactive prompt
  (`[ -t 0 ]`) when run from a terminal; `--repo-tasks`/`--invoke-only` override either.
- **§3 resolved as originally sketched**: no dedicated `bootstrap.sh`-shaped script for `repo-tasks`
  itself — the one-liner is documented in `repo-tasks/README.md`'s "Installing" section instead.
- **§4 landed** in `contributing/repo-family-architecture.md` (`08bc143`).
- **§6 landed** in PULSE (`08bc143`): `tasks/__init__.py`'s fallback is now
  `_import_repo_tasks_modules(simulate_missing=False)` — a `simulate_missing` flag exercises the
  degraded branch directly rather than needing `importlib.import_module` injection (which loses
  pyright's static module typing on the success path — `Any` leaking into `Collection.from_module()`
  calls otherwise) or `sys.modules` patching. `tests/test_tasks_init.py` covers both paths.
- **§5 landed** in PULSE (`3f3b94c`, refined `08bc143`-adjacent, `.github/workflows/ci.yml`, live on
  push/PR — this repo's first quality-gate CI, both gaps closed in one workflow as designed):
  `quality` job runs one bootstrap script (`.github/ci-bootstrap.sh`: `uv run inv dev-env.setup`,
  the one unavoidable raw `uv` call — same commands as local dev, unchanged per Design §2) then a
  bare `inv quality.check` — no inline `uv sync`/`uv run` in the workflow itself. A
  `runtime-guardrail` job mirrors bootstrap.sh's `--invoke-only` shape — bare
  `uv tool install
  invoke` (never `uv sync`), `inv --list`, then
  `PULSE_DRY_RUN=1 inv apt.repos apt.base apt.deb
  tools.install fonts.install` (the exact smoke
  command already documented in `docs/index.md`, reused rather than inventing a new list). Guards
  the Context section's actual verified invariant — bare invoke with no `repo_tasks` at all still
  gets a working `inv --list` via `_import_repo_tasks_modules` degrading to four `None`s — not the
  now-default `--repo-tasks` path, which `quality` already exercises via a real `uv sync`.
- **repo-tasks got its own CI too** (`740fd04` — it had none before): same pattern, a new root
  `bootstrap.sh` (`uv run inv venv.create`, the one unavoidable raw `uv` call, also usable directly
  by a human cloning the repo without direnv) then bare `inv quality.check`. `venv.py`'s `sync` now
  registers `.venv/bin` onto `$GITHUB_PATH` when present (a no-op locally, where direnv already does
  this) — CI's structural equivalent of direnv, so no raw PATH-activation line is ever needed in a
  workflow either. Also fixed a real bug this surfaced: `selfinstall.stamp()` was writing an
  unconditional `@v{version}` pin even when that tag doesn't exist upstream yet (true of this repo
  right now) — would have made every consumer's stamped script fail on first run; now falls back to
  an unpinned install the same way `update()` already does.
- **`scaffoldapy` investigated, deliberately left unchanged**: dropping `repo-tasks` from the
  generated `pyproject.toml.jinja`'s `dependency-groups.dev` (relying on the now-global tool
  instead, per this section's original guess) turns out entangled with a _second_, still-undesigned
  CI question — not the one §5 just closed. §5 only guards PULSE's own CI; a `scaffoldapy`-generated
  _consumer_ repo's own `.github/workflows/ci.yml` does `uv sync` then `uv run inv quality.check`,
  which structurally requires `repo-tasks`/`invoke` resolvable inside that project's own venv — a CI
  runner has no pre-bootstrapped global tool to fall back on. Making the dependency-groups change
  without also redesigning _that_ CI's bootstrap step (the stamped `bootstrap-repo-tasks.sh` pattern
  from §1, per "CI owns zero embedded bash" above) would silently break every generated repo's CI.
  Since the user has explicitly deferred that redesign ("we will build the CI later"), `scaffoldapy`
  stays on the per-repo pinned-dependency path (`repo-tasks/README.md`'s "Alternative" install
  method) until it's scoped — not a gap, a dependency ordering.
- **Remaining**: only the `scaffoldapy` consumer-repo CI redesign above — everything else in this
  plan (§1–§6) has landed.

# Guarding the runtime/dev-venv split

## Context

PULSE already has two lifecycles by design, verified empirically (2026-08-20):

- **Dev lifecycle** (contributing to this repo): `inv dev-env.setup` → `uv sync` (creates `.venv/`
  from `pyproject.toml`'s `dependency-groups.dev` — `pytest`, `ruff`, `basedpyright`, `repo-tasks`,
  `invoke`) + `direnv allow`. `inv quality.precommit`/`pytest` from there on, same as every other
  repo in the `repo-tasks` family.
- **Runtime lifecycle** (an actual PULSE user setting up/updating their machine): `./bootstrap.sh`
  installs `uv`, a Python version, and `invoke` as an isolated `uv tool`
  (`uv tool install --python ... --force invoke --with python-dotenv`) — never `uv sync`, never
  touches this repo's own dependency groups. `inv <task>` works from the repo root because invoke's
  own task-loading walks up from `cwd` and imports `tasks/` directly off the filesystem — no
  packaging/install step needed for `tasks` itself. `[project] dependencies = []` codifies that the
  package has zero runtime deps of its own; every machine-setup task shells out to OS tools (`apt`,
  `systemctl`, `gsettings`, ...), not Python packages. The one place dev-only tooling could leak
  into the runtime import graph is `tasks/__init__.py`'s
  `from repo_tasks import dev_env, docs, quality`, wrapped in a `try/except ImportError` so a
  machine with no `uv sync` ever run still gets a working `inv --list` (those three collections just
  don't show up). Ran the real, already-machine-wide `uv tool`-installed `invoke` binary directly
  against this checkout's `tasks/` tree with `uv sync` never having been run for that binary's own
  environment — `inv --list` exits `0`, lists every core collection, correctly omits
  `quality`/`dev-env`/`docs`. The invariant holds.

**2026-08-22 — scope widened to the whole `repo-tasks` family.** The holistic principle: `invoke`
should behave like `make` — a user-wide system utility, not a system-wide (apt) install, not a
per-project venv dependency. Tasks aren't part of the app they operate on, the same way a `Makefile`
target isn't coupled to whatever libraries the app it builds happens to link. Verified empirically
that the **stdlib-only-tasks principle already holds everywhere in practice**, just never stated or
protected: every `repo_tasks` module and every PULSE `tasks/*.py` module imports stdlib plus
`invoke` only, zero exceptions across ~45 files checked. The one third-party dependency reaching a
task-running environment today (`bootstrap.sh`'s `--with python-dotenv`) is already the "small,
generic, earns its place" kind of exception, not a violation.

**Where the real gap is**: every `scaffoldapy`-generated consumer repo (e.g. `olx-polite-mcp`) has
`repo-tasks` + `invoke` sitting in the _same_ `dependency-groups.dev` as the app's own runtime deps
(`fastmcp`, `httpx`, `playwright`, ...), merged by `uv sync` into one `.venv`. Nothing structurally
stops a future task module from importing an app-specific library sitting right there — the
stdlib-only invariant currently holds by convention and small repo count, not by any real boundary.
`scaffoldapy` itself doesn't have this problem (no separate app `src/` to leak into).

## Design

### 1. `repo-tasks` owns one user-wide tool install, decoupled from PULSE

`repo-tasks` owns its own install/update lifecycle entirely — explicit prep work for pulling PULSE
and `repo-tasks` fully apart. PULSE's `bootstrap.sh` currently owns the `uv tool install invoke ...`
line; that ownership moves to `repo-tasks`'s own repo.

**Hard scope boundary**: `repo-tasks`'s installer only ever touches its own isolated `uv tool` venv
— never installs `uv` itself, never touches shell rc files, never installs any other user-wide tool.
If `uv` isn't present, it fails with a clear error pointing at installing `uv` (via PULSE or
upstream) rather than trying to bootstrap `uv` itself. PULSE, conversely, always installs `uv`
unconditionally — never gated behind the repo-tasks-vs-bare-invoke choice (§2). Keeping these two
installers' responsibilities from bleeding into each other is the whole point: the moment one starts
doing a bit of the other's job "for convenience," the mental model needed to reason about any of
this stops being simple enough to hold in your head (see the hard constraint at the end of this
section).

**Only `repo-tasks` manages its own third-party dependencies.** `python-dotenv` (already in live use
via `bootstrap.sh`'s bolted-on `--with python-dotenv`) and anything added later become
`repo-tasks`'s own `pyproject.toml` `dependencies`, not flags injected by an external installer —
decouples the dependency list from PULSE entirely.

**Folding `invoke` into `repo-tasks` for a one-package install.** Goal:
`uv tool install --force
'repo-tasks @ git+...'` alone, no `--with` flags, working end to end.
**Hard requirement, to be verified — not assumed — as the first implementation step, blocking
everything else in this section**: `uv tool install` must actually install the transitive
dependency's own console-script binaries (`inv`/`invoke`) onto the tool's script path. `pipx` had
precisely this limitation historically (`--include-deps` was a required, explicit opt-in to expose a
dependency's own scripts, never implicit) — `uv tool install` needs the same behavior checked
against a real install (`uv tool
install` a package with a console-script dependency, then check
`which`/`ls` on the resulting script path directly) before relying on it. If it doesn't hold,
`repo-tasks` needs its own `[project.scripts]` entries mirroring `invoke`'s own entry-point target
(also to be confirmed by inspection, not assumed).

**A dedicated `repo-tasks` task namespace**, nested so it can never collide with a consuming
project's own local task names — CLI shape: **`inv repo-tasks.update`** (not `.self.update` — `inv`,
not `repo-tasks`, is the actual CLI entry point, so there's no "self" to refer to), alongside
`.status` (compares the globally-installed version against what the _current_ repo expects — drift
detection) and `.version` (prints what's active). A `.doctor` health check is a plausible later
addition, not designed now.

**`inv configure` stamps a committed, regenerated-on-demand bootstrap script per repo**, recording
the `repo-tasks` version active at the time `configure` last ran (via
`importlib.metadata.version("repo-tasks")` — `bump-my-version` is already a `repo-tasks` dev
dependency, so a real version string already exists to read). This script is **for CI and
reproducibility archaeology, not routine local use** — a human working across multiple repos on one
machine runs `repo-tasks.update` to move the shared global install forward; re-running a specific
repo's stamped script by habit would silently reinstall the global tool to whatever _that_ repo last
pinned, yanking it out from under whatever other repo was just being worked on. This asymmetry (CI:
always the stamped script; humans: always `repo-tasks.update`) needs to be stated explicitly
wherever this is documented. Matches an already-established rule
(`feedback_deliberate_regeneration_commit_artifacts` memory): regenerated artifacts get committed,
regenerated only by an explicit command, never silently/automatically.

**CI owns zero embedded bash** — every CI step is either the repo's stamped bootstrap script (before
`inv` exists) or a bare `inv <task>` (after). Exact CI YAML shape for consumer repos and
`repo-tasks` itself is explicitly deferred by the user ("we will build the CI later"), sequenced
after this decoupling lands — not designed here.

**The global daily-driver install doesn't need version pinning.** Original reasoning for pinning
(avoid silent drift, reproducibility) doesn't hold once the stamped-script mechanism above exists —
CI's reproducibility need is already served by that per-repo stamped script, and updates to the
daily driver are manual either way (never automatic), so "pin then bump manually" and "track main,
only bump when confirmed good" are behaviorally almost identical. The one real remaining edge:
legible version _labels_ (`v1.4.2` vs. a raw SHA) for `.status`/`.version` output and for naming a
rollback target — a UX nicety, not a safety mechanism. `repo-tasks.update` moves to the latest
tagged release (not bare `main` HEAD) purely for that legibility.

**Hard design constraint** (stated by the user directly, applies to every choice in this section):
none of this machinery may ever be something a normal user or a future agent working in a generated
repo needs to understand to work normally. One bootstrap (or it's already present from a previous
project) plus `inv <task>` must just work, with zero awareness of `uv tool install`, versions,
stamped scripts, or any of the above — otherwise the entire point of building this family of tooling
is defeated.

### 2. PULSE `bootstrap.sh`: default to installing `repo-tasks`, not bare `invoke`

Current behavior installs bare `invoke` only — sufficient for PULSE's own `tasks/`, which needs no
third-party package at all. Resolved design:

- **Default: install `repo-tasks`** (which brings `invoke` with it). Most real users of this
  machine's tooling end up working across PULSE _and_ other repos in the family sooner or later, so
  defaulting to the fuller install saves a second bootstrap step later.
- **Interactive run**: prompt at the point `bootstrap.sh` would otherwise silently install `invoke`,
  explaining the implication in plain terms (this opts the machine into a shared, globally-updated
  tool every repo in the family will use, not a per-repo pinned dependency; skippable if the user
  only wants PULSE's own machine setup) — default answer yes.
- **Unattended run**: no dedicated env var. Read the choice from `setup.toml`'s new
  `[bootstrap] install_repo_tasks = true` key — a small top-level table, deliberately separate from
  `[packages.*]` (that system only works once `inv` already exists to read it; this decision has to
  resolve _before_ `inv` exists at all). A CLI flag on `bootstrap.sh` is a reasonable one-off
  override for a single run without editing the file. No separate env var — that would just be a
  third mechanism for the same boolean.
- **Mechanical note**: `bootstrap.sh` doesn't read `setup.toml` today — that's `inv setup`'s job,
  which doesn't exist yet at this point in the script. Not a blocker: by the time the script reaches
  the invoke-install line, `uv` and a Python version are already guaranteed present, so a bare
  `python3 -c 'import tomllib; ...'` reads the key with zero new dependencies — but it is new
  responsibility for that script worth naming explicitly.

**The "chicken and egg" this raises is resolved by §1's scope boundary.** Worry: doesn't PULSE
defaulting to installing `repo-tasks` recreate the dependency it's supposed to be shedding? No, once
the two installers' scopes are genuinely separate:

1. **PULSE's own contributor dev-loop** doesn't need any of this global-tool machinery — PULSE is a
   "meta" repo with no app `src/` to mix task tooling into, same category as `repo-tasks` and
   `scaffoldapy` themselves. It keeps its current per-repo `.venv` dev loop entirely unchanged,
   independent of whatever `bootstrap.sh` does for end users.
2. **`bootstrap.sh` optionally running `repo-tasks`'s one-line install for a fresh end user** is the
   same shape `bootstrap.sh` already has with `uv` itself — it calls an external, independently
   maintained installer as one orchestrated step, guarantees that installer's own precondition (`uv`
   present) itself, and never reaches into `repo-tasks`'s internals or vice versa. Composing an
   external installer isn't the same relationship as depending on `repo-tasks` for PULSE's own
   operation.

### 3. `repo-tasks`'s zero-state bootstrap is smaller than first proposed

Given §1's scope boundary (`repo-tasks` never installs `uv`, only checks for it), `repo-tasks`'s
entire "bootstrap" collapses to one command: `uv tool install --force 'repo-tasks @ git+...'`, run
only after confirming `uv` is on `PATH`. Small enough that a dedicated curl-pipeable `bootstrap.sh`
may not be worth having — documenting the one-liner in `repo-tasks`'s own `README.md` is probably
sufficient; a trivial 2-3-line wrapper script (check `uv` present, run the install, clear error
otherwise) is the fallback if a documented one-liner turns out to be too easy to get wrong in
practice. Nothing about it resembles PULSE's `bootstrap.sh` in scope. Since `repo-tasks` is a
standard Python package with real entry points, other installers (`pipx install repo-tasks`) could
technically work too — not worth building or documenting support for, since the whole point of this
design is a `uv`-based, single-toolchain world; `pipx` compatibility is an incidental side effect of
standard packaging, not a target.

### 4. Write the stdlib-only-tasks rule down

No-regret step, independent of everything else here: a short paragraph in
`contributing/repo-family-architecture.md` (or a new `contributing/*.md` if it grows past a
paragraph) codifying "task modules are stdlib + `invoke` only; a new third-party import in a task
module needs a specific justification, the same bar `python-dotenv` already cleared." Gives the
isolation mechanism in §1 something concrete to point at.

### 5. CI guardrail for the runtime/dev-venv split (PULSE), resolved

Decided: a **lightweight CI job only** — mirrors `bootstrap.sh`'s real invocation shape (no
`uv sync`, `uv tool install invoke`, then `inv --list` + a small set of dry-run smoke tasks). Fast,
no container. `docker/Dockerfile`'s full build stays a separate, manual, heavier check as it is
today — not promoted into CI as part of this plan.

This job **lands together with PULSE's first general quality-gate CI workflow** (`pytest`/
`inv quality.check`) — this repo currently has zero CI running either. One new workflow covers both
gaps at once rather than treating them as separate asks.

### 6. `tasks/__init__.py`'s fallback branch gets a testable helper, resolved

Extract the `try/except ImportError` around `from repo_tasks import dev_env, docs, quality` into a
small, directly-callable helper function that `tasks/__init__.py` then uses.
`tests/test_tasks_init.py` covers: `tasks.namespace` builds successfully and contains every expected
top-level collection name, and a second test exercising the helper directly to assert the degraded
case is correct — no need to fake an import failure via `sys.modules` patching.

### 7. Superseded — collapsed for the record

Four mechanisms were weighed for §1's consumer-repo gap before converging on the design above; kept
here so the reasoning trail isn't lost, not because they're live options:

1. **Status quo** — `repo-tasks`/`invoke` in `dependency-groups.dev`, one `uv sync`, one `.venv`.
   Simplest, but exactly the mixing problem this plan solves — no structural boundary, relies on
   convention.
2. **One global `uv tool install invoke --with 'repo-tasks @ git+...'`** — isolated, but a single
   global environment forces every consumer repo onto the same `repo-tasks` version at once,
   breaking per-repo `uv.lock` pinning. (Resolved: the per-repo stamped script in §1 gives this
   back.)
3. **`uvx --from 'repo-tasks @ git+...@<pinned-ref>' inv <task>` per repo** — real isolation and
   per-repo pinning, but needs the pin to live somewhere per-repo since `uvx` doesn't read the
   project's own `uv.lock` — a new mechanism `uv`/`scaffoldapy` don't provide out of the box.
4. **Hybrid**: `invoke` global, `repo-tasks` resolved per-repo via option 3's pinning — splits
   "runner" from "task library" the way `make`/`Makefile` already are.

**Ruled out: `uv` workspaces.** Verified via `uv sync --help` (`--package <PACKAGE>`: "The
workspace's environment (`.venv`) is updated to reflect the subset of dependencies declared by the
specified workspace member packages") that a workspace resolves to **one `.venv` at the workspace
root**, always — `--package` only changes which subset of dependencies get synced _into that same
venv_, it doesn't produce two environments that coexist. Splitting a consumer repo into an `app`
member and a `tasks` member wouldn't isolate them; every `inv <task>` and every app test run would
need its own `uv sync --package <x>` first, overwriting the shared venv each time. Workspaces also
require every member to live locally under one root — would mean vendoring `repo-tasks` into each
consumer repo instead of a pinned git dependency, breaking the git-as-artifact-store distribution
model (`contributing/mcp-skill-shipping.md`). Workspaces solve "one coherent environment for
interdependent local packages," the opposite of what's needed here.

## Files touched

**`power-user-linux-setup`**:

- `bootstrap.sh` — default to `repo-tasks` install, interactive prompt, `setup.toml`-driven
  unattended choice, CLI override flag.
- `setup.toml` — new `[bootstrap] install_repo_tasks = true` key.
- `tasks/__init__.py` — extract the `repo_tasks` import fallback into a testable helper.
- `tests/test_tasks_init.py` (new) — namespace build + fallback-helper coverage.
- `.github/workflows/*.yml` (new) — first general quality-gate workflow + the lightweight runtime
  guardrail job, landed together.
- `pyproject.toml` — one-line comment on `dependencies = []` pointing at the design writeup.
- `contributing/repo-family-architecture.md` — stdlib-only-tasks paragraph; update with the
  finalized `repo-tasks`/PULSE scope split from this plan.
- `CONTRIBUTING.md` — "Design notes" pointer to the above.

**`repo-tasks`**:

- `pyproject.toml` — own `python-dotenv` (and future helper libs) as real `dependencies`; possibly
  `[project.scripts]` entries mirroring `invoke`'s, pending the §1 verification step.
- `README.md` — the one-line install command as the documented "bootstrap."
- New task module (naming TBD, shape settled: `repo-tasks.update`/`.status`/`.version`).
- `configure.py` — extend to stamp the per-repo bootstrap script with the active version.

**`scaffoldapy`**: likely affected but not fully specified here — once `repo-tasks` stops being a
per-repo dev dependency for consumer repos, the generated `pyproject.toml.jinja`'s
`dependency-groups.dev` entry for `repo-tasks` and the `_tasks` hook's `uv run inv configure` step
may need to change shape (e.g. to a bare `inv configure`, relying on the now-global tool). Left for
implementation time rather than guessed at here.

## Verification

- **Blocking, first**: real `uv tool install` test confirming transitive console-script exposure
  (§1) — everything else in §1 depends on the answer.
- `repo-tasks`: `inv quality.precommit` green, including new tests for the update/status/version
  tasks and the `configure`-time stamping logic.
- PULSE: `inv quality.precommit` green; new CI workflow (§5) passes on a real push;
  `tests/test_tasks_init.py` passes, including the extracted-helper fallback case.
- Manual: run the resolved `bootstrap.sh` both interactively (prompt appears, default yes works) and
  unattended with `setup.toml`'s `install_repo_tasks` set both `true` and `false`, confirming the
  right thing installs each time.
