---
status: in-progress
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

- The fragment axis was settled and its plan retired 2026-09-02:
  `contributing/global-agents-md.md`'s "Fragments are subjects, dependency is a label" holds the
  result. The Claude Code rules in `~/AGENTS.md` stay and are **labelled** rather than genericised,
  and the anticipated future is _adding_ a second harness's instructions — which is this plan's
  half. Nothing there decides the harness inventory.
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

## The skills half, measured 2026-09-02

Read out of the installed `skills` CLI's own bundle
(`~/.local/share/nvm/.../node_modules/skills/dist/cli.mjs`), not from its README: it carries a
registry of **71 agents**, each with a `skillsDir`, a `globalSkillsDir` and a `detectInstalled`
probe.

**19 of the 71 read `.agents/skills` natively** — amp, antigravity, antigravity-cli, cline, codex,
cursor, deepagents, dexto, firebender, gemini-cli, github-copilot, kimi-code-cli, loaf, opencode,
promptscript, replit, universal, warp, zed. The rest use a vendor directory (`.goose/skills`,
`.cursor`-style paths, and so on), and **Claude Code is one of those**: its `skillsDir` is
`.claude/skills`.

That inverts how the skills setup reads. `~/.agents/skills/` is not a PULSE convention with a
Claude-shaped symlink bolted on; it is **the cross-tool location 19 agents already use**, and the
`~/.claude/skills` symlink is the compatibility shim for the one agent this machine happens to run.
A PULSE machine is therefore correct for those 19 with no per-agent work at all — the rung-(b)
answer is "20 agents", and 19 of them cost nothing.

It also settles the `agents = ["claude-code", "github-copilot"]` question: `github-copilot`'s
`skillsDir` **is** `.agents/skills`, so that entry converges on the same directory rather than
producing a second copy. The list is not wrong, but only its first element does any work.

[PITFALL: **the CLI reports usage on every invocation unless told not to, and PULSE was not telling
it.** `TELEMETRY_URL = "https://add-skill.vercel.sh/t"`, gated only on `DISABLE_TELEMETRY` /
`DO_NOT_TRACK` being unset, sending CLI version, a CI flag, the detected agent name and the
skill/package names of the call. Found while reading the bundle for the agent registry — not while
looking for it. Fixed the same day: `tasks/ai.py` pins both variables on the `skills add`
invocation, per the rule that a feature which phones home by default is a decision, not a default.]

## The instructions half, measured 2026-09-02

**The `AGENTS.md` specification is repo-root only.** agents.md names ~23 adopting tools and
describes nested files for monorepos; it says nothing about a user-level file. So every global
instruction path is a **vendor-specific** claim, which is exactly why `symlink_dest` is a list of
four hand-verified paths rather than a convention that could be derived.

Each of the four verified against the vendor's own source or docs, not a search summary:

| link                                 | verified                                                        |
| ------------------------------------ | --------------------------------------------------------------- |
| `~/.claude/CLAUDE.md`                | Claude Code's documented user-level file                        |
| `~/.codex/AGENTS.md`                 | `codex-rs/codex-home/src/instructions/mod.rs`, read whole       |
| `~/.copilot/copilot-instructions.md` | GitHub docs, "user-level instructions across repositories"      |
| `~/.gemini/GEMINI.md`                | Gemini CLI's global context file, `~/.gemini/<contextFileName>` |

Three findings worth carrying:

- **Codex tries `AGENTS.override.md` first**, and returns it if non-empty without ever reading
  `AGENTS.md`. So the documented escape hatch does not merely supplement PULSE's symlink, it
  **shadows** it entirely. Leaving that file untouched is correct; a user who creates one silently
  stops receiving `~/AGENTS.md` and nothing reports it.
- **Gemini can be pointed at `AGENTS.md` directly** — `context.fileName` accepts a list, e.g.
  `["AGENTS.md", "GEMINI.md"]`, and the global file is `~/.gemini/<that name>`. That is a genuine
  alternative to the `GEMINI.md` symlink and would make the link unnecessary, at the cost of PULSE
  writing into an app-owned `settings.json`.
