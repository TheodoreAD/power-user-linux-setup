---
name: python-conventions
description: "Use when writing, reviewing, or refactoring Python code in a personal/agent-maintained project — data modeling (Pydantic vs dataclass vs NamedTuple vs TypedDict vs attrs vs msgspec), settings/secrets management, early returns/guard clauses/fail-fast/EAFP, modularity/DRY/readability/encapsulation, the module-singleton + lazy-property pattern, statelessness/immutability, test structure (DAMP vs DRY, fixture scope), exception hierarchies, and type-ignore hygiene. Gives the default answer per topic, researched against reputable sources and community precedent, so choices stay consistent across projects instead of drifting session to session. Covers design/style guidance only — for type-checker/linter/formatter/shell-check *tool configuration*, see plans/2026-08-14-python-repo-scaffolding.md instead."
---

# Python design and style defaults

Personal, agent-maintained Python projects. Applies when writing new code or reviewing existing code
against one of the topics below without an explicit "evaluate alternatives" request — pick the
default, don't re-litigate from scratch each session. Deviating is fine when a case genuinely
matches one of the named escalation paths — the point is to stop a fresh session/model from silently
picking something different for no reason, not to forbid judgment calls.

**This is design guidance, not tool config.** Nothing here tells you which type checker or linter to
install or how to configure it — that's `plans/2026-08-14-python-repo-scaffolding.md` (basedpyright,
ruff, shellcheck/shfmt, dprint, pytest config mechanics). This skill is what to reference _while
writing code_; that plan is what a repo's tooling enforces _once, at setup_.

## Data modeling

- Snippet: [`references/snippets/data-modeling.py`](references/snippets/data-modeling.py)
- Default: **Pydantic v2**, `frozen=True`, for anything parsing external/untrusted data (API
  responses, MCP tool args) or settings/config. **`@dataclass(frozen=True)`** for everything else —
  internal structured data, function returns, records.
- Why: two defaults, not six, so agents mimicking existing code have less room to pick the wrong
  one. Pydantic's Rust core closed the validation-speed gap with v1, but never closed the
  plain-attribute-access gap with a dataclass — the split isn't about which is "faster" in the
  abstract, it's boundary-validation vs. everything else.
