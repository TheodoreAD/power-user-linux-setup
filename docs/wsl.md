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

It's read-only — reports what it finds and how to fix it, changes nothing. For the fixable subset
— `/etc/wsl.conf`'s `systemd`/`generateResolvConf` settings — `inv wsl.fix` applies the fix
directly; see [Prerequisites](#prerequisites-etcwslconf) below. Everything else `wsl.check` finds
(distro choice, WSL1 vs WSL2, WSLg availability) needs action from the Windows side instead, so
there's no task for it. Everything below is the detail behind what it checks.

For the install itself, prefer `inv wsl.install` over copy-pasting the [Recommended sequence](#recommended-sequence) below by hand — see that section for why.

This isn't just advisory, either: the tasks that actually need systemd or apt/dpkg check for them
directly (`util.require_systemd()` / `util.require_apt()` in [tasks/util.py](../tasks/util.py)) and
abort immediately with an actionable message if the precondition isn't met, rather than failing
partway through with a raw `systemctl`/`apt` error. This isn't WSL-specific detection — it's a
plain capability check ("is systemd actually running", "does `apt`/`dpkg` exist"), so it fails the
same way on WSL1, a WSL2 distro with `systemd=true` unset, a non-Ubuntu WSL distro, or any other
system missing those tools. This repo targets WSL2 (with systemd enabled) specifically — WSL1 has
no real kernel and can't run systemd at all, so it's rejected by the same generic check, not a
special case. `docker.configure` similarly detects "no local `dockerd`" (Docker Desktop's WSL
integration) and skips cleanly instead of failing on `systemctl restart docker` — see
[Docker](#docker) below.

## Tags to exclude

The general principle under WSL: install as little as possible on the Linux side of the boundary.
Every extra GUI app installed inside the distro is something to keep updated, something that can
break in a WSLg-specific way, and — if it duplicates an app you already run on Windows — a second
copy to context-switch between for no reason. Default to the smallest set, and only opt back in to
something deliberately, once you have a concrete reason.

If WSLg is available (default on current Windows 11 builds — check with `inv wsl.check`), `gui`/
`desktop` packages _can_ install and work (see [GUI, WSLg, and clipboard](#gui-wslg-and-clipboard)
below), but most of them shouldn't, by default — see
[IDEs: edit from Windows instead](#ides-edit-from-windows-instead) for `ide`, and
[Windows-native duplicates](#windows-native-duplicates) for `windows-native`:

```shell
PULSE_EXCLUDE_TAGS=gnome,ide,windows-native,workstation,corporate inv apt.repos apt.base apt.deb tools.install
```

Without WSLg — no display server at all — exclude the full GUI set instead (`windows-native` and
`ide` become redundant with `gui`/`desktop` in that case, but including them doesn't hurt):

```shell
PULSE_EXCLUDE_TAGS=gui,desktop,gnome,workstation,corporate inv apt.repos apt.base apt.deb tools.install
```

| Tag              | Excludes                                                                                                                                                                                                                                                   |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `gui`            | Wayland/X11 apps, desktop tools, browsers                                                                                                                                                                                                                  |
| `desktop`        | Anything depending on a desktop session (e.g. Wayland clipboard)                                                                                                                                                                                           |
| `gnome`          | Anything needing a _live GNOME Shell_, not just a display server: GNOME Shell extensions, `gnome-extensions-cli`, and GNOME-only `xdg-desktop-portal` backends (`xdg-desktop-portal-gnome`, and `flameshot` — its capture path routes through that portal) |
| `ide`            | Full IDEs and their support profiles: `vscode`, `jetbrains-toolbox`, `apparmor-jbr-cef`                                                                                                                                                                    |
| `windows-native` | GUI apps with no Linux-specific reason to duplicate under WSL: `terminator`, `wezterm`, `freelens`, `font-manager`, `claude-desktop`, `edge`                                                                                                               |
| `workstation`    | Hardware sensors, local terminal multiplexer, **and Docker** (see below)                                                                                                                                                                                   |
| `corporate`      | Webex, Citrix, and other work-specific tools                                                                                                                                                                                                               |

Drop `workstation` from the list if you want Docker installed natively inside the distro — see
[Docker](#docker) below. Drop `ide`/`windows-native` selectively if you have an actual reason to
run one of those inside the distro instead of from Windows — the sections below cover what each
one is for and why it's excluded by default.

With the recommended set, what's left installed from the GUI/desktop tags is just
`[packages.clipboard]` (`wl-clipboard`) and `[packages.google-chrome]` — see below for why those
two specifically earn their place.

## Prerequisites — `/etc/wsl.conf`

One setting gates most of the rest, and requires a full WSL restart to take effect
(`wsl.exe --shutdown` from Windows, then reopen the terminal):

```ini
[boot]
systemd=true
```

Set it with:

```shell
inv wsl.fix
```

It edits `/etc/wsl.conf` in place — adding the key if it's missing or wrong, without touching any
other section you already have in that file (it's user-owned config, not something PULSE fully
manages) — then reminds you to restart. Idempotent: running it again once already set does nothing.
This is the only kind of WSL misconfiguration `inv wsl.fix` can address: it edits a file inside the
distro, so it only covers settings that live there. Distro choice, WSL1 vs WSL2, and WSLg
availability all require action from the Windows side instead — `inv wsl.check` still reports on
those, but there's nothing to write from inside WSL to fix them.

**`systemd=true`** — Ubuntu 24.04's WSL image ships with this by default, but confirm it.
`system.locale` (`localectl`), `system.dns` and `system.journal-size` (`systemctl`), and
`docker.configure`'s daemon restart all shell out to systemd and now abort immediately via
`util.require_systemd()` if it isn't running, rather than failing partway through. `inv wsl.check`
verifies `/run/systemd/system` is actually mounted, not just that the config file says so.

**`generateResolvConf`** — WSL's own default (`true`) regenerates `/etc/resolv.conf` from the
Windows host's DNS settings on every restart, and `inv wsl.fix`/`inv wsl.install` leave it there by
default too: it's the safe choice (see [If public DNS is blocked](#if-public-dns-is-blocked-on-this-network)
below for why), and it needs nothing further — DNS just works, mirroring whatever Windows itself
resolves. Nothing here is required unless you're opting into the public-DNS override
(`--dns=yes`/`inv wsl.fix --dns`), in which case `generateResolvConf=false` is set and `inv
system.dns` writes a systemd-resolved drop-in — but setting it doesn't finish the job by itself: on
stock Ubuntu `/etc/resolv.conf` is a symlink to systemd-resolved's stub
(`/run/systemd/resolve/stub-resolv.conf`), and `inv system.dns` (same as on bare metal) only ever
edits systemd-resolved's own drop-in config — it never touches `/etc/resolv.conf` itself. WSL's
`generateResolvConf` replaces that symlink with a plain file, and disabling the setting only stops
WSL from touching the file _going forward_ — it does not restore the symlink. So after `wsl.exe
--shutdown` and reopening, `/etc/resolv.conf` is still the stale plain file WSL last wrote, `inv
system.dns` has nothing to point at, and DNS resolution breaks (`curl: (6) Could not resolve
host`, etc.) until the symlink is put back:

```shell
sudo ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
inv system.dns
```

`inv wsl.install --dns=yes` does this relink automatically; `inv wsl.check` detects and reports
whichever of these three states you're in (WSL still generating it, generated-but-frozen without
the symlink, or correctly symlinked) if you're running the steps by hand instead.

### If public DNS is blocked on this network

`generateResolvConf=true` (WSL's own default, and `inv wsl.fix`/`inv wsl.install`'s default too —
see below) makes WSL regenerate `/etc/resolv.conf` on every restart from whatever DNS server
Windows itself is configured to use. Overriding that (`generateResolvConf=false`, what
`--dns=yes`/`inv wsl.fix --dns` does) points `/etc/resolv.conf` at public resolvers
(`1.1.1.1`/`1.0.0.1`/`8.8.8.8`, what `inv system.dns` configures) instead — and that's not risk-free
even when those resolvers are reachable:

- **They might not be reachable at all.** On some corporate networks a VPN client or firewall
  allows general internet traffic but blocks DNS (UDP 53) to anything except an internal resolver.
  The signature: `ping 1.1.1.1` works, but nothing resolves, even against `/etc/resolv.conf` pointed
  _directly_ at `1.1.1.1` (no systemd-resolved involved at all). `inv wsl.check` and
  `inv wsl.install --dns=auto` both run a direct, non-destructive probe (a raw DNS query straight
  to `1.1.1.1`/`8.8.8.8`, bypassing whatever's currently in `/etc/resolv.conf`) before touching any
  config, specifically to catch this case without a write + restart cycle. `inv wsl.install` also
  still verifies real resolution after configuring DNS and falls back to a static resolv.conf (and
  warns if even that doesn't resolve) as a second layer, in case the network's behavior changes
  between the probe and the actual configure step.
- **Even when reachable, it can still break things.** A corporate resolver often knows about
  internal/VPN-only hostnames (an internal git server, an internal package mirror, a split-DNS VPN
  zone) that `1.1.1.1` never will. Overriding WSL's own DNS trades "correct for this network" for
  "correct for the public internet" — reachability alone doesn't tell you which one you need.

Because of the second point, **the default is to leave WSL's own DNS alone regardless of whether
public DNS is reachable** — `inv wsl.install --dns=auto` (the default) and a bare `inv wsl.fix`
both default to declining the override; the reachability probe only changes the explanation shown,
never the default answer. Only opt in if you know you don't need any internal-only hostnames:

```shell
inv wsl.install --dns=yes
```

Needs the usual `wsl.exe --shutdown` + reopen to take effect, and does the relink/`system.dns`/
fallback dance described above. **Pass `--dns=yes` on every future `inv wsl.install` run on this
machine** — without it, `--dns=auto`'s default reverts `generateResolvConf` back to `true` and the
override is gone again. (In a real terminal, `wsl.install` asks this exact question interactively
before doing anything if you leave `--dns` unset — see [Interactive prompts](#interactive-prompts) below.)

## Docker

`[packages.docker]` is tagged `workstation`, so it's excluded by the recommended tag set above by
default. Two ways to get Docker working, matching the split in [docs/dev-container.md](dev-container.md):

**Docker Desktop's WSL integration** — don't install `[packages.docker]` at all (leave `workstation`
excluded). The `docker` CLI is provided by Desktop's integration; there is no local `docker.service`
for `docker.configure` to manage. `docker.configure` now detects this itself (docker CLI present,
no local `dockerd` binary) and skips with an explanatory message instead of failing on
`systemctl restart docker`. Manage Docker Desktop settings from Windows instead.

**Native `dockerd` inside the distro** — drop `workstation` from `PULSE_EXCLUDE_TAGS` (or run
`inv apt.repos apt.base` without any exclusion) and treat it like a normal Linux box. This needs
`systemd=true` from the prerequisites above; `docker.configure`'s `systemctl restart docker` then
works unmodified.

`inv wsl.check` tells you which situation you're in — presence of a local `dockerd` binary is a
reliable signal for "native", its absence alongside a working `docker` CLI means Desktop integration.

## GUI, WSLg, and clipboard

WSLg (default on current Windows 11 builds; check with `inv wsl.check`) runs a real Wayland
compositor (`weston`) plus PulseAudio/PipeWire inside the WSL2 VM, and bridges individual app
windows onto the Windows desktop over an RDP-based channel — not a full remote desktop, just
per-window compositing. GPU access comes through virtio passthrough (`/dev/dxg`) mapped to the
Windows GPU driver, so both rendering and compute get real acceleration, not software fallback.

Practically, that means `gui`/`desktop`-tagged packages _install and run_ normally under WSLg — no
separate X server (VcXsrv/X410), no manual clipboard bridge. But "would work" isn't the bar; the
bar is "is there a reason to run the Linux build specifically." Two packages clear it:

- **`[packages.clipboard]` (`wl-clipboard`)** — bidirectional and automatic. `wl-copy`/`wl-paste`
  talk to the same clipboard as Windows apps out of the box; this is reliable on any current
  Windows 11 build, not a "might work." This isn't optional the way the rest of this list is — any
  other GUI app you do run under WSLg needs it to interoperate with the Windows clipboard at all,
  and it's a single small CLI tool, not a duplicate app to maintain.
- **`[packages.google-chrome]`** — the one browser worth running as its actual Linux build: Chrome
  on Linux can render, behave, and fail differently than Chrome on Windows (font rendering, GPU
  compositing quirks, extension behavior, anything you're validating against a Linux CI/prod
  target). That's a genuine "test real Linux stuff" case WSLg makes practical. `[packages.edge]`
  doesn't add anything beyond this — same Blink/V8 engine as Chrome, so it's not distinct browser
  coverage, just a second install of the same rendering stack; see
  [Windows-native duplicates](#windows-native-duplicates).

If you're specifically doing cross-browser-engine testing, note **there's no Gecko-engine (Firefox)
package in setup.toml at all** — Chrome/Edge are both Blink. If that gap matters to you, it's worth
adding a `[packages.firefox]` entry (`apt` from Mozilla's official APT repo, not the Ubuntu snap —
same rationale as VS Code's snap avoidance elsewhere in setup.toml) rather than treating Edge as
your second engine.

Everything else `gui`/`desktop`-tagged either needs a live GNOME Shell (see the exception below) or
duplicates an app you'd run from Windows anyway — see
[Windows-native duplicates](#windows-native-duplicates) and
[IDEs: edit from Windows instead](#ides-edit-from-windows-instead).

Docker Desktop's WSL2 backend already shares this VM, which is why it's the default Docker story
for most people now rather than a separate Hyper-V VM (see [Docker](#docker) above) — but that's
Windows-side configuration, not a `[packages.*]` entry, so it isn't part of this tag discussion.

**Exception: anything that needs a live GNOME Shell, not just a compositor.** WSLg's `weston` is
not GNOME Shell — there's no `org.gnome.Shell` D-Bus service, no GNOME Shell extensions, no
`gsettings`-driven keybindings backed by a real Shell. This is exactly what the `gnome` tag now
tracks (see the table above): `[packages.xdg-desktop-portal-gnome]` and `[packages.flameshot]`
(whose capture path depends on that portal backend) are tagged `gnome` for this reason — they'll
hang or no-op under WSLg the same way they'd fail on any machine without a running GNOME session.
Anything actually `gnome`-tagged (Shell extensions, `gnome-extensions-cli`) is meaningless under
WSLg for the same reason it's meaningless in any non-GNOME compositor. `gnome.*` and `screenshot.*`
invoke tasks still shouldn't be run under WSL regardless — see the note at the bottom of this doc.

Without WSLg, skip `gui`, `desktop`, and `gnome` entirely — there's no display server at all.

## IDEs: edit from Windows instead

`[packages.vscode]`, `[packages.jetbrains-toolbox]`, and `[packages.apparmor-jbr-cef]` are tagged
`ide` and excluded by default under WSL — not because they don't work under WSLg (they would,
same as any other Electron/GTK app), but because installing them inside the distro duplicates a
client that already runs better on the Windows side:

- **VS Code**: install VS Code natively on Windows and use the **Remote-WSL** extension. The UI
  runs on Windows (native window compositing, no weston/RDP round-trip per keystroke); the
  language servers, debugger, terminal, and file watching run inside the distro over `vsock`. This
  is the same tradeoff as [dev-container.md](dev-container.md)'s Remote-Containers workflow, just
  targeting WSL instead of a container.
- **JetBrains IDEs**: same idea via **JetBrains Gateway** (or a JetBrains IDE's built-in WSL remote
  target) instead of installing `jetbrains-toolbox` inside the distro.
- **`apparmor-jbr-cef`** exists to let JetBrains' embedded Chromium (JCEF) sandbox itself — it's
  only relevant if a JetBrains IDE is actually running _inside_ the distro, so it has nothing to do
  if you're using Gateway/remote targets from Windows. It would likely need extra troubleshooting
  under WSL2 regardless: the profile requires a live AppArmor LSM (`apparmor_parser -r` against
  `/etc/apparmor.d/`), and stock WSL2 kernels don't always ship AppArmor enabled — `inv wsl.check`
  doesn't currently probe for this, so don't assume it works.

Drop `ide` from `PULSE_EXCLUDE_TAGS` if you specifically want a Linux-side IDE window running
inside the distro rather than a remote client from Windows.

## Windows-native duplicates

Tagged `windows-native` and excluded by default under WSL — these install and run fine under
WSLg, but there's no Linux-specific reason to, and you almost certainly already have (or would
rather have) the same tool on the Windows side:

- **`[packages.terminator]`, `[packages.wezterm]`** — terminal emulators. You're necessarily
  already inside _some_ terminal to reach a WSL shell in the first place (Windows Terminal, or
  Windows-side WezTerm), so launching a second terminal emulator from within that session via
  WSLg mostly just adds a redundant window, not new capability.
- **`[packages.freelens]`** — a Kubernetes GUI. It only needs network reachability to a cluster
  and a kubeconfig, neither of which is Linux-specific; run it from Windows and point it at the
  same cluster.
- **`[packages.claude-desktop]`** — an Electron chat client with no OS-specific behavior to test.
  Install once, on Windows.
- **`[packages.font-manager]`** — previews fonts already present in the _WSL-side_ filesystem,
  which per [Fonts](#fonts) below usually isn't where the fonts your terminal actually renders
  live anyway, so it's previewing the wrong set more often than not.
- **`[packages.edge]`** — see the browser discussion above: same engine as `google-chrome`, so it
  isn't distinct Linux-testing coverage, just a second Chromium install.

Drop `windows-native` selectively (not as a block) if one of these is a deliberate exception —
e.g. you want WezTerm's Linux build specifically to test its GPU passthrough behavior under WSLg.

## Fonts

`inv fonts.install` installs Nerd Fonts into `~/.local/share/fonts` _inside the WSL filesystem_.
If your terminal is Windows Terminal (or anything else running on the Windows side, not through
WSLg), it can't see fonts installed there — install the Nerd Font on the Windows side separately.
This isn't something PULSE can automate from inside WSL; there's no supported way to reach across
the WSL/Windows boundary to install a font on the host from a distro-side task.

`inv fonts.configure` sets GNOME's system monospace font and GNOME Terminal's profile font via
`gsettings` — both no-op safely without a GNOME session (confirmed: `gsettings set` failures are
caught and printed as a skip, not a crash). The VS Code settings.json part of the same task is
useful under WSL if you're using VS Code's Remote-WSL extension.

## Recommended sequence

`inv setup` auto-detects WSL (via `util.is_wsl()`) and delegates straight to `inv wsl.install` —
you don't need to know to call `wsl.install` specifically; running the same `inv setup` from the
[Quick start](index.md#quick-start) does the right thing on WSL too. Run `inv wsl.install` directly
instead of `inv setup` only when you want its `--wslg`/`--docker`/`--dns` options (`inv setup`
always uses their defaults).

`inv wsl.install` runs the sequence below for you, as task calls inside a single invoke process:

```shell
inv wsl.install              # auto-detects WSLg, excludes workstation/corporate/ide/... per the table above
inv wsl.install --wslg=no    # force the no-WSLg tag set instead of auto-detecting
inv wsl.install --docker     # also keep the workstation tag (installs Docker natively)
inv wsl.install --dns=yes    # opt into the public-DNS override — see "If public DNS is blocked" above
                              # (--dns=no is the default and needs no flag; shown here for clarity)
```

It calls `wsl.check` and `wsl.fix` first, then `system.locale`/`system.dns` (only if systemd/DNS
are actually live yet — skipped with a message otherwise, if `wsl.fix` just changed
`/etc/wsl.conf` and you haven't restarted WSL), _then_ two named phases run through
`tasks/phases.py`: **packages** (`apt.repos`/`apt.base`/`apt.deb`/`tools.install`/`ai.skills`/
`python.tools`/`node.install`) and **shell** (`zsh.omz-configure`/`zsh.configure`/
`zsh.p10k-configure`/`zsh.set-default-shell`). DNS has to be fixed before the packages/shell
phases — on a re-run after a restart with `generateResolvConf=false` already active, DNS is broken
(see [Prerequisites](#prerequisites-etcwslconf) above) until `system.dns` runs, and every one of
those later steps needs working DNS itself. It finishes by printing the next concrete manual step
(see ["next steps" reporting](#next-steps-reporting) below).

Each phase prints a labeled banner, then probes itself with `PULSE_DRY_RUN` forced on (every task
inside already has a side-effect-free dry-run check) before doing any real work. If the probe comes
back with nothing missing, it asks whether to skip the phase — default **skip** on Enter, and
skipped silently outside a real terminal. This is what makes re-running `inv wsl.install` after the
`/etc/wsl.conf` restart cheap: if packages and shell already succeeded before the restart, each is
now a single confirmation instead of redoing every `apt`/tool/`zsh` step from scratch. A phase with
real outstanding work is never gated behind a prompt — it just runs.

This is the one worth using instead of pasting the equivalent multi-line block below into a
terminal: that block is a series of separate `inv` invocations one per line, so if one hangs (a
network problem mid-`apt`, say) and you hit Ctrl-C, the shell only kills _that_ command — it then
reads the next already-pasted line from its input buffer and keeps going, which looks like Ctrl-C
"did nothing" and skipped ahead. `wsl.install` runs everything in one process instead, so Ctrl-C at
any point aborts the whole thing.

### Interactive prompts

In a real terminal (not piped, scripted, or CI — checked via `sys.stdin.isatty()`), `wsl.install`
asks before doing anything:

- If `--dns` was left at its default (`auto`), a probe result line (public DNS reachable or not —
  see [If public DNS is blocked](#if-public-dns-is-blocked-on-this-network) above) followed by the
  override question, **defaulting to "no"** regardless of what the probe found — declining on
  Enter leaves WSL's own DNS alone.
- A one-line summary of what's about to happen (given your answer above, plus `--wslg`/`--docker`),
  then a final "Proceed?" — answering no aborts before touching anything.
- Once running, the **packages** and **shell** phases each ask "Already looks complete — skip this
  phase?" if their own dry-run probe found nothing missing — see [Recommended sequence](#recommended-sequence) above.

The DNS question defaults to "no" (decline the override) on Enter; the rest default to "yes"
(proceed / skip). `yes | inv wsl.install` still works non-interactively if you ever need it
scripted, since piping `yes` answers every prompt affirmatively regardless of its own default. A
genuinely non-interactive invocation (piped, cron, CI) skips every prompt entirely and takes each
one's default — so `--dns=auto` there now means "no" (WSL-managed DNS; pass `--dns=yes` explicitly
if a scripted run needs the override instead), and any phase whose probe came back clean is skipped
silently rather than redone.

Summaries, warnings, doc pointers, and these prompts all render as bordered blocks — via
`tasks/ui.py`, a small formatting library (`ui.block`/`ui.note`/`ui.warn`/`ui.ask`) that's what
actually makes them stand out from the apt/dpkg/curl/gpg output scrolling past in the same run.
Terse per-package status lines (`[gh] repo:ok`) are deliberately left alone — they're meant to
blend in with everything else's output, not compete with it.

### "next steps" reporting

Both `inv wsl.install` and `inv setup` end by calling `next_steps.print_next_steps()` — it checks
real state rather than a stored "did we already tell you" flag, and prints the single next thing
to do:

1. If the login shell isn't zsh yet, tells you to open a new terminal (or, if `usermod` failed,
   the exact command to run by hand) and re-run.
2. Otherwise, if `~/.config/pulse/identity.toml` doesn't exist, tells you to run `inv identity.init`
   (interactive wizard — simple single-identity setup, or points you at hand-editing the example
   for multiple directories/accounts), then re-run.
3. Otherwise, walks the `inv git.*`/`inv ssh.*` chain one command at a time — global git settings
   applied? per-directory git profiles set up? an SSH key present for every `identity.toml` email?
   `~/.ssh/config` written? keys loaded into the agent? `gh` authenticated (only checked if `gh`
   is actually installed)?
4. Otherwise, nothing left that's automatable — just the Windows-side Nerd Font reminder (see
   [Fonts](#fonts) below; this one genuinely can't be checked or done from inside WSL).

Safe to re-run after doing whatever it suggests — it's checking, not remembering.

If you want to run the phases individually instead — e.g. to stop and inspect state between
steps — here's the same sequence by hand:

```shell
inv wsl.check   # do this first — tells you whether WSLg is available, and whether public DNS
                # (1.1.1.1/8.8.8.8) is even reachable on this network
inv wsl.fix     # sets systemd=true; leaves generateResolvConf=true (WSL-managed DNS, the safe
                # default — see "If public DNS is blocked" above). Pass --dns to override with
                # public DNS instead: `inv wsl.fix --dns`

# then, from Windows (PowerShell/cmd): wsl.exe --shutdown — only if wsl.fix changed anything —
# and reopen your terminal before continuing

# only if /etc/wsl.conf has systemd=true:
inv system.locale

# only if you ran `inv wsl.fix --dns` (generateResolvConf=false) — fix DNS *before* anything below
# that needs network access, and restore the symlink WSL replaced first, see "Prerequisites" above:
sudo ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
inv system.dns
# if you didn't run `inv wsl.fix --dns`, skip both lines above — WSL is already managing
# /etc/resolv.conf itself and DNS works out of the box

# with WSLg (default on current Windows 11):
PULSE_EXCLUDE_TAGS=gnome,ide,windows-native,workstation,corporate inv apt.repos apt.base apt.deb
# without WSLg:
# PULSE_EXCLUDE_TAGS=gui,desktop,gnome,workstation,corporate inv apt.repos apt.base apt.deb

inv tools.install
inv ai.skills
inv python.tools
inv node.install
inv zsh.omz-configure zsh.configure zsh.p10k-configure
inv zsh.set-default-shell   # usermod -s — takes a new terminal to actually apply
```

`gnome.*` and `screenshot.*` tasks are never called by `inv setup` and have no meaning under WSL —
just don't invoke them.
