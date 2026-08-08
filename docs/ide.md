# IDEs

## VS Code

### Install method: apt deb (not snap)

VS Code is installed via the Microsoft apt repo, managed by `inv apt.repos`. The snap
version was removed in favour of the deb.

**Why deb over snap:**

| Issue | Snap | Deb |
|---|---|---|
| Startup crashes after auto-update | Known on 24.04 (issue #224112) | Not affected |
| SSH Remote Dev | Sandbox can break extension host | Full filesystem access |
| File system access | Restricted by classic confinement | Full |
| Wayland GPU acceleration | Broken (issues #105729, #224112) | Works |
| Update delivery | Automatic background | Via `apt upgrade` |

The machine runs Wayland (switched 2026-06-08), so the GPU acceleration and sandbox
issues apply directly in addition to the startup crash and SSH Remote Dev concerns.

**Setup:**

```toml
[packages.vscode]
method      = "apt-repo"
gpg_url     = "https://packages.microsoft.com/keys/microsoft.asc"
gpg_path    = "/usr/share/keyrings/microsoft-vscode.gpg"
sources_path = "/etc/apt/sources.list.d/vscode.list"
sources_entry = "deb [arch=amd64 signed-by={gpg_path}] https://packages.microsoft.com/repos/code stable main"
```

```shell
inv apt.repos    # sets up GPG key + sources, installs code
```

**Migration from snap (done 2026-06-08):**

```shell
sudo snap remove code   # profile at ~/.config/Code/ — same path for deb, nothing to migrate
inv apt.repos
```

Settings/extensions are preserved because both snap (classic confinement) and deb use
`~/.config/Code/User/` for the user profile.

### Font configuration

Run `inv fonts.configure` to set CaskaydiaCove Nerd Font Mono 12 in VS Code. The settings
written are declared in `setup.toml` under `[settings.fonts.vscode]` and include both
`editor.fontSize` and `terminal.integrated.fontSize` (both 12).

---

## JetBrains

### JetBrains Toolbox

Toolbox is installed via `inv tools.install` using the `archive` method. It downloads the
full Toolbox archive, extracts it to `~/.local/share/jetbrains-toolbox/`, and symlinks the
binary to `~/.local/bin/jetbrains-toolbox`.

**Archive structure and strip_components (fixed 2026-06-09):**

The Toolbox tarball has two wrapper levels before the actual files:

```
jetbrains-toolbox-3.5.0.84344/
  bin/
    jetbrains-toolbox   ← binary
    jre/                ← bundled JRE — required
    lib/
    ...
```

`--strip-components=2` drops both wrapper levels so everything lands flat in
`~/.local/share/jetbrains-toolbox/`. An earlier version used `bin_pick` which extracted
only the binary, silently leaving the JRE behind — Toolbox launched but immediately failed
with `Cannot load libjvm.so` because it looks for `jre/` relative to its own path.

```toml
[packages.jetbrains-toolbox]
method           = "archive"
check_path       = "~/.local/share/jetbrains-toolbox/jetbrains-toolbox"
download_url     = "https://download.jetbrains.com/toolbox/jetbrains-toolbox-{version}.tar.gz"
extract_to       = "~/.local/share/jetbrains-toolbox"
install_dir      = "~/.local/share/jetbrains-toolbox"
strip_components = 2
symlinks         = [{ src = "jetbrains-toolbox", dst = "jetbrains-toolbox" }]
```

`version_cmd` queries the JetBrains releases API for the current build string (JetBrains
dropped the versionless URL in favour of versioned filenames like `jetbrains-toolbox-3.5.0.84344.tar.gz`).

**After install:** run `jetbrains-toolbox` to open the GUI and install IDEs. Toolbox then
self-manages IDE installs and updates. No further `inv` tasks needed for IDEs.

**Data directory:** `~/.local/share/JetBrains/` (~12 GB) — contains IDE local history,
caches, and plugin state. Kept intentionally across reinstalls.

### PyCharm Professional

Install via JetBrains Toolbox (see above). The snap version (`pycharm-professional`) has a
known Wayland issue on Ubuntu 24.04 — it starts but fails to flush the Wayland display
socket, producing a flood of `Wayland display error flushing data out to the server` warnings
and showing no window. The Toolbox-installed version does not have this problem.

If the snap is still present: `sudo snap remove pycharm-professional` once the Toolbox
version is confirmed working.

**AppArmor sandbox warning (Ubuntu 24.04):**

After installing via Toolbox, PyCharm shows:

> The system restricts the embedded browser from running with the sandbox enabled.
> A corresponding AppArmor profile must be installed to start the browser sandboxed.

This is caused by `kernel.apparmor_restrict_unprivileged_userns = 1`, which Ubuntu 24.04
sets by default. The Chromium sandbox that PyCharm's embedded browser (JCEF) uses requires
unprivileged user namespaces.

Fix: `inv system.apparmor-profiles` — this is also called automatically by `inv setup`
after `inv tools.install`. Two AppArmor profiles are installed to `/etc/apparmor.d/jbr-cef`:

- `jbr_pycharm` — targets the `pycharm` binary; `flags=(unconfined)` so it only adds
  `userns` without restricting the process
- `jbr_cef` — targets `cef_server`, the Chromium subprocess the IDE spawns

Both use `include if exists <local/chrome>` so any site-local Chrome rules are inherited
if that file is ever created (e.g. by installing Google Chrome's AppArmor profile).

### Font configuration

JetBrains IDEs do not pick up the system monospace font. For PyCharm, run:

```shell
inv ide.pycharm-configure
```

This copies `config/pycharm/editor-font.xml` and `config/pycharm/terminal-font.xml` into
the active PyCharm config directory (`~/.config/JetBrains/PyCharm*/options/`). Settings
applied: CaskaydiaCove Nerd Font (editor) and CaskaydiaCove NFM (terminal), 12pt, 1.1 line
spacing, ligatures enabled. The task globs `PyCharm*` and picks the most recent version
directory, so it survives version upgrades.

For other JetBrains IDEs (IntelliJ, GoLand, etc.), set manually:
**Settings → Editor → Font → Font:** `CaskaydiaCove Nerd Font Mono`, size 12.

---

## Terminal emulators

Two terminal emulators are configured in PULSE. Both use CaskaydiaCove Nerd Font Mono 12
and have their configs tracked in the repo.

### WezTerm

GPU-accelerated terminal with native Lua config, split panes, tabs, and SSH multiplexing.

**Install:** `inv apt.deb` — method `deb-github`, nightly rolling release from `wez/wezterm`.

**Config:** `config/wezterm.lua` — copied to `~/.config/wezterm/wezterm.lua` on first install.
Features:
- CaskaydiaCove NFM, 12pt
- Startup: maximized window, two equal vertical panes (right pane active)

**Updates:** `inv apt.upgrade-debs` re-downloads and reinstalls all `deb-github` packages
including wezterm nightly (see [index.md](index.md) — Maintenance).

**Package note:** the nightly release is tagged `nightly` with asset
`wezterm-nightly.Ubuntu24.04.deb`. The installed package name is `wezterm-nightly`; the
binary installs as `/usr/bin/wezterm`.

### Terminator

Classic GTK terminal with split panes, profiles, and GNOME integration.

**Install:** `inv apt.base` — method `apt`.

**Config:** `config/terminator.conf` — copied to `~/.config/terminator/config` on first
install. Profile settings:
- CaskaydiaCove Nerd Font Mono 12
- Infinite scrollback
- Purple title bar (`#613583`) — Adwaita-compatible accent, easy on the eyes
