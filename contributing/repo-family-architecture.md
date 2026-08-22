# The `power-user-linux-setup`/`repo-tasks`/`scaffoldapy` split

Three repos this session's own work made real, not just designed: `power-user-linux-setup` (this
one), [`repo-tasks`](https://github.com/TheodoreAD/repo-tasks), and
[`scaffoldapy`](https://github.com/TheodoreAD/scaffoldapy). Reasoning about all three at once —
which one owns a given piece of shared work, and why — got hard enough to be worth writing down
once, durably, instead of re-deriving it per decision. See
`plans/2026-08-14-python-repo-scaffolding.md` §A/§B/§D/§F for the full decision history this page
distills.

## What each one actually owns

**`power-user-linux-setup`** — machine setup/bootstrap for an actual PULSE user: `./bootstrap.sh` +
`inv setup`, zero project dependencies at runtime by design (see
`plans/2026-08-20-runtime-dev-venv-split.md` — `tasks/__init__.py`'s `_import_repo_tasks_modules`
helper, which degrades to four `None`s when `repo_tasks` isn't importable, is the mechanism, not
decoration). This repo consumes `repo-tasks` for its own dev loop exactly like any other consumer —
`inv dev-env.setup`, `inv quality.precommit`, `inv configs.pull` — but that's a dev-only dependency,
invisible to a real PULSE user running `./bootstrap.sh`. `bootstrap.sh` itself defaults to
installing the shared `repo-tasks` global tool (not bare `invoke`) for that user's own machine —
composing `repo-tasks`'s own installer as one orchestrated step, the same relationship this script
already has with `uv` itself, never reaching into `repo-tasks`'s internals (see
`plans/2026-08-20-runtime-dev-venv-split.md` §2). Not itself a `scaffoldapy` template target — its
own layout (flat `tasks/`, not `src/`) predates that whole effort and isn't shaped like the sibling
repos `scaffoldapy` generates.

**`repo-tasks`** — anything a repo in this family does _repeatedly_, identically, forever: quality
tooling (`lint`/`format`/`type_check`/`test`), venv/dependency lifecycle (`venv`/`deps`), the
dev-loop bootstrap (`dev_env`), docs builds (`docs`), canonical tool config (`configs`), and its own
daily-driver global install lifecycle (`repo_tasks`, nested as `repo-tasks.*` — `update`/`status`/
`version`/`stamp`) — the last one added specifically so the shared task runner is a
`uv tool
install`, decoupled from any one consumer's dependency groups, the same way `make` is a
system utility and not a per-project dependency of the `Makefile` it runs
(`plans/2026-08-20-runtime-dev-venv-split.md` §1). `configs` exists because a fix to
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
installer flag — see `plans/2026-08-20-runtime-dev-venv-split.md` §1), is the deliberate kind:
small, generic, and it earns its place. A new third-party import in a task module needs the same bar
cleared explicitly, not silently assumed because the package happens to be resolvable.

**`scaffoldapy`** — anything generated _once_ and then hand-maintained per repo, diverging
immediately and legitimately: project structure, the `pyproject.toml` skeleton, `AGENTS.md`/
`CLAUDE.md`/`.agents/skills` (real symlinks, via Copier's `_preserve_symlinks`, not a runtime task —
see §F), `mkdocs.yml` when `with_docs` is set. Copier-driven, `_tasks` limited to exactly two lines
(`uv sync`, `uv run inv configure`) — the universal bootstrap every `uv`-managed project needs, plus
the one stable `repo-tasks` entrypoint. Nothing else about `repo-tasks`' internals is named in this
template, on purpose.

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

## `configs.local.toml`: designed, not built

`repo-tasks`' `configs.pull` overwrites the 5 config files unconditionally — no per-repo exception
mechanism exists today, deliberately: every local exception found while designing this (two in
`power-user-linux-setup`, believed genuine at the time) turned out to be either avoidable by
construction (the `include`-list fix above) or simply never verified in the first place (a
`dprint.json` exclude that turned out to change nothing when actually tested — removed outright). A
`configs.local.toml` append-only mechanism is still designed on spec for a real future case, but
nothing in the family needs it right now — see §D for the shape if one ever does.
