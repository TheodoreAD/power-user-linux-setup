---
name: python-conventions
description: "Use when writing, reviewing, or refactoring Python code in a personal/agent-maintained project — data modeling (Pydantic vs dataclass vs NamedTuple vs TypedDict vs attrs vs msgspec), dates/times/timezones (aware-only, UTC at the boundary, DST folds and gaps), settings/secrets management, early returns/guard clauses/fail-fast/EAFP, modularity/DRY/readability/encapsulation, the module-singleton + lazy-property pattern, statelessness/immutability, test structure (DAMP vs DRY, fixture scope), exception hierarchies, type-ignore hygiene, `src/`-layout package structure, async/concurrency, and HTTP client/retry
  conventions — plus MCP-server-specific conventions (stdio logging discipline, tool-boundary error handling, LLM-facing tool docstrings) for the *-polite-mcp family. Gives the default answer per topic, researched against reputable sources and community precedent, so choices stay consistent across projects instead of drifting session to session. Each topic notes whether it overrides a model's own default instinct or just documents an already-sound one, so the skill steers rather than fights normal agent behavior. Covers design/style guidance only — for type-checker/linter/formatter/shell-check *tool configuration*, see power-user-linux-setup's contributing/quality-tooling.md instead."
---

# Python design and style defaults

Personal, agent-maintained Python projects. Applies when writing new code or reviewing existing code
against one of the topics below without an explicit "evaluate alternatives" request — pick the
default, don't re-litigate from scratch each session. Deviating is fine when a case genuinely
matches one of the named escalation paths — the point is to stop a fresh session/model from silently
picking something different for no reason, not to forbid judgment calls.

**This is design guidance, not tool config.** Nothing here tells you which type checker or linter to
install or how to configure it — that's `power-user-linux-setup`'s `contributing/quality-tooling.md`
(basedpyright, ruff, shellcheck/shfmt, dprint, pytest config mechanics), with `repo-tasks`'
`contributing/type-checking.md` for the tuned basedpyright profile. This skill is what to reference
_while writing code_; those are what a repo's tooling enforces _once, at setup_.

**Each topic below states whether it's overriding your own default instinct or just confirming
one.** A capable model already gets a lot of this right without being told — early returns, EAFP for
runtime lookups, reasonable async code, `pathlib` over `os.path`. This skill isn't trying to
relitigate those; it exists for the choices where a model left alone drifts (six equally-plausible
data-modeling options, a DRY instinct that over-abstracts, a settings pattern borrowed from the last
framework seen in training data) or where a convention is genuinely non-obvious/project-specific
rather than general Python knowledge (the `globals.py` singleton shape, MCP's stdio stdout
constraint). Each **Model default** line below says which case you're in — skim past the ones that
just confirm what you'd already do, weight the ones that don't.

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
- Model default: **overrides.** Left alone, a model mixes Pydantic/dataclass/TypedDict/NamedTuple
  inconsistently across a codebase depending on what it last saw — there's no strong single default
  instinct here to confirm.

## Dates, times, and timezones

- Default: **aware datetimes only, normalised to UTC at every boundary.** Reject a naive datetime
  where it enters, never coerce it, and `astimezone(UTC)` everything you store or compare. Convert
  to a local wall clock only at the point of display. `zoneinfo` for zones (stdlib since 3.9), never
  `pytz`.
- Why: **two aware datetimes that share a non-UTC `tzinfo` subtract and compare on their wall
  clock**, silently ignoring any DST transition between them. A "24 hour" trailing window spans 23
  real hours across spring-forward; a six-hour minimum interval between two doses elapses an hour
  early. Worse, near a fold `==` and `-` disagree — an ambiguous datetime and its own UTC equivalent
  subtract to exactly zero while comparing unequal — so any branch on instant equality is wrong.
  Normalising on the way in is what makes every later comparison mean elapsed time. Measured live
  2026-08-27 in `ingesta`, where both failures were real and neither was visible by reading the
  code.
