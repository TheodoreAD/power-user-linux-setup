# Windows corporate proxy + credential research (portable — not PULSE-scoped)

**Status: staged for migration, not a permanent home.** `power-user-linux-setup` is Linux-only in
scope (it never provisions a Windows host) — this file doesn't belong here long-term. It's committed
under `to-migrate/` (a deliberate exception to the normal `reference/`-is-gitignored convention —
see `docs/index.md`/`AGENTS.md`) purely so the Windows-specific research from the conversation that
produced this repo's Linux corporate-proxy daemon feature (`docs/corporate-proxy.md`,
`contributing/corporate-proxy.md`) doesn't live only on one machine's local disk until a separate,
Windows-only project exists to receive it. **When that project starts: move this file there
(`git mv`/copy + delete here), then delete `to-migrate/` from this repo** — don't leave it behind
once it has a real home.

The Linux/WSL/devcontainer side of this research is now the real, implemented feature — see
`docs/corporate-proxy.md` (usage) and `contributing/corporate-proxy.md` (design rationale) in this
repo. This file covers what's specific to the Windows host and doesn't belong in a Linux-setup
repo's tracked docs.

## The problem this solves

Corporate environment: one username/password for several apps and the proxy. Some apps need to go
through an authenticating proxy to reach the internet; internal artifact mirrors must **not** go
through it (blanket system-wide proxy settings are wrong). Avoid embedding the credential in the
proxy URL, and avoid anything that hits a credential store synchronously on every new terminal.

## Anti-pattern: credentials embedded in the proxy URL

`http_proxy=http://user:pass@proxy:8080` set globally (shell rc, systemd/Windows service env, CI
config) is common but bad — applies on Windows exactly as on Linux:

- Every child process inherits the secret whether it touches the network or not.
- Trivially readable by anything running as the same user: process environment inspection, task
  manager/Process Explorer, container inspection, CI logs that dump env, crash reporters.
- Tools log it themselves (`curl -v`, `pip -v`, `npm config list`, proxy-failure error messages).
- URL-encoding footguns: `@`, `:`, `/`, `%` in the password silently break or misparse the URL.
- Rotation means hunting down every place the string was copy-pasted (shell rc, CI secrets, Docker
  Compose files, Windows Task Scheduler action arguments, …).

## Core pattern: local unauthenticated proxy daemon

A local proxy that (1) holds/negotiates the real credential exactly once, (2) does the auth
handshake with the upstream corporate proxy on the client's behalf, (3) exposes a plain,
**unauthenticated** proxy on `localhost:<port>`. Apps then get `http_proxy=http://127.0.0.1:<port>`
— no secret in the string, safe in env or per-tool config, harmless even if logged. Bypass logic for
internal mirrors belongs in this daemon's own config, not duplicated per tool.

## Px — the tool, in detail