- Escalate to: `attrs` (validators/converters without Pydantic's validation+serialization bundling),
  `NamedTuple` (drop-in positional-tuple compatibility, or a small closed record where order _is_
  the meaning — never past ~3 fields), `msgspec` (once Pydantic overhead is a _measured_
  bottleneck), `TypedDict` (value must genuinely stay a plain dict, not become an object).

## Settings and secrets management

- Snippet: [`references/snippets/settings.py`](references/snippets/settings.py)
- Default: `pydantic-settings`. Base `Settings` class with production-safe defaults, one subclass
  per non-prod environment overriding only what differs, an `ENVIRONMENT`-env-var-driven selector
  wired at the top of the package's `__init__.py`, assigned once to a module-level name.
  `frozen=True` throughout.
- Why: this is the module-singleton pattern (below) applied to settings — eager construction fails
  fast at import time, and a plain (non-Singleton) class means tests can freely construct an
  isolated instance instead of fighting shared global state.
- Escalate to: `dynaconf` — only once a repo genuinely grows a multi-environment deployment matrix
  (Vault/Redis-backed dynamic sources, non-Python operators hand-editing config).
- **Don't**: FastAPI's `@lru_cache`-wrapped settings factory, outside an actual FastAPI app. Its
  rationale (amortizing repeated `.env` reads across requests) doesn't transfer to a CLI tool or MCP
  server, its test-override mechanism is FastAPI-dependency-injection-specific, and it trades away
  fail-fast-at-import-time for a benefit that doesn't apply here. Full reasoning in the rationale
  doc.

## Early returns, guard clauses, fail-fast, and EAFP

- Snippet: [`references/snippets/guard-clauses.py`](references/snippets/guard-clauses.py)
- Rule: a guard clause is for the asymmetric case — one happy path, one rare exceptional early-out.
  Don't use one to split two co-equal business branches; that's a plain `if`/`else`. Guard clauses
  validate the _caller's contract_ (argument types/ranges); EAFP handles _runtime_ operations Python
  already fails loudly on (dict/attr lookups, I/O, network).
- Fail-fast: `assert` is for internal "can't happen" self-checks only (compiled out under
  `python
  -O`) — never for input validation. Anything triggerable by bad input or external state
  `raise`s a real exception. Never return `None`/a sentinel/`(success, result)` on failure — falsy
  values make "empty" and "failed" indistinguishable to the caller.
- Exception hierarchy: [`references/snippets/exceptions.py`](references/snippets/exceptions.py) —
  one root exception per package minimum, deeper leaves only once a caller actually needs to
  discriminate (2–3 levels, matching `requests`/`click`'s own shape).

## Modularity, testability, DRY, readability, encapsulation

- Default: lean toward duplication over premature abstraction (Fowler's Rule of Three: duplicate
  once freely, wince at twice, refactor on three) — a wrong abstraction is harder for an agent to
  safely touch than duplicated code, not easier.
- Architecture: Functional Core, Imperative Shell fits CLI/data-pipeline-shaped code well; strains
  for code whose entire job _is_ I/O orchestration (MCP servers) — reach for Michael Feathers'
  "seams" vocabulary there instead.
- Encapsulation: Python has no real privacy (PEP 8: single underscore is a "weak indicator," nothing
  more). Internal helper modules public-by-default; reserve `__all__` + underscore discipline for
  genuine package-public surfaces (MCP tool definitions, CLI entrypoints).

## Modules-as-singletons and lazy-loading properties

- Snippet: [`references/snippets/settings.py`](references/snippets/settings.py) (same pattern,
  generalized beyond settings)
- Default: instantiate a plain class once at module level (the `globals.py` pattern) —
  stdlib-endorsed
  ("[The Global Object Pattern](https://python-patterns.guide/python/module-globals/)"), not a GoF
  Singleton, so tests can freely construct a second, isolated instance. `@property`/
  `cached_property` for lazy-loaded fields, but only when the getter is idempotent and
  side-effect-free — an explicit `.load()` method otherwise, since a property can't signal cost at
  the call site.
- Caveats to keep in view: `cached_property`'s thread-safety guarantee (exactly-once under
  concurrent first access) was **removed in Python 3.12** — a correctness change if the getter isn't
  idempotent, not just a performance one. `monkeypatch.setattr` in tests must target the module
  attribute itself (`monkeypatch.setattr(config_module, "X", ...)`), not a name already pulled in
  via `from config import X`.

## Statelessness and immutability

- Default: `frozen=True` on data/value objects crossing a boundary (function args, MCP payloads,
  config, records) — the same default as the data-modeling table above, not a separate decision.
  Ordinary local mutation (loop accumulators, building a result before returning it) stays
  conventionally mutable; don't route around Python's own idioms to avoid it.
- Legitimate stateful exceptions, not edge cases to explain away: caches, connection pools, rate
  limiters. Make the state explicit, scoped, and (if concurrent) protected — not eliminated.
- One gotcha across every immutability mechanism: freezing a container only freezes the container,
  never its contents (`obj.items.append(x)` works fine on a frozen dataclass with a `list` field).
  `Final`/`ClassVar` have zero runtime enforcement — a type checker actually running is what makes
  them real (see the scaffolding plan's basedpyright config).

## Testing conventions

- Snippet: [`references/snippets/testing.py`](references/snippets/testing.py)
- Fixture scope: narrowest that stays correct. For the module-singleton pattern above — construct
  the expensive object at module/session scope, but reset its _mutable_ state via a function-scoped
  fixture. A `monkeypatch` inside a broad-scoped fixture stays live for the whole scope, not just
  one test — a real, silent cross-test leak source.
- DAMP vs. DRY — a different axis from the production-code DRY decision above, not a re-derivation
  of it: setup mechanics (fixtures/helpers) stay DRY, but test bodies/assertions stay explicit and
  duplicated per test, even when near-identical — collapsing them into a shared mega-test trades
  away "read one test top-to-bottom, understand the scenario."

## Type hygiene

- Scope `# type: ignore`/`# pyright: ignore` comments to a specific error code — never blanket-
  silence a line. Type real code fully, including throwaway example/snippet code — an untyped
  snippet reads as license to skip typing elsewhere to a pattern-matching agent.

## Full rationale

See [`references/rationale.md`](references/rationale.md) — the full citation trail: sources
consulted, options considered and rejected per topic, and the reasoning behind every branch/
escalation path above. Originally researched and written up in
`plans/2026-08-15-python-conventions.md`; migrated here once the plan promoted from `idea` to a
built skill (that plan file may since have been retired — check its own history if the path is
gone).

## Starter snippets

`references/snippets/` has one real, ruff-clean, self-contained Python file per pattern above — each
directly copy-pasteable rather than a tutorial to adapt. Each topic's "Snippet:" line above links
straight to its own file.

## Editing this skill

This file is _copied_, not symlinked, into `~/.agents/skills/python-conventions` by `inv ai.skills`
(`setup.toml`'s `[packages.python-conventions]`). Edit the source at
`power-user-linux-setup/skills/python-conventions/SKILL.md`, then re-run `inv ai.skills` to refresh
every project's copy — editing a deployed copy in place is local drift, the exact thing this skill
exists to prevent.
