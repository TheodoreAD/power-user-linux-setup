---
name: plan-docs
description: "Use when capturing an idea, drafting a design, or tracking work-in-progress in a repo's plans/ directory — creating or updating a plans/YYYY-MM-DD-topic.md file (including for a bug, idea, or risk turned up incidentally by other work, not just a deliberate planning request), choosing or advancing its status, retiring a landed/abandoned plan once its durable content has a permanent home in code, docs/, or contributing/, migrating a repo's legacy monolithic plan file (PLAN.md, DESIGN.md, ...) onto this convention, or auditing AGENTS.md/README.md/docs for planning/status/future-work content that has drifted in and belongs in plans/ instead."
---

# Structured, stateful plan files

Convention for `plans/YYYY-MM-DD-topic.md` — one file per idea or design, a small YAML frontmatter
`status` field so its lifecycle is visible without opening it, and a firm rule that `plans/` stays a
working set, not a permanent archive. Full rationale, prior-art citations, and the reasoning behind
every design choice below: see [`references/design-rationale.md`](references/design-rationale.md).

## Creating a plan

Not just for deliberate "let's design something" requests — the same trigger applies whenever other
work incidentally turns up a bug worth fixing later, an idea worth brainstorming, or a risk worth
mitigating that isn't being handled right now. That goes into its own `plans/YYYY-MM-DD-topic.md`
(`status: idea`), never left as pending/future-work prose in `README.md`, `AGENTS.md`, `docs/*.md`,
or a code comment — those describe current state, not a to-do list, and prose future-work has no
status field, so nothing ever prompts anyone to circle back (see "Don't stash future work in prose
docs" below, which generalizes what "Keeping AGENTS.md itself clean" already said just for
`AGENTS.md`). Confirmed live 2026-08-23: a real, already-identified test-coverage gap
(`scaffoldapy`'s `library` interface can't be covered by its e2e quality-check test) sat as a
sentence in `README.md` — "a real gap... not yet fixed" — instead of a plan file, so it was
invisible to anything that scans `plans/` for open work.

New idea → `plans/YYYY-MM-DD-topic.md` (date = today, topic = kebab-case, one file per topic).
Frontmatter:

```yaml
---
status: idea
updated: YYYY-MM-DD
---
```

Body: `## Context` → `## Open questions` (mark each unresolved point with an inline
`[NEEDS CLARIFICATION: ...]` tag — see "Tags" below) → `## Recommended direction` (rough,
non-prescriptive).

## Committing a plan file

A plan file goes through the repo's quality gate like any other change — run it
(`inv quality.precommit` in repos on the repo-tasks quality tasks, or the repo's own equivalent)
before committing any `plans/*.md` create, update, or retirement. "Just markdown" is not an
exemption: dprint reformats markdown prose (line-wrap reflow), and doc-only commits that skipped the
gate were the one recurring CI-failure cause across this machine's repos (confirmed 2026-08-23 —
every recurring failure was a `plans/*.md`/`AGENTS.md`/`SKILL.md` reflow that `dprint fmt` would
have fixed locally).

## Tags

Five inline markers, all `[SHOUTY-WORD: text]`. They exist so the judgment calls below become greps
instead of re-reads, and so nothing costly is lost when a file is deleted.

| tag                        | means                                           | at retirement                          |
| -------------------------- | ----------------------------------------------- | -------------------------------------- |
| `[NEEDS CLARIFICATION: …]` | open question                                   | must be zero to leave `idea`           |
| `[DECISION: …]`            | settled choice + why it beat the alternatives   | → `contributing/`                      |
| `[PITFALL: …]`             | non-obvious trap, confirmed by hitting it       | → `contributing/`                      |
| `[DEFERRED: …]`            | consciously scoped out, still wanted            | → an open plan; **blocks deletion**    |
| `[UNVERIFIED: …]`          | designed or implemented but not actually proven | → verify or defer; **blocks `landed`** |

Five is the whole vocabulary. A larger set doesn't get applied consistently, and inconsistent tags
are worse than none — they make the greps look authoritative while being incomplete. There is
deliberately no `[VERIFIED:]`: that is a landed plan's default state, so tagging it would mark
everything and destroy the signal. What matters is the _absence_ of `[UNVERIFIED:`.

Not bare `TODO`/`FIXME`: those collide with code comments, so `rg TODO` is useless in a repo that
also contains source.

**Tag the claim, not the section** — one tag per discrete, individually-extractable fact. A tag
scoped to "everything below this heading" can't be migrated mechanically, which is the whole point.

**A tag opens its own line**, starting a paragraph or immediately following a list marker. This is
what makes the greps precise: an unanchored `rg '\[DEFERRED:'` also matches every prose _mention_ of
a tag, so any document discussing the convention reports a false backlog. Anchor them:

