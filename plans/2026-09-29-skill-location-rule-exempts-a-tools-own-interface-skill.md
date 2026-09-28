---
status: idea
updated: 2026-09-29
source_repo: github.com-personal/repo-tasks
source_session: 0a32e30f-5e28-40f1-b57e-78968efbacdd.jsonl
source_moment: 2026-09-28T20:37:04Z
source_plan: plans/2026-09-29-ship-a-skill-for-running-repo-tasks.md
---

# The skill-location rule should exempt a skill describing one tool's own interface

## Context

`config/agents-md/agent-knowledge.md:65` deploys "**Every skill on this machine is authored in
`agent-skills`**" into the global instructions. A repo-tasks session designing a skill for running
repo-tasks' own `inv` tasks stopped on that rule, and the user asked for it to be revisited with
data rather than kept or dropped on instinct.

Two findings:

1. **This repo already decided the exception, and the rule lost it.**
   `plans/2026-08-26-agent-artifact-authoring-decoupling.md`, Design point 5: "Per-repo API skills
   live in the repo they describe, not in `agent-skills`. A skill about `repo-tasks`' interface
   belongs in `repo-tasks`, committed, versioned with the code it documents — the same reason
   `AGENTS.md` is per-repo." The fragment generalised from the convention skills that moved, which
   were all cross-project, and dropped point 5 on the way.
2. **Outside practice splits the same way.** Platform vendors keep skills in dedicated repos (87% of
   the official Claude Code marketplace's external plugins). CLI tools whose skill describes their
   own commands keep it in the tool's repo and release it with the tool — gws, gogcli, sentry-cli,
   playwright-cli, Prisma 8, mergify-cli, firecrawl, beads — and the one counter-example, JetBrains
   teamcity-cli, re-pinned its separate skill repo as a versioned build dependency. Separate
   distribution has observed drift bugs, including a stale `uv tool` CLI beside a newer skill
   (graphify #1568). Full evidence: repo-tasks'
   `plans/2026-09-29-ship-a-skill-for-running-repo-tasks/skill-and-mcp-placement-research.md`.

## Evidence

- Transcript `0a32e30f-5e28-40f1-b57e-78968efbacdd.jsonl`, 2026-09-28T20:37:04Z, the user: "maybe we
  need to revisit the agent-skill exclusivity rule. look online how other projects or authors do
  this. shipping an agent skill or an mcp with an app/tool seems intuitive, but i'd like data and
  your expert analysis on this."
- 2026-09-28, after the research, the user chose to file this plan, the repo-tasks design plan, and
  one for `agent-skills`' `skill-authoring`.

## Open questions

[NEEDS CLARIFICATION: **Exact wording, and does the pointer line change too?** Proposed: "Every
cross-project convention skill is authored in `agent-skills`. A skill describing one tool's own
interface lives in that tool's repo and is released with it; it is installed from there." The
paragraph's second half — edit the source, push, never edit the installed copy — holds for both and
should stay.]

## Recommended direction

1. Reword the paragraph at `config/agents-md/agent-knowledge.md:65` as above, run the fragment
   pipeline, and redeploy with `inv deploy.all --name agents-md`.
2. Update `docs/claude-code.md`'s skills section and the `[packages.agent-skills]` description in
   `setup.toml`, which state the same thing ("No skill is developed in this repo any more" is about
   this repo and stays true; "where they are now authored" reads as exclusive).
3. When repo-tasks' skill exists, add its source to a `skills = [...]` list —
   `{ source = "npx", repo = "TheodoreAD/repo-tasks", … }`, on `[packages.agent-skills]` or its own
   `method = "skill"` block. Blocked on repo-tasks shipping it.
4. Record the settled half of the decoupling plan's open question on per-repo API skills (lines
   613-620) — they live in the repo they describe — and leave "one per repo or one per interface" to
   the repo-tasks pilot.
