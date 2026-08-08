# PULSE — Power User Linux Setup

**PULSE** (Power User Linux Setup) is an opinionated, reproducible workstation setup for Ubuntu 24.04, driven by a single `setup.toml` and [`invoke`](https://www.pyinvoke.org/) tasks.

## Configuration management

PULSE owns config files through named sentinel blocks rather than overwriting whole files. Any snippet written to a shared config file is wrapped in a PULSE block:

```
# ╔═══════════════════════════════ PULSE::<name> ════════════════════════════╗
...config content...
# ╚═══════════════════════════════ PULSE::<name> ════════════════════════════╝
```

78 characters wide, name centered, box-drawing corners. `╔`/`╗` open the block, `╚`/`╝` close it. `<name>` is the `[packages.<name>]` key from `setup.toml`.

**Why:** config files like `~/.zshrc` or `/etc/sysctl.conf` are shared — multiple tools and the user write to them. Overwriting the file on each run would destroy manual edits. Sentinels let each PULSE-managed entry own its own region of the file independently.

**Idempotency:** on re-run the block is found by its opening marker and replaced in place if the content changed, or left untouched if it matches. New blocks are appended. No duplicates, no drift.

### Managed files

| File | Managed by | Content |
|---|---|---|
| `~/.zshrc` | `inv zsh.configure` | completions, aliases, hooks — from `zshrc` fields in `setup.toml` |
| `~/.zshenv` | `inv zsh.configure` | environment variables, PATH — from `zshenv` fields in `setup.toml` |
| `~/.zprofile` | `inv zsh.configure` | login-shell config — from `zprofile` fields in `setup.toml` |
| `~/.config/curlrc` | `inv system.curlrc` | curl defaults (silent, follow redirects) |
| `/etc/sysctl.conf` | `inv system.disable-ipv6` | IPv6 disable keys |
| `/etc/systemd/journald.conf.d/size.conf` | `inv system.journal-size` | `SystemMaxUse` drop-in |
| `/etc/apt/apt.conf.d/99-pulse` | `inv apt.configure` | Disable dpkg progress bars |
| `~/.local/bin/askpass-zenity` | `inv tools.install` | Zenity GUI askpass helper — enables `sudo -A` without a TTY |
| `~/.claude/CLAUDE.md` | `inv tools.install` | Global Claude Code instructions (use `sudo -A` for all sudo calls) |

### Adding a new block

Declare `zshrc`, `zshenv`, or `zprofile` on any package entry in `setup.toml`:

```toml
[packages.mytool]
method = "apt"
zshrc  = """
export MYTOOL_HOME="${HOME}/.local/share/mytool"
eval "$(mytool init zsh)"
"""
```

Run `inv zsh.configure` — the block is written on first run and updated in place on subsequent runs. For non-shell config files, call `util.ensure_block(path, name, content)` or `util.ensure_block_text(text, name, content)` (returns new text without writing, for files that require `sudo`).

---

## Quick start

```shell
git clone <this repo>
cd power-user-linux-setup
./bootstrap.sh        # installs uv + invoke
inv setup             # runs all phases below
```

`inv setup` does not cover everything — see **Manual steps** below for what still requires human input.

### Environment variables

| Variable | Effect |
|---|---|
| `PULSE_DRY_RUN=1` | Print installed/missing status for every item without making any changes. Works across all install tasks. |
| `PULSE_EXCLUDE_TAGS=<tag>[,<tag>]` | Skip packages whose `tags` list contains any of the given labels. Defined tags: `gui`, `desktop`, `workstation`, `corporate`. |

```shell
# Check what's missing before running setup
PULSE_DRY_RUN=1 inv apt.repos apt.base apt.deb tools.install fonts.install

# Headless / container install — no GUI or hardware-specific packages
PULSE_EXCLUDE_TAGS=gui,workstation inv apt.repos apt.base
```

## Setup phases

One interruption: a single logout at the end. An optional reboot can follow if GRUB or initramfs were changed, but it can also wait for the next natural reboot — nothing depends on it being immediate.

### Phase 1 — System config

All of these take effect immediately (sysctl, DNS, journald restart) or on next login (locale). No reboot needed.

```shell
inv system.locale
inv system.curlrc
inv system.dns
inv system.disable-ipv6          # optional — sysctl -p applies immediately
inv system.journal-size          # optional — restarts journald
inv system.initramfs-compression # optional — deferred to next reboot
```

GRUB (`nomodeset`) is manual and hardware-specific — see [troubleshooting.md](troubleshooting.md). If applied, it also defers to next reboot.

### Phase 2 — Packages and tools

```shell
inv apt.configure      # write /etc/apt/apt.conf.d/99-pulse (disables dpkg progress bars)
inv apt.repos          # register external repo GPG keys + sources, then install their packages
inv apt.base           # install from Ubuntu default repos
inv apt.deb            # install .deb packages from GitHub releases or direct URLs
inv tools.install      # install tools via scripts, binaries, archives; also writes askpass-zenity
inv python.tools
inv node.install
```

`inv apt.configure` writes a drop-in that suppresses dpkg's progress bar output — run it once before any other apt tasks.

`inv apt.repos` is a two-phase command: Phase 1 registers all GPG keys and sources files, then runs `apt update` once; Phase 2 installs the packages. The two phases are bundled because the packages can't be installed without the repo. If a GPG key URL or sources write fails, that repo is skipped with a `WARNING:` message rather than aborting the whole run.

After `inv tools.install` + `inv zsh.configure`, all new shell sessions have `SUDO_ASKPASS` set to `~/.local/bin/askpass-zenity`. Any sudo call via `sudo -A` (used by the task scripts when `SUDO_ASKPASS` is present) opens a Zenity GUI dialog for the password instead of requiring a terminal prompt.

### Phase 3 — Shell config

```shell
inv zsh.omz-configure
inv zsh.configure
inv zsh.p10k-configure    # copies config/p10k.zsh to ~/.p10k.zsh if not already present
```

`zsh.p10k-configure` installs the repo's opinionated baseline (lean style, Nerd Fonts icons, transient prompt, instant prompt) and is a no-op if `~/.p10k.zsh` already exists — manual customizations are never overwritten.

To redo or fix the prompt: delete `~/.p10k.zsh` and run `inv zsh.p10k-configure` to restore the baseline, or run `p10k configure` to go through the interactive wizard. To update the baseline itself, copy your `~/.p10k.zsh` to `config/p10k.zsh`.

Phases 1–3 run automatically via `inv setup`.

### Phase 4 — Desktop *(before logout)*

`inv setup` also runs `fonts.install` and `fonts.configure`, which:

- Download all Nerd Font families to `~/.local/share/fonts/`
- Set **CaskaydiaCove Nerd Font Mono 12** as the system monospace, GNOME Terminal profile font, VS Code editor and terminal font, and Terminator terminal font

GNOME extensions require manual installation — see [gnome_extensions.md](gnome_extensions.md).

> **Logout and log back in.**
> Covers: docker group, locale full effect, GNOME extension activation, font cache.
> If GRUB or initramfs were changed, reboot instead of logout — one restart covers both.

### Phase 5 — Authentication *(interactive, last)*

```shell
gh auth login             # GitHub CLI — opens browser
ssh-keygen -t ed25519     # or follow ssh.md for full setup
```

For gcloud: see [gcloud.md](gcloud.md).

## Manual steps

These cannot be automated — they require hardware knowledge, a browser, or interactive auth:

| Step | Notes |
|---|---|
| GRUB `nomodeset` | Only needed on machines with GPU driver conflicts at boot — see [troubleshooting.md](troubleshooting.md) |
| SSH key generation | `ssh-keygen -t ed25519` — see [ssh.md](ssh.md) |
| GitHub auth | `gh auth login` |
| GNOME extensions | Requires browser extension + GNOME Extension Manager — see [gnome_extensions.md](gnome_extensions.md) |
| PyCharm font | `inv ide.pycharm-configure` — run after installing PyCharm via Toolbox (see [ide.md](ide.md)) |
| p10k prompt | `p10k configure` — interactive wizard to rebuild `~/.p10k.zsh` from scratch; use when the baseline doesn't suit you or the prompt is broken |
| JetBrains IDEs | Run `jetbrains-toolbox` after install to configure and download IDEs |
| Scala | Optional — see [scala.md](scala.md) |

## Maintenance

### Updating deb-github packages

Packages installed via `deb-github` (e.g. wezterm nightly) are not updated by `apt upgrade`.
To upgrade all of them to the latest release:

```shell
inv apt.upgrade-debs
```

This re-downloads and reinstalls each `deb-github` package. `dpkg` handles version comparison —
reinstalling the same version is safe. For packages using `tag = "nightly"`, this always fetches
the latest nightly build.

---

## Reference docs

| Topic | Doc |
|---|---|
| Zsh, OMZ, plugins, aliases | [zsh.md](zsh.md) |
| SSH keys and config | [ssh.md](ssh.md) |
| Git configuration | [git.md](git.md) |
| GitHub CLI | [github.md](github.md) |
| Docker | [docker.md](docker.md) |
| Kubernetes tools | [kubernetes.md](kubernetes.md) |
| Python (uv, virtualenvs) | [python.md](python.md) |
| Go | [golang.md](golang.md) |
| IDEs, terminal emulators | [ide.md](ide.md) |
| Scala | [scala.md](scala.md) |
| Networking and DNS | [networking.md](networking.md) |
| Fonts | [fonts.md](fonts.md) |
| GNOME extensions | [gnome_extensions.md](gnome_extensions.md) |
| Dev container / Dockerfile | [dev-container.md](dev-container.md) |
| AI tools (local LLMs, agents, assistants) | [ai.md](ai.md) |
| Troubleshooting | [troubleshooting.md](troubleshooting.md) |