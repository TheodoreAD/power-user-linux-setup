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

## `~/AGENTS.md` — global instructions, declaratively managed

`[packages.claude-global-md]` writes `~/AGENTS.md` (the cross-tool, cross-project instructions
file every agent CLI on this machine can read) from `setup.toml`, and symlinks
`~/.claude/CLAUDE.md -> ~/AGENTS.md` via the `wrapper-script` method's `symlink_dest` field — the
exact same real-content-plus-symlink pattern this repo's own root uses for its `AGENTS.md`/
`CLAUDE.md` pair. The sudo/ssh guidance above, plus Bash/allowlist discipline, lives there in
agent-readable form, so every session on this machine picks it up automatically without needing to
rediscover it. Edit the `content` field in `setup.toml`, then `inv tools.install`, rather than
hand-editing `~/AGENTS.md` directly — a manual edit gets silently overwritten on the next
`inv tools.install` run since the file is treated as fully PULSE-owned (same as any
`wrapper-script`-method entry). `~/.claude/CLAUDE.md` itself is never touched once it's a correct
symlink; if something other than that symlink already lives there, `inv tools.install` warns and
leaves it alone rather than overwriting it.

Several conventions live there too, deliberately global rather than repeated per-repo — see the
`content` field for the exact wording:

- **`CLAUDE.md` is only ever a symlink.** Any repo that wants agent instructions should have a real
  `AGENTS.md` (the cross-tool standard 30+ agent CLIs read) and, if `CLAUDE.md` exists at all, it's
  a plain symlink to `AGENTS.md` — not a file containing Claude Code's `@AGENTS.md` import
  directive. The import syntax is Claude-Code-specific; a symlink presents byte-identical content
  to every harness that reads a literal `CLAUDE.md`, no special-case parsing needed. Trade-off:
  nothing can be appended below a symlink's target, so a genuinely Claude-specific addendum belongs
  in `AGENTS.md` itself instead. Both this repo's own root (`AGENTS.md` real, `CLAUDE.md ->
  AGENTS.md`) and `~` itself (`AGENTS.md` real, `~/.claude/CLAUDE.md -> ~/AGENTS.md`) follow it.
- **Cross-session memory policy.** Durable, repo-specific knowledge belongs in that repo's
  `AGENTS.md`, not Claude Code's auto-memory system (`~/.claude/projects/.../memory/`) — memory is
  invisible to every other contributor, every other agent tool, and every code review; `AGENTS.md`
  is version-controlled and visible to all three.
- **Bash tool / CLI allowlist discipline.** Don't `cd` out of a project — the Bash tool's cwd is
  already the project root, so just run plain commands, and don't reach for a directory-scoping
  flag (`git -C`, `npm --prefix`, etc.) as a substitute either, since for subcommand-tree tools
  that breaks the allow-rule match the same way `cd &&` does. Also prefer several simple, separate
  Bash calls over one chained/piped/env-prefixed command. Both come from the same mechanism: `inv allowlist.*`
  (see [`cli-allowlist.md`](cli-allowlist.md)) generates permission rules that match on a literal
  command *prefix*, and a `cd x && cmd`/`cmd1 && cmd2`-style compound string can't match a prefix
  rule that was written for the plain command alone — so it prompts every time even when every
  individual piece is already allowlisted.

## `~/.claude/settings.json` — permissions merged in by `inv allowlist.apply`

Unlike `~/.claude/CLAUDE.md` above, `~/.claude/settings.json` is *not* fully PULSE-owned — it's a
partial merge. `inv allowlist.apply` (see [`cli-allowlist.md`](cli-allowlist.md) for the full
pipeline this is the last step of) rewrites only the `permissions.allow`/`permissions.ask` arrays,
tracking what it wrote via a local manifest so it never touches a rule you added by hand, or any
other key in the file (`theme`, `effortLevel`, `cleanupPeriodDays`, ...). `cleanupPeriodDays`
specifically — governs how long session transcripts/tasks/shell-snapshots/backups are kept — is
set to `365` here (default is `30`) as a deliberate preference, reviewed and confirmed while
building the allowlist pipeline, not something PULSE enforces or will change on your behalf.

## `.agents/skills/` and project scaffolding — `tasks/ai.py`

`.agents/skills/` is the emerging cross-tool convention for Agent Skills, but Claude Code itself
currently only discovers skills from `~/.claude/skills/` and `<project>/.claude/skills/` — not
`.agents/skills/` directly. To get both the cross-tool convention *and* a working Claude Code setup,
PULSE symlinks `.claude/skills` to `.agents/skills`:

- `inv ai.skills [--dir PATH]` — ensures `.agents/skills/` exists and `.claude/skills` is symlinked
  to it. Defaults to `~` (the personal, cross-project skills location); part of the standard
  `inv setup`/`inv wsl.install` chain.
- `inv ai.init [--dir PATH]` — full project scaffold: the skills symlink above, plus a minimal
  `AGENTS.md` and a `CLAUDE.md` symlinked to it, for any project on the machine (defaults to the
  current directory). Run it from this repo against another project, e.g.
  `inv ai.init --dir ~/projects/foo`.

Both tasks check for existing files/symlinks first and skip rather than overwrite — safe to re-run,
and safe to point at a project that already has hand-written `AGENTS.md`/`CLAUDE.md`/skills content.

## Slash commands

`[packages.node].global_packages` includes `skills` (an npm package installed globally via `nvm`),
which provides `npx skills add <owner>/<repo>` — installs Claude Code slash commands from a GitHub
repo. See `docs/js.md` for the general Node/nvm global-package mechanism.