```shell
rg '^\s*[-*]?\s*\[DEFERRED:' plans/          # the repo's whole backlog, no file opened
rg '^\s*[-*]?\s*\[NEEDS CLARIFICATION:' plans/<file>.md
```

Tagging is required at status transitions, not while drafting — those are the moments someone is
already reading the file closely. Retrofit a repo's existing plans in one pass rather than lazily; a
half-tagged corpus is the failure mode above.

## Promoting a plan

Promote in place, in the same file — never split into a second file for the same topic. Resolve
every `NEEDS CLARIFICATION` marker (the promotion gate: that grep must come back empty), then bump
`status` to `planned` and rewrite the body as `## Context` → `## Design` (numbered subsections, one
per file/component touched, rationale inline) → `## Files touched` → `## Verification`.

As work proceeds, bump `status` again — the sections above don't change:

- `in-progress` — actively being built, not done yet.
- `blocked on <reason>` — stalled on something external; the reason lives right in the status line,
  e.g. `blocked on olx-polite-mcp adding the /search endpoint`.
- `landed` — implemented and verified. Transient — see "Retiring a plan" below.
- `abandoned` — killed before landing. Also transient.
- `superseded by plans/<file>.md` — a landed plan whose decision was later reversed by another plan;
  the replacement's path lives in the status string itself.

Optional `depends_on: [<repo-name>, ...]` frontmatter names other repos on this machine that this
plan can't fully land without — omit it for the ordinary single-repo case.

## Retiring a plan

On reaching `landed`, `abandoned`, or an old `superseded by ...`: `plans/` is a working set that
empties out, not an ADR-style archive — but nothing genuinely costly to work out gets silently
dropped either.

**Triage the file's content by lifecycle first.** Split by what each passage _is_, never by how long
the file is — a long file that is all one lifecycle stays one file, while a short one mixing several
gets split. Most plans hold four or five distinguishable kinds:

| kind               | example                                   | destination                         |
| ------------------ | ----------------------------------------- | ----------------------------------- |
| settled decision   | why tool X beat tool Y, with the evidence | `contributing/`                     |
| pitfall            | a trap confirmed by hitting it            | `contributing/`                     |
| code contract      | signatures, flags, behavior               | already in code/tests/README — drop |
| verification log   | "ran it, it worked", dry-run transcripts  | drop, except the unverified residue |
| **live open work** | anything still wanted but not done        | **an open plan — see step 2**       |

Code contracts and verification logs are usually the bulk of the deletable volume.

1. **Default: preserve.** Assume debugging, investigation, and rejected-alternative reasoning has
   future value unless it's already written down elsewhere in the repo. Often it already is — check
   `docs/*.md` before assuming new `contributing/*.md` content is needed; a plan whose design
   rationale is already fully covered in prose there needs no new file at all.
2. **A plan carrying live unfinished work is not deletable.** Run the deletion gate —
   `rg '^\s*[-*]?\s*\[DEFERRED:|^\s*[-*]?\s*\[UNVERIFIED:' plans/<file>.md` — and move everything it
   finds into a plan that stays before going further. This is the "Don't stash future work in prose
   docs" rule applied to plans themselves: a `landed` plan is the same failure mode one level up,
   and worse, because this procedure ends in `rm`. Prefer appending the item to an existing open
   plan that already owns the concern over spawning a new file. On an untagged legacy plan, grep
   prose instead (`deferred|not yet|follow-up|TODO|known limitation`) and read what it finds.
3. **Grep inbound references before starting, not after** — the count decides whether this is one
   commit or several, and retiring a batch means rewiring a citation graph rather than fixing a
   couple of links. Grep the **whole repo**, not just `AGENTS.md`/`docs/`/`contributing/`: code
   comments and docstrings cite plan paths too. Match on the bare filename, not the full `plans/`
   path — short-form references (`docker-image-tasks.md`) are easy to miss otherwise.
