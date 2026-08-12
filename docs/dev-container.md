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

WORKDIR /setup
COPY setup.toml .
COPY bootstrap.sh .
COPY tasks/ tasks/
COPY config/ config/
COPY skills/ skills/

RUN bash bootstrap.sh

ENV PULSE_EXCLUDE_TAGS=gui,workstation,corporate,ide,gnome
ENV PATH="/root/.local/bin:${PATH}"

RUN inv setup \
    && inv cleanup.all-full \
    && rm -rf /var/lib/apt/lists/* /tmp/*
```

No `apt-get install` line at all — `bootstrap.sh` now self-installs every OS-level prerequisite
(`curl`, `gnupg`, `ca-certificates`, `sudo`) the base image doesn't already have, via a preamble
gated behind `command -v apt-get` that no-ops entirely on a system that already has them (every
bare-metal/WSL/VM install, per `README.md`'s existing "Requirements" section). Only a genuinely
minimal container base image exercises the install branch. An earlier version of this doc listed
`python3 python3-pip curl git sudo zsh ca-certificates gnupg` explicitly in a hand-maintained
`apt-get install` line — all of that is gone now:

- `python3`/`python3-pip` were never actually needed — `inv setup` never touches system Python at
  all; `bootstrap.sh` provisions Python itself via `uv python install`.
- `git`/`zsh` are ordinary `[packages.*]` apt entries (`setup.toml`'s `git`/`zsh` sections),
  installed by `apt.base` well before anything in `inv setup` needs either — no reason to also
  hand-list them here.
- `curl`/`sudo`/`ca-certificates`/`gnupg` are genuine prerequisites, but now `bootstrap.sh`'s job,
  not the Dockerfile's — the same self-heal preamble every other use case (bare metal, WSL, the
  future `postCreateCommand` model) already runs unconditionally.

`gnupg` specifically matters because every `apt-repo`-method package (`gh`, `kubectl`, `docker`,
`terraform`, ...) registers its repo by piping a downloaded key through `gpg --dearmor` — without
`gpg` present, that pipe fails (`curl: (23) Failure writing output to destination`), `apt.repos`
treats the failed key fetch as "skip this repo, print a WARNING, keep going" rather than fatal, and
`RUN inv setup` used to still exit 0 while silently missing `kubectl`/`docker`/`terraform` entirely
and getting whatever stale version of `gh` happens to already be in Ubuntu's own `universe` repo
instead of the pinned upstream one. `tasks/apt.py`'s `repos()` task independently self-ensures
`gnupg`/`lsb-release` too (a second, narrower layer — see `tasks/apt.py`'s comment on that block)
so a standalone `inv apt.repos` run stays protected even outside the `bootstrap.sh` flow. This
specific bug is also exactly the shape of thing `inv verify.all` now catches automatically and
generally — see below — so `RUN inv setup` no longer exits 0 while quietly missing something.

### Automated functional verification (`inv verify.all`)

`inv setup`'s `packages` phase ends with `inv verify.all` (`tasks/verify.py`) — a hard,
convention-based check that every package this run installed also actually _works_, not just that
it's present. The gnupg bug above was originally found by hand (manually checking `gh --version`
and `dpkg -l`); this task exists so that class of bug fails the build loudly instead of needing a
human to go looking for it.

Convention, not a hand-written test per package: the default check is `<check_cmd or table-key>
--version`, with existence checks (no invocation) for methods that install something with no
command by nature — `git-clone`/`wrapper-script`/`apparmor-profile` dest/profile paths.
`gnome-extension` always skips, since no automated path (not even `inv setup`) ever calls
`inv gnome.extensions` — see `tasks/gnome.py`, GNOME sessions are never touched programmatically
in this repo. Per-package `setup.toml` fields override the convention: `verify_cmd` for a
different invocation, `verify = false` for "no functional check is possible at all." No fallback
chain anywhere — the first failure aborts `inv setup` immediately, deliberately the opposite of
`apt.py`'s `warn=True`-and-continue pattern.

Auditing this against a real, fully-provisioned machine (not just reading the code) surfaced real
bugs the convention alone wouldn't have predicted:

- **`nyancat --version` doesn't exit** — it ignores the unrecognized flag and runs its terminal
  animation forever instead. Auditing this by hand actually hung the machine it ran on before a
  fix was in place. Every invocation is now wrapped in `timeout 15s` — not a fallback, just a hard
  ceiling on the one attempt — so a badly-behaved package fails loudly in 15 seconds instead of
  hanging `inv setup` (or the machine) indefinitely. `px-proxy --version` had the same shape of
  bug — it started the proxy daemon itself instead of printing a version and exiting.
- **Container-only PATH gaps**: `go` and `node` both install to a location that's only ever put on
  `PATH` by a `zshenv`/Oh-My-Zsh-plugin snippet, sourced by an interactive shell — never sourced
  within the single non-interactive `RUN` layer a Dockerfile build runs in. Both work fine
  interactively on bare metal (a later shell sources the snippet) but need an explicit
  `verify_cmd` pointing at the real install path in `setup.toml` to be provable inside the same
  `RUN` that just installed them.
- **Table-key-vs-real-binary mismatches**: several entries' section name isn't the command it
  installs — `[packages.edge]` installs `microsoft-edge`, `[packages.vscode]` installs `code`,
  `[packages.ripgrep]` installs `rg`, `[packages.kubectl]`/`[packages.helm]`/`[packages.go]`/`k9s`
  don't support a `--version` flag at all (subcommand or short flag instead). Each got an explicit
  `verify_cmd` once the audit found it — the convention's default guess is a starting point, not a
  guarantee.
- **A genuinely stale machine**: `[packages.pulse-proxy-start]` (a `wrapper-script` entry) was
  added to `setup.toml` after this machine's last full `inv setup` run and had simply never been
  installed here — `inv verify.all` caught that too; running `inv tools.install` once fixed it.
  This is the mechanism doing exactly its job, not a false positive.

`COPY skills/ skills/` is easy to miss and not optional — `ai.skills` (part of the `packages`
phase `inv setup` always runs) copies this repo's own `skills/research-library/` into the image
and fails with a `FileNotFoundError` if that directory wasn't copied in. `PATH` needs
`/root/.local/bin` up front since that's where `uv`, `invoke`, and most script/binary/archive
-method tools land (`~/.local/bin` when running as root during a build is `/root/.local/bin`).

`inv cleanup.all-full` is the container-appropriate cleanup call — see
[Cleanup](#cleanup-reclaiming-image-layer-space) below for what it does, what it actually saves
(less than you'd think), and why the container case wants the _full_ variant specifically, not
the conservative one a workstation should use.

If you don't want a shell/zsh configured in the image, drop `zsh.omz_configure`/`zsh.configure`
from consideration — but there's no need to hand-pick tasks any more; `inv setup` runs the full
sequence and self-skips what doesn't apply, matching the "just call `inv setup`" story bare-metal
installs already have. If you want more control than that, run the granular task list this
outline used to document instead: `inv apt.repos apt.base apt.deb tools.install python.tools
node.install zsh.omz-configure zsh.configure` (still fully supported, `inv setup` is a
convenience wrapper around the same tasks, not a replacement for calling them directly).

Re-running `inv setup` inside an already-provisioned container (not a fresh `docker build` —
e.g. `devcontainer exec -- inv setup` against a container that's been kept running) is safe:
confirmed by running it twice against the same live container. Everything already installed
reports `already installed`/`already configured` and the `shell` phase offers to skip outright;
nothing gets reinstalled or duplicated. The one thing that doesn't participate in that skip logic
is `python.tools` (`uv tool install` for `keyring`/`nox`/`mkdocs-material`/etc.) — it re-resolves
each package on every run rather than probing first, which is harmless (`uv` no-ops instantly on
an already-satisfied install) but means you'll see it "reinstall" on every re-run regardless of
whether anything changed.

### Non-root user

Every real devcontainer runs as a non-root user with passwordless sudo, not root — confirmed this
Dockerfile needs no code changes for that, only a Dockerfile-side user:

```dockerfile
RUN useradd -m -s /bin/bash dev \
    && echo "dev ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/dev \
    && chmod 0440 /etc/sudoers.d/dev
USER dev
WORKDIR /home/dev/setup
# ...same COPY/ENV/RUN as above, with --chown=dev:dev on each COPY
```

Verified specifically: `util.current_user()` resolves to the non-root username (not `root`) via
its `pwd.getpwuid()` fallback — and that fallback path turns out to be the one that's _always_
exercised in a Dockerfile build, root or non-root, since plain `docker run`/`RUN` never sets
`$USER` at all (that's a login-shell/profile behavior, not something Docker sets itself); every
tool-installed file (`~/.local/bin`, `~/.cache/uv`, `~/.npm`, `~/.local/share/{cargo,rustup,nvm}`)
lands under the non-root user's real home; and `sudo` (not `sudo -A` — no `SUDO_ASKPASS` is set in
a container either way) works non-interactively against the `NOPASSWD` sudoers entry with no
prompt.

### Alternate base image: `mcr.microsoft.com/devcontainers/base:ubuntu-24.04`

Also verified end-to-end, swapping only the `FROM` line and dropping the `useradd`/sudoers block
(the image already ships a passwordless-sudo `vscode` user, plus `curl`/`gnupg`/`ca-certificates`
preinstalled) — everything else in the outline above is unchanged, and `bootstrap.sh`'s self-heal
preamble finds nothing missing on this image (`missing` stays empty, pure no-op). No conflicts
observed between this image's preinstalled packages and anything `setup.toml` installs.

### Round-tripping through `@devcontainers/cli`

The outline above is tested as a bare `docker build`; the actual VS Code Dev Containers /
`@devcontainers/cli` workflow adds its own layer of environment setup before your Dockerfile even
runs. Confirmed clean with a throwaway `devcontainer.json` pointing at this outline:

```json
{
  "name": "pulse-devcontainer",
  "build": { "dockerfile": "Dockerfile", "context": ".." },
  "remoteUser": "dev"
}
```

`npx @devcontainers/cli build --workspace-folder .`, then `devcontainer up --workspace-folder .`,
then `devcontainer exec --workspace-folder . -- inv --list` all succeeded with no adjustments
beyond the Dockerfile outline already documented here.

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
`RUSTUP_HOME`) is genuinely reclaimable, which is exactly what `tools.clean-cache*` targets.

**How much cleanup actually saves, measured**: building the identical image with and without the
`inv cleanup.all-full` step (default tag profile, otherwise byte-for-byte the same Dockerfile) —
4.40GB without cleanup vs. 4.28GB with it, a **~120MB saving, about 2.7% of image size**. Worth
knowing before reaching for it as the main size lever: it isn't one. `PULSE_EXCLUDE_TAGS` is —
leaving out toolchains you don't need (rust, go, k8s tooling are each hundreds of MB to multiple
GB) dwarfs anything cache cleanup can reclaim. Run cleanup because it's free and has no downside
in a container, not because it meaningfully shrinks the image on its own.

## Docker

`[packages.docker]` is tagged `workstation` and excluded by default, so none of this is reachable
in the recommended tag profile — it only matters if you deliberately drop `workstation` from
`PULSE_EXCLUDE_TAGS`, which was tested specifically to check for exactly this kind of tag-gated
assumption. `docker.configure` (part of `inv setup`'s `packages` phase) already detects "docker
not installed" and skips cleanly when the package is excluded, so the default profile needs
nothing extra here.

If `workstation` _is_ included, `apt-get install docker-ce ...`'s own postinstall hooks don't fail
in a container build — Debian/Ubuntu base images ship a `policy-rc.d` that denies service-start
attempts by default, so `invoke-rc.d`/`systemctl` calls from the `.deb`'s postinst are cleanly
no-opped, not fatal. What _did_ fail, found by actually testing this combination (previously
untested since it's excluded by default): `docker.configure`'s own explicit
`sudo systemctl restart docker` call afterward, unconditionally, with no no-systemd guard —
crashing the entire `inv setup` run (and thus the whole `docker build`) with "System has not been
booted with systemd as init system." Fixed in `tasks/docker.py`'s `_ensure_running()`, matching
the `util.has_systemd()` guard pattern already used for the `system`/`desktop` phases: no systemd
means daemon.json gets written and the user gets added to the `docker` group same as before, but
the restart is skipped with a one-line message instead of attempted.

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
