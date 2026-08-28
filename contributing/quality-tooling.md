# Why the quality tools are configured the way they are

The canonical config files — `ruff.toml`, `pyrightconfig.json`, `pytest.ini`, `dprint.json`,
`.editorconfig` — live in [`repo-tasks`](https://github.com/TheodoreAD/repo-tasks) and reach this
repo through `inv configs.pull`. See [`repo-family-architecture.md`](repo-family-architecture.md)
for that distribution mechanism and which repo owns what.

This page is the reasoning behind the _content_ of those files: which tool was picked, which rules
are on and why, and the traps that only showed up when the config met real code. It exists so a rule
can be re-litigated on evidence rather than instinct, and so a new tool joining the set gets held to
the same bar. It is not something to copy by hand — `configs.pull` is.

The research below was done against real, actively-maintained OSS configs (Home Assistant, Litestar,
Pydantic, httpx, kubernetes, bats-core) rather than rule-category descriptions, and then piloted
directly on this repo before anything was written into something other repos would inherit. The
pilot is where most of the value came from; every "gotcha" section below is something the literature
review had no way to surface.

Design and style conventions — data modeling, exception hierarchies, test structure, type-ignore
hygiene — are a different concern and live in the `python-conventions` skill, authored in
[`agent-skills`](https://github.com/TheodoreAD/agent-skills). This page is tool configuration only.

## Each tool gets its own config file, not a `pyproject.toml` block

`ruff.toml`, `pyrightconfig.json`, `pytest.ini` — never `[tool.ruff]`/`[tool.basedpyright]`/
`[tool.pytest.ini_options]`. The reason is distribution, in the user's own framing: consolidating
every tool's config into `pyproject.toml` makes template-driven updates across many repos "very
difficult and risky", because that file also carries each repo's own `[project]` metadata,
dependencies and build config mixed in with the tuned tool settings. A dedicated file can be diffed
or replaced wholesale without touching anything repo-specific sitting next to it.

All three tools prefer the dedicated file natively when both are present, so this is a location
change only. `dprint.json` already worked this way.

## Type checking: basedpyright, `recommended` — not `strict`

The four real contenders as of Aug 2026, none of them a consensus winner: **mypy** (incumbent,
deepest ecosystem, lowest typing-spec conformance at ~58% in one third-party run, slowest),
**pyright** (mature, highest install base via Pylance, ~95–98% conformance), **pyrefly** (Meta, 1.0
in May 2026, best speed+conformance combination, smallest troubleshooting footprint), and **ty**
(Astral, fast and ecosystem-aligned, but still pre-1.0 by its own maintainers' versioning signal).

**basedpyright** is a fork of pyright that closes two real gaps: several editor-facing features
(inlay hints, semantic highlighting, docstring completions) exist only in Microsoft's closed-source
Pylance, licensed for VS Code alone, and basedpyright reimplements them so any editor gets parity;
and plain pyright's CLI ships only via npm, an awkward fit for a pure-Python/uv toolchain, where
basedpyright publishes a normal PyPI package bundling its own Node runtime. It tracks upstream
within 0–2 days — confirmed from commit history, not the docs' framing — so it is a superset rather
than a diverging fork. The real caveat, worth naming rather than omitting: single-maintainer
bus-factor risk against Microsoft's institutional backing of plain pyright. No source treats it as a
current problem.

**`recommended`, not `strict`**, and this corrects the obvious first instinct. `strict` mode does
**not** enable most of basedpyright's own exclusive bug-catching rules — `reportAny`,
`reportUnreachable`, `reportImplicitStringConcatenation` and `reportIgnoreCommentWithoutRule` all
default to `"none"` under `strict` (or `"hint"`, which is invisible to a CLI-driven agent loop
entirely), because those rules were wired into `recommended`/`all` rather than retrofitted into the
older `strict` ladder. Picking the tier that sounds more rigorous would have silently missed exactly
the three bug classes this profile exists to catch.

**The tuned profile itself is not documented here.** `repo-tasks`'
[`contributing/type-checking.md`](https://github.com/TheodoreAD/repo-tasks/blob/main/contributing/type-checking.md)
owns it — per-directory strictness tiers, every rule level that deviates from `recommended`, the
`invoke-stubs` distribution, `failOnWarnings`, and what was rejected — and it is current where this
page's research is not. Two of the original pilot's conclusions have since been reversed there on
better evidence: `failOnWarnings` is `true` again (flipped 2026-08-25, once every repo in the family
had reached zero warnings), and `allowedUntypedLibraries: ["invoke"]` turned out to be moot rather
than load-bearing — invoke ≥2 ships `py.typed`, and the setting only acts on names imported _from_
invoke, so an unannotated `c` was never associated with it at all. Annotating `c: Context` was the
actual fix. Read that page, not this one, before changing a rule level.

**Dissent worth keeping in view, not adopting.** Armin Ronacher's
["Untyped Python: The Python That Was"](https://lucumr.pocoo.org/2023/12/1/the-python-that-was/) and
["In Support Of Shitty Types"](https://lucumr.pocoo.org/2025/8/4/shitty-types/) argue that
fragmented, disagreeing type checkers actively hurt LLM coding agents, because models struggle when
tools disagree on what counts as an error — his conclusion is that _consistency_ of one checker's
opinion matters more than maximal strictness. Unusually on-point for this family's agent-heavy
workflow, and exactly why "pick one checker, one config, stop arguing" is the right shape of
decision even though "strict" is not universally endorsed.

### Two traps the upstream page does not cover

**Setting `exclude` replaces basedpyright's default exclude list — it does not add to it.** The
default includes `**/.*`, which is how `.venv` gets skipped with zero config. Adding
`exclude = ["reference"]` for a vendored-repos directory silently un-excluded `.venv` too: the first
run reported 16,009 errors from typeshed and third-party packages inside the virtualenv. Repeat the
defaults (`**/node_modules`, `**/__pycache__`, `**/.*`) alongside whatever you add. The family's
config sidesteps this entirely now by anchoring `include` and carrying no `exclude` at all, but the
behavior is still there for anyone who adds one.

**`cast(SomeTypedDict, x)` fails the "sufficient overlap" check when `x` is a concrete
`dict[str, Any]`** — `tomllib.load()`'s real return type — even though the same cast succeeds when
`x` is genuinely `Any`, as with `json.loads()`. basedpyright's own message names the fix: route
through `object` first, `cast(SomeTypedDict, cast(object, x))`.

One superseded finding, kept because the _shape_ recurs: `reportImplicitStringConcatenation` at
`"error"` was pure noise on this codebase — all 52 hits were the routine convention of wrapping one
long string literal across parenthesized lines, not one missing-comma bug. Ruff's `ISC001` has the
identical conflict with the formatter and is disabled for the same documented reason. The rule sits
at `"none"` family-wide now. The generalizable part: a rule that reads as obviously-correct in a
rule table can still be a pure false-positive generator against a codebase's real style, and only
running it tells you which.

## Ruff

**An explicit `select` list is additive-only — it does not inherit the zero-config default.** Ruff's
default already includes `F`, `E`, `B`, `UP` **and `RUF`** (Ruff's own family: mutable
class-attribute defaults, `noqa` hygiene, f-string pitfalls), so a repo with an explicit `select`
gets none of `RUF` unless it is listed. This repo genuinely had zero `RUF` coverage before the
pilot.

**`C901`/mccabe needs `C90` in `select` or its setting is inert.** Default `max-complexity` is 10,
tracing to McCabe's original "anything beyond 10 is too complex". Pydantic's own `pyproject.toml`
sets `[tool.ruff.lint.mccabe] max-complexity = 14` and never adds `C90` — the setting does nothing
there. Check for the identical trap whenever complexity gets tuned.

Per-category verdicts, against four real flagship configs. None of the four selects every category;
narrow hand-picked selections are the actual norm:

- **Add**: `PERF` (low-noise real inefficiency catches, selected by Home Assistant and Pydantic),
  `A`/flake8-builtins (near-zero-noise shadowed builtins), `DTZ`/flake8-datetimez (naive
  `datetime.now()`, a real timezone-bug class).
- **Add, non-`PLR` subset only**: `PL`/pylint. Every surveyed config that touches `PL` carves out
  the `PLR*` refactor-suggestion codes — Mozilla's removed "nearly 2000 warnings" by disabling
  `PLR0913`/`0911`/`0912`/`0914`/`2004` outright, and Ruff's `PLR0913` counts `self`/`cls` toward
  its argument limit without exempting overrides. Keep `PLC`/`PLE`/`PLW`, drop `PLR`. Confirmed on
  real hits here: `PLR0912`/`2004`/`0913`/`0917`/`0911`/`0915` all fired on ordinary
  CLI-task-handler code.
- **Add, then triage**: `TRY`/tryceratops. Home Assistant selects it but ignores `TRY003` (long
  exception messages) and `TRY400`. A minimal exception hierarchy — this family's own convention —
  makes `TRY003` actively fight the design rather than merely nag. Turn it on, see what fires,
  decide ignores from real signal.
- **Skip, or scope away from tests**: `ARG`/flake8-unused-arguments. None of the four flagship
  projects select it, likely because it collides with interface-conformance overrides and with
  pytest fixtures taken purely for a side effect (`monkeypatch`) — exactly this family's testing
  style.
- **Skip, cherry-pick at most**: `N`/pep8-naming. No surveyed project selects the whole category;
  the two that touch it pick 3–4 codes. Full-category fights external-API-shaped names.
- **Skip**: `FBT`/flake8-boolean-trap. A real footgun with a good argument behind it, but none of
  the four select it and it has known friction with CLI-framework decorators (click/typer positional
  boolean flags) — relevant, since this family includes CLI tools. Treat as judgment, not a lint
  rule.
- **`T20`/flake8-print does not fit an invoke-shaped repo at all.** 460 hits here, essentially the
  whole `tasks/` tree. The research verdict ("exempt the CLI-output entrypoint module") assumed a
  library with a few genuine output modules; here every `@task` function prints status as its
  primary interface, so there is no minority to exempt — printing _is_ the product. Good fit for
  library code where a stray `print()` really is leftover debug output; wrong for a CLI-tool repo.

**No official Ruff "recommended baseline" ladder exists**, basedpyright-style — confirmed, no
curated tier is published. Ruff's own _default_ jumped from 4 categories to 413 rules across 34
categories in v0.16.0 (2026), which is exactly the broad-default posture a hand-picked `select` opts
out of.

Two pilot findings worth carrying:

- **`PLW1510` (subprocess-run-without-check) was a genuine catch, not noise.** 12 `subprocess.run()`
  calls repo-wide with no explicit `check=`. Every one turned out to be a deliberate "probe and
  inspect `.returncode`", several documented as such — so the fix was making existing behavior
  explicit with `check=False`, not adding `check=True` anywhere. The rule's value was forcing the
  choice; reading each site rather than blanket-fixing is the select-then-triage workflow in
  practice.
- **`reportUnusedVariable`-style findings surfaced real test-coverage gaps.** Four tests unpacked a
  `_diff_nodes()` return value (`new_invalid`) and never asserted on it — in tests specifically
  about whether a node avoids being routed there. Fixed by adding the missing assertions, not by
  prefixing with `_`.

Pre-existing hits that were deliberately _not_ refactored — 15 `C901` complexity hits on ordinary
multi-branch task handlers, and 5 `A001`/`A002` builtin-shadowing hits (`dir`/`all`, which _are_ the
real `--dir` flag and `inv <ns>.all` subcommand names) — were recorded with `ruff check --add-noqa`.
That leaves named, greppable (`rg "noqa: C901"`) deferred work rather than either ignoring the rule
wholesale or forcing a same-session mass refactor of working automation code.

## pytest and dprint

**pytest**: marker registration via `markers = [...]` plus `--strict-markers`, matching Litestar's
and httpx's own configs.

**dprint's `textWrap` is easy to get backwards, and its default is buggy.** Markdown plugin defaults
are `line_width = 80` and `text_wrap = "maintain"`, and `maintain` has an open documented bug — it
can delete newlines inside linked or inline-code text
([dprint-plugin-markdown#149](https://github.com/dprint/dprint-plugin-markdown/issues/149)) — so the
value is worth setting explicitly regardless of style preference.

`"never"` is the trap, verified the hard way: it does not mean "leave wrapping alone", it means
dprint will never _insert_ a line break in prose, which collapses hand-wrapped paragraphs into
single giant lines. `"always"` is what enforces consistent hard-wrapping. It needs a
markdown-specific `lineWidth` (this family uses 100), deliberately left un-unified with ruff's
120-char code width: `ruff format` never auto-wraps docstring or comment prose regardless of
`line-length`, so a docstring can already run to 120 with `E501` flagging it and nothing fixing it —
a pre-existing, orthogonal inconsistency this decision did not try to resolve.

Beyond routing around the bug, hard-wrapping has one concrete checkable win: diff and merge-conflict
locality, since a one-sentence edit does not reflow the whole paragraph. The human-vs-agent
readability claim has only thin sourcing and is not what the decision rests on.

## Shell scripts: shellcheck + shfmt, inside invoke

**shellcheck is a real standard, not an asserted one** — ~40k stars, pre-installed on GitHub
Actions/Travis/CircleCI/Codacy runners per its own README, bundled into GitHub's `super-linter`,
used in CI by kubernetes (`hack/verify-shellcheck.sh`, version-pinned) and bats-core. Google's Shell
Style Guide recommends it "for all scripts, large or small". Nothing competes at comparable scope:
`bashate` is PEP8-style with far lower adoption, `shellharden` rewrites toward shellcheck
conformance (complementary), `checkbashisms` covers a narrow POSIX-portability subset.

Severity tiers work like ruff's selection knob: `error` > `warning` > `info` > `style`, everything
shown by default, `--severity=warning` suppressing the bottom two. The community norm on disabling
checks — inferred from precedent rather than one canonical statement — is to scope narrowly and say
why: kubernetes names exactly three globally-excluded codes with inline reasons (`SC1090`/`SC1091`
for heavily-used non-constant `source`, `SC2230` for a deliberate `command -v` preference). A root
`.shellcheckrc` is where any exclusion belongs, each with its reason inline. This repo needed none.

**shfmt is the formatting counterpart** — shellcheck does not reformat at all, so a consistent-style
story needs both, the same two-tool split as `ruff check` + `ruff format`. The pairing is observed
practice, not assumed: `jumanjihouse/pre-commit-hooks` bundles both for exactly this reason. Its
indent style lives in `.editorconfig` (which shfmt reads natively) rather than a flag baked into a
shared task: 2-space indent per shfmt's own README recommendation and the dominant real-world
convention, with `switch_case_indent` and `space_redirects` on — near-unanimous among projects that
configure this at all. `binary_next_line`/`keep_padding`/`function_next_line`/`simplify` are genuine
taste calls with no dominant convention and stay off, present as commented toggles.

**No `pre-commit` framework.** It is genuinely how most real projects wire these two together, but
adopting it here would mean a second task runner, a second config format and a second mental model
for "how do I run checks", sitting next to `invoke`, which already solves "aggregate multiple
quality tools behind one command" for ruff and dprint. Duplicating a solved problem is the wrong
trade. Both tools fold into the same `check`/`fix`/`precommit` graph, run over `fd -e sh` output,
degrading cleanly to a no-op on a repo with zero `.sh` files — which is what lets the composite stay
mandatory with no per-repo opt-out.

**Install via `uv-tool`, never `apt` or a hand-run `uv tool install`.** `shellcheck-py` and
`shfmt-py` are PyPI wheels bundling the real prebuilt upstream binaries. The reasoning changed
mid-pilot and is worth keeping: first from a system package to a venv-portable CI-friendly one, then
— once it was clear shell scripts are not Python-project-specific — from a project dev-dependency to
a machine-wide `uv-tool`, installed through this repo's own declarative pipeline (`setup.toml` +
`inv python.install-tools`). A manual `uv tool install` "defeats the purpose of this setup".

The precedent check that settled machine-wide-vs-project-scoped, since it recurs for any non-Python
tooling: **Rust's is unambiguous** — `rustup`/`cargo` have no system-wide install path at all,
`clippy`/`rustfmt` are `rustup component`s installed per-user by design. **Go's is mixed** — `gofmt`
ships with the toolchain, but for `golangci-lint` the maintainers steer people away from
`go install` toward a pinned binary download, because `go install` compiles against whatever Go
happens to be present so the resulting binary is not the one that was tested. That is a
reproducibility concern, not a scope one, and it does not transfer: a prebuilt-binary wheel is
already the pinned upstream release. Net: user-scoped tool management is the stronger precedent.
