# Design rationale for the `plan-docs` convention

This is the deep version of [`SKILL.md`](../SKILL.md) — why the convention looks the way it does,
what it borrows from established prior art, and what it deliberately rejects. It lives inside the
skill directory, not in a `contributing/`-style doc in whichever repo authored the skill, so it
travels with every copy the skill's distribution mechanism produces — a reader in any repo that
has this skill installed gets the same reasoning a reader of the source repo would.

## Why frontmatter, not filename/prose parsing

A plan's lifecycle state needs to be visible without opening the file (skimming a directory
listing, running a status report across many plans) and without re-deriving it from prose that
might say "landed" in one sentence and mean something looser than the formal sense. A small,
closed-vocabulary YAML frontmatter block is the cheapest mechanism that's both human-editable and
machine-greppable — no parser beyond a YAML frontmatter reader, no ambiguity about what a given
value means.

## Status vocabulary, in full

```yaml
status: idea | planned | in-progress | blocked on <reason> | landed | abandoned | superseded by plans/<file>.md
updated: YYYY-MM-DD
depends_on: [<repo-name>, ...] # optional
```

- **`idea`** — exploratory only: open questions, no committed build order. Use inline
  `[NEEDS CLARIFICATION: ...]` markers (borrowed verbatim from GitHub Spec Kit's `spec.md`
  template) for each unresolved point instead of a loose prose list — it's greppable
  (`rg "NEEDS CLARIFICATION" plans/`) across every idea-stage plan in the repo at once, so nothing
  requires opening every file to find what's still unresolved. Resolve every marker before
  promoting to `planned`.
- **`planned`** — full design written (Context/Design/Files touched/Verification), not yet
  started. Named to match Spec Kit's and Rust RFC's own vocabulary for the same stage, rather than
  inventing a new word for something that already has a common name.
- **`in-progress`** — actively being implemented, not yet landed. The single most valuable
  addition over a smaller status set: without it, "fully designed, not started" and "half-built,
  then went quiet" are indistinguishable months later, which defeats the entire point of tracking
  status at all.
- **`blocked on <reason>`** — started (or planned), then stalled on something external: an
  upstream fix, a decision, hardware, another repo's change (see `depends_on` below). The reason
  lives inline in the status string — same string-folding pattern as `superseded by`, no separate
  field to maintain. Mirrors Rust RFC's `postponed` and PEP's `Deferred`, without either's
  multi-year governance weight.
- **`landed`** — implemented and verified. **Transient, not a resting state** — see "Retirement,
  not archiving" below. This is the one place this design deliberately parts ways with ADR/PEP
  convention, where the equivalent status (`accepted`/`Final`) is permanent.
- **`abandoned`** — explicitly killed before landing. Also transient.
- **`superseded by plans/<file>.md`** — a `landed` plan whose decision was later reversed by
  another plan; the replacement's path is folded directly into the status string rather than
  living in a separate field. Also transient, once the successor itself lands.

No `created:` field: the filename's date already is the creation date, and repeating it violates
the general principle of not adding a field "just in case" it's useful. `updated:` is the one
genuinely new fact frontmatter adds — freshness at a glance, without `git log` or parsing the
filename.

### `depends_on`: cross-repo dependencies

A single-machine, poly-repo setup (a shared tooling repo, several small standalone-tool repos, and
whatever else this skill gets installed into) means a plan in one repo can genuinely require a
change in another repo first. `depends_on: [<repo-name>, ...]` — a flat list of bare repo names —
records that fact structurally instead of only in prose. It complements rather than duplicates
`blocked on <reason>`: `depends_on` is the structural, greppable fact of _which_ repos a plan
touches (usable across an entire multi-repo tree, e.g. `rg "^depends_on:" */plans/*.md` from the
parent directory that holds every repo as a sibling), while `blocked on <reason>` is the lifecycle
statement of _why work is currently stalled_, which may or may not be about a cross-repo
dependency at all. Optional, omitted by default — most plans are single-repo and gain nothing from
it.

## Retirement, not archiving

Architecture Decision Records, Python PEPs, and Rust RFCs all use an explicit status field — and
all three keep every record forever, because their job is durable institutional memory: "can this
decision still be trusted?", asked years later, by people who weren't there when it was made. That
permanence is a deliberate, reasonable choice for those formats, and a deliberate **non-goal**
here. `plans/` is meant to be a working set that empties out over time, not an ever-growing
archive that has to be read cover-to-cover to know what's still true.

That doesn't mean discarding freely, though. A plan file itself is disposable once its content is
safely elsewhere — but anything that was genuinely costly to work out (debugging that took more
than a couple of tries, an investigation with a non-obvious conclusion, rejected alternatives and
why) is presumed to have future value until proven otherwise, never dropped just because the code
shipped. A plan's durable content has exactly three legitimate final homes:

1. **The executed code itself** — for changes that need no further explanation beyond what the
   code and its own comments already carry.
2. **`docs/*.md`** — for anything usage-facing, i.e. how a person or agent uses the result.
3. **`contributing/*.md`** — for design rationale and hard-won gotchas. Some repos already have
   exactly this bucket (e.g. `contributing/verify.md`/`contributing/cli-allowlist.md` in the repo
   this skill was authored in — "every gotcha the first implementation pass hit," read before
   re-deriving or "simplifying" something that was already a deliberate tradeoff). If a repo
   doesn't yet have a `contributing/` convention, a plan's rationale can still go in a `docs/`
   section or a code comment, whichever fits — the requirement is _somewhere durable_, not this
   exact directory name.

