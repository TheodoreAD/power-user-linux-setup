# How it works

The mechanics behind `inv setup`: how PULSE writes shared config files without clobbering manual
edits, how `tags`/`enabled`/`PULSE_EXCLUDE_TAGS` decide what gets installed, and what each setup
phase actually runs. Start at [index.md](index.md) if you just want to run the thing — this page is
for when you need to change what it does, build a new environment profile, or debug why a package
was (or wasn't) picked up.

## Configuration management

PULSE owns config files through named sentinel blocks rather than overwriting whole files. Any
snippet written to a shared config file is wrapped in a PULSE block:

```
# ╔═══════════════════════════════ PULSE::<name> ════════════════════════════╗
...config content...
# ╚═══════════════════════════════ PULSE::<name> ════════════════════════════╝
```

78 characters wide, name centered, box-drawing corners. `╔`/`╗` open the block, `╚`/`╝` close it.
`<name>` is the `[packages.<name>]` key from `setup.toml`.

**Why:** config files like `~/.zshrc` or `/etc/sysctl.conf` are shared — multiple tools and the user
write to them. Overwriting the file on each run would destroy manual edits. Sentinels let each
PULSE-managed entry own its own region of the file independently.

**Idempotency:** on re-run the block is found by its opening marker and replaced in place if the
content changed, or left untouched if it matches. New blocks are appended. No duplicates, no drift.

### What PULSE claims in your home directory — `inv home.list-claims`

Blocks are one of ten ways this repo puts something in `~`. To see all of them:

```shell
inv home.list-claims                     # every claim, classified, read-only
inv home.list-claims --writer block      # just the marker-delimited regions
inv home.list-claims --tier machine      # what is true of this box only
inv home.list-claims --json              # the same, machine-readable
```

Each row says **how** the content got there (a whole-file deploy, declared in `setup.toml` or with a
destination decided at run time; a marker block; a merge into co-owned JSON; in-place surgery on one
key; a `gsettings`/`dconf` call; a symlink; an installed tree; a generated file; or a skill fetched
by the `skills` CLI), **who wins a conflict** (PULSE, you, both, or the application), and **where
the content lives today** (this public repo, this machine only, a secret, or regenerable state).

This is the command that answers "is this path PULSE-managed?" for the whole home directory.
`inv deploy.status` answers it only for the whole files declared in `setup.toml` — accurate about
its own registry, and misleading if read as the whole picture. The `state` column reflects that
split: a real deploy state wherever `deploy.py` is the writer, plain `present`/`absent` everywhere
else, because no other writer records what it wrote, and `—` for a claim with no file at all.

The table below is a curated guide to the files you are most likely to edit; the command is the
complete, generated answer.

### Managed files

| File                                                   | Managed by                                                  | Content                                                                                                                                                                                                                                           |
| ------------------------------------------------------ | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `~/.zshrc`                                             | `inv zsh.configure`                                         | completions, aliases, hooks — from `zshrc` fields in `setup.toml`                                                                                                                                                                                 |
| `~/.zshenv`                                            | `inv zsh.configure`                                         | environment variables, PATH — from `zshenv` fields in `setup.toml`                                                                                                                                                                                |
| `~/.zshenv` (separate `proxy` block)                   | `inv proxy.install`                                         | `http_proxy`/`https_proxy`/`no_proxy` pointed at the local Px daemon — written only once verified working, see [corporate-proxy.md](corporate-proxy.md)                                                                                           |
| `~/.zprofile`                                          | `inv zsh.configure`                                         | login-shell config — from `zprofile` fields in `setup.toml`                                                                                                                                                                                       |
| `~/.config/curlrc`                                     | `inv system.write-curlrc`                                   | curl defaults (silent, follow redirects)                                                                                                                                                                                                          |
| `/etc/sysctl.conf`                                     | `inv system.disable-ipv6`                                   | IPv6 disable keys                                                                                                                                                                                                                                 |
| `/etc/systemd/journald.conf.d/size.conf`               | `inv system.cap-journal-size`                               | `SystemMaxUse` drop-in                                                                                                                                                                                                                            |
| `/etc/apt/apt.conf.d/99-pulse`                         | `inv apt.configure`                                         | Disable dpkg progress bars                                                                                                                                                                                                                        |
| `~/.local/bin/askpass-zenity`                          | `inv tools.install`                                         | Zenity GUI askpass helper — enables `sudo -A` without a TTY                                                                                                                                                                                       |
| `~/AGENTS.md` (`~/.claude/CLAUDE.md` symlinks to it)   | `inv tools.install`                                         | Global agent instructions (use `sudo -A` for all sudo calls, Bash/allowlist discipline)                                                                                                                                                           |
| `~/.config/systemd/user/pulse-proxy.service`           | `inv proxy.fix`/`install`                                   | Whole file from `config/pulse-proxy.service` — runs the Px proxy daemon, see [corporate-proxy.md](corporate-proxy.md). Deployed through `deploy.py` but not declared in `setup.toml`: only a machine that configures a corporate proxy writes it. |
| `~/.config/px/px.ini`                                  | **not PULSE-managed** — owned entirely by Px's own `--save` | Upstream proxy address, bypass list, username. `inv proxy.*` never hand-authors this file's schema.                                                                                                                                               |
| `/usr/local/share/ca-certificates/pulse-corporate.crt` | `inv certs.install`                                         | Corporate CA bundle, auto-converted to PEM from whatever format IT provided — feeds `update-ca-certificates`, see [certs.md](certs.md)                                                                                                            |
| `~/.zshenv` (separate `certs` block)                   | `inv certs.install`                                         | `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`/`NODE_EXTRA_CA_CERTS`/`AWS_CA_BUNDLE`, pointed at the rebuilt system trust bundle — written only after `update-ca-certificates` succeeds, see [certs.md](certs.md)                                           |
| `~/.config/wezterm/wezterm.lua`                        | `inv deploy.all`                                            | Whole file, not a block — pane layout and keybindings, see [terminal.md](terminal.md). Written on install only if absent; redeployed on demand, see "Whole-file configs" below.                                                                   |
| `~/.config/terminator/config`                          | `inv deploy.all`                                            | Whole file, not a block — Terminator profile. Same install-once / redeploy-on-demand rules as above.                                                                                                                                              |

### Adding a new block

Declare `zshrc`, `zshenv`, or `zprofile` on any package entry in `setup.toml`:

```toml
[packages.mytool]
method = "apt"
zshrc = """
export MYTOOL_HOME="${HOME}/.local/share/mytool"
eval "$(mytool init zsh)"
"""
```

Run `inv zsh.configure` — the block is written on first run and updated in place on subsequent runs.
For non-shell config files, call `util.ensure_block(path, name, content)` or
`util.ensure_block_text(text, name, content)` (returns new text without writing, for files that
require `sudo`).

---

## Whole-file configs — `config_files`

Sentinel blocks only work for files PULSE _shares_ with other writers. Some config files aren't
shared at all: a tool's config is a single document PULSE authors end to end, in a syntax where a
`# ╔══ PULSE::name ══╗` comment would be noise (or invalid). WezTerm's Lua config is the clearest
case — the whole file is one Lua program returning one config table; there's no meaningful "PULSE's
region" of it.

For those, a package declares `config_files`: a list of `{ src, dst }` mappings copying a file from
this repo into place.

```toml
[packages.wezterm]
method = "deb-github"
config_files = [{ src = "config/wezterm.lua", dst = "~/.config/wezterm/wezterm.lua" }]
```

`src` is relative to the repo root, `dst` expands `~`. Any method can declare it.

### Install never clobbers; redeploy is a separate, deliberate command

The install tasks that apply `config_files` (`inv apt.install-base`, `inv apt.install-debs`) **only
ever write a destination that doesn't exist yet.** If the file is already there, they skip it
silently — because after the first install that file is yours, and a re-run of `inv setup` must
never throw away edits you made by hand.

The consequence surprises people: **editing `config/<file>` in this repo does not update the
deployed copy.** Re-running the install task won't do it either. That's what `inv deploy.all` is for
— the one redeploy command for everything this repo puts under `~` (`config_files` mappings,
`wrapper-script` `content_file`s such as `~/AGENTS.md`, and skills), with `inv deploy.status` as its
read-only twin:

```shell
inv deploy.status                      # what has drifted, with diffs; never writes
inv deploy.all                         # redeploy every declared path
inv deploy.all --name wezterm          # just one package's
inv deploy.all --name wezterm -y       # ...without the confirmation prompt
```

Per path it does one of four things, based on a machine-local manifest of what PULSE last wrote:

| State                          | What happens                                                              |
| ------------------------------ | ------------------------------------------------------------------------- |
| identical                      | reports `already matches`, writes nothing                                 |
| destination missing            | creates it, no prompt — nothing is being destroyed                        |
| unchanged since PULSE wrote it | updates it, no prompt — it still holds exactly what PULSE last put there  |
| edited at the destination      | prints a unified diff, then asks `Overwrite <path>? [y/N]` before writing |

A `config_files` destination is _seeded_ rather than owned — once installed it's yours — so a
customized one is left alone with a note, and only `-y` overwrites it. The prompt defaults to
**no**, and `-y`/`--yes` skips it (same shape as `apt`/`dnf`). Piped or non-interactive runs without
`-y` skip the overwrite rather than clobbering unattended. `PULSE_DRY_RUN=1` shows the diffs and
reports what it would do without touching anything.

The install tasks themselves (`inv tools.install` for `content_file`s, `apt.install-base`/
`install-debs` for `config_files`, `ai.install-skills` for skills) go through the same writer, so
they behave identically per path — they no longer overwrite a `content_file` destination
unconditionally, and no longer skip an existing `config_files` destination in silence. They have no
`--yes` of their own: `PULSE_ASSUME_YES=1` is the env-var equivalent, which
`bootstrap-devcontainer.sh` sets so an unattended container build overwrites (and says so) rather
than silently leaving a base-image file in place.

Sample run:

```console
$ inv deploy.all --name wezterm

[deploy] wezterm: /home/you/.config/wezterm/wezterm.lua was edited since PULSE deployed it — its repo-side source is config/wezterm.lua

  --- /home/you/.config/wezterm/wezterm.lua
  +++ config/wezterm.lua
  @@ -1,16 +1,43 @@
   local wezterm = require "wezterm"
  +local act = wezterm.action
   local mux = wezterm.mux
  ...

Overwrite /home/you/.config/wezterm/wezterm.lua? [y/N]
```

### Editing one of these files

Because the destination is a real, hand-editable file, there are two valid workflows — pick one per
change, don't mix them:

1. **Change it for good** — edit `config/<file>` in this repo, commit it, then
   `inv deploy.all --name <pkg>` to push it out. This is the right path for anything you want on the
   next machine too.
2. **Try something locally** — edit the deployed `~/...` file directly. Nothing will overwrite it
   until you explicitly run `inv deploy.all`, at which point the diff shows exactly what you'd be
   discarding (`inv deploy.status` shows the same diff without offering to write). Copy anything
   worth keeping back into `config/<file>` first.

Currently declared: [`config/wezterm.lua`](terminal.md) → `~/.config/wezterm/wezterm.lua`, and
`config/terminator.conf` → `~/.config/terminator/config`.

---

## Tags, `enabled`, and which tasks actually respect either

Every `[packages.*]` entry has three independent, unrelated ways to be skipped:

- **`enabled = false`** — the default for every machine that clones this repo, baked into
  `setup.toml`. Used for things that are evaluated-but-not-wanted (e.g. `freon`, superseded by
  `vitals`), opt-in extras (e.g. `glab`, `atuin`), machine-specific workarounds that would be wrong
  as a universal default (e.g. `google-chrome-x11`), and applications one person's work needs that
  nobody else's does (e.g. `telegram-desktop`).
- **`~/.config/power-user-linux-setup/overrides.toml`** — one machine's disagreement with that
  default, written in `setup.toml`'s own shape:

  ```toml
  [packages.google-chrome-x11]
  enabled = true
  ```

  Only `enabled` is honoured, and only for a package `setup.toml` already declares — every package
  _definition_ stays in git where it can be reviewed. The file is deliberately outside git and is
  not backed up by anything here: preserving a home directory is the user's own job. What this repo
  guarantees is the stability of its defaults, not of any one machine's customizations on top of
  them.
- **`tags = [...]` + `PULSE_EXCLUDE_TAGS`** — a runtime filter layered on top, for building
  environment-specific profiles (headless, container, WSL) without editing `setup.toml` per
  environment. See [index.md's Quick start](index.md#quick-start) for a live example.

Precedence is `setup.toml` → `overrides.toml` → `PULSE_EXCLUDE_TAGS`, environment last and absolute.
Tags describe _capability_ (no display server means a `gui` package genuinely cannot work); an
override describes _intent_. So a container that excluded `gui` still skips the package even on a
machine whose `overrides.toml` asked for it.

**Both are only checked by `util.packages_by_method(method)`** (`tasks/util.py`) — the dispatcher
every _generic_ install-method task loops over: `apt`, `apt-repo`, `deb-github`, `deb-url`,
`archive`, `uv-tool`, `script`, `binary`, `git-clone`, `wrapper-script`, `gnome-extension`,
`apparmor-profile`. An entry needs to pass **both** checks (`enabled != false` _and_ no tag in
`PULSE_EXCLUDE_TAGS`) to be picked up by any of these.

**Several core tasks bypass `packages_by_method` entirely.** Most read one hardcoded
`[packages.<name>]` section directly, and for those `enabled` and `tags` do nothing at all — the
only way to skip them is to not invoke the `inv` task. Bypassing `packages_by_method` is not by
itself the same as ignoring tags, though, so read the last column per row rather than the heading:

| Task                                | Reads directly                                                                   | Tag/enabled-aware?                                                                                                                                                                                                                                                                                                                                                    |
| ----------------------------------- | -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `node.install`                      | `packages["node"]`                                                               | No — always runs `[packages.node]` regardless of `enabled` or tags                                                                                                                                                                                                                                                                                                    |
| `docker.configure`                  | live `docker` command + `packages.docker`'s literal defaults                     | No — gated only by whether the `docker` binary exists on `$PATH`, plus a `dockerd` presence check: if `docker` exists without a local `dockerd` (e.g. Docker Desktop's WSL integration), it skips cleanly instead of failing on `systemctl restart docker`                                                                                                            |
| `fonts.install` / `fonts.configure` | `settings.fonts` (not `packages.*` at all)                                       | N/A — not a package entry, no tags possible                                                                                                                                                                                                                                                                                                                           |
| `zsh.configure`                     | `util.enabled_packages()` — every entry with a `zshrc`/`zshenv`/`zprofile` field | **Yes, both** (since 2026-09-01). It also _removes_ the block of a package that no longer applies, so switching a profile takes the old exports back out instead of leaving them behind — the marker-delimited region only, never anything hand-written around it. Before this it was `enabled`-only, which is how a GUI askpass export reached headless WSL distros. |

**`inv verify.all`** (`tasks/verify.py`, runs as the last step of `inv setup`'s `packages` phase —
see [dev-container.md](dev-container.md#automated-functional-verification-inv-verifyall)) sits in
neither bucket cleanly. For every method except `gnome-extension` it goes through
`packages_by_method()` like the generic install tasks, so it only checks what the current tag
profile actually installed. `gnome-extension` is force-skipped regardless of tags/enabled — no
automated path, not even `inv setup` itself, ever calls `inv gnome.install-extensions` (see
`tasks/gnome.py`), so checking those by default would fail `inv setup` for extensions it never
attempted to install. It also does a manual scan for `method = "zsh"` entries (`enabled`-only, tags
ignored), always skipping them since they're config-only with no command to verify — so the only
effect of its tag-blindness is that a tag-excluded entry is still named as skipped.

This split is exactly what [wsl.md](wsl.md) and [dev-container.md](dev-container.md) rely on — when
building a new environment profile, check which bucket the task you're skipping falls into before
assuming a tag exclusion is enough.

**A third bucket: tasks that don't read `setup.toml` at all.** `apt.clean-cache(-full)`,
`python.clean-cache(-full)`, `node.clean-cache(-full)`, `tools.clean-cache(-full)`,
`docker.clean(-full)`, and the `cleanup.*` umbrella tasks that depend on them operate on whatever's
actually on disk for that tool (apt's archive cache, `~/.cache/uv`, `~/.npm`, cargo's registry,
Docker images) — `enabled`/`tags` are irrelevant to them since there's no `[packages.*]` entry being
consulted in the first place. Excluding a tag stops something from being _installed_; it has no
bearing on whether that tool's cache-cleanup task has anything to do.

**Tag catalog** — only seven tags currently gate anything (used across the exclusion recipes in this
repo):

| Tag              | Excludes                                                                                                                                                                                                 |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `gui`            | Wayland/X11 apps, desktop tools, browsers                                                                                                                                                                |
| `desktop`        | Anything depending on a desktop session (e.g. Wayland clipboard)                                                                                                                                         |
| `gnome`          | Anything needing a _live GNOME Shell_, not just a display server: GNOME Shell extensions, `gnome-extensions-cli`, and GNOME-only `xdg-desktop-portal` backends (`xdg-desktop-portal-gnome`, `flameshot`) |
| `ide`            | Full IDEs and their support profiles (`vscode`, `jetbrains-toolbox`, `apparmor-jbr-cef`) — see [wsl.md](wsl.md) for when to exclude these in favor of a remote client                                    |
| `windows-native` | GUI apps with no Linux-specific reason to duplicate under WSL (`terminator`, `wezterm`, `freelens`, `font-manager`, `claude-desktop`, `edge`) — WSL-specific, see [wsl.md](wsl.md)                       |
| `workstation`    | Hardware sensors, local terminal multiplexer, Docker                                                                                                                                                     |
| `corporate`      | Webex, Citrix, and other work-specific tools                                                                                                                                                             |

The rest of the tags in `setup.toml` (`cli`, `dev`, `k8s`, `shell`, `vcs`, `search`, `modern`,
`legacy`, …) are purely organizational/searchable — categorization for humans reading the file, not
wired to any exclusion recipe. Don't assume a tag does something just because it exists; check
whether it's actually referenced in a documented `PULSE_EXCLUDE_TAGS` recipe (this file,
`dev-container.md`, `wsl.md`) or `setup.toml`'s header comment.

**`{version}` / `version_cmd` templating** — the `archive` and `deb-url` methods both support
resolving a dynamic version before downloading: set `version_cmd` to a shell command that prints the
version string, and include `{version}` in `download_url` (`archive`) or `url` (`deb-url`). See
`[packages.atuin]` (archive) or `[packages.glab]` (deb-url) for examples. `deb-github` resolves
version differently — via the GitHub releases API directly (`tag` field, or auto-latest if omitted)
— since it doesn't need a custom command.

---

## Setup phases

What `inv setup` actually runs, in order. One interruption: a single logout at the end. An optional
reboot can follow if GRUB or initramfs were changed, but it can also wait for the next natural
reboot — nothing depends on it being immediate.

Under WSL, `inv setup` detects it (`util.is_wsl()`) and delegates straight to `inv wsl.install`
instead of the phases below — different tag exclusions, DNS handling, and it skips
`docker.configure`/`fonts.*` by default. See [wsl.md](wsl.md) for what that runs instead.

In a container or any other environment with no systemd and not WSL, `inv setup` detects that too
(`util.has_systemd()`) and skips Phase 1 and Phase 4 below entirely — `system.set-locale`/
`system.configure-dns` need `systemctl`/`localectl`, and fonts have no meaning in a headless
container. Phases 2 and 3 run as normal. See [dev-container.md](dev-container.md) for the tested
Dockerfile.

Each phase below is a group of task calls run through `tasks/phases.py`'s `run()` helper, which
prints a labeled banner naming the phase before it starts. Before running for real, it probes the
phase with `util.DRY_RUN` forced on (every task's dry-run branch is already a side-effect-free local
check — see each task module) and, if nothing comes back `MISSING`, asks whether to skip the phase
entirely — defaulting to **skip** on Enter, and skipping silently in non-interactive runs. This is
what makes re-running `inv setup` (or `inv wsl.install`) after an interruption cheap: phases that
already succeeded are a single confirmation instead of a full redo. A phase with any outstanding
work is never gated behind a prompt — it just runs, same as before.

### Phase 1 — System config

All of these take effect immediately (sysctl, DNS, journald restart) or on next login (locale). No
reboot needed.

```shell
inv system.set-locale
inv system.write-curlrc
inv system.configure-dns
inv system.disable-ipv6          # optional — sysctl -p applies immediately
inv system.cap-journal-size          # optional — restarts journald
inv system.set-initramfs-compression # optional — deferred to next reboot
```

GRUB (`nomodeset`) is manual and hardware-specific — see [troubleshooting.md](troubleshooting.md).
If applied, it also defers to next reboot.

### Phase 2 — Packages and tools

```shell
inv apt.configure      # write /etc/apt/apt.conf.d/99-pulse (disables dpkg progress bars)
inv apt.install-repos          # register external repo GPG keys + sources, then install their packages
inv apt.install-base           # install from Ubuntu default repos
inv docker.configure   # merge log limits/DNS into daemon.json, add user to docker group
inv apt.install-debs            # install .deb packages from GitHub releases or direct URLs
inv tools.install      # install tools via scripts, binaries, archives; also writes askpass-zenity
inv ai.install-skills          # symlink ~/.claude/skills to ~/.agents/skills — see ai.md
inv system.install-apparmor-profiles
inv python.install-tools
inv node.install
```

`inv apt.configure` writes a drop-in that suppresses dpkg's progress bar output — run it once before
any other apt tasks.

`inv apt.install-repos` is a two-phase command: Phase 1 registers all GPG keys and sources files,
then runs `apt update` once; Phase 2 installs the packages. The two phases are bundled because the
packages can't be installed without the repo. If a GPG key URL or sources write fails, that repo is
skipped with a `WARNING:` message rather than aborting the whole run.

After `inv tools.install` + `inv zsh.configure`, all new shell sessions have `SUDO_ASKPASS` set to
`~/.local/bin/askpass-zenity`. Any sudo call via `sudo -A` (used by the task scripts when
`SUDO_ASKPASS` is present) opens a Zenity GUI dialog for the password instead of requiring a
terminal prompt.

### Phase 3 — Shell config

```shell
inv zsh.configure-omz
inv zsh.configure
inv zsh.configure-p10k       # seeds config/p10k.zsh to ~/.p10k.zsh (yours once it exists)
inv zsh.set-default-shell    # usermod -s — takes a new terminal to actually apply, doesn't chsh
```

`zsh.configure-p10k` installs the repo's opinionated baseline (lean style, Nerd Fonts icons,
transient prompt, instant prompt). It is a `config_files` mapping on `[packages.powerlevel10k]`, so
it goes through the same writer as every other whole file: a customized `~/.p10k.zsh` is reported
and left alone, never overwritten, and `inv deploy.status --path ~/.p10k.zsh` will show you the diff
against the repo baseline.

To redo or fix the prompt: run `p10k configure` for the interactive wizard, or
`inv deploy.all --name powerlevel10k --yes` to overwrite your copy with the repo baseline. To update
the baseline itself, copy your `~/.p10k.zsh` to `config/p10k.zsh`.

`zsh.set-default-shell` uses `usermod -s`, not `chsh` — `chsh`'s PAM password prompt doesn't work
non-interactively the way `sudo -A` does. It's a no-op if the login shell is already some zsh
(matched by binary name, not exact path — a machine can have more than one zsh on disk). Takes a
brand new terminal/login session to actually apply, not just a new tab in an already-open shell.

Phases 1–3 run automatically via `inv setup`. It finishes by calling `next_steps.print_next_steps()`
(`tasks/next_steps.py` — separate from `tasks/util.py` since it needs to check `git`/`ssh` state,
and both of those import `util`), which checks real state rather than a stored "already told you"
flag and prints the single next concrete thing to do: shell first, then
`~/.config/power-user-linux-setup/identity.toml`, then walks Phase 5 below one command at a time —
git settings/profiles applied? SSH keys present for every `identity.toml` email? `~/.ssh/config`
written? keys loaded in the agent? `gh` authenticated (only checked if `gh` is installed)? Safe to
re-run after doing whatever it suggests — it just reports whatever's still outstanding.

### Phase 4 — Desktop _(before logout)_

`inv setup` also runs `fonts.install` and `fonts.configure`, which:

- Download all Nerd Font families to `~/.local/share/fonts/`
- Set **CaskaydiaCove Nerd Font Mono 12** as the system monospace, GNOME Terminal profile font, VS
  Code editor and terminal font, and Terminator terminal font

GNOME extensions require manual installation — see [gnome_extensions.md](gnome_extensions.md).

> **Logout and log back in.** Covers: docker group, locale full effect, GNOME extension activation,
> font cache. If GRUB or initramfs were changed, reboot instead of logout — one restart covers both.

### Phase 5 — Authentication _(interactive, last)_

```shell
inv identity.init                # wizard: writes ~/.config/power-user-linux-setup/identity.toml (simple or advanced)
inv git.configure git.apply-settings   # per-directory git identity + global settings from identity.toml
inv ssh.create-keys                     # one ed25519 key per unique email — prompts for a passphrase each
inv ssh.configure                # write ~/.ssh/config
inv ssh.add                      # load this node's keys into ssh-agent
gh auth login                    # GitHub CLI — opens browser, not automatable
```

Everything after `inv identity.init` (except `gh auth login`) needs
`~/.config/power-user-linux-setup/identity.toml` filled in first — either via the wizard above
(simple: one identity, one projects directory, `~/projects/` itself by default) or by hand for
multiple directories/accounts, see [git.md](git.md) and [ssh.md](ssh.md).
`next_steps.print_next_steps()` (above) guides you through this exact sequence, one command at a
time, once identity.toml exists.

For gcloud: see [gcloud.md](gcloud.md).
