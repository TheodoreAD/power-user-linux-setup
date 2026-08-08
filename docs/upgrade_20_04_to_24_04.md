# Ubuntu 20.04 → 24.04 Upgrade Tracker

Goal: upgrade the machine from Ubuntu 20.04 LTS (Focal Fossa) to 24.04 LTS (Noble Numbat),
then install Webex and Citrix Workspace.

---

## Upgrade path

Direct 20.04 → 24.04 is **not supported**. You must hop through 22.04:

```
20.04 (Focal) → 22.04 (Jammy) → 24.04 (Noble)
```

Each hop uses `sudo do-release-upgrade` and requires a reboot between steps.

---

## Inventory (captured 2026-06-07)

### External repos / PPAs

#### Active and clean (kept)

| Repo | Format | Notes |
|---|---|---|
| Claude Desktop | modern `signed-by` | `claude-desktop.list` |
| GitHub CLI | modern `signed-by` | `github-cli.list` — GPG key was expired, refreshed 2026-06-07 |
| Google Chrome | modern DEB822 | `google-chrome.sources` — Chrome auto-upgraded its own file to new format |
| Google Cloud SDK | modern `signed-by` | `google-cloud-sdk.list` |

#### Removed — to re-add with modern `signed-by` format after upgrade

| Repo | Reason removed | Original entry |
|---|---|---|
| Bazel | old style, no `signed-by` | `deb [arch=amd64] https://storage.googleapis.com/bazel-apt stable jdk1.8` |
| Docker | old style, no `signed-by`; was in `sources.list` | `deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable` |
| Hashicorp (Terraform) | old style, no `signed-by`; was in `sources.list` | `deb [arch=amd64] https://apt.releases.hashicorp.com focal main` |
| Microsoft Edge | old style, auto-configured file | `deb [arch=amd64] https://packages.microsoft.com/repos/edge/ stable main` |
| NordVPN | old style, no `signed-by` | `deb https://repo.nordvpn.com//deb/nordvpn/debian stable main` |

#### Removed — not needed

| Repo | Reason |
|---|---|
| Microsoft (prod) | Fully commented out — targeted Ubuntu 19.10, disabled on upgrade to focal |
| Sidekick Browser | Fully commented out — duplicate Chrome entry, previously disabled to avoid conflict |
| fta/gnome3 (eoan) | Dead PPA, targeted Ubuntu 19.10 |
| tkashkin/gamehub (eoan) | Dead PPA, targeted Ubuntu 19.10 |

> To re-add Docker with modern format after reaching 24.04:
> ```shell
> curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
> echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu noble stable" | sudo tee /etc/apt/sources.list.d/docker.list
> ```
> NordVPN provides its own installer: `sh <(curl -sSf https://downloads.nordvpn.com/apps/linux/install.sh)`

### Installed applications inventory (captured 2026-06-07)

#### ~~Must remove~~ — removed 2026-06-07

| Package | Reason |
|---|---|
| `python2.7` `python2.7-dev` `python-is-python2` `python-openssl` | Python 2 EOL; `python-is-python2` conflicts with Python 3 default in 24.04 |
| `dotnet-sdk-3.1` | EOL since Dec 2022; 24.04 ships .NET 8 |
| `packages-microsoft-prod` | Targeted Ubuntu 19.10 |
| `gir1.2-clutter-1.0` | Not available in 24.04 repos |
| `resolvconf` | Superseded by `systemd-resolved` in 24.04 |
| `dstat` | Renamed to `dool`/`pcp-dstat` in 24.04 |

#### ~~From repos removed~~ — removed 2026-06-07 (except Edge)

| Package | Notes |
|---|---|
| `grafana` 6.6.2 | Re-add via official Grafana repo after upgrade if still needed |
| `influxdb` 1.7.10 | Re-add via official InfluxDB repo after upgrade if still needed |
| `nordvpn` 5.0.0 | Reinstall fresh after upgrade using NordVPN's own installer |
| `franz` | Also removed `/opt/Franz` |
| `com.github.tkashkin.gamehub` | From dead eoan PPA |
| `nuitka` | — |
| `lynx` `links` `w3m` | — |
| Cisco AnyConnect | Ran `/opt/cisco/anyconnect/bin/anyconnect_uninstall.sh`; cleaned up residual `/opt/cisco` |

#### Decide — old drivers

| Package | Issue |
|---|---|
| `nvidia-driver-470` | Released 2021; 24.04 ships 550+ series. Upgrader should handle automatically |

#### Decide — applications (keep or drop?)

| Package / App | Where | Notes |
|---|---|---|
| `microsoft-edge-dev` | apt | Repo removed, no updates; kept for now |
| `balena-etcher` | apt | ISO flashing tool |
| `gimp` | apt | Image editor |
| `httperf` | apt | HTTP benchmarking |
| `innoextract` | apt | Windows installer extractor |
| `figlet` | apt | ASCII art |
| `apache2-utils` | apt | HTTP tools (ab, htpasswd etc) |
| `yodl` | apt | Documentation preprocessor |
| `dev-sync` | `/opt/dev-sync` | Unknown — what is this? |
| Discord | desktop entry | Installed outside apt |

#### Slate for removal — post-upgrade cleanup

**PDF viewer** — browsers handle PDFs natively now

| Package | How to remove |
|---|---|
| `qpdfview` | `sudo apt purge qpdfview` |

**GOG games** — installed via GOG offline installers; each has its own uninstaller

| Game | Install location | Size | How to remove |
|---|---|---|---|
| SteamWorld Dig | `~/GOG Games/SteamWorld Dig/` | 78MB | Run `~/GOG\ Games/SteamWorld\ Dig/uninstall-SteamWorld\ Dig.sh`; delete dir; remove `.desktop` files from `~/.local/share/applications/`, `~/.gnome/apps/`, `~/Desktop/` |
| Blackwell Legacy | `~/GOG Games/` (desktop files only — may not be fully installed) | unknown | Remove `.desktop` files from `~/.local/share/applications/`, `~/.gnome/apps/`, `~/Desktop/` |
| Blake Stone: Aliens of Gold | same | unknown | same |
| Not A Hero | same | unknown | same |
| Tales of MajEyal | same | unknown | same |
| Unepic | same | unknown | same |

**Steam games and runtimes** — remove via Steam GUI (Library → right-click → Uninstall) or delete manually

| Game / Runtime | Location | Size | Notes |
|---|---|---|---|
| Soda Dungeon 2 | `~/.steam/debian-installation/steamapps/common/Soda Dungeon 2/` | 370MB | Actual game; remove via Steam or delete dir + `appmanifest_2348590.acf` |
| Proton 8.0 | `~/.steam/debian-installation/steamapps/common/Proton 8.0/` | 2.3GB | Windows compatibility layer; only needed if running Windows games |
| Proton Experimental | `~/.steam/debian-installation/steamapps/common/Proton - Experimental/` | 1.2GB | Same — keep only one Proton version if gaming |
| Steam Linux Runtime 3.0 (sniper) | `~/.steam/debian-installation/steamapps/common/SteamLinuxRuntime_sniper/` | 703MB | Required by Proton — keep if keeping Proton |

> Total recoverable from games: ~4.7GB if all removed

#### Snaps — post-24.04 state

| Snap | Version | Notes |
|---|---|---|
| ~~`pycharm-professional`~~ | — | **Removed 2026-06-09** — Wayland incompatible; replaced by JetBrains Toolbox install (see 8e) |
| `spotify` | 1.2.90 | ✓ |
| `firefox` | 151.0.3 | ✓ |
| `thunderbird` | 140.11.1esr | ✓ |
| `kubectl` | 1.35.5 | ✓ |
| `duf-utility` | v0.6.0 | Disk usage viewer ✓ |
| `mdless` | 1.0.33 | Markdown pager ✓ |
| `gnome-46-2404` | current | Active GNOME runtime for 24.04 ✓ |
| ~~`gnome-3-28-1804`~~ | — | **Removed 2026-06-09** |
| ~~`gnome-3-34-1804`~~ | — | **Removed 2026-06-09** |
| ~~`gnome-3-38-2004`~~ | — | **Removed 2026-06-09** |
| ~~`gnome-42-2204`~~ | — | **Removed 2026-06-09** |

### GNOME extensions

Full extension list, current state, cleanup history, and dconf configuration:
see **[gnome_extensions.md](gnome_extensions.md)**.

