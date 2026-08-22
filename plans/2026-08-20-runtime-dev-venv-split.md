---
status: idea
updated: 2026-08-22
depends_on: [repo-tasks, scaffoldapy]
---

# Guarding the runtime/dev-venv split

## Context

**2026-08-22 update — scope widened from PULSE-only to the whole `repo-tasks` family.** The user
framed the holistic principle directly: `invoke` should behave like `make` — a **user-wide system
utility**, not a system-wide (apt) install, and not (ideally) a per-project venv dependency either.
Tasks are not part of the app they operate on, the same way a `Makefile` target isn't coupled to
whatever libraries the app it builds happens to link. Corollary principles stated explicitly:

- **Task code should be stdlib-only, with a high bar for exceptions.** `invoke` itself is the one
  mandatory dependency; small, generic CLI-ergonomics libraries (`python-dotenv`, maybe `rich`) are
  allowed if they earn their place, but a task module must never depend on an *app-specific* library
  (`fastmcp`, `httpx`, `playwright`, ...) — those belong to the src package the tasks happen to
  operate on, not to the tasks themselves.
- **If a user-wide `invoke` install is somehow missing, fall back to `uvx invoke`** (ephemeral,
  no install) rather than failing outright.
- **Testing task code still needs a venv** (pytest has to import the task modules to test them), but
  that venv must never be the same one — or even overlap in dependency graph — with the src
  package's own runtime/dev venv. **Resolved by the converged design below**: once `repo-tasks` is a
  global `uv tool` install rather than a per-repo dev dependency, consumer repos have no task-venv at
  all to worry about — a local task customization, if one ever exists, tests against the same global
  env everyone already has, never against (or mixed with) the app's own venv.

**Verified empirically today (2026-08-22), not assumed** — the stdlib-only principle already holds
almost everywhere in practice, it's just never been stated as a rule or protected by anything:

- Every `repo_tasks` task module (`quality.py`, `dist.py`, `agents.py`, `venv.py`, `docker.py`,
  `configs.py`, `docs.py`, `configure.py`, `version.py`, `deps.py`, `dev_env.py`, `gitflow.py`,
  `direnv.py`, `projects.py`) imports only stdlib plus `from invoke import task`/`Collection`/`Exit`.
  Zero exceptions.
- Every PULSE `tasks/*.py` module: same result, stdlib + `invoke` only, zero exceptions (checked all
  ~30 files).
- The one place a third-party dependency does reach a task-running environment today:
  `bootstrap.sh`'s `uv tool install --force invoke --with python-dotenv` — already exactly the
  "small, generic, earns its place" exception the new principle describes, not a violation of it.
- `scaffoldapy` itself doesn't fit this frame the same way — it has no separate "app src" a tasks
  layer could leak into (`dependencies = []`, and `copier` in its dev group is scaffoldapy's actual
  product, not incidental task tooling), so the mixing concern below doesn't apply to it directly.
  Its `_tasks` hook (`uv sync`, `uv run inv configure`) and its own dogfooded `tasks.py` are already
  minimal and are not part of what this update is trying to change.

**Where the real gap is: generated/consumer repos** (every `scaffoldapy`-generated repo, e.g.
`olx-polite-mcp`). Today, `repo-tasks` + `invoke` sit in the *same* `dependency-groups.dev` as the
app's own runtime deps (`fastmcp`, `httpx`, `playwright`, ...), and a single `uv sync` merges all of
it into one `.venv`. Nothing stops a future task module from casually importing an app-specific
library that happens to already be sitting in that shared environment — the stdlib-only invariant
currently holds by convention and small repo count, not by any structural boundary. This is the
piece the two already-landed lifecycles (dev vs. runtime, described below for PULSE specifically)
don't yet have an equivalent of for the rest of the family.

### Converged design (2026-08-22, continued)

Four candidate mechanisms were weighed for the generated/consumer-repo gap above (status quo,
global `uv tool install`, per-repo `uvx --from ...@<pin>`, a runner/library hybrid — kept below,
collapsed, for the record) and `uv` workspaces were considered and ruled out (also kept below). The
design has since converged on a sharpened version of the global-tool option, resolving the objection
that killed it the first time round (loss of per-repo pinning):

