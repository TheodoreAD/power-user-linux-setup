---
status: in-progress
updated: 2026-09-06
---

# Corporate cert/proxy gaps left open under WSL

## Context

`inv proxy.*` (Px daemon), `inv certs.*` (TLS-inspection root CA) and `tasks/netdoctor.py` all
landed weeks ago and cover the common corporate case. Three gaps were documented as limitations
rather than closed, all three of them sharpest on a corporate WSL guest — the environment this repo
cannot dogfood:

1. **The Windows root store never crosses the boundary.** `docs/certs.md`'s WSL section states the
   fact and then hands the reader a manual `/mnt/c` copy: nothing here reads the Windows certificate
   store, even though `tasks/netdoctor.py` already talks to the Windows side through `reg.exe` and
   `netsh.exe` for the proxy half of the same problem.
2. **No keyring, no proxy.** `_capture_credential` writes the password into the OS keyring because
   that is where Px reads it back. A minimal WSL2 distro or a from-scratch container has no Secret
   Service provider, so the write fails — and it fails _after_ the password has been typed, with a
   Python traceback and no next step.
3. **Docker sees none of it.** `docs/docker.md`'s "Corporate registries/mirrors (not automated yet)"
   documents four separate mechanisms (registry mirror, daemon drop-in, container-side proxy,
   per-registry `certs.d`) and automates none.

Items 2 and 4 of that doc's limitation list — NTLM/Kerberos and real Windows PKCS#7 bundles — stay
open, because closing them needs a corporate network, not code.

## Design

### 1. `certs.install --from-windows` — export the Windows root store into the guest

WSL-only, refuses elsewhere. Runs `powershell.exe -NoProfile -NonInteractive -EncodedCommand <b64>`
over `Cert:\LocalMachine\Root` and `Cert:\CurrentUser\Root`, emitting one PEM block per certificate
with a `# <subject> [<thumbprint>]` comment line above it.

[DECISION: **`-EncodedCommand` with a UTF-16LE base64 payload, not a quoted `-Command` string.** The
script contains backslashes (`Cert:\LocalMachine\Root`), `$()` interpolation and both kinds of
quote, and it has to survive invoke's shell _and_ PowerShell's own parser. Encoding it removes the
entire quoting question, and the encoder is a pure function that unit-tests without a Windows host.
The script sets `[Console]::OutputEncoding` to UTF-8 as its first statement, since a redirected
PowerShell 5.1 stream otherwise emits the console's OEM codepage and a non-ASCII subject line comes
back as mojibake.]

[DECISION: **Only the roots the distro does not already trust are installed.** The Windows Root
store holds ~50 public CAs alongside the corporate one; installing all of them would add trust the
distro's own `ca-certificates` deliberately does not carry. The filter is a SHA-256 fingerprint set
computed over `/etc/ssl/certs/ca-certificates.crt` — the fingerprint _is_ the SHA-256 of the DER, so
this is `base64.b64decode` plus `hashlib` on both sides, no `openssl` subprocess per certificate and
a pure function to test.]

[DECISION: **The export lands at a stable path**
(`~/.local/state/power-user-linux-setup/windows-root-extras.pem`) **and its blocks are sorted by
fingerprint**, because `_desired_bundle_text` embeds the source path in a header comment and
compares the result against what is installed. A tempfile path, or PowerShell's own enumeration
order, would make the desired text differ on every run and re-trigger `update-ca-certificates`
forever.]

`--from-windows` composes with `--bundle` and with `[certs] bundle` rather than replacing them: the
exported file is appended to the resolved path list, so a machine with an IT-provided file _and_ a
root only present in the Windows store installs both. `certs.check --from-windows` performs the same
read-only export and reports what would be added.

### 2. A scoped keyring fallback for a distro with no Secret Service

Two changes, and the first matters more than the second:

**Probe before prompting.** `_keyring_round_trip()` writes, reads back and deletes a throwaway
credential in the same subprocess shape `_capture_credential` uses (the pattern
`docker.py::_credential_round_trip` already established for the same class of failure — a helper
that is installed but does not answer). `proxy.check` reports it; `proxy.install` runs it _before_
`_capture_credential`, so a machine with no keyring is told so instead of discovering it after the
password has been typed.

**`--keyring-fallback`, opt-in.** Verified locally 2026-09-06: `keyrings.alt.file.PlaintextKeyring`
round-trips a password, is selected purely by `PYTHON_KEYRING_BACKEND` with no config file, and
writes `$XDG_DATA_HOME/python_keyring/keyring_pass.cfg` mode 0600. With no backend at all,
`keyring.set_password` raises `NoKeyringError` and exits 1, which is what the probe reads.

