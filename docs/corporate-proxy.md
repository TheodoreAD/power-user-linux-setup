# Corporate proxy

Many corporate networks require an authenticating HTTP(S) proxy for external traffic while routing
internal artifact mirrors (apt, npm, PyPI, etc.) _directly_ — a blanket system-wide proxy setting
breaks the second half of that. The common ways people solve the first half are both bad: embedding
the credential in the proxy URL (`http_proxy=http://user:pass@proxy:8080`) leaks it everywhere a
process's environment is visible (`/proc/<pid>/environ`, `ps eww`, `docker
inspect`, any tool's own
`-v`/verbose logging), and a shell-startup script that hits the keyring on every new terminal is
slow and fragile.

`inv proxy.*` solves both: a local, **unauthenticated-to-the-client** proxy daemon
([Px](https://github.com/genotrance/px)) holds the real credential once, apps point at
`127.0.0.1:3128` — nothing sensitive in that URL — and the daemon does the authentication handshake
with the real corporate proxy on their behalf.

## Quick start

```shell
inv proxy.check      # detects a candidate proxy and its auth scheme; changes no configuration
inv proxy.install     # full flow: capture a credential if needed, start the daemon, verify it works
```

On a personal machine with no corporate proxy on the network, `proxy.check`/`proxy.install` both
exit cleanly with "nothing to configure" — this is the expected, non-error result, not a failure.

`inv proxy.fix` is the non-interactive half of `install` (installs/configures/restarts the daemon,
never prompts for a credential) — useful for re-applying config after a `setup.toml` change, or as a
build step where prompting isn't possible.

## How detection works

`proxy.check`/`proxy.install --proxy=auto` (the default) look for a candidate address in this order,
and print which source they used:

1. An explicit `[proxy]` `host`/`port` in `~/.config/power-user-linux-setup/identity.toml` (see
   `config/identity.toml.example`) — always wins if set, since it's an explicit statement of intent
   rather than a guess.
2. **WSL**: reachability of an unauthenticated proxy already listening at the Windows host's IP on
   port 3128 — see [WSL](#wsl) below. **Dev container**: inherited `http_proxy`/`https_proxy` env
   vars, then a `host.docker.internal` guess.
3. **Native Linux**: the current shell's `https_proxy`/`http_proxy` env vars (highest confidence —
   it's literally what every CLI tool already reads), then `/etc/environment`, then GNOME's
   `org.gnome.system.proxy` setting (lowest confidence — it doesn't populate CLI env vars on its
   own, so treat it as a hint to confirm, not a fact).

Once a candidate is found, both tasks send an unauthenticated request through it and read the
`407 Proxy Authentication Required` response's `Proxy-Authenticate` header — RFC 7235 requires the
proxy to list every scheme it supports there (`Basic`, `NTLM`, `Negotiate` for Kerberos, sometimes
several at once). No credentials are sent for this probe; it's read-only.

Nothing found, or the candidate isn't reachable at all: clean exit, nothing to configure.
`--proxy
host:port` overrides auto-discovery on any of the three tasks, e.g. to check a specific
address manually.

## Credential handling

`proxy.install` only prompts for a credential when the probe requires one and no better option is
available:

- **Kerberos/Negotiate offered, and a ticket is already cached** (`klist -s`) — no password needed
  at all; Px authenticates using the existing ticket.
- **Kerberos/Negotiate offered, no ticket** — Px's own `--kerberos=1` mode acquires and renews the
  ticket itself, given a username and password (same capture flow as Basic/NTLM below).
- **Basic and/or NTLM offered** — a username (`domain\username` or plain username) and password are
  captured once: a GUI prompt via the existing `askpass-zenity` helper if a display is present,
  `getpass()` in a real terminal otherwise, or — in a non-interactive context (`postCreateCommand`,
  CI) — a `PULSE_PROXY_PASSWORD_FILE` path read once. There's no silent fallback: if none of these
  is available, `proxy.install` says so and stops rather than guessing.
- **No auth required** — nothing captured; the daemon still runs, for the `noproxy` bypass-list
  benefit and localhost-URL consistency.

The password is written directly into the same OS keyring entry Px itself reads at its own startup
(service `Px`, account `<username>`) — over `stdin` to a short-lived `uv run --with
keyring`
subprocess, never through argv (visible in `ps`) or a file. **This departs from Px's own documented
`--password` flag** (`px --username=... --save --password`, which `--help` describes as collecting
and saving to the keyring): verified against a disposable local Squid instance while building this
feature that it doesn't actually work non-interactively — it calls Python's `getpass.getpass()`,
which opens `/dev/tty` directly and raises `EOFError` with no controlling terminal, and neither
piping input nor a `PX_PASSWORD` env var on that specific invocation changed that. Writing the
keyring entry directly, then letting Px read it back at its own startup, is what was actually
confirmed working end to end.

### When there is no keyring

Px reads the credential back out of the keyring at **its own** startup, so a machine with no Secret
Service provider — a minimal WSL2 distro, a from-scratch container — cannot hold one at all.
`proxy.check` reports which backend answers, and `proxy.install` probes it with a throwaway
store/read/delete **before** asking for a password, rather than failing after one has been typed.

**A locked store and an absent one fail that probe identically**, so `proxy.check` asks the session
bus which of the two it is (`org.freedesktop.secrets` having an owner) and prints the fix that
matches: install a provider, or unlock the one that is already there. Since
`[packages.gnome-keyring]` and `[packages.dbus-user-session]` are declared, "already there and
locked" is the state a WSL distro that ran setup ends up in — and telling it to install what it has
is the failure mode this replaced.

Two ways out, and the first is better:

- **Give the distro a keyring**: `sudo apt install gnome-keyring dbus-user-session`, then start a
  user D-Bus session, and unlock the store — [docs/wsl.md](wsl.md#the-secret-store-and-unlocking-it)
  has the command and why PULSE does not run it for you. The credential stays in a locked store,
  which is the whole premise of the feature.
- **`inv proxy.install --keyring-fallback`** — stores the password base64-encoded in a 0600 file
  (`~/.local/share/python_keyring/keyring_pass.cfg`, `keyrings.alt`'s plaintext backend). Anything
  running as this user can read it: the same exposure as `PULSE_PROXY_PASSWORD_FILE`, still better
  than a credential embedded in `http_proxy`, and a real downgrade from a locked keyring. It is a
  flag, never an automatic fallback, and the task says what it costs before writing anything.

The backend is selected **per process**, through `PYTHON_KEYRING_BACKEND` in
`~/.config/power-user-linux-setup/proxy.env`, which the systemd unit pulls in with
`EnvironmentFile=-` and the `pulse-proxy-start` fallback script sources. That file holds the backend
name and no secret. The alternative — `~/.config/python_keyring/keyringrc.cfg` — is global to every
`keyring` consumer on the machine and would silently downgrade unrelated tools, including after a
real keyring became available.

`px.ini` itself (`~/.config/px/px.ini`) is never hand-authored by PULSE — it's written entirely by
Px's own `--save`, and PULSE only checks whether a non-empty `username =` line is present as a
"credential likely cached" signal.

## WSL

WSL doesn't get its own local daemon. If an unauthenticated proxy is already reachable at the
Windows host's IP (`ip route show default`'s gateway) on port 3128, `proxy.check`/`proxy.install`
report that directly and configure WSL's side to point at it — no second daemon, no duplicated
credential.

That means the Windows host needs its own Px running first — this repo doesn't provision the Windows
side (it's Linux/WSL-guest-only in scope). On Windows:
`scoop bucket add extras && scoop
install extras/px`, run as a per-user Scheduled Task or
Startup-folder entry (not a SYSTEM service — it needs to run _as the user_ so Windows SSPI can
transparently pass through the logged- in session's identity for NTLM/Kerberos proxies, no stored
password needed on that side at all).

## Reaching the daemon from a container

By default the daemon answers **this machine's loopback and nothing else** — Px's own defaults are
`listen=127.0.0.1`, `gateway=0`, `allow=*.*.*.*`. That is the right default and it is why
`http_proxy=http://127.0.0.1:3128` is safe to export: no other host can use your corporate
credential.

