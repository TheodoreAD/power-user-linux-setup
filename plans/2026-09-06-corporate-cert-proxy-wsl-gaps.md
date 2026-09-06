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

### 4. `inv certs.discover` — find the certificate already in use, and ask

Not yet built. `--from-windows` answers "which roots exist on the Windows side that this distro
doesn't trust", which is a set, sorted by nothing that says which one matters. Four other routes
answer a better question — **which certificate is this machine already using, or being told to use**
— and three of them yield an exact file rather than a candidate list. Read-only, ranked by how
direct the evidence is, and it **asks before installing anything**: adding a root CA is a trust
decision, so each candidate is named with its subject, its fingerprint and where it was found.

**A. Environment variables that point at a certificate.** The strongest signal there is, because
somebody has already decided this file is the corporate CA — the task's job is only to put it where
the OS trust store can see it:

| variable                                                     | set by              |
| ------------------------------------------------------------ | ------------------- |
| `SSL_CERT_FILE`, `SSL_CERT_DIR`, `CURL_CA_BUNDLE`            | OpenSSL, curl       |
| `REQUESTS_CA_BUNDLE`, `PIP_CERT`, `HTTPLIB2_CA_CERTS`        | Python, pip         |
| `NODE_EXTRA_CA_CERTS`, `NPM_CONFIG_CAFILE`                   | Node, npm           |
| `GIT_SSL_CAINFO`, `GIT_SSL_CAPATH`                           | git                 |
| `AWS_CA_BUNDLE`, `AZURE_CLI_CA_BUNDLE`                       | cloud CLIs          |
| `CARGO_HTTP_CAINFO`, `DENO_CERT`, `GOPROXY`-adjacent tooling | language toolchains |
| `JAVA_TOOL_OPTIONS` / `-Djavax.net.ssl.trustStore=`          | anything on a JVM   |

Read from the current environment, `/etc/environment`, and the shell rc files — but also, and this
is the WSL-specific half, **from the Windows side through `reg.exe`**:
`HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment` and `HKCU\Environment` are where
IT sets these machine-wide, and a value like `C:\ProgramData\corp\corp-root.pem` translates straight
to a readable path with `wslpath`. `WSLENV` is worth reading in the same pass: it names which
variables were _meant_ to cross the boundary, and its `/p` flag means the path has already been
translated for the distro.

**B. Config files naming a certificate.** Weaker than A only because a stale entry can outlive its
file: `~/.npmrc`'s `cafile`, `pip.conf`/`pip.ini`'s `cert`, `.gitconfig`'s `http.sslCAInfo`,
`~/.curlrc`'s `cacert`, `~/.condarc`'s `ssl_verify`, `gradle.properties`'
`systemProp.javax.net.ssl.trustStore`, and on the Windows side `%APPDATA%\NuGet\NuGet.Config`.

**C. Verification switched off — the anti-signal, and probably the most valuable output.**
`GIT_SSL_NO_VERIFY`, `NODE_TLS_REJECT_UNAUTHORIZED=0`, `PYTHONHTTPSVERIFY=0`, npm's
`strict-ssl=false`, pip's `trusted-host`, conda's `ssl_verify: false`,
`git config http.sslVerify
false`. Each one is somebody hitting this exact problem and turning off
the check instead of installing the CA — a silent, permanent security downgrade that no error
message will ever mention again.

[DECISION: **report these, install the CA first, and only then offer to remove them — never in the
other order.** Removing the bypass before the trust store can verify the traffic breaks the tool
that was working a moment ago, and the natural next move for whoever hits that is to put the bypass
back, permanently. Removal is also a separate confirmation from installation: a bypass may exist for
an unrelated host that this CA does not cover.]

**D. Windows-native signals, which rank the candidates A–C cannot produce.**

1. **The group-policy and enterprise physical stores.** `certutil -grouppolicy -store Root` and
   `certutil -enterprise -store Root` (registry:
   `HKLM\SOFTWARE\Policies\Microsoft\SystemCertificates\Root\Certificates`) list roots that were
   **deployed by IT**, by construction. That is a far stronger statement than the current "not in
   Mozilla's set" subtraction, which cannot tell a corporate root from any other locally-added one,
   and it should become the ranking signal layered on top of that diff rather than a replacement for
   it.
2. **The certificate actually re-signing traffic right now.** `netdoctor` already reads the issuer
   common name off a failed chain by scanning the DER (it has to — `ssl` only parses a chain it
   validated, and the interesting case is the one that failed). Matching that name against the
   candidates turns "here are four extra roots" into "this is the one your traffic is signed by".
3. **Vendor drop paths, with an asymmetry worth recording so nobody hunts for a file that does not
   exist.** Netskope writes `C:\ProgramData\netskope\stagent\data\nscacert.pem` (and a
   `nscacert_combined.pem`), so a glob finds it. Zscaler's client connector injects into the Windows
   store instead and documents no fixed file path — for that one, D1 and D2 are the only routes.