**Naming correction (2026-08-22, same day):** the package/repo/CLI-collection name is `repo-tasks`
throughout — no rename to `repo-tools`. An earlier pass in this doc used `repo-tools` consistently
across two messages, which read as a deliberate naming choice and got carried into the doc as an
open question; it was actually a slip, corrected by the user directly. Recorded here as the doc's
own paper trail, not because the mistake itself matters going forward.

- **One user-wide tool install, decoupled from PULSE.** `repo-tasks` owns its *own* install/update
  lifecycle entirely — this is explicitly prep work for pulling PULSE and `repo-tasks` fully apart;
  PULSE's `bootstrap.sh` currently owns the `uv tool install invoke ...` line, and that ownership
  moves to `repo-tasks`'s own repo once this lands, not before (see the PULSE-side wrinkle below —
  this isn't quite as clean a split as it first sounds).
- **Hard scope boundary, resolved (2026-08-22): `repo-tasks`'s installer only ever touches its own
  isolated `uv tool` venv — nothing else, ever.** It never installs `uv` itself, never touches shell
  rc files, never installs any other user-wide tool. If `uv` isn't present when `repo-tasks`'s own
  install path runs, it fails with a clear error pointing the user at installing `uv` (via PULSE or
  upstream), rather than trying to bootstrap `uv` itself. PULSE, conversely, **always installs `uv`
  unconditionally** — that step is never gated behind the repo-tasks-vs-bare-invoke choice below, it
  happens either way. Keeping these two installers' responsibilities from bleeding into each other is
  the whole point: the moment one starts doing a bit of the other's job "for convenience," the mental
  model needed to reason about any of this stops being simple enough to hold in your head — which
  defeats the actual goal (see the hard design constraint further down).
