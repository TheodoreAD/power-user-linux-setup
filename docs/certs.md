# Corporate CA bundle

Many corporate networks run a TLS-inspecting proxy (Zscaler, Netskope, Palo Alto, etc.) that
terminates HTTPS and re-signs it with its own root CA. Every TLS client on the machine needs to
trust that CA, or verification fails everywhere (`SSL: CERTIFICATE_VERIFY_FAILED`, `x509:
certificate signed by unknown authority`, `unable to get local issuer certificate`). Installing it
into the OS trust store alone isn't enough — several common tools vendor their own CA bundle
instead of reading the OS one: Python (`certifi`), Node/npm, and the AWS CLI.

`inv certs.*` installs an IT-provided bundle into the OS trust store via
`update-ca-certificates`, then points those tools at the resulting merged bundle.

## Quick start

```shell
inv certs.check      # read-only — bundle/env-var/Java status, changes nothing
inv certs.install     # installs into the OS trust store, exports env vars for python/node/awscli
```

On a personal machine with no corporate CA configured, both exit cleanly with "nothing to
configure" — expected, not a failure.

## Config

Add a `[certs]` section to `~/.config/pulse/identity.toml` (see
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
   `NODE_EXTRA_CA_CERTS`, and `AWS_CA_BUNDLE`, all pointed at that *merged* bundle — not a
   corporate-only file, since those tools still need the public CAs too.

Re-running `inv certs.install` is idempotent: it compares the desired bundle text against what's
already installed and skips `update-ca-certificates` entirely when nothing changed.

## Format detection

The bundle's file extension is not trusted — `.crt`/`.cer`/`.pem` are filename conventions, not a
format guarantee, and IT-issued files show up as ASCII PEM, raw binary DER, or a Windows PKCS#7
`.p7b`/`.p7c` (common from AD Certificate Services) with no reliable way to tell from the name
alone. `certs.install` probes with `openssl` in this order and uses the first that parses:

1. `openssl x509 -noout -inform PEM` — already PEM, pass through.
2. `openssl x509 -inform DER -outform PEM` — single-cert DER, convert.
3. `openssl pkcs7 -print_certs -inform PEM` — PEM-armored PKCS#7, extract (root + intermediate).
4. `openssl pkcs7 -print_certs -inform DER` — DER-armored PKCS#7, extract (also seen from Windows
   AD CS — extension alone doesn't say which armor).

If none of the four parse, `certs.install` **fails loudly** rather than installing anything.
This is a deliberate departure from `update-ca-certificates`'s own behavior: it silently *skips*
a file it can't parse (just a warning), so a plain reinstall attempt with a bad file would
otherwise "succeed" while TLS verification keeps failing with no clear signal why. Inspect a
rejected file manually with `file <path>` or `openssl asn1parse -in <path>`.

## Java {: #java }

No JDK is installed or managed by this repo — Scala tooling uses Coursier's own private JVM
instead (see [scala.md](scala.md)), and nothing else here needs one. The `cacerts` import step is
purely conditional on `keytool` already being on `PATH`: a no-op today, and it activates
automatically without any further changes if a JDK is added independently later.

If a JDK is present, each cert in the bundle is imported into `$JAVA_HOME/lib/security/cacerts`
under aliases `pulse-corporate-0`, `pulse-corporate-1`, etc. (idempotent — checked via `keytool
-list` first, `storepass` is the Java default `changeit`).

## WSL

WSL2's trust store is fully independent of Windows' own. IT populating the Windows certificate
store via Group Policy/Intune does **not** carry over into WSL — `update-ca-certificates` still
has to run inside the WSL guest, regardless of NAT vs. mirrored networking mode (this is an
OS-trust-store issue, not a networking one). If the bundle needs to be pulled off the Windows side
first, that's a one-time manual copy (e.g. via `/mnt/c`) — this repo has no automation for reading
the Windows certificate store or shelling out to `certutil.exe`/`powershell.exe`; usually simplest
to just ask IT for the raw file directly.

## Uninstall / rotation

```shell
sudo rm /usr/local/share/ca-certificates/pulse-corporate.crt
sudo update-ca-certificates
```

Don't pass `--fresh` — it rebuilds the trust store from scratch and would also drop any *other*
locally-added certs, not just this one. Neither task prunes stale config on its own, so also
remove by hand:

- The `PULSE::certs` block from `~/.zshenv`.
- Any `pulse-corporate-*` Java aliases: `sudo keytool -delete -alias pulse-corporate-0 -keystore
  "$JAVA_HOME/lib/security/cacerts" -storepass changeit` (repeat per alias).

## Verify

Run this in a disposable container or VM, not the primary workstation — `certs.install` makes
real, persistent, root-owned changes to the system trust store, and a real corporate CA isn't
available outside a corporate network to test against anyway.

```shell
docker run --rm -it -v "$PWD":/repo -w /repo ubuntu:24.04 bash
apt update && apt install -y openssl ca-certificates python3

# Fixtures for each detection branch
openssl req -x509 -newkey rsa:2048 -sha256 -days 3650 -nodes \
  -keyout /tmp/test-ca.key -out /tmp/test-ca.pem -subj "/CN=Test Corp Root CA"
openssl x509 -in /tmp/test-ca.pem -outform DER -out /tmp/test-ca.der
openssl crl2pkcs7 -nocrl -certfile /tmp/test-ca.pem -out /tmp/test-ca.p7b
openssl crl2pkcs7 -nocrl -certfile /tmp/test-ca.pem -outform DER -out /tmp/test-ca-der.p7b
printf 'not a cert' > /tmp/garbage.txt   # must fail loudly, not silently

# End to end, no real corporate CA needed
PULSE_DRY_RUN=1 inv certs.install --bundle=/tmp/test-ca.pem
inv certs.install --bundle=/tmp/test-ca.pem

# Prove it actually works, not just that files were written
openssl genrsa -out /tmp/leaf.key 2048
openssl req -new -key /tmp/leaf.key -subj "/CN=test.example.com" -out /tmp/leaf.csr
openssl x509 -req -in /tmp/leaf.csr -CA /tmp/test-ca.pem -CAkey /tmp/test-ca.key \
  -CAcreateserial -out /tmp/leaf.pem -days 365 -sha256
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt /tmp/leaf.pem   # expect: OK

# Idempotency
inv certs.install --bundle=/tmp/test-ca.pem   # expect "already up to date", zshenv:ok not added

# Optional: Java branch
apt install -y default-jdk-headless
inv certs.install --bundle=/tmp/test-ca.pem
keytool -list -alias pulse-corporate-0 -keystore "$JAVA_HOME/lib/security/cacerts" -storepass changeit
```

## Genuine limitations

- **Real Windows-issued PKCS#7 bundles are untested** — only locally-generated `openssl`
  fixtures were used to build and verify the four detection branches (see Verify above).
- **The Java `cacerts` step is untested against a real JDK** — no JDK is present anywhere in this
  environment (see Java above). Reviewed-and-defensive, not proven.
- **`update-ca-certificates --fresh` interaction with other manually-added local certs is out of
  scope by design** — hence the "no `--fresh`" uninstall instructions above.
- **Docker registry mirrors, daemon proxy config, and per-registry `certs.d` are out of scope
  here** — a corporate registry behind the same TLS-inspecting proxy needs its own separate setup;
  see [docker.md](docker.md#corporate-registriesmirrors-not-automated-yet) for the mechanism
  (tracked as a follow-up, not covered by this task).

## See also

- [corporate-proxy.md](corporate-proxy.md) — the separate concern of authenticating *through* a
  corporate HTTP(S) proxy (Px daemon). This page is about trusting a TLS-inspection root CA;
  proxy auth is unrelated and doesn't require one to imply the other.