**All 12 active as of 2026-06-09:** dash-to-panel, extension-list, lockkeys, tophat, vitals,
tiling-shell, aatws, clipboard-indicator, smart-auto-move, caffeine, just-perfection, space-bar.
See [gnome_extensions.md](gnome_extensions.md).

---

## Checklist

### Phase 1 — Pre-upgrade preparation

- [ ] Back up important data / create a system snapshot
- [ ] Fully update the current system:
  ```shell
  sudo apt update && sudo apt full-upgrade -y && sudo apt autoremove -y
  ```
- [ ] Note any third-party PPAs (`ls /etc/apt/sources.list.d/`) — these will be disabled during upgrade and may need re-adding afterward
- [ ] Install `update-manager-core` if not present:
  ```shell
  sudo apt install -y update-manager-core
  ```
- [ ] Confirm `Prompt=lts` is set in `/etc/update-manager/release-upgrades`

### Config file decisions during upgrade

Decisions made at dpkg prompts during `do-release-upgrade`.

| File | Hop | Choice | Reason |
|---|---|---|---|
| `/etc/sysctl.conf` | 20.04 → 22.04 | **N — kept current** | Current version has IPv6 disabled; new package version removes those lines |
| `/etc/sysctl.conf` | 22.04 → 24.04 | **Y — installed package version** | Accepted the new default; IPv6 disable settings were lost — must re-add manually after upgrade |

**Action required after 24.04 upgrade completes:** re-add IPv6 disable to `/etc/sysctl.conf`:

```shell
sudo tee -a /etc/sysctl.conf > /dev/null <<'EOF'

# Disable IPv6
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv6.conf.lo.disable_ipv6 = 1
EOF
sudo sysctl -p
```

**`/etc/sysctl.conf` diff (20.04 current vs 22.04 package version):**
```diff
12c12
< ##############################################################3
---
> ###################################################################
68,71d67
<
< net.ipv6.conf.all.disable_ipv6 = 1
< net.ipv6.conf.default.disable_ipv6 = 1
< net.ipv6.conf.lo.disable_ipv6 = 1
```

**`/etc/sysctl.conf` diff (22.04 vs 24.04 package version):**
```diff
 #net.ipv6.conf.all.accept_redirects = 0
+#net.ipv4.conf.default.accept_redirects = 0
-#net.ipv4.conf.all.accept_source_route = 0
-#net.ipv6.conf.all.accept_source_route = 0
-#
-net.ipv6.conf.all.disable_ipv6 = 1
-net.ipv6.conf.default.disable_ipv6 = 1
-net.ipv6.conf.lo.disable_ipv6 = 1
```

---

### Phase 2 — Upgrade to 22.04

- [x] Start upgrade (run inside `tmux` if on SSH)
- [x] Completed — now on Ubuntu 22.04.5 LTS (Jammy), kernel 5.15.0-181
- [x] Rebooted
- [x] NVIDIA driver 535.309.01 auto-installed and working
- [x] Cleaned up `.distUpgrade` backup files
- [x] Re-ran full upgrade — system fully current
- [x] Snaps updated (core18 refreshed)
- [x] dpkg clean, no pending upgrades

#### Packages removed by upgrader — action required

| Package | Status | Action |
|---|---|---|
| `nvidia-driver-470` + all nvidia-470 libs | Removed as obsolete | **Install new driver** — see below |
| `libfuse2` | Removed | Reinstall: needed by AppImages and Balena Etcher (`sudo apt install libfuse2`) |
| `dnsutils` (`dig`, `nslookup`) | Auto-replaced by `bind9-dnsutils` | Already available — no action needed |
| `iptraf` | Removed | Replaced by `iptraf-ng` — reinstall if needed |
| `libssl1.1` | Removed | Replaced by OpenSSL 3.0 — some old compiled binaries may break; reinstall from `jammy-security` if needed |
| `lz4` | Removed | Reinstall if needed as standalone compression tool (`sudo apt install lz4`) |
| `libtool` | Removed | Reinstall if building from source (`sudo apt install libtool`) |
| `libfuse2` | Removed | Reinstall for AppImage support (`sudo apt install libfuse2`) |
| `unixodbc` / `odbcinst` | Removed | Reinstall if ODBC database connectivity needed |
| `llvm-10` | Removed | Replaced by LLVM 14 in 22.04 — reinstall with new version if needed |
| `gnome-shell-extension-arc-menu` | Removed — incompatible with GNOME 42 | Reinstall from extensions.gnome.org after upgrade |
| `gnome-shell-extension-disconnect-wifi` | Removed — incompatible | Check GNOME 42 compatibility |
| `gnome-shell-extension-remove-dropdown-arrows` | Removed — incompatible | Check GNOME 42 compatibility |
| `libgl1-mesa-glx:i386` | Removed | May need reinstalling for Steam/Wine 32-bit |
| `lz4` (tool) | Removed | `sudo apt install lz4` if needed |
| `libreoffice-*` Java components | Removed | LibreOffice will reinstall these automatically if LibreOffice is installed |

#### NVIDIA driver — resolved on reboot

Driver 470 was removed as obsolete. On reboot, NVIDIA 535.309.01 was auto-installed and working correctly (`nvidia-smi` confirmed, RTX 3070 Ti active). No manual action was needed.

### Phase 3 — Upgrade to 24.04

- [x] Start upgrade (run inside `tmux` if on SSH)
- [x] `/boot` space freed: removed old 5.11.0-37 kernel; switched initramfs to `xz` compression
- [x] Upgrade completed — 285 packages removed by upgrader (see table below)
- [x] Rebooted
- [x] Verified: Ubuntu 24.04.4 LTS, kernel 6.8.0-124-generic, GNOME 46.0
- [x] NVIDIA 535.309.01 carried over — `nvidia-smi` working, RTX 3070 Ti active
- [x] No failed systemd services, no broken packages, no pending upgrades
- [x] Re-run full upgrade — done 2026-06-08 (21 packages: systemd 255.4-1ubuntu8.16, poppler, python3-pil, libjcat1 deferred/phased)
- [x] Restore `xz` initramfs compression — done 2026-06-08 via `inv system.initramfs-compression`
- [x] Re-add IPv6 disable to `/etc/sysctl.conf` — done 2026-06-08 via `inv system.disable-ipv6`
- [x] Purged `nvidia-driver-470`; marked `nvidia-driver-535` as manually installed to prevent autoremove wiping it; ran `apt autoremove` (also cleaned old kernel headers, pdftk-java, Java runtimes, postgresql-client-14)
- [x] Removed old GNOME snap runtimes: gnome-3-28-1804, gnome-3-34-1804, gnome-3-38-2004, gnome-42-2204
- [x] Removed pyenv fully: `~/.pyenv/` dir, `~/.local/bin/pyenv` symlink, init hooks from `.zshrc`, prompt token in `.p10k.zsh`
- [x] Fixed broken PATH: removed dead `~/.poetry/bin` and `coursier/bin` entries from `.profile` and `.zshrc`; removed dead `poetry` and `thefuck` oh-my-zsh plugins; fixed GOROOT/GOPATH swap bug in `.zshrc`
- [x] Purged Steam, gamemode, all i386 gaming libs (2026-06-08); 75 nvidia i386 libs remain (legitimate)
- [x] Remove dead eoan cdrom entry — done 2026-06-08 (entire `third-party.sources` file removed, it contained only that entry)
- [x] Nerd Fonts: migrated v2 → v3 — done 2026-06-08 (36 legacy spaced-filename v2 files removed; 339 v3 compact-filename files installed across 9 families via `inv fonts.install`)
- [x] p10k baseline config stored in repo as `config/p10k.zsh`; `inv zsh.p10k-configure` installs it on fresh machines — done 2026-06-08
- [x] Re-enable disabled repos — done 2026-06-08 via `inv apt.repos` (see Phase 8a)

**Known 22.04 → 24.04 pitfalls:**
- `webkit2gtk-4.0` removed from default repos (replaced by `webkit2gtk-4.1`); affects Citrix (handled below)
- Some GNOME extensions will break — GNOME version changes from 42 to 46

#### Packages removed by upgrader — 22.04 → 24.04