- Resolving a local wall time: `fold` (PEP 495) is the whole API, and each case needs a stated
  policy rather than whatever `replace(tzinfo=...)` happens to do. Detect by comparing **offsets,
  not datetimes** — intra-zone comparison ignores `fold`, so the datetimes compare equal either way.
  `wall.replace(tzinfo=z, fold=0).utcoffset() < ...fold=1...` means the time is _nonexistent_ (a
  spring-forward gap); `>` means _ambiguous_ (a fall-back). Then choose deliberately: round-tripping
  a gap time through UTC shifts it past the gap, and `fold=0` takes the first occurrence of an
  ambiguous one.
- Testing: DST correctness needs **known-answer tests at real transitions**, expected instants
  worked out by hand and asserted literally. A property test restates the implementation and passes
  straight through this bug. Normalise in the test helpers too — a property test computing
  `anchor - duration` on zone-aware values has the bug itself and will report correct code as
  broken, which is exactly what happened before the helpers were fixed.
- **Don't**: `datetime.utcnow()` — it returns a _naive_ datetime and is deprecated since 3.12; use
  `datetime.now(UTC)`. Don't store a float timestamp to sidestep the problem either: an aware UTC
  datetime is the value, not an encoding of it. ruff's `DTZ` ruleset catches the naive-construction
  half of this automatically and none of the same-zone-arithmetic half.
- Model default: **overrides.** Models use `astimezone`/`ZoneInfo` correctly in isolation but do not
  default to normalising at the boundary, and reliably write same-zone arithmetic that is wrong only
  across a transition — invisible to review, and to every test that doesn't sit on a DST boundary.

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
- Model default: **overrides.** A model trained heavily on FastAPI examples defaults toward the
  `@lru_cache` factory pattern, not this one — the eager base+subclass+env-selector shape is a
  specific chosen idiom, not what falls out naturally.

## Early returns, guard clauses, fail-fast, and EAFP

- Snippet: [`references/snippets/guard-clauses.py`](references/snippets/guard-clauses.py)
- Rule: a guard clause is for the asymmetric case — one happy path, one rare exceptional early-out.
  Don't use one to split two co-equal business branches; that's a plain `if`/`else`. Guard clauses
  validate the _caller's contract_ (argument types/ranges); EAFP handles _runtime_ operations Python
  already fails loudly on (dict/attr lookups, I/O, network).
- Fail-fast: `assert` is for internal "can't happen" self-checks only (compiled out under
  `python -O`) — never for input validation. Anything triggerable by bad input or external state
  `raise`s a real exception. Never return `None`/a sentinel/`(success, result)` on failure — falsy
  values make "empty" and "failed" indistinguishable to the caller.
