---
status: idea
updated: 2026-11-08
---

# The one-skill refresh command targets every agent

## Context

`setup.toml`'s `[packages.agent-skills]` description says that, since the entry carries no `names`
filter, "a one-skill refresh is `skills add TheodoreAD/agent-skills --global --skill <name>`
directly". That command has no `--agent`, while the declared entry installs for exactly
`["claude-code", "github-copilot"]`.

Observed 2026-11-08 from an agent session in agent-skills:
`npx skills add TheodoreAD/agent-skills
--global --skill release-herald -y` printed "Agent detected
— installing non-interactively" and installed for **every detected agent** — "universal: GitHub
Copilot, Amp, Antigravity, Antigravity CLI, Cline +12 more", "overwrites: Claude Code, Cline, Dexto,
Kimi Code CLI, Loaf +2 more", plus "✗ release-herald → PromptScript: PromptScript does not support
global skill installation".

It was harmless on this machine only because every agent it named reads the shared
`~/.agents/skills`: checked afterwards, the skill existed in `~/.agents/skills/release-herald` and
the `~/.claude/skills` symlink and nowhere else, and `~/.agents/.skill-lock.json` recorded it like
every other skill. On a machine with an agent that keeps its own skills directory, the documented
command would write copies there that `setup.toml` never declared. Re-running
`inv ai.install-skills` afterwards does not remove them, since installs are additive.

The session also skipped the documented preference itself — `skill-authoring-taudelta` step 6 says
to run the declarative mechanism where one exists — so this is two misses: a rule not followed, and
a fallback command that is wrong when it is followed.

## Recommended direction

- Fix the documented one-skill refresh to name the declared agents:
  `skills add TheodoreAD/agent-skills --global --skill <name> --agent claude-code --agent github-copilot`
  (check the CLI's actual flag spelling for several agents before writing it).
- Better, make it unnecessary: let `inv ai.install-skills --skill <name>` pass `--skill` through to
  a `names`-less entry, carrying the entry's own `agents`, so the narrow refresh goes through the
  declared mechanism too. The description's stated reason it cannot ("ai.py can't know a remote
  repo's skill list without fetching it") applies to validating the name, not to passing it on — the
  CLI validates it.
- Consider whether the agent-skills repo's `test_remote_install_commands_are_global` should also
  require `--agent` on remote install lines — probably not for a published skill a stranger runs,
  where "every agent you have" is the right default; this is a this-machine concern.