A process **inside a container** resolves `127.0.0.1` to the container's own loopback, so it never
reaches the daemon. Pointing containers at the bridge gateway (`172.17.0.1:3128`) is the fix, and it
needs the daemon to accept a client that isn't loopback:

```toml
[proxy]
gateway = true
allow = "172.17.0.0/16" # docker's default bridge, and nothing else
```

Then `inv proxy.fix` rewrites `px.ini` and restarts the daemon.

**`allow` is not optional here, and PULSE refuses `gateway` without it.** `gateway=1` overrides
`listen`, so the daemon binds every interface — and Px's stock `allow` accepts every client that can
route to the machine. The daemon is deliberately unauthenticated to its clients (that is what keeps
the credential in one place), so the two together publish authenticated egress through _your_
corporate account to the whole LAN, and to whatever a VPN attaches you to. A value that narrows
nothing (`*`, `*.*.*.*`, `0.0.0.0/0`) is refused for the same reason.

`inv proxy.check` reports which of the two postures is in effect, and
`inv docker.configure-corporate` says so too when `container_proxy` is set while the daemon is still
loopback-only — configuration that reads correctly and cannot work is exactly the failure this
pairing produces.

## Dev container

No systemd `--user` unit is assumed available. `inv proxy.fix`/`install` fall back to a plain
wrapper script (`~/.local/bin/pulse-proxy-start`, backgrounds `px` with a `pgrep` guard against
double-starting) instead. Real limitation, not papered over: no crash auto-restart, and nothing
persists across a container rebuild — re-run `inv proxy.install` (or `fix`, if a credential is
already cached) each time the container restarts, e.g. from `postCreateCommand`.

## Genuine limitations

- **NTLM and Kerberos/Negotiate paths are not verified against real infra** — there's no corporate
  proxy available to test against. The Basic-auth path _is_ verified end to end against a disposable
  local Squid instance with `auth_param basic`. Treat the NTLM/Kerberos code paths as
  reviewed-and-defensive, not proven.
- **Secret Service availability varies** — `keyring`'s SecretService backend needs a running
  provider (`gnome-keyring-daemon` on most desktop distros), and a minimal WSL2 install or a
  from-scratch dev container may not have one. That is now detected before a password is asked for,
  with `--keyring-fallback` as the documented way out — see
  [When there is no keyring](#when-there-is-no-keyring). The probe and both backends were exercised
  locally; what remains unverified is Px's own read of the fallback store on a machine that actually
  lacks a Secret Service, since this one has one.
- **`Proxy-Authenticate` header shape** — the parser handles both a repeated header per scheme and a
  single comma-joined header (RFC 7235 permits either), but which form any given real corporate
  proxy actually sends hasn't been observed firsthand.

## See also

- [certs.md](certs.md) — the separate concern of trusting a TLS-inspection root CA. Proxy auth (this
  page) and CA trust are unrelated; a network can have either, both, or neither.