- Exception hierarchy: [`references/snippets/exceptions.py`](references/snippets/exceptions.py) —
  one root exception per package minimum, deeper leaves only once a caller actually needs to
  discriminate (2–3 levels, matching `requests`/`click`'s own shape).
- Model default: **mostly confirms.** Early-return style and EAFP-for-runtime-lookups are already
  close to default behavior; the real add is the guard-clause/co-equal-branch nuance and the
  never-return-None-on-failure rule, which models don't reliably self-apply.

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
- Model default: **overrides, actively.** A model asked to "clean up" or even just implementing a
  feature proactively tends to extract shared helpers/abstractions on sight — this is the section
  most likely to be fought against if skipped, not a minor nudge.

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
- Model default: **overrides.** A model reaches for dependency injection, a class-based Singleton,
  or a per-call instantiation before it reaches for a bare module-level instance — this pattern is
  idiosyncratic to this project family, not a common default.

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
- Model default: **overrides.** Models don't default to `frozen=True` — mutable-by-default matches
  Python's own language default, so this is a deliberate opt-in a model won't reach for unassisted.

## Testing conventions

- Snippet: [`references/snippets/testing.py`](references/snippets/testing.py)
- Fixtures first, always. Any setup a test needs — a tmp tree, a fake `HOME`, a stubbed `c.run`, a
  constructed object, a monkeypatched env — is a `pytest` fixture (in `conftest.py` once two files
  want it), not lines hand-rolled at the top of each test body. Two reasons, and the second is the
  bigger one: it removes the mechanical duplication, and it **surfaces when the suite is doing the
  same thing three different ways** — three hand-rolled versions of "make a fake repo" hide in three
  test bodies indefinitely; three fixtures named `fake_repo`, `tmp_repo`, and `repo_dir` sit next to
  each other in `conftest.py` and get merged. Reach for the built-ins (`tmp_path`, `monkeypatch`,
  `capsys`, `caplog`) before writing a helper that reimplements one. A helper _function_ is the
  fallback only for setup that needs per-call arguments a fixture can't take — and even then, a
  fixture returning a factory (`make_repo(name)`) usually fits.
- Fixture scope: narrowest that stays correct. For the module-singleton pattern above — construct
  the expensive object at module/session scope, but reset its _mutable_ state via a function-scoped
  fixture. A `monkeypatch` inside a broad-scoped fixture stays live for the whole scope, not just
  one test — a real, silent cross-test leak source.
- DAMP vs. DRY — a different axis from the production-code DRY decision above, not a re-derivation
  of it: setup mechanics (fixtures/helpers, the _how_) stay DRY; the scenario a test verifies (the
  _what_) stays explicit and readable top-to-bottom in that test. `parametrize` is the sanctioned
  everyday tool for a real input→expected matrix, and is _more_ explicit than N copy-pasted bodies,
  because the varying values are isolated from the fixed logic — attach `ids` once values stop being
  self-explanatory. The line: **if adding a case means adding a value, parametrize; if it means
  changing the test's logic (a branch, a different setup, a different assertion), write a new
  test.** What's actually warned against is collapsing genuinely different scenarios into one
  branching mega-test, or hiding the scenario inside a helper whose name doesn't say what it
  asserts.
- Model default: **mostly confirms, overrides in one direction.** A model parametrizes value
  matrices unprompted, and that's right. What it does _not_ reliably do is promote setup to fixtures
  — left alone it inlines the same three-line arrange block into every test it writes, which is the
  "same thing three ways" failure above. The other narrow override: the modularity section's
  abstraction instinct can leak into folding scenarios that differ in _logic_ into one
  parametrized-with-branches test, or into a `check_*` helper that owns the assertion.
- Never run a code-mutating command as part of a test's exercised behavior unless the test's actual
  subject is that mutation. A fix/format/autocorrect command run before the assertion silently masks
  the exact defect a check-only equivalent would have caught. Confirmed live 2026-08-23 in
  `scaffoldapy`: an e2e test ran `inv quality.precommit` (fixes formatting, _then_ checks) against a
  freshly generated repo — real CI runs the check-only `inv quality.check` with no such gate, so a
  dprint markdown-wrapping bug in the generated `README.md`/`SKILL.md` passed this test while
  failing every generated repo's actual first CI run. Prefer the check-only/dry-run form of a
  command in a test unless the mutation itself is under test.
- Model default: **overrides.** A model reaches for the "full" fix-then-check invocation of a
  quality/build tool by habit (it's the everyday command, and "make sure everything's clean" reads
  as the safe choice) — this entry blocks that instinct in tests specifically, where it silently
  narrows what the test can catch.

## Type hygiene

- Scope `# type: ignore`/`# pyright: ignore` comments to a specific error code — never blanket-
  silence a line. Type real code fully, including throwaway example/snippet code — an untyped
  snippet reads as license to skip typing elsewhere to a pattern-matching agent.
- Model default: **mostly confirms.** Scoped ignores are already close to default behavior; "type
  even throwaway snippets" is the real add — the shortcut a model takes when told "just a quick
  example."
- **Testing a type rather than a value:** `assert_type` compares the declared type _exactly_, and a
  function type carries its parameter names — a decorated task body is `(c: Context) -> None`, which
  no `Callable[[Context], None]` expression can spell, so `assert_type` can never match it. Don't
  read that as the assertion failing; it is the precision doing its job. Use an annotated assignment
  instead (`body: Callable[[Context], None] = obj.body`), which still fails if the type degrades to
  `Any` (via `reportAny`) or becomes some other concrete callable. Note that such assertions are
  checked by the type checker and are no-ops at runtime, so say so in the file — a green pytest run
  is not evidence about any of them.
- Model default: **overrides.** Reaching for `assert_type` is the natural first move for "prove this
  type is what I think", and its exactness is easy to misread as a broken assertion rather than a
  precise one.

## Package layout: `src/` over flat

- Default: any installable/importable package in this family uses `src/<pkg_name>/`, not a flat
  `<pkg_name>/` at repo root. A repo's own `tasks.py`/`tasks/` invoke entrypoint isn't a package and
  stays flat at repo root regardless — every repo in this family has one, it's never installed or
  imported elsewhere, and this convention governs the thing that gets built into a wheel and
  imported, not that repo's own tooling scripts. (Confirmed live 2026-08-19 on
  `power-user-linux-setup` itself: its `tasks/` holds ~25 modules of repo-specific invoke tasks, not
  a distributable library — moving it under `src/` would also collide with invoke's own
  `FilesystemLoader`, which walks upward from cwd for a literal `tasks.py`/`tasks/__init__.py` and
  never consults an installed copy.)
