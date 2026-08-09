# GNOME extensions

> **Citrix Workspace breaks all user extensions.** `icaclient`'s "AppProtection" module installs a
> *mandatory* dconf policy (`/etc/dconf/db/local.d/00-extensions` + a lock on
> `enabled-extensions`/`disable-user-extensions`) that hard-locks GNOME to only the
> `screen-capture-protection@citrix.com` extension. Once active, `gsettings`/`dconf`/
> `gnome-extensions enable` all silently no-op — `gsettings set ... enabled-extensions` returns
> `"The key is not writable"`. None of the `inv gnome.*` tasks can override a locked mandatory key.
> Citrix's own uninstaller only *enables* the cleanup service for the next boot, so after
> `inv apt.uninstall citrix-workspace` you need a full **reboot** (not just logout/login) before
> extensions work again. `citrix-workspace`'s `cleanup_paths` also removes the mandatory lock file
> directly (`/etc/dconf/db/local.d/locks/extensions-mandatory`) and runs `dconf update`, which is
> what let extensions become writable again immediately on 2026-08-08 without waiting for a
> reboot. See [citrix.md](citrix.md) — Citrix is currently uninstalled (paused, not abandoned).

## Ubuntu 24.04

Extensions are installed via **gext** (`gnome-extensions-cli`) — a Python CLI that queries
extensions.gnome.org directly. No browser extension or native host connector required.

All extensions are declared in `setup.toml` under `method = "gnome-extension"`. The key commands:

```shell
inv python.tools       # installs gext if not already present
inv gnome.extensions   # install + enable all enabled = true entries; handles conflicts; applies dconf config
inv gnome.enable       # re-enable installed extensions without reinstalling (use when extensions go inactive)
inv gnome.configure    # re-apply dconf settings without reinstalling (idempotent)
inv gnome.status       # diagnostic: show active state + setup.toml alignment
inv gnome.clean        # remove user extensions not in enabled set
inv gnome.update       # update all gext-managed extensions
```

**Why extensions go inactive:** A `gnome-shell` package update can change the minor version,
causing extensions that don't declare the new version as compatible to be auto-disabled. Run
`inv gnome.status` to see which extensions are affected, then `inv gnome.enable` to re-enable
them (or `inv gnome.update` if the extension needs an updated release), and logout/login to
activate. If all user extensions vanished at once, check `gsettings get org.gnome.shell
disable-user-extensions` — `inv gnome.enable` will fix it if it's `true`.

Newly installed or updated extensions activate after logout/login (no shell restart on Wayland).

---

### Extension types

GNOME Shell loads extensions from two locations. Understanding the distinction matters because
`inv gnome.clean` only touches the user directory.

#### System extensions — `/usr/share/gnome-shell/extensions/`

Owned by Ubuntu apt packages. Cannot be removed without purging those packages. PULSE does not
install or remove these; `inv gnome.clean` leaves them untouched.

| UUID | State | apt package | Role |
|---|---|---|---|
| `ubuntu-appindicators@ubuntu.com` | **ACTIVE** | `gnome-shell-extension-appindicator` | AppIndicator/KStatusNotifierItem tray icons — keep enabled |
| `ubuntu-dock@ubuntu.com` | INITIALIZED | `gnome-shell-extension-ubuntu-dock` | Ubuntu dock — disabled automatically by `inv gnome.extensions` when dash-to-panel is active |

#### Apt-package extensions — `gnome-shell-extensions`

The upstream GNOME team ships a curated set of extensions as the `gnome-shell-extensions` apt
package. Not currently installed on this machine. Listed here to document evaluation decisions —
most are covered by better gext alternatives.

To reinstall: `sudo apt install gnome-shell-extensions` (puts them in
`/usr/share/gnome-shell/extensions/`).

