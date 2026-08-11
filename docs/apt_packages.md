# Apt packages

All apt packages are declared in `setup.toml` and installed via invoke tasks.
Each package has a `method` field that determines how it is installed:

| Method       | Command                | Description                                                                       |
| ------------ | ---------------------- | --------------------------------------------------------------------------------- |
| `apt`        | `inv apt.base`         | Standard packages from Ubuntu's default repos                                     |
| `apt-repo`   | `inv apt.repos`        | External repos — registers GPG key + sources, then installs                       |
| `deb-github` | `inv apt.deb`          | Latest `.deb` from a GitHub release page                                          |
| `deb-url`    | `inv apt.deb`          | `.deb` from a direct URL (e.g. Chrome, which self-manages its sources afterwards) |
| —            | `inv apt.configure`    | Write `/etc/apt/apt.conf.d/99-pulse` — disable dpkg progress bars                 |
| —            | `inv apt.refresh-keys` | Re-download all apt-repo GPG keys                                                 |
| —            | `inv apt.audit-keys`   | Audit key hygiene across all key stores                                           |

`inv apt.repos` is a two-phase command. Phase 1 registers all GPG keys and sources files
in one pass, then runs a single `apt update`. Phase 2 installs the packages. If a GPG key
URL or sources write fails for any entry (e.g. a dead URL), that repo is skipped with a
`WARNING:` message and the rest continue — a broken third-party repo does not abort the run.

Run everything at once:

```shell
inv setup
```

Or selectively:

```shell
sudo apt update && sudo apt full-upgrade -y
inv apt.configure
inv apt.base
inv apt.repos
inv apt.deb
```

!!! WARNING

    After apt commands you may see a list of packages suggested for removal:

    ```
    Use 'sudo apt autoremove' to remove them.
    ```

    Do NOT run this unless you know exactly what each package does.

## Adding or disabling packages

Edit `setup.toml`. To disable a package without deleting it, set `enabled = false`.
To add a new apt package where the section name matches the apt package name:

```toml
[packages.mypackage]
description = "..."
method = "apt"
tags = ["some-tag"]
```

If the apt package name differs from the section name, or you need multiple packages,
declare them explicitly:

```toml
[packages.mygroup]
description = "..."
method = "apt"
packages = ["pkg-one", "pkg-two"]
```

## GPG key hygiene

### Audit

Check the state of all apt key stores:

```shell
inv apt.audit-keys
```

Checks three locations and reports issues:

| Location                                     | Rule                                                                     | Auto-fixed                      |
| -------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------- |
| `/etc/apt/trusted.gpg`                       | Must be empty — any key here trusts **all** repos with no scoping        | Yes — cleared in live mode      |
| `/etc/apt/trusted.gpg.d/`                    | Only Ubuntu system keys expected; others are old-style (not `signed-by`) | No — reported for manual review |
| `/etc/apt/keyrings/`, `/usr/share/keyrings/` | No `~` backup files                                                      | Yes — removed in live mode      |

All repos declared in `setup.toml` use the modern `signed-by` approach with keys stored in `/usr/share/keyrings/` — the old global key stores should stay empty after initial cleanup.

`PULSE_DRY_RUN=1 inv apt.audit-keys` reports without changing anything.

### Refresh expired keys

Third-party apt repo keys can expire. To re-download all keys declared in `setup.toml`:

```shell
inv apt.refresh-keys
```

This re-fetches the key from each `gpg_url` and overwrites the file at `gpg_path` for
every enabled `apt-repo` entry — no need to look up per-repo commands.

See [gcloud.md](gcloud.md) for Google Cloud CLI setup.