- Why: a flat layout lets `pytest`/an import silently resolve to the _uninstalled, cwd_ copy of the
  package instead of what's actually installed (Python puts the cwd first on the import path) —
  masking real packaging bugs (a missing sub-package, an unincluded resource file) until a real user
  installs it. `src/` makes the project root itself un-importable, so both a test run and an
  editable install are forced through the same path a real install goes through. See
  `references/rationale.md` §14 for the full PyPA/Hynek Schlawack citations.
- Escalate to: nothing — this is the default, not an escalation path. A pure script never meant to
  be installed/imported elsewhere (a one-off notebook, `tasks.py` itself) is out of scope for this
  convention entirely, not an exception to it.
- Model default: **overrides.** Flat layout (package directory directly at repo root) is what most
  quick/tutorial code — and most models, absent instruction — default to; `src/` is a deliberate
  opt-in.

## Async and concurrency

- Snippet: [`references/snippets/async-fanout.py`](references/snippets/async-fanout.py)
- Default: plain `def`, not `async def`, for MCP tool functions — FastMCP already dispatches sync
  tools onto a thread pool (`anyio.to_thread.run_sync`), giving real concurrency for free, and 100%
  of this family's existing tool code is sync. For genuine fan-out code (an orchestrator calling
  several MCP clients concurrently), default to `asyncio.TaskGroup`, not `asyncio.gather()` — it
  cancels sibling tasks on the first uncaught exception where `gather()` leaves them running
  orphaned. Reach for `gather(return_exceptions=True)`-style partial tolerance only via a per-child
  `try`/`except` _inside_ a `TaskGroup`, not bare `gather`.
- Why: `gather()`'s siblings-keep-running-after-a-failure behavior is a real resource leak for a
  deliberately throttled/session-holding "polite" client — one site erroring shouldn't leave other
  sites' rate-limited calls or browser sessions running unobserved.
- Escalate to: `asyncio.Semaphore` to cap concurrent in-flight calls at a fan-out layer — a
  different axis from a per-site rate limiter (concurrency count vs. request spacing), compose both
  rather than picking one. If a sync call is unavoidable inside `async def` code,
  `asyncio.to_thread()` is the stdlib escape hatch (the same mechanism FastMCP already uses
  internally for sync tool dispatch).
