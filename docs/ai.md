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

| Agent          | Reads the instructions from                          | Finds the skills in                     |
| -------------- | ---------------------------------------------------- | --------------------------------------- |
| Claude Code    | `~/.claude/CLAUDE.md` → `~/AGENTS.md`                | `~/.claude/skills` → `~/.agents/skills` |
| Codex          | `~/.codex/AGENTS.md` → `~/AGENTS.md`                 | `~/.agents/skills`, natively            |
| GitHub Copilot | `~/.copilot/copilot-instructions.md` → `~/AGENTS.md` | `~/.agents/skills`, natively            |
| Gemini CLI     | `~/.gemini/GEMINI.md` → `~/AGENTS.md`                | `~/.agents/skills`, natively            |

Every arrow is a symlink, so there is exactly one file to edit and no copies to keep in sync. Only
Claude Code needs one for the skills: the other three read `~/.agents/skills` themselves, as their
own source and documentation say — Codex and Gemini CLI alongside a vendor directory of their own,
Copilot as one of the two places it accepts. So **every agent PULSE hands the instructions to also
picks up the skills**, and the one that does not read the cross-tool location is the one PULSE
installs.

**A link is only created when its agent's own directory already exists** — the absence of
`~/.codex/` is how PULSE knows Codex is not installed here, so nothing is created for it. Install an
agent later and `inv deploy.all --name agents-md` links it in; `inv verify.all` then checks each
link resolves to the file this repo deploys, rather than to some stale hand-made copy.

### It goes wider than the four, in a repo

`.agents/skills` is not a PULSE invention. The [`skills`](https://github.com/vercel-labs/skills)
CLI, which is what installs these, carries a registry of 71 agents, and **19 of them read
`.agents/skills` in a repository** with no configuration — amp, Cline, Codex, Cursor, Gemini CLI,
GitHub Copilot, opencode, Warp, Zed and ten more. Claude Code is not one of them, which is why the
`~/.claude/skills` symlink exists.

That is a claim about a **project** directory you commit alongside the code, not about `~`. The four
agents above are the ones confirmed to read the home-directory copy PULSE writes; for the rest,
check the vendor's own docs before assuming, because the registry's own record of where each agent
looks in `~` is stale in every case we have checked — details in `contributing/ai-tooling.md`.

!!! note

    Reading the file is not the same as PULSE installing or configuring the agent. Only Claude Code
    gets all three today — installed, instructed, and skills found. The others get the instructions
    and the skills if they are present, which is the cheap and useful part.

## See also

- [Claude Code](claude-code.md) — the statusline, the `AGENTS.md`-over-`CLAUDE.md` convention,
  skills scaffolding for a project, and the permission settings
- [CLI allowlist](cli-allowlist.md) — generating agent permission rules from the real `--help`
  output of every CLI installed here, so read-only commands stop prompting
- [Package catalog](packages.md) — everything else this repo installs
