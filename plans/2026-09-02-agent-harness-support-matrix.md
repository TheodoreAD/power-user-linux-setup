---
status: in-progress
updated: 2026-09-04
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

It also settles the `agents = ["claude-code", "github-copilot"]` question: `github-copilot`'s
`skillsDir` **is** `.agents/skills`, so that entry converges on the same directory rather than
producing a second copy. The list is not wrong, but only its first element does any work.

### Re-measured 2026-09-04 — the 19 is a project-level number, and rung (b) was overstated

Re-run against the same installed CLI, now v1.5.10: **71 registry entries, 19 native, the same
nineteen names.** The counts hold. What does not hold is the sentence built on them.

`skillsDir` is the **project-level** directory. Each entry carries a separate `globalSkillsDir`, and
for most of the nineteen it is not `~/.agents/skills`:

| the entry's own `globalSkillsDir`       | how many | which                                                                                                     |
| --------------------------------------- | -------: | --------------------------------------------------------------------------------------------------------- |
| `~/.agents/skills`                      |        6 | cline, dexto, kimi-code-cli, loaf, warp, zed                                                              |
| `~/.config/agents/skills` (XDG variant) |        3 | amp, replit, universal                                                                                    |
| a vendor directory                      |        9 | antigravity, antigravity-cli, codex, cursor, deepagents, firebender, gemini-cli, github-copilot, opencode |
| none — falls back to the canonical dir  |        1 | promptscript                                                                                              |

[PITFALL: **the CLI contradicts itself here, and PULSE's install path happens to take the favourable
half.** `isUniversalAgent()` is defined as `skillsDir === ".agents/skills"` — the _project_ field —
and `getAgentBaseDir()` short-circuits on it, returning the canonical `~/.agents/skills` for all
nineteen and never consulting `globalSkillsDir`. So `skills add --global` really does write one copy
to `~/.agents/skills` for any of them, which is what `[packages.agent-skills]`'s comment records for
`github-copilot` and which is correct as a statement about the CLI. But other code paths in the same
bundle (the `list` scope builder, the cleanup scanner) read `globalSkillsDir` directly. The field is
presumably there because it is where that vendor's agent actually looks, in which case writing to
`~/.agents/skills` for `gemini-cli` puts the skills somewhere Gemini CLI does not read.]

**What this costs the plan is the headline, not the work.** Verified on this machine: the install
put one real copy in `~/.agents/skills` and created no `~/.copilot/skills`, and
`skills list --global` reports every skill as installed for both Claude Code and GitHub Copilot.
That is the CLI's own accounting of where it wrote, not evidence that Copilot reads it.

So "19 agents already look in the directory PULSE sets up" is **not a claim this measurement
supports** at user level. What it supports:

- **at project level** — 19 of 71 registered agents read `.agents/skills` in a repo, and that is the
  cross-tool convention it was always claimed to be;
- **at user level** — the `skills` CLI writes one copy to `~/.agents/skills` for all 19, and 6 of
  them independently record that same path as where they look. Three more record the XDG spelling of
  it. The remaining 9, plus Claude Code, record a vendor directory.

