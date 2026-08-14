---
name: plan-docs
description: "Use when capturing an idea, drafting a design, or tracking work-in-progress in a repo's plans/ directory — creating or updating a plans/YYYY-MM-DD-topic.md file, choosing or advancing its status, or retiring a landed/abandoned plan once its durable content has a permanent home in code, docs/, or contributing/."
---

# Structured, stateful plan files

Convention for `plans/YYYY-MM-DD-topic.md` — one file per idea or design, a small YAML frontmatter
`status` field so its lifecycle is visible without opening it, and a firm rule that `plans/` stays
a working set, not a permanent archive. Full rationale, prior-art citations, and the reasoning
behind every design choice below: see
[`references/design-rationale.md`](references/design-rationale.md).

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
`## Context` → `## Design` (numbered subsections, one per file/component touched, rationale
inline) → `## Files touched` → `## Verification`.

As work proceeds, bump `status` again — the sections above don't change:

- `in-progress` — actively being built, not done yet.
- `blocked on <reason>` — stalled on something external; the reason lives right in the status
  line, e.g. `blocked on olx-polite-mcp adding the /search endpoint`.
- `landed` — implemented and verified. Transient — see "Retiring a plan" below.
- `abandoned` — killed before landing. Also transient.
- `superseded by plans/<file>.md` — a landed plan whose decision was later reversed by another
  plan; the replacement's path lives in the status string itself.

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
   `docs/*.md` link if the content is usage-facing, and/or a `contributing/<topic>.md` entry (new
   or existing) for design rationale and gotchas — the same bucket `contributing/verify.md` and
   `contributing/cli-allowlist.md` already use in this repo. **Commit this addition on its own,
   before deleting the file** — add-and-delete in the same commit means the section is never
   recorded in git history at all (the deletion commit's diff only ever shows what a _prior_ commit
   last recorded), which defeats the entire point of writing it.
3. Grep the **whole repo**, not just `AGENTS.md`/`docs/`/`contributing/`, for the plan's own
   filename and fix or drop any references before they go stale — code comments and docstrings
   (`tasks/*.py`, etc.) cite plan paths too, not only narrative docs.
4. Delete `plans/<file>.md` — **only** once step 2 is genuinely covered. If there's any doubt
   whether something worth keeping was actually captured, ask before deleting rather than deciding
   unilaterally; it's a one-way door once the commit lands.

## Full reference

[`references/design-rationale.md`](references/design-rationale.md) has the full status-vocabulary
rationale, prior-art citations (MADR, PEPs, Rust RFCs, GitHub Spec Kit), why this deliberately
isn't an ADR-style permanent archive, and the reasoning behind `depends_on` and the retirement
procedure.
