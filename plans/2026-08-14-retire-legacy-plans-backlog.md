---
status: idea
updated: 2026-08-14
---

# Retire legacy plans/ backlog

## Context

The `plan-docs` skill (`skills/plan-docs/`) introduces a retirement rule: `plans/` is a working
set, not a permanent archive. A `landed`/`abandoned`/`superseded` plan's durable content belongs in
code, `docs/*.md`, or `contributing/*.md` — never left sitting in `plans/` indefinitely — and only
once that migration is done does the plan file get deleted.

The 3 plans that were `landed` before this rule existed (`2026-08-08-devcontainer-pipeline.md`,
`2026-08-10-corporate-proxy-daemon.md`, `2026-08-13-devcontainer-mounts.md`) were retrofitted with
`status: landed` frontmatter but deliberately **not** retired in that same change — deciding where
each one's content actually belongs is real per-file judgment, not a mechanical edit. This plan is
that judgment call, done properly, one file at a time.

## Open questions

- `[NEEDS CLARIFICATION: does 2026-08-08-devcontainer-pipeline.md's content need a new
  contributing/*.md entry, or is docs/dev-container.md (which already links to it, "for the design
  history behind the recommended...") a sufficient permanent home once folded in directly?]`
- `[NEEDS CLARIFICATION: does 2026-08-13-devcontainer-mounts.md need its own contributing/*.md, or
  can its content merge into a broader contributing/dev-container.md alongside the pipeline plan's
  content, given AGENTS.md already narrates both under one "Dev container distribution pipeline"
  section?]`
- `[NEEDS CLARIFICATION: 2026-08-10-corporate-proxy-daemon.md's own header already reads almost
  verbatim as contributing/*.md material ("Design record, not usage docs... preserve why the
  design landed here: what was considered and rejected") — is a near-direct move to
  contributing/corporate-proxy.md correct, or does some of it belong folded into
  docs/corporate-proxy.md instead?]`
- `[NEEDS CLARIFICATION: to-migrate/windows-corporate-proxy-notes.md references
  plans/2026-08-10-corporate-proxy-daemon.md three times — does that file get updated as part of
  this retirement, or is it out of scope since it lives in to-migrate/ (its own pending-work area)?]`

## Recommended direction

For each of the 3 plans, follow the `plan-docs` retirement procedure
(`skills/plan-docs/SKILL.md#retiring-a-plan`): write or extend the appropriate `contributing/*.md`
entry (or confirm an existing `docs/*.md` link already suffices), add a `## Migrated to` section to
the plan recording the decision, fix `AGENTS.md`'s two existing pointers (`AGENTS.md:79` and
`AGENTS.md:91`) plus `docs/dev-container.md:15` and the `to-migrate/` references, then delete the
plan file. `corporate-proxy-daemon.md` looks like the clearest single case — its own text is
already `contributing/`-shaped — so do it first as the template for the other two.
