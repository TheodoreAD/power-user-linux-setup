---
status: idea
updated: 2026-08-15
---

# Python conventions across personal repos: typing, style, and design defaults

## Context

Same underlying motivation as `skills/db-defaults`: models and sessions drift toward different
"reasonable" choices for the same recurring decisions, so conventions across this repo family
(`power-user-linux-setup`, the `*-polite-mcp` repos, `product-research-pipeline`) end up
inconsistent even though there's no real disagreement about what's best — just nobody wrote the
default down. This plan is scoped to **language-level and design-level conventions** (typing,
style, control flow, data modeling, architecture) — not repo scaffolding, which is already covered
by `plans/2026-08-14-python-repo-scaffolding.md`.

Audience is explicitly both humans and coding agents, so — per Armin Ronacher's argument cited
below — **consistency of one opinion matters as much as which opinion is "most correct"** in the
several places reputable sources genuinely disagree with each other. This plan surfaces those
disagreements rather than hiding them, and records which way the user actually decided, so a future
build-out (skill or `AGENTS.md` guidance) has real citations behind it instead of restating LLM
training-data platitudes.

No repo in this family has a static type checker configured today. Ruff already governs
mechanical style (formatting, import order, common bug patterns) — this plan deliberately doesn't
re-litigate anything ruff already enforces, only the structural/idiomatic choices ruff is silent on.

Seed topics, per the user's original list, explicitly not exhaustive ("we can start with those"):
typing, general style, early returns/guard clauses, fail-fast, Pydantic vs dataclass vs NamedTuple
vs TypedDict, modularity/testability/DRY/readability/encapsulation, modules-as-singletons,
properties for lazy loading. Research also surfaced two topics the user hadn't listed but pulled in
once flagged: **settings/secrets management** and **basedpyright** specifically (over plain
pyright).

Four research agents ran the primary pass (parallelized by cluster); a fifth follow-up pass covered
basedpyright and settings libraries after the user's own answers surfaced those gaps. Full citation
trails are in each cluster below — this file is the durable record, not a scratch summary, so
sources are kept rather than compressed away.

## 1. Static type checking — tool choice and strictness

**Landscape (Aug 2026):** four real contenders, no consensus winner.

- **mypy** — incumbent, deepest tutorial/Stack-Overflow ecosystem, but lowest typing-spec
  conformance of the four (~58% in one third-party conformance run) and slowest.
- **pyright** (Microsoft) — mature, highest install base (Pylance ships in VS Code, 196M+
  installs), strongest strict-mode documentation, ~95–98% conformance.
- **pyrefly** (Meta) — newest to reach stable (1.0, May 2026), best speed+conformance combo in
  most benchmarks, smallest community/troubleshooting footprint of the four.
- **ty** (Astral — same team as ruff/uv, OpenAI-acquired March 2026) — fast, ecosystem-aligned
  with tools already in this stack, but still pre-1.0/beta versioning (`0.0.72` as of this
  research) — not yet broadly recommended as a default by its own maintainers' versioning signal.

