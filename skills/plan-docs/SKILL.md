---
name: plan-docs
description: "Use when capturing an idea, drafting a design, or tracking work-in-progress in a repo's plans/ directory — creating or updating a plans/YYYY-MM-DD-topic.md file, choosing or advancing its status, retiring a landed/abandoned plan once its durable content has a permanent home in code, docs/, or contributing/, migrating a repo's legacy monolithic plan file (PLAN.md, DESIGN.md, ...) onto this convention, or auditing AGENTS.md for planning/status content that has drifted in and belongs elsewhere."
---

# Structured, stateful plan files

Convention for `plans/YYYY-MM-DD-topic.md` — one file per idea or design, a small YAML frontmatter
`status` field so its lifecycle is visible without opening it, and a firm rule that `plans/` stays a
working set, not a permanent archive. Full rationale, prior-art citations, and the reasoning behind
every design choice below: see [`references/design-rationale.md`](references/design-rationale.md).

## Creating a plan

New idea → `plans/YYYY-MM-DD-topic.md` (date = today, topic = kebab-case, one file per topic).
Frontmatter:

```yaml
---
status: idea
updated: YYYY-MM-DD
---
```

Body: `## Context` → `## Open questions` (mark each unresolved point with an inline
`[NEEDS CLARIFICATION: ...]` tag, greppable via `rg "NEEDS CLARIFICATION" plans/`) →
`## Recommended direction` (rough, non-prescriptive).

## Promoting a plan

Promote in place, in the same file — never split into a second file for the same topic. Resolve
every `NEEDS CLARIFICATION` marker, then bump `status` to `planned` and rewrite the body as
`## Context` → `## Design` (numbered subsections, one per file/component touched, rationale inline)
→ `## Files touched` → `## Verification`.

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

1. **Default: preserve.** Assume debugging, investigation, and rejected-alternative reasoning has
   future value unless it's already written down elsewhere in the repo. Often it already is — check
   `docs/*.md` before assuming new `contributing/*.md` content is needed; a plan whose design
   rationale is already fully covered in prose there needs no new file at all.
2. Add a `## Migrated to` section naming the destination: nothing needed for pure-code changes, a
   `docs/*.md` link if the content is usage-facing, and/or a `contributing/<topic>.md` entry (new or
   existing) for design rationale and gotchas — the same bucket `contributing/verify.md` and
   `contributing/cli-allowlist.md` already use in this repo. **Commit this addition on its own,
   before deleting the file** — add-and-delete in the same commit means the section is never
   recorded in git history at all (the deletion commit's diff only ever shows what a _prior_ commit
   last recorded), which defeats the entire point of writing it.
3. Grep the **whole repo**, not just `AGENTS.md`/`docs/`/`contributing/`, for the plan's own
   filename and fix or drop any references before they go stale — code comments and docstrings
   (`tasks/*.py`, etc.) cite plan paths too, not only narrative docs. Don't blindly swap the old
   path for the new one at every hit, though: a reference to a _specific quoted section title_
   (`PLAN.md "Setup"`) needs that title updated to match wherever that content actually landed, not
   just the path — a technically-valid path pointing at the wrong or a since-renamed heading is
   still a dangling reference. And some cited content may already be duplicated at a third location
   (e.g. an operational recipe that was always also written out in full in `AGENTS.md`) — point the
   reference at that existing copy instead of migrating a second copy into `contributing/`.
4. Delete `plans/<file>.md` — **only** once step 2 is genuinely covered. If there's any doubt
   whether something worth keeping was actually captured, ask before deleting rather than deciding
   unilaterally; it's a one-way door once the commit lands.
5. Run the repo's own lint/format/test commands before committing the reference fixes — editing many
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

## Keeping AGENTS.md itself clean

A repo's `AGENTS.md` (or equivalent instructions file) should only ever hold instructions for
developing/deploying the repo — never planning or ideation, and never a status report. It drifts
away from that over time in two recognizable ways worth auditing for, independent of any specific
plan's lifecycle:

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
