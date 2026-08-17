---
status: idea
updated: 2026-08-16
---

# Python conventions across personal repos: typing, style, and design defaults

## Context

Same underlying motivation as `skills/db-defaults`: models and sessions drift toward different
"reasonable" choices for the same recurring decisions, so conventions across this repo family
(`power-user-linux-setup`, the `*-polite-mcp` repos, `product-research-pipeline`) end up
inconsistent even though there's no real disagreement about what's best — just nobody wrote the
default down. This plan is scoped to **language-level and design-level conventions** (typing, style,
control flow, data modeling, architecture) — not repo scaffolding, which is already covered by
`plans/2026-08-14-python-repo-scaffolding.md`.

Audience is explicitly both humans and coding agents, so — per Armin Ronacher's argument cited below
— **consistency of one opinion matters as much as which opinion is "most correct"** in the several
places reputable sources genuinely disagree with each other. This plan surfaces those disagreements
rather than hiding them, and records which way the user actually decided, so the future skill
build-out (§ Recommended direction — confirmed, not folded per-repo into `AGENTS.md`: maintaining
the same guidance across every repo's own file was judged a maintenance burden the
`db-defaults`-style skill mechanism already solves) has real citations behind it instead of
restating LLM training-data platitudes.

No repo in this family has a static type checker configured today. Ruff already governs mechanical
style (formatting, import order, common bug patterns) — this plan deliberately doesn't re-litigate
anything ruff already enforces, only the structural/idiomatic choices ruff is silent on.

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

