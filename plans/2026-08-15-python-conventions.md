---
status: landed
updated: 2026-08-17
---

# Python conventions across personal repos: typing, style, and design defaults

## Context

Same underlying motivation as `skills/db-defaults`: models and sessions drift toward different
"reasonable" choices for the same recurring decisions, so conventions across this repo family
(`power-user-linux-setup`, the `*-polite-mcp` repos, `product-research-pipeline`) end up
inconsistent even though there's no real disagreement about what's best — just nobody wrote the
default down. This plan is scoped to **language-level and design-level conventions** — the choices
an agent makes continuously while writing Python code (typing discipline, data modeling, control
flow, architecture, testing style) — not repo scaffolding
(`plans/2026-08-14-python-repo-scaffolding.md`) and not quality-tooling configuration, covered
below.

**Split from quality-tooling configuration (2026-08-17).** This plan originally also covered tool
_choice and config_ — which type checker, which ruff rules, shellcheck/shfmt, dprint's markdown
settings — alongside the design guidance. The user asked for these to become separate concerns:
design conventions are read continuously while writing code, tool config is applied once when a repo
is set up. That config content (basedpyright's tuned profile, the ruff select/ignore list,
shellcheck/shfmt, dprint's `textWrap` fix, and the full pilot-findings writeup from applying all of
it to this repo) moved to `plans/2026-08-14-python-repo-scaffolding.md`, whose own "shared
invoke-tasks package" / "repo template" pieces are exactly where that config already needs to live —
it wasn't a new third bucket, just a piece of an existing plan that hadn't been filled in yet. This
file keeps only the design/style guidance; the two plans cross-reference each other rather than
duplicating content.

Audience is explicitly both humans and coding agents, so — per Armin Ronacher's argument cited in
the tooling plan's typing section — **consistency of one opinion matters as much as which opinion is
"most correct"** in the several places reputable sources genuinely disagree with each other. This
plan surfaces those disagreements rather than hiding them, and records which way the user actually
decided, so the resulting skill (see "Design" below) has real citations behind it instead of
restating LLM training-data platitudes.

Ruff already governs mechanical style (formatting, import order, common bug patterns, now including
the rule-selection tuning documented in the scaffolding plan) — this plan deliberately doesn't
re-litigate anything ruff already enforces, only the structural/idiomatic choices ruff is silent on.

Seed topics, per the user's original list, explicitly not exhaustive ("we can start with those"):
general style, early returns/guard clauses, fail-fast, Pydantic vs dataclass vs NamedTuple vs
TypedDict, modularity/testability/DRY/readability/encapsulation, modules-as-singletons, properties
for lazy loading. Research also surfaced a topic the user hadn't listed but pulled in once flagged:
**settings/secrets management**.

Four research agents ran the primary pass (parallelized by cluster); follow-up passes covered
settings libraries, statelessness/immutability, a community-precedent check on the user's own
`globals.py` pattern, the FastAPI `@lru_cache` settings alternative, and a NamedTuple-vs-dataclass
decision rule, after the user's own answers and follow-up questions surfaced those gaps. Full
citation trails are kept below — this file is the durable record, not a scratch summary.

**Research retention, independent of this plan's own lifecycle** (explicit user instruction,
2026-08-16): this research "validates our ideas" and must survive regardless of how the plan itself
ends up being used — consolidated is fine, lost is not. Concretely: this file's citation trail
migrates into the `python-conventions` skill's own `references/rationale.md` as part of the same
build this promotion covers — see "Files touched" below.

## Design

### 1. Data modeling — Pydantic vs dataclass vs NamedTuple vs TypedDict vs attrs vs msgspec

