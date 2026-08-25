# Full rationale — Python design and style defaults

Full citation trail behind [`../SKILL.md`](../SKILL.md)'s decision table. Researched across multiple
passes (four parallel research agents on the first pass, several follow-ups pulled in by later
questions) against reputable sources, real OSS project configs, and community precedent — this file
is the durable record, not a scratch summary, so sources are kept rather than compressed away.
Originally written up in `plans/2026-08-15-python-conventions.md`; migrated here once that plan
promoted from `idea` to this built skill.

For type-checker/linter/formatter/shell-check _tool configuration_ (a different concern — applied
once at repo setup, not referenced while writing code), see
`plans/2026-08-14-python-repo-scaffolding.md` instead, particularly its "Quality-tooling
conventions" section.

## 1. Data modeling — Pydantic vs dataclass vs NamedTuple vs TypedDict vs attrs vs msgspec

**Decision: trim to as few default choices as possible.** The user's explicit ask — fewer options so
agents mimicking existing code have less room to pick the wrong one — overrides the general
best-tool-per-concern instinct here; the research below (attrs vs. Pydantic tradeoffs, msgspec's
speed) stays in the file as real, verified options, but only two are the routine default:

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
     `key, group = pair` — not a multi-field "bag of results," which Effective Python (Slatkin) Item
     31 argues against past 2 values regardless of container type: unpacking more than ~3 variables
     is "all too easy to reorder... accidentally," and his own fix is a dataclass, not a NamedTuple.
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
beyond boundaries?** Answer: **no, and the reason it doesn't is itself informative.** Every direct
Pydantic-v2-vs-dataclass benchmark found (not vs. attrs/msgspec, which the table above already
covers) still shows dataclass ahead on the "just hold typed fields" comparison: ~2.6x faster
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

## 2. Settings and secrets management

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

## 3. Early returns / guard clauses, fail-fast, and the EAFP tension

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

## 4. Modularity, testability, DRY, readability, encapsulation

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
existing best-tool-per-concern preference and was confirmed directly**: for solo-maintained repos, a
miscalibrated abstraction costs only the maintainer, but also has to survive being correctly
understood by an agent before it can be safely modified — a wrong abstraction is _harder_ for an
agent to safely touch than duplicated code, not easier.

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

## 5. Modules-as-singletons and lazy-loading properties — the `globals.py` pattern

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

**Net honest framing**: present this as _"Flask's fifteen-year-old config-subclass idiom,
reimplemented in Pydantic with stronger immutability guarantees,"_ not as _"the standard Pydantic
pattern"_ — the shape is excellent and well-precedented, the Pydantic-specific combination is a
reasonable, well-motivated synthesis rather than a copied best practice.

## 6. Statelessness and immutability

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
application instead of hiding inside an MCP transport session."** The operative rule, narrower and
more useful than "no state anywhere": **no _shared_, _hidden_ mutable state that a future
request/process/test can't see coming** — architecture-level (don't let a process assume its own
memory outlives the request), not a ban on any object anywhere holding data.

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
comment, not a guarantee (see the scaffolding plan's basedpyright section for what makes that check
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

## 7. Testing conventions

**Fixture scope directly ties to §5's singleton-testing concern.** Official rule of thumb: narrowest
scope that keeps tests correct, widen only when setup is genuinely expensive; pytest's own docs warn
that a `monkeypatch` used inside a broad-scoped fixture stays live for the _whole_ scope, not just
one test — the exact mechanism by which a shared-scope fixture silently leaks state across tests
that look independent. **Practical rule for this repo family's module-singleton pattern**: construct
the expensive object at module/session scope, but reset/monkeypatch its _mutable_ state via a
function-scoped fixture — cheap construction stays shared, isolation stays per-test. `conftest.py`:
keep one root file for genuinely cross-cutting fixtures, split per-directory only once a real subset
of tests needs fixtures the rest shouldn't see. `parametrize`: attach `ids` once values stop being
self-explanatory.

**DAMP vs. DRY in tests — a real, sourced debate that does _not_ simply inherit §4's "lean toward
duplication" production-code stance.** Vladimir Khorikov's reframing ("DRY vs DAMP in Unit Tests",
Enterprise Craftsmanship) resolves the popular "DAMP not DRY" framing as a false dichotomy: "the DRY
principle should be applied to the how-to's, whereas the DAMP principle should be applied to the
what-to's." The actionable split: **setup mechanics (the "how") stay DRY** — pytest fixtures/helpers
are exactly the right tool, use them freely, no tension with anything else in this file — **but the
scenario a test verifies (the "what") stays explicit in that test**, because collapsing genuinely
different scenarios into a shared abstracted mega-test trades away the "read one test top-to-bottom,
understand the scenario" property that's the actual point of a test suite. This is a genuinely
different axis from §4's production-code DRY decision, not a re-derivation of it — worth stating
explicitly so a reader doesn't assume "this project avoids DRY everywhere" and over-apply it to test
bodies.

