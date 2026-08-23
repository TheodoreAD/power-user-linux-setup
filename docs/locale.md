# Locale

## Setup

```shell
inv system.set-locale
```

Runs `sudo localectl set-locale LANG=en_US.UTF-8`, writes to `/etc/locale.conf` (systemd-integrated,
persists across reboots), and is idempotent. Also runs as part of `inv setup`. `en_US.UTF-8` is
pre-generated on Ubuntu 24.04 — `locale-gen` is not needed.

## Verify

```shell
locale
```

All categories should show `en_US.UTF-8`.

## Pitfalls

- **Do not set `LC_ALL`** — it overrides all individual `LC_*` categories with no escape hatch,
  breaking intentional per-category overrides
- **Do not set every `LC_*` individually** — they all inherit from `LANG`; over-specifying creates
  maintenance burden with no benefit
- **Do not use `export LANG=...` in a shell profile** — session-only, does not survive reboot
- **A `C` or `POSIX` locale will break things** — Python throws Unicode errors, git and compiler
  output may be garbled