Once a plan's content is genuinely in one of those three homes, the plan file has no remaining
job. Git history is the fallback permanent record for the _file_ itself, if anyone ever needs to
dig up exactly how it was worded — but that fallback exists for recovering an old plan file, not
as a substitute for actually migrating content someone would otherwise have to dig through git log
to rediscover. The retirement procedure in `SKILL.md` operationalizes this: preserve by default,
name the destination explicitly, fix any references that would otherwise dangle, and only delete
once that's genuinely done — asking first whenever there's real doubt, since deletion is a
one-way door that git history only partially undoes (it recovers the file, not the judgment call
that nothing in it still mattered).

## Relationship to a repo's own `AGENTS.md`

`status:` frontmatter is a plan's own machine-greppable lifecycle marker, updated the moment its
state changes. A repo's `AGENTS.md` (or equivalent) typically stays a separate, curated narrative
index of what's currently true about the repo, written at landing time. The two are decoupled
day-to-day — don't strip "landed"-style language out of `AGENTS.md` just because a plan's
frontmatter also says so, since it serves a different reader (someone skimming for context, not
auditing plan state) — but retirement is the one moment they must be kept in sync: once a plan
file is actually deleted, any `AGENTS.md` prose citing that exact path needs to be repointed (to
wherever the content actually migrated) or have the dead reference dropped.

## Prior art

Checked how established communities solve "dated proposal document with a lifecycle" before
settling on this design — mechanics were borrowed where they were good and cheap, ceremony and
permanence were rejected where they didn't fit a personal/small-team, poly-repo, single-machine
context:

- **MADR (Markdown Architectural Decision Records)** — [adr.github.io/madr](https://adr.github.io/madr/),
  the de facto standard ADR format. Its
  [template](https://raw.githubusercontent.com/adr/madr/main/template/adr-template.md) uses flat
  YAML frontmatter with `status: "{proposed | rejected | accepted | deprecated | … | superseded by
  ADR-0123}"` and `date: {when the decision was last updated}` — the direct source for this
  design's minimal-frontmatter approach, `date`/`updated` meaning _last touched_ rather than
  _created_, and folding a supersession pointer straight into the status string instead of a
  separate field. ADRs are immutable once `accepted` — "corrections to typos and link rot are
  fine, but conclusions are not edited; write a new ADR that supersedes this one" — which is
  exactly the permanence this design rejects for `landed`.
- **Python PEPs** — [peps.python.org/pep-0001](https://peps.python.org/pep-0001/) — a richer
  status vocabulary (`Draft, Active, Accepted, Provisional, Deferred, Rejected, Withdrawn, Final,
  Superseded`) for a much bigger, multi-year governance process. Confirms the general pattern
  (single closed-vocabulary status field on a dated proposal doc) but is overkill here — states
  like `Provisional`/`Deferred` weren't worth importing.
- **Rust RFCs** — [rust-lang.github.io/rfcs](https://rust-lang.github.io/rfcs/) — `draft → active
  (accepted, not yet implemented) → complete/inactive`, plus a `postponed` state for stalled RFCs.
  The same core progression this design lands on (idea/planned/landed, plus `blocked on ...`
  mirroring `postponed`), arrived at independently before the comparison was made.
- **GitHub Spec Kit** — [github.com/github/spec-kit](https://github.com/github/spec-kit),
  `spec-driven.md` — the most directly comparable AI-agent-era prior art. Uses `spec.md` →
  `plan.md` → `tasks.md` per feature, but deliberately carries **no status frontmatter at all**:
  these are living documents "edited in place... when requirements change, you update the
  specification," with freshness implicit rather than explicit. It also keeps a separate
  `memory/constitution.md` holding immutable, repo-wide governing principles checked against every
  spec — the same shape as a repo's own `AGENTS.md` staying a separate narrative/governance layer,
  independent validation of keeping plan frontmatter decoupled from it day-to-day. Spec Kit was
  also checked specifically for how it handles pre-spec ideation: it deliberately ships no
  `/brainstorm` command (community consensus: AI is capable enough without one, and a formal
  brainstorming step risks bloated, overengineered pre-specs), and real-world adopters keep
  ideation in a wholly separate system (a ticket tracker, a chat scratchpad) rather than inside
  Spec Kit's own tracked files at all — a gap this design closes by giving `idea` its own status
  and section template inside the same file, rather than punting ideation to a second system.
- **Claude Code's own plan mode** — no persistent status convention of its own; a plan is
  transient until approved, then the plan file's job is done. Confirms there's no existing
  Anthropic-sanctioned answer to "how do I track a plan after approval" — this convention fills a
  real gap rather than duplicating a built-in mechanism.

**Takeaway:** the decision-record camp (ADR/PEP/RFC) uses explicit status _and_ keeps every record
forever, because their job is permanent institutional memory. GitHub Spec Kit skips status
entirely because its documents are continuously rewritten and never really "finish," and punts
pre-spec ideation to a different, disconnected system. This design borrows the decision-record
camp's cheap, greppable status mechanics and the living-document camp's in-place-editing spirit,
but rejects both camps' actual endpoints: not permanent archiving, and not open-ended living
documents either — every plan is meant to terminate in a deliberate migrate-then-delete step.
