# PULSE — Power User Linux Setup

**PULSE** (Power User Linux Setup) is an opinionated, reproducible workstation setup for Ubuntu 24.04, driven by a single `setup.toml` and [`invoke`](https://www.pyinvoke.org/) tasks. Clone, run `bootstrap.sh`, run `inv setup` — no step-by-step walkthrough required for the golden path.

<div class="grid cards" markdown>

-   :material-desktop-classic:{ .lg .middle } **Full workstation**

    ---

    Bare-metal or VM Ubuntu 24.04 desktop: shell, languages, GNOME, fonts, terminals — everything below runs.

    [:octicons-arrow-right-24: Quick start](#quick-start)

-   :material-server:{ .lg .middle } **Headless / server**

    ---

    Skip anything needing a display with `PULSE_EXCLUDE_TAGS=gui,workstation,...`.

    [:octicons-arrow-right-24: Tags and exclusion](configuration.md#tags-enabled-and-which-tasks-actually-respect-either)

-   :material-docker:{ .lg .middle } **Dev container**

    ---

    The same manifest builds a Dockerfile-based dev image via a documented tag-exclusion profile.

    [:octicons-arrow-right-24: Dev container guide](dev-container.md)

-   :material-microsoft-windows:{ .lg .middle } **WSL2**

    ---

    A read-only diagnostic task plus a documented tag profile for Windows/WSL2 setups.

    [:octicons-arrow-right-24: WSL guide](wsl.md)

</div>

## Quick start

```shell
git clone <this repo>
cd power-user-linux-setup
./bootstrap.sh        # installs uv + invoke
inv setup             # runs the full setup — see configuration.md for what that covers, phase by phase
```

`inv setup` does not cover everything — see **Manual steps** below for what still requires human input.

### Environment variables

| Variable | Effect |
|---|---|
| `PULSE_DRY_RUN=1` | Print installed/missing status for every item without making any changes. Works across all install tasks. |
| `PULSE_EXCLUDE_TAGS=<tag>[,<tag>]` | Skip packages whose `tags` list contains any of the given labels — see [configuration.md](configuration.md#tags-enabled-and-which-tasks-actually-respect-either) for the full catalog and its limits. |

```shell
# Check what's missing before running setup
PULSE_DRY_RUN=1 inv apt.repos apt.base apt.deb tools.install fonts.install

# Headless / container install — no GUI or hardware-specific packages
PULSE_EXCLUDE_TAGS=gui,workstation inv apt.repos apt.base
```

Curious what `inv setup` actually runs, phase by phase, or how config files and tags work under the hood? See [How it works](configuration.md).

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
