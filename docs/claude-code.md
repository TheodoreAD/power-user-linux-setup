# Claude Code environment

What this repo does specifically to make [Claude Code](https://claude.ai/code) (the CLI agent) work
smoothly on this machine — as opposed to `docs/ai.md`, which covers AI tools generally (install,
model choice, other agents).

## The core problem: no TTY

Claude Code's Bash tool runs commands non-interactively — there's no controlling terminal, so
anything that tries to prompt interactively (a `sudo` password, an SSH key passphrase) just fails
outright instead of waiting for input. Two independent instances of this are solved the same way:

## askpass-zenity — GUI dialog instead of a TTY prompt

`[packages.askpass-zenity]` in `setup.toml` writes `~/.local/bin/askpass-zenity`, a script that pops
a Zenity GUI password dialog and prints whatever was entered to stdout — the standard `*_ASKPASS`
program contract. It's wired up for two separate purposes:

```shell
export SUDO_ASKPASS="${HOME}/.local/bin/askpass-zenity"
export SSH_ASKPASS="${HOME}/.local/bin/askpass-zenity"
export SSH_ASKPASS_REQUIRE="prefer"
```

**sudo** — use `sudo -A` (not plain `sudo`) for every sudo call from Claude Code. `-A` tells sudo to
use `$SUDO_ASKPASS` instead of prompting on a TTY that doesn't exist. Plain `sudo` fails with
`sudo: a terminal is required`.

**git over SSH** — `SSH_ASKPASS` + `SSH_ASKPASS_REQUIRE=prefer` fixes a related but separate
failure: this machine's SSH keys are passphrase-protected and managed by `keychain` (see
[ssh.md](ssh.md#keychain-persistent-agent-across-logins)), which loads a key into the agent
_lazily_, the first time it's actually used each session (`AddKeysToAgent yes` in `~/.ssh/config`).
If Claude Code runs the first `git fetch`/`git push` of the day before anything else has triggered
that lazy load, `ssh` needs the passphrase to unlock the key — and with no TTY, that fails as
`Permission denied (publickey)`, indistinguishable from an actual auth problem. `SSH_ASKPASS` makes
`ssh` pop the same Zenity dialog for the passphrase instead of failing. **No HTTPS/token workaround
is needed — just run `git fetch`/`git push` normally.**

`SSH_ASKPASS_REQUIRE=prefer`, deliberately not `force`: `force` would hijack passphrase prompts in a
normal interactive terminal too (popping a GUI dialog even when you're sitting at a real shell that
could just prompt you inline) — a regression to the normal workflow. `prefer` only engages the GUI
dialog when there's no usable TTY, which is exactly the Bash-tool case; an interactive terminal
session is unaffected.

The dialog blocks on user input — if nobody's at the machine to enter the passphrase, the git
command times out rather than hanging forever.

The askpass script itself shows the caller's actual prompt (`$1` — sudo passes something like
`[sudo] password for user:`, ssh passes `Enter passphrase for key '...':`) instead of a hardcoded
string, so the dialog text is accurate regardless of which one triggered it.

## direnv auto-activation in the Bash tool — `inv agents.wire-claude-hook`

A second consequence of the Bash tool's execution model (see "The core problem: no TTY" above),
separate from the askpass issue: direnv (`[packages.direnv]`, e.g. a project's `.envrc` activating
its Python `.venv`) doesn't auto-activate for Claude Code's Bash tool the way it does in a real
terminal, even after `direnv allow`. Two things stack:

1. Each Bash tool call runs as `zsh -c 'source <captured-shell-snapshot> && ... && eval "<cmd>"'`.
   direnv's normal hook (`eval "$(direnv hook zsh)"` in `~/.zshrc`, from `[packages.direnv]`) fires
   on `precmd` — a real interactive prompt cycle — which never happens in this non-interactive,
   one-shot `zsh -c`. Writing the export to `~/.zshenv` instead doesn't help either: `.zshenv` _is_
   sourced unconditionally, but the snapshot sourced right after it carries its own hardcoded
   `export PATH=...` (captured from whatever shell state existed when the snapshot was taken), which
   clobbers it before the real command runs.
2. Separately, this environment can carry stale `DIRENV_DIR`/`DIRENV_WATCHES` inherited from before
   `direnv allow` was ever run (e.g. baked into a GUI app's launch environment), which makes
   `direnv export` silently no-op even when invoked correctly — `unset`ting those first forces a
   correct recompute.

The fix uses `CLAUDE_ENV_FILE` (a Claude Code environment variable naming a file it sources before
each Bash command — its documented purpose is exactly this: persisting environment changes across
tool calls) paired with a `PreToolUse` hook on the Bash tool that keeps that file fresh from
`direnv export zsh` before every single call, so `cd`/`.envrc` changes are picked up too, not just
whatever was true at session start.

`inv agents.wire-claude-hook [--dir PATH]` (from the
[`repo-tasks`](https://github.com/TheodoreAD/repo-tasks) dev dependency — see `pyproject.toml`)
writes this into `<dir>/.claude/settings.json`:

```json
{
  "env": { "CLAUDE_ENV_FILE": "~/.cache/claude-code/<sanitized-abs-path>-direnv-env" },
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "unset DIRENV_DIR DIRENV_WATCHES DIRENV_DIFF DIRENV_FILE; direnv export zsh > <that file> 2>/dev/null || true"
      }]
    }]
  }
}
```

The env-file path is derived the same way Claude Code's own auto-memory directory is
(`~/.claude/projects/<sanitized-cwd>/memory/`) — the repo's absolute path with `/` → `-` — so two
repos sharing a basename never collide. No-ops if `<dir>/.envrc` doesn't exist (nothing to
activate), and merges into an existing `settings.json` (appending to a `Bash` `PreToolUse` group if
one already exists, adding one if not) rather than overwriting, so hand-written hooks survive a
re-run. `dev-env.setup` calls it for this repo's own `.venv` automatically; run it directly against
any other project — `inv agents.wire-claude-hook --dir ~/projects/foo` — to set the same thing up
there.

Caveat: `env` values in `settings.json` are only read at Claude Code process launch, unlike hooks,
which are read fresh per call — so this needs a session restart (or VS Code window reload) to take
effect after first being configured, even though the hook itself starts firing immediately.

## Installing the CLI

`[packages.claude-code]` installs the `claude` binary itself via `inv tools.install`, using
Anthropic's native installer (`curl -fsSL https://claude.ai/install.sh | bash`) — a `script`-method
entry, same as Oh My Zsh. This is the officially recommended method: it needs no Node.js, ships a
signed per-platform binary, and auto-updates itself in the background (`~/.local/bin/claude`
symlinked into `~/.local/share/claude/versions/`). Don't use
`npm install -g @anthropic-ai/claude-code` for a fresh install on this machine — it still works but
is the legacy path; PULSE only needs to `curl`-install once and then leaves auto-update to Claude
Code itself.

## `~/AGENTS.md` — global instructions, declaratively managed

`[packages.agents-md]` writes `~/AGENTS.md` (the cross-tool, cross-project instructions file every
agent CLI on this machine can read) from `setup.toml`, and symlinks
`~/.claude/CLAUDE.md -> ~/AGENTS.md` via the `wrapper-script` method's `symlink_dest` field — the
exact same real-content-plus-symlink pattern this repo's own root uses for its `AGENTS.md`/
`CLAUDE.md` pair. The sudo/ssh guidance above, plus Bash/allowlist discipline, lives there in
agent-readable form, so every session on this machine picks it up automatically without needing to
rediscover it.

**The file is assembled, not copied.** `[packages.agents-md]` sets `assembled_from = "agents_md"`,
and every package declaring an `agents_md` fragment contributes whole `##` sections to the result,
ordered by a sparse `order` — the same any-section pattern as `zshrc`/`zshenv`, for a file where
section order carries meaning. Today three fragments split the content by audience:
`config/agents-md/this-setup.md` (facts true only of this machine and this user's repos),
`claude-code.md` (one harness's own behavior), and `portable.md` (conventions that hold anywhere).
Which one owns what, and why the split exists, is `config/agents-md/README.md`.

Edit the fragment that owns the rule, then `inv deploy.all --name agents-md`, rather than
hand-editing `~/AGENTS.md` directly — the file is fully PULSE-owned (same as any
`wrapper-script`-method entry) and regenerated end to end, so the `<!-- PULSE::agents-md/… -->`
markers in it are provenance, not an ownership boundary: nothing outside a block survives either.
Both `deploy.all` and the install-time writer in `inv tools.install` go through the same deploy
writer, so an edit made to `~/AGENTS.md` directly is shown as a diff and asked about (default: keep
it) rather than silently overwritten — but it still only lives on this machine until it's ported
into a fragment. `~/.claude/CLAUDE.md` itself is never touched once it's a correct symlink; if
something other than that symlink already lives there, `inv tools.install` warns and leaves it alone
rather than overwriting it.

Several conventions live there too, deliberately global rather than repeated per-repo — see
`config/agents-md/portable.md` for the exact wording:

- **`CLAUDE.md` is only ever a symlink.** Any repo that wants agent instructions should have a real
  `AGENTS.md` (the cross-tool standard 30+ agent CLIs read) and, if `CLAUDE.md` exists at all, it's
  a plain symlink to `AGENTS.md` — not a file containing Claude Code's `@AGENTS.md` import
  directive. The import syntax is Claude-Code-specific; a symlink presents byte-identical content to
  every harness that reads a literal `CLAUDE.md`, no special-case parsing needed. Trade-off: nothing
  can be appended below a symlink's target, so a genuinely Claude-specific addendum belongs in
  `AGENTS.md` itself instead. Both this repo's own root (`AGENTS.md` real,
  `CLAUDE.md ->
  AGENTS.md`) and `~` itself (`AGENTS.md` real,
  `~/.claude/CLAUDE.md -> ~/AGENTS.md`) follow it.
- **Cross-session memory policy.** Durable, repo-specific knowledge belongs in that repo's
  `AGENTS.md`, not Claude Code's auto-memory system (`~/.claude/projects/.../memory/`) — memory is
  invisible to every other contributor, every other agent tool, and every code review; `AGENTS.md`
  is version-controlled and visible to all three.
- **Bash tool / CLI allowlist discipline.** Don't `cd` out of a project — the Bash tool's cwd is
  already the project root, so just run plain commands, and don't reach for a directory-scoping flag
  (`git -C`, `npm --prefix`, etc.) as a substitute either, since for subcommand-tree tools that
  breaks the allow-rule match the same way `cd &&` does. Also prefer several simple, separate Bash
  calls over one chained/piped/env-prefixed command. Both come from the same mechanism:
  `inv allowlist.*` (see [`cli-allowlist.md`](cli-allowlist.md)) generates permission rules that
  match on a literal command _prefix_, and a `cd x && cmd`/`cmd1 && cmd2`-style compound string
  can't match a prefix rule that was written for the plain command alone — so it prompts every time
  even when every individual piece is already allowlisted.

## `~/.claude/settings.json` — permissions merged in by `inv allowlist.apply`

Unlike `~/.claude/CLAUDE.md` above, `~/.claude/settings.json` is _not_ fully PULSE-owned — it's a
partial merge. `inv allowlist.apply` (see [`cli-allowlist.md`](cli-allowlist.md) for the full
pipeline this is the last step of) rewrites only the `permissions.allow`/`permissions.ask` arrays,
tracking what it wrote via a local manifest so it never touches a rule you added by hand, or any
other key in the file (`theme`, `effortLevel`, `cleanupPeriodDays`, ...). `cleanupPeriodDays`
specifically — governs how long session transcripts/tasks/shell-snapshots/backups are kept — is set
to `365` here (default is `30`) as a deliberate preference, reviewed and confirmed while building
the allowlist pipeline, not something PULSE enforces or will change on your behalf.

## `.agents/skills/` — `inv ai.install-skills`

`.agents/skills/` is the emerging cross-tool convention for Agent Skills, but Claude Code itself
currently only discovers skills from `~/.claude/skills/` and `<project>/.claude/skills/` — not
`.agents/skills/` directly. To get both the cross-tool convention _and_ a working Claude Code setup,
PULSE symlinks `.claude/skills` to `.agents/skills`:

- `inv ai.install-skills [--dir PATH]` — ensures `.agents/skills/` exists and `.claude/skills` is
  symlinked to it, then installs every skill declared via a `skills` field anywhere in `setup.toml`
  (see below). Defaults to `~` (the personal, cross-project skills location); part of the standard
  `inv setup`/`inv wsl.install` chain.

Checks for existing files/symlinks first and skips rather than overwrites — safe to re-run, and safe
to point at a project that already has hand-written skills content. A new Python project's own
`AGENTS.md`/`CLAUDE.md`/`.agents/skills`/`.claude/skills` scaffold isn't this task's job —
[`scaffoldapy`](https://github.com/TheodoreAD/scaffoldapy) stamps that at generation time instead.

## Declaring skills to install — the `skills` field

Any `setup.toml` package entry can carry a `skills` list, checked by `inv ai.install-skills`
regardless of that entry's own `method` — same any-section pattern as `zshenv`/`zshrc`/`zprofile`.
Two sources:

- **`{ source = "local", path = "skills/<name>" }`** — for skills authored _in this repo_. Real
  skill directories (a `SKILL.md`, plus whatever else the skill needs — scripts, references, assets)
  live under `skills/` at the repo root, tracked by git like any other repo content — not tucked
  away as untracked research material, and not nested under this repo's own `.agents/skills/`
  (that's the _deployed_, tool-agnostic location on a given machine; this repo is where some skills
  happen to be authored, not where they run from). `inv ai.install-skills` **copies** the repo's
  `skills/<name>/` to `~/.agents/skills/<name>` — a real, standalone copy, not a symlink, matching
  how the `npx` source below behaves (it copies too). A `.pulse-source` marker file inside the copy
  records which entry installed it, so a re-run can tell "ours, safe to refresh to match the repo"
  apart from "something else is already here, leave it alone" — editing the repo copy needs an
  `inv ai.install-skills` re-run to take effect, it doesn't apply instantly the way a symlink would.
  `[packages.research-library]` is the example: its `skills` field points at
  `skills/research-library/`, which documents `$RESEARCH_HOME` (see
  `contributing/research-library.md`).
- **`{ source = "npx", repo = "<owner>/<repo>", names = [...], agents = [...] }`** — for skills
  published on GitHub. Installed via the real `skills` CLI (`[packages.node].global_packages`,
  [skills.sh](https://skills.sh)):
  `skills add <repo> --global --skill <names...> --agent
  <agents...> --yes`. `names` omitted
  installs every skill the repo has; `agents` defaults to `["claude-code"]` — this repo doesn't
  manage other agents' skill directories, and since `.claude/skills` is already symlinked to
  `.agents/skills`, targeting `claude-code` lands in the same shared directory the `local` source
  uses, not a separate copy. The CLI prints its own security-risk assessment (Socket/Snyk-style) per
  skill at install time — worth actually reading before adding an entry, since an installed skill
  runs with full agent permissions, same trust level as any other content read into an agent
  session.

Add a skill to install without attaching it to some other tool's entry by giving it its own
`[packages.<name>]` block with `method = "skill"` and nothing else but `skills`.

**Caveat found live (2026-08-23): don't run `inv ai.install-skills` from an agent session (or any
other non-interactive context) if you only need the permissions/statusline side effects.** The
npx-source install confirmation (`_install_remote_skill`'s `ui.ask(...)`) defaults to **proceed**,
not skip, when `not yes` — unlike the statusline-overwrite prompt above, which defaults to decline.
Per "The core problem: no TTY" up top, an agent's Bash tool is always non-interactive, so `ui.ask()`
always returns that default with no real prompt ever shown. Running the full `skills` task from
inside an agent session would therefore silently install every declared-but-not-yet-installed
npx-source skill with no approval gate at all — exactly the scenario this doc's own
security-risk-assessment paragraph above assumes a human is present to read. To apply just a new
`claude_permissions_allow` rule or statusline change without touching skill installation, call
`tasks.ai._apply_static_claude_permissions()` (or `_apply_declared_statusline()`) directly instead
of the `skills` task.

The `npx` source was validated end-to-end against a real package
([caveman](https://github.com/JuliusBrussee/caveman), an ultra-compressed communication-style skill)
before being trusted for `research-library`'s own `local` source — but caveman itself ended up
living in `~/AGENTS.md` instead (see "Caveman-style terse output" in
`config/agents-md/portable.md`), not as an installed skill: a skill only reaches Claude Code, and
the simpler, always-on AGENTS.md version covers every agent tool on this machine for less overall
complexity than keeping both. `contributing/research-library.md` has the fuller review notes.

## Declaring static permission rules — the `claude_permissions_allow` field

A second any-section field, same pattern as `skills`: any package entry can carry
`claude_permissions_allow`, a list of literal Claude Code permission-rule strings, checked
regardless of that entry's `method`. `inv ai.install-skills` merges every declared rule into
`~/.claude/settings.json`'s `permissions.allow` — same safe-merge shape as `tasks/allowlist.py`'s
`apply` (every other key untouched, `.json.bak` written before any real change, only rule strings
this mechanism wrote previously are ever removed) but through its own, separate manifest
(`~/.local/state/power-user-linux-setup/claude-static-permissions-applied.json`) — **deliberately
not routed through the CLI-allowlist pipeline** (see [`cli-allowlist.md`](cli-allowlist.md)): that
pipeline exists specifically to classify CLI tool risk from `--help` output, and these are static,
hand-declared rules with nothing to classify. Keeping the manifests separate means neither mechanism
can ever remove a rule the other one owns, even though both write to the same file.

`[packages.research-library]` is the example: `Read`/`Glob`/`Grep` allowed, unprompted, for
everything under `$RESEARCH_HOME` — deliberately treating that curated, read-only library like
project files rather than gating every lookup, which is the entire point of building a shared
library instead of fetching things ad hoc.

**GitHub Copilot, if present, gets checked but not written to.** `inv ai.install-skills` looks for a
`github.copilot-*` VS Code extension and, if found, prints a note rather than guessing: research
turned up `chat.tools.terminal.autoApprove` (terminal commands — already handled by
`inv allowlist.render --target=copilot`) and `chat.tools.urls.autoApprove` (URL fetches), but no
confirmed, documented Copilot setting for path-scoped _file-read_ auto-approval the way Claude's
`Read(pattern)` rules work — only a global, all-or-nothing
`github.copilot.chat.agent.autoApproveFileChanges` boolean, which governs edits, not reads, and
isn't scopable to one directory. Shipping a guessed key into a real settings.json seemed worse than
an honest "nothing applied, here's why." Revisit if a scoped-read key is ever confirmed.

## Declaring the permission mode and scratch directories — `claude_default_mode`, `claude_additional_directories`

Two more `settings.json` keys `inv ai.install-skills` syncs, both declared on
`[packages.claude-code]` (the mode is a single scalar read directly, like `claude_statusline`; the
directories are an any-section list merged through their own manifest,
`~/.local/state/power-user-linux-setup/claude-additional-directories-applied.json`, like
`claude_permissions_allow`):

- `claude_default_mode = "acceptEdits"` → `permissions.defaultMode`. Absent → set; matches → no-op;
  a different explicit value → ask before replacing (declines by default). This machine's permission
  setup is built for `acceptEdits`, where the allow/ask rules decide and anything unmatched that
  isn't read-only prompts; `auto` mode replaces that with a classifier and, on top, instructs the
  agent to prefer `cat`/`sed`/heredocs over the Read/Edit tools — the opposite of `~/AGENTS.md`. The
  audit that settled this (3,956 Bash calls over four days, per-model chaining and truncation rates,
  the `git -C` ask-rule bypass) and the mode comparison are in the `session-bash-audit` skill's
  `references/research.md`; re-run the skill to re-measure.
- `claude_additional_directories = ["/tmp/claude-1000", "~/.claude/jobs"]` →
  `permissions.additionalDirectories`, `~` expanded. The harness's own scratch locations — the
  per-session scratchpad and background-job tmp — are outside every repo, so under `acceptEdits`
  every write there would prompt. Entries from a settings file grant file access only; nothing
  (`CLAUDE.md`, skills, hooks) loads from them, unlike `--add-dir`.

Read `cli-allowlist.md`'s `mode_covered` section for the matching change on the rules side: the
filesystem commands `acceptEdits` gates by path (`mkdir`, `cp`, `rm`, ...) no longer render as `ask`
rules, because an explicit `ask` rule would beat the mode's in-scope grant.

## Declaring the statusline — the `claude_statusline` field

`[packages.claude-statusline]` deploys the custom Claude Code statusline script
(`config/statusline-command.sh` → `~/.claude/statusline-command.sh`, a `wrapper-script`-method
entry, chmod 0o755 — same mechanism as `agents-md`/`pulse-proxy-start`) and declares
`claude_statusline = { type = "command", command = "bash ~/.claude/statusline-command.sh" }` on that
same package entry. `inv ai.install-skills` reads that value directly (not a scanned any-package
field like `claude_permissions_allow` above — there's only ever one statusline, so no merge/manifest
mechanism is needed) and syncs it into `~/.claude/settings.json`'s top-level `statusLine` key:
absent → set it; already correct → no-op; set to something else → ask before overwriting (declines
by default, same `ui.ask` convention used elsewhere, auto-skipped non-interactively).

Edit `config/statusline-command.sh` and re-run `inv tools.install` to change the script's behavior —
its own header comment documents the color palette, icon sources (powerlevel10k's nerdfont icon
table), and threshold rationale in full; this doc only covers how it's _deployed_.
