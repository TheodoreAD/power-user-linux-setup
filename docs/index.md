# PULSE — Power User Linux Setup

**PULSE** (Power User Linux Setup) is an opinionated, reproducible workstation setup for Ubuntu
24.04, driven by a single `setup.toml` and [`invoke`](https://www.pyinvoke.org/) tasks. Clone, run
`bootstrap.sh`, run `inv setup` — no step-by-step walkthrough required for the golden path.

<div class="grid cards" markdown>

- :material-desktop-classic:{ .lg .middle } **Full workstation**

  ---

  Bare-metal or VM Ubuntu 24.04 desktop: shell, languages, GNOME, fonts, terminals — everything
  below runs.

  [:octicons-arrow-right-24: Quick start](#quick-start)

- :material-server:{ .lg .middle } **Headless / server**

  ---

  Skip anything needing a display with `PULSE_EXCLUDE_TAGS=gui,workstation,...`.

  [:octicons-arrow-right-24: Tags and exclusion](configuration.md#tags-enabled-and-which-tasks-actually-respect-either)

- :material-docker:{ .lg .middle } **Dev container**

  ---

  The same manifest builds a Dockerfile-based dev image via a documented tag-exclusion profile.

  [:octicons-arrow-right-24: Dev container guide](dev-container.md)

- :material-microsoft-windows:{ .lg .middle } **WSL2**

  ---

  A read-only diagnostic task plus a documented tag profile for Windows/WSL2 setups.

  [:octicons-arrow-right-24: WSL guide](wsl.md)

</div>

## What you get, out of the box

Everything below is configured by `inv setup` and works together on purpose — the font is what the
prompt icons and the statusline glyphs are drawn from, and the statusline is laid out to match the
prompt. None of it needs a wizard, and all of it is yours to change.

- **A terminal that opens ready to work** — WezTerm starts maximized as a 2×2 pane grid with
  `ALT+1..4` to jump between panes, `CTRL+Tab` to cycle, and `ALT+SHIFT+arrows` to resize.
  [Startup layout and keys](terminal.md#startup-layout)
- **A finished shell prompt** — Powerlevel10k, two-line lean style, transient prompt, instant
  prompt, git status and the active environment where you expect them. No `p10k configure` step.
  [The prompt](zsh.md#the-prompt)
- **A Claude Code statusline that shows what the session costs** — model, context window, both
  rate-limit windows and session cost, each coloured by thresholds chosen from how the pricing
  actually works. [The statusline](claude-code.md#the-statusline)
- **Nerd Fonts, installed and wired up** — every icon in the three items above comes from here.
  [Fonts](fonts.md)
- **Agent instructions that come with the machine** — `~/.agents/AGENTS.md`, assembled from reviewed
  fragments and read by every agent tool that follows the convention.
  [Global instructions](claude-code.md#agentsagentsmd-global-instructions-declaratively-managed)

## Quick start

```shell
cd ~
mkdir -p projects
cd projects
git clone https://github.com/TheodoreAD/power-user-linux-setup.git
cd power-user-linux-setup
./bootstrap.sh        # installs uv + invoke
inv setup             # runs the full setup — see configuration.md for what that covers, phase by phase
```

`inv setup` does not cover everything — see **Manual steps** below for what still requires human
input.

On a restricted or corporate network, `bootstrap.sh` runs a network preflight before its first
download and prints which of the hosts a setup run needs are reachable and what to do about each one
that isn't — the same report as `inv net.check`, available with nothing installed as
`python3 tasks/netdoctor.py`. See [net-doctor.md](net-doctor.md).

### Environment variables

| Variable                           | Effect                                                                                                                                                                                                                                                           |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PULSE_DRY_RUN=1`                  | Print installed/missing status for every item without making any changes. Works across all install tasks.                                                                                                                                                        |
| `PULSE_EXCLUDE_TAGS=<tag>[,<tag>]` | Skip packages whose `tags` list contains any of the given labels — see [configuration.md](configuration.md#tags-enabled-and-which-tasks-actually-respect-either) for the full catalog and its limits.                                                            |
| `PULSE_SKIP_PREFLIGHT=1`           | Skip `bootstrap.sh`'s network preflight ([net-doctor.md](net-doctor.md)). It is advisory — it reports and continues — so this is only for saving the few seconds it takes.                                                                                       |
| `PULSE_ASSUME_YES=1`               | `--yes` for `inv setup` and the other composite tasks that have no flag of their own: overwrite a deployed file that was edited at its destination (the diff is still printed). Unattended runs need it — the prompt defaults to _no_ with no terminal attached. |

```shell
# Check what's missing before running setup
PULSE_DRY_RUN=1 inv apt.install-repos apt.install-base apt.install-debs tools.install fonts.install

# Headless / container install — no GUI or hardware-specific packages
PULSE_EXCLUDE_TAGS=$(inv devcontainer.print-exclude-tags) inv setup
```

Curious what `inv setup` actually runs, phase by phase, or how config files and tags work under the
hood? See [How it works](configuration.md).

## Manual steps

These cannot be automated — they require hardware knowledge, a browser, or interactive auth:

| Step               | Notes                                                                                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| GRUB `nomodeset`   | Only needed on machines with GPU driver conflicts at boot — see [troubleshooting.md](troubleshooting.md)                                    |
| SSH key generation | `ssh-keygen -t ed25519` — see [ssh.md](ssh.md)                                                                                              |
| GitHub auth        | `gh auth login`                                                                                                                             |
| GNOME extensions   | Installed via gext (`inv gnome.install-extensions`), then logout/login to activate — see [gnome_extensions.md](gnome_extensions.md)         |
| PyCharm font       | `inv ide.configure-pycharm` — run after installing PyCharm via Toolbox (see [ide.md](ide.md))                                               |
| p10k prompt        | `p10k configure` — interactive wizard to rebuild `~/.p10k.zsh` from scratch; use when the baseline doesn't suit you or the prompt is broken |
| JetBrains IDEs     | Run `jetbrains-toolbox` after install to configure and download IDEs                                                                        |
| Scala              | Optional — see [scala.md](scala.md)                                                                                                         |

## Maintenance

Day-two operations live on their own page: [Updating and removing](updating.md) covers what apt
upgrades for you and what needs its own command (`deb-github` packages, GNOME extensions, rustup,
nvm, uv tools), how to reclaim cache space, and how to remove a package including the files a plain
`apt purge` leaves behind.

The three worth knowing without reading it:

```shell
inv apt.upgrade-debs   # the packages apt cannot upgrade, because they came from a release artifact
inv verify.all         # re-check that everything installed still actually runs
inv clean.all          # reclaim cache space, conservatively
```

## See also

- [How it works](configuration.md) — phases, tags, and how config files are written without
  clobbering yours
- [Package catalog](packages.md) — everything a full run installs
- [Updating and removing](updating.md) — what to run once the machine is set up