- **Don't**: run a blocking call (`time.sleep()`, a `threading.Lock`-based throttle, a sync HTTP
  call) directly inside `async def` code — it freezes the entire event loop for its duration, not
  just the calling task.
- Model default: **partial.** Models write async syntax correctly; the specific choice of
  `TaskGroup` over `gather`, and the sync/async tool-function boundary FastMCP imposes, aren't
  something a model infers without being told the framework's actual dispatch mechanism.

## HTTP client, sessions, timeouts, and retry/backoff

- Snippet: [`references/snippets/http-retry.py`](references/snippets/http-retry.py)
- Default: `httpx` for any new plain-HTTP fetch path (requests-compatible API, safer default
  timeouts, async-ready). One `Client`/`Session` per fetcher instance, constructed once and reused
  for its lifetime — never a new connection per request. An explicit, site-tuned timeout on every
  request, regardless of client. `tenacity` for retry/backoff: exponential with jitter, scoped to a
  narrow retryable-status set (429/502/503/504) and transient network exceptions, never plain 4xx
  "real answers" like 404/403 — and honor a response's `Retry-After` header when present, in
  preference to the computed delay.
- Why: connection reuse and conservative, `Retry-After`-respecting retry aren't just performance —
  they're direct service to a "polite," rate-limited client's actual mission; retrying aggressively
  or opening a fresh connection per request is antithetical to it.
- Escalate to: nothing — this is the default, not an escalation path. Existing working code using
  `requests` isn't something to churn to httpx without a concrete driving need (see Modularity's
  lean-toward-duplication stance).
- **Don't**: assume any HTTP client's own built-in retry covers HTTP-level conditions — httpx's/
  requests' built-in retry is connection-level only; a 503 or a `Retry-After`-bearing 429 needs an
  actual retry library or hand-rolled logic layered on top. If a rate limiter's throttle call wraps
  a retried function, the retry must happen _inside_ the throttled call, not around it, or a slow
  retry's backoff sleep holds the site-wide rate-limit lock too.
- Model default: **mostly confirms, one real gap.** Models already default to setting a timeout and
  reusing a session/client; they do _not_ reliably default to jittered (vs. plain
  linear/exponential) backoff or to honoring `Retry-After` — the retry-scoping specifics are the
  real add here.

## MCP-stdio logging discipline

_Scope: stdio-transport MCP servers only (the `*-polite-mcp` family) — not applicable to
`power-user-linux-setup` itself, which has no MCP server._

- Snippet: [`references/snippets/mcp-tool-boundary.py`](references/snippets/mcp-tool-boundary.py)
- Default: never a bare `print()` in server package code. Route all logging through the stdlib
  `logging` module, explicitly configured to write to stderr at startup (or defer to FastMCP's own
  `configure_logging()`, which already defaults there).
- Why: the MCP stdio spec is unambiguous — a server **MUST NOT** write anything to stdout that isn't
  a valid MCP message; a single stray `print()` or a dependency's stdout-bound log handler corrupts
  the JSON-RPC stream. stderr is the sanctioned outlet for everything, logs included.
- **Don't**: trust that "no `print()` in my code" is sufficient — a dependency that logs to stdout
  on its own initiative isn't caught by explicit stderr configuration of your own logging. The
  robust check is exercising the real stdio transport end-to-end, not code review alone.
- Model default: **overrides — sharply, not a style nudge.** This is protocol-specific knowledge a
  model has no general-Python reason to know; without it, a model reaches for `print()` debugging
  exactly as it would in any other script, silently breaking the server.

## Error handling at the MCP tool boundary

_Scope: stdio-transport MCP servers only, same as above._