**basedpyright** (the user's actual pick, researched in depth as a follow-up): a fork of pyright,
maintained primarily by one contributor (`DetachHead`) plus ~90–200+ contributors depending on
counting method. Exists to close two real gaps in plain pyright: (1) several editor-facing
features — inlay hints, semantic highlighting, docstring/import-suggestion completions — are
implemented only in Microsoft's closed-source **Pylance**, licensed for VS Code only; basedpyright
reimplements Pylance-equivalent features into its own language server so any editor gets parity.
(2) Plain pyright's CLI ships only via npm and needs a Node runtime — an awkward fit for a
pure-Python/uv toolchain; basedpyright publishes a normal PyPI package that bundles its own Node
runtime internally. It tracks upstream pyright tightly — new pyright releases get merged in within
0–2 days, confirmed directly from commit history, not just from the docs' framing — so it's a
genuine superset, not a diverging fork. It keeps pyright's `off`/`basic`/`standard`/`strict` ladder
intact and adds two more tiers: `recommended` (its new default — every practically-useful rule on,
distinguishing likely-bug errors from style warnings) and `all`, plus a `--writebaseline` mechanism
for adopting stricter rules on an existing codebase incrementally (comparable to ruff's/mypy's own
baseline-adoption story). Posit's engineering blog (Mar 2026), evaluating type checkers for their
Positron IDE, called it "the most mature" of the four forks/alternatives they tested but chose
Pyrefly instead — not on a technical deficiency, but because basedpyright's aggressive-by-default
strictness is a worse fit for exploratory data-science workflows than for package/CLI development,
which is the opposite of this repo family's shape. The one real, unstress-tested caveat: **single-
maintainer bus-factor risk**, vs. Microsoft's institutional backing of plain pyright — no source
found treats this as a current problem, but it's worth naming rather than omitting.

**Decision: basedpyright, strict enforcement from day one.** The "strict is unnecessary for small
codebases" framing from PEP 484/Guido himself, and typing.python.org's own "not all practices are
applicable in all situations," is real and cited — but it's advice about _migrating_ an existing
large codebase gradually, which doesn't apply here: there's no legacy debt to protect, and the user
already has an established "type everything, even snippets" precedent
([[feedback_type_everything_for_agent_precedent]]). basedpyright's `recommended` mode plus its
baseline mechanism is a good practical answer to Ronacher's "shitty types" agent-legibility
argument (below) even at strict settings — it separates likely-bug errors from style noise instead
of dumping an undifferentiated wall of errors.

**Genuine dissent worth keeping in view, not adopting:** Armin Ronacher (Flask creator), two posts —
["Untyped Python: The Python That Was"](https://lucumr.pocoo.org/2023/12/1/the-python-that-was/)
(Dec 2023) argues Python's original strength was a tiny language-runtime surface area, and heavy
typing risks "creating the new Java." More pointed: ["In Support Of Shitty Types"](https://lucumr.pocoo.org/2025/8/4/shitty-types/) (Aug 2025) argues fragmented, disagreeing
type checkers actively hurt LLM coding agents specifically, because models struggle when tools
disagree on what counts as an error — his conclusion is that _consistency_ of one checker's opinion
matters more than maximal strictness for agent-driven workflows. This is unusually on-point given
this plan's own stated audience, and is exactly why "pick one checker, strict, and stop arguing
about it" is the right shape of decision here even though "strict" itself isn't universally
endorsed.

**`Any` / `# type: ignore` hygiene:** community-uncontested — scope ignores to a specific error code
(`# type: ignore[code]`) rather than blanket-silencing a line; Ruff has `PGH003
(blanket-type-ignore)` for exactly this, not currently in this repo's `select` list.

## 2. Data modeling — Pydantic vs dataclass vs NamedTuple vs TypedDict vs attrs vs msgspec

| Situation                                                                                       | Default                                        |
| ----------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| Parsing external/untrusted JSON (API responses, MCP tool args) + want auto JSON-Schema          | **Pydantic v2**                                |
| Same, but validation/serialization throughput is a measured bottleneck                          | **msgspec**                                    |
| Internal-only container, no validation needed, zero dependencies wanted                         | **dataclass** (`frozen=True` for immutability) |
| Internal-only container, want validators/converters without Pydantic's full weight              | **attrs**                                      |
| Must behave like a plain tuple (positional unpack, hashable)                                    | **NamedTuple**                                 |
| Genuinely staying a plain dict (kwargs, already-parsed JSON); static-checker documentation only | **TypedDict**                                  |

Pydantic v2's validation core (`pydantic-core`) is Rust-based — 4–50x faster than v1 depending on
model shape, per multiple independent benchmarks. **Any pre-2023 "Pydantic is slow" take is
measuring v1** and should be discounted. attrs and msgspec still win on raw speed against Pydantic
v2 (attrs ~3x faster instantiation per one blogger's own benchmark; msgspec 10–20x faster decode,
5–60x faster struct operations per multiple 2025–2026 sources) — both are legitimate, not
theoretical, alternatives once Pydantic's overhead is a measured problem, not a guess.

The single sharpest source on Pydantic's actual tradeoff:
["Why I use attrs instead of pydantic"](https://threeofwands.com/why-i-use-attrs-instead-of-pydantic/) —
"Pydantic makes things that should be hard appear easy, and things that should be easy,
frustratingly hard," arguing Pydantic's bundling of validation+conversion+serialization causes
surprising default behavior, while attrs' opt-in model is more composable (pairs with `cattrs` for
un/structuring, kept separate from the model definition by design). Concedes Pydantic's default
validation error messages are better precisely because Pydantic validates by default where attrs
requires opting in per field.

**No decision needed here beyond the table** — this maps cleanly onto the existing
[[feedback_best_tool_per_concern]] preference (best tool per concern, not fewest total
dependencies), same reasoning that kept DuckDB as both the OLAP and time-series pick in
`db-defaults`.

## 3. Settings and secrets management

Not in the original seed list — the user flagged this gap explicitly and named `pydantic-settings`
as the candidate.

**pydantic-settings**: split out of Pydantic v1's built-in `BaseSettings` into its own
`pydantic`-org-maintained package for v2. Verified mechanics: typed `BaseSettings` subclass,
source-priority chain (CLI args → init kwargs → env vars → `.env` file(s), layerable →
`secrets_dir` → field defaults), nested config via `env_nested_delimiter` or JSON, first-class TOML/
YAML/JSON/`pyproject.toml` sources, and genuine Docker/K8s-secret-mount support
(`SettingsConfigDict(secrets_dir=...)`, one file per field). `SecretStr` masks `repr()`/`str()`
only — genuinely prevents the common "stray `print(settings)` leaks a secret" accident, but
`.get_secret_value()` still returns the raw string, so it is **not** a full secrets-management
control; state this plainly wherever it's documented, since it's a common point of over-trust.
~488M PyPI downloads/month (reflecting FastAPI's install base as much as direct adoption), commits
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

## 4. Early returns / guard clauses, fail-fast, and the EAFP tension

**Guard clauses — the actual rule, not the folk version.** Fowler's _Refactoring_ (the origin,
"Replace Nested Conditional with Guard Clauses") draws an asymmetry test, not a blanket
"flatten everything" rule: if-then-else is right when both branches are equally likely/important;
a guard clause is right specifically when one path is the happy path and the other a rare,
exceptional early-out. **Using a guard clause to split two co-equal business branches destroys the
signal the construct is supposed to carry** — this is the single most load-bearing nuance to keep.
PEP 8 never mentions guard clauses, early return, EAFP, or LBYL at all (verified directly against
the PEP text — several web summaries claiming "PEP 8 endorses EAFP" are wrong). The closest thing
to an official Python endorsement is PEP 20's "Flat is better than nested" — a philosophy, not a
rule.

**The EAFP/LBYL tension is real, not manufactured.** A guard clause is structurally LBYL — it looks
before it leaps. Python's own glossary calls out LBYL's race-condition risk directly (check-then-act
gap) and names EAFP as the culturally preferred style. The reconciliation that holds up: **guard
clauses validate a function's own contract** (did the caller uphold the API — argument types,
value ranges) — a different question than "will this specific runtime operation succeed," which is
EAFP's territory (dict/attr lookups, file I/O, network calls — things Python already knows how to
fail loudly on). Where sources disagree is how strictly to police that boundary; mainstream practice
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
`wemake-python-styleguide`), ["Python exceptions considered an anti-pattern"](https://sobolevn.me/2019/02/python-exceptions-considered-an-antipattern) — argues
exception-heavy EAFP code is itself a readability/correctness hazard (almost any line can silently
raise, no static way to see what runs after a catch), proposing explicit `Result[Success, Error]`
container types instead. Real standing, genuinely rejects mainstream EAFP culture — not adopted
here, but worth recording so it isn't silently "rediscovered" later and treated as a regression from
current practice.

## 5. Modularity, testability, DRY, readability, encapsulation

**Architecture lineage:** _Architecture Patterns with Python_ (Percival & Gregory, cosmicpython.com)
is the standard current Python-specific reference, built explicitly on three borrowed ideas:
Hexagonal/Ports-and-Adapters, Dependency Inversion, and Gary Bernhardt's **Functional Core,
Imperative Shell**. Their own opening line on DI: **"Dependency injection (DI) is regarded with
suspicion in the Python world."** Their prescription is not a DI framework but a manual
**Composition Root** — explicit wiring at the application entrypoint via closures/partials — because
monkeypatch-style mocking "couples tests tightly to implementation details."

**Clean Code / Clean Architecture (Robert C. Martin) — the Python-specific pushback is real and
documented**, not invented for balance: ["Why I can't recommend Clean Architecture by Robert C
Martin"](https://dev.to/bosepchuk/why-i-cant-recommend-clean-architecture-by-robert-c-martin-ofd)
(discussed on HN and Lobsters) argues Clean Architecture's abstract-interface-class machinery is
"a very common, and necessary tactic when using statically typed languages like Java and C#," but
in Python those interface classes and the dependencies that would target them don't need to exist
at all — duck typing already provides the decoupling. **The core idea (depend on abstractions, keep
the domain free of I/O concerns) survives; the Java-flavored mechanism doesn't fit and is rejected
by Python-specific voices.**

**Functional Core, Imperative Shell** — legitimate, live, actionable advice, not a dated pattern:
Google's own engineering blog revived it in Oct 2025 (Testing on the Toilet series). Fits
CLI-tool/data-pipeline-shaped code well (arguably this repo family); strains for code whose entire
job _is_ I/O orchestration (MCP servers) — there, Michael Feathers' "seams" vocabulary (a place to
alter behavior without editing code at that place, from _Working Effectively with Legacy Code_) is
the more applicable concept.

**DRY vs. its critiques — decision: lean toward duplication.** Fowler's older Rule of Three
(duplicate once freely, wince at twice, refactor on three, attributed to Don Roberts) is the
moderate position. Sandi Metz's sharper "[The Wrong Abstraction](https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction)" — "duplication is far
cheaper than the wrong abstraction," inline a strained abstraction back out rather than patch it
with more parameters — is a Ruby-community citation with **no independently-argued Python-authority
echo found**, worth being honest about rather than dressing up as cross-language consensus; it
reaches Python circles by reference (e.g. via Kent C. Dodds' "AHA Programming" / "Avoid Hasty
Abstractions," which does the same move). "WET" as a backronym has **no verifiable single
coiner** — treat as crowd folklore, not a cited origin. **This decision matches the user's existing
[[feedback_best_tool_per_concern]] preference and was confirmed directly**: for solo-maintained
repos, a miscalibrated abstraction costs only the maintainer, but also has to survive being
correctly understood by an agent before it can be safely modified — a wrong abstraction is _harder_
for an agent to safely touch than duplicated code, not easier.

**Readability:** PEP 8 itself (authored by Guido, Barry Warsaw, Alyssa Coghlan) states directly:
"code is read much more often than it is written," immediately followed by subordinating the style
guide itself to project-level consistency. **The commonly-cited "Knuth quote" on this topic is a
misattribution** — "programs are meant to be read by humans" is Abelson & Sussman (SICP preface),
not Knuth; Knuth's real, distinct contribution to this lineage is Literate Programming. Comment
philosophy ("why, not what") is already governed by this session's own global instructions
(`~/AGENTS.md`'s "default to no comments... only when the WHY is non-obvious"), not re-litigated
here — but worth noting the pushback exists: Hillel Wayne's ["The Myth of Self-Documenting Code"](https://buttondown.com/hillelwayne/archive/the-myth-of-self-documenting-code/) argues some
information (negative information — "we tried X, it broke because Y" — optimization rationale,
caller-facing gotchas) genuinely can't be inferred from clean code no matter how well-named, so
"self-documenting code" as an ideal is oversold. Consistent with, doesn't override, the existing
comment policy.

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

## 6. Modules-as-singletons and lazy-loading properties — the `globals.py` pattern

**Modules-as-singletons is real, stdlib-endorsed practice**, not just a convenient accident: the
official [CPython Programming FAQ](https://docs.python.org/3/faq/programming.html#how-do-i-share-global-variables-across-modules)
states directly that a module is the canonical way to share state, "because there is only one
instance of each module," and explicitly names this as the basis for implementing Singleton in
Python. Brandon Rhodes' python-patterns.guide sharpens this into the actually-useful form: prefer
"[The Global Object Pattern](https://python-patterns.guide/python/module-globals/)" — instantiate a plain class once at
module level — over a GoF class-based Singleton, specifically because **the Global Object Pattern
doesn't architecturally forbid a second instance**, which is exactly what makes tests able to
construct an independent, isolated object instead of fighting shared global state. This is the
precise shape of the `globals.py` pattern described: a class, one default module-level instance,
freely re-instantiable for tests.

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
- **Concurrency correctness:** the official [free-threading guide](https://py-free-threading.github.io/testing/) states plainly that global mutable state
  relying on unstated GIL assumptions is not safe even under the classic GIL for compound operations
  (check-then-set, `+=`), and is a live forward-looking risk now that free-threaded builds are a
  real (if opt-in) option.

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
construction cannot. (This specific explicit-method-vs-property contrast is reasoned from the
Google guide's stated principle, not independently sourced by name — flagged as the single weakest-
evidenced sub-point in this whole research pass.)

**Decision, confirmed with the user:** the `globals.py` pattern — a class instantiated once at
module level, `@property`/`cached_property` for lazy-loaded fields, freely re-instantiable with
different settings so tests can swap or recreate the object — is a sound, well-precedented default.
Document both live caveats alongside it wherever it's written up: the 3.11→3.12 `cached_property`
locking change, and "only lazy-load via property when the getter is idempotent/side-effect-free;
use eager `__init__`-time loading or an explicit method when it isn't."

## Recommended direction

Package as a new Agent Skill, `python-conventions`, mirroring `db-defaults`' proven structure:
`SKILL.md` in the same labeled-line spec-block format the user already approved for `db-defaults`
(same LLM/human-readability goal applies here), `references/rationale.md` carrying this file's full
citation trail, and `references/snippets/*.py` — small, typed, runnable examples per convention
(a `globals.py` example with the `cached_property` caveat inline, a guard-clause/EAFP example, an
exception-hierarchy example, a `pydantic-settings` example). This repo already has the skill-
authoring and deployment pipeline (`inv ai.skills`) built and proven once; reusing it is lower-risk
than inventing a second packaging mechanism for what's structurally the same kind of
decision-consistency problem `db-defaults` solved.

This file stays at `status: idea` — no skill has been built yet, and per `plan-docs` convention,
promoting to `planned` happens in the same file once the actual build starts.

## Open questions

- [NEEDS CLARIFICATION: confirm skill packaging (vs. folding directly into each repo's own
  `AGENTS.md`) before starting the build — same shape of decision `db-defaults` already resolved in
  favor of a skill, but worth confirming rather than assuming it carries over automatically.]
- [NEEDS CLARIFICATION: exact snippet set for the skill — one file per convention (matching
  `db-defaults`' one-file-per-category split, which the user confirmed didn't hurt agent
  readability) or grouped by theme (typing, control-flow, architecture)?]
- [NEEDS CLARIFICATION: this research surfaced two concrete, low-cost, well-precedented additions to
  this repo's own `pyproject.toml` ruff `select` list — `PGH003` (blanket-type-ignore) and a
  `mccabe`/`C901` complexity ceiling (industry-default threshold 10) as an objective backstop for
  the guard-clause/nesting guidance in §4. Worth doing as part of this work, or tracked separately?]
- ["and more" — the user's own framing: this is a starting set, not the full scope. Candidates
  raised implicitly by this research but not yet covered: async/concurrency conventions, logging
  conventions, CLI-argument-parsing conventions. Revisit once this batch is packaged rather than
  scope-creeping the current pass.]
