---
status: idea
updated: 2026-08-26
---

## Context

Every AI-facing artifact this machine uses is authored inside `power-user-linux-setup` and reaches
agents through this repo's own machinery:

- **Skills** — directories under `skills/<name>/`, declared as
  `skills = [{ source = "local", path = "skills/<name>" }]` on a `[packages.<name>]` entry with
  `method = "skill"`, **copied** to `~/.agents/skills/<name>` by `inv ai.install-skills`, reaching
  Claude Code only because `~/.claude/skills` is symlinked to `~/.agents/skills`.
- **Global instructions** — `config/global-AGENTS.md` → `~/AGENTS.md` via
  `[packages.claude-global-md]`, with `~/.claude/CLAUDE.md` symlinked to it.
- **Harness settings** — `claude_permissions_allow`, `claude_additional_directories`,
  `claude_default_mode`, `claude_statusline`, the `cli-allowlist` pipeline, the direnv `PreToolUse`
  hook, `askpass-zenity`.
- **Rationale** — `contributing/*.md`, one hop from the artifact it explains.
- **MCP servers** — nothing yet; `contributing/mcp-skill-shipping.md` defers a declarative
  `mcp_servers` list until a real server exists.

Failure modes for anyone who is not this repo's maintainer:

1. **Not obtainable without the repo.** No `git clone` + one command gets someone `plan-docs` or
   `python-conventions`. They would clone a Linux machine-setup repo, install `uv`/`invoke`, and run
   a task whose default target is `~`.
2. **Authoring requires editing an unrelated repo's config** — a `setup.toml` package block in a
   repo whose subject is apt packages, GNOME extensions and Citrix.
3. **Deployment is a copy, not a link.** An edit to `skills/<name>/SKILL.md` does nothing until
   `inv ai.install-skills --skill=<name>` re-runs, defeating every agent's own live-reload.
4. **Single-agent, single-machine.** The install targets exactly one agent's directory on exactly
   one box.

## Constraints (settled with the user, 2026-08-26)

[DECISION: **No vendor lock-in. The artifact vocabulary is `AGENTS.md`, Agent Skills (`SKILL.md`),
and MCP — nothing else.** Claude Code plugins, marketplaces, `.claude-plugin/`, `~/.claude/rules/`
and `CLAUDE.md`-as-a-real-file are all out, on principle, not on cost. Anything Claude-specific is
admissible only when it is _harness plumbing that makes an agent work better_ — the direnv
`PreToolUse` hook, the CLI allowlist, permission mode, statusline — never as a carrier for
instructions or knowledge. Reaching feature parity for Copilot/Codex/Gemini/Devin on that plumbing
is additive PULSE work, not skill work.]

