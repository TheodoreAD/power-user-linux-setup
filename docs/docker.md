# Docker

Installed via apt-repo by `inv apt.install-repos` (or `inv setup`). Installs: `docker-ce`,
`docker-ce-cli`, `containerd.io`, `docker-buildx-plugin`, `docker-compose-plugin`.

`inv docker.configure` (part of `inv setup`) adds the current user to the `docker` group and
configures the daemon.

## Post-install

Group membership takes effect in new login sessions. Open a new terminal after running
`inv docker.configure` — no full logout needed.

Verify:

```shell
docker run hello-world
```

## Compose

Docker Compose v1 (`docker-compose`) is deprecated and unmaintained. Use the v2 plugin:

```shell
docker compose up
```

## Daemon config

`overlay2` storage driver and `systemd` cgroup driver are the defaults on Ubuntu 24.04 — no changes
needed for those.

Log limits and DNS are configured by `inv docker.configure` (also runs as part of `inv setup`):

```shell
inv docker.configure
```

This merges the following into `/etc/docker/daemon.json` and restarts the daemon only if something
changed. Existing keys not listed here are left untouched.

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  },
  "dns": ["1.1.1.1", "1.0.0.1", "8.8.8.8"]
}
```

**Log limits:** Docker's default log driver (`json-file`) writes to
`/var/lib/docker/containers/<id>/<id>-json.log` with no size cap, which will eventually fill the
disk on long-running or chatty containers. `max-size` caps each file before rotation; `max-file`
sets how many rotated files to keep. With the defaults above each container uses at most 150 MB of
log space (3 × 50 MB). Per-container overrides work via `--log-opt` or the `logging:` key in
docker-compose.

**DNS:** optional but makes containers use Cloudflare, matching `inv system.configure-dns`. Without
it, Docker falls back to `8.8.8.8` automatically. See [networking.md](networking.md).

## Troubleshooting

**Daemon masked** (`Loaded: masked`): `inv docker.configure` detects and fixes this automatically.
To fix manually:

```shell
sudo systemctl unmask docker
sudo systemctl start docker
```

**Socket permission error** (temporary workaround if the group change hasn't propagated):

```shell
sudo chown $USER:docker /var/run/docker.sock
```

## Corporate registries/mirrors (not automated yet)

Not covered by `inv docker.configure` or `inv certs.install` — tracked as a follow-up, documented
here so the mechanism doesn't have to be re-derived. Three distinct, easily-conflated pieces if this
network has a corporate registry mirror and/or TLS-inspecting proxy:

- **Registry pull-through mirror** (Docker Hub only) — `registry-mirrors` in
  `/etc/docker/daemon.json`, same merge mechanism `inv docker.configure` already uses for
  `log-driver`/`dns` above.
- **Daemon's own outbound proxy** — dockerd is a systemd service and does _not_ inherit the shell's
  `http_proxy`/`https_proxy`. Needs its own systemd drop-in:
  `/etc/systemd/system/docker.service.d/http-proxy.conf` with `Environment="HTTPS_PROXY=..."`, then
  `systemctl daemon-reload && systemctl restart docker`.
- **Containers' own proxy** (so processes _inside_ containers see it too) — not a daemon setting,
  goes in `~/.docker/config.json`'s `proxies` key.

**Cert-wise**, this is separate from `inv certs.install` — Docker doesn't read the OS trust store
the way `curl` does. A corporate registry behind the same TLS-inspecting proxy (see
[certs.md](certs.md)) needs its own per-registry CA file:
`/etc/docker/certs.d/<registry-host>/ca.crt`.

Also relevant if this is being configured under WSL2 with Docker Desktop's WSL integration:
`docker.configure` already detects that case (`docker` CLI present, no local `dockerd` —
`tasks/docker.py`) and skips, since the daemon isn't running inside the WSL guest at all. None of
the above applies there either — it goes in Docker Desktop's Windows-side settings instead.
