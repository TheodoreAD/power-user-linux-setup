# Corporate CA bundle — verification

Companion to [`docs/certs.md`](../docs/certs.md). QA playbook for `inv certs.*` (`tasks/certs.py`) —
how the four detection branches were built and verified, and what's still untested.

## Verify

Run this in a disposable container or VM, not the primary workstation — `certs.install` makes real,
persistent, root-owned changes to the system trust store, and a real corporate CA isn't available
outside a corporate network to test against anyway.

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

- **Real Windows-issued PKCS#7 bundles are untested** — only locally-generated `openssl` fixtures
  were used to build and verify the four detection branches (see Verify above).
- **The Java `cacerts` step is untested against a real JDK** — no JDK is present anywhere in this
  environment. Reviewed-and-defensive, not proven.
