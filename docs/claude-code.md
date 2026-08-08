# Claude Code environment

What this repo does specifically to make [Claude Code](https://claude.ai/code) (the CLI agent)
work smoothly on this machine — as opposed to `docs/ai.md`, which covers AI tools generally
(install, model choice, other agents).

## The core problem: no TTY

Claude Code's Bash tool runs commands non-interactively — there's no controlling terminal, so
anything that tries to prompt interactively (a `sudo` password, an SSH key passphrase) just fails
outright instead of waiting for input. Two independent instances of this are solved the same way:

## askpass-zenity — GUI dialog instead of a TTY prompt

`[packages.askpass-zenity]` in `setup.toml` writes `~/.local/bin/askpass-zenity`, a script that
pops a Zenity GUI password dialog and prints whatever was entered to stdout — the standard
`*_ASKPASS` program contract. It's wired up for two separate purposes:

```shell
export SUDO_ASKPASS="${HOME}/.local/bin/askpass-zenity"
export SSH_ASKPASS="${HOME}/.local/bin/askpass-zenity"
export SSH_ASKPASS_REQUIRE="prefer"
```

**sudo** — use `sudo -A` (not plain `sudo`) for every sudo call from Claude Code. `-A` tells sudo
to use `$SUDO_ASKPASS` instead of prompting on a TTY that doesn't exist. Plain `sudo` fails with
`sudo: a terminal is required`.

**git over SSH** — `SSH_ASKPASS` + `SSH_ASKPASS_REQUIRE=prefer` fixes a related but separate
failure: this machine's SSH keys are passphrase-protected and managed by `keychain` (see
[ssh.md](ssh.md#keychain-persistent-agent-across-logins)), which loads a key into the agent
*lazily*, the first time it's actually used each session (`AddKeysToAgent yes` in `~/.ssh/config`).
If Claude Code runs the first `git fetch`/`git push` of the day before anything else has triggered
that lazy load, `ssh` needs the passphrase to unlock the key — and with no TTY, that fails as
`Permission denied (publickey)`, indistinguishable from an actual auth problem. `SSH_ASKPASS` makes
`ssh` pop the same Zenity dialog for the passphrase instead of failing. **No HTTPS/token
workaround is needed — just run `git fetch`/`git push` normally.**

`SSH_ASKPASS_REQUIRE=prefer`, deliberately not `force`: `force` would hijack passphrase prompts in
a normal interactive terminal too (popping a GUI dialog even when you're sitting at a real shell
that could just prompt you inline) — a regression to the normal workflow. `prefer` only engages the
GUI dialog when there's no usable TTY, which is exactly the Bash-tool case; an interactive terminal
session is unaffected.

The dialog blocks on user input — if nobody's at the machine to enter the passphrase, the git
command times out rather than hanging forever.

The askpass script itself shows the caller's actual prompt (`$1` — sudo passes something like
`[sudo] password for user:`, ssh passes `Enter passphrase for key '...':`) instead of a hardcoded
string, so the dialog text is accurate regardless of which one triggered it.

## `~/.claude/CLAUDE.md` — global instructions, declaratively managed

`[packages.claude-global-md]` writes `~/.claude/CLAUDE.md` (Claude Code's global, cross-project
instructions file) from `setup.toml` — the sudo/ssh guidance above is duplicated there in
Claude-readable form, so every session on this machine picks it up automatically without needing
to rediscover it. Edit the `content` field in `setup.toml`, then `inv tools.install`, rather than
hand-editing `~/.claude/CLAUDE.md` directly — a manual edit gets silently overwritten on the next
`inv tools.install` run since the file is treated as fully PULSE-owned (same as any
`wrapper-script`-method entry).

## Per-project instructions: `AGENTS.md`, not memory

This repo's own root has an `AGENTS.md` (actual content — the cross-tool standard several agent
CLIs read) and a one-line `CLAUDE.md` that does `@AGENTS.md` (Claude Code has no native AGENTS.md
support — confirmed against its own docs — so this is the officially documented import pattern).

Durable, repo-specific knowledge (how `setup.toml`'s tag system works, what modules already exist,
etc.) belongs in `AGENTS.md`, **not** in Claude Code's cross-session memory system
(`~/.claude/projects/.../memory/`). Memory is invisible to every other contributor, every other
agent tool, and every code review — `AGENTS.md` is version-controlled and visible to all three.

## Slash commands

`[packages.node].global_packages` includes `skills` (an npm package installed globally via `nvm`),
which provides `npx skills add <owner>/<repo>` — installs Claude Code slash commands from a GitHub
repo. See `docs/js.md` for the general Node/nvm global-package mechanism.
