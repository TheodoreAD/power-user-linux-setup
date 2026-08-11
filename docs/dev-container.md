# Dev Container

The same `setup.toml` and invoke tasks that configure a workstation can build a dev container
image — no Docker-in-Docker required. `RUN inv setup` in a plain Dockerfile is a real, tested
path (see [Dockerfile outline](#dockerfile-outline) below); the difference from a bare-metal
install is which tags you exclude and, automatically, which phases `inv setup` itself skips.

For the `postCreateCommand`/live-git-reference distribution model instead of baking a custom
image (letting consumers layer PULSE's tooling onto _their own_ base image), see
`plans/2026-08-08-devcontainer-pipeline.md` — a separate, not-yet-implemented design. Both paths
share the same underlying fix described next.

## `inv setup` in a container — the systemd gap, and why it's handled automatically

`inv setup` runs a `system` phase first (`system.locale`, `system.dns`) that needs `systemctl`/
`localectl` — meaningless, and previously fatal, in a container with no init system. `inv setup`
now detects this itself (`util.has_systemd()`, the same check `require_systemd()` uses) and, when
there's no systemd and it isn't WSL, skips both the `system` phase and the `desktop` phase
(`fonts.install`/`fonts.configure` — irrelevant in a headless container, same reasoning
`wsl.install` already applies) instead of raising. Nothing to configure for this — it Just Works
the same way `inv setup` already auto-detects WSL and delegates to `wsl.install`.

## Tags to exclude

```dockerfile
ENV PULSE_EXCLUDE_TAGS=gui,workstation,corporate,ide,gnome
```

| Tag           | Excludes                                                                         |
| ------------- | -------------------------------------------------------------------------------- |
| `gui`         | Wayland/X11 apps, desktop tools, browsers                                        |
| `workstation` | Hardware sensors (`lm-sensors`), local terminal multiplexer (`tmux`), **Docker** |
| `corporate`   | Webex, Citrix, and other work-specific tools                                     |
| `ide`         | Full IDEs and their support profiles (`vscode`, `jetbrains-toolbox`)             |
| `gnome`       | GNOME Shell extensions and GNOME-only `xdg-desktop-portal` backends              |

`ide`/`gnome` weren't part of the original recipe here but earn their place the same way they do
under WSL (see `docs/wsl.md`) — nothing in a container has a GNOME session or benefits from a
second IDE window running inside it.

## Dockerfile outline

Tested end-to-end (`docker build`, then confirmed the installed tools actually work — not just
that the build didn't error):

```dockerfile
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip curl git sudo zsh ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://astral.sh/uv/install.sh | sh
RUN pip3 install --break-system-packages --no-cache-dir invoke

WORKDIR /setup
COPY setup.toml .
COPY tasks/ tasks/
COPY config/ config/
COPY skills/ skills/

ENV PULSE_EXCLUDE_TAGS=gui,workstation,corporate,ide,gnome
ENV PATH="/root/.local/bin:${PATH}"

RUN inv setup \
    && inv cleanup.all-full \
    && rm -rf /var/lib/apt/lists/* /tmp/*
```

`COPY skills/ skills/` is easy to miss and not optional — `ai.skills` (part of the `packages`
phase `inv setup` always runs) copies this repo's own `skills/research-library/` into the image
and fails with a `FileNotFoundError` if that directory wasn't copied in. `PATH` needs
`/root/.local/bin` up front since that's where `uv`, `invoke`, and most script/binary/archive
-method tools land (`~/.local/bin` when running as root during a build is `/root/.local/bin`).

`inv cleanup.all-full` is the container-appropriate cleanup call — see
[Cleanup](#cleanup-reclaiming-image-layer-space) below for what it does and why the container
case wants the _full_ variant specifically, not the conservative one a workstation should use.

If you don't want a shell/zsh configured in the image, drop `zsh.omz_configure`/`zsh.configure`
from consideration — but there's no need to hand-pick tasks any more; `inv setup` runs the full
sequence and self-skips what doesn't apply, matching the "just call `inv setup`" story bare-metal
installs already have. If you want more control than that, run the granular task list this
outline used to document instead: `inv apt.repos apt.base apt.deb tools.install python.tools
node.install zsh.omz-configure zsh.configure` (still fully supported, `inv setup` is a
convenience wrapper around the same tasks, not a replacement for calling them directly).

## Cleanup — reclaiming image-layer space

Every layer `inv setup` writes is permanent once committed — a later `RUN rm -rf` doesn't shrink
an _earlier_ layer, it only hides those files from the final filesystem view while the bytes stay
in the image. This is why the Dockerfile above puts cleanup in the _same_ `RUN` as `inv setup`
(chained with `&&`), not a separate step — a separate `RUN inv cleanup.all-full` after the fact
would add a new layer on top without reclaiming anything from the layer where the caches were
actually written. If you split `inv setup` across multiple `RUN` lines for better build-cache
reuse, run the matching cleanup inside whichever `RUN` created the mess, or switch to a
multi-stage build.

Two families of things accumulate during install, verified by actually building an image and
inspecting it — not assumed from reading the code:

**Downloaded archives** — confirmed clean already, no action needed. `apt.py`'s deb-github/
deb-url installers remove their downloaded `.deb` after `dpkg -i` (including a fix, made
alongside this doc, for a case where a failed `dpkg -i` used to leave the `.deb` behind); the
`archive` method streams `curl | tar` directly with no intermediate file at all. Inspecting a
built image directly (`find` for `*.zip`/`*.tar*`/`*.deb` under `~/.local/bin` and `~/`) turned
up nothing — every method that downloads an archive already cleans up after itself.

**Caches** — the real target, handled by `inv cleanup.*` (new task family, `tasks/cleanup.py` +
per-tool tasks in `tasks/apt.py`/`tasks/python.py`/`tasks/node.py`/`tasks/tools.py`/
`tasks/docker.py`). Each cache has both a conservative and a full-wipe variant, since the two
audiences for this want different tradeoffs:

| Cache                                     | Conservative (`inv cleanup.caches`)       | Full (`inv cleanup.caches-full`)                                 |
| ----------------------------------------- | ----------------------------------------- | ---------------------------------------------------------------- |
| apt `.deb` archive cache                  | `apt.clean-cache` (`apt-get autoclean`)   | `apt.clean-cache-full` (`apt-get clean`)                         |
| uv build/wheel cache (`~/.cache/uv`)      | `python.clean-cache` (`uv cache prune`)   | `python.clean-cache-full` (`uv cache clean`)                     |
| npm package cache (`~/.npm`)              | `node.clean-cache` (`npm cache verify`)   | `node.clean-cache-full` (`npm cache clean --force`)              |
| cargo registry cache (rust, if installed) | `tools.clean-cache` (downloads only)      | `tools.clean-cache-full` (downloads + extracted sources + index) |
| Docker images/containers/build cache      | `docker.clean` (`docker system prune -f`) | `docker.clean-full` (`docker system prune -af`)                  |

`inv cleanup.all` / `inv cleanup.all-full` run every row above (conservative or full,
respectively) plus Docker pruning — invoke `pre=[...]` task dependencies, same pattern as
`tasks/quality.py`'s `check`/`apply`/`fix`. Neither Docker variant touches volumes; those can
hold irreplaceable data, a different risk class than a rebuildable cache.

**Conservative on a workstation, full in a container, and why that split matters**: the uv/npm/
cargo caches directly speed up your _next_ install of the same tool. On a persistent workstation
that's worth keeping — `inv cleanup.caches`/`inv cleanup.all` (conservative) is the one to run by
hand occasionally, and neither is part of `inv setup`. A container image has no "next install" on
that machine to speed up, so the Dockerfile above calls `inv cleanup.all-full` unconditionally at
the end of its `RUN` — there's no downside to being aggressive there.

One more cache found only by actually inspecting a built image, not by reading code: Node's own
V8 compile cache under `/tmp` (small, a few MB, created by any `node`/`npm` invocation during
install — separate from npm's own package cache at `~/.npm`, which `node.clean-cache*` already
covers). Rather than chasing every script-installed tool's own `/tmp` litter by name — fragile,
breaks the moment a new tool is added to `setup.toml` — the Dockerfile above just does a blanket
`rm -rf /tmp/*` at the end, the standard Docker pattern for exactly this class of problem.

**What's _not_ a cache, confirmed by inspection**: `~/.local/share/rustup` was 1.6G in the test
build — almost entirely the actual installed toolchain (`toolchains/`), not reclaimable cache;
rustup's own `downloads`/`tmp` scratch dirs were already empty (rustup cleans its own install
-time artifacts). Only `~/.local/share/cargo/registry` (crate download/build cache, separate from
`RUSTUP_HOME`) is genuinely reclaimable, which is exactly what `tools.clean-cache*` targets. If
disk footprint matters more than cache cleanup can address, the bigger lever is
`PULSE_EXCLUDE_TAGS` itself — leaving out toolchains you don't need (rust, go, k8s tooling) beats
cleaning up after installing them.

## Docker

`[packages.docker]` is tagged `workstation` and excluded by default. It installs the full daemon
(`docker-ce`, `containerd.io`) whose apt postinstall hooks try to start the service via systemctl
— this fails in a container build. The `usermod -aG docker` post-install step is also meaningless
inside a container. `docker.configure` (part of `inv setup`'s `packages` phase) already detects
"docker not installed" and skips cleanly rather than failing, so nothing extra to do here beyond
leaving `workstation` excluded.

If you need Docker CLI tooling inside the container (e.g. for socket passthrough from the host),
install just the CLI packages manually in your Dockerfile instead:

```dockerfile
RUN apt-get install -y docker-ce-cli docker-compose-plugin docker-buildx-plugin
```

The OMZ `docker` and `docker-compose` plugins will still be loaded if you do this, since they
come from `[packages.docker].omz_plugin` — but that entry is excluded, so you'd need to add those
plugins via a separate mechanism or accept they won't load. Alternatively, mount the host socket
and use the host Docker installation directly.

## Other notes

- Tasks use `sudo` internally; either run as root (as the outline above does) or ensure `sudo` is
  installed and the build user is in sudoers.
- `claude-code`'s installer (`https://claude.ai/install.sh`) needs bash, not the `script` method's
  default `sh` (dash on Ubuntu) — already declared correctly in `setup.toml`
  (`[packages.claude-code]` sets `shell = "bash"`), nothing to do here, just don't remove it if
  editing that section.
- The `deb-url` method for Citrix is excluded by the `corporate` tag; Webex is also excluded.
- `kind` and `tilt` are included by default — remove `k8s` from tags or add your own exclusion if
  you don't need them in the container.
