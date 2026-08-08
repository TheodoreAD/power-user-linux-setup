# Citrix

> **Paused, not abandoned — uninstalled 2026-08-08.** All three packages were on this machine
> and working (VPN/EPA blocked only by the IT-side gateway bug below) up through 2026-06-12. They
> were fully uninstalled on 2026-08-08 because Citrix Workspace's AppProtection module locks down
> all GNOME Shell extensions system-wide (see [gnome_extensions.md](gnome_extensions.md)), which
> was blocking normal desktop/extension development. Everything below — install steps, the EPA
> token bug, IT talking points — stays accurate for picking this back up later.
>
> The employer's gateway doesn't include a session token in the `nsgcepa://` EPA callback for
> Linux clients (see "Access denied" section below) — login never completes, so the VPN client was
> unusable regardless of how well it was configured. This is a gateway-side bug on IT's end, not
> something fixable from the Linux side, and is unrelated to the AppProtection/extensions issue.
>
> All three packages (`icaclient`, `nsgclient`, `nsepa`) are tracked in `setup.toml` with
> `enabled = false`. Sections: `citrix-workspace`, `citrix-secure-access`, `citrix-epa` — each now
> also declares a `cleanup_paths` list (leftover `/opt/Citrix`, logs, desktop entries, the
> `~/.citrix` dir, orphaned `/usr/local/bin` symlinks, and — for `citrix-workspace` — the
> AppProtection dconf lock at `/etc/dconf/db/local.d/locks/extensions-mandatory`) so
> `inv apt.uninstall <section-name>` removes not just the dpkg package but every trace, the same
> way the 2026-08-08 uninstall did. To pick this back up: flip `enabled = true`, `inv apt.deb`,
> then re-open this doc from the top.

## What Citrix Secure Access is

**Citrix Secure Access** (formerly NetScaler Gateway Plugin) is the corporate VPN client for connecting to resources behind a Citrix Gateway (NetScaler Gateway). It creates an SSL/TLS tunnel on port 443 — not a traditional IPsec VPN.

On Windows, the web portal automatically downloads and launches `nglauncher.exe`, which is part of the Secure Access client. `nglauncher` handles **Endpoint Analysis (EPA)**: device posture checks that verify OS version, antivirus state, etc. before granting access.

## Linux packages

Two packages exist, both from Cloud Software Group (Citrix):

| Package | Role | Installs to |
|---|---|---|
| `nsginstaller64.deb` | VPN client — standalone GUI app | `/opt/Citrix/NSGClient/` |
| `nsepa.deb` | Endpoint Analysis (posture checks, equiv. of nglauncher) | `/opt/Citrix/Browser-EPA/` |

Download from:
- VPN client: https://www.citrix.com/downloads/citrix-secure-access/plug-ins/Citrix-Gateway-VPN-EPA-Clients-Ubuntu.html
- EPA client: https://www.citrix.com/downloads/citrix-endpoint-analysis/plug-ins/EPA-Clients-Linux.html

Select the Ubuntu 22/24 section. Require version ≥ 24.8.5 for Ubuntu 24.04 support.

## Why not the browser extension

The **Citrix Web Extension** (browser plugin, Chrome Web Store ID `dbdlmgpfijccjgnnpacnamgdfmljoeee`) is the mechanism that lets the VPN portal auto-launch the client from the browser — equivalent to the Windows behavior. It has consistently poor reviews and is unreliable.

**Use the standalone client instead.** The `nsginstaller64.deb` installs a full GUI app that connects directly without any browser extension. Launch it from the app menu or:

```shell
/opt/Citrix/NSGClient/bin/NSGClient
```

## Installation

### The `resolvconf` problem

`nsginstaller64.deb` lists `resolvconf` as a dependency, but Ubuntu 24.04 uses `systemd-resolved` exclusively — `resolvconf` is not available in the Noble repos (see [networking.md](networking.md)). `openresolv` is also absent from 24.04 repos, so there is no clean substitute package.

The `resolvconf` dependency is a packaging artifact: the client uses `libnm0` (NetworkManager) for DNS at runtime, not resolvconf directly.

