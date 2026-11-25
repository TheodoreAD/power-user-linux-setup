# AI tools

What PULSE does for coding agents. The short version: it installs one agent, and it writes the
instructions and skills **every** agent reads, in the cross-tool locations they all look at — so
whichever agent you choose, it starts on this machine already knowing how this machine works.

You choose the tools. This repo's job is to make the machine good for whichever ones you choose.

## What PULSE installs

| Tool               | How                                                                                            |
| ------------------ | ---------------------------------------------------------------------------------------------- |
| Claude Code        | `[packages.claude-code]` — the native self-updating installer                                  |
| Claude desktop app | `[packages.claude-desktop]` — a community Debian repackage, on machines with a desktop (`gui`) |

That is the whole list, and it is deliberately short: an agent is a personal choice, and installing
one is a single command in every case. See [Package catalog](packages.md) for everything else this
repo installs, and `contributing/ai-tooling.md` in the repo for install notes on the other agents,
editor extensions and local model runners — Ollama, Aider, Goose, Gemini CLI, Continue.dev, Cline,
Copilot, Cursor, Windsurf and Tabby.

## The part that is not Claude-specific

Two conventions do the work, and neither belongs to any one vendor:

- **`AGENTS.md`** — the cross-tool instructions file. PULSE assembles `~/.agents/AGENTS.md` from the
  fragments in `config/agents-md/` and deploys it once.
- **`.agents/skills/`** — the cross-tool location for Agent Skills. PULSE installs every skill it
  declares into `~/.agents/skills/`, once.

Both halves live under `~/.agents/`, which is nobody's vendor directory. Every other path below is a
shim for an agent that does not read the cross-tool one, and a shim is written only for an agent
that is installed — the absence of `~/.codex/` is how PULSE knows Codex is not, so nothing is
created for it.

| Agent                         | Reads the instructions from                          | Finds the skills in                         |
| ----------------------------- | ---------------------------------------------------- | ------------------------------------------- |
| Claude Code                   | `~/.claude/CLAUDE.md`, a copy                        | `~/.claude/skills/<name>`, a link per skill |
| Codex                         | `~/.codex/AGENTS.md`, a copy                         | `~/.agents/skills`, natively                |
| GitHub Copilot                | `~/.copilot/copilot-instructions.md`, a copy         | `~/.agents/skills`, natively                |
| Gemini CLI                    | `~/.gemini/GEMINI.md`, a copy                        | `~/.agents/skills`, natively                |
| Goose, Warp, Cline, Kimi Code | `~/.agents/AGENTS.md`, natively                      | `~/.agents/skills`, natively                |
| opencode, Zed, Crush, Amp     | a vendor path PULSE does not write yet, see the plan | `~/.agents/skills`, natively                |

**The instruction shims are copies, not symlinks.** Claude Code skips a symlinked
`~/.claude/CLAUDE.md` in some sessions, opencode reads that same file as its fallback, and Windows
cannot make a file link without privileges — a copy behaves the same everywhere. `inv verify.all`
checks each copy's content against the real file, and `inv deploy.all --name agents-md` rewrites
them; install an agent later and the same command adds its copy.

**The skills are one real copy plus Claude Code's links.** The
[`skills`](https://github.com/vercel-labs/skills) CLI installs with
`--agent universal --agent claude-code`, which writes each skill once to `~/.agents/skills/` and
links `~/.claude/skills/<name>` to it, and touches no other agent's directory. Every agent in the
table except Claude Code reads `~/.agents/skills` itself. `~/.claude/skills` stays a real directory
because Claude Code keeps skills synced from a claude.ai account there.

### In a repo

- **`AGENTS.md` at the root, and no `CLAUDE.md`.** Claude Code reads `AGENTS.md` itself since
  2.1.277, but only while no `CLAUDE.md` exists in the directory or above it. Codex, Copilot,
  opencode, Cursor, Zed and the rest read it natively; Gemini CLI does once `context.fileName` lists
  it.
- **Skills authored in `skills/<name>/`, installed per clone.** repo-tasks' `inv dev-env.setup` runs
  `agents.install-skills`, which has the `skills` CLI copy each one into `.agents/skills/` — the
  directory every agent surveyed reads except Claude Code — and link it from `.claude/skills/` for
  Claude Code, as a junction on Windows. `.agents/skills/`, `.claude/skills/` and `skills-lock.json`
  are gitignored: no symlink is committed, and trying another skill in the project with
  `npx skills add` changes nothing git tracks.

The survey behind both tables — fourteen agents, each checked against its source or its vendor's
docs — is `plans/2026-11-25-agents-md-and-agents-skills-as-the-only-source.md`, with the per-vendor
install notes in `contributing/ai-tooling.md`.

### Keeping skills current

`inv ai.install-skills` installs; `inv ai.update-skills` updates what is installed, from each
skill's recorded source. `inv upgrade` runs the CLI's own upgrade and then the skills update, and
`inv self.update` offers it. None of it is part of `inv setup`, which reproduces the machine rather
than taking whatever upstream released today.

!!! note

    Reading the file is not the same as PULSE installing or configuring the agent. Only Claude Code
    gets all three today — installed, instructed, and skills found. The others get the instructions
    and the skills if they are present, which is the cheap and useful part.

## See also

- [Claude Code](claude-code.md) — the statusline, the instructions file, skills, and the permission
  settings
- [CLI allowlist](cli-allowlist.md) — generating agent permission rules from the real `--help`
  output of every CLI installed here, so read-only commands stop prompting
- [Package catalog](packages.md) — everything else this repo installs
