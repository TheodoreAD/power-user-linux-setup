# Corporate CA bundle

Many corporate networks run a TLS-inspecting proxy (Zscaler, Netskope, Palo Alto, etc.) that
terminates HTTPS and re-signs it with its own root CA. Every TLS client on the machine needs to
trust that CA, or verification fails everywhere (`SSL: CERTIFICATE_VERIFY_FAILED`,
`x509:
certificate signed by unknown authority`, `unable to get local issuer certificate`).
Installing it into the OS trust store alone isn't enough — several common tools vendor their own CA
bundle instead of reading the OS one: Python (`certifi`), Node/npm, and the AWS CLI.

`inv certs.*` installs an IT-provided bundle into the OS trust store via `update-ca-certificates`,
then points those tools at the resulting merged bundle.

## Quick start

```shell
inv certs.check      # read-only — bundle/env-var/Java status, changes nothing
inv certs.install     # installs into the OS trust store, exports env vars for python/node/awscli
```

On a personal machine with no corporate CA configured, both exit cleanly with "nothing to configure"
— expected, not a failure.

## Config

Add a `[certs]` section to `~/.config/power-user-linux-setup/identity.toml` (see
`config/identity.toml.example`):

```toml
[certs]
bundle = "/home/jsmith/Downloads/CorporateRootCA.crt"
```

A root + separate intermediate can be given as a list instead. `--bundle=path` on either task
overrides this for a one-off run without editing the file.

## What gets installed

1. Each configured file is format-detected and normalized to PEM (see below), then written to
   `/usr/local/share/ca-certificates/pulse-corporate.crt`.
2. `update-ca-certificates` merges it with the public CA set into
   `/etc/ssl/certs/ca-certificates.crt`.
3. A `PULSE::certs` block in `~/.zshenv` exports `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`,
   `NODE_EXTRA_CA_CERTS`, and `AWS_CA_BUNDLE`, all pointed at that _merged_ bundle — not a
   corporate-only file, since those tools still need the public CAs too.

**Step 3 requires zsh to be the login shell**, which is a prerequisite of this repo rather than a
preference: nothing here writes a file bash reads, so on a bash login shell those four exports reach
nothing and say nothing — the failure looks like a network fault, not a missing setting.
`certs.check` and `certs.install` both report it; the full reasoning, and why no bash-side file is
written instead, is in [wsl.md](wsl.md#assumptions-this-repo-makes-about-wsl) (it is not
WSL-specific, that is just where the prerequisites are listed).

Re-running `inv certs.install` is idempotent: it compares the desired bundle text against what's
already installed and skips `update-ca-certificates` entirely when nothing changed.

## Finding the certificate in the first place

```shell
inv certs.discover             # read-only — what this machine already uses, and what it turned off
inv certs.discover --install   # asks about each one, installs what you accept
```

`--from-windows` above answers "which roots exist on the Windows side that this distro doesn't
trust". `discover` answers a better question — **which certificate is this machine already using, or
being told to use** — and most of its routes name an exact file:

- **Environment variables** naming a bundle: `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`,
  `NODE_EXTRA_CA_CERTS`, `GIT_SSL_CAINFO`, `AWS_CA_BUNDLE`, `CARGO_HTTP_CAINFO`,
  `-Djavax.net.ssl.trustStore` inside `JAVA_TOOL_OPTIONS`, and the rest — read from the live shell,
  `/etc/environment` and the shell rc files. Somebody has already decided which file is the
  corporate CA; this just puts it where the OS trust store can see it.
