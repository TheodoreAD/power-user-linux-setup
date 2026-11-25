---
status: in-progress
updated: 2026-11-25
---

# `AGENTS.md` and `.agents/skills` as the only source, at home and in every repo

## Context

Asked 2026-11-25, after a Claude Code upgrade to 2.1.332: _"do a thorough review of what claude can
do now regarding agents.md and .agents/skills, and how we install and update skills in general.
there are a few repos involved […] the purpose is to have a universal approach as much as possible
with as little customization on our side. we are planning to use more agents than claude, and we
should have a single source of truth in agents.md and .agents/skills, both in the user home and in
each repo."_ Two additions the same day: wire `node.update-globals` into the update chain, and make
the `skills` CLI install minimally — the universal copy, plus only the links an agent that does not
read the universal path needs.

This plan supersedes the open half of `plans/2026-09-02-agent-harness-support-matrix.md` (its rungs
and per-vendor table) with a re-measurement, and spans four repos: this one, `agent-skills`,
`scaffoldapy` and `repo-tasks`, and the repos that carried a `CLAUDE.md`. The first draft proposed
filing a plan per repo; the user then authorised the cross-repo edits directly, see "Done".

### How this was measured

Source clones in the research library, refreshed 2026-11-25 (19 entries, plus a new Warp clone and
the refreshed vscode-docs and Roo Code clones). Claude Code, Cursor and Amp are closed, so their
rows come from vendor pages; Claude Code's were mirrored the same day into the research library's
`pages/claude-code-docs-2026-11-25/` (`memory.md`, `skills.md`, `settings.md`, plugin and subagent
pages) together with its public `CHANGELOG.md`. Every cell below cites where it was read. The
mirrors and clones are local to this machine, not part of this repo.

## What changed since September