| Package | Notes |
|---|---|
| `python3.10` + dev/stdlib | 24.04 ships Python 3.12; expected |
| `llvm-14` + dev tools | Replaced by LLVM 18 in 24.04; reinstall if needed: `sudo apt install llvm` |
| `libstdc++-11-dev` | GCC 11 dev removed; GCC 13 is the 24.04 default |
| `libwebkit2gtk-4.0` | Confirmed removed — Citrix workaround required (Phase 5) |
| `gimp-data` | GIMP data removed — check if GIMP itself still works after reboot; may need `sudo apt install gimp` |
| `imagemagick-6-common` + libs | ImageMagick 6 removed; 24.04 has ImageMagick 7 — reinstall with `sudo apt install imagemagick` if needed |
| `pdftk` | PDF toolkit removed — use `pdftk-java` or `ghostscript` as alternatives |
| `libqt5*` (all Qt5 libs) | Qt5 removed; Qt6 is the 24.04 default — apps that required Qt5 may break |
| `pulseaudio-utils` | PulseAudio fully replaced by PipeWire in 24.04; expected |
| `libavcodec58` / `libavformat58` / `libavutil56` | FFmpeg 4.4 libs removed; FFmpeg 6.x in 24.04 |
| `irqbalance` | IRQ balancing daemon removed — reinstall if seeing CPU load imbalance: `sudo apt install irqbalance` |
| `isc-dhcp-client` | DHCP now handled by NetworkManager/systemd-networkd directly; expected |
| `acpi-support` | Legacy ACPI scripts removed; modern systemd handles this |
| `ubuntu-advantage-tools` | Replaced by `ubuntu-pro-client` |
| `libpoppler118` | Old poppler version removed; newer version will be installed |
| `mime-support` | Replaced by `shared-mime-info` |
| `chromium-codecs-ffmpeg-extra` | Was the snap-era codec shim; no longer needed |

### Phase 4 — Install Webex

Supported on Ubuntu 22.04 and 24.04. Ubuntu 20.04 support was dropped after Webex 45.6.

