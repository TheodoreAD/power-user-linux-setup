---
status: idea
updated: 2026-09-02
---

# What the `.agents` structure already supports, and for whom

## Context

Asked 2026-09-02, out of the docs review's decision about `docs/ai.md`
(`plans/2026-08-27-docs-site-usability.md`): _"we should clarify that we offer the agnostic
structure that works for not just claude. actually, you should make a plan to see what we can
support with the current .agents structure. i'm sure we've visited this before."_

The framing that makes it worth answering, from the same message: _"we don't choose the tools, devs
do, and it's our job to show we give them better experiences for whichever tools we can."_ So the
question is not "which agent should PULSE bless" — it is **which agents a machine PULSE provisioned
already works for, without anyone doing anything else**, and what the gap is for the rest.

It has been visited before, in pieces, and none of the pieces is a matrix:

- `plans/2026-08-30-portable-fragment-names-one-harness.md` (in-progress) settled that the Claude
  Code rules in `~/AGENTS.md` stay and get **labelled** rather than genericised, and that the
  anticipated future is _adding_ a second harness's instructions. That plan owns the fragment axis;
  this one owns the harness inventory. They cite each other rather than merging.
- `plans/2026-08-26-agent-artifact-authoring-decoupling.md` owns why `~/AGENTS.md` is assembled from
  fragments at all.
- `docs/claude-code.md` documents the convention itself — `AGENTS.md` as the cross-tool file, why
  `CLAUDE.md` is a symlink and never an `@import`, and that Copilot is _checked_ but never written
  to.

## What is actually wired today

Read off `setup.toml` and `tasks/ai.py` 2026-09-02, not from memory:

**`~/AGENTS.md` is deployed once and symlinked into four agents' homes** — `[packages.agents-md]`'s
`symlink_dest`: `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.copilot/copilot-instructions.md`,
`~/.gemini/GEMINI.md`. A link whose parent directory does not exist is reported and skipped, and
that absence is exactly how an uninstalled agent is detected — so the mechanism already degrades per
machine with no configuration.

**Skills are installed once into `~/.agents/skills/`**, with `~/.claude/skills` symlinked to it
because Claude Code does not read `.agents/skills/` natively. `[packages.agent-skills]` declares
`agents = ["claude-code", "github-copilot"]` for the `skills` CLI; `tasks/ai.py` defaults that list
to `["claude-code"]` when a package omits it.

**`inv verify.all` proves the links**, not just the file: `_symlink_checks()` builds one check per
`symlink_dest` whose parent directory exists, and `_symlink_check` requires the link to resolve to a
path this repo deploys — a link pointing at a stale hand-made copy fails.

So the honest current claim is: **four agents get the instructions file, one gets the skills
directory natively, one more gets skills through the `skills` CLI's own list.**

## Open questions

[NEEDS CLARIFICATION: which agents does the `skills` CLI actually support, and does its list still
match ours? `agents = ["claude-code", "github-copilot"]` was chosen when the entry was written; the
CLI's own supported-agent list is upstream and moves. This is the one item that needs a real look at
the tool rather than at this repo.]

[NEEDS CLARIFICATION: what does each candidate agent read, natively? The four with symlinks were
chosen by their known filenames. `docs/ai.md`'s survey already covers Aider, Goose, Gemini CLI,
Copilot, Cursor, Continue.dev and Ollama — and by the docs decision its _installation
particularities_ half is moving to `contributing/`, which is the same material this matrix needs.
Doing both passes at once avoids reading the same release notes twice.]

[NEEDS CLARIFICATION: what is the bar for "supported"? Three rungs, and they are not the same
promise: (a) the agent reads `~/AGENTS.md` because PULSE symlinked it, (b) the agent finds the
skills, (c) PULSE installs the agent itself. Only `claude-code` has all three today. The site should
not claim (a) as if it were (c), which is roughly what "agent-agnostic" would imply if written
without care.]

[NEEDS CLARIFICATION: does adding an agent cost anything beyond a `symlink_dest` entry? A wrong
filename is silent — the link lands, the agent ignores it, and `verify.all` still passes, because
the check proves the link resolves to a deployed path, not that anything reads it. That asymmetry is
worth a sentence in whatever documents the matrix.]

## Recommended direction

1. **Survey once, use twice** — one pass over the candidate agents that produces both this matrix
   and the filtered `contributing/` page the docs plan calls for. Installation particularities and
   what each agent reads; no market-share or ARR material, per that plan's decision.
2. **Publish the matrix as a table on the site**, in whatever page ends up saying what PULSE offers
   an agent user, with the three rungs above named explicitly rather than collapsed into
   "supported".
3. **Add `symlink_dest` entries for the agents that read a file we already produce** — the cheapest
   real support there is, and the mechanism already skips what is not installed.
4. Leave the fragment-labelling question to `2026-08-30-portable-fragment-names-one-harness.md`;
   this plan does not decide what goes in `~/AGENTS.md`, only who reads it.
