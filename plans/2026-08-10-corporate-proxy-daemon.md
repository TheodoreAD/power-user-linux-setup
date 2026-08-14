---
status: landed
updated: 2026-08-10
---

# Corporate proxy auth detection + local daemon (PULSE feature)

Design record, not usage docs — for how this actually works today, see
[`docs/corporate-proxy.md`](../docs/corporate-proxy.md) and `tasks/proxy.py` directly. This file
exists to preserve _why_ the design landed here: what was considered and rejected, and what was
genuinely unknown going in vs. what testing resolved.

## Context

PULSE currently has zero proxy story: `docs/networking.md` covers DNS only, no `tasks/*.py`
module touches proxying, and `reference/corporate-proxy-auth.md` (gitignored scratch notes from
this conversation) is the only trace of the idea. The goal, worked out over the conversation: many
corporate networks require going through an authenticating HTTP(S) proxy for external traffic
while _not_ wanting that proxy applied to internal artifact mirrors, and the common ways people
handle the credential (`http://user:pass@proxy:8080` embedded in `http_proxy`, or a keyring call on
every shell startup) are both bad — the former leaks the secret everywhere (`/proc/<pid>/environ`,
`ps eww`, `docker inspect`, tool `-v` logging), the latter is slow/fragile per terminal.

The agreed pattern: a local, **unauthenticated-to-the-client** proxy daemon that holds/negotiates
the real credential once and re-exposes `127.0.0.1:<port>`; apps point at that instead of a
credential-bearing URL. [Px](https://github.com/genotrance/px) already does this and was the
settled choice for Windows (`scoop install extras/px`, using Windows SSPI for free NTLM/Kerberos
passthrough of the logged-in session — out of scope here, this repo doesn't provision the Windows
host). What was left open was: (1) the equivalent for native Linux, since there's no SSPI
equivalent there, and (2) how to auto-detect the proxy's auth scheme and address in the first
place, across native Linux, WSL2, and a dev container. The user is building this for the
open-source tool on a personal machine with **no real corporate proxy to test against** — the
design has to degrade gracefully and be honest about what can/can't be verified locally.

## Design

### 1. Linux daemon: Px again (`px-proxy` on PyPI), not a new tool

Confirmed directly from Px's `--help` (run locally via `uvx --from px-proxy px --help`, not just
read from its README): it's Python-only, cross-platform, installable via `pip install px-proxy` /
`uv tool install px-proxy`, listens on `127.0.0.1:3128` by default, authenticates upstream via
libcurl's mechanism support (Basic, NTLM, Kerberos/Negotiate — plus its own `--kerberos=1` mode
that acquires/renews a ticket itself given a username/password, not just an existing `kinit`
ticket), and has exactly the credential-caching PULSE needs already built in — a keyring lookup at
its own startup, service `Px`, account `<username>`. There's also a `--auth=TYPE` flag
(`NEGOTIATE`/`NTLM`/`DIGEST`/`BASIC` plus combinators like `ANY`), but the final implementation
never passes it — Px's documented default behavior is to auto-discover the upstream scheme itself,
which is simpler and avoids PULSE's own probe result ever forcing a wrong mechanism.

Rejected alternatives: `cntlm` is NTLM-only and unmaintained — narrower, and doesn't reuse the
Windows-side mental model already settled. A custom `mitmproxy`/`proxy.py` script means
reimplementing NTLM/Kerberos negotiation from scratch for paths that can't be tested locally —
high effort, high risk, no way to validate. A no-daemon raw-Kerberos-ticket approach (just use an
existing `kinit` ticket directly, no proxy in the middle) is checked as a first step by `install`
before falling back to Px, but can't be the only path since Basic/NTLM-only proxies still need a
daemon. Px is the one option installable via an existing `setup.toml` method, reuses the credential
storage PULSE would otherwise have to build, and defers the protocol-correctness risk to an
externally maintained implementation instead of home-grown code nobody here can test.

### 2. Shape of the solution

Three tasks (`check`/`fix`/`install`), matching `tasks/wsl.py`'s read-only-diagnose /
idempotent-mutate / prompting-orchestrator split rather than one do-everything command — chosen so
`fix` can be called from non-interactive contexts (CI, a container's `postCreateCommand`) without
ever risking a credential prompt, which only `install` performs. A systemd `--user` unit is new
territory for this repo (only system-level units existed before); a plain background-process
fallback covers dev containers, where a user systemd manager usually isn't available at all — a
real limitation (no crash auto-restart, no persistence across a rebuild), not papered over.

Reused rather than re-derived: `tasks/wsl.py`'s `_dns_resolves()` "verify it actually works, don't
trust the config" pattern (`install` re-probes the daemon before ever pointing a shell at it);
`system.py`'s "restart unconditionally on any config change" rationale; the existing `corporate`
setup.toml tag (no new tag needed — it already means "skip on personal machines," which is exactly
right here); and the `uv-tool`/`wrapper-script` install methods already in `tasks/tools.py`, so
installing Px needed zero new install-method code.

## Genuine unknowns going in, and what testing resolved

Built with no real corporate proxy available to test against — the design had to degrade
gracefully and be honest about what could/couldn't be verified locally. What was actually done: a
disposable local Squid container (`auth_param basic`) on `127.0.0.1:3129` let the full
`check → capture credential → configure → start daemon → verify` pipeline be run for real, not
just dry-run, and confirmed an unauthenticated `curl` through Px returned `200`. That caught three
things the design got wrong purely from reading `--help` text and docs:

1. **Px's actual config path is `~/.config/px/px.ini`, not `~/.px/px.ini`** as `--help` implied.
2. **`px --username=... --save --password` doesn't work non-interactively**, despite `--help`
   describing it as collecting and saving to the keyring. It calls Python's `getpass.getpass()`,
   which opens `/dev/tty` directly and raised `EOFError` with no controlling terminal — piping
   input, a pty (`script`), and a `PX_PASSWORD` env var on that specific invocation all failed to
   produce a stored password. Fix: write the keyring entry directly
   (`keyring.set_password('Px', username, password)`, matching what Px itself looks up) instead of
   driving Px's own interactive collector.
3. A minor race: the post-restart verification probe ran before the daemon had bound its port —
   fixed with a short retry instead of one immediate probe.

Still genuinely unverified after this: **NTLM and Kerberos/Negotiate**, since no proxy requiring
either was available to test against — those code paths are reviewed-and-defensive, not proven,
per `docs/corporate-proxy.md`'s "Genuine limitations" section. Also unresolved: Secret Service
availability on a from-scratch WSL2 install or dev container (no fallback secret store today if
it's missing), and which `Proxy-Authenticate` header shape (repeated vs. comma-joined) real
corporate proxies actually send — the parser handles both per RFC 7235, but neither has been
observed firsthand.

All test artifacts (keyring entry, `px.ini`, the systemd unit, the `~/.zshenv` block, the
`uv tool install`ed `px` binary, the Squid container) were removed after verification.

## Migrated to

- Usage docs: [`docs/corporate-proxy.md`](../docs/corporate-proxy.md) (already existed alongside
  this plan; unchanged by this retirement).
- Design rationale (rejected alternatives, the check/fix/install task-split reasoning, and the
  restart-race-condition fix not already captured in the usage doc):
  [`contributing/corporate-proxy.md`](../contributing/corporate-proxy.md) (new).
- This file is deleted in the same change that adds the above.