- **Copilot was nearly recorded wrong.** A search summary stated flatly that Copilot "does not read
  user-level global files the way Codex reads `~/.codex/AGENTS.md`". GitHub's own docs list
  `$HOME/.copilot/copilot-instructions.md` as exactly that. The summary was confident, specific, and
  false — and the entry it would have removed is one that works.

## The three rungs, answered

| rung                         | how many                         | cost per additional agent         |
| ---------------------------- | -------------------------------- | --------------------------------- |
| (a) reads `~/AGENTS.md`      | 4, each a hand-verified path     | one `symlink_dest` entry + verify |
| (b) finds the skills         | 20 (19 native + Claude via shim) | **zero** for anything on the 19   |
| (c) PULSE installs the agent | 1 (`claude-code`)                | a full `[packages.*]` entry       |

The honest public claim is rung (b): **a PULSE machine's skills directory is the one 19 agents
already look in.** Rung (a) is four agents and is where the per-agent work is; rung (c) is one.

## Open questions

**Answered above**: 71 agents in the CLI's registry, 19 of them reading `.agents/skills` natively,
and our two-element list is correct with only its first element doing any work. Worth re-reading the
bundle when the CLI is upgraded — the registry is upstream and moves, and the count is the cheap
tell that it has.

[NEEDS CLARIFICATION: what does each candidate agent read, natively? The four with symlinks were
chosen by their known filenames. `docs/ai.md`'s survey already covers Aider, Goose, Gemini CLI,
Copilot, Cursor, Continue.dev and Ollama — and by the docs decision its _installation
particularities_ half is moving to `contributing/`, which is the same material this matrix needs.
Doing both passes at once avoids reading the same release notes twice.]

**Answered above** — the three rungs are 4 / 20 / 1, and they are different promises. The site
should name the rung rather than say "supported"; the strongest true sentence is the rung-(b) one,
and it is stronger than the framing this plan was opened with expected.

**Confirmed, and it nearly bit during this survey.** A wrong filename is silent: the link lands, the
agent ignores it, and `verify.all` still passes, because the check proves the link resolves to a
path this repo deploys — not that anything reads it. The Copilot near-miss above is the live
instance, in the other direction: a confident search summary would have had us _remove_ a working
entry, and only the vendor's own docs settled it. So the rule for this matrix is that **every
rung-(a) path is verified against the vendor's source or its own documentation, never against a
summary**, and the verification belongs next to the entry in `setup.toml` where the next person will
meet it.

[NEEDS CLARIFICATION: should `verify.all` do better than proving the link resolves? It cannot prove
an agent reads the file, but it could prove the _filename_ still matches what that vendor documents
— which is the part that goes stale. That means a per-agent assertion maintained by hand, i.e. the
same claim written twice, so it may not be worth it. Worth deciding once rather than rediscovering
the asymmetry each time an agent is added.]

## Recommended direction

The survey is done and the numbers are above; what is left is publishing them and deciding whether
to widen rung (a).

1. **Publish the matrix**, naming the three rungs rather than collapsing them into "supported". The
   lead should be the rung-(b) fact, because it is the strongest true claim and it is the one that
   costs a reader nothing: the skills directory a PULSE machine sets up is the one 19 agents already
   look in. Keep it out of `docs/ai.md`'s survey half, per the docs plan's decision, and put the
   installation particularities in `contributing/`.
2. **Decide rung (a) per candidate, and expect most answers to be no.** The specification is
   repo-root only, so an agent qualifies only if its vendor documents a user-level file. That is a
   per-vendor lookup with no shortcut, and the four we have may be most of what exists. Verify each
   against the vendor's source or docs — a summary got Copilot backwards during this pass.
3. **Weigh the Gemini `context.fileName` alternative** against its `GEMINI.md` symlink. Pointing it
   at `AGENTS.md` is arguably the more honest wiring, but it means PULSE editing an app-owned
   `settings.json`, which `inv home.list-claims` already treats as its own class of write. A symlink
   that works is not obviously worse.
4. Leave the fragment-labelling question alone — settled, in `contributing/global-agents-md.md`.
   This plan does not decide what goes in `~/AGENTS.md`, only who reads it.

Not in scope, and worth saying so: **nothing here argues for widening rung (c).** PULSE installing a
second agent is a different decision with real maintenance cost, and the user's framing was that
developers pick their own tools.
