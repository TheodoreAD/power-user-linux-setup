---
status: in-progress
updated: 2026-08-19
---

# Standardizing scaffolding for personal Python agent-tool repos

## Context

A growing family of small, standalone repos — `olx-polite-mcp`, `emag-polite-mcp`,
`altex-polite-mcp`, `temu-polite-mcp`, `product-research-pipeline`, more expected — each
independently reproduce the same dev-tooling shape: a uv-managed `pyproject.toml` (hatchling build,
ruff config, `[project.scripts]` entry point), a `tasks.py` (invoke: `lint_check`/`apply`,
`format_check`/ `apply`, `test`, `check`/`apply`/`fix`), `dprint.json`, and (for the MCP-shaped
repos) a `core/` + `sites/<key>/` adapter split. Right now this happens by hand-porting one repo's
files into the next, with no way to push a later improvement backward into repos already created.

Captured now, before it's forgotten, per explicit request — **not a committed build order.** This
plan only records the problem and a recommended shape; building either piece described below is a
separate future task.

**Concrete evidence the drift risk is real, not hypothetical:** `olx-polite-mcp/tasks.py` (the most
mature sibling repo) is an explicit, acknowledged port of `tasks/quality.py` in this repo — its own
docstring says "ported... see AGENTS.md's cross-repo notes" and its `AGENTS.md` spells out "reusing
conventions, not code, from that repo." The two files are ~50 lines each and have _already_ diverged
after a single port (`pytest` vs. `pytest tests/`). Multiply that across every current and future
sibling repo and silent drift is the default outcome, not an edge case.

**This plan absorbed the quality-tooling half of `plans/2026-08-15-python-conventions.md`
(2026-08-17).** That plan originally covered both design/style guidance (data modeling, settings,
control flow, architecture — a `python-conventions` skill's job, read continuously while writing
code) and tool _choice and config_ (basedpyright, ruff, shellcheck/shfmt, dprint — applied once at
repo setup). The user asked for these to split along that consumption-pattern line rather than stay
one plan; the config half moved here, since "apply config once at setup" is exactly what §A/§B below
already exist to do — see "Quality-tooling conventions" below for the concrete, researched
decisions, already piloted directly on `power-user-linux-setup` itself (commit `c01b53c`,
2026-08-16/17) before being written up as something §A/§B would hand to other repos.

## Problem framing: two different kinds of reuse, often conflated

1. **Structural scaffolding** — what files a brand-new repo starts with: `pyproject.toml` skeleton,
   `tasks.py`, `dprint.json`, `LICENSE`, `README.md` skeleton, package layout (`core/` +
   `sites/<key>/` for a multi-site MCP server like `olx-polite-mcp`; flatter for an
   orchestrator/skill repo like `product-research-pipeline`).
2. **Ongoing shared logic** — code whose _behavior_ should stay identical across repos and improve
   everywhere at once when a lesson is learned (the `dprint --config-discovery=ignore-descendants`
   gotcha, ruff rule selection, the `check`/`apply`/`fix` task graph shape). Today this is 100%
   copy-paste — there's no update path at all.

Solving only (1) — a one-time generator — doesn't solve (2): repos still drift the moment either the
template or an individual repo's `tasks.py` changes after the fact. The "keep improving that
structure as we incorporate learnings" half of the ask specifically needs (2), not just (1).

## Recommended approach: two complementary pieces

### A. Shared invoke-tasks package — solves ongoing drift

**Design resolved 2026-08-18** (naming and composition were open questions as of the previous
revision — both settled this session, including one substantial correction: an earlier draft that
proposed leaf-tasks-only, each repo composing its own `check`/`apply`/`fix`, was rejected by the
user directly — **no per-repo allowances. Every consumer repo uses the exact same composite tasks
from the shared package, unmodified.**). New, small repo **`repo-tasks`** (`pulse-dev-tasks`
rejected — clashes with PulseAudio; `py-dev-tasks` rejected — too generic; a `taudelta`/`td`-branded
option considered and passed over), `src/` layout (see `skills/python-conventions`'s new "Package
layout" topic), cloned locally to `~/projects/github.com-personal/repo-tasks`:

```
repo-tasks/
  pyproject.toml            # hatchling, dependencies = ["invoke"], packages = ["src/repo_tasks"]
  ruff.toml                 # dedicated file, not [tool.ruff] in pyproject.toml — see §C0
  pyrightconfig.json        # dedicated file, not [tool.basedpyright]
  pytest.ini                # dedicated file, not [tool.pytest.ini_options]
  dprint.json                # already a dedicated file today, unchanged
  src/repo_tasks/
    __init__.py
    quality.py               # extracted from tasks/quality.py, see below
  tests/
    test_quality.py
```

A real Python package exposing an invoke `Collection` extracted from `tasks/quality.py` in this repo
(already the proven source), but with three renamed/added composite tasks — **`fix`** (auto-fix only
— renamed from this repo's current `apply`, revised 2026-08-18: "apply" read fine for solo use, but
"fix" is the name people sharing this package will already expect), `check` (CI gate, unchanged),
and **`precommit`** (`fix` then `check`, replacing what this repo currently calls `fix` for the
combo task) — **`precommit` is the one command an agent always runs, without needing to know or
invoke the individual tools itself.** Every `c.run(...)` call echoes the command it runs
(`echo=True`) so both a human and an agent see exactly what executed — the only exception would be a
step involving a secret, and none of the quality tasks do. Because `type_check`/`shell_check` are
now unconditional parts of every consumer's `check` (no allowances to skip them),
`shell_check`/`shell_format_*` must degrade gracefully on a repo with zero `*.sh` files (confirmed:
none of `olx`/`temu`/`freshful-polite-mcp` has any) rather than erroring the way
`shellcheck $(fd -e sh .)` does today on an empty file list — and every consumer repo must carry its
own `pyrightconfig.json` (§C0), since "every repo runs type_check" only works if "every repo has
type-check config" also holds. **Every task, leaf and composite alike, carries a succinct one-line
docstring** — this is what `inv -l` displays as that task's help text in a consumer repo, so
`inv -l` alone should be enough to know what's available without reading source (revised 2026-08-18,
per explicit request):

```python
"""Shared, reproducible quality-tooling invoke tasks. Every command is echoed
(echo=True) so both a human and an agent see exactly what ran — the only
exception is a step that would involve a secret, and none here do."""

from invoke import task


def _sh_files(c):
    result = c.run("fd -e sh .", hide=True, warn=True)
    return result.stdout.split() if result.ok else []


@task
def lint_check(c):
    """Run ruff's linter (no fixes)."""
    c.run("ruff check .", echo=True)


@task
def lint_apply(c):
    """Run ruff's linter and apply auto-fixes."""
    c.run("ruff check --fix .", echo=True)


@task
def format_check(c):
    """Check formatting (ruff format, dprint) without writing changes."""
    c.run("ruff format --check .", echo=True)
    c.run("dprint check --config-discovery=ignore-descendants", echo=True)


@task
def format_apply(c):
    """Apply formatting: ruff format, then dprint fmt."""
    c.run("ruff format .", echo=True)
    c.run("dprint fmt --config-discovery=ignore-descendants", echo=True)


@task
def type_check(c):
    """Run basedpyright's type checker."""
    c.run("basedpyright", echo=True)


@task
def shell_check(c):
    """Run shellcheck against every *.sh file in the repo.

    No-ops cleanly on a repo with no shell scripts, so this is safe to run
    unconditionally in every consumer's `check` — no per-repo opt-out needed.
    """
    files = _sh_files(c)
    if files:
        c.run(f"shellcheck {' '.join(files)}", echo=True)


@task
def shell_format_check(c):
    """Check shell script formatting (shfmt) without writing changes. No-ops
    cleanly on a repo with no shell scripts."""
    files = _sh_files(c)
    if files:
        c.run(f"shfmt -d {' '.join(files)}", echo=True)


@task
def shell_format_apply(c):
    """Apply shell script formatting (shfmt). No-ops cleanly on a repo with
    no shell scripts."""
    files = _sh_files(c)
    if files:
        c.run(f"shfmt -w {' '.join(files)}", echo=True)


@task
def test(c):
    """Run the pytest suite."""
    c.run("pytest", echo=True)


@task(pre=[lint_apply, format_apply, shell_format_apply])
def fix(c):
    """Fix everything auto-fixable: ruff --fix, ruff format, dprint fmt, shfmt -w."""


@task(pre=[lint_check, format_check, type_check, shell_check, test])
def check(c):
    """CI-style gate: every check, no changes written."""


@task(pre=[fix, check])
def precommit(c):
    """Fix, then check — the one command to run before considering a change
    done, with no need to know or invoke the individual tools."""
```