- Snippet: [`references/snippets/mcp-tool-boundary.py`](references/snippets/mcp-tool-boundary.py)
- Default: at the point an internal exception is about to cross back to the client, decide
  deliberately what's safe to expose — either re-raise as `fastmcp.exceptions.ToolError` with an
  explicit, hand-written message, or let a plain exception raise (FastMCP's default already surfaces
  it, unmasked, to the client). Never assume `str(exc)` of an arbitrarily caught exception is safe
  by default, especially inside a broad per-item `except Exception` (a legitimate pattern for
  isolating one bad item in a batch call — just don't let its caught exception's message reach the
  client unreviewed).
- Why: FastMCP's default (`mask_error_details=False`) already includes full exception detail in the
  client-facing response — this isn't an opt-in risk, it's the out-of-the-box behavior. The same
  shape as this skill's `SecretStr` caveat: a broad safety switch doesn't sanitize text you
  deliberately choose to expose.
- **Don't**: flip `mask_error_details=True` project-wide as a blanket fix — it suppresses
  legitimately useful validation detail (a bad argument, a batch-size violation) that plain
  `raise ValueError(...)` call sites rely on being visible to the calling agent. Prefer the
  finer-grained per-message `ToolError` choice.
- Model default: **overrides.** A model doesn't know `ToolError` exists or that FastMCP unmasks
  exceptions by default unless told — without this, it either leaves exceptions to propagate as-is
  (today's actual state in this family) or reaches for a blanket masking flag, both worse than the
  deliberate per-boundary choice.

## MCP tool docstrings

_Scope: any function decorated as an MCP tool (`@mcp.tool()` in this family). A genuinely distinct
concern from general docstring style — no general docstring-content rule exists elsewhere in this
skill to extend._

- Default: write the docstring to Anthropic's tool-definition bar, not PEP 257's — what the tool
  does and how it differs from its nearest sibling by name, when to use/not use it, where each
  non-obvious parameter's value comes from, response shape/size caveats, **at least 3–4 sentences,
  more for a complex tool**. See `references/rationale.md` §11 for the concrete template and this
  family's own strongest real examples.
- Why: the docstring becomes the wire-level `Tool.description` an LLM client reads at inference time
  to decide whether/how to call the tool — a weak one causes wrong-tool-picked, wrong-arguments, or
  never-invoked failures, a correctness cost paid by every future call, not a comprehension-speed
  one the way a weak human-facing docstring is.
- Escalate to: `Annotated[x, Field(description=...)]` for per-parameter descriptions once free-form
  prose isn't enough (so the JSON-Schema `inputSchema` itself carries them); `annotations=`
  (`readOnlyHint`/`destructiveHint`/etc.) on any tool with real side effects, since clients use it
  to decide when to skip or require confirmation prompts.
- Model default: **overrides.** A model's default docstring instinct is PEP 257's — a concise
  one-line summary — which is actively worse here; the entire point of this section is that the bar
  for an LLM-facing description is different from, not a stricter version of, ordinary docstring
  style.

## Full rationale

See [`references/rationale.md`](references/rationale.md) — the full citation trail: sources
consulted, options considered and rejected per topic, and the reasoning behind every branch/
escalation path above. §1–8 were originally researched and written up in
`plans/2026-08-15-python-conventions.md`, migrated here once that plan promoted from `idea` to this
built skill (the plan file has since been retired — see git history if you need it). §9 onward
(async/concurrency, HTTP/retry, the MCP-specific sections, and `src/`-layout) were researched
directly against this skill after that promotion, with no separate plan-file stage.

## Starter snippets

`references/snippets/` has one real, ruff-clean, self-contained Python file per pattern above — each
directly copy-pasteable rather than a tutorial to adapt. Each topic's "Snippet:" line above links
straight to its own file.

## Editing this skill

This file is _copied_, not symlinked, into `~/.agents/skills/python-conventions` by
`inv ai.install-skills` (`setup.toml`'s `[packages.python-conventions]`). Edit the source at
`power-user-linux-setup/skills/python-conventions/SKILL.md`, then re-run `inv ai.install-skills` to
refresh every project's copy — editing a deployed copy in place is local drift, the exact thing this
skill exists to prevent.
