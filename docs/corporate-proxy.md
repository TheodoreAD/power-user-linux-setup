# Corporate proxy

Many corporate networks require an authenticating HTTP(S) proxy for external traffic while
routing internal artifact mirrors (apt, npm, PyPI, etc.) _directly_ — a blanket system-wide proxy
setting breaks the second half of that. The common ways people solve the first half are both
bad: embedding the credential in the proxy URL (`http_proxy=http://user:pass@proxy:8080`) leaks
it everywhere a process's environment is visible (`/proc/<pid>/environ`, `ps eww`, `docker
inspect`, any tool's own `-v`/verbose logging), and a shell-startup script that hits the keyring
on every new terminal is slow and fragile.

`inv proxy.*` solves both: a local, **unauthenticated-to-the-client** proxy daemon
([Px](https://github.com/genotrance/px)) holds the real credential once, apps point at
`127.0.0.1:3128` — nothing sensitive in that URL — and the daemon does the authentication
handshake with the real corporate proxy on their behalf.

## Quick start

```shell
inv proxy.check      # read-only — detects a candidate proxy and its auth scheme, changes nothing
inv proxy.install     # full flow: capture a credential if needed, start the daemon, verify it works
```

On a personal machine with no corporate proxy on the network, `proxy.check`/`proxy.install` both
exit cleanly with "nothing to configure" — this is the expected, non-error result, not a failure.

`inv proxy.fix` is the non-interactive half of `install` (installs/configures/restarts the
daemon, never prompts for a credential) — useful for re-applying config after a `setup.toml`
change, or as a build step where prompting isn't possible.

## How detection works

`proxy.check`/`proxy.install --proxy=auto` (the default) look for a candidate address in this
order, and print which source they used:

1. An explicit `[proxy]` `host`/`port` in `~/.config/pulse/identity.toml` (see
   `config/identity.toml.example`) — always wins if set, since it's an explicit statement of
   intent rather than a guess.
2. **WSL**: reachability of an unauthenticated proxy already listening at the Windows host's IP
   on port 3128 — see [WSL](#wsl) below. **Dev container**: inherited `http_proxy`/`https_proxy`
   env vars, then a `host.docker.internal` guess.
3. **Native Linux**: the current shell's `https_proxy`/`http_proxy` env vars (highest confidence
   — it's literally what every CLI tool already reads), then `/etc/environment`, then GNOME's
   `org.gnome.system.proxy` setting (lowest confidence — it doesn't populate CLI env vars on its
   own, so treat it as a hint to confirm, not a fact).

Once a candidate is found, both tasks send an unauthenticated request through it and read the
`407 Proxy Authentication Required` response's `Proxy-Authenticate` header — RFC 7235 requires
the proxy to list every scheme it supports there (`Basic`, `NTLM`, `Negotiate` for Kerberos,
sometimes several at once). No credentials are sent for this probe; it's read-only.

Nothing found, or the candidate isn't reachable at all: clean exit, nothing to configure. `--proxy
host:port` overrides auto-discovery on any of the three tasks, e.g. to check a specific address
manually.

## Credential handling

`proxy.install` only prompts for a credential when the probe requires one and no better option is
available:

- **Kerberos/Negotiate offered, and a ticket is already cached** (`klist -s`) — no password
  needed at all; Px authenticates using the existing ticket.
- **Kerberos/Negotiate offered, no ticket** — Px's own `--kerberos=1` mode acquires and renews
  the ticket itself, given a username and password (same capture flow as Basic/NTLM below).
- **Basic and/or NTLM offered** — a username (`domain\username` or plain username) and password
  are captured once: a GUI prompt via the existing `askpass-zenity` helper if a display is
  present, `getpass()` in a real terminal otherwise, or — in a non-interactive context
  (`postCreateCommand`, CI) — a `PULSE_PROXY_PASSWORD_FILE` path read once. There's no silent
  fallback: if none of these is available, `proxy.install` says so and stops rather than guessing.
- **No auth required** — nothing captured; the daemon still runs, for the `noproxy` bypass-list
  benefit and localhost-URL consistency.

The password is written directly into the same OS keyring entry Px itself reads at its own
startup (service `Px`, account `<username>`) — over `stdin` to a short-lived `uv run --with
keyring` subprocess, never through argv (visible in `ps`) or a file. **This departs from Px's own
documented `--password` flag** (`px --username=... --save --password`, which `--help` describes as
collecting and saving to the keyring): verified against a disposable local Squid instance while
building this feature that it doesn't actually work non-interactively — it calls Python's
`getpass.getpass()`, which opens `/dev/tty` directly and raises `EOFError` with no controlling
terminal, and neither piping input nor a `PX_PASSWORD` env var on that specific invocation changed
that. Writing the keyring entry directly, then letting Px read it back at its own startup, is what
was actually confirmed working end to end.

`px.ini` itself (`~/.config/px/px.ini`) is never hand-authored by PULSE — it's written entirely by
Px's own `--save`, and PULSE only checks whether a non-empty `username =` line is present as a
"credential likely cached" signal.

## WSL

WSL doesn't get its own local daemon. If an unauthenticated proxy is already reachable at the
Windows host's IP (`ip route show default`'s gateway) on port 3128, `proxy.check`/`proxy.install`
report that directly and configure WSL's side to point at it — no second daemon, no duplicated
credential.

That means the Windows host needs its own Px running first — this repo doesn't provision the
Windows side (it's Linux/WSL-guest-only in scope). On Windows: `scoop bucket add extras && scoop
install extras/px`, run as a per-user Scheduled Task or Startup-folder entry (not a SYSTEM
service — it needs to run _as the user_ so Windows SSPI can transparently pass through the logged-
in session's identity for NTLM/Kerberos proxies, no stored password needed on that side at all).

## Dev container

No systemd `--user` unit is assumed available. `inv proxy.fix`/`install` fall back to a plain
wrapper script (`~/.local/bin/pulse-proxy-start`, backgrounds `px` with a `pgrep` guard against
double-starting) instead. Real limitation, not papered over: no crash auto-restart, and nothing
persists across a container rebuild — re-run `inv proxy.install` (or `fix`, if a credential is
already cached) each time the container restarts, e.g. from `postCreateCommand`.

## Genuine limitations

- **NTLM and Kerberos/Negotiate paths are not verified against real infra** — there's no
  corporate proxy available to test against. The Basic-auth path _is_ verified end to end against
  a disposable local Squid instance with `auth_param basic`. Treat the NTLM/Kerberos code paths as
  reviewed-and-defensive, not proven.
- **Secret Service availability varies** — `keyring`'s SecretService backend needs a running
  provider (`gnome-keyring-daemon` on most desktop distros). A minimal WSL2 install or a
  from-scratch dev container may not have one; `keyring.set_password`/Px's own lookup will fail
  loudly rather than silently in that case, but there's no PULSE-side fallback secret store today.
- **`Proxy-Authenticate` header shape** — the parser handles both a repeated header per scheme and
  a single comma-joined header (RFC 7235 permits either), but which form any given real corporate
  proxy actually sends hasn't been observed firsthand.

## See also

- [certs.md](certs.md) — the separate concern of trusting a TLS-inspection root CA. Proxy auth
  (this page) and CA trust are unrelated; a network can have either, both, or neither.