- **Only `repo-tasks` manages its own third-party dependencies.** `python-dotenv` (already in live
  use via `bootstrap.sh`'s bolted-on `--with python-dotenv`) and anything added later become
  `repo-tasks`'s *own* `pyproject.toml` `dependencies`, not flags injected by an external installer.
  This decouples the dependency list from PULSE (or anything else) entirely.
- **Folding `invoke` into `repo-tasks` for a one-package install — real, with a hard requirement that
  must be verified, not assumed, before implementation starts.** The goal: `uv tool install --force
  'repo-tasks @ git+...'` alone, no `--with` flags, working end to end — **`uv tool install` must
  actually install the transitive dependency's own console-script binaries (`inv`/`invoke`) onto the
  tool's script path.** This is a hard requirement of the design, not a nice-to-have: if it doesn't
  hold, the whole one-package-install shape doesn't work and `repo-tasks` needs its own
  `[project.scripts]` entries mirroring `invoke`'s (mirroring exactly what — its real entry-point
  target — also unverified). `pipx` had precisely this limitation historically (`--include-deps` was
  a required, explicit opt-in to expose a dependency's own scripts, never implicit) — `uv tool
  install` needs the same behavior checked against a real install before this is relied on, not
  assumed to differ just because it's a different tool. **First implementation step, blocking
  everything else in this section**: run a real `uv tool install` of a package with a console-script
  dependency and check `which`/`ls` on the resulting script path directly — not documentation-reading,
  the same "verify with the real exit code / real command output" discipline already established
  elsewhere in this session.
- **A dedicated `repo-tasks` task namespace**, nested so it can never collide with a consuming
  project's own local task names — CLI shape settled: **`inv repo-tasks.update`**, not
  `.self.update` — `self` doesn't fit because `invoke` (`inv`), not `repo-tasks`, is the actual CLI
  entry point; `repo-tasks` is just a collection name inside it, so there's no "self" to refer to.
  Alongside `.status` (compares the globally-installed version against what the *current* repo
  expects — drift detection) and `.version` (prints what's active); a `.doctor` health check is a
  plausible later addition, not decided.
- **`inv configure` stamps a committed, regenerated-on-demand bootstrap script per repo**, recording
  the `repo-tasks` version active at the time `configure` last ran (introspected via
  `importlib.metadata.version("repo-tasks")` or equivalent — `bump-my-version` is already a
  `repo-tasks` dev dependency, so a real version string already exists to read). This script is
  **for CI and reproducibility archaeology, not routine local use** — a human working across
  multiple repos on one machine should run `repo-tasks.update` to move the shared global install
  forward, never re-run a specific repo's stamped script by habit, since that would silently
  reinstall the global tool to whatever *that* repo last pinned and yank it out from under whatever
  other repo was just being worked on. This asymmetry (CI: always the stamped script; humans:
  always `repo-tasks.update`) needs to be stated explicitly wherever this gets documented, or the
  design will get misused. Matches an already-established rule
  (`feedback_deliberate_regeneration_commit_artifacts` memory): regenerated artifacts get committed,
  and regenerated only by an explicit command (`configure`), never silently/automatically.
- **CI owns zero embedded bash.** Every CI step is either the repo's stamped bootstrap script (before
  `inv` exists) or a bare `inv <task>` (after) — single source of truth either way. Actual CI YAML
  shape is explicitly deferred (`we will build the CI later` — the user's own words), not designed
  here yet.
- **Whether the global daily-driver install itself should be version-pinned (a release tag, bumped
  deliberately) or track a moving ref (`main`, upgraded via `uv tool upgrade invoke` with no
  version-resolution logic of its own) turned out to be a much smaller decision than first
  assessed.** Original reasoning for pinning (avoid silent drift, reproducibility) doesn't actually
  hold once the stamped-script mechanism above exists — CI's reproducibility need is already served
  by that per-repo stamped script, which is version-pinned regardless of what the human-facing daily
  driver does, and updates to the daily driver are manual either way (never automatic), so "pin then
  bump manually" and "track main, only bump when confirmed good" are behaviorally almost identical.
  The one real remaining edge pinning still buys: legible version *labels* (`v1.4.2`) instead of raw
  git SHAs, for `.status`/`.version` output and for naming a rollback target — a UX nicety, not a
  safety mechanism. Leaning toward `repo-tasks.update` moving to the latest tagged release (not bare
  `main` HEAD) purely for that legibility, not because it's protecting against anything.
- **Zero-state bootstrap, resolved (2026-08-22) to be much smaller than first proposed.** Given the
  scope boundary above (`repo-tasks` never installs `uv`, only checks for it), `repo-tasks`'s entire
  "bootstrap" collapses to one command: `uv tool install --force 'repo-tasks @ git+...'`, run only
  after confirming `uv` is on `PATH`. That's small enough that a dedicated curl-pipeable `bootstrap.sh`
  may not be worth having at all — documenting the one-liner in `repo-tasks`'s own `README.md` is
  probably sufficient; a trivial 2-3-line wrapper script (check `uv` present, run the install, clear
  error otherwise) is the fallback if a documented one-liner turns out to be too easy to get wrong in
  practice. Either way, nothing about it resembles PULSE's `bootstrap.sh` in scope. Worth naming
  explicitly: since `repo-tasks` is a standard Python package with real entry points, other installers
  (`pipx install repo-tasks`, etc.) could technically work too — not worth building or documenting
  support for, since the whole point of this design is a `uv`-based, single-toolchain world; `pipx`
  compatibility is an incidental side effect of using standard packaging, not a target.
- **PULSE-side wrinkle, resolved (2026-08-22): should `bootstrap.sh` default to installing bare
  `invoke`, or `repo-tasks` (which brings `invoke` with it)?** Current behavior installs bare
  `invoke` only — sufficient for PULSE's own `tasks/`, which is deliberately stdlib-only and doesn't
  need `repo_tasks` at all (verified earlier in this doc). Resolved design:
  - **Default: install `repo-tasks`.** Most real users of this machine's tooling end up working
    across PULSE *and* other repos in the family sooner or later, so defaulting to the fuller install
    saves a second bootstrap step later.
  - **Interactive run**: prompt at the point `bootstrap.sh` would otherwise silently install
    `invoke`, explaining the implication in plain terms (this opts the machine into a shared,
    globally-updated tool that every repo in the family will use, not a per-repo pinned dependency;
    skippable if the user only wants PULSE's own machine setup) — default answer yes.
  - **Unattended run**: no dedicated env var. Read the choice from `setup.toml` (new key, section
    TBD — e.g. under a `[bootstrap]`-style table) as the persisted source of truth, same as every
    other install decision in PULSE already works; a CLI flag on `bootstrap.sh` is a reasonable
    one-off override for a single run without editing the file. A separate env var would just be a
    third mechanism for the same boolean — not worth adding on top of TOML + CLI flag.
  - **Mechanical note**: `bootstrap.sh` doesn't read `setup.toml` today — that's `inv setup`'s job,
    which doesn't exist yet at the point this decision needs to be made. Not a blocker (by the time
    the script reaches the invoke-install line, `uv` and a Python version are already guaranteed
    present, so a bare `python3 -c 'import tomllib; ...'` reads the key with zero new dependencies)
    but it is new responsibility for that script worth naming explicitly rather than assuming away.
  - **Key name, resolved**: `[bootstrap] install_repo_tasks = true` — a new small top-level table,
    deliberately separate from `[packages.*]` (that system only works once `inv` already exists to
    read it; this decision has to resolve before `inv` exists at all, so it can't reuse that
    machinery).
- **The "chicken and egg" this raises — resolved (2026-08-22) by the scope boundary above.** The
  worry: doesn't PULSE defaulting to installing `repo-tasks` recreate the dependency it's supposed to
  be shedding? No, once the two installers' scopes are genuinely separate:
  1. **PULSE's own contributor dev-loop** (developing this repo itself) doesn't need any of this
     global-tool machinery at all — PULSE is a "meta" repo with no app `src/` to mix task tooling
     into, the same category as `repo-tasks` and `scaffoldapy` themselves (established earlier in
     this doc). It keeps its current per-repo `.venv` (`uv sync` + `dependency-groups.dev`) dev loop
     entirely unchanged, independent of whatever `bootstrap.sh` does for end users.
  2. **`bootstrap.sh` optionally running `repo-tasks`'s one-line install for a fresh *end user*** is
     the same shape `bootstrap.sh` already has with `uv` itself — it calls an external, independently
     maintained installer as one orchestrated step, guarantees that installer's own precondition
     (`uv` present) itself, and never reaches into `repo-tasks`'s internals or vice versa. Composing
     an external installer isn't the same relationship as depending on `repo-tasks` for PULSE's own
     operation — the scope boundary above is exactly what keeps this non-circular instead of just
     asserting it is.
- **Hard design constraint, stated by the user directly and worth repeating verbatim in spirit**:
  none of this machinery may ever be something a normal user or a future agent working in a
  generated repo needs to understand to work normally. One bootstrap (or it's already present from a
  previous project) plus `inv <task>` must just work, with zero awareness of `uv tool install`,
  versions, stamped scripts, or any of the above — otherwise the entire point of building this
  family of tooling is defeated. Every design choice above should be checked against this before
  being finalized.

**Collapsed for the record — the four original candidates and the workspaces rule-out** (superseded
by the converged design above, kept so the reasoning that led here isn't lost):

### Original context (PULSE only, 2026-08-20)

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

- **Design fully converged as of 2026-08-22 — no remaining open design decisions in this thread.**
  What's left is exactly one blocking verification step, not a question: `uv tool install`'s
  dependency-script-exposure behavior must be checked against a real install before implementation
  proceeds past that point — see "Folding `invoke` into `repo-tasks`" above for what that check needs
  to do. Everything else in this thread (naming, scope boundaries, `setup.toml` key, zero-state
  bootstrap shape, the PULSE/`repo-tasks` circularity concern) is resolved above.
- **CI YAML shape** for consumer repos and for `repo-tasks` itself, once the above exists — explicitly
  deferred by the user ("we will build the CI later"), sequenced after PULSE/`repo-tasks` decoupling.
  Not an open question to resolve now, noted so it isn't forgotten.
- **Collapsed history — the four originally-considered mechanisms and the `uv` workspaces rule-out**,
  kept for the reasoning trail, superseded by the converged design above:
  1. **Status quo** — `repo-tasks`/`invoke` in `dependency-groups.dev`, one `uv sync`, one `.venv`.
     Simplest, zero new moving parts, but exactly the mixing this update is about — no structural
     boundary, relies on convention.
  2. **One global `uv tool install invoke --with 'repo-tasks @ git+...'`**, same shape as PULSE's own
     bootstrap, used everywhere. Genuinely isolated from every app's own venv, `inv <task>` "just
     works" with no per-repo setup — but a `uv tool install` is a single global environment: every
     consumer repo on the machine would be forced onto the *same* `repo-tasks` version at once, which
     breaks the per-repo pinning/reproducibility `uv.lock` currently gives each repo (a `repo-tasks`
     change could silently alter every repo's task behavior simultaneously, with no lockfile telling
     you it happened).
  3. **`uvx --from 'repo-tasks @ git+...@<pinned-ref>' inv <task>`** (or the equivalent
     `uv run --with ... --no-project inv`) per repo — real isolation *and* real per-repo pinning
     (the ref lives in the command, cached separately per unique spec by `uv`), but needs the pin to
     live somewhere per-repo (a checked-in wrapper script? a documented alias?) since `uvx` doesn't
     read the project's own `uv.lock` for `--from` package resolution — a new mechanism to design,
     not something `uv`/`scaffoldapy` currently provide out of the box.
  4. Some hybrid: `invoke` genuinely global (option 2, since `invoke` itself is the near-zero-dep
     "make" analog and versioning it globally is low-risk), but `repo-tasks` resolved per-repo via
     option 3's pinning — splits the "runner" from the "task library" the same way `make` (system)
     and a `Makefile` (project-pinned) are already split today.

  **Ruled out: `uv` workspaces.** Considered and rejected 2026-08-22 — verified via `uv sync --help`
  (`--package <PACKAGE>`: "The workspace's environment (`.venv`) is updated to reflect the subset of
  dependencies declared by the specified workspace member packages") that a workspace resolves to
  **one `.venv` at the workspace root**, always — `--package` only changes which subset of
  dependencies get synced *into that same venv*, it doesn't produce two environments that coexist.
  Splitting a consumer repo into an `app` member and a `tasks` member wouldn't isolate them; it would
  make every `inv <task>` and every app test run require its own `uv sync --package <x>` first,
  overwriting the shared venv each time — worse than today's single always-available venv, not
  better. Workspaces also require every member to live locally under one root, which would mean
  vendoring `repo-tasks` into each consumer repo instead of depending on it as a pinned git
  dependency — breaks the git-as-artifact-store distribution model documented in
  `contributing/mcp-skill-shipping.md`. Workspaces solve "one coherent environment for interdependent
  local packages," which is the opposite of what's needed here.
- **Where would the "uvx invoke as a fallback when the global tool is missing" idea actually get
  documented/exercised** — `contributing/mcp-skill-shipping.md` (per-repo dev loop) is one candidate,
  `bootstrap.sh`'s own docs another, since it applies to both PULSE's runtime lifecycle and any
  consumer repo. `[NEEDS CLARIFICATION]`
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

Rough, not prescriptive — the cross-repo isolation mechanism itself is fully converged (see
"Converged design" above); the only thing left there is the blocking `uv tool install` verification
step, not a design choice. Items below predate that thread, are still mostly PULSE-local, and are
unaffected either way:

0. **No-regret step, independent of the mechanism decision**: write the stdlib-only-tasks rule down
   now, since it's already true everywhere and costs nothing to state — a short paragraph in
   `contributing/repo-family-architecture.md` (or a new `contributing/*.md` if it grows past a
   paragraph) codifying "task modules are stdlib + `invoke` only; a new third-party import in a task
   module needs a specific justification, the same bar `python-dotenv` already cleared." Doing this
   now also gives the eventual isolation mechanism something concrete to enforce, rather than
   inventing the rule and the enforcement together later.
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