**Claude Code reads a repo's `AGENTS.md` natively since 2.1.277** (changelog; `memory.md`, section
"AGENTS.md"), through a built-in plugin `cc-plugin-agents-md@builtin`. Default mode
`claude-md-or-agents-md`: it reads every `AGENTS.md` and `.claude/AGENTS.md` from the working
directory up, **but only when no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` exists in the
working directory or above it**. `~/.claude/CLAUDE.md` does not count against it. A `CLAUDE.md`
symlinked to `AGENTS.md` is read once either way. Unchanged, and stated outright on the same page:
it reads **nothing under a `.agents/` directory** — not `~/.agents/AGENTS.md`, not `.agents/skills`
at either level. Skills come only from `~/.claude/skills` and `.claude/skills`, where a
`<skill-name>` entry may be a symlink (`skills.md`, "Choose where skills load").

Two details that constrain the design:

- `~/.claude/skills/synced/` is Claude Code's own, for skills synced from the claude.ai account, and
  removed skills go to `~/.claude/skills/.trash/`. So `~/.claude/skills` must stay a real directory:
  as a symlink to `~/.agents/skills` it would put Anthropic's synced skills and a trash folder into
  the directory every other agent reads.
- Claude Code's Edit and Write refuse to write through a symlinked `CLAUDE.md` and redirect to the
  target. Harmless, but one more reason the repo symlinks are now pure overhead.

**The `skills` CLI is 1.9.0** (upgraded here the same day; it had sat at 1.5.24 since the summer,
see "The update chain"). Read in `vercel-labs/skills` at that version:

- `add -g` always writes the real copy to `~/.agents/skills/<name>` (`installer.ts`,
  `getCanonicalSkillsDir`). An agent that reads that directory itself gets nothing more
  (`readsCanonicalGlobally`). Every other selected agent gets one **per-skill** relative symlink in
  its own directory — a junction on Windows, a copy only as a fallback or with `--copy`. Claude Code
  is one of those, so `--agent claude-code` produces exactly the canonical copy plus
  `~/.claude/skills/<name> -> ../../.agents/skills/<name>`, and nothing else.
- Without `--agent` it targets every agent it **detects**, and its registry lags: Crush, Goose and
  Roo are recorded with their own directories though all three read `~/.agents/skills`, so a bare
  `skills add` writes redundant links for them. `universal` is a valid `--agent` value, and naming
  it is a no-op beside the canonical copy that is always written.
- New commands: `update [-g|-p]` (follows each lock entry's ref head and moves its recorded commit),
  `check` (exit 1 when an update or a local change exists), `remove --all`, and project restore
  `install` from a committed `skills-lock.json`, `--frozen-lockfile` by default in CI.
- The global lock is `~/.agents/.skill-lock.json`, version 3, recording source, ref, commit, tree
  hash and `installMode` per skill. Two claims in `agent-skills` that a global install writes no
  lock file are wrong; they looked for the project lock's filename. This machine's lock still lists
  `deploy-to-vercel`, which is not installed.
- Telemetry and the audit request are off with `DO_NOT_TRACK=1` or `DISABLE_TELEMETRY=1`, which
  `tasks/ai.py` already sets.

**The rest of the field converged further on `.agents/skills`**, and not on `~/.agents/AGENTS.md`.

### The matrix, 2026-11-25

`~/.agents/AGENTS.md` and `.agents/skills` are the two canonical paths. "Native" means the agent
reads it with no file or setting from us.

| agent                | home instructions                                                                     | home skills (`~/.agents/skills`) | repo `AGENTS.md`                      | repo `.agents/skills` |
| -------------------- | ------------------------------------------------------------------------------------- | -------------------------------- | ------------------------------------- | --------------------- |
| Claude Code          | `~/.claude/CLAUDE.md` only                                                            | no — `~/.claude/skills`          | native since 2.1.277, if no CLAUDE.md | no — `.claude/skills` |
| Codex                | `~/.codex/AGENTS.md` (`AGENTS.override.md` shadows it)                                | native                           | native, root down to cwd              | native                |
| Gemini CLI           | `~/.gemini/GEMINI.md`                                                                 | native                           | only via `context.fileName`           | native                |
| Copilot CLI          | `~/.copilot/copilot-instructions.md`, or `COPILOT_CUSTOM_INSTRUCTIONS_DIRS=~/.agents` | native                           | native                                | native                |
| VS Code, local agent | profile only, no file                                                                 | native                           | native (root; nested off by default)  | native                |
| opencode             | `~/.config/opencode/AGENTS.md`, **else `~/.claude/CLAUDE.md`**                        | native                           | native                                | native                |
| Goose                | **native**                                                                            | native                           | native                                | native                |
| Cline                | **native**                                                                            | native                           | native (root)                         | native                |
| Kimi Code            | **native**                                                                            | native                           | native                                | native                |
| Warp                 | **native** (the only file-based global rule)                                          | native                           | native                                | native                |
| Zed                  | `~/.config/zed/AGENTS.md`                                                             | native (its only user path)      | native (root)                         | native                |
| Crush                | `~/.config/AGENTS.md`                                                                 | native                           | native                                | native                |
| Amp                  | `~/.config/amp/AGENTS.md` or `~/.config/AGENTS.md`                                    | native                           | native                                | native                |
| Cursor               | settings UI only, no file                                                             | native                           | native, nested too                    | native                |

Sources, by row: Codex `codex-rs/codex-home/src/instructions/mod.rs`,
`ext/skills/src/host_roots.rs`, `core/src/agents_md.rs`; Gemini CLI
`packages/core/src/utils/memoryDiscovery.ts`, `skills/skillManager.ts`, `docs/cli/gemini-md.md`;
Copilot CLI GitHub's docs source,
`content/copilot/reference/copilot-cli-reference/cli-command-reference.md` (instructions and skills
tables); VS Code `vscode-docs`, `docs/agent-customization/agent-skills.md` and
`custom-instructions-reference.md`; opencode `packages/core/src/config/plugin/instruction.ts`,
`config/discovery.ts`; Goose `crates/goose/src/hints/load_hints.rs`, `skills/mod.rs`; Cline
`sdk/packages/shared/src/storage/paths.ts`; Kimi Code
`packages/agent-core-v2/src/agent/profile/context.ts`, `features/skill/catalog/skillRoots.ts`; Warp
`crates/ai/src/project_context/global_rules.rs`, `crates/ai/src/skills/skill_provider.rs`; Zed
`crates/paths/src/paths.rs`, `prompt_store/src/prompts.rs`, `agent_skills/agent_skills.rs`; Crush
`internal/config/load.go`, `config.go`; Amp and Cursor, their docs pages. Roo Code also reads both
`.agents/skills` paths, but its repository was archived 2026-05-15, so it is not a target.

Read across, the matrix says:

- **Skills are solved everywhere except Claude Code**, at both levels. Thirteen of fourteen read
  `~/.agents/skills` and `.agents/skills` natively. Claude Code needs one link per skill.
- **Repo instructions are solved everywhere except Gemini CLI**, which needs a per-machine setting,
  and Claude Code, which needs the repo to _not_ have a `CLAUDE.md`.
- **Home instructions are the fragmented part.** Four agents read `~/.agents/AGENTS.md`; the rest
  each have a vendor path, and two have no file at all. One `~/.config/AGENTS.md` would serve both
  Crush and Amp.
- **No sync tool is needed.** ruler, rulesync and agentsmesh earn their keep translating MCP
  servers, hooks and permissions, which neither `AGENTS.md` nor skills covers. For instructions and
  skills alone, the shims above are a handful of copies and links.

## Where we stand, against that

Inventoried 2026-11-25 across every repo under the personal projects root and the home directory.

**Home** — already the target shape, with drift around it:

- `~/.agents/AGENTS.md` is the assembled real file; `~/.claude/CLAUDE.md` and
  `~/.copilot/copilot-instructions.md` are byte-identical copies (`[packages.agents-md]`
  `also_deploy_to`). Codex and Gemini are not installed, so their copies are correctly absent.
- `~/.agents/skills` holds 16 real skill directories, and `~/.claude/skills` is a real directory of
  16 per-skill symlinks plus `synced/` — exactly the CLI's per-skill layout.
- `[packages.agent-skills]` passes `agents = ["claude-code", "github-copilot"]`. The second element
  is a no-op, as the entry's own comment says.
- **Install and update are one command.** `inv ai.install-skills` runs `skills add … --global --yes`
  for each declared entry and cannot tell an install from a refresh, so it asks every time.
  `skills
  update -g` did not exist when it was written.

**Repos** — the old shape everywhere it exists:

- Every `CLAUDE.md` in the personal repos is a 9-byte symlink to `AGENTS.md`: this repo,
  `agent-skills`, `repo-tasks`, `scaffoldapy` and its `template/`, `hekate`, `ingesta`,
  `invoke-stubs`, `olx-polite-mcp`, `freshful-polite-mcp`, `temu-polite-mcp`. None imports, none
  holds content. No repo has a `GEMINI.md` or `.github/copilot-instructions.md`.
- `.claude/skills` is a committed **directory** symlink to `.agents/skills` in
  `freshful-polite-mcp`, `ingesta` and the scaffoldapy template (relative), and in `repo-tasks` and
  `olx-polite-mcp` (**absolute**, `/home/<user>/projects/…`, so broken on every other machine and in
  CI).
- scaffoldapy stamps that layout into every generated project, with a README stub saying Claude Code
  cannot read `.agents/skills`, and pins it in `tests/unit/test_template.py`.

**Stale text that now contradicts the machine**, found while inventorying:

- `docs/ai.md` still says every arrow is a symlink and mentions an `always` link; both went in
  September. `docs/claude-code.md` has the same leftovers in its `~/.agents/AGENTS.md` and
  `.agents/skills/` sections, and still says `CLAUDE.md` is "only ever a symlink".
- `setup.toml`'s `[packages.agent-skills]` description still says `inv ai.install-skills` maintains
  a `~/.claude/skills` symlink, which `_ensure_agents_skills` stopped doing on 2026-09-07.
- `agent-skills`' `skill-authoring-taudelta` tells the reader to
  `ln -s ~/.agents/skills
  ~/.claude/skills` — the directory link this plan rules out — and says a
  global install writes no lock file.
- scaffoldapy's `template/AGENTS.md`, its own `AGENTS.md` and `repo-tasks`' `AGENTS.md`, docs and
  `projects.py` still send readers to `~/AGENTS.md`, which has not existed since 2026-09-09.
- The global rule "`CLAUDE.md`, if present at all, is a plain symlink" in
  `config/agents-md/agent-knowledge.md` was right until 2.1.277 and is now the wrong default.

## The target

**At home**, the canonical files are `~/.agents/AGENTS.md` (assembled by PULSE) and
`~/.agents/skills/` (written by the `skills` CLI). Every other path is a shim, and a shim exists
only for an agent that is installed and does not read the canonical one:

| shim                                 | for         | kind                           |
| ------------------------------------ | ----------- | ------------------------------ |
| `~/.claude/CLAUDE.md`                | Claude Code | copy (kept, see decision)      |
| `~/.claude/skills/<name>`            | Claude Code | per-skill link, by the CLI     |
| `~/.codex/AGENTS.md`                 | Codex       | copy, when `~/.codex` exists   |
| `~/.copilot/copilot-instructions.md` | Copilot     | copy, when `~/.copilot` exists |
| `~/.gemini/GEMINI.md`                | Gemini CLI  | copy, when `~/.gemini` exists  |

**In a repo**, `AGENTS.md` and `.agents/skills/` are the only files with content. No `CLAUDE.md`.
One shim stays, because Claude Code is the one agent that cannot see the skills: `.claude/skills` as
a committed **relative** directory symlink to `../.agents/skills`, only in repos that have skills.

[DECISION: **keep `~/.claude/CLAUDE.md` a copy, not a one-line `@~/.agents/AGENTS.md` import.** The
import is now documented, loads without an approval dialog from a user-scope file, and would remove
the drift check entirely. It loses in three places the copy does not: opencode falls back to
`~/.claude/CLAUDE.md` when it has no file of its own and would read the literal import line; Claude
Code skips an import that leaves the working directory in Cowork sessions; and a copy is the one
wiring identical on Windows. The copy's cost, drift, is already checked by `inv verify.all` and
repaired by `inv deploy.all`.]

[DECISION: **delete every repo `CLAUDE.md` symlink.** With native reading, a `CLAUDE.md` anywhere
from the working directory up is what switches `AGENTS.md` loading off, so the symlink has gone from
"the compatibility shim" to "the one file whose presence changes which path Claude takes". Content
is identical today, so nothing breaks either way — but the target says one source, and a second path
to the same bytes is exactly what Zed, Crush, Amp and Copilot read as a fallback name. Claude Code
updates itself on every machine PULSE sets up, so a version before 2.1.277 is not a case to design
for. Rejected: setting `claude-md-and-agents-md` globally to keep the symlinks harmless — it is a
Claude-only setting that exists to tolerate a file the target does not have.]

[DECISION: **repo skills keep a committed relative `.claude/skills -> ../.agents/skills` directory
link, not per-skill links.** Repo-authored skills (the polite-mcp ones, a tool's own interface
skill) are not in any lock file, so `skills install -a claude-code` cannot produce their links; a
committed per-skill link would need a new link every time a skill is added. One relative link is
zero maintenance and is what the CLI's own installer already expects to find
(`resolveParentSymlinks`). The home directory stays per-skill because `synced/` and `.trash/` live
there; a repo `.claude/skills` holds neither. Cost: on Windows without `core.symlinks`, git checks
the link out as a one-line text file, the same limitation every committed symlink here has.]

[DECISION: **the `skills` CLI is called with `--agent universal --agent claude-code` and nothing
else** (`_DEFAULT_AGENTS` in `tasks/ai.py`). Corrected the same day: the first draft said
`claude-code` alone, from reading `getCanonicalSkillsDir`, and a throwaway-`HOME` run disproved it.
1.9.0's `defaultInstallMode` copies straight into the one directory when every target shares it, so
`claude-code` alone wrote a plain copy into `~/.claude/skills` and left `~/.agents/skills` empty.
With `universal` beside it the targets span two directories, and the CLI writes the canonical copy
plus one relative link per skill for Claude Code, and touches nothing else. `github-copilot` went
from the list. Without an explicit agent the CLI would link every detected agent, which is the
redundant shape the request ruled out.]

## The update chain

`inv node.install` installs a declared npm global only when it is missing, and
`inv
node.update-globals` (which does upgrade, per declared package, to `@latest`) is called by
nothing. That is why the `skills` CLI sat at 1.5.24 for months. Skills themselves have the same gap
one level down: they update only when `inv ai.install-skills` happens to re-run `skills add`.

[DECISION: **upgrading is its own step, not part of `inv setup`.** `inv setup` reproduces the
declared machine; an upgrade takes whatever upstream published today, which is a change nobody
reviewed — the same line `~/.agents/AGENTS.md` draws between pulling a canonical file and generating
one. So a new `inv upgrade` composite runs the upgraders that already exist plus one new one, and
`inv self.update` offers it after offering `inv setup`, so the chain the user already runs reaches
it.]

`inv upgrade`, in order:

1. `node.update-globals` — the `skills` CLI first, so step 2 runs on the current release.
2. `ai.update-skills` (new) — `skills update --global --yes` with the telemetry variables set. It
   replaces re-running `skills add` as the way skills refresh. `ai.install-skills` still runs
   `skills add` for the whole agent-skills repo, because that is how a skill added upstream arrives
   and `add --list` cannot be combined with `--json` to diff against the lock.

[DECISION: **`apt.upgrade-debs` stays out of `inv upgrade`** (user's choice, 2026-11-25: "Agent
tooling only"), so the command needs no sudo.]

## Done, 2026-11-25

The user asked for everything at once ("do absolutely everything from here, let's clean this mess
up. you have permission to work across all other repos"), so the per-repo filings this plan first
proposed were done directly instead, each repo pulled first.

**This repo** (pushed, CI green on each):

- `85242fb` — `_DEFAULT_AGENTS = ("universal", "claude-code")`, `ai.update-skills`, the agent-skills
  entry without its own `agents`. Then re-installed here: 16 skills, canonical copies plus Claude
  links, and the stale `deploy-to-vercel` lock entry removed with `skills remove -g`.
- `1b05783` — `inv upgrade` and the `self.update` offer. Run end to end: CLI unchanged at 1.9.0,
  skills up to date. Later the same day `inv ai.update-skills` picked up exactly the two skills
  agent-skills had just changed, and their Claude links survived the update — which settles the
  UNVERIFIED this plan carried about lock entries written by 1.5.24.
- `32b6632` — the global rule and this repo's `CLAUDE.md`. A headless session started afterwards
  quoted this repo's `AGENTS.md` heading and named the file, with no `CLAUDE.md` present.
- `5196841` — `docs/ai.md`, `docs/claude-code.md`, `docs/configuration.md`,
  `contributing/ai-tooling.md`.

**Elsewhere:**

- `agent-skills` — `CLAUDE.md` was already gone, removed from the user's Windows machine the same
  morning: a checkout without Developer Mode had materialised the symlink as a 9-byte text file, so
  Claude Code there loaded the word `AGENTS.md` as its instructions. `83e1013` rewrote
  `skill-authoring-taudelta`'s re-install and verify steps (`skills update`, both agent names, no
  whole-directory link), the README's install block, two lock-file claims and a `skill-fitness`
  docstring.
- `scaffoldapy` `354d4ed` — template and repo without `CLAUDE.md`, the skills README stub rewritten,
  `~/.agents/AGENTS.md` pointers, `test_template.py` asserting no `CLAUDE.md`. The template keeps
  generating `.claude/skills` for every project, not only ones with a skill: `.agents/skills` always
  exists with its README, and a link waiting for the first skill costs nothing.
- `repo-tasks` `4f82b12`, `olx-polite-mcp` `eeaffcb` — `CLAUDE.md` and the absolute `.claude/skills`
  links deleted (neither repo has a skill), `~/AGENTS.md` references fixed.
- `ingesta` `015f144`, `invoke-stubs` `7406f1d`, `freshful-polite-mcp` `83dafbf`, `temu-polite-mcp`
  `ceff62e` — `CLAUDE.md` deleted, `~/AGENTS.md` references fixed where present. `ingesta` and
  `freshful-polite-mcp` keep their relative `.claude/skills` links.
- `hekate` — through PR 19, since everything there lands by squash-merged pull request.

## Open questions

**A committed `.claude/skills` symlink does not survive a Windows checkout without Developer Mode**
— git writes it as a text file, so Claude Code there sees no repo skills. Found the same day from
the agent-skills Windows commit, which hit exactly this with `CLAUDE.md`. It is an OS-axis question,
so it is filed as a NEEDS CLARIFICATION in
`plans/2026-09-07-agents-md-and-skills-on-native-windows.md` rather than here.

[NEEDS CLARIFICATION: **should PULSE configure Gemini CLI to read `AGENTS.md`** in repos
(`context.fileName: ["AGENTS.md", "GEMINI.md"]` in `~/.gemini/settings.json`) once Gemini is
installed? It is the only agent in the matrix that needs a setting for repo instructions, and the
write is into an app-owned settings file. Not installed here, so nothing is blocked.]

[DEFERRED: **home instruction copies for agents not installed** — `~/.config/AGENTS.md` for Crush
and Amp, `~/.config/zed/AGENTS.md`, `~/.config/opencode/AGENTS.md`. The parent-exists test that
detects an installed agent does not work for `~/.config`, which always exists, so each needs its own
detection. Add when one of them is actually used.]

[NEEDS CLARIFICATION: carried from the retired `plans/2026-09-02-agent-harness-support-matrix.md` —
should `inv verify.all` check that each instruction copy's _filename_ is still what its vendor
documents? It proves the copy matches today, not that anything reads it, and a renamed vendor path
is silent. It would mean a per-agent assertion maintained by hand.]

[DEFERRED: a slow-tier test that runs the real `skills` CLI against a throwaway `HOME`, pinning the
universal-plus-claude-code layout. The CLI changed its default install mode between 1.5.24 and 1.9.0
without notice, and `inv upgrade` now takes every new release unreviewed. Worth adding once CI can
reach npm without adding minutes to every run.]

## Recommended direction

What is left is the open questions above, none of which blocks anything. The Windows
`.claude/skills` question is the one with a real user behind it, and the first time a repo with
skills is opened on the Windows machine is when to answer it.