**In practice, `apt` resolves this silently** — just use `apt install`, it handles it without needing `--force-depends`.

### Install commands

```shell
sudo -A apt install -y ~/Downloads/nsginstaller64.deb
sudo -A apt install -y ~/Downloads/nsepa.deb
```

`apt` pulls in the 4 missing deps automatically (`libnl-cli-3-200`, `libnl-nf-3-200`, `libproxy1-plugin-webkit`, `libpugixml1v5`) and silently handles `resolvconf`. No `apt install -f` or force flags needed.

The harmless errors during install ("NSGClient: no process found", "Failed to stop nsgverctl.service") are just pre-install cleanup trying to stop a service that wasn't running yet.

### After install

Launch from the app menu ("Citrix Secure Access") or:

```shell
NSGClient
```

The EPA client registers the `nsgcepa://` protocol handler automatically via `/usr/share/applications/nsgcepa.desktop`. Verify with:

```shell
xdg-mime query default x-scheme-handler/nsgcepa
# should return: nsgcepa.desktop
```

If not registered, fix with:

```shell
xdg-mime default nsgcepa.desktop x-scheme-handler/nsgcepa
```

## "Access denied — your device is not compliant"

### How EPA works on Linux

The gateway serves `nsg-epa.js` which detects the OS and invokes the EPA binary via a custom protocol:

```
nsgcepa://nsgcepa/epav2plugin/{gateway-host}/{session-token}/
```

The browser (or NSGClient's embedded WebView) navigates to this URL, which triggers the registered `nsgcepa` protocol handler, launching `/opt/Citrix/Browser-EPA/nsgcepa`. That binary runs the compliance checks and reports results back to the gateway through a NetScaler proxy channel.

### Root cause

Investigation confirmed that the software side is correct — the protocol handler is registered, the EPA binary runs, and the gateway JavaScript does have Linux support. The actual failure is that **the gateway does not include the session token in the `nsgcepa://` URL for Linux clients**.

The EPA binary receives `nsgcepa://nsgcepa` with no host or token appended, logs `URL not present`, and exits. Without a token the scan cannot complete, so the gateway denies access.

Evidence from `~/.citrix/nssslvpn.txt`:
```
ERROR | URL not present.
```
And from NSGClient's standalone attempt:
```
ERROR | Webview: Invalid URL. `_result=` not found in the URL. Cannot proceed with login.
```

This is a **gateway-side configuration gap** — the pre-authentication EPA policy for Linux is not generating session tokens. On Windows/Mac it issues a token; on Linux the token step is skipped and the client falls through to the denial page.

### What to tell IT

> I'm on Ubuntu 24.04 with `nsgclient 25.8.2` and `nsepa 26.2.3` installed (official Citrix Linux packages). The EPA binary is invoked correctly via the `nsgcepa://` protocol handler, but the gateway is not including the session token in the URL for Linux clients — the binary receives `nsgcepa://nsgcepa` with no host or token, so the EPA scan cannot complete. The gateway needs a Linux pre-authentication EPA policy that provides the session token in the `nsgcepa://` invocation.

### Logs to check

```shell
cat ~/.citrix/nssslvpn.txt   # main EPA/VPN log
cat ~/.citrix/nsepa.txt      # EPA scan detail (only created if scan runs)
cat ~/.citrix/nsgcepa.txt    # EPA launcher log (only created if scan runs)
```

## Known issues

### TLS 1.3 required on Ubuntu 22+

Ubuntu 22.04+ enforces TLS 1.3. If the employer's NetScaler Gateway only has TLS 1.2 enabled, the VPN connects but the tunnel silently fails. The fix is on the IT/gateway side: they need to set `denySSLReneg NONSECURE` in the NetScaler CLI config.

### Split-tunnel DNS

If the VPN connects but internal hostnames don't resolve, `systemd-resolved` needs to be told to route those domains through the VPN's DNS server. Check which interface the VPN creates:

```shell
ip link show | grep -i citrix
resolvectl status
```

Then configure the interface's DNS:

```shell
sudo -A resolvectl dns <interface> <vpn-dns-server>
sudo -A resolvectl domain <interface> ~<internal-domain>
```
