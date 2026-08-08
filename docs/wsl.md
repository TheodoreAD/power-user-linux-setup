# WSL

The same `setup.toml` and invoke tasks that configure a workstation can bootstrap a WSL2
distro. Most of it works unmodified — apt/apt-repo/deb-github/deb-url/uv-tool/archive installs and
the zsh/uv/nvm toolchain are plain userspace and don't care that they're running under WSL. The
parts that need attention are the ones that assume a full systemd-managed machine with a GNOME
session: DNS, Docker, and anything `gui`/`desktop`/`gnome`-tagged.

Run the diagnostic first, before installing anything:

```shell
inv wsl.check
```

It's read-only — reports what it finds and how to fix it, changes nothing. Everything below is the
detail behind what it checks.

## Tags to exclude

```shell
PULSE_EXCLUDE_TAGS=gui,desktop,gnome,workstation,corporate inv apt.repos apt.base apt.deb tools.install
```

| Tag | Excludes |
|---|---|
| `gui` | Wayland/X11 apps, desktop tools, browsers |
| `desktop` | Anything depending on a desktop session (e.g. Wayland clipboard) |
| `gnome` | GNOME Shell extensions and `gnome-extensions-cli` — meaningless without GNOME Shell |
| `workstation` | Hardware sensors, local terminal multiplexer, **and Docker** (see below) |
| `corporate` | Webex, Citrix, and other work-specific tools |

Drop `workstation` from the list if you want Docker installed natively inside the distro — see
[Docker](#docker) below.

## Prerequisites — `/etc/wsl.conf`

Two settings gate most of the rest. Both require a full WSL restart to take effect
(`wsl.exe --shutdown` from Windows, then reopen the terminal):

```ini
[boot]
systemd=true

[network]
generateResolvConf = false
```

**`systemd=true`** — Ubuntu 24.04's WSL image ships with this by default, but confirm it.
`system.locale` (`localectl`), `system.dns` and `system.journal-size` (`systemctl`), and
`docker.configure`'s daemon restart all shell out to systemd and fail without it. `inv wsl.check`
verifies `/run/systemd/system` is actually mounted, not just that the config file says so.

**`generateResolvConf = false`** — without it, WSL regenerates `/etc/resolv.conf` from the Windows
host's DNS settings on every restart, silently discarding whatever `inv system.dns` wrote. With it
set, `/etc/resolv.conf` stays under your control and `inv system.dns` works exactly as it does on
bare metal.

## Docker

`[packages.docker]` is tagged `workstation`, so it's excluded by the recommended tag set above by
default. Two ways to get Docker working, matching the split in [docs/dev-container.md](dev-container.md):

**Docker Desktop's WSL integration** — don't install `[packages.docker]` at all (leave `workstation`
excluded). The `docker` CLI is provided by Desktop's integration; there is no local `docker.service`
for `docker.configure` to manage, so running it would fail on `systemctl restart docker`. Manage
Docker Desktop settings from Windows instead.

**Native `dockerd` inside the distro** — drop `workstation` from `PULSE_EXCLUDE_TAGS` (or run
`inv apt.repos apt.base` without any exclusion) and treat it like a normal Linux box. This needs
`systemd=true` from the prerequisites above; `docker.configure`'s `systemctl restart docker` then
works unmodified.

`inv wsl.check` tells you which situation you're in — presence of a local `dockerd` binary is a
reliable signal for "native", its absence alongside a working `docker` CLI means Desktop integration.

## GUI, WSLg, and clipboard

If WSLg is enabled (default on current Windows 11 builds), GUI Linux apps and a Wayland compositor
are available inside the distro, which means `[packages.clipboard]` (`wl-clipboard`) and other
`gui`/`desktop`-tagged packages might actually work. PULSE doesn't test against this — if you want
to try it, drop `gui`/`desktop` from the exclusion list selectively rather than installing a GNOME
desktop's worth of extensions and expecting them to mean anything (there's no GNOME Shell under
WSLg, so anything `gnome`-tagged specifically still doesn't apply).

Without WSLg, skip `gui`, `desktop`, and `gnome` entirely — there's no display server at all.

## Fonts

`inv fonts.install` installs Nerd Fonts into `~/.local/share/fonts` *inside the WSL filesystem*.
If your terminal is Windows Terminal (or anything else running on the Windows side, not through
WSLg), it can't see fonts installed there — install the Nerd Font on the Windows side separately.
This isn't something PULSE can automate from inside WSL; there's no supported way to reach across
the WSL/Windows boundary to install a font on the host from a distro-side task.

`inv fonts.configure` sets GNOME's system monospace font and GNOME Terminal's profile font via
`gsettings` — both no-op safely without a GNOME session (confirmed: `gsettings set` failures are
caught and printed as a skip, not a crash). The VS Code settings.json part of the same task is
useful under WSL if you're using VS Code's Remote-WSL extension.

## Recommended sequence

Skip `inv setup` wholesale — it calls `system.dns` and `docker.configure` unconditionally, which
you may not want depending on your `/etc/wsl.conf` and Docker choice above. Run the phases you want
directly:

```shell
inv wsl.check   # do this first

PULSE_EXCLUDE_TAGS=gui,desktop,gnome,workstation,corporate inv apt.repos apt.base apt.deb
inv tools.install
inv python.tools
inv node.install
inv zsh.omz-configure zsh.configure zsh.p10k-configure

# only if /etc/wsl.conf has systemd=true:
inv system.locale

# only if /etc/wsl.conf also has generateResolvConf = false:
inv system.dns
```

`gnome.*` and `screenshot.*` tasks are never called by `inv setup` and have no meaning under WSL —
just don't invoke them.
