---
status: in-progress
updated: 2026-08-28
---

## What has landed, and what hasn't

The `~/AGENTS.md` half is **done and deployed** — the "Design — the assembled `~/AGENTS.md`" section
below (D1–D9) describes what now exists, not what is proposed: the `assembled_from`/`agents_md`
fields, the three fragments under `config/agents-md/`, `symlink_dest` as a list gated on agent
detection, the `verify.all` symlink check, and `[packages.agents-md]`'s rename. `~/AGENTS.md` is
assembled and linked into Claude Code and Copilot; Codex and Gemini are declared and skip themselves
until those agents exist here.

The **skills half is seven-ninths done.**
[`TheodoreAD/agent-skills`](https://github.com/TheodoreAD/agent-skills) is public and holds
`db-defaults`, `invoke-task-conventions`, `mcp-skill-shipping`, `plan-docs`,
`polite-mcp-conventions`, `python-conventions` and `session-harvest`. PULSE declares them in one
`[packages.agent-skills]` `source = "npx"` entry, their `skills/` directories are gone from here,
and `contributing/mcp-skill-shipping.md` folded into that skill's own `references/rationale.md` per
the rationale DECISION below. `plan-docs` went first, alone, as the pilot — see "The pilot, measured
(2026-08-27)".

**Two skills stay `source = "local"`:** `research-library` (assumes `$RESEARCH_HOME`, and ships a
`claude_permissions_allow` rule naming an absolute path under this user's home) and
`session-bash-audit` (reads `~/.claude/projects/*.jsonl` and carries this machine's permission-mode
research). Both fail `agent-skills`' own bar — "every skill has to work for someone who has only
this repo" — as written. Deciding per skill whether the assumption is declarable or whether the
skill stays here is the remaining move work; the `local` source exists for exactly that case, so
"never moves" is a legitimate outcome, not a failure.

That is what keeps this plan open, along with the `[NEEDS CLARIFICATION:]` and `[DEFERRED:]` tags
below — the pilot answered some of them and added one.

## Context

Written before any of the above landed, and describing the state at that point — the "Global
instructions" bullet in particular is now history, not current behaviour. Every AI-facing artifact
this machine uses was authored inside `power-user-linux-setup` and reached agents through this
repo's own machinery:

- **Skills** — directories under `skills/<name>/`, declared as
  `skills = [{ source = "local", path = "skills/<name>" }]` on a `[packages.<name>]` entry with
  `method = "skill"`, **copied** to `~/.agents/skills/<name>` by `inv ai.install-skills`, reaching
  Claude Code only because `~/.claude/skills` is symlinked to `~/.agents/skills`.
- **Global instructions** — `config/global-AGENTS.md` → `~/AGENTS.md` via
  `[packages.claude-global-md]`, with `~/.claude/CLAUDE.md` symlinked to it. (Both names are
  pre-change: that file is now the `config/agents-md/` fragments, and the package is
  `[packages.agents-md]`.)
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
(`cli-allowlist`, `deploy`, `verify`, `repo-family-architecture`, ...). Applied 2026-08-28 for
`mcp-skill-shipping` — folded, minus the `mcp_servers` deferral, which is a PULSE mechanism and is
carried below instead. `contributing/research-library.md` stays put while that skill does; it also
turns out to document the `$RESEARCH_HOME` machinery PULSE deploys _around_ the skill, not just the
skill, so the fold may be a split rather than a move when its turn comes.]

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

### The pilot, measured (2026-08-27)

`agent-skills` created, `plan-docs` moved into it alone, published public, and installed back onto
this machine through PULSE. What the run actually established, beyond "it works":

- **The published repo needs no manifest, exactly as researched.**
  `skills add
  TheodoreAD/agent-skills --list` against the bare GitHub repo found `plan-docs` under
  `skills/<name>/` and printed its full description. Nothing was registered anywhere.
- [PITFALL: **The announced-but-absent Claude Code symlink reproduces against the published repo,
  and `_ensure_agents_skills` is now confirmed load-bearing rather than merely suspected.** Run in a
  clean scratch directory at project scope with `--agent claude-code --agent github-copilot`, the
  CLI's "Installation Summary" box listed `symlink → Claude Code`, and the final "Installed 1 skill"
  box silently dropped that line; `find` afterwards showed `.agents/skills/plan-docs` and
  `skills-lock.json` and **no `.claude/` directory at all**. The global install on this machine
  reports both agents only because PULSE's `~/.claude/skills → ~/.agents/skills` symlink predates
  it. Deleting `_ensure_agents_skills` would take Claude Code's access to every skill with it.]
- **At global scope, `github-copilot` resolves to the `~/.agents/skills` hub, not to the
  `globalSkillsDir` its own registry entry names.** Reading the CLI bundle's agent table
  (`dist/cli.mjs`) suggests Copilot's global directory is `~/.copilot/skills`; the actual install
  wrote one real copy to `~/.agents/skills/plan-docs`, labelled it `universal: GitHub Copilot`, and
  never created `~/.copilot/skills`. So the one-canonical-copy model PULSE already assumes survives
  the move — the CLI does not fan out per-agent copies here. Do not re-derive this from the registry
  table; it disagrees with the behaviour.
- **The agents that genuinely map to `~/.agents/skills` at global scope are a short list**, from the
  same table: `cline`, `dexto`, `kimi-code-cli`, `loaf`, `warp`, `zed`. Note that the agent whose id
  is literally `universal` maps to `~/.config/agents/skills`, **not** `~/.agents/skills` — the two
  are easy to conflate and are different directories. Only `claude-code` (`~/.claude`) and
  `github-copilot` (`~/.copilot`) are detected as installed on this machine; `~/.codex`,
  `~/.cursor`, `~/.gemini` do not exist.
- **The installed copy is now indistinguishable from the eight local ones in `skills ls -g --json`**
  — all nine report `["Claude Code", "GitHub Copilot"]`. Useful for D7's check, but note what that
  means: the listing cannot tell a working install from one whose Claude Code link happens to be
  supplied by PULSE. A D7 check that only reads this listing would have passed on a machine where
  the defect above had actually bitten.
- **The dev loop got worse, not better, and that was foreseen but is worth stating plainly.** Before
  the move: edit `skills/<name>/SKILL.md`, run `inv ai.install-skills --skill=<name>`. After: edit
  in `agent-skills`, commit, **push**, then run the same task — the `skills` CLI clones from GitHub
  every time, so an unpushed edit is invisible. The local-path source (`skills add ../agent-skills`)
  is the escape hatch for iterating, but it is not what `setup.toml` declares. This sharpens the
  open question below about whether a dev loop is worth building.

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
skills. **That gap is exactly PULSE-shaped work**, and it is already half-built: the package's
`wrapper-script` + `symlink_dest` mechanism writes one real file and points a symlink at it.
Extending `symlink_dest` from one path to a list is the whole change. (Landed: it takes a list, and
skips a link whose agent directory is absent.)

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

## Design — the assembled `~/AGENTS.md`

Settled 2026-08-26. This is one subsystem of the plan; the rest stays `idea`, which is why the
file's status has not moved.

### D1. `agents_md` — a path-valued any-section field

Same scan as `zshrc`/`zshenv`/`zprofile` (`tasks/zsh.py`'s `_declared_dotfile_snippets`): any
`[packages.*]` entry may declare one, read regardless of that entry's own `method`. It differs from
the zsh fields in one way — **the value is a path, not an inline string.** A multi-line Markdown
section inside a TOML string would be unreadable and undiffable; the fragment is a real `.md` file
in the repo, edited with a Markdown editor, formatted by `dprint` with everything else:

```toml
agents_md = { src = "config/agents-md/this-setup.md", order = 10 }
```

`src` resolves the same way `config_files`' `src` does. This also means a fragment can be reviewed
on its own in a PR diff, which an inline TOML blob cannot.

[DECISION: **Fragment content is authored as whole `##` sections, never fragments of one.** A
fragment file contributes one or more complete top-level sections with their `###` rules inside.
Assembly is then ordered concatenation with no rule-level merging machinery. See D2 for the content
change this forces.]

### D2. Re-cut the clusters so no cluster straddles the portable/machine line

D1's "whole `##` sections" rule has a real cost, and it is worth paying explicitly rather than
discovering later. The current six clusters do **not** align with the portable/machine split:
`Bash & the CLI allowlist` mixes portable call-composition rules with the PULSE-generated allowlist,
and `Verification` holds one machine fact (the `ro_RO` `LC_TIME`/`LC_NUMERIC` locale rule) among
otherwise portable ones.

Two ways out: rule-level assembly (PULSE emits the `##` headings from a fixed list, each fragment
declares which cluster each `###` rule joins) or re-clustering so every rule sits in a cluster that
is wholly portable or wholly machine-specific. **Take the re-clustering.** Rule-level assembly is
real machinery for a handful of outliers, and `contributing/global-agents-md.md`'s own research says
clustering matters for adherence but **position does not** — so moving a rule between clusters is
cheap, and moving the locale rule next to `sudo -A` is arguably more honest anyway: both are facts
about this machine, not conventions. `~/AGENTS.md`'s existing top cluster is already literally
`## This machine & the harness`; the re-cut mostly grows it.

### D3. Ordering is an explicit integer, spaced

`order` on each `agents_md` entry, sparse (10, 20, 30 …) so a fragment can be inserted without
renumbering. Alphabetical-by-package is rejected: it is arbitrary and a package rename silently
reorders a document. Ties break on package name, deterministically, so two fragments at the same
order never produce a diff that depends on `setup.toml` key iteration.

### D4. Markers, and why a hand-edit is already safe

[DECISION: **`util.ensure_block(..., style=MarkerStyle.HTML)`, one block per fragment.** Already
built, already used for `docs/dev-container.md`. Two comment lines per fragment; on ~6 fragments
that is a dozen lines, visible to any agent that doesn't strip HTML comments (Claude Code documents
stripping them; nothing else does). Accepted as harmless — it is the same shape `~/.zshrc` already
carries, and a dozen comment lines in a 300-line document does not plausibly change behavior.]

The clobber risk raised while deciding this is **already covered, without needing git**:
`deploy.classify()` compares the deployed file against the manifest record of what PULSE last wrote
and returns `CLEAN`/`DIRTY`/`ABSENT`; `deploy.deploy()` prints the diff and asks before overwriting
a `DIRTY` file, defaulting to keeping it; `inv deploy.status` reports the same read-only. Routing
the assembled `~/AGENTS.md` through `deploy.deploy()` — as every other path under `~` already is —
inherits all of that with no new code.

A git-based comparison would be strictly worse: the deployed file is not in a repo, so there is no
history to compare against, and the manifest already records exactly the thing git would be
consulted for.

[PITFALL: **The markers do not give partial ownership here, and an earlier draft of this design
claimed they did.** The reasoning was that `ensure_block` only rewrites between its own markers, so
anything a human adds outside every block survives — true of `~/.zshrc`, and false of this file.
`deploy._write()` writes `expected_bytes(m)` over the whole destination, and `expected_digest` has
to be a pure function of the repo's fragments for `classify`/`diff` to mean anything at all; a
destination whose expected content depended on what was already there could not be compared. So
`~/AGENTS.md` is regenerated end to end, exactly as it was when it had a single `content_file`. The
markers earn their place as **provenance** — they name the fragment to go edit for a given section —
not as an ownership boundary, and the hand-edit protection is entirely the manifest's. Caught while
writing the tests for the mechanism, after the claim had already been written into the design, the
`config/agents-md/README.md`, and the assembled file's own header.]

### D5. The symlink farm — `symlink_dest` becomes a list

One real file (`~/AGENTS.md`), symlinks into each agent's own path. **Create a link only when the
agent's own directory already exists**, mirroring the `skills` CLI's auto-detection — `~/.codex/`
does not exist on this machine today, and creating it would be litter that makes Codex look
installed. Targets, in confirmation order: `~/.claude/CLAUDE.md` (exists today),
`~/.codex/AGENTS.md`, `~/.copilot/copilot-instructions.md`. Codex's `AGENTS.override.md` is
deliberately never touched — it is the documented per-user escape hatch and must stay hand-owned.

Rename the package, since it stops being Claude's. (Landed as `[packages.agents-md]`.)

### D6. Gemini is a settings tweak, not a symlink

Gemini CLI's `context.fileName` accepts a list, so `["AGENTS.md", "GEMINI.md"]` makes it read the
real thing directly. That is harness plumbing — explicitly admissible — and strictly better than a
`~/.gemini/GEMINI.md` symlink. Same category as `claude_default_mode`: a declared scalar synced into
a vendor settings file. [UNVERIFIED: whether `context.fileName` governs the user-level `~/.gemini/`
lookup or only the project-tree walk — if only the latter, fall back to the symlink for Gemini.]

### D7. PULSE owns a verifier for what the `skills` CLI misses

The division of labour: **use the `skills` CLI for everything it does, and have PULSE check the
result rather than reimplement it.** The verification run above found a real gap worth checking for
— the announced-but-absent Claude Code symlink — and `skills ls --json` makes the check cheap.

Fits `inv verify.all`'s existing contract ("every package a run installed also actually works"),
which is where it belongs rather than in a new namespace:

- every declared skill appears in `skills ls -g --json`, and its `agents` list contains every agent
  the entry declared — this is precisely the dropped-symlink case;
- `~/AGENTS.md` exists and is non-empty, and every `symlink_dest` target resolves to it;
- every declared fragment's block is present in the assembled file.

`inv deploy.status` covers the drift side read-only, unchanged.

### D8. Files touched

- `setup.toml` — the `agents_md` field's documentation in the header comment; the package renamed to
  `[packages.agents-md]`, `symlink_dest` becomes a list; one `agents_md` entry per fragment.
- `config/agents-md/*.md` — the fragment files; `config/global-AGENTS.md` splits into these.
- `tasks/ai.py` or a new module — the assembly, going through `deploy.deploy()`.
- `tasks/verify.py` — D7's checks.
- `contributing/global-agents-md.md` — the re-clustering rationale, and D2's trade-off.

### D9. The rule-by-rule triage, and the third category it turned up

Every heading in `config/global-AGENTS.md` classified 2026-08-26. The binary portable/machine split
assumed above **does not hold**: a handful of rules are neither. They describe Claude Code's own
behavior — not this machine, not a convention — and they would be noise in Codex or Gemini.

[DECISION: **Three fragments, not two.** `this-setup.md` (this machine, this user's repos, PULSE's
own mechanisms), `claude-code.md` (harness behavior specific to one agent), and `portable.md` (the
conventions, eventually shipped from `agent-skills`). The middle one is the carve-out the
constraints already allow — "harness plumbing that makes an agent work better" — applied to
instructions about a harness rather than to settings.]

[DECISION: **The Claude-specific fragment is visible to every agent, and that is accepted.** One
real file symlinked to N agent paths means there is no per-agent assembly; a Codex session reads the
Claude Code cluster too. Today that is four rules — cheap enough that per-agent assembled files (N
real files, no symlink farm, each agent getting exactly its own set) are not worth the multiplied
deploy targets. Revisit if the per-agent volume grows past a cluster or two. Label the cluster
plainly in prose so a non-Claude agent can skip it.]

Where each rule lands, and what has to move:

| Current cluster            | Rule                                                       | Fragment    | Note                                                                                  |
| -------------------------- | ---------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------- |
| This machine & the harness | sudo                                                       | this-setup  |                                                                                       |
| This machine & the harness | git fetch/push needing an SSH key                          | this-setup  |                                                                                       |
| This machine & the harness | Editing `~/.claude/settings.json` in auto mode             | claude-code |                                                                                       |
| This machine & the harness | Setting up a repo's agent instructions and skills          | **split**   | convention → portable; `inv ai.install-skills`/`scaffoldapy` → this-setup             |
| This machine & the harness | Saving to cross-session memory                             | **split**   | auto-memory mechanics → claude-code; "durable knowledge goes in AGENTS.md" → portable |
| This machine & the harness | Designing a uv tool-install or shared-dependency mechanism | portable    | uv/PEP 735 facts are true anywhere; **moves clusters**                                |
| This machine & the harness | Installing a tool on this machine                          | this-setup  |                                                                                       |
| Git & commits              | Pushing to a personal repo's default branch                | this-setup  | names this user's own repos; **moves clusters**                                       |
| Git & commits              | About to commit                                            | portable    | generalize `inv quality.precommit` → "the repo's quality gate"                        |
| Git & commits              | Committing multi-part work                                 | portable    |                                                                                       |
| Git & commits              | Regenerating a file from a canonical source                | portable    |                                                                                       |
| Git & commits              | Unexplained git/file state in a working tree               | portable    | soften "this user runs parallel sessions"                                             |
| Bash & the CLI allowlist   | cluster intro (`acceptEdits`, prefix matching)             | claude-code | the `cli-allowlist` half is this-setup; mostly one rewrite                            |
| Bash & the CLI allowlist   | Composing a Bash call                                      | portable    |                                                                                       |
| Bash & the CLI allowlist   | Viewing, searching, or editing files                       | portable    | Read/Grep/Edit are Claude tool names — generalize to "the harness's own file tools"   |
| Bash & the CLI allowlist   | Running a command against a different repo                 | portable    |                                                                                       |
| Bash & the CLI allowlist   | Invoking a venv tool in the session's own project          | portable    | generalize "most of this user's repos"                                                |
| Research & design          | all 8 rules                                                | portable    | unchanged                                                                             |
| Verification               | Reading a command's result                                 | portable    |                                                                                       |
| Verification               | Generalizing from a sample to a set                        | portable    |                                                                                       |
| Verification               | Verifying behavior in a repo with test coverage            | portable    |                                                                                       |
| Verification               | Formatting a date or decimal in a shell script             | this-setup  | this machine's `ro_RO` locale; **moves clusters**                                     |
| Collaboration & output     | all 5 rules                                                | portable    | generalize `AskUserQuestion`, "plan mode"                                             |
| (preamble)                 | `Plan`/`Explore` subagents never load this file            | claude-code |                                                                                       |
| (preamble)                 | "edit `config/global-AGENTS.md`, redeploy with …"          | this-setup  | rewritten: the file is assembled, edit the fragment                                   |

Roughly 23 rules portable, 6 to `this-setup`, 4 to `claude-code`, 2 split across two fragments.

Resulting clusters, in `order`:

- `0` header — how the file is assembled, which fragment owns what (this-setup)
- `10` `## This machine & this setup` — sudo, SSH askpass, locale, installing a tool, pushing to a
  personal default branch, the PULSE half of the skills/instructions rule
- `20` `## Claude Code specifics` — subagent instruction loading, `settings.json` under auto mode,
  auto-memory mechanics, the permission-mode/allowlist intro
- `30` `## Agent instructions & knowledge` — **new cluster**, portable: `AGENTS.md` as the real
  file, where durable knowledge goes. This is the half of two split rules that had no home, and it
  is the cluster `agent-skills` is most directly about.
- `40` `## Git & commits`, `50` `## Bash & tool use` (renamed — the allowlist intro left), `60`
  `## Research & design`, `70` `## Verification`, `80` `## Collaboration & output` — all portable,
  all unchanged in content apart from the moves above.

Eight clusters, up from six, with every one wholly owned by a single fragment — which is what D2
required. The two additions are the setup and Claude clusters that were previously interleaved
through the others, so nothing was actually split that was together before.

Content edits this forces, worth costing separately from the mechanism: about a dozen rules name
Claude-specific tools or this user's own repos in passing (`Read`/`Grep`/`Edit`, `AskUserQuestion`,
"plan mode", `inv quality.precommit`, "most of this user's repos"). They generalize with one-line
rewrites, but every one of them is a real edit to a rule whose exact wording was tuned for adherence
— per `contributing/global-agents-md.md`, "when a rule is observed being missed, strengthen its
language rather than lengthen its explanation." Rewrite them one at a time, not in a sweep.

### Open within this design

[DECISION: **`config/agents-md/portable.md` stays in PULSE for now**, moving to `agent-skills`
later. Decided 2026-08-26 on sequencing: splitting the content is valuable on its own and needs no
new mechanism, while moving the fragment out needs either a `git-clone`-method package (a second
mechanism pointed at a repo the skills CLI is already installing from) or a deliberate pull task
committing the fetched file — the shape `repo-tasks`' `configs.pull` uses, already governed by
`~/AGENTS.md`'s "regenerating a file from a canonical source" rule. The pull task is the better
long-term fit; it just isn't on the critical path.]

[DEFERRED: **`inv deploy.all` cannot repair a symlink**, which the new `verify.all` symlink check
made visible the moment it went red: `symlink_dest` handling lives in `tools.py`'s installer, so the
only way to create a missing link is `inv tools.install` — a much broader command than the one
`deploy.status` tells you to reach for, and than a single missing link warrants. It was harmless
here (every other installer short-circuits on "already installed"), but the repair path being wider
than the fault is the wart. The fix is probably a `links` field on `deploy.Managed`, so `deploy()`
ensures them after a successful write and symlink handling joins content in the one writer —
`lookup()` already resolves symlinks into the registry, so the module half-knows about them
already.]

[DEFERRED: **Gemini's `context.fileName` is not implemented.** The design (D6) prefers pointing
Gemini at `AGENTS.md` via its own settings over a `~/.gemini/GEMINI.md` symlink. Gemini CLI is not
installed on this machine, so writing a settings file for it would be unverifiable and speculative —
the symlink is declared instead and skips itself until `~/.gemini` exists. Revisit when Gemini is
actually installed, and verify then whether `context.fileName` governs the user-level lookup at
all.]

[DEFERRED: **Migrating a skill from `local` to `npx` orphans its deploy-manifest entry, and nothing
prunes it — there are now seven.** Confirmed 2026-08-27 on `plan-docs` and repeated 2026-08-28 for
the six that followed: once the `source = "local"` entry is gone the path leaves
`deploy.managed_paths()`, so `inv deploy.status` stops reporting it entirely — while
`~/.local/state/power-user-linux-setup/deployed.json` still records each
`/home/tdumitrescu/.agents/skills/<name>` as deployed from `skills/<name>`, sources that no longer
exist. `deploy.forget()` is written and unit-tested for exactly this and **has no production
caller**. Removing each installed directory before re-installing was likewise a bare `rm -rf` with
no task behind it. The batch this was meant to be decided before has happened, so the deferral is
now a real debt rather than a precaution: pick the mechanism (a prune step in `deploy`, or a task
calling `forget`) and clear all seven at once.]

[DEFERRED: **The `skills ls --json` per-agent check from D7 is not built**, and the pilot showed it
needs a stronger predicate than first designed. The symlink check that landed covers the instruction
file; the skills half would verify that every declared skill is visible to every declared agent. But
`skills ls -g --json` reports `["Claude Code", "GitHub Copilot"]` for a skill whose Claude Code
access comes entirely from PULSE's own symlink, so the listing alone cannot distinguish a working
install from the defect it is supposed to catch — the check has to assert the symlink's existence
and target directly, not just read the CLI's own report. Now unblocked: `plan-docs` is the first
skill actually on the `npx` source, so there is something to check.]

[DEFERRED: move `config/agents-md/portable.md` into `agent-skills` behind a pull task, once that
repo exists.]

[NEEDS CLARIFICATION: **Where does `contributing/global-agents-md.md` go?** It holds the evidence
for every `~/AGENTS.md` rule plus the admission criteria, and "rationale lives in each skill's
`references/`" gives it no home — it belongs to no skill. If the portable conventions become a
fragment shipped from `agent-skills`, the natural answer is a sibling `references/` next to that
fragment, mirroring the skill convention. But the file also carries evidence for the PULSE-specific
rules, which stay here. Likely splits the same way the rules do; needs confirming before either half
moves.]

Fragment ordering, the marker mechanism, and the hand-edit/clobber question are settled in "Design —
the assembled `~/AGENTS.md`" above (D3, D4). One question inside that design is still open; it is
stated at the end of that section rather than repeated here.

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
explicitly rather than inheriting the limitation by accident. Sharpened by the pilot: the declared
`npx` source clones from GitHub, so the real post-move loop is edit → commit → **push** → re-run the
task. Iterating on a skill against an unpushed working tree needs the local-path source, which
`setup.toml` does not declare — so "no dev loop" now costs a push per iteration, not just a
command.]

[NEEDS CLARIFICATION: **`--yes` and the non-interactive trap.** `docs/claude-code.md` records that
`_install_remote_skill`'s confirmation defaults to _proceed_ under a non-interactive shell, so an
agent running the task installs every declared remote skill with no approval gate. Moving this
repo's own skills to the `npx` source makes that path the primary one rather than the exception, so
the default needs revisiting before the migration, not after. Now live for one skill, and there is a
second gate that also isn't one: the `skills` CLI detects it is running inside a Claude Code session
and prints `Agent detected — installing non-interactively`, skipping its own prompts regardless of
what PULSE passes. So an agent running `inv ai.install-skills` fetches and installs code from GitHub
with no human in the loop at either layer. Decide before the eight-skill batch.]

[NEEDS CLARIFICATION: **What marks a skill "opinionated/niche"?** The `skills` CLI already has
`metadata: { internal: true }` + `INSTALL_INTERNAL_SKILLS=1`, but that means "work in progress", not
"personal to this author". Options: a `metadata` key of our own, a convention in the `description`,
or a `README` table in the repo. The `description` is the field agents actually match on, so putting
audience-signalling text there costs trigger quality — probably `metadata`. The pilot shipped the
`README` table form (a **Scope** column: _general_ / _opinionated but general_ / _personal_) as the
interim answer, because it is the one that needed no format decision to publish. It is not the
answer to this question: a README column is invisible to `skills find` and to anyone installing
without reading the repo. Decide the `metadata` key before the eight-skill batch, since that is when
several genuinely-personal skills arrive at once.]

## Recommended direction

Rough, and contingent on the questions above.

**One new public repo of skills, distributed by the `skills` CLI; PULSE keeps only the harness.**

1. **`agent-skills`** — plain `skills/<name>/{SKILL.md,references/,scripts/}` at the root, no
   manifest, no vendor directory. Discoverable by `npx skills add TheodoreAD/agent-skills` for
   anyone, on any of 75+ agents. Its README documents the one-liner and nothing else is required to
   consume it. **Done 2026-08-27**, public, holding `plan-docs`. It runs the family's standard
   quality composite unmodified (`inv quality.precommit` via `repo-tasks`, configs from
   `inv configure`) rather than a markdown-only shortcut — skills carry real Python in `scripts/`
   and `references/snippets/`, so ruff/basedpyright/pytest all have work once the rest arrive. Its
   own gate is `tests/unit/test_skill_layout.py`: frontmatter present, `name` matching the
   directory, `description` non-empty and under the 1024-char cap, no unexpected directory entries,
   and every skill linked from the README. That catches the one failure nothing else in the pipeline
   notices — a skill that installs cleanly and then never triggers.
2. **PULSE installs it with one declaration** — a single `[packages.agent-skills]` entry with
   `skills = [{ source = "npx", repo = "TheodoreAD/agent-skills", agents = [...] }]`, replacing nine
   `method = "skill"` blocks, `_install_local_skill` and the `.pulse-source` marker logic.
   `_ensure_agents_skills` **is not part of that deletion** — the verification above found the CLI
   does not reliably create the Claude Code link, now confirmed against the published repo. That is
   a real deletion of working, tested code, and it should happen only after the pilot below proves
   the replacement.

   **Consolidated 2026-08-28**, once seven skills had moved: one `[packages.agent-skills]` entry
   replaced seven per-skill blocks. Waiting for the last two would have meant seven npx entries all
   naming the same repo, and `_install_remote_skill` runs one `skills add` — one clone — per entry,
   so that is seven clones of the same repo per run instead of one. The `names` filter stays until
   `research-library` and `session-bash-audit` are resolved; dropping it then is what makes a new
   upstream skill arrive without editing `setup.toml`. `_install_local_skill` and the
   `.pulse-source` marker logic stay for as long as those two do.
3. **`~/AGENTS.md` becomes an assembled, multi-agent file** — fully designed in "Design — the
   assembled `~/AGENTS.md`" above: an `agents_md` any-section field, `util.ensure_block` with HTML
   markers, ordered whole-`##`-section fragments, `symlink_dest` as a list, Gemini handled by
   `context.fileName` instead of a symlink, and a `verify.all` check for what the `skills` CLI
   drops.

   The content split behind it: portable conventions (commit granularity, research depth, reading a
   command's result, the caveman style) ship from `agent-skills`, because they are genuinely one
   design with the skills — the tier-1/tier-2/tier-3 model in `contributing/global-agents-md.md`
   spans both, and rules there point at skills and vice versa. PULSE-mechanism rules (`sudo -A`
   because of `askpass-zenity`, "installing a tool goes through `setup.toml`", "never hand-edit a
   deployed dotfile", `inv quality.precommit`) stay in PULSE: they are not conventions, they are
   documentation of one machine's mechanisms, actively misleading to anyone without PULSE, and
   keeping them here means the rule and the mechanism it describes change in the same commit. A
   non-PULSE user gets only the portable half, which is the correct outcome.
4. **Pilot on one skill first — done 2026-08-27.** `plan-docs` was the candidate: self-contained, no
   machine specifics, already had `references/`. Published alone, installed with `skills add`, and
   confirmed to land for Claude Code _and_ one universal agent (`github-copilot`). Findings in "The
   pilot, measured (2026-08-27)" above; the headline one is that the CLI's dropped Claude Code
   symlink reproduces against the published repo, so `_ensure_agents_skills` stays.

   **Six more moved 2026-08-28, and it was not a mechanical repeat.** Four of them documented their
   own maintenance in terms of this repo — "edit the source at
   `power-user-linux-setup/skills/<name>/`, re-run `inv ai.install-skills`" — advice that becomes
   actively wrong on the move, naming a path the reader does not have and a command they cannot run.
   `mcp-skill-shipping` needed more: its "how skills ship" section _was_ the old mechanism, so a
   skill about shipping skills was documenting something only its author could run. Budget content
   work per skill, not a `git mv`.

   `research-library` and `session-bash-audit` remain, for the reasons in "What has landed" above.
5. **Per-repo API skills live in the repo they describe, not in `agent-skills`.** A skill about
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
6. **MCP stays as the `mcp-skill-shipping` skill has it** — `uv tool install git+…`, stable binary
   name, `claude mcp add --scope user`. The reasoning moved with the skill into its
   `references/rationale.md`; only the PULSE-mechanism half stayed behind, as the tag below.

   [DEFERRED: **A declarative `mcp_servers` field in `tasks/ai.py`.** `_install_declared_skills`
   already reads a `skills` list off any `setup.toml` package and installs it idempotently; the
   natural extension is an `mcp_servers` list read the same way, each entry
   `{name, repo, entry_point}`, driving `claude mcp add --scope user` (a no-op when already
   registered with the same command). Now the _right_ thing to build eventually, since the
   alternative — a plugin's `.mcp.json` — is vendor-locked. Not built because nothing is registered
   yet: no `*-polite-mcp` repo has a real `server.py`, and designing the installer ahead of a real
   consumer risks guessing at a shape that doesn't match what registering an actual server needs.
   Design it cross-agent from the start, since MCP registration paths differ per agent the way
   instruction files do. Carried here 2026-08-28 from the deleted
   `contributing/mcp-skill-shipping.md`, which was folded into the skill.]

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