4. **Windows git defaults to the schannel TLS backend**, which reads the Windows store directly. So
   a corporate laptop can have git working perfectly on the Windows side with **no PEM file anywhere
   on disk** — meaning "there is no file to copy" is the normal state on exactly the machines that
   need this most, not a failed search. That is the argument for D1 being the primary route rather
   than a file hunt.

[DECISION: **`discover` reports by default and installs only under `--install`**, which asks about
each certificate individually and defaults to no. That keeps the read-only/mutating split every
other pair here has, and the per-certificate question is not ceremony: trusting a root means
trusting whoever holds its private key for every TLS connection the machine makes. `util.confirm`
returns its default without a terminal, so a non-interactive run installs nothing.]

[PITFALL: **ask before authenticating, not after.** The first version called `util.ensure_sudo()` at
the top of the install path, which opens a GUI password dialog — so a non-interactive
`discover --install`, where every question answers no, asked for a root password in order to install
nothing. The confirmations now run first and sudo is reached only once something has been accepted.]

[PITFALL: **`netdoctor` fills `tls_issuer` whether or not the chain verified**, scanning the DER on
success and re-reading the chain without verification on failure. Reporting the issuer alone printed
"pypi.org is re-signed by GlobalSign …" on a perfectly clean personal machine — an interception
claim about an ordinary public CA. The report carries `tls_ok` with it now. Caught by running the
task, not by reading it: every unit test passed either way, because the bug was in what the sentence
asserted rather than in what the code computed.]

### 5. Who may talk to the local proxy daemon

Found by asking what the state of the proxy half actually was, after sections 2 and 3 had landed:
**they contradicted each other.** `[docker] container_proxy` points containers at the bridge
gateway, and the daemon answers loopback only — Px's defaults are `listen=127.0.0.1`, `gateway=0`,
`allow=*.*.*.*`. Nothing here configured that, so the key shipped as configuration that reads
correctly and cannot work, with the docs naming the requirement and nothing implementing it.

[DECISION: **`gateway` is refused without an `allow` that narrows something.** The obvious fix for
the above is `gateway = 1`, and it is the dangerous one: gateway overrides `listen`, so the daemon
binds every interface, while Px's stock allow-list accepts every client that can route to the
machine. The daemon is unauthenticated to its clients by design — that is what keeps the credential
in one place — so the pair publishes authenticated egress through the user's own corporate account
to the LAN, and to whatever a VPN attaches them to. An `allow` of `*`, `*.*.*.*` or `0.0.0.0/0` is
refused for the same reason: it is the default wearing an explicit spelling.]

[DECISION: **the mismatch is reported where it is discovered, not only where it is configured.**
`proxy.check` prints which posture is in effect, and `docker.configure-corporate` warns when a
container proxy is set while the daemon is still loopback-only. The symptom otherwise is every
container pull timing out while the host is fine, which reads as a network problem rather than as a
setting — and the two halves are configured in different files, by different tasks, on different
days.]

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

Section 4 landed as `tasks/cert_sources.py` (all the parsing, pure and stdlib-only) plus
`inv certs.discover` in `tasks/certs.py`, `tests/unit/test_cert_sources.py`, and `docs/certs.md`'s
"Finding the certificate in the first place".

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

`certs.discover` was run for real against a fabricated corporate environment — a bundle named by two
environment variables and an npmrc at once (merged into one candidate with three origins), a
variable pointing at a file that does not exist (reported as a stale pointer), a JVM trust store,
and four separate verification-off settings across the environment, npmrc, curlrc and condarc. Both
bugs above came out of that run rather than out of the tests.

The exposure settings were checked against the real binary rather than its documentation: `px` is
installed on this machine, so `--gateway=1 --allow=172.17.0.0/16 --save` was run with
`XDG_CONFIG_HOME` redirected into a scratch directory, and it wrote `gateway = 1` and
`allow = 172.17.0.0/16` into a px.ini that the reader then parsed correctly. The user's own
`~/.config/px` was never touched — it does not exist.

[PITFALL: **`px --version` starts the daemon instead of printing a version**, which is why
`[packages.px-proxy]` carries `verify_cmd = "px --help"`. Hit live while checking whether px was
installed at all: the call hung for the full timeout and left a proxy running until it was killed.
The comment in setup.toml says this; running the command anyway is how it gets learned.]

[UNVERIFIED: **the Windows-side halves of `discover` have never run on Windows** — the registry
environment read, the group-policy thumbprint read, `WSLENV`, and the vendor globs. Their parsers
are tested against captured output shapes; what no machine here can check is that a real
`reg.exe query` prints what those fixtures assume.]
