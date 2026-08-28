---
status: idea
updated: 2026-08-23
---

## Context

Split out of `plans/2026-08-23-cross-repo-skill-feedback-capture.md` on 2026-08-23. That plan needed
a channel for reporting a skill/`~/AGENTS.md` problem found while working in a _different_ repo, and
picked "write a plan file directly into `power-user-linux-setup/plans/`", with
`gh issue create -R
TheodoreAD/power-user-linux-setup` as a fallback for when this repo's working
tree isn't reachable at all (dev container, WSL, another machine, cloud session).

The user's read is that issues are **probably the cleaner approach overall** — not just the
fallback. That's plausible enough to design properly rather than decide in passing, and big enough
that folding it into the capture plan would have blocked that plan on a question it doesn't need
answered to land. Hence this file.

What makes it non-trivial: `plans/*.md` (the `plan-docs` skill) is already a complete lifecycle —
`idea` → `planned` → `in-progress`/`blocked on X` → `landed`/`abandoned`/`superseded by`, then a
retirement procedure that migrates durable content to `docs/`/`contributing/` and deletes the file.
GitHub issues have their own lifecycle (open/closed, labels, milestones). Adopting issues without
deciding how the two relate produces the worst outcome: two half-tracked backlogs where an item can
be open in one and dead in the other, and no single place that answers "what's actually pending".

**Settle `agent-skills`' `plans/2026-08-28-cross-repo-plan-store.md` first.** That plan asks where
the durable plan store lives at all — per-repo `plans/`, one central location, or a tracker mirrored
down to markdown — and this file's "issue as inbox vs. issue as backlog" choice is downstream of it.
Answering this one first risks designing an issue lifecycle around a store that then moves. It lives
in `agent-skills` because that repo owns the `plan-docs` convention; it was drafted here, and its
research history is in this repo up to commit `c4053e4`.

Current state, verified 2026-08-23: `gh` is installed, issues are enabled on
`TheodoreAD/power-user-linux-setup`, and there are **zero** issues, open or closed. So this is a
clean adoption with no migration burden — and equally, no existing habit pulling in its favour.

## Open questions

- [NEEDS CLARIFICATION: what is an issue actually _for_ — inbound reports only (a field report from
  another repo, triaged into a plan file), or the whole backlog (every `plans/*.md` gets a companion
  issue)? These are very different designs. The first is additive and cheap; the second replaces
  `plans/` as the index of pending work and needs a much stronger justification.]
- [NEEDS CLARIFICATION: does an issue ever hold design content, or is it strictly a pointer? Lean:
  strictly a pointer plus evidence — the design lives in the plan file, because that's what gets
  reviewed, formatted by the repo's own gate, and read by future agents from the working tree. An
  issue body is invisible to a session working offline in the repo.]
- [NEEDS CLARIFICATION: what closes the issue, and who? Options: triage (issue → plan file created,
  close immediately, plan file owns it from there), or landing (issue stays open until the plan is
  `landed`, giving a single "what's pending" view across both). The first keeps issues as an inbox;
  the second makes them the backlog.]
- [NEEDS CLARIFICATION: how does the link survive in both directions? Plan frontmatter could carry
  `issue: 12`; the issue body carries the plan path. Both are hand-maintained and both rot. Is there
  a check worth adding to `inv quality.*` (or a small `inv plans.*` task) that flags a plan citing a
  closed issue, or an open issue whose plan file no longer exists?]
- [NEEDS CLARIFICATION: does this generalize to the other repos in the family (`repo-tasks`,
  `scaffoldapy`, the `*-polite-mcp` set), or is it specific to this repo's role as the user-wide
  source of truth? `~/AGENTS.md` "Cross-repo family conventions" says convergence work should
  produce one mandatory identical composite, which argues for deciding this once for all of them
  rather than adopting it here only.]
- [NEEDS CLARIFICATION: does the offline case break it? A capture written from a machine with no
  network can't open an issue. If issues become primary, the plan-file path has to stay as the
  offline fallback — which means both channels exist permanently and the lifecycle has to handle an
  item arriving by either route.]

## Recommended direction

Rough, deliberately non-prescriptive until the questions above are answered.

**Most likely shape: issue as inbox, plan file as the work item.** An issue is opened only for a
report that arrives from outside this repo's working tree; it carries the same body template the
capture plan defines (source repo, session-id/transcript path, timestamp, verbatim correction,
repro) and nothing more. Triage in a session _in_ this repo converts it to a
`plans/YYYY-MM-DD-topic.md` with the provenance frontmatter, links both ways, and closes the issue.
`plans/` stays the single answer to "what's pending"; issues answer "what hasn't been triaged yet",
a queue that should normally be empty.

This keeps `plan-docs` unchanged except for one new optional frontmatter field and a short "arrived
as an issue" note, and it avoids the two-backlogs failure entirely — an issue is never open at the
same time as an active plan for the same thing.

The alternative worth actually weighing before settling: **issue as the durable backlog**, where the
issue stays open until the plan lands, `plans/` becomes purely the design document store, and issue
labels carry `status`. That buys a backlog visible from a phone and from repos/machines that don't
have this one checked out — a real advantage given the whole premise here is that friction surfaces
elsewhere. It costs the ability to see pending work offline and duplicates the status vocabulary
`plan-docs` already defines.

Do not start using issues ad hoc before this is settled — an inconsistently-used tracker is worse
than none, and with zero issues today there is nothing to unwind.
