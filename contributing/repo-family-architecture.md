# The `power-user-linux-setup`/`repo-tasks`/`scaffoldapy` split

Three repos this session's own work made real, not just designed: `power-user-linux-setup` (this
one), [`repo-tasks`](https://github.com/TheodoreAD/repo-tasks), and
[`scaffoldapy`](https://github.com/TheodoreAD/scaffoldapy). Reasoning about all three at once —
which one owns a given piece of shared work, and why — got hard enough to be worth writing down
once, durably, instead of re-deriving it per decision. Distilled from the now-retired
`plans/2026-08-14-python-repo-scaffolding.md`; the reasoning behind the _content_ of the shared
config files is [`quality-tooling.md`](quality-tooling.md).

## What each one actually owns

**`power-user-linux-setup`** — machine setup/bootstrap for an actual PULSE user: `./bootstrap.sh` +
`inv setup`, zero project dependencies at runtime by design (`tasks/__init__.py`'s
`_import_repo_tasks_modules` helper, which degrades to four `None`s when `repo_tasks` isn't
importable, is the mechanism, not decoration — see "The runtime/dev-venv split" below). This repo
consumes `repo-tasks` for its own dev loop exactly like any other consumer — `inv dev-env.setup`,
`inv quality.precommit`, `inv configs.pull` — but that's a dev-only dependency, invisible to a real
PULSE user running `./bootstrap.sh`. `bootstrap.sh` itself defaults to installing the shared
`repo-tasks` global tool (not bare `invoke`) for that user's own machine — composing `repo-tasks`'s
own installer as one orchestrated step, the same relationship this script already has with `uv`
itself, never reaching into `repo-tasks`'s internals (see "Two installers, two scopes" below). Not
itself a `scaffoldapy` template target — its own layout (flat `tasks/`, not `src/`) predates that
whole effort and isn't shaped like the sibling repos `scaffoldapy` generates.

**`repo-tasks`** — anything a repo in this family does _repeatedly_, identically, forever: quality
tooling (`lint`/`format`/`type_check`/`test`), venv/dependency lifecycle (`venv`/`deps`), the
dev-loop bootstrap (`dev_env`), docs builds (`docs`), canonical tool config (`configs`), and its own
daily-driver global install lifecycle (`repo_tasks`, nested as `repo-tasks.*` — `update`/`status`/
`version`/`stamp`) — the last one added specifically so the shared task runner is a
`uv tool
install`, decoupled from any one consumer's dependency groups, the same way `make` is a
system utility and not a per-project dependency of the `Makefile` it runs (see "The global
daily-driver install" below). `configs` exists because a fix to
`ruff.toml`/`pyrightconfig.json`/`dprint.json`/`pytest.ini`/ `.editorconfig` needs to reach every
consumer without three repos' worth of hand-copying and silent drift. Distributed as a pinned git
dependency for a repo that wants its own locked version (no PyPI — see `repo-tasks/README.md`,
synced deliberately via `uv lock --upgrade-package repo-tasks`, `inv configs.pull`, never
automatically) — or, the recommended default, a single global `uv tool install` every repo in the
family shares, moved forward by `inv repo-tasks.update` rather than a per-repo lockfile bump.
`inv
configure` is the one command anything outside this package should ever need to name by value —
it composes `dev_env.setup` + `configs.pull` + `repo_tasks.stamp` internally, and that composition
is free to change without anything outside `repo-tasks` (a `scaffoldapy` `_tasks` hook, a human)
noticing.

### Task modules are stdlib + `invoke` only

Every `repo_tasks` module and every PULSE `tasks/*.py` module imports stdlib plus `invoke` only —
verified by inspection across the whole family, zero exceptions. A task module is infrastructure
that operates _on_ a project, the same way a `Makefile` target isn't coupled to whatever libraries
the app it builds happens to link — nothing here should import an app-specific dependency (a web
framework, a scraping library, ...) just because it happens to be sitting in the same `.venv`. The
one third-party exception today, `python-dotenv` (a real `repo-tasks` dependency, not a bolted-on
installer flag — only `repo-tasks` manages its own third-party dependencies, never an external
installer injecting `--with` flags), is the deliberate kind: small, generic, and it earns its place.
A new third-party import in a task module needs the same bar cleared explicitly, not silently
assumed because the package happens to be resolvable.

**`scaffoldapy`** — anything generated _once_ and then hand-maintained per repo, diverging
immediately and legitimately: project structure, the `pyproject.toml` skeleton, `AGENTS.md`/
`CLAUDE.md`/`.agents/skills` (real symlinks, via Copier's `_preserve_symlinks`, not a runtime task —
see §F), `mkdocs.yml` when `with_docs` is set. Copier-driven, `_tasks` is three bare `inv`/
`repo-tasks` calls, never `uv run`/a raw `uv` subcommand: `repo-tasks configs.ensure-deps`
(populates the generated `dependency-groups.dev` — deliberately empty in the template itself — from
`repo-tasks`' own canonical `dependency-groups.quality`), `inv deps.lock`, then `inv configure`.
Neither `repo-tasks` nor `invoke` is ever a project dependency of a generated repo at all (see
"Quality tools vs. public-API deps" below) — both `_tasks` and the generated CI workflow assume the
global `uv tool install`ed daily-driver is already on PATH, the same assumption
`power-user-linux-setup`'s own `bootstrap.sh` makes real. Nothing else about `repo-tasks`' internals
is named in this template, on purpose.

### Quality tools vs. public-API deps: which dependency list a thing belongs in

`repo-tasks`' own `pyproject.toml` splits three ways, and the split is the actual design, not an
implementation detail:

- **`[project.dependencies]`** (main deps — inherited transitively by anything depending on
  `repo-tasks`, and pulled into the global `uv tool install` too): `invoke`, `python-dotenv`,
  `bump-my-version`. The test: does a repo need this just by depending on `repo-tasks` at all, or by
  having the global tool installed? `bump-my-version` is here because `version.py`'s public `bump`
  task (and `gitflow.py`'s release/hotfix flows) shell out to it — any consumer running
  `inv
  version.bump` needs it resolvable, not just `repo-tasks`' own dev loop.
- **`dependency-groups.quality`** (basedpyright/pytest/ruff/shellcheck-py/shfmt-py/dprint-py) — the
  test: does a repo need this only if it opts into `repo-tasks`' quality gates. Never a main
  dependency or an installable extra — either would leak these into the global tool venv, which
  should stay exactly the three main deps above, nothing quality-tool-shaped. **Getting these into a
  _consumer's_ own `dependency-groups.dev` isn't automatic** — PEP 735 dependency-groups are
  per-project, never inherited transitively through a regular dependency (confirmed real: adding a
  tool to `repo-tasks`' own group did nothing for `power-user-linux-setup`'s `.venv` until its own
  `pyproject.toml` was updated too) — `inv configs.ensure-deps` is the mechanism: reads
  `repo-tasks`' own `dependency-groups.quality` (force-included as package data) and additively
  patches a consumer's `pyproject.toml`, never touching an entry already present.
  `power-user-linux-setup` and `repo-tasks` itself are the one deliberate exception to "never add
  `repo-tasks`/`invoke` to a consumer" — they keep both by hand in their own dev groups because
  their own test suites exercise real `repo_tasks` integration (e.g. `tasks/__init__.py`'s
  degrade-to-`None` path), not just consume its tasks.
- **`bump-my-version`'s own transitive weight** (rich-click, questionary, pydantic, ...) lands in
  the global tool venv now too, same as any main dependency — accepted deliberately, it's a small,
  single-purpose CLI wrapper, not a quality tool.

**A related uv/packaging trap, worth remembering for any future tool-install work, not just this
family**: `uv tool install --with-executables-from <dep> <pkg>` only _adds_ console-scripts from
`<dep>` on top of whatever `<pkg>` already exposes — it does not substitute for `<pkg>` having at
least one entry point of its own. `repo-tasks` had zero `[project.scripts]` and failed to install as
a tool ("No executables are provided by package `repo-tasks`") even with
`--with-executables-from invoke` supplying `inv`/`invoke` — confirmed against the real package, not
a hypothetical (the original design was only ever verified against a throwaway fixture). Fixed with
`src/repo_tasks/cli.py`'s own `[project.scripts] repo-tasks = "repo_tasks.cli:program.run"`, which
also solves a second, unrelated gap: bare `inv <task>` needs a `tasks.py`/`tasks/` in the current
directory to find any collection at all — there's no way to point it at an arbitrary installed
package's submodule — so the standalone `repo-tasks` script is also how `configs.ensure-deps` stays
reachable in a directory with nothing invoke-related in it yet.

## The test that actually settles it

When new shared work comes up, ask: **would this need to run again after the first time, identically
everywhere?**

- Yes → `repo-tasks`. A synced task, not a stamped file.
- No — written once, then diverges per repo by design → `scaffoldapy`. A structural template, not a
  task.
- Neither — it's this one machine's own state (a real user's dotfiles, installed packages, desktop
  config) → `power-user-linux-setup`.

Two things that look like they could go either way, resolved by this test directly (both hit for
real, not hypothetically):

- `AGENTS.md`/`CLAUDE.md`/`.agents/skills` — tempting to think of as "config," but it's written once
  and then hand-edited per repo forever; nothing about it should be silently overwritten by a later
  sync the way `ruff.toml` should be. `scaffoldapy`, not `repo-tasks` (§F).
- `pyrightconfig.json`'s `include` list — looked at first like it needed to differ per repo (`src`/
  `tests` for a `src`-layout consumer vs. `tasks`/`tests` for this repo's flat layout), which would
  have meant it _couldn't_ be a single synced file. **First conclusion — that `basedpyright`
  silently no-ops on a nonexistent `include` entry, so one static
  `["src", "tests", "tasks", "tasks.py"]` list just works everywhere — was wrong, and shipped broken
  for a while before being caught.** Real behavior: `basedpyright` hard-errors (exit 3, a config
  error) on any `include` entry that isn't a real path — the opposite of `exclude`, which does
  tolerate missing ones. That silently aborted `inv quality.precommit` right after `type_check`,
  before `shell_check`/`test` ever ran, in every repo missing one or more of the four candidates —
  caught only once a later check verified the actual process exit code directly instead of
  eyeballing "0 errors, N warnings" text piped through `tail`. Fixed in
  `configs.pull`/`configs.diff` themselves: filter the canonical `include` list down to whichever
  candidates actually exist at the pull target before writing, so the single declarative source of
  truth survives without every consumer hand-tuning its own subset — the original goal, just
  implemented one level down (a materialization-time filter, not a static value) instead of assumed
  to already work for free. **The lesson that actually generalizes: re-testing an assumption
  empirically means checking the real exit code, not scanning text output for the word "error" — a
  tool can print a clean summary and still exit nonzero.**

## The runtime/dev-venv split

Extracted from the now-retired `plans/2026-08-20-runtime-dev-venv-split.md` (landed 2026-08-23).

PULSE has two lifecycles by design. **Dev** (contributing to this repo): `inv dev-env.setup` →
`uv sync` + `direnv allow`, then `inv quality.precommit`/`pytest` like every other repo in the
family. **Runtime** (a PULSE user setting up a machine): `./bootstrap.sh` installs `uv`, a Python,
and the task runner as an isolated `uv tool` — never `uv sync`, never this repo's dependency groups.
`inv <task>` works from the repo root because invoke walks up from cwd and imports `tasks/` off the
filesystem; `[project] dependencies = []` codifies that the package has zero runtime deps, every
machine-setup task shelling out to OS tools. The one place dev-only tooling could leak into the
runtime import graph is `tasks/__init__.py`'s `repo_tasks` import, which is why that import lives in
`_import_repo_tasks_modules(simulate_missing=False)`: a `simulate_missing` flag exercises the
degraded branch directly in `tests/unit/test_tasks_init.py`, rather than `importlib.import_module`
injection (which loses pyright's static module typing on the success path — `Any` leaking into
`Collection.from_module()`) or `sys.modules` patching.

CI guards the invariant with a `runtime-guardrail` job that mirrors `bootstrap.sh`'s `--invoke-only`
shape — bare `uv tool install invoke` (never `uv sync`), `inv --list`, then the `PULSE_DRY_RUN=1`
smoke command from `docs/index.md`. It guards the actually-verified invariant (bare invoke with no
`repo_tasks` at all still gets a working `inv --list`), not the now-default `--repo-tasks` path,
which the `quality` job already exercises through a real `uv sync`. `docker/Dockerfile`'s full build
stays a separate, manual, heavier check — deliberately not promoted into CI.

### Two installers, two scopes

`repo-tasks` owns its own install/update lifecycle entirely, with a hard boundary: its installer
only ever touches its own isolated `uv tool` venv — never installs `uv` itself, never touches shell
rc files, never installs any other user-wide tool. If `uv` is missing it fails with a clear pointer
at installing `uv` rather than bootstrapping it. PULSE, conversely, always installs `uv`
unconditionally — never gated behind the repo-tasks-vs-bare-invoke choice. The moment one installer
starts doing a bit of the other's job "for convenience", the mental model stops being simple enough
to hold in your head.

That boundary is also what dissolves the apparent chicken-and-egg of PULSE's `bootstrap.sh`
defaulting to install `repo-tasks`: PULSE's own contributor dev loop never needs the global-tool
machinery (it is a "meta" repo with no app `src/` to mix task tooling into, same category as
`repo-tasks` and `scaffoldapy`), and calling an independently maintained installer as one
orchestrated step — guaranteeing its precondition, never reaching into its internals — is the same
relationship `bootstrap.sh` already has with `uv`, not a dependency on `repo-tasks` for PULSE's own
operation. The unattended default is `setup.toml`'s `[settings] install_repo_tasks` (an existing
top-level table `bootstrap.sh` already greps for the `uv_python_*` keys — not a separate
`[bootstrap]` table, and not an env var, which would be a third mechanism for the same boolean); an
interactive run is asked; `--repo-tasks`/`--invoke-only` override either for one run.

### The global daily-driver install

`inv repo-tasks.update`/`.status`/`.version`/`.stamp` (nested so it can never collide with a
consumer's own task names; `inv`, not `repo-tasks`, is the CLI entry point, so there is no "self" to
name). Design points that were argued, not assumed:

- **CI uses the stamped script; humans use `repo-tasks.update`.** `inv configure` stamps a committed
  `bootstrap-repo-tasks.sh` per repo recording the `repo-tasks` version active when it last ran —
  for CI and reproducibility archaeology, not routine local use. Re-running a specific repo's
  stamped script by habit would reinstall the global tool to whatever _that_ repo last pinned,
  yanking it out from under whichever other repo was just being worked on. State this asymmetry
  wherever it is documented.
- **No version pinning of the global install.** Pinning's reasons (avoid silent drift,
  reproducibility) are already served by the per-repo stamped script, and updates to the daily
  driver are manual either way, so "pin then bump" and "track latest, bump when confirmed good" are
  behaviorally almost identical. `repo-tasks.update` moves to the latest tagged release rather than
  bare `main` purely for legible version _labels_ in `.status`/`.version` output and rollback
  targets — a UX nicety, not a safety mechanism.
- **CI owns zero embedded bash.** Every CI step is either the repo's stamped bootstrap script
  (before `inv` exists) or a bare `inv <task>` (after). Both PULSE's and `repo-tasks`' workflows
  collapse to `setup-uv` + one bootstrap script + `inv quality.check`.
- **The hard constraint over all of it** (stated by the user): none of this machinery may be
  something a normal user or a future agent working in a generated repo needs to understand to work
  normally. One bootstrap (or it's already present) plus `inv <task>` must just work, with zero
  awareness of `uv tool install`, versions, or stamped scripts — otherwise the point of the family
  is defeated.

### Rejected: `uv` workspaces, and three other shapes

For the consumer-repo gap (`repo-tasks` + `invoke` sitting in the same `dependency-groups.dev` as an
app's own runtime deps, with nothing structural stopping a task module from importing `httpx`
because it happens to be there), four mechanisms were weighed: the status quo; one global
`uv tool install invoke --with 'repo-tasks @ git+...'` (isolated, but forces every consumer onto one
`repo-tasks` version at once — resolved later by the stamped script giving per-repo pinning back);
`uvx --from 'repo-tasks @ git+...@<ref>' inv <task>` per repo (real isolation, but the pin has to
live somewhere per-repo that `uv`/`scaffoldapy` don't provide); and a hybrid with `invoke` global
and `repo-tasks` resolved per-repo. The global-tool shape won once the stamped script existed.

`uv` workspaces were ruled out on evidence, not taste: `uv sync --help` documents that
`--package <PACKAGE>` updates "the workspace's environment (`.venv`)" — one venv at the workspace
root, always; `--package` only changes which subset gets synced _into that same venv_. Splitting a
consumer into an `app` member and a `tasks` member would not isolate them, and every `inv <task>`
and app test run would need its own `uv sync --package` first, overwriting the shared venv each
time. Workspaces also require every member under one local root, which would mean vendoring
`repo-tasks` into each consumer and breaking the git-as-artifact-store distribution
(`contributing/mcp-skill-shipping.md`). They solve "one coherent environment for interdependent
local packages" — the opposite of what was needed.

## `configs.local.toml`: designed, not built

`repo-tasks`' `configs.pull` overwrites the 5 config files unconditionally — no per-repo exception
mechanism exists today, deliberately: every local exception found while designing this (two in
`power-user-linux-setup`, believed genuine at the time) turned out to be either avoidable by
construction (the `include`-list fix above) or simply never verified in the first place (a
`dprint.json` exclude that turned out to change nothing when actually tested — removed outright). A
`configs.local.toml` append-only mechanism is still designed on spec for a real future case, but
nothing in the family needs it right now.

The shape, if one ever appears — deliberately dumb, no per-repo `select`/`extends`/deep-merge. A
single tracked `configs.local.toml` at the consumer's root, present only in repos that need one.
Additive-only, list-append per target file and key, with each entry's _why_ required inline as a
TOML comment, since the exception cannot always carry a comment in the generated file itself
(`dprint.json` is plain JSON with no comment syntax; `pyrightconfig.json` is JSONC and could, but
shouldn't be the only place the reasoning lives):

```toml
# illustrative shape only — no live case exists.
[ruff."lint".exclude]
append = ["some/repo/specific/generated/path"]
```

`configs.pull` would read the file if present and append each entry onto the corresponding list in
the pulled base before writing. No scalar overrides, no arbitrary deep merge. Build it when a real
case appears, not preemptively against a hypothetical one — the two exceptions that originally
motivated it both dissolved on inspection, one absorbed into the shared `include` list and the other
removed outright once testing showed it changed nothing.

Note that `repo-tasks`' own root config files are **not** generated output kept identical to
`src/repo_tasks/configs/*`. It is a normal Python project whose root files govern its own dev loop,
and they are allowed to diverge in flight; `configs.promote` is the deliberate one-directional
action that makes the current root files the new canonical baseline once the maintainer decides that
tuning is ready to ship.
