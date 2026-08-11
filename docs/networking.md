# Networking

## Corporate proxy

For authenticating HTTP(S) proxies (common on corporate networks) — detecting what auth scheme is
required and running a local unauthenticated daemon so apps never see the real credential — see
[corporate-proxy.md](corporate-proxy.md), not this page. This page covers DNS only.

## DNS

Ubuntu 24.04 uses **systemd-resolved** exclusively. `resolvconf` is gone — do not use it.

DNS is configured via a drop-in file at `/etc/systemd/resolved.conf.d/pulse-dns.conf`, managed by `inv system.dns`:

```shell
inv system.dns
# or with custom servers:
inv system.dns --primary=9.9.9.9 --secondary=149.112.112.112 --fallback=8.8.8.8
```

### Default servers

| Server    | IP                     | Why                                              |
| --------- | ---------------------- | ------------------------------------------------ |
| Primary   | `1.1.1.1` (Cloudflare) | Fastest globally, no query logging, no filtering |
| Secondary | `1.0.0.1` (Cloudflare) | Same, alternate                                  |
| Fallback  | `8.8.8.8` (Google)     | Reliable fallback if Cloudflare unreachable      |

Cloudflare is preferred over Google for privacy: Cloudflare does not log queries or sell DNS data.

### Why DNSSEC is disabled

`DNSSEC=no` is intentional. DNSSEC breaks:

- Corporate VPNs and split-horizon DNS
- Docker's internal DNS resolver (`127.0.0.11`)
- Some self-signed local services

The security benefit for a development workstation is marginal compared to the breakage risk.

### Why DNS-over-TLS is disabled

`DNSOverTLS=no` is intentional. It adds ~50 ms latency on cold connections and interferes with `.local` mDNS resolution used by some dev tools and printers. Not worth it for a workstation.

### Verifying

```shell
resolvectl status
# look for: DNS Servers: 1.1.1.1 1.0.0.1
```

### Drop-in file location

`/etc/systemd/resolved.conf.d/pulse-dns.conf` — a PULSE sentinel block wraps the `[Resolve]` section so the file is idempotent across runs and safe to edit manually outside the block.

## Docker DNS

Docker containers use their own internal resolver (`127.0.0.11`) for container-to-container DNS, but for external resolution they read the host's `/etc/resolv.conf` at container start — with a catch.

With systemd-resolved active, `/etc/resolv.conf` contains `nameserver 127.0.0.53` (the stub listener). That address is only reachable on the host's loopback interface, not from inside a container's network namespace. Docker detects this and **silently falls back to `8.8.8.8`**, ignoring the Cloudflare servers configured by `inv system.dns`.

Without explicit config, Docker falls back to Google DNS (`8.8.8.8`) automatically — containers resolve fine, just not via Cloudflare. To make containers match the host DNS, set it explicitly in `/etc/docker/daemon.json` — see [docker.md](docker.md).