Rung (b) is therefore not 20 at user level; on the registry alone it is 7 (the 6, plus Claude Code
through PULSE's symlink), with the other 12 a per-vendor question exactly like rung (a). **Three of
those 12 were then resolved — see immediately below, which takes it to 10.**

### Answered 2026-09-04 — `globalSkillsDir` is not where the vendor looks

Three of the nine vendor-directory entries are agents this repo already sends `~/AGENTS.md` to, so
they were the cheapest to settle. All three were checked against the vendor's own source or docs
source, never a summary, and **all three read `~/.agents/skills` at user level**:

| agent            | the registry says   | the vendor's own source says                                                                                                              |
| ---------------- | ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `codex`          | `~/.codex/skills`   | `~/.agents/skills` **and** `$CODEX_HOME/skills`, the latter commented "Deprecated user skills location … kept for backward compatibility" |
| `gemini-cli`     | `~/.gemini/skills`  | `~/.gemini/skills` **and** `~/.agents/skills`, loaded as the "user agent skills alias"                                                    |
| `github-copilot` | `~/.copilot/skills` | "For **personal skills**, shared across projects, create a `~/.copilot/skills` or `~/.agents/skills` directory"                           |

- Codex: `codex-rs/ext/skills/src/host_roots.rs`, `roots_from_layer_stack`'s
  `ConfigLayerSource::User` arm pushes both roots. The deprecation comment is in the file.
- Gemini CLI: `packages/core/src/skills/skillManager.ts` step 3.1 loads
  `Storage.getUserAgentSkillsDir()`, which `packages/core/src/config/storage.ts` defines as
  `join(homedir(), ".agents", "skills")`.
- Copilot: `github/docs`, `data/reusables/copilot/creating-adding-skills.md` — the docs source, not
  the rendered page or a search result.

[DECISION: **`globalSkillsDir` is the `skills` CLI's own preferred write target, not a claim about
where that agent reads.** Three for three, it named a path the vendor supports but does not prefer —
one of them explicitly deprecated by its own maintainers. So the `isUniversalAgent` short-circuit
that ignores the field and writes to `~/.agents/skills` is not the CLI taking a shortcut; it is the
CLI being right, and the field is what is stale. This reverses the reading in the PITFALL above,
which guessed the field was authoritative because a vendor would know its own path. Keep the
PITFALL: the internal contradiction is real and the next reader will hit it, and "the obvious
reading of the two fields is backwards" is the useful half.]

**So rung (b) at user level is 10, verified**: the 6 that record the path themselves, Claude Code
through PULSE's symlink, plus `codex`, `gemini-cli` and `github-copilot` from their own sources. Not
20, and no longer 7.

[NEEDS CLARIFICATION: the remaining **6 of the 9** — `antigravity`, `antigravity-cli`, `cursor`,
`deepagents`, `firebender`, `opencode` — are unchecked. None is installed here and none receives
`~/AGENTS.md`, so the lookup buys a bigger number on the page and nothing else. Worth doing before
the page claims a total; not worth doing to unblock anything. Given three for three above, the prior
is that most of them also read `~/.agents/skills` and the registry field is simply stale across the
board.]

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

Corrected 2026-09-04, per the re-measurement and the vendor lookups above.

| rung                         | how many                                 | cost per additional agent                            |
| ---------------------------- | ---------------------------------------- | ---------------------------------------------------- |
| (a) reads `~/AGENTS.md`      | 4, each a hand-verified path             | one `symlink_dest` entry + verify                    |
| (b) finds the skills in `~`  | **10 verified**, 6 unchecked             | a per-vendor lookup; so far always "it already does" |
| (b′) finds them in a repo    | 20 (19 native + Claude via project shim) | **zero** for anything on the 19                      |
| (c) PULSE installs the agent | 1 (`claude-code`)                        | a full `[packages.*]` entry                          |

The 19 is real, but it is rung (b′) — a **project** `.agents/skills` directory. PULSE writes at user
level, which is rung (b): 6 agents record that path in the CLI's registry, three more were confirmed
from their own source or docs (`codex`, `gemini-cli`, `github-copilot`), and Claude Code reaches it
through PULSE's symlink. Six remain unchecked and none of them is installed here. Rung (a) is four
agents and is where the per-agent work already is; rung (c) is one.

**Every one of the four rung-(a) agents is also rung (b)** — Claude Code by symlink, the other three
by their own published behaviour. That is the sentence the page has been looking for, and unlike the
"19 agents" one it survives contact with the source.

[PITFALL: **the two rungs were one number until the fields were read separately, and the merged
number was the flattering one.** Nothing failed — the plan's own count was correct and its list of
nineteen names is unchanged — but a single `skillsDir` reading answered a user-level question with a
project-level fact, and the sentence it produced was the one earmarked to lead the public page. This
is the third time in this plan that the failure mode is a confident, specific, wrong claim about
_which path an agent reads_, after the Copilot near-miss and the wrong-filename-is-silent finding.
Worth noting how it ended: the follow-up lookups moved the number **up**, from 7 to 10, so the
correction was not pessimism winning — it was the difference between a number that was asserted and
one that was checked.]

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

**Answered above** — the rungs are 4 / 10 / 20 / 1, and they are different promises. The site should
name the rung rather than say "supported". Revised 2026-09-04: the strongest _verified_ sentence is
the rung-(b) one, that all four agents PULSE hands `~/AGENTS.md` to also read the skills it installs
into `~/.agents/skills`. The 19 stays on the page as the project-level fact it is, and the page must
not let a reader carry it across to `~`.

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

## Step 1 landed 2026-09-04

Published, in three commits:

- `docs/ai.md` — the four-agent table now names a real skills path for all four rather than `—` for
  Codex and Gemini CLI, and the page states the rung-(b) sentence: the only agent needing a symlink
  for skills is the one PULSE installs. The 19 is on the page as an explicitly **project-level**
  count, in its own subsection, with a pointer to the rationale.
- `contributing/ai-tooling.md` — the registry's two fields, the CLI's internal contradiction, the
  three vendor sources, the rule never to quote `globalSkillsDir` as where an agent looks, and the
  six entries still unchecked. The Gemini CLI and Copilot sections were corrected in the same pass.
- `setup.toml` — `[packages.agent-skills]` now says the `github-copilot` element is a no-op and why,
  so nobody "fixes" the list by adding `codex` and `gemini-cli` to it.

Steps 2–4 below are untouched.

## Recommended direction

The survey is done and the numbers are above; step 1 has landed. What is left is deciding whether to
widen rung (a).

1. **Publish the matrix**, naming the rungs rather than collapsing them into "supported". Revised
   2026-09-04: the lead is the rung-(b) fact, because it is both the strongest and the one a reader
   can act on — every agent PULSE hands `~/AGENTS.md` to also reads the skills it installs, verified
   per vendor. The 19 goes on the page as what it is, a **project** `.agents/skills` count, and the
   page must not blur the two, which is exactly what this plan did until the fields were read apart.
   `docs/ai.md`'s current table is wrong in the safe direction and needs fixing either way: it shows
   `—` under skills for Codex and Gemini CLI, both of which read `~/.agents/skills`. Keep it out of
   that page's survey half, per the docs plan's decision, and put the installation particularities
   and the `globalSkillsDir` contradiction in `contributing/ai-tooling.md`.
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
