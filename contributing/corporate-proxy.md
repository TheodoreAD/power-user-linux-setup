# Corporate proxy daemon — design notes

Companion to [`docs/corporate-proxy.md`](../docs/corporate-proxy.md) (the published "what it is /
how to use it" page). This is the durable record of what was considered and rejected while building
`tasks/proxy.py`, and what testing against a disposable local proxy resolved that reading `--help`
text alone didn't. Read this before re-deriving the design from scratch or "simplifying" something
that was already a deliberate tradeoff.

Built with **no real corporate proxy available to test against** — the design had to degrade
gracefully and be honest about what could/couldn't be verified locally. `docs/corporate-proxy.md`'s
own "Genuine limitations" section is the living record of what's still unverified; this file covers
the reasoning that got the design to that point.

## Why Px, not a home-grown or NTLM-only alternative

`cntlm` was rejected: NTLM-only and unmaintained — narrower than what's needed (Kerberos/Negotiate
matters too) and doesn't reuse the Windows-side mental model already settled for the Windows half of
this feature (`px` there too, via SSPI passthrough — see
[`to-migrate/windows-corporate-proxy-notes.md`](../to-migrate/windows-corporate-proxy-notes.md)).

A custom `mitmproxy`/`proxy.py` script was rejected: it would mean reimplementing NTLM/Kerberos
negotiation from scratch for paths that can't be tested locally at all — high effort, high risk, no
way to validate correctness before it matters.

A no-daemon, raw-`kinit`-ticket-only approach (skip the local proxy entirely, rely on an existing
Kerberos ticket) was considered as a first step, and is checked by `proxy.install` before falling
back to Px — but it can't be the _only_ path, since Basic-auth-only and NTLM-only proxies have no
ticket to reuse at all.

[Px](https://github.com/genotrance/px) (`px-proxy` on PyPI) won on three independent points at once:
installable via an install method this repo already has (`uv-tool`/`wrapper-script`, no new
`setup.toml` method needed), reuses OS-keyring credential storage PULSE would otherwise have to
build itself, and defers the actual protocol-correctness risk (NTLM/Kerberos wire format) to an
externally maintained implementation instead of code nobody here can fully test.

## Why three tasks (`check`/`fix`/`install`), not one

Matches `tasks/wsl.py`'s read-only-diagnose / idempotent-mutate / prompting-orchestrator split
rather than a single do-everything command, specifically so `fix` is safe to call from
non-interactive contexts (CI, a container's `postCreateCommand`) without ever risking a credential
prompt — only `install` performs one. A systemd `--user` unit was new territory for this repo (only
system-level units existed before this feature); the plain background-process-plus-`pgrep`-guard
fallback exists specifically for dev containers, where a user systemd manager is usually unavailable
— a real limitation (no crash auto-restart, no persistence across a rebuild), stated plainly in
`docs/corporate-proxy.md` rather than papered over.

Reused rather than re-derived: `tasks/wsl.py`'s `_dns_resolves()` "verify it actually works, don't
trust the config" pattern (`install` re-probes the daemon before ever pointing a shell at it);
`system.py`'s "restart unconditionally on any config change" rationale; and the existing `corporate`
`setup.toml` tag (already meant "skip on personal machines," exactly right here — no new tag
needed).

## What testing against a disposable local Squid instance actually found

A throwaway Squid container (`auth_param basic`) on `127.0.0.1:3129` let the full
`check → capture credential → configure → start daemon → verify` pipeline run for real, not just
dry-run, and confirmed an unauthenticated `curl` through Px returned `200`. That caught three things
the design got wrong purely from reading `--help` text and docs — the first two are also called out
in `docs/corporate-proxy.md`'s "Credential handling" section since they shape the shipped behavior
directly; the third is implementation-only and lives here:

1. **Px's actual config path is `~/.config/px/px.ini`, not `~/.px/px.ini`** as `--help` implied.
2. **`px --username=... --save --password` doesn't work non-interactively**, despite `--help`
   describing it as collecting and saving to the keyring. It calls Python's `getpass.getpass()`,
   which opens `/dev/tty` directly and raised `EOFError` with no controlling terminal — piping
   input, a pty (`script`), and a `PX_PASSWORD` env var on that specific invocation all failed to
   produce a stored password. Fix: write the keyring entry directly
   (`keyring.set_password('Px', username, password)`, matching what Px itself looks up) instead of
   driving Px's own interactive collector.
3. **A restart/verify race**: the post-restart verification probe ran before the daemon had actually
   bound its port yet, producing a false "not working" result immediately after a clean restart.
   Fixed with a short retry loop instead of one immediate probe — the daemon needs a brief moment
   after process start before its listening socket is up.

All test artifacts (keyring entry, `px.ini`, the systemd unit, the `~/.zshenv` block, the
`uv tool install`ed `px` binary, the Squid container) were removed after verification — nothing from
this testing pass is left behind on the dev machine.