| UUID | EGO | Notes | Verdict |
|---|---|---|---|
| `apps-menu@...gcampax...` | [#6](https://extensions.gnome.org/extension/6/) | GNOME 2-style category launcher in the panel | Skip — Super search and dash-to-panel cover this |
| `auto-move-windows@...gcampax...` | [#16](https://extensions.gnome.org/extension/16/) | Rule-based workspace assignment on app launch | Skip — superseded by `smart-auto-move` (in setup.toml) |
| `drive-menu@...gcampax...` | [#7](https://extensions.gnome.org/extension/7/) | Removable drive eject menu in the panel | Skip — Quick Settings → Removable Storage covers this |
| `horizontal-workspaces@...gcampax...` | [#12](https://extensions.gnome.org/extension/12/) | Arranges workspaces in a horizontal strip | **Incompatible with GNOME 46** |
| `launch-new-instance@...gcampax...` | [#600](https://extensions.gnome.org/extension/600/) | Clicking a dock icon always opens a new window instead of focusing existing | Skip — niche; default focus behaviour is fine |
| `native-window-placement@...gcampax...` | [#18](https://extensions.gnome.org/extension/18/) | Tighter, proportional window thumbnails in Activities overview | Mild improvement; low priority |
| `places-menu@...gcampax...` | [#8](https://extensions.gnome.org/extension/8/) | Bookmarked folder quick-access from the panel | Skip — Files sidebar covers this |
| `screenshot-window-sizer@...gcampax...` | [#881](https://extensions.gnome.org/extension/881/) | Resize focused window to standard screenshot dimensions | Skip — niche tool for GNOME app developers |
| `user-theme@...gcampax...` | [#19](https://extensions.gnome.org/extension/19/) | Allows loading a custom GNOME Shell theme from `~/.themes/` | **Enable if theming** — required prerequisite for any Shell theme |
| `window-list@...gcampax...` | [#602](https://extensions.gnome.org/extension/602/) | Bottom taskbar showing open windows | Skip — fully replaced by dash-to-panel |
| `windowsNavigator@...gcampax...` | [#10](https://extensions.gnome.org/extension/10/) | Number-key window selection in Activities overview | Skip — niche; keyboard nav in overview already works |
| `workspace-indicator@...gcampax...` | [#21](https://extensions.gnome.org/extension/21/) | Workspace number in the top bar | Skip — replaced by `space-bar` (in setup.toml) |

**Worth reconsidering:** `user-theme` is the only one that has no gext equivalent and may be
needed later if you apply a custom Shell theme. If that comes up, reinstall the package and
add it to `setup.toml`.

#### User extensions — `~/.local/share/gnome-shell/extensions/`

Installed by gext (or left over from old installs). Owned entirely by PULSE.
`inv gnome.extensions` installs declared extensions here.
`inv gnome.clean` removes every directory not matching an `enabled = true` UUID in `setup.toml`.

---

### PULSE-managed extension list

All entries below have a `[packages.gnome-ext-*]` section in `setup.toml`. Set `enabled = true`
and run `inv gnome.extensions` to install and activate. Currently 12 `enabled = true`,
10 `enabled = false` (22 total).

#### Currently active

All 12 confirmed active as of 2026-06-09:

| UUID | EGO | setup.toml key | Notes |
|---|---|---|---|
| `dash-to-panel@jderose9.github.com` | [#1160](https://extensions.gnome.org/extension/1160/) | `gnome-ext-dash-to-panel` | Merges top bar and dock into a single Windows-style taskbar |
| `extension-list@tu.berry` | [#3088](https://extensions.gnome.org/extension/3088/) | `gnome-ext-extension-list` | Toggle extensions from a top-bar dropdown without opening Settings |
| `lockkeys@vaina.lt` | [#36](https://extensions.gnome.org/extension/36/) | `gnome-ext-lockkeys` | CapsLock / NumLock state in top bar — defaults fine (`style=both`, always-on) |
| `tophat@fflewddur.github.io` | [#5219](https://extensions.gnome.org/extension/5219/) | `gnome-ext-tophat` | CPU/mem/net sparklines + disk I/O; no extra deps |
| `Vitals@CoreCoding.com` | [#1460](https://extensions.gnome.org/extension/1460/) | `gnome-ext-vitals` | Hardware sensors: CPU/GPU temps, load average; redundant readings disabled via dconf |
| `tilingshell@ferrarodomenico.com` | [#7065](https://extensions.gnome.org/extension/7065/) | `gnome-ext-tiling-shell` | Snap zones + custom grid layouts; Super+Arrow moves windows between tiles; Wayland-native. `inv gnome.extensions` auto-disables `tiling-assistant@ubuntu.com` (confirmed conflict on fresh Ubuntu 24.04 installs — gsettings key collision). Its own `override-alt-tab` setting conflicts with AATWS (see below) and is disabled via dconf. |
| `advanced-alt-tab@G-dH.github.com` | [#4412](https://extensions.gnome.org/extension/4412/) | `gnome-ext-aatws` | Replaces Alt+Tab/Super+Tab with a searchable, filterable switcher — type to find running windows by title; actively maintained for GNOME 46–50. Replaces Switcher (maintainer inactive). Tiling Shell's `override-alt-tab` (default on) monkey-patches the same native `WindowSwitcherPopup.show` and crashes it with `TypeError: this._switcherList is null`, breaking Alt+Tab entirely — confirmed conflict, fixed by setting `gnome-ext-tiling-shell`'s dconf `override-alt-tab` to `false` in `setup.toml`. |
| `clipboard-indicator@tudmotu.com` | [#779](https://extensions.gnome.org/extension/779/) | `gnome-ext-clipboard-indicator` | Clipboard history in the top bar; Ctrl+F9. Works on Wayland via shell extension privilege. |
| `smart-auto-move@khimaros.com` | [#4736](https://extensions.gnome.org/extension/4736/) | `gnome-ext-smart-auto-move` | Learns and restores window positions/workspaces across sessions. |
| `caffeine@patapon.info` | [#517](https://extensions.gnome.org/extension/517/) | `gnome-ext-caffeine` | Panel toggle to prevent screen lock/suspend; auto-activates in fullscreen. |
| `just-perfection-desktop@just-perfection` | [#3843](https://extensions.gnome.org/extension/3843/) | `gnome-ext-just-perfection` | GUI for all GNOME Shell UI tweaks: Activities button, clock position, hot corners, animations. |
| `space-bar@luchrioh` | [#5090](https://extensions.gnome.org/extension/5090/) | `gnome-ext-space-bar` | Named i3-style workspace bar replacing the dot indicator; pairs with dash-to-panel. |

**Applied dconf configuration** (stored in `setup.toml`, applied by `inv gnome.extensions` / `inv gnome.configure`):

| Extension | Key | Value |
|---|---|---|
| dash-to-panel | `panel-size` | `28` |
| tophat | `show-disk` | `true` |
| tophat | `mount-to-monitor` | `'/'` |
| tophat | `fs-hide-in-menu` | `'/boot'` |
| tophat | `refresh-rate` | `'slow'` |
| vitals | `show-processor` | `false` — Top Hat handles CPU |
| vitals | `show-memory` | `false` |
| vitals | `show-network` | `false` |
| vitals | `show-fan` | `false` — IT8628E ACPI-blocked on this hardware |
| vitals | `show-voltage` | `false` |
| vitals | `show-storage` | `false` |
| vitals | `show-gpu` | `false` |
| vitals | `hot-sensors` | `['_temperature_gpu_', '_temperature_processor_0_', '_system_load_1m_']` |

> **dash-to-panel `panel-element-positions`** (clock centering, element order) contains the
> monitor serial ID (`SAM-0x01000e00`) — machine-specific, not stored in `setup.toml`. Set via
> the extension Prefs dialog after each new install.

> **Vitals sensors (this machine):** `hot-sensors` is pre-populated with GPU temp, CPU Package
> temp, and 1-min load average. On a new machine with different hardware, sensor IDs may differ —
> open the Vitals dropdown, right-click desired readings to pin them, then read back the IDs via
> `dconf read /org/gnome/shell/extensions/vitals/hot-sensors` and update `setup.toml`.

> **Freon (`gnome-ext-freon`)** is kept `enabled = false` — Vitals is a strict superset
> (adds voltage, more temps, storage) with 10× the install base.

#### Not installed — disabled in setup.toml

These 3 extensions are `enabled = false` in `setup.toml` and not on disk. Enable individually
if needed; `inv gnome.extensions` will install and activate.

| UUID | EGO | setup.toml key | Notes |
|---|---|---|---|
| `freon@UshakovVasilii_Github.yahoo.com` | [#841](https://extensions.gnome.org/extension/841/freon/) | `gnome-ext-freon` | Superseded by Vitals — keep disabled; confirmed GNOME 46-compatible (extension supports Shell 45-50) |
| `gTile@vibou` | [#28](https://extensions.gnome.org/extension/28/) | `gnome-ext-gtile` | Keyboard-driven tiling grid overlay. **→ retired** — replaced by Tiling Shell. |
| `switcher@landau.fi` | [#973](https://extensions.gnome.org/extension/973/) | `gnome-ext-switcher` | Combined app launcher + window switcher. **→ retired** — original maintainer inactive (no maintainer-authored commits since 2023); GNOME 47 fix was community-contributed. Replaced by AATWS. |

#### Not yet installed — evaluated, pending decision

All are in `setup.toml` with `enabled = false`. GNOME 46 compatible.

| UUID | EGO | setup.toml key | Popularity | Assessment |
|---|---|---|---|---|
| `system-monitor-next@paradoxxx.zero.gmail.com` | [#3010](https://extensions.gnome.org/extension/3010/) | `gnome-ext-system-monitor-next` | 391K DL, 293★ | Alternative to Top Hat — older C-based architecture, requires `gir1.2-gtop-2.0` + `gir1.2-nm-1.0`. No reason to use over Top Hat. **→ skip** — tophat + vitals cover all system monitoring needs. |
| `light-dict@tuberry.github.io` | [#2959](https://extensions.gnome.org/extension/2959/) | `gnome-ext-light-dict` | 7K DL, 41★ | Popup on mouse text selection: dictionary lookup, translate, custom shell commands. Very low adoption. **→ skip** — too niche. |

#### Worth enabling

All entries below are in `setup.toml` with `enabled = false`. Enable via the usual workflow.

| UUID | EGO | setup.toml key | Popularity | Assessment |
|---|---|---|---|---|
| `blur-my-shell@aunetx` | [#3193](https://extensions.gnome.org/extension/3193/) | `gnome-ext-blur-my-shell` | 4.8M DL, 2k★ | Frosted blur on the top panel, overview, dash, and lockscreen. Purely cosmetic — near-zero performance impact on modern hardware. Most-installed GNOME extension by raw numbers. **→ defer** — may try later. |

**Phone integration:**

| UUID | EGO | setup.toml key | Popularity | Assessment |
|---|---|---|---|---|
| `gsconnect@andyholmes.github.io` | [#1319](https://extensions.gnome.org/extension/1319/) | `gnome-ext-gsconnect` | 2.6M DL, 3.7k★ | KDE Connect for GNOME — clipboard sync, file transfer, notification mirroring, SMS from desktop, media control. No KDE runtime needed. Integrates with Nautilus and Chrome/Firefox. Add if you use Android alongside the workstation. **→ skip for now** |

**Quality of life:**

| UUID | EGO | setup.toml key | Popularity | Assessment |
|---|---|---|---|---|
| `nightthemeswitcher@romainvigier.fr` | [#2236](https://extensions.gnome.org/extension/2236/) | `gnome-ext-night-theme-switcher` | 331K DL | Auto-switches dark/light colour scheme at sunset/sunrise — GNOME 46 has the toggle but no time-based automation. Can run custom commands on switch to sync terminal/editor themes. **→ skip for now** |
| `quick-settings-tweaks@qwreey` | [#5446](https://extensions.gnome.org/extension/5446/) | `gnome-ext-quick-settings-tweaker` | 393K DL, 590★ | Adds media controls, notification list, and per-app volume mixer to the Quick Settings popup. Fills the gap GNOME 46's sparse system tray leaves. Verify the specific version matches GNOME 46 before enabling. **→ skip for now** |

---

### Dropped / superseded

Extensions that were evaluated and ruled out. Not in `setup.toml`.

| Old extension | EGO | Verdict |
|---|---|---|
| `arc-menu` (old, fishears) | — | Abandoned — built-in `Super` launcher + dash-to-panel covers app launching |
| `disconnect-wifi` | #904 | Low value — Quick Settings → Wi-Fi toggle (two clicks) already covers it |
| `show-ip` (old, sgaraud) | — | Abandoned — `ip -br a` in terminal; low value for a panel indicator |
| `SimpleWeather` | #8261 | Deferred — requires OpenWeatherMap API key; evaluate separately if wanted |
| `extensions@abteil.org` (petres) | — | Abandoned (stuck at GNOME 3.34) — replaced by Extension List (#3088) |
| `sound-output-device-chooser` | — | Superseded — Quick Settings volume dropdown now shows output device switcher inline |
| `remove-dropdown-arrows` | — | Superseded — arrows removed from GNOME 40 onward, no extension needed |
| `netspeed` | — | Superseded — GNOME 46 incompatible; use Top Hat or Vitals instead |
| `timezone@jwendell` | — | Abandoned — GNOME 46 incompatible |
| `appindicatorsupport@rgcjonas.gmail.com` | [#615](https://extensions.gnome.org/extension/615/) | Superseded — `ubuntu-appindicators@ubuntu.com` system extension (pre-installed, ACTIVE) covers AppIndicator/KStatusNotifierItem tray icons identically. No need to install a user-space duplicate. |
| `paperwm@paperwm.github.com` | [#6099](https://extensions.gnome.org/extension/6099/) | Different paradigm — scrollable infinite canvas of windows per workspace; 4.2k⭐, actively maintained, GNOME 46+Wayland fine. Not in `setup.toml` — only worth adding if you want a full tiling WM lifestyle change. |
| `switcher@landau.fi` | [#973](https://extensions.gnome.org/extension/973/) | Maintainer inactive since 2023; GNOME 47 fix was community-contributed; 37 open issues untriaged. Replaced by AATWS (#4412). |

### Browser-based install (alternative)

If you prefer the extensions.gnome.org web UI, install the native host connector:

```shell
sudo apt install -y gnome-browser-connector
```

Then use the Chrome extension:
<https://chromewebstore.google.com/detail/gnome-shell-integration/gphhapmejobijbbhgpjhcjognlahblep>

Note: `gnome-browser-connector` is disabled in `setup.toml` by default since gext covers the
same function without requiring a browser.
