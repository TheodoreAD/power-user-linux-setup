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

## Corporate networks

`inv docker.configure` handles neither a registry mirror nor a proxy nor a corporate CA —
`inv docker.configure-corporate` does, driven entirely by an optional `[docker]` table in
`~/.config/power-user-linux-setup/identity.toml` (see `config/identity.toml.example`):

```toml
[docker]
registry_mirrors = ["https://registry.corp.example.com"]
proxy = "http://127.0.0.1:3128" # dockerd's own outbound proxy
container_proxy = "http://172.17.0.1:3128" # what processes inside containers see
no_proxy = "localhost,127.0.0.1,*.corp.example.com"
registries = ["registry.corp.example.com:5000"]
```

Each key is independent and a key you leave out is simply not configured; with no `[docker]` table
at all the task exits cleanly having done nothing. Four mechanisms, easy to conflate and not
interchangeable:

- **Registry pull-through mirror** (Docker Hub only) — `registry-mirrors` merged into
  `/etc/docker/daemon.json`, the same merge `inv docker.configure` uses for `log-driver`/`dns`.
- **The daemon's own outbound proxy** — dockerd is a systemd service and does _not_ inherit the
  shell's `http_proxy`/`https_proxy`, so this is a drop-in at
  `/etc/systemd/system/docker.service.d/http-proxy.conf`, followed by `daemon-reload` and a restart.
- **Containers' own proxy** — `proxies.default` in `~/.docker/config.json`, injected as environment
  variables when a container is created. **Not the same address as the daemon's**: dockerd runs in
  the host's network namespace and reaches a local Px at `127.0.0.1:3128`, while `127.0.0.1` inside
  a container is that container's own loopback. This one has to be the bridge gateway
  (`172.17.0.1`), and Px answers there only once `[proxy] gateway`/`allow` are set — see
  [corporate-proxy.md](corporate-proxy.md#reaching-the-daemon-from-a-container), which is also where
  the reason `allow` is mandatory lives. `docker.configure-corporate` warns when this key is set
  while the daemon is still loopback-only. That is why the two are separate keys rather than one
  value used twice.
- **Per-registry CA** — docker doesn't read the OS trust store the way `curl` does, so
  `inv certs.install` alone does nothing for a registry pull. Each host in `registries` gets the
  same bundle written to `/etc/docker/certs.d/<host>/ca.crt`, resolved from the `[certs]` table so
  the two tasks can't disagree about which file the corporate CA is.

Under WSL2 with Docker Desktop's WSL integration, the task detects that there is no local `dockerd`
and stops: none of the above applies in that distro, and the settings belong in Docker Desktop's
Windows-side UI instead.

**Not verified against a running daemon** — the writers are unit-tested, but restarting a real
dockerd isn't something this repo's test run does. Run
`PULSE_DRY_RUN=1 inv
docker.configure-corporate` first; it reports what each piece would do and
changes nothing.

## See also

- [Kubernetes](kubernetes.md) — the cluster tooling built on top of it
- [Dev container](dev-container.md) — running this whole setup inside a container
- [Updating and removing](updating.md) — pruning images and caches safely
