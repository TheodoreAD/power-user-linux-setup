# Updating, reclaiming space, and removing things

What to run after the machine has been set up for a while. Nothing here is part of `inv setup` —
these are the operations that come later, and they were previously scattered across a page per tool.

## Updating

**Most things update themselves through apt.** Everything installed by `apt`, `apt-repo`, `deb-url`
and the repositories PULSE registered is covered by the system's own upgrade:

```shell
sudo -A apt update && sudo -A apt upgrade
```

The rest have their own mechanisms, because their upstreams do:

| What                                     | Command                    | Why it is separate                                                                        |
| ---------------------------------------- | -------------------------- | ----------------------------------------------------------------------------------------- |
| `deb-github` packages (wezterm, dive, …) | `inv apt.upgrade-debs`     | installed from a release artifact, not a repo — apt has nothing to compare against        |
| GNOME Shell extensions                   | `inv gnome.update`         | `gext`-managed, versioned against your GNOME release rather than the distro               |
| Rust toolchain                           | `rustup update`            | rustup owns its own installs under `~/.local/share/rustup`                                |
| Node                                     | `nvm install --lts`        | nvm keeps every version it has ever installed; this adds the current LTS and points at it |
| Python tools (`uv-tool` packages)        | `inv python.install-tools` | idempotent — reinstalls each declared tool at its latest version                          |
| Claude Code                              | nothing                    | the native installer self-updates                                                         |
| Scala tooling                            | `cs update`                | coursier manages its own artifacts — see [scala.md](scala.md)                             |

`inv apt.upgrade-debs` re-downloads and reinstalls each `deb-github` package; `dpkg` handles the
version comparison, so reinstalling the same version is harmless, and a package pinned to
`tag = "nightly"` always fetches the current nightly.

**After any of them, `inv verify.all` re-checks that every installed package still works** — the
same functional pass `inv setup` ends with, safe to run at any time, and the quickest health check
after installing or removing something by hand. See
[dev-container.md](dev-container.md#automated-functional-verification-inv-verifyall) for how it
decides what to check. Note that it _invokes_ each package, so a GUI-tagged one may briefly open a
window.

**To pick up changes to this repo itself** — a new package, a changed dotfile — pull and re-run
`inv setup`. Phases that are already complete offer to skip, so a re-run is cheap; and
`inv deploy.status` shows which deployed files have drifted before you change anything, with
`inv deploy.all` to push repo-side changes back out. See
[How it works](configuration.md#install-never-clobbers-redeploy-is-a-separate-deliberate-command).

## Reclaiming space

```shell
inv clean.caches        # apt, uv, npm and cargo download caches — conservative
inv clean.all           # the above plus a conservative Docker prune
inv clean.caches-full   # wipe those caches entirely
inv clean.all-full      # everything, including unused-but-tagged Docker images
```

Each step self-skips when the tool it cleans is not installed, so the umbrella tasks are safe on a
machine that has only some of them. **No Docker volume is ever touched** by any of these — see
`inv --help docker.clean` for why that is a deliberate line.

None of it runs as part of `inv setup`: a persistent workstation usually wants to keep these caches,
since they are what makes the next install fast. The conservative/full split, and exactly which
cache each task covers, is broken down in
[dev-container.md](dev-container.md#cleanup-reclaiming-image-layer-space).

## Removing a package

```shell
inv apt.uninstall <section-name>     # the [packages.<name>] key, not the apt package name
```

It purges every apt package that section declares **and** the `cleanup_paths` it lists — vendor
installers under `/opt`, stale logs, orphaned dconf locks, the things a plain `apt purge` leaves
behind. `PULSE_DRY_RUN=1` reports what it would remove without removing it.

Two caveats worth knowing before you rely on it:

- It covers packages installed **through apt or dpkg**. A tool installed by `archive`, `script` or
  `uv-tool` is not removed by this — those live under `~/.local` and are removed by deleting what
  the package's own entry in [the catalog](packages.md) says it installed.
- Some removals need a **full reboot** rather than a logout, notably Citrix Workspace — see
  [citrix.md](citrix.md).

**To stop installing something in the first place**, set `enabled = false` on its `[packages.*]`
section, or exclude a tag with `PULSE_EXCLUDE_TAGS`. Neither uninstalls what is already there;
`enabled = false` only means future runs skip it — but a `zsh`-method package whose block was
already written **is** taken back out on the next `inv zsh.configure`, since a shell block that no
longer applies would otherwise sit in your dotfile forever.

## See also

- [How it works](configuration.md) — phases, tags, and what `inv setup` does on a re-run.
- [Package catalog](packages.md) — what is installed and by which method, which decides how it
  updates and how it is removed.
- [Task index](tasks.md) — every command, including the read-only ones (`*.status`, `*.check`) worth
  running before any of the above.