_Citation check, 2026-08-25 (the now-retired
`plans/2026-08-22-damp-vs-dry-testing-convention-revisit.md`)._ An earlier wording here said
Khorikov's split was "echoed by Brian Okken" and that test bodies "stay duplicated per test, even
when tests look near-identical" — both over-extrapolated, read against the sources. Khorikov's
article never mentions parametrized/data-driven tests at all; its example of misapplied DRY is
shared mutable state (class fields) and an arrange step hidden in a setup method, not a data table.
Okken (Test & Code ep. 160, "DRY, WET, DAMP, AHA", 2021 — transcript in
`okken/testandcode_transcripts`) does not cite Khorikov and is explicitly "on the fence" about the
DAMP-for-tests framing; his own stated rule is readability-first with one standard for production
and test code, and he names parametrization as a sanctioned tool: "if there is duplication,
parameterization, fixtures, and helper functions are great to clean that duplication up, but only if
you can still read the test quickly and understand it." His book's parametrization chapters exist
precisely to replace near-identical repeated test functions. So the sourced position is _not_
"duplicate bodies even when near-identical" — it's "keep the _what_ visible." `parametrize` over a
pure input→expected matrix keeps the _what_ more visible than N copy-pasted bodies (the varying
values are isolated from the fixed logic), so it's expected, not tolerated. The dividing line the
skill now states comes from the pytest-community formulation (Simply The Test, "Keeping DRY or
staying DAMP? When to parametrize tests", 2019): _"If a value needs to be changed to add a new case,
parametrize. If logic needs to be changed to add a new case, create a new test."_ The thing actually
warned against is a parametrized test that branches on its parameters, or a `check_*` helper that
owns the assertion — those hide the scenario; a data table doesn't. The three sources are mirrored
in `$RESEARCH_HOME/pages/testing-dry-vs-damp/` (see the `research-library` skill).

**Fixtures wherever possible — a stated preference of this repo family's owner (2026-08-25), not
just a sourced default.** The "how" side of the split above is not merely _allowed_ to be DRY; it
should be, via `pytest` fixtures specifically. Beyond removing duplication, the argument that made
it a rule is discoverability: setup hand-rolled inside test bodies has no name and no shared
location, so a suite can accumulate three different ways of doing the same thing (three fake-repo
builders, three env-patching idioms) with nothing that ever puts them side by side. Fixtures give
each piece of setup a name and a home (`conftest.py`), which is exactly what makes the duplication
visible and mergeable. This is consistent with every source above — Okken's own list of duplication
cleanups is "parameterization, fixtures, and helper functions" — and with Khorikov's DRY-the-how; it
just makes the fixture the default form of the "how" rather than one option among helpers.

## 8. Type hygiene

**`Any` / `# type: ignore` hygiene:** community-uncontested — scope ignores to a specific error code
(`# type: ignore[code]` / `# pyright: ignore[reportX]`) rather than blanket-silencing a line. Ruff's
`PGH003` (blanket-type-ignore) enforces exactly this mechanically — see the scaffolding plan's ruff
section for whether it's selected in a given repo; the convention itself holds regardless of whether
the lint rule is turned on.

The pre-existing "type everything, even snippets" precedent still holds: annotate real code paths
fully, including throwaway example/snippet code, since agents pattern-match off existing precedent
and an untyped snippet reads as license to skip typing elsewhere. The scaffolding plan's
basedpyright profile is how that precedent gets enforced without also demanding annotation ceremony
that doesn't catch bugs.

## 9. MCP-stdio logging discipline

**Scope: stdio-transport MCP servers only** (the `*-polite-mcp` family) — not
`power-user-linux-setup` itself, which has no MCP server and no stdio-framing constraint.

**The spec is unambiguous, fetched directly, not inferred.** MCP specification, stdio transport page
(2026-07-28 revision) —
[modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)
— quoted verbatim: "The server **MUST NOT** write anything to its `stdout` that is not a valid MCP
message. The server **MAY** write UTF-8 strings to `stderr` for any logging purposes." All of stdout
is reserved, not just framing bytes — a stray `print()`, a dependency's own
`logging.StreamHandler()` wired to stdout, or a traceback printed instead of raised all corrupt the
JSON-RPC stream.

**FastMCP (`fastmcp==3.4.7`, this family's pinned version) already defaults its own logging to
stderr — corroborated across independent secondary sources (a GitHub issue thread, unaffiliated blog
posts), but a first-party doc page/source fetch could not be completed during this research (the
FastMCP GitHub org transferred `jlowin/fastmcp` → `PrefectHQ/fastmcp` mid-pass, breaking several
URLs) — treat as reliable, not as a verbatim citation. The framework protects itself by construction
but doesn't document the _why_, and doesn't guard a server author's own code or dependencies.

**Ground truth against the sibling repos: no violation today, but no guard either.** Zero `print()`
calls inside any `*_polite_mcp/` package proper (the only hits are in standalone dev/ops scripts —
`recapture_fixtures.py`, `spike_cdp.py`, `login.py`, `recover_session.py` — never imported by
`server.py`, never run as part of the stdio process). Zero `logging`/`basicConfig`/`StreamHandler`
imports anywhere across all three repos — correctness today rests on "nobody happened to write
`print()` in `server.py` yet," not on any enforced convention.

**Decision: never call bare `print()` in package code** (the existing standalone-dev-script category
is fine as-is — those never run inside the stdio process). **Route all logging through the stdlib
`logging` module, explicitly configured to stderr at server startup**
(`logging.basicConfig(stream=sys.stderr, ...)`, or defer to FastMCP's own `configure_logging()`/
`get_logger()`, which already defaults there) rather than leaving it unconfigured and implicit.
State the caveat plainly wherever this lands: explicit stderr configuration protects code this
project owns, not a third-party dependency that writes to stdout on its own initiative — the only
fully robust check is exercising the real stdio transport end-to-end (MCP Inspector, or a real
client round-trip), not code review alone.

## 10. Error handling at the MCP tool boundary

**Scope: stdio-transport MCP servers only**, same as §9.

**FastMCP has a documented, structured mechanism, fetched directly from
[gofastmcp.com/servers/tools](https://gofastmcp.com/servers/tools).** `ToolError` (from
`fastmcp.exceptions`) is the sanctioned channel: its message reaches the client unmodified,
"regardless of the `mask_error_details` setting." **The load-bearing, easy-to-miss fact: FastMCP's
default already unmasks plain exceptions.** A tool that raises a standard
`ValueError`/`TypeError`/... without `ToolError` has its full exception detail included in the
client-facing response by default (`mask_error_details=False`) — not something a repo opts into by
skipping a setting, the out-of-the-box behavior. `mask_error_details=True` converts non-`ToolError`
exceptions to a generic message, but `ToolError` messages still pass through even with masking on —
it's the explicit "this text is safe to show" channel, masking is the "don't show anything else"
channel.

**This has the identical shape to §2's `SecretStr` caveat, not a new kind of problem.**
`mask_error_details=True` protects against FastMCP's own automatic traceback inclusion, but does
nothing to sanitize text a developer deliberately embeds in a `ToolError` message or hands to
`str(exc)` — if that string itself contains something sensitive, masking never touches it, exactly
as `SecretStr` never touches a value already pulled via `.get_secret_value()`. Also orthogonal to
§3's exception-hierarchy decision: internal hierarchies govern what the _code_ catches and
discriminates on; `ToolError` governs what crosses the MCP wire — a separate concern the existing
hierarchy decision doesn't cover.

**Ground truth: zero `ToolError` imports or uses anywhere in the family.** All three repos call
plain `FastMCP("name")` with no `mask_error_details` argument, so FastMCP's unmasked default applies
everywhere. Two patterns exist in practice: direct `raise ValueError(...)` for bad tool arguments
(uncaught, propagates through FastMCP's default unmasked path — consistent with upstream default,
nothing hidden or leaked beyond what FastMCP already does), and per-item `except Exception` inside
batch tools (deliberately broad, `# noqa: BLE001`) that writes `error=str(exc)` into a structured
result field rather than re-raising — isolates one bad item from failing an entire batch (a good,
deliberate pattern for that problem), but means whatever text `str(exc)` produces for _any_
exception type flows to the client with zero review. Today likely benign (the caught exceptions are
mostly this project's own deliberately-worded `ValueError`/`NotFoundError` types), but an unreviewed
assumption — a future dependency exception (a raw Playwright/requests error embedding a URL, header,
or path) would flow through identically, unexamined.

**Decision: adopt `ToolError` at the MCP tool boundary specifically** — the point an internal
exception is about to cross back to the client is the one place that decides what's safe to expose,
by either re-raising as `ToolError` with an explicit, hand-written message, or leaving a plain
exception to raise (accepting FastMCP's default unmasked behavior). Never assume `str(exc)` of an
arbitrarily caught exception is safe by default just because it happens to be dev-controlled today.
Do **not** flip `mask_error_details=True` project-wide as the fix — it would suppress legitimately
useful debugging detail the plain-`ValueError` argument-validation call sites still rely on being
visible to the calling agent; the finer-grained per-message `ToolError` choice mirrors §2's own
preference for explicit control over a broad, blanket toggle.

## 11. MCP tool docstrings — the LLM-facing contract

**Scope: any function decorated as an MCP tool** (`@mcp.tool()` in this family's FastMCP-based
servers) — a genuinely distinct concern from general docstring style, not an extension of one (no
general docstring-content rule exists elsewhere in this skill to extend; §8 covers only type-hint
hygiene). The reader and the failure mode are both different: a human-facing docstring costs reading
time when weak; an MCP tool description is read by an LLM at inference time to decide whether to
invoke the tool at all and with what arguments — a weak one causes wrong-tool-picked,
wrong-arguments, or never-invoked failures, a correctness cost paid by every future call, not a
comprehension-speed one. Mechanically, in this exact stack: FastMCP's docstring parser turns the
_entire_ docstring into the wire-level `Tool.description` — there is no split between "the
IDE-tooltip part" and "the MCP-wire part." A PEP-257-conformant one-line summary would be a _worse_
MCP tool description by the bar below even though it would pass ordinary docstring-style review
cleanly.

**MCP spec, fetched directly**:
[modelcontextprotocol.io/specification/2025-11-25/server/tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
— "Tools in MCP are designed to be **model-controlled**, meaning that the language model can
discover and invoke tools automatically." The spec itself is thin on content guidance (`description`
is defined only as "Human-readable description of functionality" — no prescribed length/structure).

**Anthropic's platform docs are the most directly actionable source found**,
["Define tools"](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools), "Best
practices for tool definitions," fetched directly: **"Provide extremely detailed descriptions. This
is by far the most important factor in tool performance."** Content checklist: what the tool does,
when it should/shouldn't be used, what each parameter means and how it affects behavior, caveats/
limitations, what information the tool does _not_ return. **"Aim for at least 3–4 sentences for each
tool description, more if the tool is complex."** Also: consolidate related operations into fewer
tools rather than one-tool-per-action ("fewer, more capable tools reduce selection ambiguity");
meaningful namespacing once a library spans multiple services; design responses to return only
high-signal information ("Bloated responses waste context"). A worked good-vs-poor example pair
(`get_stock_price`) is given directly: the good version states what's returned, when to use it, and
what it explicitly does _not_ cover in ~3 sentences; the poor version is a six-word fragment with no
parameter description at all.

**Anthropic's engineering blog,
["Writing effective tools for agents"](https://www.anthropic.com/engineering/writing-tools-for-agents),
is the deeper "why."** Core heuristic, quoted in full: **"When writing tool descriptions and specs,
think of how you would describe your tool to a new hire on your team. Consider the context that you
might implicitly bring — specialized query formats, definitions of niche terminology, relationships
between underlying resources — and make it explicit."** Parameter-naming guidance: "input parameters
should be unambiguously named: instead of a parameter named `user`, try a parameter named `user_id`"
— this family's tools already do this consistently (`listing_url`, `seller_url`, `category_slug`,
never a bare `id`/`url`). "Every word in your tool's name, description, and parameter documentation
shapes how agents understand and use it" — the function name is part of the same selection surface
as the prose. The article's evidence this matters at all: Claude Sonnet 3.5's SWE-bench Verified
result followed specifically from "precise refinements to tool descriptions, dramatically reducing
error rates."

**OpenAI's guidance is directionally consistent but pulls toward brevity for a different reason —
token cost, not clarity** (aggregated via search, not independently deep-fetched — the weaker
citation here): "a tool list with 10 verbose function descriptions can add hundreds of tokens to
every API call... keep descriptions specific but concise." A real tension with Anthropic's "3–4
sentences minimum" bar, not a contradiction — different cost model. OpenAI's guidance targets a
large multi-tool library resent every call; this family's actual shape (5–8 tools per server, MCP's
session-scoped tool listing, not resent per-message) pays that token cost once per session, not per
message — **Anthropic's "detailed over concise" bar is the better fit here**, a judgment call, not a
claim that OpenAI's advice is wrong in its own context.

**Ground truth: this family's own code is already unusually strong practice, well beyond the
Anthropic floor — worth naming specifically what it does right.** Read directly from
`olx-polite-mcp/olx_polite_mcp/server.py` and `freshful-polite-mcp/freshful_polite_mcp/server.py`
(both `fastmcp==3.4.7`, no `description=` override anywhere — every tool relies on docstring
parsing): `get_listing_details_batch`'s docstring **disambiguates from the sibling
`get_listing_details` tool by name, inline**, states argument provenance ("pass `listing_url` from a
`search_listings` result"), and explains its batch cap as a deliberate anti-misuse guard, not just a
number ("specifically to keep that from being a one-call blanket-enrichment shortcut"), preempting a
plausible LLM misuse pattern rather than only documenting the ceiling. `list_favorites` explicitly
contrasts itself against `list_usuals` and `search_products`. `get_shopping_patterns`'s docstring
states a measured response-size number (~69KB for 200 products, against a ~64KB cap) as the reason a
smaller default shape exists — response-shape documentation, not just tool-purpose documentation.

**Two concrete, checkable gaps found — mechanism, not content quality.** (1) None of the ~11 tools
grepped use `Annotated[x, Field(description=...)]` or a docstring `Args:` section — every parameter
description lives only in free-form prose, so the JSON-Schema
`inputSchema.properties.<param>.description` field itself is empty for every parameter in both files
(checkable via `tools/list`). Functionally this mostly still reaches the LLM (most clients send the
whole description), but it's unexercised as FastMCP's parameter-description mechanism is designed to
work. (2) `add_to_cart`/`remove_from_cart` in `freshful-polite-mcp` — real-money-adjacent, clearly
destructive/write operations — have no `annotations=` set (`readOnlyHint`/`destructiveHint`/etc., a
structurally separate field from `description`, per the MCP spec). FastMCP's own docs state clients
"use annotation hints to determine when to skip confirmation prompts" — a client capable of
consulting `destructiveHint` gets no signal from this server at all today, relying entirely on
docstring prose to convey what the field exists specifically to make machine-readable. (Per the
spec, annotations must also be treated as untrusted unless from a trusted server — a security
framing distinct from the writing-quality question here.)

**Decision:** for any `@mcp.tool()`-decorated function, the docstring is the tool's contract with an
LLM caller, not internal documentation — write to Anthropic's bar (what it does and how it differs
from its nearest sibling by name, when to use/not use it, where each non-obvious parameter's value
comes from, response shape/size caveats, at least 3–4 sentences, more for a complex tool), not PEP
257's. Concrete shape, extracted from this family's own strongest examples rather than invented
fresh:

```python
@mcp.tool()
def get_listing_details_batch(listing_urls: list[str], report_path: str | None = None) -> DetailBatchReport:
    """<What it does, one sentence, and how it differs from the nearest sibling tool by name.>

    <When to use it vs. not — e.g. the shortlist-vs-full-search distinction, the batch-cap rationale.>

    <Where each non-obvious parameter's value comes from — "pass X from Y's result" — and what
    the response contains/omits, including size caveats if the tool can return a lot of data.>
    """
```

Two secondary follow-ups, worth a line each even though they're not the docstring itself: attach
per-parameter descriptions via `Annotated[x, Field(description=...)]` so the JSON-Schema itself
carries them, not just the aggregate description text; and set `annotations=` on any tool with real
side effects, since clients use it specifically to decide when to skip or require confirmation
prompts.

**Honesty flags carried forward**: the OpenAI-conciseness citation and FastMCP's claim that
"docstrings should describe response shape" both came from search summaries, not independently
re-fetched primary text — directionally trusted, not verbatim-cited. "FastMCP docstrings are
LLM-facing" is a correct-but-inferred combination of two separately-verified facts (FastMCP
populates `Tool.description` from the docstring; the spec defines `Tool.description` as what the
model-controlled invocation flow reads), not one direct FastMCP statement.

## 12. Async and concurrency

**Ground truth first, since this shapes everything below**: zero `async def`/`await`/`asyncio.`
matches across all five `*-polite-mcp` repos — every implemented site MCP is 100% synchronous code
today. `product-research-pipeline` (the fan-out orchestrator) has no code at all yet — its own
roadmap states "research-before-build" deliberately. The sub-decisions below for the orchestrator
are therefore forward-looking design decisions, not extraction from existing practice — flagged
honestly rather than dressed up as already-proven.

**Sync-vs-async boundary — FastMCP forces the answer for MCP tool code, verified directly from
installed source (`fastmcp==3.4.7`), not docs alone.** `FunctionTool.run()` branches on
`is_coroutine_function`: an `async def` tool is awaited directly on the event loop; a plain `def`
tool is dispatched via `anyio.to_thread.run_sync` — a **thread pool**, not the event loop,
explicitly noted as "safe for functions that depend on context (like dependency injection)" since it
propagates contextvars. **This is exactly the mechanism `olx-polite-mcp`'s `RateLimiter` docstring
is defending against**: "Thread-safe since FastMCP may dispatch concurrent tool calls... across
threads" — verified correct, not a guess, which is why `RateLimiter` uses `threading.Lock`, not
`asyncio.Lock` (an `asyncio.Lock` would be useless across FastMCP's thread pool — it only guards
concurrent tasks on one event loop).

**Decision: `def`, not `async def`, for site-MCP tool functions** — matches 100% of existing code,
and FastMCP already gives a sync tool function real concurrency (thread-pool dispatch) for free;
`async def` would only be justified by needing structured control over _that_ concurrency inside one
tool call (e.g. fanning out to several upstream URLs within a single tool response) — decide
per-tool if that need arises, not as a blanket switch. **Decision: `product-research-pipeline`'s
orchestrator should be async** — it's structurally the fan-out-then-merge case below, the opposite
of a single-request-at-a-time MCP server (inferred from its own roadmap architecture, not working
code — flagged as the one part of this section resting on doc inference).

**Structured concurrency: `asyncio.TaskGroup`, not `asyncio.gather()`, as the default** — official
docs, fetched directly, quoted verbatim: "_TaskGroup_ provides stronger safety guarantees than
_gather_ for scheduling a nesting of subtasks: if a task... raises an exception, _TaskGroup_ will,
while _gather_ will not, cancel the remaining scheduled tasks." `gather()`'s default mode propagates
the first exception but leaves sibling awaitables running orphaned in the background unless
something else awaits/cancels them — for a fan-out orchestrator calling 3–6 site MCPs, that means
one site erroring leaves the others' in-flight rate-limited/browser-session calls running
unobserved, exactly the kind of resource leak a deliberately-throttled, deliberately-session-holding
"polite" client can't afford. `TaskGroup`'s fail-fast-and-cancel-siblings is the closer match to "if
one site errors, stop hitting all the others and surface the failure." Where genuine
partial-tolerance is wanted (return whichever sites answered, list the rest as errors — plausible
per the roadmap's own "normalize/ dedupe/sort" language), the right shape is catch-and-record
_inside_ each child coroutine, preserving TaskGroup's cancellation semantics for genuinely uncaught
cross-cutting failures, rather than reaching for `gather(return_exceptions=True)` directly. **Real
internal precedent, not just docs**: FastMCP's own `fastmcp/utilities/async_utils.py` implements its
internal `gather()` helper on top of `anyio.create_task_group()`, catching exceptions inside each
child task rather than letting them propagate into the group — the exact pattern recommended above,
corroborated from the framework this family is built on.

**Rate-limiting vs. concurrency-capping — two different jobs, not competing mechanisms.**
`RateLimiter` (`core/politeness.py`) is correctly sync/`threading.Lock`-based given the sync-tool
decision above, and stays that way — it would not compose directly inside genuinely async code (a
blocking `with` inside a coroutine freezes the entire event loop for however long it's held,
defeating the point of being async). Two load-bearing, source-confirmed design points in the
existing code: `throttle()` holds its lock for the **entire request**, not just the pre-send wait —
its docstring cites a real 2026-08-13 production incident (olx.ro connection resets from concurrent
`get_listing_details` calls) as the reason a naive "just space out request starts" version was
insufficient; and `retry_with_backoff()`'s docstring requires retries to happen _inside_ the
throttled call, not wrapped around it, or a slow retry's backoff sleep holds the site-wide lock too.
For the future async orchestrator, `asyncio.Semaphore` is the standard tool to cap how many site-MCP
calls are in flight simultaneously — a different axis than `RateLimiter`'s per-site request spacing,
layered on top of (not replacing) each site MCP's own existing rate limiter, since each site MCP is
a separate process/connection the orchestrator's semaphore doesn't conflict with.

**Blocking calls inside async code — the hazard and where it actually applies.** The moment any code
in this family becomes genuinely `async def`, a sync HTTP call or a `threading.Lock`-based
`throttle()` call executed directly inside a coroutine blocks the _entire_ event loop for its
duration — a serious footgun for a deliberately-throttled client (a blocking `time.sleep()` inside
`async def` freezes every other concurrent task on that loop for the sleep's duration, cancelling
out the concurrency the orchestrator exists to get). Mitigation: either use a client with a native
async API end-to-end, or — if a sync call is genuinely unavoidable — push it off the loop via
`asyncio.to_thread()` (stdlib, 3.9+, the same `anyio.to_thread.run_sync` mechanism FastMCP already
uses internally for sync tool dispatch, so not a novel pattern for this codebase). Concretely,
though, this hazard is narrower than "any HTTP call blocks the loop": orchestrator-to-site-MCP calls
go over `fastmcp.client` (itself async), so that boundary is async-clean by construction — the
hazard only bites a _future_ async site-MCP tool doing its own sync HTTP/CDP call inline rather than
through an async client.

## 13. HTTP client, sessions, timeouts, and retry/backoff

**Ground truth first.** `olx-polite-mcp/olx_polite_mcp/core/fetch.py` is the only file in the family
importing `requests` — one `requests.Session()` per `PoliteFetcher` instance (itself a module-level
singleton per site, §5's `globals.py` pattern), explicit `REQUEST_TIMEOUT_SECONDS = 15` on every
call, and a hand-rolled `retry_with_backoff()` scoped to exactly `ConnectionError`/
`ChunkedEncodingError`/`Timeout` — deliberately **excluding** `HTTPError`, with a comment explaining
why: "a 404/403 is a real answer from the site, not a network blip, and retrying it would just be
hammering the site for no reason." `freshful-polite-mcp`/`temu-polite-mcp` don't use a plain HTTP
client at all for their main fetch path — both sites are anti-bot-hardened enough that Playwright
over CDP is the working approach. All three fetch robots.txt via stdlib `urllib.request` directly,
not `RobotFileParser.read()` — a documented, deliberate workaround for a real bug (a live incident
where `publi24.ro` 403s the default `Python-urllib` UA, and `RobotFileParser`'s own `disallow_all`
latch on a 401/403 never resets), not a general client-library preference. No async anywhere
(`rg -c
'async def'` returns zero across all `server.py` files) — the premise that async-concurrency
work forces httpx adoption doesn't currently hold; noted honestly rather than assumed.

**HTTP client library — httpx is the default for any new plain-HTTP fetch path** (what `emag-`/
`altex-polite-mcp` should reach for once they get real code). requests' own docs, fetched directly,
name httpx as the answer to requests' own biggest gap: "If you are concerned about the use of
blocking IO... some excellent examples are... **httpx**." httpx's own site, fetched directly:
"builds on the well-established usability of `requests`, and gives you a broadly requests-compatible
API" — confirming low migration cost from the existing `PoliteFetcher` shape if ever done — plus
"Strict timeouts everywhere" as a named feature (see below), HTTP/2, and async-ready if any
`@mcp.tool()` function ever does go async. **Not a recommendation to churn
`olx-polite-mcp/core/fetch.py` today** — it's small, already handles the real gotchas, and rewriting
working code with no concrete driving need contradicts this project's own §4 "lean toward
duplication / don't fix what isn't measured-broken" stance (this "don't migrate working code" half
is this research's own inference from that existing stance, not separately sourced). Stdlib `urllib`
stays the deliberate, correct choice for the robots.txt case specifically — not a general-purpose
contender.

**Session/connection reuse — already correctly done, now stated as an explicit convention.**
`PoliteFetcher.__init__` constructs one `Session` and reuses it for the object's lifetime; requests'
own docs confirm the mechanism ("keep-alive is 100% automatic within a session... the underlying TCP
connection will be reused"). The politeness argument is real, not just a perf one: every new TCP+TLS
handshake is extra load the _target site_ pays for, so reuse is doubly justified here — the standard
perf argument, and direct service to the "polite" mission (fewer distinct connections against a site
that isn't expecting bulk traffic), the same instinct visible in `RateLimiter.throttle()`'s own
comment about a live connection-reset incident from concurrent in-flight requests. **Decision: one
`Client`/`Session` per fetcher instance, constructed once and reused for its lifetime** — the direct
`httpx.Client()` equivalent applies unchanged if `olx-polite-mcp` ever migrates.

**Timeout defaults — requests has no default timeout, confirmed directly from requests' own docs, a
real and well-sourced gotcha that is already avoided here.** "By default, requests do not time out
unless a timeout value is set explicitly. Without a timeout, your code may hang for minutes or more"
— but `REQUEST_TIMEOUT_SECONDS = 15` is already passed on every call, and a separate
`ROBOTS_FETCH_TIMEOUT_SECONDS = 10.0` guards the robots.txt fetch. httpx ships a safer default
(`Timeout(5.0)`, "Strict timeouts everywhere" as a stated feature) but 5s is generic, not tuned to
any site's actual latency profile the way `olx-polite-mcp`'s 15s deliberately is — so the operative
convention is **"keep setting an explicit, site-tuned timeout regardless of which client is in
use,"** not "httpx's default is safe enough to skip setting one."

**Retry/backoff — tenacity is the default for retry/backoff logic going forward.** What exists
today: `retry_with_backoff()` is small and already does the two things that matter most for a
_polite_ retry policy (bounded attempts at `RETRY_ATTEMPTS = 3`; a hard exclusion of `HTTPError`
since 404/403 are real answers, not blips) — it's just **linear**, not exponential, has no jitter,
and there's no `Retry-After` handling anywhere in the family. httpx deliberately doesn't fill this
gap itself — confirmed from its own docs: `HTTPTransport(retries=N)` only retries connection-level
failures, and for anything beyond that httpx's own docs say "consider general-purpose tools such as
**tenacity**" (the same relationship requests has via `urllib3.util.Retry` mounted on an
`HTTPAdapter` — even requests' own example scopes `allowed_methods` narrowly rather than retrying
everything). Exponential-backoff-with-jitter is settled practice, not contested: AWS's Architecture
Blog,
["Exponential Backoff and Jitter"](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/),
fetched directly — unjittered backoff still clusters retries into synchronized spikes; jitter
"should be considered a standard approach for remote clients," and most AWS SDKs now ship it as a
built-in default. This family's fetch paths are exclusively GET (idempotent by construction — no
POST/PATCH in scope for these lookup tools), so retry-safety's idempotency precondition (AWS's
Builders' Library,
["Making retries safe with idempotent APIs"](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/))
is already satisfied structurally. `Retry-After` handling is the one genuine gap — none of the three
retry paths currently parse or honor it, the more impolite of the two behaviors given the family's
whole premise.

**Decision: tenacity going forward** — for `emag-`/`altex-polite-mcp`'s new retryable-HTTP code, and
as the natural next iteration of `retry_with_backoff()` itself, should someone pick that improvement
up (not a mandate to do so now). Scoping rules to carry forward, all already true in spirit of the
existing hand-rolled code: **retry only transient network conditions and a narrow retryable-status
set (429/502/503/504), never 4xx "real answers" like 404/403; keep attempts low (the existing
`RETRY_ATTEMPTS = 3` is a reasonable ceiling to preserve, not a floor to raise — more retries
against a low-traffic personal tool cuts against the politeness mission); and parse and honor
`Retry-After` when present, in preference to the computed backoff delay.** One architectural detail
that must survive any tenacity migration: `RateLimiter.throttle()`'s docstring documents the
retry-vs-throttle ordering as a deliberate, incident-informed choice — the throttle call must be
_inside_ the retried function, not wrapping the whole retry loop, or a slow retry's backoff sleep
holds the site-wide rate-limit lock too. A tenacity-decorated replacement needs to preserve this
same nesting or it silently reintroduces the lock-contention problem that comment documents having
been fixed.

## 14. Package layout: `src/` over flat

**Default: any installable/importable package in this family uses `src/<pkg_name>/`, not a flat
`<pkg_name>/` at repo root.** A top-level `tasks.py` or other script entrypoint isn't a package and
stays at repo root regardless — this convention governs the thing that gets built into a wheel and
imported, not tooling scripts.

**PyPA's own packaging guide states the reasoning directly, fetched verbatim**:
[packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
— three distinct, separately-stated arguments, not one vague appeal to convention. (1) "The src
layout helps prevent accidental usage of the in-development copy of the code" — Python puts the
current working directory first on the import path, so a flat layout lets an import silently resolve
to the _uninstalled, cwd_ copy instead of whatever's actually installed, which can mask "subtle
misconfiguration of the project's packaging tooling" (files missing from a real distribution, for
example) that only surfaces once someone else installs the package for real. (2) It "helps enforce
that an editable installation is only able to import files that were meant to be importable" — flat
layout lets an editable install expose non-package files (a `README`, a config file sitting at repo
root) on the import path, so "certain imports work in editable installations but not regular
installations," a real cross-environment inconsistency. (3) "The src layout requires installation of
the project to be able to run its code, and the flat layout does not" — an explicit, deliberate
development step rather than code that happens to run by accident from the wrong location.

**Hynek Schlawack's "Testing & Packaging," fetched directly, makes the same case from the testing
angle specifically**:
[hynek.me/articles/testing-packaging](https://hynek.me/articles/testing-packaging/) — "If you use
the ad hoc layout without an `src` directory, your tests do not run against the package as it will
be installed by its users. They run against whatever the situation in your project directory is." A
flat layout's test suite silently tests the development-directory state of the code, not the actual
packaged deliverable — packaging mistakes (a missing sub-package, an unincluded resource file) stay
invisible in CI and surface only once a real user installs it. `src/` layout makes the project root
itself un-importable, so a test run is forced through the same install path a real consumer goes
through.

**Honest scope note**: neither source claims flat layout is unsafe for code that's never
packaged/installed anywhere (a pure script, a one-off notebook) — the argument is specifically about
anything meant to be `pip`/`uv`-installed, which is every package in this family (MCP servers
install via `uv tool install`; a shared library like `repo-tasks` installs via `uv add`).

## Not yet covered

The user's own framing when this research started: "we can start with those" — a starting set, not
the full scope. §9–13 above closed the async/concurrency and (MCP-scoped) logging gaps this section
used to list. Still open: **general logging conventions for non-MCP code** (log levels, structured
logging vs. stdlib `logging`, applicable to `power-user-linux-setup` itself and any future CLI tool
in the family — §9 only covers the MCP-stdio-specific stdout/stderr constraint, not logging style
broadly) and **CLI-argument-parsing conventions** (no CLI-heavy repo in the family yet to ground
against — `product-research-pipeline`'s orchestrator is the most likely first real case). Two
narrower follow-ups surfaced during §11/§13 and worth tracking even though they're not new topics:
adopting `Annotated[x, Field(description=...)]` for per-parameter MCP tool descriptions, and adding
`Retry-After` handling to the family's retry logic — both concrete gaps in existing code, not new
conventions to decide.
