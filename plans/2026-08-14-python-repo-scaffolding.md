# Standardizing scaffolding for personal Python agent-tool repos

## Context

A growing family of small, standalone repos — `olx-polite-mcp`, `emag-polite-mcp`,
`altex-polite-mcp`, `temu-polite-mcp`, `product-research-pipeline`, more expected — each independently reproduce the
same dev-tooling shape: a uv-managed `pyproject.toml` (hatchling build, ruff config,
`[project.scripts]` entry point), a `tasks.py` (invoke: `lint_check`/`apply`, `format_check`/
`apply`, `test`, `check`/`apply`/`fix`), `dprint.json`, and (for the MCP-shaped repos) a
`core/` + `sites/<key>/` adapter split. Right now this happens by hand-porting one repo's files
into the next, with no way to push a later improvement backward into repos already created.

Captured now, before it's forgotten, per explicit request — **not a committed build order.** This
plan only records the problem and a recommended shape; building either piece described below is a
separate future task.

**Concrete evidence the drift risk is real, not hypothetical:** `olx-polite-mcp/tasks.py` (the
most mature sibling repo) is an explicit, acknowledged port of `tasks/quality.py` in this repo —
its own docstring says "ported... see AGENTS.md's cross-repo notes" and its `AGENTS.md` spells out
"reusing conventions, not code, from that repo." The two files are ~50 lines each and have
_already_ diverged after a single port (`pytest` vs. `pytest tests/`). Multiply that across every
current and future sibling repo and silent drift is the default outcome, not an edge case.

## Problem framing: two different kinds of reuse, often conflated

1. **Structural scaffolding** — what files a brand-new repo starts with: `pyproject.toml`
   skeleton, `tasks.py`, `dprint.json`, `LICENSE`, `README.md` skeleton, package layout
   (`core/` + `sites/<key>/` for a multi-site MCP server like `olx-polite-mcp`; flatter for an
   orchestrator/skill repo like `product-research-pipeline`).
2. **Ongoing shared logic** — code whose _behavior_ should stay identical across repos and improve
   everywhere at once when a lesson is learned (the `dprint --config-discovery=ignore-descendants`
   gotcha, ruff rule selection, the `check`/`apply`/`fix` task graph shape). Today this is 100%
   copy-paste — there's no update path at all.

Solving only (1) — a one-time generator — doesn't solve (2): repos still drift the moment either
the template or an individual repo's `tasks.py` changes after the fact. The "keep improving that
structure as we incorporate learnings" half of the ask specifically needs (2), not just (1).

## Recommended approach: two complementary pieces

### A. Shared invoke-tasks package — solves ongoing drift

New, small repo (e.g. `pulse-dev-tasks` — naming caveat below), a real Python package exposing an
invoke `Collection` extracted verbatim from `tasks/quality.py` in this repo (already the proven
source of truth — `lint_check`/`lint_apply`/`format_check`/`format_apply`/`test`/`check`/`apply`/
`fix`). Distributed the same way `skills/mcp-skill-shipping` already teaches for MCP servers:
git-as-artifact-store, no PyPI —

```shell
uv add --dev git+https://github.com/TheodoreAD/pulse-dev-tasks
```

Each consumer repo's own `tasks.py` shrinks from a ~50-line copy to a thin re-export plus its own
repo-specific tasks:

```python
from invoke import Collection
from pulse_dev_tasks import quality

ns = Collection(quality, ...)  # + repo-specific tasks, same shape as this repo's tasks/__init__.py
```

A fix or improvement in the shared package reaches every repo on its next `uv sync`/version bump —
not a manual re-port. Mirrors this repo's own `tasks/` package (many small task modules), just
extracted one level up so it's importable instead of merely copyable.

### B. Repo template — solves one-time scaffolding (Copier, not Cookiecutter)

Recommend **Copier** over literal Cookiecutter: Copier supports `copier update` to apply template
changes to an _already-generated_ project (diffs against the template's own git history and
merges); Cookiecutter has no native update story (the closest bolt-on, `cruft`, is less actively
maintained). Given the explicit ask to keep improving the structure over time, the update path is
the deciding factor, not just initial generation quality.

New template repo (e.g. `python-agent-repo-template`), parameterized for at least the three shapes
already seen: **stateless MCP server** (`olx-polite-mcp`/`emag-polite-mcp`/`altex-polite-mcp`
shape — `core/` + `sites/<key>/`, fetch/parse/models split, `[project.scripts]` entry,
`tests/*/fixtures/` convention), **session-backed MCP server** (`temu-polite-mcp`'s shape — site
requires a logged-in account, so it drives a persistent, manually-authenticated Chrome instance
over CDP rather than a plain `requests`/per-call-`Playwright` fetch; different enough from the
stateless shape to need its own variant, not a bolt-on flag), and **orchestrator/skill** (flatter,
no site-adapter split, no fetch layer at all) — a Copier conditional on one answer, not three forks
to keep in sync.

Seeds: `pyproject.toml` skeleton (hatchling build, ruff block, dev-dependency on package A above),
`tasks.py` stub, `dprint.json`, `LICENSE`, a `README.md` "Installation" section shaped like
`olx-polite-mcp`'s/`temu-polite-mcp`'s (the `uv tool install` editable/git pattern documented in
`skills/mcp-skill-shipping` — independently arrived at in both repos' READMEs, good sign it's the
right default to template), and a call to `inv ai.init` for `AGENTS.md` — reuse what already works
there rather than re-templating it.

**`olx-polite-mcp` (stateless shape) and `temu-polite-mcp` (session-backed shape) are the two
reference implementations to extract the template from** — both mature, battle-tested repos, not
building from a blank guess.

### Retrofit path for existing repos

- `emag-polite-mcp`/`altex-polite-mcp` are still plan-only — apply the template once their
  implementation actually starts; no retrofit needed.
- `olx-polite-mcp` already has real code that will have diverged from any not-yet-built template —
  retrofitting it means `copier update` once the template exists (exactly the direction Copier's
  update mechanism is built for), not a manual re-diff by hand.

## Open questions to resolve before building

- **Naming**: `pulse-dev-tasks` ties the package to `power-user-linux-setup`'s "PULSE" branding
  even though it's consumed by unrelated repos with no runtime dependency on this one — probably
  wants a name that doesn't imply personal-machine-setup scope.
- Should the shared package eventually also carry MCP-specific reusable pieces (robots.txt guard,
  rate limiter, disk cache — currently `olx-polite-mcp/core/`) once a _second_ MCP repo needs them,
  or does that stay per-repo? `olx-polite-mcp`'s own `AGENTS.md` already applies exactly this
  restraint to its Playwright fetch path ("generalize... only once a second site actually needs
  it") — the same principle likely applies here.
- Sequencing: build the shared tasks package (§A) first — smaller, immediately useful, ~50 lines
  already proven and ready to extract — before investing in the heavier Copier template (§B), or
  do both together. §A has no dependency on §B and can land independently.

## Explicitly out of scope right now

No code changes accompany this plan. Next step, whenever picked back up, is a real planning
session for whichever piece comes first — most likely §A, given it's the smaller, lower-risk,
immediately-useful piece with a proven source already sitting in this repo's own `tasks/quality.py`.