**Decision: trim to as few default choices as possible.** The user's explicit ask — fewer options so
agents mimicking existing code have less room to pick the wrong one — overrides the general
[[feedback_best_tool_per_concern]] instinct here; the research below (attrs vs. Pydantic tradeoffs,
msgspec's speed) stays in the file as real, verified options, but only two are the routine default:

| Situation                                                                                                                 | Default                        |
| ------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| Parsing external/untrusted JSON (API responses, MCP tool args) + want auto JSON-Schema; also **all settings/config** (§2) | **Pydantic v2**, `frozen=True` |
| Everything else — internal structured data, function returns, records                                                     | **`@dataclass(frozen=True)`**  |

`frozen=True` is the default on both, not an occasional opt-in — see §6's immutability-preference
decision. `TypedDict` stays as a named exception, not a third default: reach for it only when the
value must genuinely remain a plain dict (already-parsed JSON being passed through unchanged,
`**kwargs`-shaped structures) rather than becoming an object. `attrs`, `NamedTuple`, and `msgspec`
are demoted from "pick one of six" to **documented escalation paths**, not part of the routine
choice:

- **attrs** — only if a concrete case needs validators/converters without Pydantic's
  validation+serialization bundling. The sharpest source found on this tradeoff:
  ["Why I use attrs instead of pydantic"](https://threeofwands.com/why-i-use-attrs-instead-of-pydantic/)
  — "Pydantic makes things that should be hard appear easy, and things that should be easy,
  frustratingly hard," arguing Pydantic's bundling causes surprising default behavior, while attrs'
  opt-in model is more composable (pairs with `cattrs`, kept separate from the model by design).
  Concedes Pydantic's default validation error messages are better, precisely because Pydantic
  validates by default where attrs requires opting in per field.
- **NamedTuple** — a frozen dataclass already covers "immutable record with named fields," so a
  follow-up pass researched exactly what's left for NamedTuple to be the _better_ choice for, given
  it's not just "the tuple-flavored option" anymore. Concrete decision rule, reach for NamedTuple
  over the frozen-dataclass default only when:
  1. **Drop-in positional-tuple compatibility is the actual requirement** — the value needs to
     interoperate with code that expects a plain `tuple` (stdlib's own `os.stat_result`/
     `sys.version_info`/`urllib.parse.urlparse()`'s `ParseResult` all do exactly this via
     `PyStructSequence`/`namedtuple`, specifically for backward-compatible positional access
     alongside named fields), a C extension expecting positional args, or `Row._make(csv_row)`-style
     construction from an existing iterable.
  2. **The record is small, closed, and order-_is_-the-meaning** — `x, y = point`,
     `key, group =
     pair` — not a multi-field "bag of results," which Effective Python (Slatkin)
     Item 31 argues against past 2 values regardless of container type: unpacking more than ~3
     variables is "all too easy to reorder... accidentally," and his own fix is a dataclass, not a
     NamedTuple.
  3. **Zero validation/behavioral needs** — NamedTuple subclasses genuinely **cannot add new
     fields** (verified against the `typing.NamedTuple` docs; subclassing only lets you add/override
     methods), and `__post_init__`-style validation requires overriding `__new__`, an awkward,
     easy-to-get-wrong pattern next to a dataclass's dedicated hook. Any real validation or
     field-adding-subclass need is an immediate dataclass signal.

  Hashability (works with zero config on both once `frozen=True`, verified against the dataclasses
  docs — `eq=True` + `frozen=True` auto-generates `__hash__`, so this is a non-differentiator now)
  and raw memory/speed (NamedTuple keeps a modest edge over even `slots=True` dataclasses, since
  it's tuple-native rather than slot-retrofitted, but the gap is small post-3.10 and not a
  legitimate deciding factor at this project's scale) were both checked and ruled out as deciding
  factors.
- **msgspec** — only once Pydantic's validation/serialization overhead is a _measured_ bottleneck,
  not a guess. Pydantic v2's Rust core (`pydantic-core`) is 4–50x faster than v1 depending on model
  shape — **any pre-2023 "Pydantic is slow" take is measuring v1** and should be discounted — but
  msgspec still wins on raw speed when it matters (10–20x faster decode, 5–60x faster struct
  operations per multiple 2025–2026 sources).

**Does Rust-core Pydantic close the gap with plain dataclass enough to widen its default scope
beyond boundaries?** A direct follow-up check, since the person raised it as a real "did our
reasoning stay current" question — answer: **no, and the reason it doesn't is itself informative.**
Every direct Pydantic-v2-vs-dataclass benchmark found (not vs. attrs/msgspec, which the table above
already covers) still shows dataclass ahead on the "just hold typed fields" comparison: ~2.6x faster
instantiation even on Python 3.13 after both CPython's own dataclass-codegen speedup _and_
pydantic-core's Rust rewrite; a maintainer-unaddressed Pydantic GitHub issue's own 1M-iteration
timeit shows plain attribute _writes_ ~50x slower on a Pydantic model; per-instance memory ~2.6x
larger (Pydantic instances carry `__dict__` plus `__pydantic_fields_set__`/`__pydantic_extra__`/
`__pydantic_private__` bookkeeping a dataclass never allocates). **The "Pydantic got faster"
narrative is real but scoped to validation/serialization throughput specifically** — every "5–50x"
figure in circulation is v2-vs-v1, i.e. Rust-validator-vs-Python-validator, and a frozen dataclass
never paid that Python-validator cost to begin with, so the Rust rewrite didn't touch the actual
axis that differentiates it from a dataclass for unvalidated internal data. No reputable source
found argues Pydantic should be a general internal-data default even post-Rust-core; the ones that
address this directly
(["Pydantic and Performance Spaghetti Code"](https://leehanchung.github.io/blogs/2025/07/03/pydantic-is-all-you-need-for-performance-spaghetti/),
coining "SerDes Debt" for exactly this anti-pattern) argue the opposite. **No change to the existing
split** — the case for `@dataclass(frozen=True)` internally rests on grounds the Rust core doesn't
address at all (zero validation-library coupling, full transparency, stdlib-only dependency weight),
not on a performance gap that's since closed.

### 2. Settings and secrets management

Not in the original seed list — the user flagged this gap explicitly and named `pydantic-settings`
as the candidate.

**pydantic-settings**: split out of Pydantic v1's built-in `BaseSettings` into its own
`pydantic`-org-maintained package for v2. Verified mechanics: typed `BaseSettings` subclass,
source-priority chain (CLI args → init kwargs → env vars → `.env` file(s), layerable → `secrets_dir`
→ field defaults), nested config via `env_nested_delimiter` or JSON, first-class TOML/
YAML/JSON/`pyproject.toml` sources, and genuine Docker/K8s-secret-mount support
(`SettingsConfigDict(secrets_dir=...)`, one file per field). `SecretStr` masks `repr()`/`str()` only
— genuinely prevents the common "stray `print(settings)` leaks a secret" accident, but
`.get_secret_value()` still returns the raw string, so it is **not** a full secrets-management
control; state this plainly wherever it's documented, since it's a common point of over-trust. ~488M
PyPI downloads/month (reflecting FastAPI's install base as much as direct adoption), commits
same-day as this research — lowest realistic maintenance-risk option checked.

**Contenders evaluated and rejected for this use case, not just unmentioned:**

- `python-dotenv` — `.env`-to-`os.environ` loader only, no typing/validation; pydantic-settings
  already uses it internally for `.env` parsing, so it's not a competing choice, just a dependency
  underneath the real choice.
- `environs` — typed env-var _casting_ (`env.int()` etc.) via a thin marshmallow wrapper, no model
  object, no native file-secrets support.
- `dynaconf` — the one genuine heavier alternative: layered multi-format, multi-environment
  (`[default]`/`[production]`/...) config with Vault/Redis-backed dynamic sources. Right choice the
  moment a repo needs a real dev/staging/prod config matrix or non-Python operators hand-editing a
  TOML file — **not** currently true for any repo in this family, so not the default, but the named
  escalation path.
- `python-decouple` — effectively stale (no commits in ~21 months as of this research); actively
  avoid given the explicit preference for low-maintenance-risk tooling.
- `Hydra` (Meta) — ML-experiment config composition (parameter sweeps, multirun) — high star count
  reflects dominance in that specific niche, not general applicability; explicitly out of scope
  here, named so its absence doesn't read as an oversight.
- `typed-settings` — technically interesting (backend-agnostic, 1Password integration) but
  GitLab-hosted with a tiny (33-star) footprint — essentially unadopted, not a serious contender.

**Decision: pydantic-settings as default; escalate to dynaconf only if a repo genuinely grows a
multi-environment deployment matrix.**

**The user's own already-in-use pattern, adopted as the concrete implementation shape:** a base
`Settings`/`Default` class (`pydantic_settings.BaseSettings` subclass) holding production-safe
defaults for every field; one subclass per non-prod environment overriding only the fields that
differ; a small piece of bootstrap code — wired at the very top of the package's `__init__.py`,
before anything else runs — reads an `ENVIRONMENT`-style env var and instantiates the matching
subclass once, assigning the instance to a module-level name (this is §5's modules-as-singletons
pattern, applied specifically to settings). `frozen=True` throughout, so once the correct
environment's settings load, nothing downstream can mutate config at runtime — the concrete
mechanism behind §6's statelessness/immutability decision. Because it's a plain class, not a
GoF-style Singleton, tests can freely construct an independent instance (any subclass, or the base
class with field overrides) rather than fighting shared global state — the same "Global Object
Pattern over class-based Singleton" reasoning §5 already covers. See §5 for community-precedent
validation of this composite pattern specifically (Flask's own long-documented
`Config`/`DevelopmentConfig`/`ProductionConfig` idiom is the closest established analogue found).

**The competing idea — FastAPI's own `@lru_cache`-wrapped factory pattern — researched in depth per
the user's explicit request ("I'm not entirely confident in my globals.py and init design"), and the
verdict is: don't adopt it, the eager pattern above is the better fit here.** FastAPI's docs
(`get_settings()` decorated with `@lru_cache`, consumed via `Depends()`) state their own rationale
directly: "reading a file from disk is normally a costly (slow) operation... we would be reading the
`.env` file for each request" if the factory weren't cached — an explicitly **per-request
amortization** argument. `@lru_cache` on a zero-argument function degenerates to a lazy singleton
(one possible cache key, `maxsize` is inert); the real distinguishing property is _lazy_
construction versus the `globals.py` pattern's _eager_ one. Three findings against adopting it here:

1. **The stated rationale doesn't transfer.** Neither a CLI tool (one invocation total) nor a
   well-behaved MCP server (settings should already only be read once regardless of pattern)
   reproduces the "N times per request" condition the whole argument depends on — it's solving a
   problem specific to a request-serving loop, which these applications don't have.
2. **The testability mechanism is genuinely framework-specific, confirmed from FastAPI's own
   source.** `app.dependency_overrides[get_settings] = ...` works because FastAPI's request-dispatch
   code (`solve_dependencies` in `fastapi/dependencies/utils.py`) explicitly consults that dict at
   call time — a real interception point that doesn't exist outside FastAPI. Without it, the
   portable equivalent is `get_settings.cache_clear()`, which is real and documented but has a
   genuine, sourced gotcha: it doesn't fix stale references anything already holds to the pre-clear
   instance — real enough that a dedicated pytest plugin (`pytest-antilru`) exists specifically to
   manage this. The `globals.py` pattern's isolation is structurally simpler: construct another
   instance, no cache to bust, nothing to go stale.
3. **Fail-fast timing favors eager.** A missing/invalid env var fails at _import_ time (before any
   application code runs) with the eager pattern, vs. at _first call_ time — possibly deep in a CLI
   subcommand or, worse, the first real client request in production — with the lazy one. This is
   this project's own already-decided §3 principle (fail fast at the earliest diagnosable point),
   and the eager pattern gets it for free; `@lru_cache` actively trades it away for a benefit
   (per-request amortization) that doesn't apply outside a request-serving context.

One real-world data point cited as corroboration, not proof: an independent, non-FastAPI MCP server
(`frontmatter-mcp`) that tried a similar lazy-cached-factory shape ended up hand-rolling its own
resettable cache with an explicit `reset_caches()` specifically once testability became a
first-class concern — someone hit the same friction and engineered around it rather than reaching
for `lru_cache` directly once outside FastAPI's dependency-override safety net.

### 3. Early returns / guard clauses, fail-fast, and the EAFP tension

**Guard clauses — the actual rule, not the folk version.** Fowler's _Refactoring_ (the origin,
"Replace Nested Conditional with Guard Clauses") draws an asymmetry test, not a blanket "flatten
everything" rule: if-then-else is right when both branches are equally likely/important; a guard
clause is right specifically when one path is the happy path and the other a rare, exceptional
early-out. **Using a guard clause to split two co-equal business branches destroys the signal the
construct is supposed to carry** — this is the single most load-bearing nuance to keep. PEP 8 never
mentions guard clauses, early return, EAFP, or LBYL at all (verified directly against the PEP text —
several web summaries claiming "PEP 8 endorses EAFP" are wrong). The closest thing to an official
Python endorsement is PEP 20's "Flat is better than nested" — a philosophy, not a rule.

**The EAFP/LBYL tension is real, not manufactured.** A guard clause is structurally LBYL — it looks
before it leaps. Python's own glossary calls out LBYL's race-condition risk directly (check-then-act
gap) and names EAFP as the culturally preferred style. The reconciliation that holds up: **guard
clauses validate a function's own contract** (did the caller uphold the API — argument types, value
ranges) — a different question than "will this specific runtime operation succeed," which is EAFP's
territory (dict/attr lookups, file I/O, network calls — things Python already knows how to fail
loudly on). Where sources disagree is how strictly to police that boundary; mainstream practice
(`requests`, `click`, the Google style guide) mixes both freely as long as the EAFP half catches
specific, narrow exception types.

**Fail-fast, concretely in Python:** `assert` = internal "can't happen" self-checks only — it is
compiled out entirely under `python -O`, confirmed via the Python wiki's own
"UsingAssertionsEffectively" page and the Google style guide, both independently. Anything
triggerable by bad input, external state, or another part of the system must `raise` a real
exception instead. Effective Python (Slatkin) Item 32 is the sharpest concrete tie to a real
anti-pattern: never return `None`/a sentinel/`(success, result)` tuple on failure — `None`, `0`, and
`""` are all falsy, so callers silently can't distinguish "legitimately empty" from "failed," and a
discarded tuple flag (`_, result = ...`) makes the failure invisible entirely.

**Custom exception hierarchies:** real precedent from `requests` and `click` — both shallow (2–3
levels), single library-wide root, sometimes multiply-inheriting a leaf from both the library's own
base _and_ the matching stdlib type (e.g. `requests.MissingSchema` also inherits `ValueError`) so
callers can catch at whatever granularity they need. No reputable named source found specifically
endorsing a _minimal_ version of this for personal-scale code — **this piece is closer to a
reasonable inference than a cited consensus**, so stated as one: one root exception per package
minimum, deeper leaves only once a caller actually needs to discriminate.

**Genuine minority dissent, not a strawman:** Nikita Sobolevn (maintainer,
`wemake-python-styleguide`),
["Python exceptions considered an anti-pattern"](https://sobolevn.me/2019/02/python-exceptions-considered-an-antipattern)
— argues exception-heavy EAFP code is itself a readability/correctness hazard (almost any line can
silently raise, no static way to see what runs after a catch), proposing explicit
`Result[Success, Error]` container types instead. Real standing, genuinely rejects mainstream EAFP
culture — not adopted here, but worth recording so it isn't silently "rediscovered" later and
treated as a regression from current practice.

### 4. Modularity, testability, DRY, readability, encapsulation

**Architecture lineage:** _Architecture Patterns with Python_ (Percival & Gregory, cosmicpython.com)
is the standard current Python-specific reference, built explicitly on three borrowed ideas:
Hexagonal/Ports-and-Adapters, Dependency Inversion, and Gary Bernhardt's **Functional Core,
Imperative Shell**. Their own opening line on DI: **"Dependency injection (DI) is regarded with
suspicion in the Python world."** Their prescription is not a DI framework but a manual
**Composition Root** — explicit wiring at the application entrypoint via closures/partials — because
monkeypatch-style mocking "couples tests tightly to implementation details."

**Clean Code / Clean Architecture (Robert C. Martin) — the Python-specific pushback is real and
documented**, not invented for balance:
["Why I can't recommend Clean Architecture by Robert C
Martin"](https://dev.to/bosepchuk/why-i-cant-recommend-clean-architecture-by-robert-c-martin-ofd)
(discussed on HN and Lobsters) argues Clean Architecture's abstract-interface-class machinery is "a
very common, and necessary tactic when using statically typed languages like Java and C#," but in
Python those interface classes and the dependencies that would target them don't need to exist at
all — duck typing already provides the decoupling. **The core idea (depend on abstractions, keep the
domain free of I/O concerns) survives; the Java-flavored mechanism doesn't fit and is rejected by
Python-specific voices.**

**Functional Core, Imperative Shell** — legitimate, live, actionable advice, not a dated pattern:
Google's own engineering blog revived it in Oct 2025 (Testing on the Toilet series). Fits
CLI-tool/data-pipeline-shaped code well (arguably this repo family); strains for code whose entire
job _is_ I/O orchestration (MCP servers) — there, Michael Feathers' "seams" vocabulary (a place to
alter behavior without editing code at that place, from _Working Effectively with Legacy Code_) is
the more applicable concept.

**DRY vs. its critiques — decision: lean toward duplication.** Fowler's older Rule of Three
(duplicate once freely, wince at twice, refactor on three, attributed to Don Roberts) is the
moderate position. Sandi Metz's sharper
"[The Wrong Abstraction](https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction)" — "duplication
is far cheaper than the wrong abstraction," inline a strained abstraction back out rather than patch
it with more parameters — is a Ruby-community citation with **no independently-argued
Python-authority echo found**, worth being honest about rather than dressing up as cross-language
consensus; it reaches Python circles by reference (e.g. via Kent C. Dodds' "AHA Programming" /
"Avoid Hasty Abstractions," which does the same move). "WET" as a backronym has **no verifiable
single coiner** — treat as crowd folklore, not a cited origin. **This decision matches the user's
existing [[feedback_best_tool_per_concern]] preference and was confirmed directly**: for
solo-maintained repos, a miscalibrated abstraction costs only the maintainer, but also has to
survive being correctly understood by an agent before it can be safely modified — a wrong
abstraction is _harder_ for an agent to safely touch than duplicated code, not easier.

**Readability:** PEP 8 itself (authored by Guido, Barry Warsaw, Alyssa Coghlan) states directly:
"code is read much more often than it is written," immediately followed by subordinating the style
guide itself to project-level consistency. **The commonly-cited "Knuth quote" on this topic is a
misattribution** — "programs are meant to be read by humans" is Abelson & Sussman (SICP preface),
not Knuth; Knuth's real, distinct contribution to this lineage is Literate Programming. Comment
philosophy ("why, not what") is already governed by this session's own global instructions
(`~/AGENTS.md`'s "default to no comments... only when the WHY is non-obvious"), not re-litigated
here — but worth noting the pushback exists: Hillel Wayne's
["The Myth of Self-Documenting Code"](https://buttondown.com/hillelwayne/archive/the-myth-of-self-documenting-code/)
argues some information (negative information — "we tried X, it broke because Y" — optimization
rationale, caller-facing gotchas) genuinely can't be inferred from clean code no matter how
well-named, so "self-documenting code" as an ideal is oversold. Consistent with, doesn't override,
the existing comment policy.

**Encapsulation:** Python has no real privacy. PEP 8, verbatim: single underscore is a "weak
'internal use' indicator" (affects `import *` only); double-underscore triggers name mangling for
**subclass attribute-collision avoidance**, not access control, and remains fully reachable via the
mangled name. "We're all consenting adults here" (Guido, via Python community/", _Python in a
Nutshell_") is the named cultural stance behind this. Effective Python (Slatkin) is more concretely
useful than the folklore: **Item 55, "Prefer Public Attributes over Private Ones"** — default to no
underscore; Items 58–59 — start with a plain public attribute, retrofit `@property` only once
validation/computed behavior is actually needed, since `@property` is transparent to callers and
requires no API change later. **Recommendation: internal helper modules public-by-default;
`__all__` + underscore discipline reserved for genuine package-public surfaces** (MCP tool
definitions, CLI entrypoints) — the point at which unknown external callers, not just future-you,
are reading the boundary.

### 5. Modules-as-singletons and lazy-loading properties — the `globals.py` pattern

**Modules-as-singletons is real, stdlib-endorsed practice**, not just a convenient accident: the
official
[CPython Programming FAQ](https://docs.python.org/3/faq/programming.html#how-do-i-share-global-variables-across-modules)
states directly that a module is the canonical way to share state, "because there is only one
instance of each module," and explicitly names this as the basis for implementing Singleton in
Python. Brandon Rhodes' python-patterns.guide sharpens this into the actually-useful form: prefer
"[The Global Object Pattern](https://python-patterns.guide/python/module-globals/)" — instantiate a
plain class once at module level — over a GoF class-based Singleton, specifically because **the
Global Object Pattern doesn't architecturally forbid a second instance**, which is exactly what
makes tests able to construct an independent, isolated object instead of fighting shared global
state. This is the precise shape of the `globals.py` pattern described: a class, one default
module-level instance, freely re-instantiable for tests.

**Validated against this family's actual code, not just the abstract pattern:** none of the
`*-polite-mcp` repos has a config/settings module today, but all three implemented ones
(`olx-polite-mcp`, `freshful-polite-mcp`, `temu-polite-mcp`) already use exactly this shape for
stateful managers — `_fetcher = PoliteBrowserFetcher()`, `_watch_state = WatchState()`,
`_product_cache = ProductCache()` at module level in each `server.py`. **The `globals.py`
settings-object pattern is a natural, consistent generalization of an already-established
convention, not a new direction being introduced.**

**Known pitfalls, documented so they're designed around rather than discovered later:**

- **Testing:** `monkeypatch.setattr` must target the _module attribute itself_
  (`monkeypatch.setattr(config_module, "X", value)`), not a name already pulled in via
  `from config import X` — a stale-alias trap confirmed across multiple independent sources.
  `importlib.reload()` is the documented heavier fallback for re-running a module's init from
  scratch, but leaves state changed for later tests unless explicitly reset — a fallback, not a
  default.
- **Circular imports:** Python registers a module in `sys.modules` before executing its body, so a
  cycle can leave a singleton only partially constructed when a peer module reads it mid-init.
  Standard mitigation: defer the import inside the function that needs it.
- **Multiprocessing:** singleton state does not survive process boundaries meaningfully — under
  `fork`, the child gets a point-in-time copy that then diverges silently; under `spawn` (default on
  macOS/Windows, increasingly recommended generally), the child re-executes module top-level code
  from scratch, independently re-initializing anything with construction-time side effects (opening
  a file, binding a port). A lock held at fork time can be copied in the _locked_ state without the
  thread that would release it — a real hang source if a singleton wraps anything lock-protected.
- **Concurrency correctness:** the official
  [free-threading guide](https://py-free-threading.github.io/testing/) states plainly that global
  mutable state relying on unstated GIL assumptions is not safe even under the classic GIL for
  compound operations (check-then-set, `+=`), and is a live forward-looking risk now that
  free-threaded builds are a real (if opt-in) option.

**`cached_property` — a genuinely version-sensitive fact for this repo family (targets 3.11+),
verified against current stdlib docs rather than assumed:** thread-safety semantics **changed
between Python 3.11 and 3.12**. Pre-3.12, `cached_property` had an undocumented per-property lock
guaranteeing the getter ran exactly once under concurrent first access (at the cost of lock
contention). **3.12 removed that locking entirely** — the getter can now run redundantly under
concurrent first access, which is a correctness change, not just a performance one, if the getter
isn't idempotent (appends to a shared list, opens a resource with a side effect, increments a
counter). Also confirmed: no built-in invalidation beyond `del instance.attr`; requires a mutable
`__dict__` (incompatible with `__slots__` unless `__dict__` is explicitly included, or unless
stacking `@property` on `@lru_cache` instead — the docs' own stated workaround).

**When lazy-loading via property is right vs. an anti-pattern — a real, named source, not an
inference:** the Google Python Style Guide states directly that properties "can hide side-effects
much like operator overloading," and that property behavior "must match the general expectations of
regular attribute access: that they are cheap, straightforward, and unsurprising." **Lazy-loading
via property is fine for expensive, side-effect-free computation** (the stdlib's own doc example:
`stdev` computed once from already-loaded, immutable data); **it's the wrong tool once the deferred
work has externally-visible side effects** (opening a DB connection, a network call) — an explicit
`.load()`/`.ensure_loaded()` method makes that cost visible at the call site, which a property by
construction cannot. (This specific explicit-method-vs-property contrast is reasoned from the Google
guide's stated principle, not independently sourced by name — flagged as the single weakest-
evidenced sub-point in this whole research pass.)

**Decision, confirmed with the user:** the `globals.py` pattern — a class instantiated once at
module level, `@property`/`cached_property` for lazy-loaded fields, freely re-instantiable with
different settings so tests can swap or recreate the object — is a sound, well-precedented default.
Document both live caveats alongside it wherever it's written up: the 3.11→3.12 `cached_property`
locking change, and "only lazy-load via property when the getter is idempotent/side-effect-free; use
eager `__init__`-time loading or an explicit method when it isn't."

**Community-precedent check on the composite settings pattern (§2), run at the user's explicit
request — an honest, mixed result, not inflated into false consensus.** The pattern decomposes into
five pieces with sharply differing precedent strength:

- **Base class + environment-specific subclasses + env-var-driven selection (pieces 1–3) — very
  strong precedent, but for Flask's older, non-Pydantic `Config` idiom.** Flask's own docs, fetched
  directly, have described this exact shape for over a decade:
  ["Configuration Handling"](https://flask.palletsprojects.com/en/stable/config/#development-production)
  — `class Config` → `ProductionConfig(Config)`/`DevelopmentConfig(Config)`/`TestingConfig(Config)`,
  each overriding only what differs, selected via `app.config.from_object()` driven by an env var.
  Django's `DJANGO_SETTINGS_MODULE` does the same job by swapping a whole _module_, not subclassing
  — confirmed genuinely different, a useful contrast rather than a competing endorsement. A real,
  independent, non-Flask precedent for the "class hierarchy auto-selected by an env var" mechanism
  itself exists in `django-classy-settings` (a real PyPI package doing exactly this for Django).
- **The Pydantic-specific version of the composite is real but thinly precedented — one tutorial
  lineage, not community consensus.** Three online sources (Teclado's FastAPI course, rednafi.com, a
  smaller blog) show near-identical `GlobalConfig`/`DevConfig`/`ProdConfig` code and naming,
  probably traceable to one common origin rather than independently invented three times. Neither
  pydantic-settings' own docs nor FastAPI's own docs recommend this composite — pydantic-settings'
  docs show layered `.env` files instead (`.env`, `.env.prod`, later overriding earlier), and
  FastAPI's own "Settings and Environment Variables" guide shows a flat `Settings` class behind an
  `@lru_cache`-wrapped factory function, not subclassing.
- **A genuine, worth-surfacing tension with FastAPI's own recommended pattern**: FastAPI's docs
  explicitly favor _lazy_ instantiation (`@lru_cache` factory, overridden via
  `app.dependency_overrides` in tests) over _eager_ module-import-time instantiation, and other
  sources describing the same idiom state the reason directly — "creating a global settings instance
  at module import time can limit flexibility, making it difficult to override settings during
  testing." This is a different mechanism solving the _same_ testability goal the `globals.py`
  pattern already solves a different way (a frozen-but-freely-constructible class, not a Singleton)
  — a legitimate design choice, not a flaw, but worth stating honestly as "not the way FastAPI's
  docs demonstrate" rather than implying it's the only correct approach.
- **`frozen=True` on `BaseSettings` — confirmed clean, no subclass-override conflict.** Pydantic's
  own docs confirm `frozen` blocks reassignment on an already-constructed instance; it has no
  interaction with a subclass declaring a different field _default_ at class-definition time, since
  that's a schema-building-time concern. A targeted search of Pydantic's own issue tracker for a
  documented conflict here came back empty — decent, not conclusive, evidence. The only real caveat
  found is narrow and tooling-only: some static type checkers need `frozen=True` redeclared
  explicitly on the subclass to recognize the inherited immutability, even though it holds at
  runtime regardless.
- **Plain class, not a GoF Singleton (piece 5) — directly, strongly validated**, and by an unusually
  authoritative source for this specific point: a pydantic-settings maintainer, on a GitHub issue
  requesting native Singleton support, **explicitly declined**:
  ["reconsider adding Singleton option for BaseSettings"](https://github.com/pydantic/pydantic-settings/issues/410)
  — "it is not `pydantic-settings`'s responsibility to care about singleton instance... adding a new
  config flag makes our configs more complex... and needs maintenance work as well." This is a
  direct, citable confirmation from the library's own team that keeping `BaseSettings` a freely
  re-instantiable plain class — exactly the Global Object Pattern reasoning above — is the
  deliberate design, not an oversight to work around.

**Net honest framing for the eventual skill writeup**: present this as _"Flask's fifteen-year-old
config-subclass idiom, reimplemented in Pydantic with stronger immutability guarantees,"_ not as
_"the standard Pydantic pattern"_ — the shape is excellent and well-precedented, the
Pydantic-specific combination is a reasonable, well-motivated synthesis rather than a copied best
practice.

### 6. Statelessness and immutability

Two new topics the user pulled in after the first pass, tightly related to §5's singleton pattern
and §1's `frozen=True` default.

**Statelessness — the canonical source says less than the word implies.** Twelve-Factor App, Factor
VI ("Processes"), Adam Wiggins/Heroku, 2011 —
[12factor.net/processes](https://12factor.net/processes) — fetched directly: "Twelve-factor
processes are stateless and share-nothing... any data that needs to persist must be stored in a
stateful backing service." Explicitly **not** "zero state, ever" — the process's memory/filesystem
"can be used as a brief, single-transaction cache," and the actual rule being enforced is that
nothing assumes a _future_ request/invocation is served by the _same_ process holding onto what an
earlier one left behind. Traces back further to Fielding's REST dissertation (2000): "session state
is therefore kept entirely on the client" — same shape, state relocated to an explicit place, not
banned outright. **Directly relevant same-week evidence in this exact tool family**: MCP's own spec
revision, SEP-2575 "Make MCP Stateless" (2026-07-28), removed the protocol-level session handshake —
and the writeup on it draws precisely the distinction this plan needs: **"stateless MCP does not
mean stateless software — application state must be explicit, addressable, and secured by the
application instead of hiding inside an MCP transport session."** The user's actual goal, and what
the research supports as the operative rule, is narrower and more useful than "no state anywhere":
**no _shared_, _hidden_ mutable state that a future request/process/test can't see coming** —
architecture-level (don't let a process assume its own memory outlives the request), not a ban on
any object anywhere holding data.

**Legitimate, source-acknowledged exceptions — not edge cases to explain away.** Caches, connection
pools, and rate limiters are the standard trio, and this project's own `db-defaults` skill research
already contains the sharpest example: a `time.monotonic()`-based rate limiter's entire job is
tracking "how many hits already happened in this window" — there is no stateless implementation of
rate limiting, full stop. The correct move per every source checked isn't eliminating this state,
it's making it explicit, scoped, and (if concurrent) protected — the free-threading porting guide's
own pitfall list (global config state, an ad-hoc dict used as a cache) is framed as "be aware and
guard this," not "eliminate all mutable state."

**Immutability mechanisms — one unifying gotcha across all of them.** `@dataclass(frozen=True)`,
Pydantic's `frozen=True`/`ConfigDict`, `NamedTuple`, `tuple`/`frozenset`, `types.MappingProxyType`,
and `Final`/`ClassVar` all share the same structural limit, confirmed independently for both
dataclasses and Pydantic: **freezing a container only freezes the container, never its contents** —
a frozen dataclass with a `list` field can't be reassigned, but `obj.items.append(x)` works fine.
`MappingProxyType` is a _view_, not a copy — mutating the underlying dict directly still shows
through it. `Final`/`ClassVar` have **zero runtime enforcement** — purely a static-checker contract,
confirmed directly from the typing spec ("there is no runtime checking of these properties"), which
is exactly why running a type checker in CI matters: without one actually running, `Final` is a
comment, not a guarantee (the scaffolding plan's basedpyright section is what makes that check
real).

**Why immutability matters — four distinct, separately-sourced arguments, not one vague appeal:**
thread/free-threading correctness (ties directly to §5's free-threading finding); easier reasoning
(no hidden mutation of arguments — the entire reason the shallow-freeze gotcha above is worth
documenting is that it violates this exact expectation); hashability (immutable types are required
for dict keys/set members — `list.__hash__` is deliberately `None` so a container's hash can't
silently change after insertion and corrupt the structure); and defensive-copying elimination (if a
value can't change, sharing it is behaviorally identical to copying it, so the copy becomes pure
overhead — a real, source-backed argument, not just asserted).

**Where blanket immutability doesn't fit Python — the real, Python-specific tension, not FP dogma
imported uncritically.** Python is mutable-by-default at the language level (lists, dicts, class
attributes) — the inverse of Haskell/Clojure/F#, where mutation is the opt-in case. Building up a
list incrementally in a `for` loop is Python-idiomatic, not an anti-pattern to route around with
`functools.reduce`/tuple-concatenation — a Python-specific FP-in-Python survey makes exactly this
point: "unless a mutation is involved a classic for loop is a good choice... you're not trying to
write Haskell in Python." **Practical resolution, and the one adopted here**: immutability is the
default for data/value objects crossing a boundary (function args, MCP tool payloads, config,
records — covered by §1's `frozen=True` default) — ordinary local mutation (loop accumulators,
building a result before returning it) stays conventionally mutable. This is the same functional-
core/imperative-shell split §4 already covers, applied one level down to individual objects rather
than whole modules.

**Third-party persistent-structure libraries (`pyrsistent`, stdlib-adjacent `immutables` — the
latter genuinely powers CPython's own `contextvars`, not a fringe library) — honest verdict:
overkill for this project family.** Both solve efficient repeated-modification of large, deeply-
nested collections (undo stacks, CRDTs) — not the shape of a config object, CLI arg record, or MCP
payload. `frozen=True` dataclasses/Pydantic + `tuple`/`frozenset` cover the vast majority of cases
here at zero extra dependency weight; reach for a persistent-structure library only against a
measured, not guessed, copy-cost problem on a large nested collection.

### 7. Testing conventions

**Fixture scope directly ties to §5's singleton-testing concern.** Official rule of thumb: narrowest
scope that keeps tests correct, widen only when setup is genuinely expensive; pytest's own docs warn
that a `monkeypatch` used inside a broad-scoped fixture stays live for the _whole_ scope, not just
one test — the exact mechanism by which a shared-scope fixture silently leaks state across tests
that look independent. **Practical rule for this repo family's module-singleton pattern**: construct
the expensive object at module/session scope, but reset/monkeypatch its _mutable_ state via a
function-scoped fixture — cheap construction stays shared, isolation stays per-test. `conftest.py`:
keep one root file for genuinely cross-cutting fixtures, split per-directory only once a real subset
of tests needs fixtures the rest shouldn't see. `parametrize`: attach `ids` once values stop being
self-explanatory. (Marker registration and `--strict-markers` are mechanical pytest _config_, not
design guidance — that lives with the rest of the tool-config decisions in
`plans/2026-08-14-python-repo-scaffolding.md`.)

**DAMP vs. DRY in tests — a real, sourced debate that does _not_ simply inherit §4's "lean toward
duplication" production-code stance.** Vladimir Khorikov's reframing (Enterprise Craftsmanship, and
echoed by Brian Okken) resolves the popular "DAMP not DRY" framing as a false dichotomy: DRY was
never about _code_ duplication, it's about not duplicating _domain knowledge_. The actionable split:
**setup mechanics (the "how") stay DRY** — pytest fixtures/helpers are exactly the right tool, use
them freely, no tension with anything else in this file — **but test bodies/assertions (the "what" —
the scenario being verified) should stay explicit and duplicated per test**, even when tests look
near-identical, because collapsing them into a shared abstracted mega-test trades away the "read one
test top-to-bottom, understand the scenario" property that's the actual point of a test suite. This
is a genuinely different axis from §4's production-code DRY decision, not a re-derivation of it —
worth stating explicitly in the skill so a reader doesn't assume "this project avoids DRY
everywhere" and over-apply it to test bodies.

### 8. Type hygiene

**`Any` / `# type: ignore` hygiene:** community-uncontested — scope ignores to a specific error code
(`# type: ignore[code]` / `# pyright: ignore[reportX]`) rather than blanket-silencing a line. Ruff's
`PGH003` (blanket-type-ignore) enforces exactly this mechanically — see the scaffolding plan's ruff
section for whether it's selected in a given repo; the convention itself holds regardless of whether
the lint rule is turned on.

The pre-existing "type everything, even snippets" precedent
([[feedback_type_everything_for_agent_precedent]]) still holds: annotate real code paths fully,
including throwaway example/snippet code, since agents pattern-match off existing precedent and an
untyped snippet reads as license to skip typing elsewhere. The basedpyright profile in
`plans/2026-08-14-python-repo-scaffolding.md` is how that precedent gets enforced without also
demanding annotation ceremony that doesn't catch bugs (see that plan for which rules are `error` vs.
left at the untyped-dependency default).

## Files touched

- `skills/python-conventions/SKILL.md` — decision-table-style entry point, one row/section per
  convention above, linking to the rationale and a runnable snippet.
- `skills/python-conventions/references/rationale.md` — this file's §1–8 citation trail, migrated in
  full (per the "research retention" note in Context — nothing here gets lost, only moved).
- `skills/python-conventions/references/snippets/*.py` — one example file per major pattern:
  `data-modeling.py` (dataclass vs. Pydantic vs. NamedTuple side by side), `settings.py`
  (`globals.py` + pydantic-settings environment-subclass pattern, `cached_property` caveat inline),
  `guard-clauses.py` (early-return/EAFP boundary example), `exceptions.py` (minimal hierarchy
  example), `testing.py` (fixture-scope + DAMP-vs-DRY example). Resolves the prior
  `[NEEDS CLARIFICATION: exact snippet set]` open question — grouped by theme (one file per major
  convention area), matching what the pre-promotion draft had already sketched for four of the five.
- `setup.toml` — new `[packages.python-conventions]` entry, `method = "skill"`, mirroring
  `db-defaults`/`plan-docs`.

## Verification

- `inv quality.fix` then `inv quality.check`: ruff clean ("All checks passed!"), dprint clean (120
  files already formatted), basedpyright 0 errors (2852 pre-existing warnings in `tasks/`/`tests/`,
  unrelated to this change — the new skill's `references/snippets/` is excluded from basedpyright by
  the same `exclude` entry that already covered `db-defaults`'), shellcheck/shfmt silent (clean),
  all 169 existing tests still passing. Confirmed 2026-08-17.
- `setup.toml`'s new `[packages.python-conventions]` entry mirrors `db-defaults`'/`plan-docs`'
  existing `method = "skill"` shape exactly — same pattern already proven to work with
  `inv ai.skills`.
- Spot-check: every cross-section `§N` reference in "Design" above points at the section it now
  claims to (renumbered during this promotion — mapping: old §2→1, §3→2, §4→3, §5→4, §6→5, §7→6,
  plus two new sections, 7 and 8). The three code-comment citations in `pyproject.toml` that pointed
  at this file's old §1/§4/§9 were updated in the same pass (§9→`python-repo-scaffolding.md` §C2,
  §4→this file's new §3, §1→`python-repo-scaffolding.md` §C1).

## Migrated to

- `skills/python-conventions/` — `SKILL.md` (decision table) + `references/rationale.md` (this
  file's full §1–8 citation trail, migrated verbatim) + `references/snippets/*.py` (5 runnable
  examples: `data-modeling.py`, `settings.py`, `guard-clauses.py`, `exceptions.py`, `testing.py`).
- `plans/2026-08-14-python-repo-scaffolding.md` — the quality-tooling half (basedpyright/ruff/
  shellcheck/dprint config + pilot findings), split out per the user's explicit request that design
  guidance and tool config become separate concerns.

Per `plan-docs`' retirement procedure: this file's durable content now has a permanent home (the
skill's own `references/rationale.md`, plus the scaffolding plan for the tooling half), so this file
is safe to delete in a follow-up pass once every repo reference to its path is confirmed updated —
not done in this same pass to keep the "Migrated to" section itself visible in git history first.

**Follow-up research pass, 2026-08-18 — landed directly in the skill, no separate plan-file stage.**
Before deleting this file, audited what else belonged in it: five more topics researched (four
parallel research agents against the actual `*-polite-mcp` sibling repos, not just docs) and written
straight into `skills/python-conventions/references/rationale.md` §9–13 and the matching `SKILL.md`
sections — MCP-stdio logging discipline, error handling at the MCP tool boundary, MCP tool
docstrings as an LLM-facing contract (distinct from PEP 257), async/concurrency conventions, and
HTTP client/ session/timeout/retry-backoff conventions. Three new snippets:
`references/snippets/mcp-tool-boundary.py`, `async-fanout.py`, `http-retry.py`. Also retrofitted a
**Model default** line onto every topic in `SKILL.md` (old and new), per explicit user request, so
the skill states plainly whether a topic overrides a model's own default instinct or just confirms
an already-sound one — the skill should steer, not fight normal agent behavior on things a capable
model already gets right. This pass had no plan-file stage of its own since this plan was already
`landed` and migrated before it started — the skill's `references/rationale.md` is the durable
record for it, the same role this file served for §1–8.
