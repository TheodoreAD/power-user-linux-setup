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

- **`AGENTS.md`** — the cross-tool instructions file. PULSE assembles `~/AGENTS.md` from the
  fragments in `config/agents-md/` and deploys it once.
- **`.agents/skills/`** — the cross-tool location for Agent Skills. PULSE installs every skill it
  declares into `~/.agents/skills/`, once.

Each agent then reads that same content from wherever it happens to look:

| Agent          | Reads the instructions from                          | Finds the skills                        |
| -------------- | ---------------------------------------------------- | --------------------------------------- |
| Claude Code    | `~/.claude/CLAUDE.md` → `~/AGENTS.md`                | `~/.claude/skills` → `~/.agents/skills` |
| Codex          | `~/.codex/AGENTS.md` → `~/AGENTS.md`                 | —                                       |
| GitHub Copilot | `~/.copilot/copilot-instructions.md` → `~/AGENTS.md` | via the `skills` CLI                    |
| Gemini CLI     | `~/.gemini/GEMINI.md` → `~/AGENTS.md`                | —                                       |

Every arrow is a symlink, so there is exactly one file to edit and no copies to keep in sync.

**A link is only created when its agent's own directory already exists** — the absence of
`~/.codex/` is how PULSE knows Codex is not installed here, so nothing is created for it. Install an
agent later and `inv deploy.all --name agents-md` links it in; `inv verify.all` then checks each
link resolves to the file this repo deploys, rather than to some stale hand-made copy.

!!! note

    Reading the file is not the same as PULSE installing or configuring the agent. Only Claude Code
    gets all three today — installed, instructed, and skills wired natively. The others get the
    instructions if they are present, which is the cheap and useful part.

## See also

- [Claude Code](claude-code.md) — the statusline, the `AGENTS.md`-over-`CLAUDE.md` convention,
  skills scaffolding for a project, and the permission settings
- [CLI allowlist](cli-allowlist.md) — generating agent permission rules from the real `--help`
  output of every CLI installed here, so read-only commands stop prompting
- [Package catalog](packages.md) — everything else this repo installs
