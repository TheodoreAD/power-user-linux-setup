# Dev Container

The same `setup.toml` and invoke tasks that configure a workstation can be used to build a dev container image. The difference is which tasks you run and which tags you exclude.

## Tags to exclude

```dockerfile
ENV PULSE_EXCLUDE_TAGS=gui,workstation,corporate
```

| Tag | Excludes |
|---|---|
| `gui` | Wayland/X11 apps, desktop tools, browsers |
| `workstation` | Hardware sensors (`lm-sensors`), local terminal multiplexer (`tmux`) |
| `corporate` | Webex, Citrix, and other work-specific tools |

## Tasks to skip

These tasks configure the physical machine and have no meaning in a container:

- `system.locale` — calls `localectl`, which requires systemd
- `system.journal_size` — configures systemd-journald
- `system.curlrc` — per-user config, fine to include but skip if you want clean image layers
- `system.disable_ipv6` — sysctl, irrelevant inside a container
- `system.initramfs_compression` — initramfs, irrelevant inside a container

`zsh.omz_configure` and `zsh.configure` are fine to include if you want an interactive shell in the container.

## Dockerfile outline

```dockerfile
FROM ubuntu:24.04

# Install bootstrap dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip curl git sudo zsh \
    && rm -rf /var/lib/apt/lists/*

# Install uv and invoke
RUN curl -fsSL https://astral.sh/uv/install.sh | sh
RUN pip3 install invoke

WORKDIR /setup
COPY setup.toml .
COPY tasks/ tasks/

ENV PULSE_EXCLUDE_TAGS=gui,workstation,corporate

RUN inv apt.repos apt.base apt.deb
RUN inv tools.install
RUN inv python.tools
RUN inv node.install
RUN inv zsh.omz-configure zsh.configure
```

## Docker

`[packages.docker]` is tagged `workstation` and excluded by default. It installs the full daemon (`docker-ce`, `containerd.io`) whose apt postinstall hooks try to start the service via systemctl — this fails in a container build. The `usermod -aG docker` post-install step is also meaningless inside a container.

If you need Docker CLI tooling inside the container (e.g. for socket passthrough from the host), install just the CLI packages manually in your Dockerfile instead:

```dockerfile
RUN apt-get install -y docker-ce-cli docker-compose-plugin docker-buildx-plugin
```

The OMZ `docker` and `docker-compose` plugins will still be loaded if you do this, since they come from `[packages.docker].omz_plugin` — but that entry is excluded, so you'd need to add those plugins via a separate mechanism or accept they won't load. Alternatively, mount the host socket and use the host Docker installation directly.

## Other notes

- Tasks use `sudo` internally; either run as root or ensure `sudo` is installed and the build user is in sudoers
- `apt.base` and `apt.repos` call `apt-get` — run `apt-get update` first if the base image cache is stale
- The `deb-url` method for Citrix is excluded by the `corporate` tag; Webex is also excluded
- `kind` and `tilt` are included by default — remove `k8s` from tags or add your own exclusion if you don't need them in the container