- **The Windows side's own environment**, under WSL, read out of the registry
  (`HKLM\...\Session Manager\Environment` and `HKCU\Environment`). This is where IT sets those same
  variables machine-wide, nothing carries them across the boundary, and the value is an exact path
  reachable through `/mnt`. `WSLENV` is checked in the same pass: a certificate variable shared
  without the `/p` flag arrives holding a `C:\` path, so every Linux tool reading it looks
  configured and fails to open the file.
- **Config files**: npm's `cafile`, pip's `cert`, git's `http.sslCAInfo`, curl's `cacert`, conda's
  `ssl_verify`, gradle's `systemProp.javax.net.ssl.trustStore`.
- **Vendor install directories**, where a vendor writes a readable file at a documented path —
  Netskope's `C:\ProgramData\netskope\stagent\data\nscacert*.pem`. Zscaler's client connector
  injects into the Windows store and documents no fixed file, so for that one the store and the live
  issuer are the routes; hunting for a file is not a search that failed.
- **The Windows certificate store**, with roots **deployed by group policy or enterprise enrolment
  flagged** — read from the registry, where each subkey name is the certificate's thumbprint. That
  is IT deployment read directly, rather than inferred from what the public CA set lacks, and it is
  the ranking `--from-windows` on its own cannot produce. (The registry rather than
  `certutil -grouppolicy -store Root` because certutil's output is localized — a parser for it would
  work on an English machine and quietly find nothing on a German one.)
- **The live connection**: the issuer that actually signed the certificate served to this machine,
  and whether it verified. An issuer that _doesn't_ verify names the exact root to install.

Everything found is reported with where it was found; a value naming a file that doesn't exist is
reported as a stale pointer rather than silently dropped. `--install` then asks about each
certificate **individually and defaults to no** — trusting a root CA means trusting whoever holds
its private key for every TLS connection this machine makes, so it is a decision to put in front of
someone, not a step to complete. A non-interactive run installs nothing.

### Where verification was switched off instead

`discover` also reports the opposite of a certificate: `GIT_SSL_NO_VERIFY`,
`NODE_TLS_REJECT_UNAUTHORIZED=0`, `PYTHONHTTPSVERIFY=0`, npm's `strict-ssl=false`, pip's
`trusted-host`, conda's `ssl_verify: false`, curl's `--insecure`, `git config http.sslVerify false`.

Each one is somebody who hit exactly this problem and turned the check off rather than installing
the CA — a permanent, silent downgrade that no error message will mention again. Each is reported
with the command that undoes it, and **the order matters: install the CA first, undo the bypass
second.** Removing it while the trust store still can't verify breaks the tool that was working a
moment ago, and the natural next move is to put the bypass back for good. Nothing removes them
automatically; a bypass may also exist for an unrelated host this CA doesn't cover.

## Format detection

The bundle's file extension is not trusted — `.crt`/`.cer`/`.pem` are filename conventions, not a
format guarantee, and IT-issued files show up as ASCII PEM, raw binary DER, or a Windows PKCS#7
`.p7b`/`.p7c` (common from AD Certificate Services) with no reliable way to tell from the name
alone. `certs.install` probes with `openssl` in this order and uses the first that parses:

1. `openssl x509 -noout -inform PEM` — already PEM, pass through.
2. `openssl x509 -inform DER -outform PEM` — single-cert DER, convert.
3. `openssl pkcs7 -print_certs -inform PEM` — PEM-armored PKCS#7, extract (root + intermediate).
4. `openssl pkcs7 -print_certs -inform DER` — DER-armored PKCS#7, extract (also seen from Windows AD
   CS — extension alone doesn't say which armor).

If none of the four parse, `certs.install` **fails loudly** rather than installing anything. This is
a deliberate departure from `update-ca-certificates`'s own behavior: it silently _skips_ a file it
can't parse (just a warning), so a plain reinstall attempt with a bad file would otherwise "succeed"
while TLS verification keeps failing with no clear signal why. Inspect a rejected file manually with
`file <path>` or `openssl asn1parse -in <path>`.

## Java {: #java }

No JDK is installed or managed by this repo — Scala tooling uses Coursier's own private JVM instead
(see [scala.md](scala.md)), and nothing else here needs one. The `cacerts` import step is purely
conditional on `keytool` already being on `PATH`: a no-op today, and it activates automatically
without any further changes if a JDK is added independently later.

If a JDK is present, each cert in the bundle is imported into `$JAVA_HOME/lib/security/cacerts`
under aliases `pulse-corporate-0`, `pulse-corporate-1`, etc. (idempotent — checked via
`keytool
-list` first, `storepass` is the Java default `changeit`).

## WSL

WSL2's trust store is fully independent of Windows' own. IT populating the Windows certificate store
via Group Policy/Intune does **not** carry over into WSL — `update-ca-certificates` still has to run
inside the WSL guest, regardless of NAT vs. mirrored networking mode (this is an OS-trust-store
issue, not a networking one).

`--from-windows` bridges that without a manual file copy:

```shell
inv certs.check --from-windows      # read-only — names the roots this distro doesn't trust yet
inv certs.install --from-windows    # installs them, alongside anything else configured
```

It reads `Cert:\LocalMachine\Root` and `Cert:\CurrentUser\Root` through WSL interop
(`powershell.exe`, so `/etc/wsl.conf`'s `[interop] enabled` has to be on — `inv wsl.check` reports
that) and **installs only the roots this distro doesn't already trust**. The Windows Root store
carries ~50 public CAs alongside the corporate one; trusting all of them would add trust Ubuntu's
own `ca-certificates` deliberately doesn't carry, so the public set is subtracted by SHA-256
fingerprint rather than filtered by name. Every remaining root is printed by subject before anything
is installed — read that list; it is the whole review step.

The filtered export is kept at `~/.local/state/power-user-linux-setup/windows-root-extras.pem`,
which is also what makes a re-run idempotent. `--from-windows` composes with `--bundle` and with a
configured `[certs] bundle` rather than replacing either, so a machine with both an IT-provided file
and a Windows-only root installs both. Outside WSL the flag refuses rather than guessing.

Asking IT for the raw file and pointing `--bundle` at it is still the most direct route when that's
available; this exists for the common case where the root is already on the Windows side and nobody
has a copy to hand out.

## Uninstall / rotation

```shell
sudo rm /usr/local/share/ca-certificates/pulse-corporate.crt
sudo update-ca-certificates
```

Don't pass `--fresh` — it rebuilds the trust store from scratch and would also drop any _other_
locally-added certs, not just this one. Neither task prunes stale config on its own, so also remove
by hand:

- The `PULSE::certs` block from `~/.zshenv`.
- Any `pulse-corporate-*` Java aliases:
  `sudo keytool -delete -alias pulse-corporate-0 -keystore
  "$JAVA_HOME/lib/security/cacerts" -storepass changeit`
  (repeat per alias).

## Genuine limitations

- **Real Windows-issued PKCS#7 bundles are untested** — only locally-generated test fixtures were
  used to build and verify the four detection branches.
- **`--from-windows` has never run against a real Windows certificate store.** The PowerShell
  payload, the PEM parsing, the fingerprint diff and the ordering are unit-tested against captured
  fixtures and a real (locally-generated) certificate; what nobody here can test is that
  `Get-ChildItem Cert:\...` on a domain-joined machine emits what those fixtures assume. Run
  `inv certs.check --from-windows` first and read the subjects it prints before installing.
- **The Java `cacerts` step is untested against a real JDK** — no JDK is present anywhere in this
  environment (see Java above). Reviewed-and-defensive, not proven.
- **`update-ca-certificates --fresh` interaction with other manually-added local certs is out of
  scope by design** — hence the "no `--fresh`" uninstall instructions above.
- **Docker registry mirrors, daemon proxy config, and per-registry `certs.d` are out of scope here**
  — docker doesn't read the OS trust store, so a corporate registry behind the same TLS-inspecting
  proxy needs the certificate written per registry. `inv docker.configure-corporate` does that, from
  this same `[certs]` bundle; see [docker.md](docker.md#corporate-networks).

## See also

- [corporate-proxy.md](corporate-proxy.md) — the separate concern of authenticating _through_ a
  corporate HTTP(S) proxy (Px daemon). This page is about trusting a TLS-inspection root CA; proxy
  auth is unrelated and doesn't require one to imply the other.