[DECISION: **The backend is selected per-process through an env var, never through
`~/.config/python_keyring/keyringrc.cfg`.** That file is global to every `keyring` consumer on the
machine, so a fallback written there would silently downgrade unrelated tools — and would keep doing
so after a Secret Service provider appeared. The env var is written to
`~/.config/power-user-linux-setup/proxy.env`, pulled in by the systemd unit's
`EnvironmentFile=-%h/...` (the `-` making it optional) and sourced by the `pulse-proxy-start`
fallback script, so exactly two processes see it: Px, and PULSE's own one-shot keyring writer.]

[DECISION: **Plaintext-on-disk is offered rather than hidden, and never chosen automatically.** The
credential ends up base64-encoded in a 0600 file — the same risk class as the
`PULSE_PROXY_PASSWORD_FILE` this task already supports, and strictly better than the
credential-in-the-proxy-URL pattern the whole feature exists to avoid, but it is a real downgrade
from a locked keyring. The flag is the user stating that trade, and the task prints what it means
before writing anything.]

`keyrings.alt` reaches Px's own environment as `extras = ["keyrings.alt"]` on `[packages.px-proxy]`
— the `uv-tool` method already supports extras (`tasks/python.py`), so no new mechanism, and
`_install_px` reads the same declaration rather than hard-coding a second copy of it.

### 3. `inv docker.configure-corporate`

One task, four independently-gated pieces, each keyed off a new optional `[docker]` table in
`identity.toml`. Nothing runs for a key that is absent, and the whole task is a no-op on a machine
with no `[docker]` table — the same "clean exit, nothing to configure" shape `proxy.check` and
`certs.check` already have.

| key                | writes                                                         |
| ------------------ | -------------------------------------------------------------- |
| `registry_mirrors` | `registry-mirrors` merged into `/etc/docker/daemon.json`       |
| `proxy`/`no_proxy` | `/etc/systemd/system/docker.service.d/http-proxy.conf`         |
| `container_proxy`  | `proxies.default` in `~/.docker/config.json`                   |
| `registries`       | `/etc/docker/certs.d/<host>/ca.crt`, from the `[certs]` bundle |

[DECISION: **`proxy` and `container_proxy` are separate keys rather than one value reused twice**,
because they cannot be the same address. dockerd runs in the host's network namespace and reaches a
local Px at `127.0.0.1:3128`; a process _inside_ a container resolves `127.0.0.1` to the container's
own loopback and never reaches it, so the container-side value has to be the bridge gateway
(`172.17.0.1`) — and Px only answers there if it was started in gateway mode. Deriving one from the
other would produce a config that looks right and fails for containers only.]

[DECISION: **Docker Desktop's WSL integration short-circuits the whole task**, reusing
`util.is_docker_desktop_wsl_integration()` exactly as `docker.configure` does. There is no local
daemon in that distro, so a drop-in and a `daemon.json` would be written where nothing reads them —
those settings belong in Desktop's Windows-side UI.]

## Files touched

- `tasks/certs.py` — Windows root export, fingerprint diff, `--from-windows` on `check`/`install`.
- `tasks/proxy.py` — keyring round-trip probe, `--keyring-fallback`, `proxy.env` writer.
- `tasks/docker.py` — `configure_corporate` and its four writers.
- `tasks/util.py` — `load_docker_override()`, `DockerSection`.
- `config/pulse-proxy.service`, `config/pulse-proxy-start.sh` — optional env file.
- `setup.toml` — `extras = ["keyrings.alt"]` on `[packages.px-proxy]`.
- `config/identity.toml.example`, `docs/certs.md`, `docs/corporate-proxy.md`, `docs/docker.md`,
  `docs/wsl.md`.
- `tests/unit/test_certs.py` (new), `tests/unit/test_proxy.py`, `tests/unit/test_docker.py`.

## Verification

Pure functions carry the load, the way `netdoctor.evaluate()` does: the PowerShell encoder, the PEM
splitter, the fingerprint diff, the drop-in renderer and the `daemon.json`/`config.json` merges are
all testable with literal fixtures and no corporate host.

[UNVERIFIED: **the PowerShell export has never run against a real Windows certificate store.** The
encoder and every parser downstream of it are tested against captured fixtures; what cannot be
tested here is that `Get-ChildItem Cert:\...` on a real machine emits what those fixtures assume.]

[UNVERIFIED: **the systemd drop-in and `certs.d` writes have not been exercised against a running
dockerd** — the writers are unit-tested, but restarting the dev machine's docker daemon is not
something a test run may do.]
