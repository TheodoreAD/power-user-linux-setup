# Google Cloud CLI

!!! NOTE

    Only needed for GCP work — large install (~1GB). Disabled by default in `setup.toml`.

## Why not apt?

Installing via apt completely disables `gcloud components install` — it fails outright.
Additional components must then be managed as separate `google-cloud-cli-*` apt packages,
which is more cumbersome and ties component versions to the distro's packaging cadence.

The standalone installer keeps everything self-contained under `~/.local/share/google-cloud-sdk`,
handles its own updates, and gives full access to `gcloud components install/update` with
no sudo required after the initial setup.

## Install

Enable `[packages.gcloud]` in `setup.toml`, then run:

```shell
inv tools.install
inv zsh.configure   # adds gcloud to PATH and enables zsh completion
```

The installer script runs non-interactively and does not modify any shell rc files —
PATH and completion are handled by the `zshrc` field in `setup.toml` via `inv zsh.configure`.

## Post-install (interactive — run manually)

```shell
gcloud init

# Container Registry:
gcloud auth configure-docker

# Artifact Registry (repeat per region you use):
gcloud auth configure-docker REGION-docker.pkg.dev
```

!!! WARNING

    `gcloud auth configure-docker` does not work with Docker installed via Snap.
    Use the apt-installed Docker from `[packages.docker]` in `setup.toml`.

## Managing components

```shell
gcloud components list              # see all available components and their status
gcloud components install cloud-run-proxy   # example: local proxy for Cloud Run services
gcloud components install beta      # alpha/beta command groups
gcloud components update            # update all installed components
```

No sudo, no apt, no package names to look up — the component manager handles everything.

## Upgrade the CLI itself

```shell
gcloud components update
```

## Uninstall

```shell
rm -rf ~/.local/share/google-cloud-sdk
# remove the block from ~/.zshrc added by inv zsh.configure
```
