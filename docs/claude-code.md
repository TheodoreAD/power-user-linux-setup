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

## Installing the CLI

`[packages.claude-code]` installs the `claude` binary itself via `inv tools.install`, using
Anthropic's native installer (`curl -fsSL https://claude.ai/install.sh | bash`) — a `script`-method
entry, same as Oh My Zsh. This is the officially recommended method: it needs no Node.js, ships a
signed per-platform binary, and auto-updates itself in the background (`~/.local/bin/claude`
symlinked into `~/.local/share/claude/versions/`). Don't use `npm install -g @anthropic-ai/claude-code`
for a fresh install on this machine — it still works but is the legacy path; PULSE only needs to
`curl`-install once and then leaves auto-update to Claude Code itself.

## `~/.claude/CLAUDE.md` — global instructions, declaratively managed

`[packages.claude-global-md]` writes `~/.claude/CLAUDE.md` (Claude Code's global, cross-project
instructions file) from `setup.toml` — the sudo/ssh guidance above is duplicated there in
Claude-readable form, so every session on this machine picks it up automatically without needing
to rediscover it. Edit the `content` field in `setup.toml`, then `inv tools.install`, rather than
hand-editing `~/.claude/CLAUDE.md` directly — a manual edit gets silently overwritten on the next
`inv tools.install` run since the file is treated as fully PULSE-owned (same as any
`wrapper-script`-method entry).

Two conventions live there too, deliberately global rather than repeated per-repo — see the
`content` field for the exact wording:

- **`CLAUDE.md` is only ever a shim.** Any repo that wants agent instructions should have a real
  `AGENTS.md` (the cross-tool standard 30+ agent CLIs read — Anthropic's own docs recommend this
  import pattern) and, if `CLAUDE.md` exists at all, it's a one-line `@AGENTS.md` import. This
  repo's own root follows that: `AGENTS.md` has the actual content, `CLAUDE.md` is `@AGENTS.md`.
- **Cross-session memory policy.** Durable, repo-specific knowledge belongs in that repo's
  `AGENTS.md`, not Claude Code's auto-memory system (`~/.claude/projects/.../memory/`) — memory is
  invisible to every other contributor, every other agent tool, and every code review; `AGENTS.md`
  is version-controlled and visible to all three.

## `.agents/skills/` and project scaffolding — `tasks/ai.py`

`.agents/skills/` is the emerging cross-tool convention for Agent Skills, but Claude Code itself
currently only discovers skills from `~/.claude/skills/` and `<project>/.claude/skills/` — not
`.agents/skills/` directly. To get both the cross-tool convention *and* a working Claude Code setup,
PULSE symlinks `.claude/skills` to `.agents/skills`:

- `inv ai.skills [--dir PATH]` — ensures `.agents/skills/` exists and `.claude/skills` is symlinked
  to it. Defaults to `~` (the personal, cross-project skills location); part of the standard
  `inv setup`/`inv wsl.install` chain.
- `inv ai.init [--dir PATH]` — full project scaffold: the skills symlink above, plus a minimal
  `AGENTS.md` and a `CLAUDE.md` shim, for any project on the machine (defaults to the current
  directory). Run it from this repo against another project, e.g. `inv ai.init --dir ~/projects/foo`.

Both tasks check for existing files/symlinks first and skip rather than overwrite — safe to re-run,
and safe to point at a project that already has hand-written `AGENTS.md`/`CLAUDE.md`/skills content.

## Slash commands

`[packages.node].global_packages` includes `skills` (an npm package installed globally via `nvm`),
which provides `npx skills add <owner>/<repo>` — installs Claude Code slash commands from a GitHub
repo. See `docs/js.md` for the general Node/nvm global-package mechanism.