`shfmt`'s indent style (hardcoded before this as `-i 4 -ci` in `tasks/quality.py`) moved to
`.editorconfig` instead of a flag — `shfmt` reads `.editorconfig` natively, fitting §C0's "each tool
owns its own config file" principle better than a flag baked into the shared task. **Resolved
2026-08-19, researched rather than just kept as-is**: 2-space indent (not the old 4), matching
shfmt's own README-recommended "Google Shell Style" tip and the dominant real-world convention
(`fzf`, `Shopify/toxiproxy`, 1,400+ other GitHub repos with `switch_case_indent` set) —
`switch_case_indent = true` and `space_redirects = true` are near-unanimous among projects that
configure this at all, so both are on; `binary_next_line`/`keep_padding`/`function_next_line`/
`simplify` are genuine taste calls with no dominant convention, left off but present as commented
toggles for easy per-preference use. Landed in both `power-user-linux-setup`'s own `.editorconfig`
and `repo-tasks`'s (the file to actually copy from, per §C's redirect above). Distributed the same
way `skills/mcp-skill-shipping` already teaches for MCP servers — git-as-artifact-store, no PyPI —
but via `uv add`, not `uv tool install`, since this is a library, not an executable:

```shell
uv add --dev git+https://github.com/TheodoreAD/repo-tasks
```

Each consumer repo's own `tasks.py` shrinks to exactly this, with **no local override**:

```python
from invoke import Collection
from repo_tasks import quality

ns = Collection.from_module(quality)
```

**Every task above — leaf and composite alike — is a plain public function in the `quality` module,
not just the three composites.** `from repo_tasks import quality; quality.test` works directly at
the Python level, and `Collection.from_module(quality)` surfaces every one of them individually
under `inv quality.<name>` in a consumer repo: `inv quality.test` (pytest alone),
`inv quality.lint_check`, `inv quality.type_check`, etc. all remain fully supported entrypoints on
their own — `precommit` is the recommended default for "run everything, I don't want to think about
which tools," not the only supported one (revised 2026-08-18, per explicit request — `test`/pytest
specifically called out as a command people will often want standalone). `inv quality.precommit` is
the single command, identical across every repo, for the common case — matching the pattern already
proven in this repo's own `tasks/__init__.py`'s `Collection.from_module(quality)` usage, not a
guessed shape. A fix or improvement in the shared package reaches a consumer only via a deliberate
`uv lock --upgrade-package repo-tasks` (or a pinned `@<tag>` bump) plus a committed lockfile change
— not automatic, same as any other dependency bump.

**Tested via invoke's own `MockContext`** (`from invoke import MockContext, Result`), asserting the
right command string is built per task, plus dedicated tests for `_sh_files`'s empty-vs-nonempty
behavior specifically — the one piece of real logic, and exactly what makes the mandatory composite
safe to run unconditionally.

**Required follow-ups this design does not itself execute** (per "no allowances," every one of these
is required eventually, not optional — sequenced out because each is a real migration of
already-relied-upon tooling, not because the convention doesn't apply to it):

- ~~This repo's own `tasks/quality.py`: rename its current `apply` → `fix` and current `fix` →
  `precommit`~~ — **done 2026-08-19** (`af86f6a`), plus `AGENTS.md`/`CONTRIBUTING.md` wording.
- ~~This repo's own `pyproject.toml`: migrate `[tool.ruff]`/`[tool.basedpyright]`/
  `[tool.pytest.ini_options]` into dedicated files per §C0~~ — **done 2026-08-19** (`af86f6a`):
  `ruff.toml`/`pyrightconfig.json`/`pytest.ini`, content unchanged, verified empirically that
  basedpyright accepts JSONC comments in `pyrightconfig.json` before relying on it.
- ~~This repo's own `tasks/` package: migrate to `src/tasks/` layout~~ — **struck 2026-08-19, was
  wrong.** This repo's `tasks/` is the canonical per-repo invoke-tasks directory every repo in this
  family has (repo-specific tasks, never installed/imported elsewhere), the exact same role a
  consumer's own `tasks.py` plays in §A/§3 above — src-layout was never meant to reach it, it
  governs distributable packages only (the future `repo-tasks` extraction, e.g.). Attempted live and
  caught before landing: moving `tasks/` under `src/` also collides with invoke's own
  `FilesystemLoader` (walks upward from cwd for a literal `tasks.py`/`tasks/__init__.py`, never
  consults an installed copy) — `inv` would have nothing to find.
  `skills/python-conventions/SKILL.md`'s src-layout topic updated same day to state this scoping
  explicitly, so a sibling-repo retrofit doesn't repeat it.
- ~~Whether this repo becomes an actual consumer of `repo-tasks`~~ — **done 2026-08-19** (`6a9c981`):
  `uv add --dev git+https://github.com/TheodoreAD/repo-tasks`, `tasks/__init__.py` now does
  `from repo_tasks import quality`, no local `tasks/quality.py` duplicate remains. See §D for the
  config-file half of this same question (still open as of that commit — resolved below).
- **Still open**: retrofitting `olx-polite-mcp`/`temu-polite-mcp`/`freshful-polite-mcp` onto
  `repo-tasks` + `src/` layout, now unblocked since `repo-tasks` exists.
- ~~Actually creating the `repo-tasks` repo and its code~~ — **done 2026-08-19**:
  [github.com/TheodoreAD/repo-tasks](https://github.com/TheodoreAD/repo-tasks), public (matching
  this repo's own visibility, not the private convention the `*-polite-mcp`/
  `product-research-pipeline` siblings use — a reusable dev-tooling package, not a personal
  scraper). `src/repo_tasks/quality.py` matches §2 exactly (`_sh_files` graceful degradation,
  `echo=True`, per-task docstrings); `tests/test_quality.py` covers every task via `MockContext`
  plus dedicated `_sh_files` empty/nonempty/failure cases per §4; dedicated `ruff.toml`/
  `pyrightconfig.json`/`pytest.ini`/`dprint.json`; root `tasks.py` dogfoods the same
  `Collection.from_module(quality)` wiring every consumer will use. Verified before pushing:
  `inv precommit` clean (0 lint/type errors, 14 tests) from repo-tasks's own venv — this needed
  running with `VIRTUAL_ENV` unset and its own `.venv/bin` prepended to `PATH`, since a same-named
  `repo_tasks` package already editable-installed from this repo's own `src/` would otherwise shadow
  it and silently test the wrong copy.

### B. Repo template — solves one-time scaffolding (Copier, not Cookiecutter)

**Built 2026-08-19 as [`scaffoldapy`](https://github.com/TheodoreAD/scaffoldapy).** Recommended
**Copier** over literal Cookiecutter, as originally planned: `copier update` applies template
changes to an already-generated project; Cookiecutter has no native equivalent.

**Design changed from the original three-fixed-shapes sketch below to composable axes**, per
explicit user correction during the build session: `interface`
(`mcp_server`/`cli`/`web_service`/`skill`/ `library`), `fetch_strategy`
(`none`/`http`/`browser_session`), and `multi_source` (bool — a single upstream vs. a pluggable
`core/`+`sources/<key>/` adapter split) are independent questions, each gating a small module of
files, rather than one `project_type` choice branching into separate monolithic trees. This scales
to kinds beyond the three sibling repos originally scoped (a CLI, a FastAPI web service) without
forking the whole template, and lets e.g. a CLI that scrapes reuse the exact same `core/`
polite-fetch primitives an MCP server gets. `olx-polite-mcp`'s `core/`+`sites/` split and
`temu-polite-mcp`'s CDP session-manager pattern were still the architecture references — their
_tooling_ (flat layout, no dedicated config files, hand-copied `tasks.py`) was explicitly **not**
copied forward, since it predates `repo-tasks`/`skills/python-conventions` and is itself due for
retrofit (see below), not a source of truth. Seeds match §A/§C0 as originally planned:
`src/<pkg_name>/` layout, `pyproject.toml` (hatchling, dev-dependency on `repo-tasks`,
`[project.scripts]` wired from day one for `mcp_server`/`cli`), dedicated
`ruff.toml`/`pyrightconfig.json`/`pytest.ini`/`dprint.json`/`.editorconfig` copied verbatim from
`repo-tasks`, a two-line `tasks.py` (`Collection.from_module(quality)`, no local override), `.envrc`
(direnv, matching `power-user-linux-setup`'s own — a gap discovered live: even `repo-tasks` itself
was missing this), a new `.github/workflows/ci.yml` (no family precedent before this — `uv sync` +
`inv check`), and a `README.md` "Installation" section shaped like `mcp-skill-shipping`'s pattern.
`AGENTS.md` is deliberately **not** templated — `copier.yml`'s comment explains why (`inv ai.init`
needs its cwd inside a `power-user-linux-setup` checkout, which the template can't reliably locate
on an arbitrary machine); the generated README documents it as a one-time manual step instead.

**Real bug caught during the build, and its permanent fix (same session):**
`Collection.from_module
(quality)` assigned directly as a `tasks.py`'s `ns` puts tasks at the
**root** — `inv precommit`, no `quality.` prefix — unlike `power-user-linux-setup`'s own
`tasks/__init__.py`, which nests via `namespace.add_collection(...)` and does get the prefix.
`repo-tasks/README.md` had exactly this typo (prose said `inv quality.precommit`, its own code
example two lines below correctly said `inv precommit`). Rather than just fixing every doc site to
say the un-prefixed form, **`repo-tasks` now ships the fix as a feature**: `repo_tasks/__init__.py`
exports a ready-made root `ns` with `quality` (and every future module — `docker`, `python_pkg`,
`helm`, ...) nested under its own name, so a consumer's `tasks.py` is just
`from repo_tasks import ns` and `inv quality.precommit` works everywhere, permanently, with no
per-repo `add_collection` boilerplate and no consumer-side change needed as `repo-tasks` grows new
modules. Each module stays individually importable (`from repo_tasks import quality`) for a consumer
that wants to hand-pick a subset instead. Both `repo-tasks` and `scaffoldapy` (its own dogfooding
`tasks.py`, and the template it seeds) were updated to this pattern and re-verified end-to-end.

**`olx-polite-mcp` (stateless shape) and `temu-polite-mcp` (session-backed shape) were the two
reference implementations the template's `core`/`sources` architecture was extracted from** — both
mature, battle-tested repos. `product-research-pipeline` (the `skill`/orchestrator reference) turned
out to have no code at all yet (roadmap-only) — that shape was designed from `mcp-skill-shipping`'s
conventions and the roadmap's stated architecture, not extracted from real code.

### C. Quality-tooling conventions — concrete config for §A/§B

Tool _choice_ for all four (basedpyright, ruff, shellcheck/shfmt, dprint/pytest config) was already
decided before this research; what follows is the tuned configuration each pick actually needs,
researched against real, actively-maintained OSS projects (Home Assistant, Litestar, Pydantic,
httpx, kubernetes, bats-core) rather than abstract rule-category descriptions — this is the content
§A's shared invoke-tasks package and §B's `pyproject.toml`/`dprint.json` template skeleton actually
seed into every consuming repo, not just this one.

**Superseded by §D (2026-08-19): "pull those files directly [and] copy" turned out to be wrong in
practice — `repo-tasks`'s own config files stalled at their initial-commit snapshot while this
repo's kept evolving post-extraction (RUF/C90/PERF/A rule additions, the dprint `textWrap` fix,
`reference`/`skills` excludes), so manual copy-on-demand silently produced the exact drift this
whole plan exists to prevent. §D replaces "copy by hand" with an actual `inv configs.pull`/
`configs.diff` mechanism, and moves this repo's now-more-mature config content into `repo-tasks`'s
package as the real, enforced canonical copy — read that section for the current mechanism.** The
one-genuinely-per-repo-field framing (`known-first-party`) still holds. **The rest of §C below stays
as the reasoning trail** (why `recommended` not `strict`, why this ruff `select` list, the dprint
`textWrap` bug, ...) — useful when a rule needs re-litigating or a new tool gets added, but, per §D,
is no longer something to copy by hand into a new repo.

