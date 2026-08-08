# Power User Linux Setup (PULSE)

An opinionated, reproducible workstation setup for Ubuntu 24.04: one `setup.toml` manifest and a
set of [`invoke`](https://www.pyinvoke.org/) tasks that take a fresh install to a fully configured
dev/desktop environment in one run — shell (zsh, Oh My Zsh, Powerlevel10k), languages and CLIs
(Python/uv, Go, Rust, Node, kubectl, gcloud, ...), GNOME, fonts, terminal config, and more, all
declared in one place and safe to re-run.

Along with source control, this is meant to minimize the impact of hardware failure and to make it
easy to reproduce your setup on a new machine, with the least amount of manual reconfiguration.

## Use cases

- **Full workstation** — bare-metal or VM Ubuntu 24.04 desktop, GNOME included.
- **Headless / server** — `PULSE_EXCLUDE_TAGS` skips anything needing a display or hardware access.
- **Dev container** — the same manifest builds a Dockerfile-based dev image.
- **WSL2** — a diagnostic task (`inv wsl.check`) and a one-shot install task (`inv wsl.install`)
  with a documented tag profile for Windows/WSL2.

## Requirements

- Ubuntu 24.04 (bare metal, WSL2, or a container base image)
- `sudo` access
- `git`, `curl`, `bash` — present on any stock Ubuntu install

Everything else — `uv`, Python, `invoke` — is installed by `bootstrap.sh` itself. The intent is to
be distribution-agnostic eventually, but only Ubuntu 24.04 (`noble numbat`) is tested today.

## Quick start

```shell
cd ~
mkdir -p projects
cd projects
git clone https://github.com/TheodoreAD/power-user-linux-setup.git
cd power-user-linux-setup
./bootstrap.sh        # installs uv + invoke
inv setup             # runs the full setup
```

## Recommended hardware

Not a requirement — just a sizing guideline for what this setup assumes you're comfortable running:

| Tier | Spec |
|---|---|
| Minimum | 8GB RAM, 1× 27" FHD display |
| Regular | 16GB RAM, 2× 27" FHD displays |
| Power user | 32GB RAM, 1× 42"+ 4K UHD display |

***

This is just a short overview. For everything else — use-case walkthroughs, the full package
catalog, how the config system and tags work, and per-topic reference docs (shell, languages,
Docker/Kubernetes, GNOME, WSL, troubleshooting, ...) — see the docs site:

**[theodoread.github.io/power-user-linux-setup](https://theodoread.github.io/power-user-linux-setup/)**