[Px](https://github.com/genotrance/px) (`genotrance/px`) implements exactly this pattern. MIT
licensed, actively maintained, cross-platform (Windows/Linux/macOS), Python-only.

**Install (Windows):**

```
scoop bucket add extras
scoop install extras/px
```

Also installable via `pip install px-proxy` / `pipx install px-proxy` / `uv tool install px-proxy`
(confirmed from the project's README) on any platform, Python ≥ 3.10. Not built into Windows —
third-party.

**Mechanism, per protocol:**

- **Plain HTTP**: app sends the request to Px → Px forwards it to the real corporate proxy →
  corporate proxy responds `407 Proxy Authentication Required` → Px performs the auth handshake (see
  below) → retries with auth headers attached → relays the final response back to the app.
- **HTTPS**: client sends Px a `CONNECT host:443`. Px does the same 407/auth dance with the
  corporate proxy to establish the tunnel, then relays raw encrypted bytes end-to-end — TLS happens
  between the client and the destination server, so Px never sees decrypted payload, only brokers
  the tunnel.

**Auth, Windows specifically:** for NTLM/Kerberos-authenticating proxies, Px uses Windows **SSPI**
to transparently pass through the _currently logged-in Windows session's_ identity — the same
mechanism behind Integrated Windows Authentication for intranet sites. No password is ever typed
into Px or stored by it for this path. This requires Px to run **as the user**, not as SYSTEM — set
it up as a per-user Scheduled Task or Startup-folder entry at logon, not a `services.msc` entry, so
it inherits the correct logon token. README confirms: `"Windows SSPI or single sign-on"` on Windows;
elsewhere it "supports all the authentication mechanisms supported by libcurl" (no free SSPI
passthrough off-Windows).

**Auth, cross-platform / explicit credential path:** `px --username=domain\username --password`
prompts once and stores the password in the **system keyring** (on Windows: Credential
Manager/DPAPI, tied to the login session, no separate unlock step — Python's `keyring` library picks
this backend up automatically as `WinVaultKeyring`). `px --proxy=proxyserver.com:8080 --save`
persists the rest of the config to `px.ini` (default `~/.px/px.ini`). Default listen port `3128`. A
confirmed `--auth=TYPE` flag accepts `ANY | NTLM | NEGOTIATE | BASIC | NONE` — `ANY` is the safe
default, letting libcurl negotiate the strongest mechanism the proxy actually offers rather than
forcing a specific guessed value.

**Why Basic-auth-only proxies still need an explicit credential:** SSPI passthrough only applies to
NTLM/Kerberos/Negotiate. If the corporate proxy only speaks Basic, Px needs the password supplied
explicitly (as above) — there's no SSO shortcut for Basic auth on any platform.

## Detecting which auth scheme a proxy requires

Send an unauthenticated request through the candidate proxy and read the `407`'s
`Proxy-Authenticate` header — RFC 7235 requires the proxy to list every scheme it supports (`Basic`,
`NTLM`, `Negotiate` for Kerberos, sometimes `Digest`; multiple can be listed together).

```bash
curl -sv -o /dev/null --proxy http://<proxy-host>:<port> http://example.com 2>&1 \
  | grep -i 'proxy-authenticate\|< HTTP'
```

No credentials sent, read-only, safe to run against an unknown proxy. Interpreting the result:

- **`Negotiate` present** → Kerberos/SPNEGO supported, best case (no stored password needed at all
  if a ticket is already held — `klist` to check, `kinit user@REALM` to obtain one; test with
  `curl --proxy-negotiate --proxy-user : --proxy http://proxy:port URL`, the `:` being a required
  placeholder since GSSAPI uses the ticket, not a password).
- **`NTLM` only** → older Windows-proxy-style auth; on Windows, SSPI covers this for free.
- **Only `Basic`** → simplest to implement, weakest security — explicit credential unavoidable on
  every platform.

## Windows service/startup mechanics

- Run via per-user **Scheduled Task** ("run at logon", as the user — not SYSTEM) or the Startup
  folder, specifically so the process inherits the interactive logon session SSPI needs to pass
  through NTLM/Kerberos credentials transparently. A SYSTEM-context service would authenticate as
  the machine account instead of the logged-in user for NTLM/Kerberos, defeating the SSO benefit.
- Config lives in `px.ini` — proxy address(es), a `--noproxy=LIST`/`noproxy=` bypass list for
  internal mirror hosts (the "don't want proxy universal" requirement), port, etc.

## How apps point at Px

Same as any ordinary, unauthenticated proxy — no userinfo in the URL:

- Env vars: `HTTP_PROXY=http://127.0.0.1:3128`, `HTTPS_PROXY=http://127.0.0.1:3128`
- Per-tool config: `npm config set proxy http://127.0.0.1:3128`, `pip.ini`'s `proxy =` line,
  `git config --global http.proxy http://127.0.0.1:3128`, Docker Desktop's Settings → Resources →
  Proxies, browser system-proxy settings.
- Bypass list for internal mirrors lives in Px's own config, not duplicated per tool.

## WSL2 interop (the one place this touches the Linux side)

Don't run a second proxy daemon inside the WSL guest. Run Px once on the Windows host (gets SSO for
free), and have WSL's per-tool proxy configs point at the host's IP
(`$(ip route show default | awk '{print $3}')`, since WSL2's default route points at the Windows
host) on that Px port. Keeps the only credential-holding process on the Windows side, where SSPI
actually works. This is the one conclusion the Linux side's WSL discovery logic
(`docs/corporate-proxy.md`'s "WSL" section) directly consumes — it probes for a Px already listening
at the host IP and, if found, skips installing a Linux-side daemon entirely rather than duplicating
it.

## Open items if this becomes a real Windows-only project

- Automate the Scheduled Task creation (`schtasks`/`New-ScheduledTask` PowerShell) instead of a
  manual Startup-folder drop.
- Confirm whether Px's Windows build needs any extra Kerberos/GSSAPI dependency beyond stdlib SSPI,
  or if that's Windows-only-and-free as the README implies.
- Investigate whether `winget`/Chocolatey offer Px as an alternative to Scoop, for environments
  where Scoop itself isn't installed/allowed.
- A PowerShell equivalent of the `curl`-based `Proxy-Authenticate` probe (`Invoke-WebRequest`
  against the proxy, inspecting the `407` response headers) for environments without `curl.exe`
  available (rare on modern Windows 10/11, which ships `curl.exe`, but worth confirming).