#### C0. Config file location: dedicated per-tool files, not `pyproject.toml` (resolved 2026-08-18)

**Every tool below gets its own dedicated config file — `ruff.toml`, `pyrightconfig.json`,
`pytest.ini` — instead of a `[tool.X]` block inside `pyproject.toml`.** `dprint.json` already
follows this shape today and doesn't change. The reasoning is the user's own, stated directly:
consolidating every tool's config into one `pyproject.toml` makes template-driven updates across
many repos "very difficult and risky," since `pyproject.toml` also carries each repo's own
`[project]` metadata, dependencies, and build config mixed in with the tuned tool settings — a
dedicated file can be diffed/replaced cleanly on its own (via `copier update` or a manual patch)
without touching anything repo-specific sitting next to it in the same file. All three tools support
this natively — ruff reads `ruff.toml`/`.ruff.toml` in preference to `[tool.ruff]`,
basedpyright/pyright reads `pyrightconfig.json` in preference to `[tool.basedpyright]`, and pytest
reads `pytest.ini`'s `[pytest]` section in preference to `[tool.pytest.ini_options]` — this is a
file-location change only, the tuned rule content documented in §C1/§C2 below is unchanged.

~~This repo (`power-user-linux-setup`) has not yet migrated to this~~ — **done 2026-08-19**
(`af86f6a`): `ruff.toml`/`pyrightconfig.json`/`pytest.ini`, content unchanged from what was in
`pyproject.toml`. `repo-tasks` (§A) ships the same three files from day one, so this is now the
default shape for every repo in the family, not a pilot-only convention.

#### C1. Static type checking — tool choice and strictness

**Landscape (Aug 2026):** four real contenders, no consensus winner.

- **mypy** — incumbent, deepest tutorial/Stack-Overflow ecosystem, but lowest typing-spec
  conformance of the four (~58% in one third-party conformance run) and slowest.
- **pyright** (Microsoft) — mature, highest install base (Pylance ships in VS Code, 196M+ installs),
  strongest strict-mode documentation, ~95–98% conformance.
- **pyrefly** (Meta) — newest to reach stable (1.0, May 2026), best speed+conformance combo in most
  benchmarks, smallest community/troubleshooting footprint of the four.
- **ty** (Astral — same team as ruff/uv, OpenAI-acquired March 2026) — fast, ecosystem-aligned with
  tools already in this stack, but still pre-1.0/beta versioning (`0.0.72` as of this research) —
  not yet broadly recommended as a default by its own maintainers' versioning signal.