- [ ] Download the `.deb` from the [Webex download page](https://www.webex.com/downloads.html) (Linux section)
- [ ] Install:
  ```shell
  sudo dpkg -i ~/Downloads/Webex.deb
  sudo apt install -f    # fix any missing dependencies
  ```
- [ ] If the app launches but crashes: install the missing OpenGL library:
  ```shell
  sudo apt install -y libgl1-mesa-glx
  ```
- [ ] If AppArmor blocks the app (common on 24.04): create an unconfined profile:
  ```shell
  sudo tee /etc/apparmor.d/local/opt.webex.bin.webex > /dev/null <<'EOF'
  /opt/webex/bin/webex flags=(unconfined) {
  }
  EOF
  sudo apparmor_parser -r /etc/apparmor.d/local/opt.webex.bin.webex
  ```
- [ ] Verify: launch Webex, sign in, test audio/video

### Phase 5 — Install Citrix Workspace ✓

Supported on Ubuntu 20.04, 22.04, and 24.04. Recent versions bundle `webkit2gtk-4.0`
to avoid the 24.04 library-removal issue.

- [x] Installed and verified working — 2026-06-09 (done before this session)
- [x] Uninstalled — 2026-08-08: `icaclient`'s AppProtection module was locking down all GNOME
  Shell extensions system-wide (mandatory dconf lock on `enabled-extensions`), which blocked
  normal desktop development. **Paused, not abandoned** — full status, the AppProtection
  conflict, and how to bring it back are in [docs/citrix.md](citrix.md).

### Phase 6 — Python toolchain: pyenv → uv

The existing guide (`docs/python.md`) is built around pyenv + Poetry + pipx. Switch to `uv` after reaching 24.04. Existing venvs do not need to be migrated.

**What uv replaces:**

| Old tool | uv equivalent |
|---|---|
| `pyenv` (Python version management) | `uv python install`, `uv python pin` |
| `python -m venv` / `pyenv virtualenv` | `uv venv` |
| `pip install` | `uv pip install` |
| `pipx` (isolated global tools) | `uv tool install` |
| `poetry` (project dependency management) | `uv` (has built-in lockfile/project workflow) |

**Install uv:**
```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Guiding principle:** install all Python CLI tools via `uv tool install` — never via apt or pipx. This keeps the Python toolchain fully independent of the system Python and the distro upgrade cycle.

**Tasks:**
- [x] Remove pyenv, poetry, pipx and their shell init hooks from `~/.zshrc` — done 2026-06-07
- [x] Remove `~/.pyenv` directory — done 2026-06-07
- [x] Install uv — done via `bootstrap.sh` (reads Python version from `setup.toml`)
- [x] Reinstall all global Python tools via `uv tool install` — done via `inv python.tools`:
  - `nox`, `mkdocs` (+ `mkdocs-material`), `twine`, `glances`, `nuitka`, `zensical` (invoke is in bootstrap.sh)
- [x] Update `docs/python.md` — fully rewritten for uv workflow
- [x] Nuitka — added as `uv tool install nuitka` in `setup.toml`
- [x] Remove the pip global config — done 2026-06-08: `rm ~/.config/pip/pip.conf` (had legacy `wheel-dir`/`find-links` settings from an old offline-install workflow; uv does not read pip.conf)

### Phase 7 — Node.js toolchain ✓

Was: `nodejs` 18.19.1 (apt, EOL), `nodejs-doc`, orphaned `/usr/local/bin/{npm,npx,fkill}` symlinks
and `/usr/local/lib/node_modules/{npm,fkill-cli}` from a manually installed npm@7.

**Tasks:**
- [x] Purge apt packages and orphaned globals — done 2026-06-08
- [x] `inv node.install` — done 2026-06-08: nvm to `~/.local/share/nvm`, Node v24.16.0 LTS
- [x] `inv zsh.configure` — done 2026-06-08: `NVM_DIR` in `~/.zshenv` + `~/.zshrc`; omz `nvm` plugin owns loading and completion; `PROFILE=/dev/null` prevents nvm install script from touching shell files

### Phase 8 — Post-upgrade cleanup

#### 8a — Repos: re-enable and re-add ✓

- [x] All repos re-enabled — done 2026-06-08 via `inv apt.repos`
  - Deleted stale `.distUpgrade` files; `inv apt.repos` rewrote all sources with modern `signed-by` format
  - Installed: kubectl, microsoft-edge-stable, VS Code (deb)
  - helm and tilt moved from `apt-repo` to `archive` method (their apt repos were dead/broken)
  - Chrome moved from `apt-repo` to `deb-url` (Chrome self-manages its own `google-chrome.sources`)
  - NordVPN and Bazel dropped — no longer needed

#### 8b — Go update ✓

- [x] Old install (1.16.2, 2021) removed 2026-06-08
- [x] Go 1.26.4 installed — confirmed working (`go version go1.26.4 linux/amd64`)

#### 8c — GNOME extensions

All old extensions were installed via apt or git clone against GNOME 3.36 and are gone after
the upgrade. Full extension research and the current list live in **`docs/gnome_extensions.md`**.

Extensions are declared in `setup.toml` as `method = "gnome-extension"` entries and installed via:

```shell
inv python.tools        # installs gext (gnome-extensions-cli) if missing
inv gnome.extensions    # installs and enables all enabled = true entries; fixes disable-user-extensions; handles conflicts
inv gnome.status        # diagnostic: GNOME version, dconf flags, per-extension active/installed/missing/blocked state
inv gnome.clean         # remove user extensions not matching enabled=true UUIDs in setup.toml
inv gnome.update        # update all gext-managed extensions
```

22 extensions declared in `setup.toml` (currently 12 `enabled = true`, 10 `enabled = false`).
Full evaluations, current state, dconf config, and extension selection guide: **`docs/gnome_extensions.md`**.

- [x] ✓ **2026-06-09** — `gnome-extensions-cli` (gext) installed via `inv python.tools`
- [x] ✓ **2026-06-09** — `tasks/gnome.py` written: `inv gnome.extensions` (install+enable+dconf), `inv gnome.configure` (dconf only), `inv gnome.status` (diagnostic), `inv gnome.clean` (remove unmanaged), `inv gnome.update`
- [x] ✓ **2026-06-09** — `inv gnome.extensions` handles `ubuntu-dock` conflict automatically; clears `disable-user-extensions = true` (Ubuntu default that silently blocks all user extensions)
- [x] ✓ **2026-06-09** — `inv gnome.clean` ran; 6 dead GNOME 3.36 extensions removed (5 with setup.toml entries kept)
- [x] ✓ **2026-06-09** — dash-to-panel + extension-list enabled; confirmed active after logout/login
- [x] ✓ **2026-06-09** — lockkeys + tophat + vitals enabled; dconf config applied (see gnome_extensions.md — Currently active); IT8628E SuperIO ACPI-blocked (fans/voltage show as unavailable — see troubleshooting.md)
- [x] ✓ **2026-06-09** — `sensors-detect` ran; coretemp confirmed; Vitals sensors pinned: GPU temp, CPU Package, 1-min load
- [x] ✓ **2026-06-09** — tiling-shell, AATWS, clipboard-indicator, smart-auto-move, caffeine, just-perfection, space-bar enabled; all 12 extensions confirmed active after logout/login (see gnome_extensions.md)

#### 8d — Microsoft Edge: dev → stable ✓

- [x] Profile data copied — 2026-06-08: rsync `~/.config/microsoft-edge-dev/` → `~/.config/microsoft-edge/` excluding all caches (3.3 GB). Both profiles (Profile 3: DoHu, Profile 4: Beltane) and `Local State` transferred. Cookies/local sessions preserved; bookmarks/passwords/extensions also backed by account sync.
- [x] `microsoft-edge-stable` 149.0.4022.52 installed (was already present from `inv apt.repos` in 8a)
- [x] `microsoft-edge-dev` 150.0.4064.2 purged — 2026-06-08

#### 8e — Remaining housekeeping

- [x] Confirmed `Prompt=lts` in `/etc/update-manager/release-upgrades` — 2026-06-08
- [x] Removed all legacy apt keys — done 2026-06-08:
  - Cleared `/etc/apt/trusted.gpg` entirely (9 stale/expired keys: Google×2, Docker, InfluxDB, GitHub CLI×2 expired, HashiCorp×2, Fortinet expired)
  - Removed `/etc/apt/trusted.gpg.d/`: bazel, fta gnome3, google-chrome (redundant), nordvpn×2, sidekick×2, gamehub
  - Removed `/usr/share/keyrings/cloud.google.gpg~` (stale backup)
  - Verified: `sudo apt update` clean, no `NO_PUBKEY` warnings
- [x] Edge dev → stable — done 2026-06-08 (see 8d above)
- [x] Purged `qpdfview` — 2026-06-08 (also removed Qt6 orphans via autoremove)
- [x] Apt cache cleaned — 2026-06-08
- [x] Journal vacuumed to 500MB — freed 3.5GB — 2026-06-08
- [x] `/var/log/martalog` removed — 2026-06-08
- [x] Cap ongoing journal size permanently — done 2026-06-08 via `inv system.journal-size`; journal at 497.4 MB
- [x] Browser caches cleared — 2026-06-08
- [x] Apt sources cleaned — 2026-06-08: removed 3× `.distUpgrade` backups, `microsoft-edge.sources` (Edge self-managed duplicate), `freelens.sources` (invalid leftover). Remaining: `claude-desktop.list`, `docker.list`, `github-cli.list`, `google-chrome.sources`, `hashicorp.list`, `kubernetes.list`, `microsoft-edge.list`, `ubuntu.sources`, `vscode.list`
- [x] pipx fully removed — 2026-06-08: all tools migrated to `uv tool install`; 275MB freed
- [x] NVIDIA driver upgraded — 2026-06-08: `nvidia-driver-535` (proprietary DKMS) → `nvidia-driver-595-open` (open kernel modules, Ubuntu-recommended for Ampere/GA104). Pre-built kernel modules; no DKMS compile step.
- [x] `nomodeset` removed from GRUB — 2026-06-08: was set as the only `GRUB_CMDLINE_LINUX_DEFAULT` value, blocking KMS and causing black screen after login with the new driver. Replaced with `quiet splash` (Ubuntu default). `sudo update-grub` + reboot.
- [x] Switched to Wayland — 2026-06-08: GDM session chooser showed "GNOME on Wayland" once KMS was enabled. RTX 3070 Ti on nvidia-driver-595-open with Wayland confirmed working.
- [x] `~/.local/share/JetBrains` ~12GB — kept intentionally (local history, plugins)
- [x] `pycharm-professional` snap removed — 2026-06-09: Wayland incompatible (display socket flush errors, no window shown); replaced by Toolbox version
- [x] JetBrains Toolbox installed — 2026-06-09: full archive extract via `inv tools.install` (`strip_components=2` to include bundled JRE); symlinked to `~/.local/bin/jetbrains-toolbox`
- [x] PyCharm Professional installed via Toolbox — 2026-06-09: Toolbox manages IDE installs, updates, and settings; no snap required
- [x] PyCharm AppArmor profiles installed — 2026-06-09: `inv system.apparmor-profiles` writes `/etc/apparmor.d/jbr-cef` (two profiles: `jbr_pycharm` + `jbr_cef`); also called automatically from `inv setup` after `inv tools.install`; fixes `kernel.apparmor_restrict_unprivileged_userns=1` sandbox warning

#### 8f — Screenshot tool

**Decision required:** keep the built-in GNOME screenshot tool, or replace it with Flameshot.

| Option | When to choose |
|---|---|
| Keep built-in | PrtSc interactive mode is enough; no annotation needed |
| Replace with Flameshot | You frequently annotate screenshots (arrows, text, blur, crop) for docs or bug reports |

**Correction (2026-08-08):** this phase previously documented disabling 6 keys under
`org.gnome.settings-daemon.plugins.media-keys` (`screenshot`, `screenshot-clip`,
`window-screenshot`, etc.) and installing Flameshot straight from apt with a `QT_QPA_PLATFORM`
`.desktop` patch. Both were wrong for this machine:
- Those media-keys don't exist on GNOME 46 — it moved screenshot bindings to
  `org.gnome.shell.keybindings` and collapsed the save/clipboard split entirely (`screenshot` and
  `screenshot-window` now always do *both* by default). The old gsettings commands here would have
  silently failed ("No such key") had anyone actually run them.
- Flameshot's apt package (`v12.1.0`) hangs indefinitely on every capture on this GNOME
  46/Wayland setup — a real bug in that build, unrelated to the XWayland/`.desktop` issue the old
  Wayland warning here described. Fixed by installing `v14.0.0` from GitHub releases instead (see
  `docs/screen_capture.md` for the full investigation — `busctl`/`gdb` root-caused it to Flameshot's
  own Qt/D-Bus signal handling, not anything on our end).

Full detail, the up-to-date shortcut table, and both root-cause writeups are in
`docs/screen_capture.md`; this phase now just points at the automated tasks.

##### If keeping the built-in — no action needed

Flameshot is in `setup.toml` as `enabled = false` (see `[packages.flameshot]`). Leave it.

##### If replacing with Flameshot

**Step 1 — install:**

```shell
inv apt.base   # installs xdg-desktop-portal-gnome — required for Flameshot (or any
               # portal-based screenshot tool) to capture at all on Wayland; see docs/screen_capture.md
inv apt.deb    # installs Flameshot v14.0.0 from GitHub releases (setup.toml pins the exact
               # release — see the comment above [packages.flameshot] before bumping it)
```

**Step 2 — apply shortcuts and save-path config:**

```shell
inv screenshot.enable
```

This sets Flameshot's `savePath` to `~/Pictures/Screenshots` (matching the built-in tool),
applies the Wayland `.desktop` fix if needed (harmless no-op on v14, which doesn't need it), disables
GNOME's `show-screenshot-ui`/`screenshot` keys, and binds `PrtSc`/`Shift+PrtSc` to Flameshot
(`flameshot gui`/`full -p ~/Pictures/Screenshots -c` — always save *and* clipboard, no dialog,
matching the built-in tool's own behavior). `Alt+PrtSc` is deliberately left on GNOME's native
`screenshot-window` action — it already saves and copies to clipboard by default, and Flameshot has
no active-window capture mode. See `docs/screen_capture.md` for the full shortcut table and the
source-level verification behind it.

Reversible: `inv screenshot.disable` removes the 2 custom bindings and restores GNOME's shipped
defaults via `gsettings reset` (not hardcoded values), so removing Flameshot later needs no manual
gsettings work. `inv screenshot.status` shows current state.

**Step 3 — `setup.toml` already has `[packages.flameshot]` and `[packages.xdg-desktop-portal-gnome]`
enabled** — nothing further needed for future machine setups.

#### 8g — Developer tooling and font configuration

- [x] WezTerm nightly installed — 2026-06-09: `inv apt.deb`; `deb-github` method, tag `nightly`,
  asset `wezterm-nightly.Ubuntu24.04.deb` from `wez/wezterm`; installed version
  `20260607-082427-8afe0ad3`; config at `config/wezterm.lua` → `~/.config/wezterm/wezterm.lua`
  (startup: maximized, two vertical panes)
- [x] Terminator config tracked in repo — 2026-06-09: `config/terminator.conf` → `~/.config/terminator/config`
  via `config_files` mechanism; profiles-only (no global/keybindings/layouts sections); purple
  title bar (`#613583`)
- [x] Font size standardized to 12pt everywhere — 2026-06-09:
  - System monospace: CaskaydiaCove Nerd Font Mono 12
  - GNOME Terminal: 12 (via `inv fonts.configure`)
  - VS Code: `editor.fontSize = 12`, `terminal.integrated.fontSize = 12`
  - Terminator: CaskaydiaCove Nerd Font Mono 12
  - WezTerm: CaskaydiaCove NFM 12
  - PyCharm editor: CaskaydiaCove Nerd Font 12 (via `inv ide.pycharm-configure`)
  - PyCharm terminal: CaskaydiaCove NFM 12 (via `inv ide.pycharm-configure`)
- [x] `inv ide.pycharm-configure` task added — 2026-06-09: copies `config/pycharm/editor-font.xml`
  and `config/pycharm/terminal-font.xml` into active `~/.config/JetBrains/PyCharm*/options/`
  (glob-resolved, survives version upgrades)
- [x] `inv apt.upgrade-debs` task added — 2026-06-09: re-downloads and reinstalls all `deb-github`
  packages (wezterm, etc.); fills the gap left by `apt upgrade` not covering deb-github installs

- [x] Decision made 2026-08-08: replace with Flameshot (annotation editor)
- [x] Installed (v14.0.0 via GitHub releases, not apt — see correction above), shortcuts rebound
  via `inv screenshot.enable`, capture-and-save confirmed working live
- [x] `[packages.flameshot]` and `[packages.xdg-desktop-portal-gnome]` enabled in `setup.toml`
- [x] Confirmed 2026-08-08: clipboard copy (`-c`) works live (pasted a real capture into another
  app) and `Alt+PrtSc` (untouched GNOME native window capture) both work as designed
- [x] Confirmed 2026-08-08: annotation editor (arrows, text, blur, crop) works

#### 8h — Citrix Secure Access VPN

Separate from Citrix Workspace (virtual desktop client). Citrix Secure Access is the SSL VPN
client for connecting to the corporate network via NetScaler Gateway (`myworkspace.rbcvpn.com`).
Full details and troubleshooting log: **[docs/citrix.md](citrix.md)**.

- [x] Researched Linux packages — 2026-06-12: two packages required: `nsginstaller64.deb` (VPN client) and `nsepa.deb` (Endpoint Analysis / device posture checks). Skipped the Citrix Web Browser Extension (1-star reviews, unreliable); standalone client works without it.
- [x] Installed `nsgclient` 25.8.2 + `nsepa` 26.2.3 — 2026-06-12:
  ```shell
  sudo -A apt install -y ~/Downloads/nsginstaller64.deb
  sudo -A apt install -y ~/Downloads/nsepa.deb
  ```
  `apt` pulled in 4 missing deps and silently handled the `resolvconf` → `systemd-resolved` gap. EPA `nsgcepa://` protocol handler registered automatically.
- [ ] **BLOCKED — IT action required**: gateway (`myworkspace.rbcvpn.com`) does not include the session token in the `nsgcepa://` URL for Linux clients. The EPA binary receives `nsgcepa://nsgcepa` with no host/token, logs `URL not present`, and exits — the scan never completes, so the gateway returns "access denied — your device is not compliant". This is a server-side EPA policy gap, not a missing-software problem.
- [x] Uninstalled `nsgclient` + `nsepa` — 2026-08-08: still blocked on IT, and `nsgclient`/`nsepa`
  ride along with Citrix Workspace's AppProtection lock on GNOME extensions. Paused pending the
  gateway fix, not abandoned — `setup.toml` still tracks `citrix-secure-access`/`citrix-epa` with
  `enabled = false` plus a new declarative `cleanup_paths` list (leftover `/opt/Citrix`, logs,
  desktop entries, the `~/.citrix` dir, the broken `/usr/local/bin` symlinks) so
  `inv apt.uninstall <section>` fully reverses a reinstall, not just the dpkg package. See
  [docs/citrix.md](citrix.md) for the up-to-date status.

  **What to tell IT:** The gateway needs a Linux pre-authentication EPA policy that passes the session token in the `nsgcepa://` invocation (`nsgcepa://nsgcepa/epav2plugin/{host}/{token}/`). Alternatively, ask them to switch to post-authentication EPA or whitelist Linux devices.

---

## Status

| Phase | Status |
|---|---|
| 1 — Pre-upgrade prep | complete |
| 2 — Upgrade to 22.04 | complete |
| 3 — Upgrade to 24.04 | complete |
| 4 — Install Webex | not started |
| 5 — Install Citrix Workspace | complete, later uninstalled 2026-08-08 — paused, see [citrix.md](citrix.md) |
| 6 — Python toolchain: pyenv → uv | complete |
| 7 — Node.js toolchain: apt → nvm | complete |
| 8 — Post-upgrade cleanup | in progress — 8f (screenshot tool) resolved 2026-08-08, Flameshot v14.0.0 installed and working; 8h (Citrix VPN) blocked on IT, uninstalled 2026-08-08 |
| PULSE setup | **complete** — all `inv` tasks green, full dry-run ok |

### System state (2026-06-12)

| Item | State |
|---|---|
| Ubuntu version | 24.04.4 LTS (Noble) ✓ |
| Kernel | 6.8.0-124-generic ✓ |
| GNOME | 46.0 ✓ |
| Display session | Wayland (GNOME on Wayland) ✓ |
| NVIDIA | 595.71.05-open — RTX 3070 Ti, Wayland/KMS active ✓ |
| Failed services | None ✓ |
| Broken packages | None ✓ |
| initramfs compression | xz ✓ |
| IPv6 | Disabled ✓ |
| Dead eoan cdrom entry | Removed ✓ |
| Google Chrome repo | Active ✓ (DEB822, self-managed) |
| Third-party repos | All active ✓ — sources cleaned 2026-06-08 |
| DNS | Cloudflare + Google fallback via systemd-resolved ✓ |
| curl defaults | ~/.config/curlrc ✓ |
| Docker daemon.json | Configured ✓ |
| Fonts | CaskaydiaCove Nerd Font Mono 12 — system, GNOME Terminal, VS Code, Terminator, WezTerm, PyCharm ✓ |
| JetBrains Toolbox | Installed ✓ — `~/.local/share/jetbrains-toolbox/` via `inv tools.install` |
| PyCharm Professional | Installed via Toolbox ✓ — Wayland working; AppArmor profiles applied |
| askpass-zenity | Installed ✓ — SUDO_ASKPASS set in ~/.zshenv |
| NordVPN / Bazel | Dropped — no longer needed |
| Old GNOME snaps | Removed ✓ (including pycharm-professional) |
| pyenv | Fully removed ✓ |
| pip.conf | Removed ✓ |
| uv | Installed ✓ — Python 3.11 default, tools migrated |
| PATH | Cleaned ✓ |
| Steam / games / i386 libs | Removed ✓ |
| Node.js | v24.16.0 LTS via nvm ✓ |
| Go | 1.26.4 ✓ |
| GNOME extensions | All 12 ACTIVE ✓ — see [gnome_extensions.md](gnome_extensions.md) |
| Microsoft Edge | Stable ✓ — dev purged 2026-06-08 (**Phase 8d** complete) |
| Citrix Workspace | Uninstalled 2026-08-08 — AppProtection locked all GNOME extensions; paused not abandoned, see [citrix.md](citrix.md) |
| Citrix Secure Access VPN | Uninstalled 2026-08-08 (was `nsgclient` 25.8.2 + `nsepa` 26.2.3) — still blocked on IT (gateway EPA token not issued for Linux); paused not abandoned |

---

## Git history — landing `initial_version` on `master`

All of the PULSE rewrite work above happened on `initial_version` — a branch whose last real
commit was from 2022-07-06, then dormant for four years while this upgrade work continued on it
starting 2026-06-07. Meanwhile `master` was independently rewritten from scratch in Sept–Nov 2024
(commits `da61690`, `fd51827`, `bf5400d`, `d0f193d`, `a68fbc3`, `629a3d5`) — its own mkdocs site,
its own docs set — and neither branch ever saw the other's work. Both traced back to the same
2019-08-02 "Initial commit" (`719a1e2`, just `LICENSE` + `README.md`), so a plain merge would have
tried to reconcile two independent full rewrites against a nearly-empty common ancestor.

**Investigation (2026-08-08)** — found real content on `master` the tracker had never reviewed,
since it only ever looked at `initial_version`'s own docs:

- Two genuine regressions if landed naively: `README.md` still said "Ubuntu 20.04" (never touched
  by the 2026 rewrite) while `master` had already corrected this to 24.04 in 2024; and the docs
  site's `mkdocs.yml`/`requirements-docs.txt` were frozen at a 2021 `mkdocs-material~=7.0` config,
  missing plugins `master` had picked up in 2024 (`mkdocs-awesome-pages-plugin`, `mkdocs-markmap`,
  `pymdownx.snippets`, `pymdownx.progressbar`).
- Four doc pages existed only on `master`, never reviewed: `docs/browsers.md`, `docs/cloud.md`,
  `docs/extras.md`, `docs/kubernetes-server.md`. Assessed and confirmed superseded (Terraform/gcloud
  now automated via `setup.toml`, browsers install via `inv apt.repos`, `kubernetes-server.md`
  duplicates content already deliberately deleted under a different filename) — dropped, not
  carried over.
- Everything else `master` had independently added (`docs/kubernetes-dev.md`, the old EFK/history-
  fix scripts, `poetry.lock`/`pyproject.toml`/`requirements.txt`, old mermaid/tablesort assets) was
  already accounted for by name in this tracker's own deletion decisions, or cleanly superseded.

**Resolution:**
1. New branch `land-on-master` off `initial_version`'s tip, staged PULSE work committed as `b9300b1`.
2. `git merge master -X ours` — auto-resolves every overlapping-content conflict in favor of the
   2026 work (the more recent, actively-verified rewrite) while structurally preserving anything
   `master`-only untouched, since a 3-way merge treats "we never touched that path" as unchanged.
3. Follow-up commit removing the 13 `master`-only files confirmed superseded above, fixing the
   `README.md` regression, and — **user decision, in place of just patching the old mkdocs config**
   — migrating the docs site from `mkdocs-material` to `zensical` (verified drop-in compatible with
   the existing `mkdocs.yml`; see the Docs site entry below and [zensical.md](zensical.md)).
4. Remaining tracker items worked through in the same effort: `glab` automated into `setup.toml`
   (deb-url + a new `{version}`/`version_cmd` extension to `_install_deb_url`, since GitLab releases
   aren't mirrored to GitHub), zsh history hardening (`HIST_FCNTL_LOCK`), the Freon EGO id, the
   `ssh.md` keychain warning removed (verified working), a WSL support module added
   (`inv wsl.check` + [wsl.md](wsl.md)), and the `setup.toml`/tag-system architecture fully
   documented in `docs/index.md` and `setup.toml`'s own header comment.
5. **Memory policy correction:** durable project knowledge (the tag/method architecture findings,
   the WSL module pointer) was briefly saved to Claude Code's cross-session memory system, then
   moved into the repo instead — `AGENTS.md` (actual content, cross-tool standard) + `CLAUDE.md`
   (`@AGENTS.md` import, since Claude Code has no native AGENTS.md support). Version-controlled and
   visible to any contributor or agent tool beats memory hidden in `~/.claude/`.
6. Two further commits from other sessions landed on top of this same branch: a Rust toolchain via
   rustup (`abc1c23` — see docs/rust.md below) and a real fix for the zensical migration (`e959de7`
   — the original migration was only build-clean by accident; see the corrected Docs site entry
   below and [zensical.md](zensical.md)).
7. **Push blocker fixed properly, not routed around:** `git push` failed from Claude Code with
   `Permission denied (publickey)` — this machine's SSH keys are passphrase-protected and
   `keychain` loads them into the agent lazily on first use, and Claude Code's Bash tool has no TTY
   to prompt for that passphrase. Rather than push over HTTPS as a one-off workaround, extended the
   existing `askpass-zenity` helper (already solving the identical problem for `sudo -A`) to also
   serve as `SSH_ASKPASS` (`SSH_ASKPASS_REQUIRE=prefer`, not `force`, so a real interactive
   terminal is unaffected). Verified: `git push` succeeded over the real SSH remote once the
   passphrase was entered in the popped-up dialog. Full writeup, and everything else this repo does
   to make Claude Code work well here, in the new [claude-code.md](claude-code.md).

`initial_version` and the pre-landing `master` history are both left untouched — branches kept for
historical reference, not deleted.

---

## Guide analysis — what needs updating for 24.04

Full read of all docs in this repo. Issues and update tasks recorded here so the guide reflects 24.04 reality post-upgrade.

### docs/zsh.md

Status: ✓ **done 2026-06-09** — fully rewritten for PULSE. All items resolved:

| Issue | Status |
|---|---|
| `thefuck` plugin in Oh-My-Zsh plugins list | ✓ not in rewritten doc — `thefuck` uninstalled pre-upgrade |
| `poetry` plugin in Oh-My-Zsh plugins list | ✓ not in rewritten doc — switched to `uv` |
| `sed` patch to comment out pyenv in `.p10k.zsh` | ✓ removed — pyenv gone |
| No uv shell integration | ✓ **done** — `uv generate-shell-completion zsh` in completions table |
| `xclip` aliases | ✓ **done** — `[packages.clipboard]` uses `wl-clipboard`; Wayland-only, documented |
| No history tuning | ✓ **done 2026-06-09** — `[packages.zsh-history]` in `setup.toml` |
| History corruption recovery script | ✓ **done 2026-06-09** — `inv zsh.history-fix` task |
| Concurrent-session corruption mitigation | ✓ **done 2026-08-08** — `setopt HIST_FCNTL_LOCK` added to `[packages.zsh-history]` and applied live via `inv zsh.configure`. Uses standard `fcntl()` locking instead of zsh's ad-hoc default, closing the "concurrent session race" half of the corruption risk. Power-loss mid-write corruption remains unfixable at the zsh level (upstream limitation) — `inv zsh.history-fix` is still the recovery path for that. Documented in a new "History" section in docs/zsh.md. |
| Evaluate Atuin as history backend | **Decided 2026-08-08 — stick with fzf, defer Atuin.** fzf's Ctrl+R over the native history file is sufficient and adds no daemon/data store. `[packages.atuin]` stays in `setup.toml` with `enabled = false` for future evaluation. **→ future task:** experiment with Atuin (richer Ctrl+R UI, exit codes/duration/cwd per command, optional sync) once there's an actual pain point fzf doesn't cover. To enable: remove `key-bindings.zsh` source from `[packages.fzf]`, set `[packages.atuin] enabled = true`, run `inv tools.install`. |
| fzf integration | ✓ **done 2026-06-09** — fd as default command (Ctrl+T + Alt+C), bat preview for files, ls preview for directories, Ctrl+R preview with Ctrl+/ toggle. |

### docs/git.md

Status: updated 2026-06-09.

| Issue | Status |
|---|---|
| PyCharm difftool path uses `which pycharm-professional` | ✓ **done 2026-06-09** — updated to `~/.local/share/JetBrains/Toolbox/apps/pycharm/bin/pycharm`; note added that path changes on IDE version upgrades |
| `git-projects.txt` approach untested on fresh machine | **→ future task** (2026-08-08) — `~/projects` is a working setup on this machine now; testing this requires a fresh install or throwaway environment, deliberately not risking the current one. Test when a new machine is next provisioned: create the file, run the script, verify per-dir `.gitconfig` and global `includeIf` entries. |

### docs/github.md

Status: ✓ **done 2026-06-08** — rewritten. Install via `inv apt.repos`; deprecated apt-key and manual methods removed; zsh completions noted as automatic from apt package; manual steps: `gh auth login`, config set.

### docs/fonts.md

Status: ✓ **done 2026-06-08** — fully rewritten. Bash script replaced with `inv fonts.install` / `inv fonts.configure` Python tasks. Nerd Fonts v2 → v3 migration logic documented (legacy glob cleanup + v3 file detection). Dry-run shows `ok (v2 — will upgrade)` for families needing migration. Font families and VS Code settings moved to `setup.toml`. FiraMono `.otf` anomaly documented. CaskaydiaCove / CascadiaCode naming explained.

### docs/ssh.md

Status: updated 2026-06-09.

| Issue | Status |
|---|---|
| RSA 4096 keys | ✓ **done 2026-06-09** — keygen updated to `ssh-keygen -t ed25519`; all `_rsa` filename suffixes updated to `_ed25519` throughout |
| Multi-account alias flow (`ssh_hosts` in `identity.toml`) | **→ future task, assessed 2026-08-08.** Not hard in principle — the underlying mechanism (`Host` alias + `IdentitiesOnly yes` + per-alias `IdentityFile`) is exactly what the *current* live `~/.ssh/config` has been running manually for years across 8+ hosts (four employers, AWS, etc.), so it's proven. The catch: this machine's live `~/.ssh/config` still predates PULSE entirely (old RSA keys, hand-written blocks, no PULSE sentinel markers). Running `inv ssh.configure` now would *append* a new PULSE block via `ensure_block` (additive, doesn't touch existing blocks) — but a new alias that collides with an existing hand-written `Host` entry (e.g. `github.com`) would silently lose to the old block, since ssh config resolution is first-match-wins per keyword. Safe to test in a throwaway `$HOME`/container; testing directly against this machine's config needs the alias list checked for collisions with the existing hand-written entries first. |
| keychain on 24.04 + Wayland | ✓ **verified 2026-08-08** — already installed and active in `~/.zprofile` on this machine (pre-PULSE, but confirmed working). The keychain-managed `ssh-agent` socket persists correctly across the Wayland session; `ssh-add -l` reporting no identities right after login is expected (`AddKeysToAgent yes` loads each key lazily on first use, not eagerly at login), not a failure. Warning removed from docs/ssh.md. |

### docs/golang.md

Status: ✓ **done 2026-06-08** — rewritten. Manual install steps removed; references `inv tools.install` and `inv zsh.configure`. GOROOT/GOPATH bug fixed (were swapped in original). Update instructions use `rm -rf ~/.local/share/go && inv tools.install`.

### docs/rust.md

Status: ✓ **new file, 2026-08-08** (added in a separate session, not part of the original 24.04
guide review — recorded here for completeness). Rust toolchain via rustup, added as `[packages.rust]`
in `setup.toml` — `method = "script"` piping the official rustup installer, redirected to XDG paths
(`~/.local/share/{cargo,rustup}` instead of the `~/.cargo`/`~/.rustup` defaults) via a new
`post_install` hook on the `script` method (`tasks/tools.py`) that adds the `rust-analyzer`
component right after a fresh install. `docs/ide.md` documents the PyCharm Rust plugin separately —
it uses its own analysis engine, not `rust-analyzer`, so no extra component is needed there, just
the toolchain itself and (if PyCharm doesn't autodetect it) manually setting the toolchain location
to `~/.local/share/cargo/bin`.

### docs/js.md

Status: ✓ **done 2026-06-08** — rewritten. References `inv node.install` and `inv zsh.configure`. nvm to `~/.local/share/nvm`, Node LTS, global packages from `setup.toml`. Updated 2026-06-08: `NVM_DIR` in `~/.zshenv`; omz `nvm` plugin owns loading and completion; `PROFILE=/dev/null` prevents install script from touching shell files.

### docs/kubernetes.md

Status: ✓ **done 2026-06-08** — rewritten. All deprecated install blocks removed; replaced with `inv apt.repos` / `inv tools.install` references. kubectl, helm, kind, tilt, freelens all declared in `setup.toml`. Content past the "Stop here" warning left untouched.

### docs/locale.md

Status: WIP/incomplete but the approach is correct. No 24.04 changes needed.

### docs/games.md

Status: ✓ **deleted 2026-06-08**.

### docs/apt_packages.md

Status: ✓ **done** — fully rewritten. Now documents the invoke-based workflow (`inv apt.base`, `inv apt.repos`, `inv apt.deb`, `inv apt.refresh-keys`). All deprecated packages removed. All install methods reference `setup.toml`.

### docs/python.md

Status: ✓ **done** — fully rewritten for uv. Covers bootstrap, shims, UV_PYTHON, `inv python.tools`, project venvs, private PyPI, Nuitka. Poetry/pipx/pyenv sections gone. **Updated 2026-08-08:**
added a "How the pieces fit together" section with a Mermaid diagram showing how interpreters
(`uv python install`), tools (`uv tool install`), project venvs, and the system Python never share
dependencies — written as part of verifying the zensical Mermaid fix (see Docs site entry below)
using this doc as the real test case. Also clarifies that `mkdocs`/`mkdocs-material` stay installed
via `inv python.tools` for other projects even though they no longer build *this* repo's docs site.

### docs/docker.md

Status: ✓ **done 2026-06-08** — rewritten. Install via `inv apt.repos`; deprecated apt-key method removed; `overlay2`/cgroupdriver daemon.json dropped (both are 24.04 defaults); compose v2 noted; `newgrp docker` and troubleshooting kept.

### docs/gnome_extensions.md

Status: ✓ **done 2026-06-09** — fully rewritten for 24.04; all 12 extensions confirmed active.

| Issue | Status |
|---|---|
| UUIDs for some "not yet enabled" extensions | ✓ **done 2026-08-08** — every other `enabled = false` entry already had its EGO link recorded; `gnome-ext-freon` was the one actually missing it (no `ego_id` field at all). Confirmed via extensions.gnome.org: [#841](https://extensions.gnome.org/extension/841/freon/), GNOME Shell 45-50 compatible. Added `ego_id = 841` to `setup.toml` and the EGO link to docs/gnome_extensions.md. |
| Per-extension confirmed-active status | ✓ **done 2026-06-09** — all 12 confirmed via `gnome-extensions list --enabled` after login |

### docs/gitlab.md

Status: updated 2026-06-09 — config, completions, and SSH key upload sections filled in.

| Issue | Status |
|---|---|
| `glab` install uses manual `curl` + `dpkg` | ✓ **done 2026-08-08** — added `[packages.glab]` to `setup.toml`. Note: `deb-github` doesn't apply — `gitlab-org/cli` has no GitHub release mirror (confirmed: `api.github.com/repos/gitlab-org/cli/releases/latest` 404s). Used `method = "deb-url"` instead, extending `_install_deb_url` (`tasks/apt.py`) with the same `{version}`/`version_cmd` templating the `archive` method already had, resolving the latest tag via the GitLab releases API. Also caught a stale asset-name assumption in the old manual instructions: glab's actual release filenames are `glab_{version}_linux_amd64.deb` (lowercase, `amd64`), not `Linux_x86_64` as the old doc had it. Installed and verified live: `glab 1.112.0`. |
| Config and completions | ✓ **done 2026-06-09** — `glab config set` and `glab completion -s zsh` documented |
| SSH key upload | ✓ **done 2026-06-09** — `glab ssh-key add` documented |

### docs/kubernetes-dev.md

Status: ✓ **deleted 2026-06-09** — entirely superseded by PULSE. kubectl and Helm already in `setup.toml` with modern GPG patterns; KIND already installed as latest binary via `setup.toml`. The file also had a stale v0.10.0 KIND pin and a path typo.

### docs/kubernetes_bare_metal.md + scripts/kubernetes-efk-stack.sh

Status: ✓ **deleted 2026-06-09** — old kubeadm/Flannel/MetalLB/Istio bare-metal setup and EFK stack Helm charts. No content relevant to current PULSE approach. Recoverable from git history if ever needed.

### docs/ide.md

Status: ✓ **done 2026-06-09** — new file, written this session. VS Code (deb vs snap, Wayland rationale), JetBrains Toolbox (archive extract, strip_components=2, bundled JRE), PyCharm (snap removal, Wayland fix, AppArmor profiles).

### docs/screen_capture.md

Status: new file added — GNOME built-in shortcuts, Flameshot overview, Wayland caveats.

| Issue | Action |
|---|---|
| Flameshot `enabled = false` in `setup.toml` | Enable once decision in Phase 8f is made and tested |
| Wayland `.desktop` fix not scripted | Consider adding a PULSE task to apply the `sed` fix on install |

### docs/index.md

Status: ✓ **done 2026-06-09** — fully rewritten for PULSE. All issues resolved:

| Issue | Status |
|---|---|
| References 20.04/focal throughout | ✓ done — PULSE index references Ubuntu 24.04 only |
| DNS/networking section uses `resolvconf` | ✓ done — replaced by `inv system.dns` (systemd-resolved) |
| `nomodeset` grub flag | ✓ kept as troubleshooting note in troubleshooting.md |
| p10k TODO | ✓ **done 2026-06-08** — `config/p10k.zsh` + `inv zsh.p10k-configure` |
| Phase ordering | ✓ **done** — `apt.repos` before `apt.base` |
| `PULSE_DRY_RUN` / `PULSE_EXCLUDE_TAGS` | ✓ **done** — documented in Quick start |

### docs/shortcuts.md

Status: **→ future task** (confirmed 2026-08-08) — pulled from master 2026-06-09, currently only
contains a Flameshot gsettings script. Deferred: a full review/audit is a lot of work and not
essential right now.

| Task | Notes |
|---|---|
| Review for non-Flameshot shortcuts | The script structure (looping `create_custom_shortcut`) is generic and reusable — audit what other custom bindings are worth adding (terminal, file manager, etc.) |
| Audit default GNOME system shortcuts | Inventory what bindings GNOME 46 provides out of the box before adding custom ones; prefer leaving defaults intact and only overriding where there is a clear gap or conflict |
| Guiding principle | Minimize overrides — fewer custom bindings means less to maintain and fewer surprises on a fresh install |
| Wayland env var | Any Flameshot binding needs `QT_QPA_PLATFORM=wayland` in the command (see Phase 8f); check if other app shortcuts have similar requirements |

### docs/wsl.md

Status: ✓ **new file, 2026-08-08** (added in a separate session, not part of the original 24.04
guide review — recorded here for completeness; substantially expanded in a follow-up session, also
2026-08-08). Covers bootstrapping this repo inside a WSL2 distro instead of a native workstation.

- `inv wsl.check` — read-only diagnostic: WSL1 vs WSL2, distro (Ubuntu vs other), systemd running,
  `/etc/resolv.conf` WSL-managed vs not, native `dockerd` vs Docker Desktop's WSL integration, WSLg
  availability.
- `inv wsl.fix` — **added in the follow-up session** — the fixable subset of the above: idempotently
  sets `systemd=true` / `generateResolvConf=false` in `/etc/wsl.conf` via a targeted key/value merge
  (`tasks/wsl.py`'s `_ensure_wsl_conf_kv`) that leaves any other content in that file untouched, then
  reminds you to run `wsl.exe --shutdown` from Windows. Distro choice, WSL1→WSL2, and WSLg
  availability all need action from the Windows side instead — no task can fix those from inside
  the distro, so `wsl.check` still just reports on them.
- Task-level enforcement, not just advisory — **added in the follow-up session**: `util.require_systemd()`
  / `util.require_apt()` (`tasks/util.py`) are generic capability checks, not WSL-specific branching,
  wired into `system.locale`/`system.dns`/`system.journal_size` and
  `apt.configure`/`apt.base`/`apt.repos`/`apt.deb` — they abort immediately with an actionable
  message instead of failing partway through a raw `systemctl`/`apt` error. `docker.configure`
  similarly detects "`docker` CLI present, no local `dockerd`" and skips cleanly instead of failing
  on `systemctl restart docker`.
- Two new `setup.toml` tags scope the WSLg-enabled GUI package set down to what's actually useful
  under WSL, instead of installing everything that merely *can* run there: `ide` (`vscode`,
  `jetbrains-toolbox`, `apparmor-jbr-cef` — use Windows-native VS Code/JetBrains + Remote-WSL
  instead) and `windows-native` (`terminator`, `wezterm`, `freelens`, `font-manager`,
  `claude-desktop`, `edge` — each duplicates a Windows app with no Linux-specific reason to run the
  Linux build). Recommended WSLg install set:
  `PULSE_EXCLUDE_TAGS=gnome,ide,windows-native,workstation,corporate`, leaving just `wl-clipboard`
  (Windows clipboard interop) and Google Chrome (real-Linux-build testing) from the `gui`/`desktop`
  tags. Also flagged that setup.toml has no Gecko-engine (Firefox) package at all — worth adding if
  cross-browser-engine testing under WSLg ever matters, since Chrome/Edge are both Blink.
- `xdg-desktop-portal-gnome` and `flameshot` retagged `gnome` (not just `desktop`) — their capture
  path needs a live GNOME Shell D-Bus service to back the portal, which WSLg's `weston` compositor
  doesn't provide; they'd hang under WSLg the same way `flameshot` already hangs on any machine
  without a running GNOME session (see the comment above `[packages.xdg-desktop-portal-gnome]` in
  `setup.toml`).
- Tag catalog and exclusion recipes also updated in `docs/index.md` and `setup.toml`'s own header
  comment to match.

### Docs site — mkdocs-material → zensical

Status: ✓ **done 2026-08-08** — migrated during the `initial_version` → `master` git landing effort
(see the Git history section below). Full findings, pain points, and a re-verify checklist for
next time: [zensical.md](zensical.md).

| Item | Outcome |
|---|---|
| Compatibility | `zensical` (same author as mkdocs-material, Rust core) reads the existing `mkdocs.yml` directly — confirmed drop-in, no rewrite needed. Kept the `mkdocs.yml` filename rather than migrating to zensical's native `zensical.toml` format, to stay on the officially-supported compat path rather than an early-alpha (v0.0.44) native config schema. |
| Feature parity | **Correction, 2026-08-08:** originally assessed as "mermaid already worked via the `mermaid2` plugin — no gap," but that plugin is actually a silent no-op under zensical (not in its native plugin allowlist) and the diagram was only rendering by accident, in the wrong (light) theme — see [zensical.md § Mermaid](zensical.md#mermaid) for the full story and the actual fix (`fence_code_format` + zensical's native mermaid support). `tablesort.js` was dropped — grep confirmed no doc actually uses sortable tables, so nothing lost there. |
| Verification | `zensical build --strict` — 0 issues against the real doc content. |
| Vendor-clone dir moved out of `docs_dir` | The original verification pass only worked because `docs/reference/repos/` (gitignored research clones) happened to be absent from CI's clean checkout — zensical's directory walker isn't gitignore-aware, so every *local* `zensical build`/`serve` was walking into vendored repos (gnome-shell, flameshot, …) and either hanging or drowning in broken-link warnings. Fixed properly by moving the whole dir to repo-root `reference/` (still gitignored), outside `docs_dir` entirely, so it's structurally excluded rather than excluded by chance. |
| Dependency change | `requirements-docs.txt` replaced `mkdocs-material~=7.0` / `mkdocs-mermaid2-plugin~=0.5` with `zensical==0.0.44` — confirmed zensical has zero mkdocs/mkdocs-material dependencies, fully self-contained. |
| GitHub Actions | `publish_on_push.yml` updated: `zensical build --strict` instead of `mkdocs gh-deploy`, deploy step switched to `peaceiris/actions-gh-pages@v4` (zensical has no built-in gh-deploy equivalent — build/serve/new only). Also bumped `actions/checkout` and `actions/setup-python` to current major versions and dropped the temporary `initial_version` trigger branch. |
| Side fix | Found and fixed a dead link in `docs/kubernetes.md` (pointed at the already-deleted `kubernetes_bare_metal.md`) — would have failed the new `--strict` build. |

---

## References

- [Official Ubuntu upgrade guide (desktop)](https://documentation.ubuntu.com/desktop/en/latest/how-to/upgrade-ubuntu-desktop/)
- [Official Ubuntu upgrade guide (server)](https://documentation.ubuntu.com/server/how-to/software/upgrade-your-release/)
- [Webex App for Linux — official docs](https://help.webex.com/en-us/article/9vstcdb/Webex-App-for-Linux)
- [Citrix Workspace for Linux — install docs](https://docs.citrix.com/en-us/citrix-workspace-app-for-linux/installation.html)
- [Making Citrix Workspace work on Ubuntu 24.04 (blog)](https://schulz.dk/2025/04/23/making-citrix-workspace-work-on-ubuntu-24-04/)
- [Webex on Ubuntu 24.04 — Cisco Community thread](https://community.cisco.com/t5/webex-meetings-and-webex-app/installing-webex-app-on-ubuntu-24-04/td-p/5163446)