4. Add a `## Migrated to` section naming the destination: nothing needed for pure-code changes, a
   `docs/*.md` link if the content is usage-facing, and/or a `contributing/<topic>.md` entry (new or
   existing) for design rationale and pitfalls. Name what you deliberately did _not_ migrate, and
   why. **Commit this addition on its own, before deleting the file** — add-and-delete in the same
   commit means the section is never recorded in git history at all (the deletion commit's diff only
   ever shows what a _prior_ commit last recorded), which defeats the entire point of writing it.
   - Organize `contributing/` by **the question a reader arrives with**, not one file per retired
     plan (that just reproduces each plan's own lifecycle mixing under a new name). Expect the most
     valuable file to be one that existed in no single plan — cross-cutting conventions are usually
     scattered across several.
   - Before dropping anything as "already in the code," actually check it is. Verify the claims you
     migrate, too: prose written months ago about a module drifts, and a plan is not evidence about
     current behavior.
5. Fix the references from step 3, then delete `plans/<file>.md` — **only** once step 4 is genuinely
   covered. If there's any doubt whether something worth keeping was captured, ask before deleting
   rather than deciding unilaterally; it's a one-way door once the commit lands.
   - Don't blindly swap the old path for the new one at every hit: a reference to a _specific quoted
     section title_ (`PLAN.md "Setup"`) needs that title updated to match wherever the content
     actually landed — a valid path aimed at a since-renamed heading is still dangling. Some cited
     content may already be duplicated at a third location (an operational recipe also written out
     in `AGENTS.md`) — point at that existing copy rather than migrating a second one. And some
     references are better rewritten than repointed: "X landed in `<plan>`" just becomes "X landed."
   - The finishing grep should return **no live pointers**, which is not the same as zero hits.
     Provenance legitimately survives ("extracted from the now-retired `plans/X.md`") and should —
     but must say _retired_, so a reader knows not to go looking. Only a bare path offered as
     somewhere to read more is dangling.
6. Run the repo's own lint/format/test commands before committing the reference fixes — editing many
   docstrings/comments in one pass is exactly the kind of change that quietly trips a line-length
   rule or similar, and it's cheap to catch immediately rather than in a later session.

## Migrating a legacy single plan file onto this convention

A repo that predates this convention often has one big `PLAN.md`/`DESIGN.md`/`NOTES.md` mixing
several unrelated threads at different lifecycle stages in one file. Don't retire it as a single
unit — first split it by thread, then apply the lifecycle above to each piece:

1. Read the whole file and sort its sections into threads: fully implemented/verified content (→
   `landed`), a thread that's genuinely still undecided or stalled (→ its own new
   `plans/YYYY-MM-DD-topic.md`, `status: blocked on <reason>` or `idea`), and content that's just
   inaccurate now (a described design that was later replaced — drop it, it has no destination). A
   single legacy file routinely turns into zero, one, or several `plans/*.md` files, not one.
2. Run the `landed` threads through "Retiring a plan" above immediately, in the same pass — there's
   no reason to first copy them verbatim into `plans/` only to retire them a moment later.
3. Give the still-open thread(s) a real plan file with correct frontmatter, not a leftover fragment
   of the old file's prose — reformat into `## Context` / `## Design` / `## Open questions` as the
   status warrants, same as any other plan.
4. Only once every thread has a home does the legacy file itself get a `## Migrated to` section
   (naming every destination, since there may be several) and go through the normal commit-then-
   delete sequence.

## Don't stash future work in prose docs

Applies to any narrative doc in a repo — `README.md` and `docs/*.md` included, not only `AGENTS.md`.
Each should describe the repo as it is right now; a known bug, an unfinished feature, or an open
risk belongs in its own `plans/*.md` entry (`status: idea` or further along), linked from the doc if
it's worth a pointer, not spelled out in prose there. Prose future-work has no status field and
nothing ever prompts a return visit — it just rots into a permanently-true-sounding sentence, or,
worse, an already-fixed problem left calling itself "not yet fixed" (exactly what "Stale
implementation claims" below catches, but the fix is to not write it that way in the first place).

`AGENTS.md` (or an equivalent instructions file) gets the strictest version of this rule: it should
only ever hold instructions for developing/deploying the repo — never planning, ideation, or a
status report. It drifts away from that over time in two recognizable ways worth auditing for,
independent of any specific plan's lifecycle:

- **Dated status narrative.** A heading like "Status: implemented and exercised live 2026-08-14"
  reads as a changelog entry, not an instruction — it's true today and stale tomorrow. Trim it to an
  undated statement of _what's actually true about the architecture right now_ (which module backs
  which behavior), and drop the "as of `<date>`, confirmed working, tests pass" framing entirely —
  that belongs in a commit message or, if it needs to persist, `contributing/*.md`.
- **Stale implementation claims.** Prose describing something as unfinished ("these functions are
  stubs," "not yet confirmed") silently rots once the work lands, and nobody remembers to update the
  sentence that made it true. Don't just prose-review these claims — grep the actual code for the
  thing being described (e.g. `rg NotImplementedError` before trusting a docstring that says a
  function raises it) before deciding whether a passage is still accurate, superseded, or safe to
  cut.
- **Speculative asides.** "This might be cheaper to do a different way once X is understood" isn't
  an instruction either — it's a musing. Either it's a real open question worth its own `plans/*.md`
  idea file, or it's color already captured in `contributing/*.md`'s design rationale and can just
  be dropped from `AGENTS.md` without losing anything.

## Full reference

[`references/design-rationale.md`](references/design-rationale.md) has the full status-vocabulary
rationale, prior-art citations (MADR, PEPs, Rust RFCs, GitHub Spec Kit), why this deliberately isn't
an ADR-style permanent archive, and the reasoning behind `depends_on` and the retirement procedure.