[DECISION: **`.agents/skills/` stays, unconditionally.** It is the community convention; `AGENTS.md`
is a Linux Foundation (AAIF) project. Claude Code's refusal to read `.agents/skills/` natively is
Claude Code's problem, solved by a symlink, not a reason to move off the convention.]

[DECISION: **One repo, one flat set of skills — no tiering into public/private repos.** Skills that
are personal or heavily opinionated live in the same repo, marked as such in their own frontmatter
or description. Two repos is overhead that buys nothing. `research-library` in particular is worth
publishing as-is: requiring a directory in the user's home is unremarkable for any software.]

[DECISION: **Skills are cut by clear responsibility with non-contending trigger conditions**, not by
theme, release cadence, or bundle convenience. Trigger contention between two skills is the failure
to design against — see `plans/2026-08-22-skill-trigger-quality-review.md`.]

[DECISION: **The repo is named `agent-skills`.** Plain, matches what the ecosystem calls them
(`addyosmani/agent-skills`, `VoltAgent/awesome-agent-skills`), legible to a stranger with no
context.]

[DECISION: **Rationale lives in each skill's own `references/`, and nowhere else.** Six skills
already do this; `contributing/mcp-skill-shipping.md` and `contributing/research-library.md` fold
into their skills' `references/rationale.md` and stop existing as separate pages. No `contributing/`
tree in `agent-skills`. PULSE's own `contributing/` keeps only PULSE-mechanism pages
(`cli-allowlist`, `deploy`, `verify`, `repo-family-architecture`, ...).]

[DECISION: **`~/AGENTS.md` is assembled from contributed fragments, zsh-style, not owned by one
source.** The delivery mechanism mirrors `zshrc`/`zshenv`/`zprofile`: an any-section `setup.toml`
field any package may declare, each fragment written into one named, idempotent block, so every
package that changes `~/AGENTS.md` does so responsibly and re-runs cleanly. Hard requirement: **the
assembled file must not read as machine-generated to an agent.** Fragments are authored as coherent
document sections with real headings, not snippets, and section order must be deterministic.]

[DECISION: **Every repo in the family gets its own skill describing its API/interface**, committed
to that repo, so an agent can work against it without reading the source every session. Scope item
added 2026-08-26; design below.]

## Research findings (2026-08-26)

### The vendor-neutral stack is real, governed, and already what this repo half-uses

`AGENTS.md` was donated by OpenAI to the **Agentic AI Foundation (AAIF)** under the Linux
Foundation, alongside MCP itself and Block's `goose` — AAIF launched with 150+ member organizations.
`AGENTS.md` is adopted by 60,000+ open-source projects and by Copilot, VS Code, Cursor, Codex and
Gemini CLI. The Agent Skills format (`SKILL.md` + YAML frontmatter, `name`/`description` minimum)
originated at Anthropic and was released as an open standard; ~40 skills-compatible products are
listed on `agentskills.io`'s showcase, and the `skills` CLI claims coverage of 75+ agents. This is
not an emerging convention any more — it is the mainstream one, and the vendor-specific paths are
the adapters hanging off it.

### How community projects actually distribute skills: the hub-and-symlink model

The dominant mechanism is [`vercel-labs/skills`](https://github.com/vercel-labs/skills) — the
`skills` CLI, `npx skills`, `skills.sh`. Its model is exactly the shape this repo needs:

- **One canonical copy** at `.agents/skills/` (project) or `~/.agents/skills/` (global).
- **Symlinks from every detected agent's own directory** into that canonical copy —
  `~/.claude/skills`, `~/.codex/skills`, `~/.cursor/skills`, `~/.copilot/skills`,
  `~/.codeium/windsurf/skills`, etc. Symlink is the default and recommended mode; copy is the
  fallback where symlinks aren't supported. Stated benefit: "a single source of truth, easy
  updates."
- **Agent auto-detection.** It detects which agents are installed and offers those; if none is
  detected it asks.
- **A publishable repo needs no manifest.** Skills are discovered up to three levels deep in
  standard locations — `skills/`, `skills/<category>/<name>/`, agent-specific directories, or
  top-level `SKILL.md` directories at the repo root. A manifest is required _only_ for the Claude
  Code plugin marketplace, which is out of scope here.
- **Authoring commands exist**: `npx skills init [name]` scaffolds a skill,
  `npx skills find [query]` searches, `--list` previews a repo's skills before installing,
  `INSTALL_INTERNAL_SKILLS=1` surfaces work-in-progress skills marked `metadata: { internal: true }`
  — a ready-made mechanism for the "opinionated/niche" marking the constraints above call for.

**This repo already has the CLI installed and already uses it.** `[packages.node].global_packages`
includes `skills`, and `tasks/ai.py`'s `_install_remote_skill` shells out to
`skills add <repo> --global --agent <agents...> --yes`. The `source = "npx"` path was validated
end-to-end against a real package (`caveman`). What is missing is not machinery — it is that this
repo's own skills are declared `source = "local"` and therefore reachable by nobody else.

The other prevalent shape, for reference: [`obra/superpowers`](https://github.com/obra/superpowers)
splits framework skills (in the distributed repo) from a user's own personal skills repo cloned to
`~/.config/superpowers/skills/`, plus a dedicated skill for authoring and testing new skills. Useful
as precedent for the "core vs. personal" question, but it is Claude-plugin-delivered, so its
distribution half doesn't transfer.

### Verified hands-on against the installed CLI (2026-08-26)

Run against `skills` 2.x from `[packages.node].global_packages`, in a scratch directory, project
scope only — nothing global was mutated. Several things the write-ups claim did not survive contact.

- **Local paths are a first-class source.** `skills add ../srcrepo --list` answers "Local path
  validated", finds the skills, and installs them. Not GitHub-only, which the docs never say. A
  local source is recorded in the lockfile as `"sourceType": "local"`.
- **`skills-lock.json` is the real declarative artifact** — `{source, sourceType, computedHash}` per
  skill, written on every `add`, restored by `skills experimental_install`. It is a direct,
  community-maintained analogue of PULSE's `setup.toml` `skills` field, and it is per-directory
  (project or global), not per-machine.
- **Installs are always copies, never links to the source checkout.** Editing
  `srcrepo/skills/demo-skill/SKILL.md` from `VERSION_MARKER_ONE` to `..._TWO` left both installed
  copies unchanged. `skills experimental_install` re-copies and picks the edit up. So the dev loop
  is edit → one refresh command, exactly today's `inv ai.install-skills --skill=<name>` shape —
  moving to the CLI does not buy live-reload. (`--copy` exists as a flag, so symlinking is the
  _default_ for the agent-directory leg — but the canonical copy itself is still a copy of the
  source.)
- **The layout depends on which agents are targeted.** With `--agent claude-code` alone it wrote a
  real file to `./.claude/skills/demo-skill/SKILL.md` and created **no** `.agents/skills/` hub at
  all. With `--agent claude-code codex cursor` it created `./.agents/skills/demo-skill/` and treated
  Codex and Cursor as "universal" (they read `.agents/skills` directly).
  `skills experimental_install` reported 17 universal agents on this machine — Amp, **Antigravity**,
  **Antigravity CLI**, Cline, Codex, Cursor and 11 more — all resolving to the one `.agents/skills/`
  path.
- [PITFALL: **The Claude Code symlink is announced and never created.** Both multi-agent runs
  printed `symlink → Claude Code` in the installation summary, and no `.claude/` directory existed
  afterwards — reproduced twice, and `skills ls --json` agreed, listing the skill's agents as
  `["GitHub
  Copilot"]` only. So installing alongside any universal agent silently leaves Claude
  Code with nothing. **This machine is only unaffected because PULSE's own
  `~/.claude/skills → ~/.agents/skills` symlink already exists** — `_ensure_agents_skills` is not
  superseded by the CLI as the research above assumed, it is actively covering a defect. Do not
  delete it. Worth reporting upstream.]
- **Agent auto-detection notices it is being run by an agent**: every invocation printed
  `claude-code_2-1-245_agent Agent detected — installing non-interactively`, i.e. it skips its own
  prompts inside a Claude Code session. That interacts directly with the `--yes` trap below — the
  confirmation gate is bypassed by the CLI itself, not only by PULSE's wrapper.

### Where each agent actually looks

Skills, user-level. Per the hands-on run above, most agents are "universal" — they read
`.agents/skills/` directly and need no per-agent directory at all; Claude Code is the outlier that
does:

| Agent                                              | User-level skills directory   |
| -------------------------------------------------- | ----------------------------- |
| Canonical — read directly by 17 agents on this box | `~/.agents/skills/`           |
| Claude Code (needs its own path)                   | `~/.claude/skills/`           |
| Windsurf                                           | `~/.codeium/windsurf/skills/` |

Global instructions — **no canonical path exists**, and this is the genuinely unsolved half:

| Agent       | User-level instruction file                                        | Source             |
| ----------- | ------------------------------------------------------------------ | ------------------ |
| Claude Code | `~/.claude/CLAUDE.md`                                              | vendor docs        |
| Codex       | `~/.codex/AGENTS.md` — or `$CODEX_HOME`; `AGENTS.override.md` wins | vendor docs        |
| Gemini CLI  | `~/.gemini/GEMINI.md`                                              | vendor docs        |
| Copilot     | `~/.copilot/copilot-instructions.md`                               | secondary write-up |
| Amp         | `~/.config/AGENTS.md`                                              | secondary write-up |
| droid       | `~/.factory/AGENTS.md`                                             | secondary write-up |

Two things confirmed 2026-08-26 that change the shape of the symlink farm:

- **Codex reads one file per scope, first non-empty wins** — global `AGENTS.override.md` then
  `AGENTS.md`, then project scope from the git root down, "closer files override earlier guidance".
  A symlink at `~/.codex/AGENTS.md` therefore just works, and `AGENTS.override.md` is a deliberate
  escape hatch a user can keep hand-owned.
- **Gemini CLI can be told to read `AGENTS.md` directly** — `context.fileName` in `settings.json`
  accepts a list, e.g. `["AGENTS.md", "GEMINI.md"]`. That is a _harness tweak_, not a symlink, and
  therefore the cleaner fix for Gemini under the constraints above. [UNVERIFIED: whether
  `context.fileName` governs the user-level `~/.gemini/` lookup too, or only the project-tree walk.]

`agentsmd/agents.md` issue #91 proposes standardizing on `~/.config/agents/AGENTS.md` (XDG). It is
open, unassigned, with no linked PR and no tool commitment. So a global instruction file needs an
N-way symlink farm today, and the `skills` CLI does not do instruction files at all — it only does
skills. **That gap is exactly PULSE-shaped work**, and it is already half-built:
`[packages.claude-global-md]`'s `wrapper-script` + `symlink_dest` mechanism writes one real file and
points a symlink at it. Extending `symlink_dest` from one path to a list is the whole change.

[UNVERIFIED: the Copilot, Amp and droid rows above are still from secondary write-ups (a
compatibility matrix and vendor guides), not each vendor's own docs. Claude Code, Codex and Gemini
CLI were confirmed against vendor documentation 2026-08-26. Confirm the remaining three before any
of them is baked into a `setup.toml` field.]

### What this means for the current PULSE mechanism

- `_install_local_skill` (copy + `.pulse-source` marker + deploy-manifest integration) exists
  because skills are authored _inside_ this repo. Once they are in their own published repo, the
  correct installer is the one the community already maintains —
  `skills add <owner>/<repo> --global`, i.e. the `source = "npx"` path this file already implements.
  The `local` source becomes dead weight for this repo's own skills, though it stays meaningful for
  any genuinely PULSE-specific skill.
- `_ensure_agents_skills` (the `.claude/skills → .agents/skills` symlink) **stays, and is now known
  to be load-bearing.** The first draft of this plan assumed the `skills` CLI superseded it; the
  hands-on run above disproved that — the CLI announces the Claude Code symlink and does not create
  it whenever any universal agent is also targeted. PULSE's symlink is the only reason Claude Code
  sees anything on this machine today.
- The `claude_*` settings fields, the `cli-allowlist` pipeline, `askpass-zenity` and the direnv hook
  are harness plumbing and stay exactly where they are — with the open work being per-agent parity.

### Rejected: Claude Code plugins and marketplaces

Researched first, before the constraints above were stated; recorded so it isn't re-researched. A
plugin bundles skills, subagents, hooks, MCP servers, commands, LSP configs and `bin/` executables
into a versioned unit installed via `/plugin marketplace add <owner>/<repo>`; a marketplace is a git
repo with `.claude-plugin/marketplace.json` supporting github/git/npm/archive/command sources; it is
the pattern most Claude-focused write-ups now recommend over "skills as dotfiles". Two things kill
it here. First and decisive: it is Anthropic-only, and the whole point is portability. Second, even
on its own terms it cannot carry the instruction file — verbatim from the reference, "A `CLAUDE.md`
file at the plugin root is not loaded as project context. Plugins contribute context through skills,
agents, and hooks rather than CLAUDE.md" — so it would have solved at most half the problem while
locking in the half it did solve.

One genuinely useful fact survives the rejection: Claude Code's cloud sessions, Cowork, and routines
do **not** read `~/.claude/skills/`; only skills committed into a repo's own `.claude/` or enabled
on a claude.ai account reach them. Anything installed globally on this machine — by PULSE today or
by `skills add --global` tomorrow — is terminal-only. Consistent with "i live in the terminal", so
it costs nothing, but it is the reason the global-install route is a deliberate choice rather than a
free one.

## Open questions

[NEEDS CLARIFICATION: **Where does `contributing/global-agents-md.md` go?** It holds the evidence
for every `~/AGENTS.md` rule plus the admission criteria, and "rationale lives in each skill's
`references/`" gives it no home — it belongs to no skill. If the portable conventions become a
fragment shipped from `agent-skills`, the natural answer is a sibling `references/` next to that
fragment, mirroring the skill convention. But the file also carries evidence for the PULSE-specific
rules, which stay here. Likely splits the same way the rules do; needs confirming before either half
moves.]

[NEEDS CLARIFICATION: **Fragment ordering and the "must not look machine-generated" bar.** Shell
fragments can append in any order; a document cannot. Options: an explicit `order` key per fragment,
alphabetical by package name (arbitrary and unstable), or a fixed list of section slots in PULSE
naming which contributor fills each. The current file's structure — six trigger-clustered sections,
researched in `contributing/global-agents-md.md` — is the thing being preserved, so the slots
probably _are_ those clusters, and a fragment declares which cluster it extends.]

[NEEDS CLARIFICATION: **Do the HTML markers survive every agent, not just Claude Code?** Claude Code
documents stripping block-level HTML comments from instruction files before injecting them, so
`util.MarkerStyle.HTML` markers cost nothing there. Checked 2026-08-26: **no other vendor documents
any such stripping**, so the working assumption must be that Codex, Copilot and Gemini feed them to
the model verbatim. Two markers per fragment across ~6 fragments is a dozen visible comment lines —
survivable, but it is exactly the "looks machine-generated" cost the decision above rules out.
Marker-free alternative to weigh: manifest-tracked assembly, the shape
`_apply_static_claude_permissions` already uses (remember what we wrote, rewrite only that, never
touch anything else) — no in-file markers at all, at the cost of the file no longer being
self-describing.]

[NEEDS CLARIFICATION: **Where does `contributing/repo-family-architecture.md`'s settling test put
`agent-skills`?** It has no bucket for "artifacts an agent consumes on any machine, authored once,
distributed as a package" — a fourth category alongside PULSE/`repo-tasks`/`scaffoldapy`. That page
needs a paragraph either way.]

[NEEDS CLARIFICATION: **Per-repo API skills — one skill per repo, or one per interface?**
`repo-tasks` alone exposes `inv` namespaces, the `repo-tasks` CLI, and canonical config files. A
single `repo-tasks` skill risks being a grab-bag with a vague trigger, which is exactly the
description-quality failure `plans/2026-08-22-skill-trigger-quality-review.md` documents. Also
undecided: does a per-repo skill duplicate that repo's `AGENTS.md`, or replace part of it? The
distinction that probably settles it — `AGENTS.md` is _how to work on this repo_, the skill is _how
to consume this repo's interface from outside it_ — but the two overlap heavily for a task runner.]

[NEEDS CLARIFICATION: **Do per-repo skills need committed per-agent symlinks?** A repo committing
`.agents/skills/<name>/SKILL.md` is invisible to Claude Code without `.claude/skills` symlinked to
it, and to Codex without `.codex/skills`. Git stores symlinks fine, so committing them works — but
it means every repo carries one symlink per agent anyone might use, and `scaffoldapy` has to stamp
them. Alternative: `npx skills` run per-repo at clone time, which is a step a stranger must
remember.]

[NEEDS CLARIFICATION: **Given that installs are always copies (verified below), is a live dev loop
worth building at all?** `skills experimental_install` re-copies from a local source and picks up
edits, so the loop is edit → one command → refreshed, identical in shape to today's
`inv ai.install-skills --skill=<name>`. That is good enough that a bespoke symlink-to-checkout
mechanism may not be worth its own maintenance — but it does mean no agent's live-reload ever fires
on an edit, which is the property that made the move look attractive in the first place. Decide
explicitly rather than inheriting the limitation by accident.]

[NEEDS CLARIFICATION: **`--yes` and the non-interactive trap.** `docs/claude-code.md` records that
`_install_remote_skill`'s confirmation defaults to _proceed_ under a non-interactive shell, so an
agent running the task installs every declared remote skill with no approval gate. Moving this
repo's own skills to the `npx` source makes that path the primary one rather than the exception, so
the default needs revisiting before the migration, not after.]

[NEEDS CLARIFICATION: **What marks a skill "opinionated/niche"?** The `skills` CLI already has
`metadata: { internal: true }` + `INSTALL_INTERNAL_SKILLS=1`, but that means "work in progress", not
"personal to this author". Options: a `metadata` key of our own, a convention in the `description`,
or a `README` table in the repo. The `description` is the field agents actually match on, so putting
audience-signalling text there costs trigger quality — probably `metadata`.]

## Recommended direction

Rough, and contingent on the questions above.

**One new public repo of skills, distributed by the `skills` CLI; PULSE keeps only the harness.**

1. **`agent-skills`** — plain `skills/<name>/{SKILL.md,references/,scripts/}` at the root, no
   manifest, no vendor directory. Discoverable by `npx skills add TheodoreAD/agent-skills` for
   anyone, on any of 75+ agents. Its README documents the one-liner and nothing else is required to
   consume it.
2. **PULSE installs it with one declaration** — a single `[packages.agent-skills]` entry with
   `skills = [{ source = "npx", repo = "TheodoreAD/agent-skills", agents = [...] }]`, replacing nine
   `method = "skill"` blocks, `_install_local_skill` and the `.pulse-source` marker logic.
   `_ensure_agents_skills` **is not part of that deletion** — the verification above found the CLI
   does not reliably create the Claude Code link. That is a real deletion of working, tested code,
   and it should happen only after step 5 proves the replacement.
3. **`~/AGENTS.md` becomes an assembled file with an `agents_md` any-section field** — the direct
   analogue of `zshrc`/`zshenv`/`zprofile`. Each contributing package declares a fragment; PULSE
   writes each into one named block via the existing
   `util.ensure_block(..., style=MarkerStyle.HTML)` (already used for `docs/dev-container.md`'s tag
   table, and HTML markers specifically because a `#`-prefixed marker renders as a heading in
   Markdown). Two known contributors at the start: `agent-skills`' portable conventions, and PULSE's
   own machine rules. Idempotent, diffable, re-runnable — and it goes through `deploy.deploy()` like
   every other path under `~`, so a hand-edit is shown as a diff and asked about rather than
   clobbered.
4. **Deployment becomes multi-agent** — generalize `[packages.claude-global-md]`'s `symlink_dest`
   from one path to a list, so the assembled file is linked into `~/.claude/CLAUDE.md`,
   `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`, `~/.copilot/copilot-instructions.md` and whatever
   else is confirmed. Rename the package — `claude-global-md` is the wrong name for a cross-agent
   artifact.

   The content split behind this: portable conventions (commit granularity, research depth, reading
   a command's result, the caveman style) ship from `agent-skills`, because they are genuinely one
   design with the skills — the tier-1/tier-2/tier-3 model in `contributing/global-agents-md.md`
   spans both, and rules there point at skills and vice versa. PULSE-mechanism rules (`sudo -A`
   because of `askpass-zenity`, "installing a tool goes through `setup.toml`", "never hand-edit a
   deployed dotfile", `inv quality.precommit`) stay in PULSE: they are not conventions, they are
   documentation of one machine's mechanisms, actively misleading to anyone without PULSE, and
   keeping them here means the rule and the mechanism it describes change in the same commit. A
   non-PULSE user gets only the portable half, which is the correct outcome.
5. **Pilot on one skill first.** `plan-docs` is the best candidate: self-contained, no machine
   specifics, already has `references/`. Publish it alone, install it with `skills add`, confirm the
   symlink lands for Claude Code _and_ one other agent, confirm live-reload, and only then move the
   rest. `~/AGENTS.md`'s "pilot on one real repo before writing the shareable version" rule is
   exactly this case.
6. **Per-repo API skills live in the repo they describe, not in `agent-skills`.** A skill about
   `repo-tasks`' interface belongs in `repo-tasks`, committed, versioned with the code it documents
   — the same reason `AGENTS.md` is per-repo. Layout is the standard one:
   `.agents/skills/<name>/SKILL.md` at the repo root, with per-agent symlinks (`.claude/skills`,
   `.codex/skills`, ...) alongside. That makes it available to any agent working in that repo with
   zero install step, and to a consumer repo via `npx skills add TheodoreAD/<repo>` if it turns out
   to be wanted globally. **`scaffoldapy` should stamp the skeleton**, the same way it already
   stamps `AGENTS.md`/`CLAUDE.md`/`.agents/skills` — that is precisely its "written once, then
   diverges per repo" bucket in `contributing/repo-family-architecture.md`. The content bar: what an
   _outside_ caller needs (task names, flags, entry points, contracts) — not how to develop the
   repo, which is what its `AGENTS.md` already covers.
7. **MCP stays as `contributing/mcp-skill-shipping.md` already has it** — `uv tool install git+…`,
   stable binary name, `claude mcp add --scope user`. Its deferred `mcp_servers` field in
   `tasks/ai.py` is now the _right_ thing to build eventually, because the alternative (a plugin's
   `.mcp.json`) is vendor-locked. It should be designed cross-agent from the start, since MCP
   registration paths differ per agent the same way instruction files do.

**Deliberately not doing:** Claude plugins/marketplaces/`~/.claude/rules/` (constraint); MCPB
bundles (heavier than needed for single-user servers, and orthogonal to this plan); a second private
repo (constraint); submitting anything to a vendor marketplace.

## Sources

- [Linux Foundation — Agentic AI Foundation formation (MCP, goose, AGENTS.md)](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation),
  [OpenAI — co-founding the AAIF](https://openai.com/index/agentic-ai-foundation/)
- [`vercel-labs/skills` (the `skills` CLI)](https://github.com/vercel-labs/skills),
  [skills.sh CLI docs](https://www.skills.sh/docs/cli),
  [`agentskills/agentskills` spec](https://github.com/agentskills/agentskills),
  [Agent Skills as a cross-tool standard](https://agentpatterns.ai/standards/agent-skills-standard/)
- [`agentsmd/agents.md` issue #91 — global user-level AGENTS.md](https://github.com/agentsmd/agents.md/issues/91),
  [AI harness engineering compatibility matrix (June 2026)](https://codylindley.github.io/ai-harness-engineering-compatibility-matrix/),
  [Agent instruction files & cross-tool portability with Codex CLI](https://codex.danielvaughan.com/2026/05/27/agent-instruction-files-agents-md-claude-md-cross-tool-portability-codex-cli/)
- [`obra/superpowers`](https://github.com/obra/superpowers),
  [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills)
- Rejected-branch research: [Claude Code plugins](https://code.claude.com/docs/en/plugins),
  [plugins reference](https://code.claude.com/docs/en/plugins-reference),
  [plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces),
  [skills](https://code.claude.com/docs/en/skills),
  [cloud environments](https://code.claude.com/docs/en/cloud-environments)
