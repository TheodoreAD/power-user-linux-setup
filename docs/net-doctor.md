# Network doctor

Answers one question: **which of the hosts a PULSE run needs are reachable from here, by what route,
and when one isn't — what do I type next.**

```shell
python3 tasks/netdoctor.py       # nothing installed yet: runs on the distro's own python3
inv net.check                    # the same code, once you have an inv
inv net.check --json-output      # machine-readable
```

It is read-only. It resolves names, opens connections and reads response headers; it never sends a
credential — including when it asks a proxy what authentication it wants, which is a bare `CONNECT`
with no `Proxy-Authorization` header.

## Why it isn't just "is the internet up"

A corporate network that blocks `pypi.org` while allowing `github.com` is completely ordinary: the
sanctioned path to Python packages is an internal Artifactory/Nexus mirror. Nothing about that is
visible from the outside, though — `uv` cheerfully installs a managed Python (which comes from
GitHub) and then fails on the first package, which reads as "uv is broken". The same goes for a
TLS-inspecting proxy (every https download fails with a certificate error that looks like a server
problem) and for a proxy that wants NTLM (a 407 nobody sees, buried in curl's exit code).

Each of those has a different fix, and each is a one-line diagnosis if something actually asks the
question per host.

## What it checks

| Layer            | What it asks                                                                                                                            |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| DNS              | does each host resolve; does a public resolver (1.1.1.1) answer a direct UDP query                                                      |
| TCP              | does the connection open — directly, or `CONNECT` through the configured proxy                                                          |
| TLS              | does the chain verify, and if not, **who issued the certificate we were handed**                                                        |
| HTTP             | the status code, and the `Date` header (which is how clock skew is detected)                                                            |
| this machine     | proxy env vars, `/etc/environment`, apt proxy config, pip/uv/npm/git indexes, `/etc/resolv.conf` and where it came from, extra CA roots |
| the Windows side | under WSL only: the host's proxy from `reg.exe`/`netsh.exe`, its PAC file, `/etc/wsl.conf`, `%USERPROFILE%\.wslconfig`                  |

The endpoints are the ones a run genuinely depends on — PyPI and files.pythonhosted.org for every
`uv tool install`, astral.sh and GitHub for uv and the `deb-github` packages, the Ubuntu archives
for apt, npm/nodejs/docker/microsoft for the rest. `--quick` probes only the ones that gate a
bootstrap; `--full` also probes every URL declared in `setup.toml`, so a newly added apt repo or
`.deb` URL is covered without anyone maintaining a second list.

## What it tells you to do

Every finding ends in commands. The ones it can produce:

- **PyPI blocked while GitHub answers** → export `UV_DEFAULT_INDEX`/`PIP_INDEX_URL`, reusing an
  internal index already configured on this machine if there is one.
- **The certificate was issued by something this machine doesn't trust** → the issuer's name, and
  `inv certs.install --bundle …` ([certs.md](certs.md)).
- **The proxy answered 407** → which schemes it offered, and `inv proxy.install`
  ([corporate-proxy.md](corporate-proxy.md)).
- **Windows has a proxy configured and this distro doesn't** → the address it found, the `export`
  line for right now, and the `.wslconfig` block that fixes it permanently ([wsl.md](wsl.md)).
- **Nothing resolves** → what `/etc/resolv.conf` is and where it came from. Under WSL this is one
  finding, not eight: everything else failed for the same reason.
- **TCP connects but TLS stalls** → a path-MTU black hole, the classic VPN-in-front-of-WSL symptom.
- **The clock is more than five minutes out** → certificate validation fails on skew, and a WSL
  distro's clock drifts when the Windows host sleeps.
- **Public DNS is blocked but the local resolver works** → the normal corporate shape, and a warning
  _not_ to "fix" DNS by pointing it at 1.1.1.1, which would break internal names.

## It runs before anything is installed

`bootstrap.sh` runs it (`--quick`) before its first download, so a blocked network is diagnosed up
front rather than surfacing as a `curl: (7)` or a uv resolver error several screens later. That is
advisory — it prints, waits five seconds and continues, because a probe is not authoritative about a
network that might route the real request differently. `PULSE_SKIP_PREFLIGHT=1` skips it.

Being able to run there is what shapes the module: `tasks/netdoctor.py` uses the **standard library
only**, stays within **Python 3.12** (Ubuntu 24.04's system Python — this repo's target), imports
nothing from `tasks/`, and is executed as a file rather than imported as part of the package — so it
works before uv, invoke, or this repo's venv exist. Tests enforce all three, and CI runs it under a
real 3.12.

## Limits

- It probes; it doesn't authenticate. A proxy that would accept the run's real credentials still
  shows as 407 here — that is the finding, not a failure.
- The PAC file is scanned for the `PROXY host:port` literals it names, not interpreted. A PAC whose
  choice of proxy depends on its JavaScript logic will list all of the candidates.
- The certificate issuer is read by scanning the DER for the commonName OID rather than by a full
  X.509 parse — enough to answer "who signed this, if not a public CA", which is the only question
  asked of it.
- A finding is a diagnosis, not a change: nothing here edits config, installs a CA, or exports a
  variable. The commands it prints are yours to run.