**Research retention, independent of this plan's own lifecycle** (explicit user instruction,
2026-08-16): this research "validates our ideas" and must survive regardless of how the plan itself
ends up being used — consolidated is fine, lost is not. This is already the default behavior the
`plan-docs` skill's own "Retiring a plan" step 1 prescribes ("preserve unless already written down
elsewhere") — flagged here explicitly anyway so a future retirement pass doesn't need to rediscover
that instruction from scratch. Concretely: when this file eventually reaches `landed`/`superseded`,
its citation trail migrates to a permanent home (most likely the `python-conventions` skill's own
`references/rationale.md`, or a `contributing/*.md` entry if the skill idea doesn't pan out)
_before_ this file is deleted — never delete-without-migrating just because the plan's specific
proposed next step (the skill) didn't happen.

**This repo is now the pilot/reference implementation** (explicit user instruction, 2026-08-16):
rather than building the `python-conventions` skill first and only then finding out whether its
picks hold up in practice, `power-user-linux-setup`'s own `pyproject.toml`/`tasks/quality.py`/
`setup.toml`/`dprint.json` adopt the tool choices and tuned configs from §§1 and 9 directly, the
same role `olx-polite-mcp` already played as the reference implementation for the scaffolding plan
(`plans/2026-08-14-python-repo-scaffolding.md`). This tests the defaults against a real codebase
before they're baked into a skill other repos will copy — see the repo's own commit history from
2026-08-16 onward for what actually landed and what friction, if any, it produced.

## 1. Static type checking — tool choice and strictness

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

**Decision: basedpyright, `recommended` as the base mode — not `strict`.** This corrects the plan's
own first-pass instinct ("strict from day one"), on direct evidence: **`strict` mode does not enable
most of basedpyright's own exclusive bug-catching rules** — `reportAny`, `reportUnreachable`,
`reportImplicitStringConcatenation`, and `reportIgnoreCommentWithoutRule` all default to `"none"`
(or, for `reportUnreachable`, `"hint"` — invisible to a CLI-driven agent loop entirely) under
`strict`, because those rules were wired into `recommended`/`all` for pyright/VS-Code
backward-compatibility reasons, not retrofitted into the older `strict` ladder. Picking `strict` —
the tier that sounds more rigorous — would have silently missed the exact three bug classes the user
asked this profile to catch. `recommended` turns them on, but has its own gap: it grades everything
as `"warning"` or `"error"`, and defaults `failOnWarnings = true`, which makes the grading
meaningless to a CLI-driven agent (a `"warning"`-level ceremony rule still fails the run). The
concrete, tuned profile:

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
reportImplicitStringConcatenation = "error" # classic missing-comma bug
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
not adapted from a third party's already-published tuning. The pre-existing "type everything, even
snippets" precedent ([[feedback_type_everything_for_agent_precedent]]) still holds — this profile is
how that precedent gets enforced without also demanding annotation ceremony that doesn't catch bugs.

**Genuine dissent worth keeping in view, not adopting:** Armin Ronacher (Flask creator), two posts —
["Untyped Python: The Python That Was"](https://lucumr.pocoo.org/2023/12/1/the-python-that-was/)
(Dec 2023) argues Python's original strength was a tiny language-runtime surface area, and heavy
typing risks "creating the new Java." More pointed:
["In Support Of Shitty Types"](https://lucumr.pocoo.org/2025/8/4/shitty-types/) (Aug 2025) argues
fragmented, disagreeing type checkers actively hurt LLM coding agents specifically, because models
struggle when tools disagree on what counts as an error — his conclusion is that _consistency_ of
one checker's opinion matters more than maximal strictness for agent-driven workflows. This is
unusually on-point given this plan's own stated audience, and is exactly why "pick one checker,
strict, and stop arguing about it" is the right shape of decision here even though "strict" itself
isn't universally endorsed.

**`Any` / `# type: ignore` hygiene:** community-uncontested — scope ignores to a specific error code
(`# type: ignore[code]`) rather than blanket-silencing a line; Ruff has
`PGH003
(blanket-type-ignore)` for exactly this, not currently in this repo's `select` list.

## 2. Data modeling — Pydantic vs dataclass vs NamedTuple vs TypedDict vs attrs vs msgspec

**Decision: trim to as few default choices as possible.** The user's explicit ask — fewer options so
agents mimicking existing code have less room to pick the wrong one — overrides the general
[[feedback_best_tool_per_concern]] instinct here; the research below (attrs vs. Pydantic tradeoffs,
msgspec's speed) stays in the file as real, verified options, but only two are the routine default:

| Situation                                                                                                                 | Default                        |
| ------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| Parsing external/untrusted JSON (API responses, MCP tool args) + want auto JSON-Schema; also **all settings/config** (§3) | **Pydantic v2**, `frozen=True` |
| Everything else — internal structured data, function returns, records                                                     | **`@dataclass(frozen=True)`**  |

`frozen=True` is the default on both, not an occasional opt-in — see §7's immutability-preference
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
- **NamedTuple** — only if the value must behave like a plain tuple for a specific contract
  (positional unpack, hashable, drop-in tuple replacement). A frozen dataclass covers "immutable
  record" already; reach for NamedTuple only when tuple-ness itself is the requirement.
- **msgspec** — only once Pydantic's validation/serialization overhead is a _measured_ bottleneck,
  not a guess. Pydantic v2's Rust core (`pydantic-core`) is 4–50x faster than v1 depending on model
  shape — **any pre-2023 "Pydantic is slow" take is measuring v1** and should be discounted — but
  msgspec still wins on raw speed when it matters (10–20x faster decode, 5–60x faster struct
  operations per multiple 2025–2026 sources).

## 3. Settings and secrets management

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
subclass once, assigning the instance to a module-level name (this is §6's modules-as-singletons
pattern, applied specifically to settings). `frozen=True` throughout, so once the correct
environment's settings load, nothing downstream can mutate config at runtime — the concrete
mechanism behind §7's statelessness/immutability decision. Because it's a plain class, not a
GoF-style Singleton, tests can freely construct an independent instance (any subclass, or the base
class with field overrides) rather than fighting shared global state — the same "Global Object
Pattern over class-based Singleton" reasoning §6 already covers. See §6 for community-precedent
validation of this composite pattern specifically (Flask's own long-documented
`Config`/`DevelopmentConfig`/`ProductionConfig` idiom is the closest established analogue found).

## 4. Early returns / guard clauses, fail-fast, and the EAFP tension

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

## 5. Modularity, testability, DRY, readability, encapsulation

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

## 6. Modules-as-singletons and lazy-loading properties — the `globals.py` pattern

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

**Community-precedent check on the composite settings pattern (§3), run at the user's explicit
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

## 7. Statelessness and immutability

Two new topics the user pulled in after the first pass, tightly related to §6's singleton pattern
and §2's `frozen=True` default.

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
is exactly why §1's basedpyright profile matters: without a type checker actually running, `Final`
is a comment, not a guarantee.

**Why immutability matters — four distinct, separately-sourced arguments, not one vague appeal:**
thread/free-threading correctness (ties directly to §6's free-threading finding); easier reasoning
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
records — covered by §2's `frozen=True` default) — ordinary local mutation (loop accumulators,
building a result before returning it) stays conventionally mutable. This is the same functional-
core/imperative-shell split §5 already covers, applied one level down to individual objects rather
than whole modules.

**Third-party persistent-structure libraries (`pyrsistent`, stdlib-adjacent `immutables` — the
latter genuinely powers CPython's own `contextvars`, not a fringe library) — honest verdict:
overkill for this project family.** Both solve efficient repeated-modification of large, deeply-
nested collections (undo stacks, CRDTs) — not the shape of a config object, CLI arg record, or MCP
payload. `frozen=True` dataclasses/Pydantic + `tuple`/`frozenset` cover the vast majority of cases
here at zero extra dependency weight; reach for a persistent-structure library only against a
measured, not guessed, copy-cost problem on a large nested collection.

## 8. Shell script checking

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
`style`, default shows everything; `--severity=warning` suppresses `info`/`style` noise, matching
this repo's existing "narrow, deliberate selection over broad defaults" philosophy from §1/§9.
Community norm on disabling checks (inferred from real precedent, not one canonical statement):
scope narrowly and say why — kubernetes' own `verify-shellcheck.sh` names exactly three globally-
excluded codes with inline reasons (`SC1090`/`SC1091` for extensively-used non-constant `source`,
`SC2230` for an intentional `command -v` vs `which` preference) — the one documented friction point
worth planning for up front if any bootstrap script sources a runtime-computed path.

**`shfmt` is the real formatting counterpart** — shellcheck does not reformat code at all, so a
consistent-style story needs both, same two-tool split as `ruff check` + `ruff format`. 8,982 stars,
packaged across every major distro/package-manager, actively maintained. The shellcheck+shfmt
pairing is observed real practice, not assumed: `jumanjihouse/pre-commit-hooks` bundles both for
exactly this reason.

**Integration: fold into the existing `tasks/quality.py` invoke namespace, no `pre-commit`
framework.** `pre-commit` is genuinely how most real projects wire these two together, but adopting
it here would mean a second task-runner, a second config format, and a second mental model for "how
do I run checks" sitting alongside `invoke`, which already exists, is already the single entry point
(`inv quality.fix`), and already solves exactly this "aggregate multiple quality tools behind one
command" problem for ruff+dprint. Duplicating a problem this repo already solved is the wrong
tradeoff here — this is the one place [[feedback_best_tool_per_concern]] doesn't argue for a second
tool, because `invoke` isn't a worse fit for this concern, it's the _same_ tool already doing this
job. Concrete shape: `shfmt -l -d` (check) / `-w` (fix) and `shellcheck --severity=warning` (or
whatever floor is chosen), both run over `fd -e sh` output, folded into `inv quality.fix`/
`inv quality.check` as new steps alongside ruff/dprint — the same shape bats-core's and kubernetes'
own plain-script (non-pre-commit) integrations already use. A root `.shellcheckrc` should hold any
exclusions, each with an inline comment stating why, following kubernetes' precedent directly.

## 9. Ruff, pytest, and dprint — configuration conventions, not tool choice

All three tools are already decided; this is about tuning, researched against real, actively-
maintained OSS projects' own configs (Home Assistant, Litestar, Pydantic, httpx) rather than
abstract rule-category descriptions.

**A concrete gap in this repo's current `select` list, independent of anything flagged before:**
Ruff's own zero-config default already includes `F`, `E`, `B`, `UP`, **and `RUF`** (Ruff's own rule
family — mutable class-attribute defaults, `noqa` hygiene, f-string pitfalls). Because this repo's
`select` is explicit rather than additive, it currently gets **none** of `RUF` despite that category
being close to table-stakes elsewhere (22.7% direct-selection rate across a ~127k-repo PyPI survey).
Worth adding on its own merits, separate from the `PGH003`/`C901` candidates already noted.

**`C901`/mccabe — confirmed precisely, plus a real gotcha to avoid.** Default `max-complexity = 10`
per Ruff's own settings docs, tracing to McCabe's original "anything beyond 10 is too complex." Not
covered by any currently-selected category — must add `C90` to `select` explicitly. **The gotcha**:
Pydantic's own `pyproject.toml` sets `[tool.ruff.lint.mccabe] max-complexity = 14` but never adds
`C90`/`C901` to its `select` array — the complexity setting is silently inert without it. Worth
double-checking this repo's own config for the identical trap once added.

**Per-category verdicts, evidence-based against four real flagship configs** (none of the four
select every category — hand-picked, narrow selections are the actual norm, validating this repo's
existing philosophy rather than contradicting it):

- **Add**: `PERF` (low-noise, real inefficiency catches — selected by Home Assistant and Pydantic),
  `A`/flake8-builtins (near-zero-noise, catches shadowed builtins), `DTZ`/flake8-datetimez (catches
  naive `datetime.now()`, real timezone-bug class), `T20`/flake8-print (high value specifically for
  an _agent_-maintained codebase — a stray debug `print()` an agent forgets to remove is exactly
  this rule's target; exempt any genuine CLI-output entrypoint module via `per-file-ignores` rather
  than dropping the category).
- **Add, but only the non-`PLR` subset**: `PL`/pylint. Every real config surveyed that touches `PL`
  immediately carves out the `PLR*` (refactor-suggestion) codes — Mozilla's own config removed
  "nearly 2000 warnings" by disabling `PLR0913`/`0911`/`0912`/`0914`/`2004` outright; Ruff's
  `PLR0913` counts `self`/`cls` toward its argument limit and doesn't exempt overrides by default, a
  frequently-cited annoyance. Select `PL`, keep `PLC`/`PLE`/`PLW` (closer to real bugs), drop `PLR`.
- **Add, same pattern**: `TRY`/tryceratops — directly relevant to §4's exception-hierarchy research.
  Home Assistant selects it but ignores `TRY003` (long exception messages) and `TRY400`
  (`logging.error` vs `.exception`) as too opinionated. Recommend select-then-triage: turn it on,
  see what actually fires, decide ignores from real signal rather than pre-guessing.
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
  rules across 34 categories in v0.16.0 (2026) — exactly the broad-default this repo's config
  comment already deliberately opts out of, now confirmed as a real, recent, documented change
  rather than a stale assumption. The real signal is the pattern across flagship configs above:
  narrow, hand-picked, explicit ignores for noisy subcategories — this repo's existing approach.

**pytest — fixture scope directly ties to §6's singleton-testing concern.** Official rule of thumb:
narrowest scope that keeps tests correct, widen only when setup is genuinely expensive; pytest's own
docs warn that a `monkeypatch` used inside a broad-scoped fixture stays live for the _whole_ scope,
not just one test — the exact mechanism by which a shared-scope fixture silently leaks state across
tests that look independent. **Practical rule for this repo family's module-singleton pattern**:
construct the expensive object at module/session scope, but reset/monkeypatch its _mutable_ state
via a function-scoped fixture — cheap construction stays shared, isolation stays per-test.
`conftest.py`: keep one root file for genuinely cross-cutting fixtures, split per-directory only
once a real subset of tests needs fixtures the rest shouldn't see. `parametrize`: attach `ids` once
values stop being self-explanatory. Marker registration via `markers = [...]` plus
`--strict-markers` (already this repo's convention) matches Litestar's and httpx's own configs
exactly.

**DAMP vs. DRY in tests — a real, sourced debate that does _not_ simply inherit §5's "lean toward
duplication" production-code stance.** Vladimir Khorikov's reframing (Enterprise Craftsmanship, and
echoed by Brian Okken) resolves the popular "DAMP not DRY" framing as a false dichotomy: DRY was
never about _code_ duplication, it's about not duplicating _domain knowledge_. The actionable split:
**setup mechanics (the "how") stay DRY** — pytest fixtures/helpers are exactly the right tool, use
them freely, no tension with anything else in this file — **but test bodies/assertions (the "what" —
the scenario being verified) should stay explicit and duplicated per test**, even when tests look
near-identical, because collapsing them into a shared abstracted mega-test trades away the "read one
test top-to-bottom, understand the scenario" property that's the actual point of a test suite. This
is a genuinely different axis from §5's production-code DRY decision, not a re-derivation of it —
worth stating explicitly in the eventual skill so a reader doesn't assume "this project avoids DRY
everywhere" and over-apply it to test bodies.

**dprint — one real, documented bug to route around, one call this project makes on its own
reasoning.** Markdown plugin defaults: `line_width = 80`, `text_wrap = "maintain"` (tries to
preserve the source's existing wrap decisions). The default `maintain` mode has an **open,
documented bug** — it can delete newlines inside linked/inline-code text in some cases
([dprint-plugin-markdown#149](https://github.com/dprint/dprint-plugin-markdown/issues/149)) — worth
setting `textWrap` explicitly (`always` or `never`) rather than relying on the buggy default,
independent of any style preference. Beyond that: the "docs read by both humans and agents" framing
has thin direct sourcing (flagged honestly, not inflated) — the one concrete, verifiable win found
is that hard-wrapping at a fixed width improves diff/merge-conflict locality (a one-sentence edit
doesn't reflow the whole paragraph in the diff), which is a real, checkable property independent of
any human-vs-agent readability claim.

## Recommended direction

**Confirmed: package as a new Agent Skill, `python-conventions`**, mirroring `db-defaults`' proven
structure — not folded into each repo's own `AGENTS.md`, which the user judged would run into real
maintenance trouble keeping N copies of the same guidance in sync across the family. `SKILL.md` in
the same labeled-line spec-block format the user already approved for `db-defaults`,
`references/rationale.md` carrying this file's full citation trail, and `references/snippets/*.py` —
small, typed, runnable examples per convention (a `globals.py` example with the `cached_property`
caveat inline, a guard-clause/EAFP example, an exception-hierarchy example, a `pydantic-settings`
environment-subclass example). This repo already has the skill-authoring and deployment pipeline
(`inv ai.skills`) built and proven once; reusing it is lower-risk than inventing a second packaging
mechanism for what's structurally the same kind of decision-consistency problem `db-defaults`
solved.

This file stays at `status: idea` — **explicitly, per the user: "just plans, for now."** No skill
build starts until the user says so; per `plan-docs` convention, promoting to `planned` happens in
this same file once that build actually starts.

A second research round (2026-08-15, same day) added five more topics the user pulled in after
reviewing the first pass — ruff/pytest/dprint _configuration_ conventions (tool choice already
decided, only best-practice config was in question), shell-script checking, statelessness,
immutability, a community-precedent check on the `globals.py` settings pattern, and a basedpyright
rule profile tuned for "hard to mess up for agents, not so strict it's pure ceremony." All landed
and are folded into §1 (revised) and new §§7–9 above, in place, per `plan-docs`' "promote in place"
rule — this file was not superseded.

## Open questions

- [NEEDS CLARIFICATION: exact snippet set for the skill — one file per convention (matching
  `db-defaults`' one-file-per-category split, which the user confirmed didn't hurt agent
  readability) or grouped by theme (typing, control-flow, architecture)? §8/§9's tool-config
  findings (basedpyright profile, ruff additions, shellcheck/shfmt invoke tasks) also need a home —
  likely the skill's `references/`, alongside or instead of each repo's own `pyproject.toml`/
  `tasks/quality.py`, since those are config changes a skill can't make on a consuming repo's
  behalf.]
- [NEEDS CLARIFICATION: this repo's _own_ `pyproject.toml`/`tasks/quality.py` is a candidate to
  adopt several of these findings directly, independent of the skill build: `RUF`/`C90`/`PERF`/`A`/
  `DTZ`/`T20`/`PL`(minus `PLR`)/`TRY`(minus noisy codes) added to `select`; `basedpyright` added as
  a new dev dependency with §1's tuned profile; `shellcheck`/`shfmt` added as new `inv quality.*`
  steps for this repo's own `.sh` files (`bootstrap-devcontainer.sh` etc.); `dprint.json`'s markdown
  `textWrap` set explicitly to route around the `maintain`-mode bug. Worth doing here first (as the
  reference implementation, the same role `olx-polite-mcp` played for the scaffolding plan) once the
  user says so, or held until the skill itself is being built?]
- ["and more" — the user's own framing: this is a starting set, not the full scope. Candidates
  raised implicitly by this research but not yet covered: async/concurrency conventions, logging
  conventions, CLI-argument-parsing conventions. Revisit once this batch is packaged rather than
  scope-creeping the current pass.]