**basedpyright** (the user's actual pick, researched in depth as a follow-up): a fork of pyright,
maintained primarily by one contributor (`DetachHead`) plus ~90–200+ contributors depending on
counting method. Exists to close two real gaps in plain pyright: (1) several editor-facing features
— inlay hints, semantic highlighting, docstring/import-suggestion completions — are implemented only
in Microsoft's closed-source **Pylance**, licensed for VS Code only; basedpyright reimplements
Pylance-equivalent features into its own language server so any editor gets parity. (2) Plain
pyright's CLI ships only via npm and needs a Node runtime — an awkward fit for a pure-Python/uv
toolchain; basedpyright publishes a normal PyPI package that bundles its own Node runtime
internally. It tracks upstream pyright tightly — new pyright releases get merged in within 0–2 days,
confirmed directly from commit history, not just from the docs' framing — so it's a genuine
superset, not a diverging fork. It keeps pyright's `off`/`basic`/`standard`/`strict` ladder intact
and adds two more tiers: `recommended` (its new default — every practically-useful rule on,
distinguishing likely-bug errors from style warnings) and `all`, plus a `--writebaseline` mechanism
for adopting stricter rules on an existing codebase incrementally (comparable to ruff's/mypy's own
baseline-adoption story). Posit's engineering blog (Mar 2026), evaluating type checkers for their
Positron IDE, called it "the most mature" of the four forks/alternatives they tested but chose
Pyrefly instead — not on a technical deficiency, but because basedpyright's aggressive-by-default
strictness is a worse fit for exploratory data-science workflows than for package/CLI development,
which is the opposite of this repo family's shape. The one real, unstress-tested caveat: **single-
maintainer bus-factor risk**, vs. Microsoft's institutional backing of plain pyright — no source
found treats this as a current problem, but it's worth naming rather than omitting.

**Decision: basedpyright, `recommended` as the base mode — not `strict`.** This corrects this
research's own first-pass instinct ("strict from day one"), on direct evidence: **`strict` mode does
not enable most of basedpyright's own exclusive bug-catching rules** — `reportAny`,
`reportUnreachable`, `reportImplicitStringConcatenation`, and `reportIgnoreCommentWithoutRule` all
default to `"none"` (or, for `reportUnreachable`, `"hint"` — invisible to a CLI-driven agent loop
entirely) under `strict`, because those rules were wired into `recommended`/`all` for
pyright/VS-Code backward-compatibility reasons, not retrofitted into the older `strict` ladder.
Picking `strict` — the tier that sounds more rigorous — would have silently missed the exact three
bug classes this profile is meant to catch. `recommended` turns them on, but has its own gap: it
grades everything as `"warning"` or `"error"`, and defaults `failOnWarnings = true`, which makes the
grading meaningless to a CLI-driven agent (a `"warning"`-level ceremony rule still fails the run).
The concrete, tuned profile now lives at
[repo-tasks's own `pyrightconfig.json`](https://github.com/TheodoreAD/repo-tasks/blob/main/pyrightconfig.json)
— that's the copy to actually pull from for a new or existing repo; this section documents the
reasoning, not something to keep in sync by hand. The snippet below is the same profile in its
original TOML form (kept for readability of the reasoning above, not as something to copy —
`repo-tasks`'s JSON version is authoritative and may have moved on):

```toml
[tool.basedpyright]
typeCheckingMode = "recommended"

# recommended sets failOnWarnings=true by default, which makes "warning" mean
# the same thing as "error" to a CLI-driven agent loop. Turning it off restores
# the warning/error split as an actual blocking-vs-visible distinction: rules
# left at "warning" below are ceremony the agent shouldn't have to fix to get
# a green run, but still show up in an editor / on review.
failOnWarnings = false

# --- escalate: real bugs "recommended" only grades as warning, or that
# basedpyright's own exclusive rules leave off under "strict" entirely ---
reportAny = "error" # Any silently laundered through instead of a real fix
reportUnreachable = "error" # dead branch from a logic error; "hint" even under strict, CLI-invisible
reportImplicitStringConcatenation = "error" # classic missing-comma bug — see C4 pilot note: can be
# noisy on a codebase with a routine multi-line-string-wrapping style; downgrade per-repo if so
reportIgnoreCommentWithoutRule = "error" # blanket ignore can mask an unrelated future error on the same line
reportUnnecessaryTypeIgnoreComment = "error" # stale suppression left after the real fix landed
reportUnusedImport = "error"
reportUnusedVariable = "error"
reportUnusedFunction = "error"
reportUnusedClass = "error" # unused code = likely leftover from a half-finished edit
reportUnusedCoroutine = "error" # forgotten `await`; recommended oddly downgrades this from basic's error
reportUnnecessaryIsInstance = "error"
reportUnnecessaryCast = "error"
reportUnnecessaryComparison = "error"
reportUnnecessaryContains = "error" # always-true/false check = wrong assumption from a bad refactor
reportMatchNotExhaustive = "error" # missing match case
reportRedeclaration = "error" # same symbol, two incompatible types = probably duplicated code
reportPropertyTypeMismatch = "error" # subtly-wrong getter/setter type

# --- downgrade: strict-mode ceremony that recommended doesn't already soften ---
reportMissingTypeArgument = "warning" # bare generics; not worth a turn parametrizing every list/dict use

# --- left at recommended's default "warning" (non-blocking once failOnWarnings=false): the
# annotation-completeness / untyped-third-party-dependency cluster — reportMissingParameterType,
# reportUnknown{Parameter,Argument,Variable,Member}Type, reportMissingTypeStubs,
# reportUntyped{FunctionDecorator,ClassDecorator,BaseClass,NamedTuple},
# reportUnannotatedClassAttribute, reportCallInDefaultInitializer, reportUnusedCallResult,
# reportUnusedParameter, reportPrivateUsage — no override needed.

# fill in per untyped dependency as encountered, instead of a global severity change:
allowedUntypedLibraries = []
```

`useLibraryCodeForTypes` stays at its default `true` (already reduces `reportUnknown*` noise by
reading a dependency's actual source when no stub exists). basedpyright added
`allowedUntypedLibraries` specifically in response to the well-documented pyright pain point of the
`reportUnknown*`/ `reportMissingTypeStubs` cluster cascading badly against untyped third-party
libraries ([microsoft/pyright#10566](https://github.com/microsoft/pyright/issues/10566) was an open,
unmerged request for exactly this in upstream pyright) — the practical answer to that friction is a
per-library allowlist entry as it's encountered, not a global severity retreat. No comparable
basedpyright-specific "pragmatic strict config" writeup exists yet in the wild (`recommended` mode
and `allowedUntypedLibraries` are both new enough that this appears to be a genuine gap) — this
profile is derived directly from basedpyright's own rule-default table
([docs.basedpyright.com/latest/configuration/config-files/#diagnostic-settings-defaults](https://docs.basedpyright.com/latest/configuration/config-files/#diagnostic-settings-defaults)),
not adapted from a third party's already-published tuning. Type-hygiene conventions this profile
enforces (scoped `# type: ignore[code]`, "type everything including snippets") live in
`skills/python-conventions/references/rationale.md` §8 — this section is the tool config, that one
is the writing convention it backs.

**Genuine dissent worth keeping in view, not adopting:** Armin Ronacher (Flask creator), two posts —
["Untyped Python: The Python That Was"](https://lucumr.pocoo.org/2023/12/1/the-python-that-was/)
(Dec 2023) argues Python's original strength was a tiny language-runtime surface area, and heavy
typing risks "creating the new Java." More pointed:
["In Support Of Shitty Types"](https://lucumr.pocoo.org/2025/8/4/shitty-types/) (Aug 2025) argues
fragmented, disagreeing type checkers actively hurt LLM coding agents specifically, because models
struggle when tools disagree on what counts as an error — his conclusion is that _consistency_ of
one checker's opinion matters more than maximal strictness for agent-driven workflows. This is
unusually on-point given this repo family's own agent-heavy workflow, and is exactly why "pick one
checker, one config, and stop arguing about it" is the right shape of decision here even though
"strict" itself isn't universally endorsed.

#### C2. Ruff, pytest, and dprint — configuration conventions

All three tools' _choice_ is already decided; this is about tuning.

**A concrete gap found, independent of anything flagged before:** Ruff's own zero-config default
already includes `F`, `E`, `B`, `UP`, **and `RUF`** (Ruff's own rule family — mutable
class-attribute defaults, `noqa` hygiene, f-string pitfalls). Because an explicit `select` list is
additive-only, not inheriting the zero-config default, a repo with an explicit `select` gets
**none** of `RUF` unless it's listed — worth adding on its own merits (22.7% direct-selection rate
across a ~127k-repo PyPI survey, close to table-stakes elsewhere).

**`C901`/mccabe — confirmed precisely, plus a real gotcha to avoid.** Default `max-complexity = 10`
per Ruff's own settings docs, tracing to McCabe's original "anything beyond 10 is too complex." Not
covered by any default-selected category — must add `C90` to `select` explicitly. **The gotcha**:
Pydantic's own `pyproject.toml` sets `[tool.ruff.lint.mccabe] max-complexity = 14` but never adds
`C90`/`C901` to its `select` array — the complexity setting is silently inert without it. Double-
check any new repo's config for the identical trap once `C90` is added.

**Per-category verdicts, evidence-based against four real flagship configs** (none of the four
select every category — hand-picked, narrow selections are the actual norm):

- **Add**: `PERF` (low-noise, real inefficiency catches — selected by Home Assistant and Pydantic),
  `A`/flake8-builtins (near-zero-noise, catches shadowed builtins), `DTZ`/flake8-datetimez (catches
  naive `datetime.now()`, real timezone-bug class), `T20`/flake8-print — but see C4's pilot
  correction below: this one is genuinely repo-shape-dependent, don't apply it blindly.
- **Add, but only the non-`PLR` subset**: `PL`/pylint. Every real config surveyed that touches `PL`
  immediately carves out the `PLR*` (refactor-suggestion) codes — Mozilla's own config removed
  "nearly 2000 warnings" by disabling `PLR0913`/`0911`/`0912`/`0914`/`2004` outright; Ruff's
  `PLR0913` counts `self`/`cls` toward its argument limit and doesn't exempt overrides by default, a
  frequently-cited annoyance. Select `PL`, keep `PLC`/`PLE`/`PLW` (closer to real bugs), drop `PLR`.
- **Add, same pattern**: `TRY`/tryceratops — directly relevant to
  `skills/python-conventions/references/rationale.md` §3's exception-hierarchy guidance. Home
  Assistant selects it but ignores `TRY003` (long exception messages) and `TRY400` (`logging.error`
  vs `.exception`) as too opinionated — a minimal exception hierarchy (that plan's own §3 decision)
  makes `TRY003` actively fight the design, not just style noise. Recommend select-then-triage: turn
  it on, see what actually fires, decide ignores from real signal rather than pre-guessing.
- **Skip, or scope to non-test code**: `ARG`/flake8-unused-arguments — none of the four flagship
  projects select it, likely because it collides with two common, legitimate patterns: interface-
  conformance overrides, and pytest fixtures that take an argument purely for its side effect (e.g.
  `monkeypatch`) — exactly this repo family's testing style. If added at all, exclude `tests/**` via
  `per-file-ignores`.
- **Skip, cherry-pick at most**: `N`/pep8-naming — no surveyed project selects the whole category;
  the two that touch it cherry-pick 3–4 specific codes. Full-category tends to fight external-API-
  shaped names (JSON keys, wrapped library attributes).
- **Skip for now**: `FBT`/flake8-boolean-trap — a real, well-articulated footgun (Ruff's own docs
  make the correctness case directly), but none of the four flagship projects select it, and it has
  known friction with CLI-framework decorators (click/typer positional boolean flags) — relevant
  friction given this repo family includes CLI tools. Treat as "read the linked article, apply the
  judgment manually," not a lint rule, for this context.
- **No official Ruff "recommended baseline" ladder exists**, basedpyright-style — confirmed no
  curated tier is published. Ruff's _default_ itself jumped from a narrow 4-category set to 413
  rules across 34 categories in v0.16.0 (2026) — exactly the broad-default posture this repo's own
  config comment deliberately opts out of, now confirmed as a real, recent, documented change rather
  than a stale assumption. The real signal is the pattern across flagship configs above: narrow,
  hand-picked, explicit ignores for noisy subcategories.

**pytest config mechanics** (design guidance on fixture scope and DAMP-vs-DRY test structure lives
in `skills/python-conventions/references/rationale.md` §7 — this is only the mechanical setup):
marker registration via `markers = [...]` plus `--strict-markers` matches Litestar's and httpx's own
configs exactly — already this repo's convention, already in `pyproject.toml`'s
`[tool.pytest.ini_options]`.

**dprint — one real, documented bug to route around, one call this project makes on its own
reasoning.** Markdown plugin defaults: `line_width = 80`, `text_wrap = "maintain"` (tries to
preserve the source's existing wrap decisions). The default `maintain` mode has an **open,
documented bug** — it can delete newlines inside linked/inline-code text in some cases
([dprint-plugin-markdown#149](https://github.com/dprint/dprint-plugin-markdown/issues/149)) — worth
setting `textWrap` explicitly rather than relying on the buggy default, independent of any style
preference. **`"never"` is a trap, verified the hard way (see C4)**: it does not mean "leave
wrapping alone" — it means dprint will _never insert a line break in prose_, which collapses
hand-wrapped paragraphs into single giant lines. `"always"` is what actually enforces consistent
hard-wrapping at a configured width. Needs a markdown-specific `lineWidth` override, separate from
the top-level code/JSON/TOML width — this repo landed on an explicit `100` (confirmed to not already
exist as a value anywhere else in its configs, and deliberately left un-unified with ruff's 120-char
code width; ruff format never auto-wraps docstring/comment prose regardless of `line-length`, so a
docstring can already run up to 120 chars with `E501` flagging it but nothing auto-fixing it — a
pre-existing, orthogonal inconsistency this decision didn't try to resolve). Beyond the bug-routing
argument, hard-wrapping at a fixed width has one concrete, checkable win: it improves diff/merge-
conflict locality (a one-sentence edit doesn't reflow the whole paragraph in the diff) — independent
of any human-vs-agent-readability claim, which has only thin direct sourcing and is flagged honestly
rather than inflated.

#### C3. Shell script checking

Not in the original seed list — the user flagged a real gap ("I also need something to check shell
scripts") for the bootstrap/setup `.sh` scripts already in this repo family.

**`shellcheck` is the real, not just asserted, standard** — 39,879 GitHub stars, pre-installed on
GitHub Actions/Travis/CircleCI/Codacy runners per its own README, bundled into GitHub's own
`super-linter`, and used in CI by real large projects independently verified live: kubernetes/
kubernetes' `hack/verify-shellcheck.sh` (version-pinned), bats-core's own `shellcheck.sh`. Google's
own Shell Style Guide recommends it "for all scripts, large or small." No genuine competing static
analyzer exists at comparable scope — `bashate` (PEP8-style, far lower adoption), `shellharden`
(rewrites toward shellcheck conformance, complementary not competing), `checkbashisms` (narrow
POSIX-portability subset only).

**Severity tiers, directly analogous to ruff's rule-selection knob**: `error` > `warning` > `info` >
`style`, default shows everything; `--severity=warning` suppresses `info`/`style` noise. Community
norm on disabling checks (inferred from real precedent, not one canonical statement): scope narrowly
and say why — kubernetes' own `verify-shellcheck.sh` names exactly three globally-excluded codes
with inline reasons (`SC1090`/`SC1091` for extensively-used non-constant `source`, `SC2230` for an
intentional `command -v` vs `which` preference) — the one documented friction point worth planning
for up front if any bootstrap script sources a runtime-computed path.

**`shfmt` is the real formatting counterpart** — shellcheck does not reformat code at all, so a
consistent-style story needs both, same two-tool split as `ruff check` + `ruff format`. 8,982 stars,
packaged across every major distro/package-manager, actively maintained. The shellcheck+shfmt
pairing is observed real practice, not assumed: `jumanjihouse/pre-commit-hooks` bundles both for
exactly this reason.

**Integration: fold into the shared invoke-tasks namespace (§A), no `pre-commit` framework.**
`pre-commit` is genuinely how most real projects wire these two together, but adopting it here would
mean a second task-runner, a second config format, and a second mental model for "how do I run
checks" sitting alongside `invoke`, which already exists and already solves exactly this "aggregate
multiple quality tools behind one command" problem for ruff+dprint — duplicating a problem already
solved is the wrong tradeoff. Concrete shape: `shfmt -l -d` (check) / `-w` (fix) and `shellcheck`
(severity floor per-repo, see C4 — this repo needed none), both run over `fd -e sh` output, folded
into the same `check`/`fix`/`precommit` task graph as ruff/dprint — landed exactly this way in
[repo-tasks's `quality.py`](https://github.com/TheodoreAD/repo-tasks/blob/main/src/repo_tasks/quality.py),
including the graceful zero-`.sh`-files degradation §A's "no allowances" decision required. A root
`.shellcheckrc` should hold any exclusions, each with an inline comment stating why, following
kubernetes' precedent directly.

**Install mechanism: `uv-tool`, not `apt` — see C4** for the reasoning (Rust/Go precedent check) and
the mid-pilot correction that led here; `shellcheck-py`/`shfmt-py` (PyPI wheels bundling the real
prebuilt upstream binaries) are what §A/§B's `setup.toml`-equivalent for a consuming repo should
seed, installed through whatever that repo's own declarative package pipeline is — never a manual
`uv tool install`/`apt install` run by hand.

#### C4. Pilot findings — applying all of this to `power-user-linux-setup` itself

Landed in commit `c01b53c` (2026-08-16/17), config _content_ only — still inside `pyproject.toml` at
that point. The file-_location_ move (`ruff.toml`/`pyrightconfig.json`/`pytest.ini`) landed later,
2026-08-19, `af86f6a`; content unchanged by that move. Real gotchas a pure literature review
couldn't have surfaced — this is the actual payoff of piloting on a real codebase before writing any
of it into something other repos would copy verbatim via §A/§B.

**basedpyright config gotchas, both self-inflicted, both worth avoiding when seeding a new repo:**

- **Setting `exclude` explicitly replaces basedpyright's own default exclude list, it doesn't add to
  it.** The default list includes `**/.*` (any dot-directory), which is how `.venv` normally gets
  skipped with zero config. Adding `exclude = ["reference"]` to keep out a vendored-repos directory
  silently un-excluded `.venv` too — the first real run type-checked 16,009 errors across
  typeshed/third-party packages inside the virtualenv itself before this was caught. Fix: repeat the
  defaults (`"**/node_modules"`, `"**/__pycache__"`, `"**/.*"`) alongside whatever you're adding.
- **TOML scopes bare `key = value` lines to the most recently opened table**, not back to the parent
  table — a `reportImportCycles = "warning"` line placed after
  `[[tool.basedpyright.
  executionEnvironments]]` silently became a property of that array entry
  instead of a top-level basedpyright setting, and did nothing at the top level. Every top-level
  `[tool.basedpyright]` key has to come before the first `[[executionEnvironments]]` block in the
  file.
- **`cast(SomeTypedDict, x)` fails basedpyright's "sufficient overlap" check when `x`'s static type
  is a concrete `dict[str, Any]`** (e.g. `tomllib.load()`'s real return type), even though the same
  cast succeeds cleanly when `x`'s type is genuinely `Any` (e.g. `json.loads()`'s return type).
  basedpyright's own error message names the fix: route through `object` first —
  `cast(SomeTypedDict, cast(object, x))`.
- **`reportImplicitStringConcatenation` at `"error"` was pure noise on this codebase's real style**:
  every one of the 52 hits found was this repo's routine convention of wrapping one long string
  literal across several parenthesized lines (log/print messages, docstrings) — not a single genuine
  missing-comma bug. Downgraded to `"none"` for this repo. Ruff's own `ISC001` has the identical
  conflict with the formatter's string-wrapping and is disabled for the same documented reason —
  this wasn't a one-off surprise, it's a known category of false positive for this exact rule shape,
  just not one C1's research surfaced because it never ran the rule against real code. **Not a
  reason to drop the rule from the template default in C1** — just a reminder that any repo adopting
  it should run it against real code before assuming `"error"` is the right severity there too.
- **`reportImportCycles` fired on `tasks/__init__.py`'s own necessary shape**: it imports every task
  submodule to build an `invoke.Collection`, and each submodule does `from . import util` (a sibling
  import through the package) — a textbook, harmless Python circular-import pattern (Python resolves
  submodule imports fine without needing the package's own `__init__` body to finish first), not a
  bug. Downgraded to `"warning"` rather than silenced entirely, so a _genuine_ cycle elsewhere would
  still surface.
- **`allowedUntypedLibraries` doesn't cover `reportAny`/`reportFunctionMemberAccess`** — confirmed
  by running into it directly: adding `invoke` there fixed the bulk of the warning volume (every
  `reportUnknown*`/`reportMissingTypeStubs` hit from invoke's own missing stubs) but did nothing for
  `ai.skills.body(...)` (reaching into invoke's `Task.body` attribute to unit-test the undecorated
  function directly) — that rule pair needed a scoped
  `# pyright: ignore[reportAny,
  reportFunctionMemberAccess]` at the two call sites instead. The
  docs' own wording ("`reportUnknownVariableType`, `reportUnknownMemberType`, and
  `reportMissingTypeStubs`") is precise and was easy to over-generalize from without hitting this in
  practice.

**Ruff findings — confirmed research, plus one repo-shape-dependent correction the research couldn't
have predicted without real code to run against:**

- `RUF`'s absence was real, not hypothetical — this repo genuinely had zero `RUF` coverage before
  this pass. `PLR`/`TRY003` were confirmed noisy on real hits here too (`PLR0912`/`PLR2004`/
  `PLR0913`/`PLR0917`/`PLR0911`/`PLR0915` all fired on ordinary CLI-task-handler code, matching Home
  Assistant/Litestar/Mozilla's own documented reasons for dropping them).
- **`T20`/flake8-print does not fit this repo's shape at all — 460 hits, essentially the whole
  `tasks/` tree.** C2's own verdict ("exempt the CLI-output entrypoint module") assumed a library
  with one or a few genuine CLI-output modules; here, _every_ `@task`-decorated function prints
  status as its primary interface — there's no minority of files to exempt, printing _is_ what this
  whole package does. Not added to this repo's `select`. Worth carrying into any future skill/
  template as an explicit caveat: `T20` is a good fit for library code where a stray `print()`
  really is a leftover debug statement, not for an invoke/Click/argparse-shaped CLI-tool repo where
  console output is the product.
- `C901` (15 pre-existing complexity hits, all ordinary multi-branch `@task` handlers) and the 5
  `A001`/`A002` builtin-shadowing hits (`dir`/`all` as invoke task/parameter names — which _are_ the
  actual `--dir` flag and `inv <ns>.all` subcommand names, so renaming would break the CLI) were
  deliberately **not** refactored in this pass — `ruff check --add-noqa` recorded them as known,
  named, greppable (`rg "noqa: C901"`) deferred work rather than either silently ignoring the whole
  rule or forcing a same-session mass refactor of working automation code.
- **`PLW1510` (subprocess-run-without-check) was a genuine, valuable catch, not noise**: 12
  `subprocess.run()` calls repo-wide with no explicit `check=`. Checked every single one before
  fixing — all 12 turned out to already be deliberate "probe and inspect `.returncode`/`.stdout`,
  never raise" patterns (several with docstrings saying so explicitly), so the uniform fix was
  making the existing behavior explicit (`check=False`) everywhere, not adding `check=True`
  anywhere. The rule's value here was forcing an explicit choice, not revealing a bug — but reading
  each site to confirm that, rather than blindly adding `check=False` everywhere, is exactly the
  "select-then-triage" workflow C2 already recommended.
- **`reportUnusedVariable`-style findings surfaced real test-coverage gaps, not just dead code**:
  four tests in `test_allowlist.py` unpacked a `_diff_nodes()` return value (`new_invalid`) without
  ever asserting on it — a real, silent verification gap in tests specifically about "does this node
  correctly avoid being routed to `new_invalid`." Fixed by adding the missing assertions, not by
  prefixing the variable with `_` — the ruff finding was pointing at an actual weaker-than-intended
  test, not a false positive.

**Shell tooling: the install mechanism changed mid-pilot, and the reasoning is worth keeping.**
Originally planned as a plain `apt`-installed `shellcheck` (already true before this pass) plus a
new `apt`-installed `shfmt`. The user redirected twice: first to prefer a fully venv-portable,
CI-friendly install over any system package at all (`shellcheck-py`/`shfmt-py`, verified real and
actively maintained via the PyPI index directly, not just search-result summaries) — then, once it
became clear shell scripts aren't Python-project-specific and both tools should be available
machine-wide, to `uv-tool` instead of a plain project dev-dependency, installed through this repo's
_own_ declarative package pipeline (`setup.toml` + `inv python.tools`), explicitly **not** a manual
`uv tool install` run by hand — "that defeats the purpose of this setup." Both `shellcheck` and
`shfmt` (previously apt, now `uv-tool`) ended up in `setup.toml` exactly like every other
user-scoped uv tool this repo already manages (`gnome-extensions-cli`, `nox`, `mkdocs`, `glances`,
...). Checked whether Rust/Go's own quality tools set a precedent either way, since shell tools now
being machine-wide (not Python-project-scoped) raised the same question §A/§B will face for any
non-Python tooling: **Rust's is unambiguous** — `rustup`/`cargo` have no system-wide install path at
all; `clippy`/`rustfmt` are `rustup component`s installed per-user to `~/.cargo/bin`, by design.
**Go's is more mixed** — `gofmt` ships bundled with the toolchain itself, but for a real linter
(`golangci-lint`), the maintainers themselves steer people _away_ from the user-scoped `go install`
toward a pinned binary-download script, specifically because `go install` compiles locally against
whatever Go version happens to be present, so the resulting binary isn't the one that was actually
tested — a reproducibility concern, not a scope-of-install one, and it doesn't transfer here (a
prebuilt-binary wheel is already the pinned upstream release, same guarantee a `deb-github` install
would give). Net: user-scoped tool management is the stronger, cleaner precedent of the two — the
`uv-tool` install mechanism this repo landed on is the right default to carry into §A/§B, not a
one-off local choice.

**dprint's `textWrap` modes are easy to get backwards — verified the hard way**, confirming C2's own
warning above: `"never"` does not mean "never touch wrapping, leave the file alone" — it means
dprint will _never insert a line break in prose_, which collapsed this repo's existing hand-wrapped
paragraphs into single giant lines on the first attempt (the opposite of the intended fix).
`"always"` is what actually enforces consistent hard-wrapping at a configured width.

### D. Repo-family scope split + config distribution mechanism (2026-08-19)

**Scope split across the three repos, stated explicitly per the user's own framing (this
supersedes any looser language earlier in this plan):**

- **`power-user-linux-setup`**: machine initial setup + small subsequent updates. Not itself a
  template target — it's the meta/origin repo, shaped nothing like the `interface`/`fetch_strategy`
  sibling repos §B targets.
- **`repo-tasks`**: using tools daily in dev — the invoke tasks run constantly (`lint`/`format`/
  `type_check`/`test`/`precommit`), **and now also the config each of those tools reads**, since the
  config is strongly coupled to the task that invokes it (a `ruff.toml` divorced from the `ruff
  check` call that reads it is exactly the kind of split-brain this plan is trying to eliminate).
  This is the resolution to §C0/§C's "which repo is source of truth" ambiguity: **`repo-tasks`,
  full stop, as a real enforced mechanism, not a "please copy this by hand" note.**
- **`scaffoldapy`**: one-time project *structural* scaffolding (layout, `pyproject.toml` skeleton,
  CI workflow, packaging entry points) — **not** tool config anymore (see below), and, for now,
  **not** fixing the structure of already-existing repos either (see "Narrowed for now" below).

**Why `repo-tasks`'s config files, not `power-user-linux-setup`'s, going forward:** confirmed live
(2026-08-19) that `repo-tasks`'s copies had drifted to a stale initial-commit snapshot while this
repo's kept evolving after extraction — the plan's own §C0 text claiming "repo-tasks is the thing to
copy from" was aspirational, not yet true. One-time reconciliation needed: this repo's current,
more-tuned `ruff.toml`/`pyrightconfig.json`/`dprint.json`/`pytest.ini`/`.editorconfig` content moves
into `repo-tasks`'s package as `src/repo_tasks/configs/*` (replacing its stale copies), stripped of
this-repo-only local exceptions (see below) — `repo-tasks` package data becomes the one committed,
canonical copy, everywhere.

**Mechanism: `inv configs.pull` / `inv configs.diff`, a new task module (`repo_tasks.configs`)
shipped alongside `quality`, config files bundled as package data
(`src/repo_tasks/configs/*`, resolved via `importlib.resources`).**

- `inv configs.pull` — materialize each config file at the calling repo's root from the *installed*
  `repo_tasks` package, applying that repo's local-override manifest if one exists (below).
  Overwrites whatever's on disk.
- `inv configs.diff` — dry-run: diff installed-package (+ local overrides) version against what's
  currently on disk, print, nonzero exit if different. Never writes.
- **Default source is simply "the `repo_tasks` package already resolved into this environment"** —
  which makes it index-agnostic for free: works identically whether that resolved via the public
  `github.com/TheodoreAD/repo-tasks` git dependency, a private git remote, or a private
  PyPI-compatible index in a corporate environment. Nothing in `configs.pull` itself needs to know
  or care which.
- Update lifecycle is identical to `quality.py`'s: `uv lock --upgrade-package repo-tasks` bumps the
  version, `inv configs.pull` re-materializes. One update lifecycle for code and config both, not
  two.
- **Explicitly rejected**: dprint's native `"extends": "<url>"` (would fetch over the network on
  *every* `dprint check` run, not just at dependency-resolve time — exactly the kind of surprise
  runtime network dependency that fails opaquely behind a corporate proxy/firewall — "corpos HATE
  blockers"). A raw `curl`/git-fetch-at-pull-time sync (re-invents the version pinning `uv.lock`
  already solves, and needs its own auth/private-index story from scratch). Using Copier for config
  sync too (couples config lifecycle to structural lifecycle — the exact thing this scope split is
  separating).

**Trigger: deliberate, not automatic — corrected 2026-08-19, an earlier draft of this section had
`configs.pull` wired as a `pre=` dependency of `fix`/`check`/`precommit` so it "self-healed" on every
run. Rejected directly**: config files need to be committed (below), and quietly rewriting a tracked
file as a side effect of a routine `inv quality.precommit` run — possibly pulling in a newer
`repo-tasks` version the developer never decided to take yet — is exactly the kind of surprise this
family's tooling is supposed to avoid. `configs.pull`/`configs.diff` are standalone tasks, run
deliberately, same tier as `uv lock --upgrade-package repo-tasks` itself: something a human or agent
decides to do, reviews the diff of, runs the test suite against, and commits — an intentional,
tested, reviewed code change like any other, not a background side effect of daily `inv` use.

**Root-level config files are committed, in every repo — never gitignored.** Reversed from an
earlier draft of this section. Two concrete reasons this actually matters, not just preference: (1)
**CI** in some setups needs the files present without first running `inv` (a raw `ruff`/`basedpyright`
invocation outside this family's `inv quality.*` wrapper, or a CI cache/restore step that assumes the
working tree is already complete); (2) **audit** — `git blame`/`git log` on the config file itself is
how you answer "what ruleset was actually in effect for this PR," which is impossible if the file was
never checked in. `configs.pull`'s committed output is the reviewable artifact; nothing about the
mechanism changes, only that its result lands in a normal commit instead of a gitignored, silently-
regenerated file.

**Local exceptions: investigated, not assumed — most turned out to already be unnecessary.** Live
tested against `power-user-linux-setup`'s actual config files (2026-08-19/20) rather than guessed:

- **`ruff.toml` needs zero local exceptions.** Ruff's file discovery already respects `.gitignore`
  by default — confirmed empirically: `ruff check .` surfaces 0 hits from the (gitignored)
  `reference/` tree, but explicitly targeting `ruff check reference/` (bypassing discovery) surfaces
  143. No `exclude` entry was ever needed for it, and `ruff.toml` has none.
- **`pyrightconfig.json`'s `reference`/`skills/*/references/snippets` excludes are genuine and
  unavoidable — basedpyright does *not* respect `.gitignore`.** Confirmed empirically: stripping
  those two entries from `exclude` (leaving only basedpyright's own defaults) took this repo from
  `0 errors, 2811 warnings` to `132 errors, 3509 warnings`, entirely from `reference/`'s vendored
  clones and the standalone example snippets under `skills/*/references/`. This is the one real,
  irreducible per-repo exception found.
- **`dprint.json`'s `.vscode`/`uv.lock` excludes are *not* a `power-user-linux-setup`-specific
  exception at all** — `repo-tasks`'s own (stale) `dprint.json` already carries both. They belong in
  the shared baseline as-is, no local override needed.
- **`dprint.json`'s `cli-allowlist/help-cache` exclude is genuine**: real, git-tracked (not
  gitignored — confirmed via `git ls-files`), machine-generated JSON cache content specific to this
  repo's own allowlist pipeline. Stays a local exception.

Net: after reconciliation, **exactly two lines of local override exist across the whole family
today** — `pyrightconfig.json`'s two extra `exclude` globs and `dprint.json`'s one extra `excludes`
entry, both `power-user-linux-setup`-only. This is small enough to validate the whole "rely on
gitignore, keep true exceptions rare and loud" premise rather than assume it.

**What `configs.local.toml` is for, stated plainly**: it's the one place a consumer repo declares the
small number of config additions it genuinely needs beyond the shared `repo-tasks` baseline, so that
re-running `configs.pull` later (after a `repo-tasks` version bump) doesn't silently wipe them out.
Without it, `configs.pull` would just overwrite each config file verbatim from the package every
time — fine for the common case (most repos need nothing extra), but for the rare repo that does
(`power-user-linux-setup` today), the person running the next pull would have to *remember*, by hand,
which lines to re-add and why. `configs.local.toml` makes that unnecessary: it's a small, committed,
human-and-agent-readable manifest — "this repo needs X, in addition to the shared config, because
Y" — that `configs.pull` reads and folds in automatically on every run, so the addition survives
indefinitely without depending on anyone's memory. It is not a general override/customization system
— see the "kept deliberately dumb" framing below for exactly how narrow its actual scope is.

**Mechanism, kept deliberately dumb (no per-repo `select`/`extends`/deep-merge)**: a single tracked
`configs.local.toml` at a consumer repo's root, present only in repos that need one (today: only
`power-user-linux-setup`). Shape — additive-only, list-append per target file/key, each entry's *why*
required inline as a TOML comment (this is the concrete mechanism for "exceptions must always be
explained in a comment," since the exceptions can't all carry a comment in the generated file itself
— `dprint.json` is plain JSON, no comment syntax, while `pyrightconfig.json`'s JSONC *could* but
shouldn't be relied on as the only place the reasoning lives):

```toml
# basedpyright doesn't respect .gitignore (confirmed 2026-08-19) — reference/ is gitignored but
# still gets type-checked without this. skills/*/references/snippets are standalone example files
# with their own "pip install X" docstrings, not this project's own code.
[pyrightconfig."exclude"]
append = ["reference", "skills/*/references/snippets"]

# cli-allowlist/help-cache is real, git-tracked generated JSON content specific to this repo's own
# allowlist pipeline — not something any other repo in the family has.
[dprint."excludes"]
append = ["cli-allowlist/help-cache"]
```

`configs.pull` reads this file if present, and appends each listed entry onto the corresponding list
in the pulled base file before writing — no scalar overrides, no arbitrary deep merge, exactly the
two real cases found above and nothing more general than that.

**Self-hosting, corrected 2026-08-19**: an earlier draft of this section had `repo-tasks`'s own root
config files as pure generated output, kept identical to `src/repo_tasks/configs/*` at all times.
Wrong — clarified directly: `repo-tasks` is still a normal Python project, developed to the same
standards as anything else in this family, and its root config files are what govern *its own* dev
loop (`inv quality.check` linting/type-checking `repo-tasks`'s own `src/`/`tests/`). Those root files
are allowed to diverge, in-flight, from `src/repo_tasks/configs/*` — the package data is "what gets
shipped to consumers," the root files are "what `repo-tasks` uses on itself today," and the two are
related deliberately, not by an automatic identity mapping:

- Root files are committed and hand-developed like any repo's config — including possibly their own
  `configs.local.toml` if `repo-tasks` itself ever needs a local exception (none known today).
- `configs.promote` (below) is the deliberate, one-directional action that takes whatever's currently
  at root and makes it the new canonical `src/repo_tasks/configs/*` baseline, once the maintainer
  decides that tuning is ready to ship to every consumer.
- `configs.pull` still applies to `repo-tasks` itself too (per direct instruction) for the opposite
  case: resetting root back to what's currently shipped, or, combined with `--source` below, staging
  a candidate baseline pulled in from another repo's already-tuned config before reviewing it.

**Authoring/harvest workflow — how an update made *outside* `repo-tasks` gets back in.** Composed
from two primitives rather than one bespoke harvest tool, per the instruction to keep `configs.pull`
itself the one mechanism everything routes through:

1. `configs.pull` gains an optional `--source` override (default: the installed package) —
   `--source git:<url>` or `--source local:<path>` — pointing it at *another repo's root* config
   files instead of the installed package. Run from inside `repo-tasks`'s own checkout, this
   materializes some other repo's (e.g. `power-user-linux-setup`'s) current root config files at
   `repo-tasks`'s own root — the same shape any consumer ends up in, just sourced differently. A
   generically useful flag on its own (e.g. testing against a fork), not repo-tasks-only.
2. A second task, **local to `repo-tasks`'s own `tasks.py`** (not part of the distributed
   `repo_tasks.configs` module — this is exactly the "a project's `tasks.py` may carry its own
   custom tasks beyond the shared import" allowance below) — `inv configs.promote` — diffs whatever
   is now sitting at `repo-tasks`'s root against `src/repo_tasks/configs/*` and, by default, only
   prints the diff; `--apply` writes root → package. Diff-first-by-default matches `configs.diff`'s
   own "surface drift, don't blind-overwrite" posture.

Net authoring loop: `configs.pull --source local:/path/to/power-user-linux-setup` (or `git:`), review
`configs.promote`'s diff, `configs.promote --apply` once satisfied. Two small, testable primitives,
no separate one-off script.

**Consumer `tasks.py`/`tasks/` is no longer required to be *only* the two-line import.** The original
§A framing ("Every consumer repo's own `tasks.py` shrinks to exactly this, with no local override")
is revised: that "no allowances" decision was and stays about the *shared quality task graph's
internals* — every consumer's `fix`/`check`/`precommit` still resolve to the exact same composite
tasks from `repo_tasks`, unmodified, no per-repo fork of what "check" means. What's relaxed is the
*container* — a repo's `tasks.py`/`tasks/` package may define additional local tasks alongside
`from repo_tasks import ns` for that repo's own custom needs (`power-user-linux-setup`'s own
`tasks/__init__.py` already does exactly this — `apt`, `allowlist`, `wsl`, `devcontainer`, `verify`,
now also `quality` — and `repo-tasks`'s own `configs.promote` above is the same pattern). Nothing
about `quality`'s or `configs`'s own composite-task shape changes.

**`scaffoldapy` narrowed for now, two ways:**

- **Sheds its own literal copies of the four config files** (currently a *third* duplicate, per the
  diff run 2026-08-19 — `scaffoldapy/{ruff.toml,pyrightconfig.json,dprint.json,pytest.ini}` and
  `template/{dprint.json,pyrightconfig.json}`). Post-generation step becomes `uv sync` → the
  generated `tasks.py`'s own `inv configs.pull`, materializing them from the now-installed
  `repo-tasks` dependency instead of stamping template copies that immediately go stale.
- **No `copier update`/`recopy` against already-existing repos for now, by direct instruction** —
  `scaffoldapy` needs to stabilize on fresh-repo generation first. This defers the "Retrofit path"
  section below (`olx-polite-mcp`/`temu-polite-mcp`/`freshful-polite-mcp`) and the "paired agent
  skill for fixing an existing repo's structure" idea floated earlier in this conversation — both
  depend on `copier update` being trustworthy against real, already-diverged repos, which isn't
  being exercised yet. `scaffoldapy`'s current scope is fresh-repo generation only.

**Every tool's actual relationship with `.gitignore` needs to be known and controlled, not assumed —
tracked as its own plan in `repo-tasks`, not here.** The ruff-vs-basedpyright split found above (one
respects `.gitignore` natively and needs zero manual excludes, the other doesn't and needs permanent
ones) was discovered empirically, one tool at a time, while designing this mechanism — it was not
predictable from documentation alone, and the same is true for whatever `pytest`/`dprint`/
`shellcheck`/`shfmt` turn out to do. Given how easy it would be to get this wrong per tool (and how
wrong "probably respects gitignore" would have been for basedpyright specifically), this needs the
same empirical audit applied to every tool `repo-tasks` configures, not just the two checked so far —
written up as
[`repo-tasks/plans/2026-08-19-gitignore-tool-alignment.md`](https://github.com/TheodoreAD/repo-tasks/blob/main/plans/2026-08-19-gitignore-tool-alignment.md)
since it's `repo-tasks`'s config baseline the findings actually land in, not this repo's. That plan
also carries the related "preemptively cover community-standard excludes (`.venv`, `dist/`,
`__pycache__`, cache dirs, ...), but let `.gitignore` itself absorb as much of that as possible rather
than duplicating it into every tool's own exclude list" question — same investigation, same place.

**Open questions:**

- Naming is a placeholder, not load-bearing: `configs.pull`/`configs.diff`/`configs.promote`, the
  `--source git:<url>|local:<path>` prefix convention. Fine to bikeshed at implementation time.
- Whether `configs.promote`'s diff should also flag when a *local-override manifest* entry looks
  like it's actually generic (i.e., candidate to fold into the shared baseline instead of staying a
  per-repo exception) — not designed, `power-user-linux-setup`'s own `.vscode`/`uv.lock` false-alarm
  (found already-generic content sitting in a spot that looked local) suggests this pattern will
  recur.
- Per-tool `.gitignore` relationships and the community-convention exclude set — deliberately not
  answered here, see `repo-tasks/plans/2026-08-19-gitignore-tool-alignment.md` above.

### Retrofit path for existing repos

**Deferred by direct instruction (2026-08-19) — `scaffoldapy` needs to stabilize on fresh-repo
generation before `copier update` gets pointed at any already-existing, already-diverged repo.** Not
abandoned, just not now — revisit once `scaffoldapy` has some real fresh-generation mileage on it.
Required eventually, per §A's "no allowances" decision, once resumed: `olx-polite-mcp`/
`temu-polite-mcp`/`freshful-polite-mcp` all already have real code that will have diverged from
`repo-tasks`/the template; retrofitting each means adopting `repo-tasks` (§A) plus `src/` layout,
then `copier update` against `scaffoldapy` (exactly the direction Copier's update mechanism is built
for, not a manual re-diff by hand). `emag-polite-mcp`/`altex-polite-mcp` are still plan-only — they
pick up the template (with `repo-tasks` as a dependency from the start) once their implementation
actually begins, so no separate retrofit step for those two regardless of this deferral.

## Open questions — resolved 2026-08-18

Every question this section used to list is now resolved — see §A for the full design:

- **Naming**: `repo-tasks` (`pulse-dev-tasks` rejected — clashes with PulseAudio; `py-dev-tasks`
  rejected — too generic).
- **Composition**: no per-repo allowances — every consumer uses the exact same `fix`/`check`/
  `precommit` composite from the shared package, unmodified (an earlier leaf-tasks-only draft was
  considered and rejected). This also resolves the "should shell/type checks be optional per repo"
  question the leaf-tasks draft implied: no — they're unconditional, and the tasks themselves
  degrade gracefully instead (§A).
- **Config file location**: dedicated per-tool files (`ruff.toml`, `pyrightconfig.json`,
  `pytest.ini`), not `pyproject.toml` blocks — see §C0.
- **Package layout**: `src/`, not flat — see `skills/python-conventions`'s new "Package layout"
  topic.
- **Sequencing**: §A (the package) first, since §B (the template) depends on `repo-tasks` existing
  as a dev-dependency to seed. Still true, unchanged from the original framing.

One question remains genuinely open, not yet resolved: whether the shared package should eventually
also carry MCP-specific reusable pieces (robots.txt guard, rate limiter, disk cache — currently
`olx-polite-mcp/core/`) once a _second_ MCP repo needs them, or stay quality-tooling-only forever.
`olx-polite-mcp`'s own `AGENTS.md` already applies the relevant restraint to its own Playwright
fetch path ("generalize... only once a second site actually needs it") — the same principle likely
applies here, but not decided.

**Resolved 2026-08-19 — §B went further, as this note hoped:** `scaffoldapy` wires the
`[project.scripts]` entry point into `pyproject.toml` from day one for `mcp_server`/`cli`, and
pre-writes the `uv tool install`/`claude mcp add --scope user` "Installation" section into
`README.md`, chosen by the generated repo's actual `interface`. No `copier update`-safe registration
stub — `claude mcp add` itself isn't idempotent-safe to script blindly, left as a manual one-liner
per `mcp-skill-shipping`.

## Explicitly out of scope right now

§A (`repo-tasks`) and §B (`scaffoldapy`) are both built; §D (config distribution mechanism,
`repo_tasks.configs`) is designed but not yet implemented — see §D for the resolved design and its
own open questions. §C's config _content_ was already piloted with real code changes directly in
`power-user-linux-setup`'s own `tasks/quality.py`/`pyproject.toml`/`setup.toml`/`dprint.json`
(commit `c01b53c`, 2026-08-16/17) and §C0's file-location convention has since been applied to
`power-user-linux-setup` itself too — §D is what actually carries that content into `repo-tasks` as
the enforced canonical copy, superseding §C0's "copy by hand" framing. Still open: the retrofit pass
on `olx-polite-mcp`/`temu-polite-mcp`/`freshful-polite-mcp`, deferred by direct instruction until
`scaffoldapy` stabilizes on fresh-repo generation (see "Retrofit path" above), and the
still-genuinely-open question of whether `core/`'s politeness/cache/fetch primitives eventually move
into a shared package instead of being duplicated per generated repo.
