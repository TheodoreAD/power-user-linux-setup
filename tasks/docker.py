import json
import re
import shlex
import tempfile
from pathlib import Path
from typing import cast

from invoke import Context, Exit, task

from . import certs, proxy, util

_DAEMON_JSON = Path("/etc/docker/daemon.json")

DOCKER_CONFIG = Path.home() / ".docker" / "config.json"
CREDS_STORE = "secretservice"
CREDENTIAL_HELPER = f"docker-credential-{CREDS_STORE}"
# Nothing resolves, so a stray entry left by an interrupted probe can never be used against a real
# registry. The secret is a constant for the same reason it is discardable: it is compared against
# what comes back, and it is never anyone's credential.
_PROBE_SERVER = "https://pulse-credential-store-check.invalid"
_PROBE_USERNAME = "pulse-check"
_PROBE_SECRET = "pulse-round-trip"
# The fields an `auths` entry can carry a secret in. `auth` is the base64 user:password pair docker
# writes without a helper; `identitytoken` is what a registry's OAuth flow leaves; `password` appears
# in hand-written and third-party-generated configs. Everything else in an entry is bookkeeping.
_SECRET_FIELDS = ("auth", "identitytoken", "password")

_DEFAULTS: util.JsonObject = {
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "50m",
        "max-file": "3",
    },
    "dns": ["1.1.1.1", "1.0.0.1", "8.8.8.8"],
}


def _is_subset(defaults: util.JsonObject, existing: util.JsonObject) -> bool:
    for key, value in defaults.items():
        current = existing.get(key)
        if isinstance(value, dict):
            if not isinstance(current, dict) or not _is_subset(value, current):
                return False
        elif current != value:
            return False
    return True


def _merge(base: util.JsonObject, updates: util.JsonObject) -> util.JsonObject:
    result: util.JsonObject = {**base}
    for key, value in updates.items():
        current = result.get(key)
        if isinstance(value, dict) and isinstance(current, dict):
            result[key] = _merge(current, value)
        else:
            result[key] = value
    return result


def _ensure_running(c: Context) -> None:
    if not util.has_systemd():
        print("[docker] no systemd — daemon.json/group updated, but nothing to restart here")
        return
    if c.run("systemctl is-enabled docker", hide=True, warn=True).stdout.strip() == "masked":
        c.run(f"{util.SUDO} systemctl unmask docker")
        print("[docker] daemon was masked — unmasked")
    c.run(f"{util.SUDO} systemctl restart docker")


def _read_daemon_json(c: Context) -> util.JsonObject:
    if not _DAEMON_JSON.exists():
        return {}
    return cast(util.JsonObject, util.parse_json(c.run(f"{util.SUDO} cat {_DAEMON_JSON}", hide=True).stdout))


def _configure_group(c: Context, user: str) -> None:
    groups = c.run(f"id -nG {user}", hide=True).stdout.split()
    if "docker" not in groups:
        c.run(f"{util.SUDO} usermod -aG docker {user}")
        print(f"[docker] {user} added to docker group — open a new terminal to pick it up")


def _write_daemon_json(c: Context, config: util.JsonObject) -> None:
    updated = json.dumps(config, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write(updated)
        tmp = f.name
    c.run(f"{util.SUDO} mkdir -p {_DAEMON_JSON.parent} && {util.SUDO} install -m 0644 {tmp} {_DAEMON_JSON} && rm {tmp}")


def _configure_daemon_json(c: Context) -> None:
    existing = _read_daemon_json(c)
    if _is_subset(_DEFAULTS, existing):
        print("[docker] daemon.json already configured — nothing to do")
        _ensure_running(c)
        return

    _write_daemon_json(c, _merge(existing, _DEFAULTS))
    _ensure_running(c)
    print("[docker] daemon.json updated, daemon restarted")


@task
def configure(c: Context):
    """Merge log limits and DNS into /etc/docker/daemon.json, add user to docker group."""
    util.ensure_sudo()  # standalone-safe: no sudo call inside c.run may prompt
    if util.is_docker_desktop_wsl_integration():
        print(
            "[docker] `docker` CLI found but no local dockerd — nothing to configure here. "
            "This looks like Docker Desktop's WSL integration: there is no local docker.service, "
            "so daemon.json/systemctl have nothing to act on. Manage Docker Desktop settings from "
            "Windows instead. See docs/wsl.md."
        )
        return

    if util.DRY_RUN:
        if not util.command_exists("docker"):
            print("[docker] MISSING")
            return
        user = util.current_user()
        in_group = "docker" in c.run(f"id -nG {user}", hide=True).stdout.split()
        cfg_ok = _is_subset(_DEFAULTS, _read_daemon_json(c))
        print(f"[docker] group:{util.ok_label(in_group)}  daemon.json:{util.ok_label(cfg_ok)}")
        return

    if not util.command_exists("docker"):
        print("[docker] not installed — skipping")
        return

    _configure_group(c, util.current_user())
    _configure_daemon_json(c)


# ---------------------------------------------------------------------------
# Corporate network wiring. Four mechanisms that are easy to conflate and are not interchangeable:
# a registry mirror (daemon.json), the daemon's own outbound proxy (a systemd drop-in — dockerd is
# a service and inherits nothing from a shell), the proxy processes *inside* containers see
# (~/.docker/config.json), and a per-registry CA (docker doesn't read the OS trust store).
# See docs/docker.md.

_PROXY_DROPIN = Path("/etc/systemd/system/docker.service.d/http-proxy.conf")
_CERTS_D = Path("/etc/docker/certs.d")
# A registry directory name is host[:port]; anything else is a config typo, and these values reach
# a shell as a path.
_REGISTRY_RE = re.compile(r"^[A-Za-z0-9.\-]+(:\d{1,5})?$")


def _proxy_dropin(proxy: str, no_proxy: str | None) -> str:
    """The systemd drop-in that puts dockerd's own outbound traffic through a proxy — image pulls,
    not container traffic. Both variables are set: dockerd reads the upper-case names, and a proxy
    that serves plain HTTP registries as well as HTTPS ones needs both pointed at it.
    """
    lines = [
        "# Written by `inv docker.configure-corporate` — see docs/docker.md.",
        "[Service]",
        f'Environment="HTTP_PROXY={proxy}"',
        f'Environment="HTTPS_PROXY={proxy}"',
    ]
    if no_proxy:
        lines.append(f'Environment="NO_PROXY={no_proxy}"')
    return "\n".join(lines) + "\n"


def _with_container_proxy(config: util.JsonObject, proxy: str, no_proxy: str | None) -> util.JsonObject:
    """`proxies.default` merged into ~/.docker/config.json, leaving credentials and everything else
    in that file untouched. docker injects these as environment variables when a container is
    created — which is why this address is not the daemon's: 127.0.0.1 inside a container is the
    container's own loopback, and a local Px listening on the host's loopback is unreachable from
    there.
    """
    default: util.JsonObject = {"httpProxy": proxy, "httpsProxy": proxy}
    if no_proxy:
        default["noProxy"] = no_proxy
    return _merge(config, {"proxies": {"default": default}})


def _mirror_config(mirrors: list[str]) -> util.JsonObject:
    """The daemon.json fragment for a pull-through mirror. A cast because JsonObject's list arm is
    list[Json] and a list[str] is not that — invariance, not a real type mismatch."""
    return cast(util.JsonObject, {"registry-mirrors": list(mirrors)})


def _configure_registry_mirrors(c: Context, mirrors: list[str]) -> bool:
    desired = _mirror_config(mirrors)
    existing = _read_daemon_json(c)
    if _is_subset(desired, existing):
        print("[docker-corporate] registry mirrors already in daemon.json")
        return False
    _write_daemon_json(c, _merge(existing, desired))
    print(f"[docker-corporate] {len(mirrors)} registry mirror(s) written to {_DAEMON_JSON}")
    return True


def _configure_daemon_proxy(c: Context, proxy: str, no_proxy: str | None) -> bool:
    desired = _proxy_dropin(proxy, no_proxy)
    if util.sudo_read(c, _PROXY_DROPIN) == desired:
        print("[docker-corporate] daemon proxy drop-in already current")
        return False
    c.run(f"{util.SUDO} mkdir -p {_PROXY_DROPIN.parent}")
    util.sudo_write(c, _PROXY_DROPIN, desired)
    print(f"[docker-corporate] daemon proxy written to {_PROXY_DROPIN}")
    return True


def _warn_if_daemon_is_loopback_only(container_proxy: str) -> None:
    """A container-side proxy pointing at a local Px that only listens on loopback is config that
    reads correctly and cannot work: 127.0.0.1 inside a container is the container's own loopback,
    and Px binds 127.0.0.1 by default. Said here because the symptom — every pull timing out while
    the host is fine — points at the network rather than at this setting.
    """
    if "127.0.0.1" in container_proxy or "localhost" in container_proxy:
        print(
            "[docker-corporate] container_proxy names loopback, which inside a container is the "
            "container's own — it will not reach a proxy on the host. Use the bridge gateway "
            "(172.17.0.1) and see docs/corporate-proxy.md's gateway section."
        )
        return
    if util.command_exists("px") and not proxy.accepts_remote_clients():
        print(
            "[docker-corporate] the local px daemon listens on 127.0.0.1 only, so containers "
            "cannot reach it at that address. Set [proxy] gateway and allow in identity.toml, "
            "then re-run `inv proxy.fix` — see docs/corporate-proxy.md."
        )


def _configure_container_proxy(proxy_url: str, no_proxy: str | None) -> None:
    _warn_if_daemon_is_loopback_only(proxy_url)
    config = _read_docker_config()
    updated = _with_container_proxy(config, proxy_url, no_proxy)
    if updated == config:
        print("[docker-corporate] container proxy already set")
        return
    DOCKER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    # 0600 before the write, for the same reason _write_creds_store does it: this file can hold
    # credentials, and a new one created under the default umask is world-readable in between.
    DOCKER_CONFIG.touch(mode=0o600, exist_ok=True)
    DOCKER_CONFIG.write_text(json.dumps(updated, indent=2) + "\n")
    print(f"[docker-corporate] container proxy written to {DOCKER_CONFIG}")


def _configure_registry_certs(c: Context, registries: list[str]) -> None:
    """Give each configured registry the corporate CA, from the same file `inv certs.install` uses.

    Docker doesn't read the OS trust store, so trusting the inspecting proxy system-wide does
    nothing for a registry pull — that needs the certificate at this exact per-registry path.
    """
    bundle = certs.corporate_bundle_text(c)
    if bundle is None:
        print(
            "[docker-corporate] registries configured but no corporate CA is — add a [certs] "
            "bundle to identity.toml (see docs/certs.md), then re-run. Skipping certs.d."
        )
        return
    for host in registries:
        if not _REGISTRY_RE.match(host):
            raise RuntimeError(
                f"[docker] {host!r} is not a host[:port] registry name — refusing to build a path from it"
            )
        path = _CERTS_D / host / "ca.crt"
        if util.sudo_read(c, path) == bundle:
            print(f"[docker-corporate] {host}: CA already current")
            continue
        c.run(f"{util.SUDO} mkdir -p {shlex.quote(str(path.parent))}")
        util.sudo_write(c, path, bundle)
        print(f"[docker-corporate] {host}: corporate CA written to {path}")


def _corporate_status(c: Context, cfg: util.DockerSection) -> None:
    daemon = _read_daemon_json(c)
    mirrors = _is_subset(_mirror_config(cfg["registry_mirrors"]), daemon) if "registry_mirrors" in cfg else None
    dropin = bool(util.sudo_read(c, _PROXY_DROPIN)) if "proxy" in cfg else None
    container = _read_docker_config().get("proxies") is not None if "container_proxy" in cfg else None
    parts = [
        f"{label}:{'skip' if state is None else util.ok_label(state)}"
        for label, state in (("mirrors", mirrors), ("daemon-proxy", dropin), ("container-proxy", container))
    ]
    print(f"[docker-corporate] {'  '.join(parts)}")


def _apply_corporate(c: Context, cfg: util.DockerSection) -> bool:
    """Each piece runs only if its key is configured. Returns whether dockerd needs restarting —
    the certs.d files don't need one (the daemon reads them per connection), and the container-side
    proxy isn't a daemon setting at all.
    """
    restart = False
    if mirrors := cfg.get("registry_mirrors"):
        restart |= _configure_registry_mirrors(c, mirrors)
    if proxy := cfg.get("proxy"):
        restart |= _configure_daemon_proxy(c, proxy, cfg.get("no_proxy"))
    if container_proxy := cfg.get("container_proxy"):
        _configure_container_proxy(container_proxy, cfg.get("no_proxy"))
    if registries := cfg.get("registries"):
        _configure_registry_certs(c, registries)
    return restart


@task
def configure_corporate(c: Context):
    """Wire docker into a corporate network: registry mirror, the daemon's own outbound proxy, the
    proxy processes inside containers see, and the corporate CA per registry. Each piece is driven
    by a key in identity.toml's [docker] table and skipped when that key is absent; a machine with
    no [docker] table exits cleanly having done nothing. See docs/docker.md.
    """
    util.ensure_sudo()  # standalone-safe: no sudo call inside c.run may prompt
    if util.is_docker_desktop_wsl_integration():
        print(
            "[docker-corporate] `docker` CLI found but no local dockerd — this looks like Docker "
            "Desktop's WSL integration. There is no daemon in this distro to configure; set the "
            "proxy, registry mirror and CA in Docker Desktop's own Windows-side settings."
        )
        return
    cfg = util.load_docker_override()
    if not cfg:
        print(
            "[docker-corporate] no [docker] table in ~/.config/power-user-linux-setup/identity.toml "
            "— nothing to configure (see config/identity.toml.example)."
        )
        return
    if not util.command_exists("docker"):
        print("[docker-corporate] docker not installed — skipping")
        return

    if util.DRY_RUN:
        _corporate_status(c, cfg)
        return

    if _apply_corporate(c, cfg) and util.has_systemd():
        # daemon-reload first: a drop-in systemd hasn't re-read is a file with no effect, and the
        # restart would look like it applied.
        c.run(f"{util.SUDO} systemctl daemon-reload")
        _ensure_running(c)
        print("[docker-corporate] dockerd restarted")


def _read_docker_config() -> util.JsonObject:
    if not DOCKER_CONFIG.exists():
        return {}
    return cast(util.JsonObject, util.parse_json(DOCKER_CONFIG.read_text()))


def _plaintext_secret_hosts(config: util.JsonObject) -> list[str]:
    """The `auths` hosts whose entry still carries a secret in the file itself.

    Not every `auths` entry is a credential: docker leaves `{"<host>": {}}` behind after a logout, and
    an entry pointing at a helper carries no secret either. Counting the whole mapping would report a
    credential that is not there — and would keep reporting one forever after a successful migration,
    which is how a warning stops being read.
    """
    auths = config.get("auths")
    if not isinstance(auths, dict):
        return []
    return [
        host
        for host, entry in auths.items()
        if isinstance(entry, dict) and any(entry.get(field) for field in _SECRET_FIELDS)
    ]


def _plaintext_auth_count(config: util.JsonObject) -> int:
    """How many registries still hold a secret in the file. Counted, never named: a registry hostname
    here is likely to be work infrastructure, and this output goes into a public repo's CI logs and an
    agent's transcript."""
    return len(_plaintext_secret_hosts(config))


def _purge_plaintext_auths() -> tuple[int, int]:
    """Strip the secret fields from every `auths` entry that has them, then drop any entry left
    holding nothing at all. Returns (hosts whose secret was removed, entries removed outright).

    Both halves match what docker's own code does, read from `docker/cli` rather than assumed:

    - **A logout deletes the entry.** `nativeStore.Erase` erases from the helper and then delegates
      to `fileStore.Erase`, which is a `delete()` on the `auths` map — so an entry stripped of its
      secret and left in place is not "what docker leaves", it is a state docker never produces.
    - **An entry with no secret is a *login* artifact.** `nativeStore.Store` writes the credential to
      the helper, blanks `Username`/`Password`/`IdentityToken`, and saves the remainder to the file
      to keep the email. So a secretless entry means a live helper-backed login, and one holding an
      email is docker's own bookkeeping — left alone. One holding nothing is residue with no secret,
      no email and no purpose, and it goes.
    """
    config = _read_docker_config()
    auths = config.get("auths")
    if not isinstance(auths, dict):
        return 0, 0
    hosts = _plaintext_secret_hosts(config)
    for host in hosts:
        entry = cast(util.JsonObject, auths[host])
        for field in _SECRET_FIELDS:
            entry.pop(field, None)
    emptied = [host for host, entry in auths.items() if isinstance(entry, dict) and not entry]
    for host in emptied:
        del auths[host]
    if hosts or emptied:
        DOCKER_CONFIG.write_text(json.dumps(config, indent=2) + "\n")
    return len(hosts), len(emptied)


def _credential_round_trip(c: Context) -> str | None:
    """Store a throwaway credential through the helper, read it back, erase it. Returns a reason
    string on failure, or None when the store answered correctly.

    A `which` check passes on exactly the machine where the confusing failure happens — helper
    installed, Secret Service absent or locked, every registry push failing as though the password
    were wrong. So presence is not the question; whether the store answers is.
    """
    payload = json.dumps({"ServerURL": _PROBE_SERVER, "Username": _PROBE_USERNAME, "Secret": _PROBE_SECRET})
    stored = c.run(f"printf '%s' '{payload}' | {CREDENTIAL_HELPER} store", hide=True, warn=True)
    if not stored.ok:
        return f"`{CREDENTIAL_HELPER} store` failed: {(stored.stderr or stored.stdout).strip()}"
    got = c.run(f"printf '%s' '{_PROBE_SERVER}' | {CREDENTIAL_HELPER} get", hide=True, warn=True)
    # Erased before the result is judged, so a mismatch does not also leave the probe behind.
    c.run(f"printf '%s' '{_PROBE_SERVER}' | {CREDENTIAL_HELPER} erase", hide=True, warn=True)
    if not got.ok:
        return f"`{CREDENTIAL_HELPER} get` failed: {(got.stderr or got.stdout).strip()}"
    if cast(util.JsonObject, util.parse_json(got.stdout)).get("Secret") != _PROBE_SECRET:
        return f"`{CREDENTIAL_HELPER}` returned a different secret than was stored"
    return None


def _write_creds_store() -> bool:
    """Set `credsStore`, preserving every other key. True when the file changed."""
    config = _read_docker_config()
    if config.get("credsStore") == CREDS_STORE:
        return False
    config["credsStore"] = CREDS_STORE
    DOCKER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    # 0600 before the write, not after: this file holds credentials, and a new one created under
    # the default umask would be world-readable for the moment between the two calls.
    DOCKER_CONFIG.touch(mode=0o600, exist_ok=True)
    DOCKER_CONFIG.write_text(json.dumps(config, indent=2) + "\n")
    return True


@task(
    help={
        "purge_plaintext": (
            "Also strip the secret out of every `auths` entry that has one, and delete any entry "
            "left holding nothing — the same two effects `docker logout` has on this file. "
            "Destructive: the credential is gone from this machine unless it is also in the keyring "
            "or you can log in again."
        )
    }
)
def configure_credential_store(c: Context, purge_plaintext: bool = False):
    """Point docker (and, through oras, helm) at the OS secret store instead of a plaintext file.

    `credsStore` is written explicitly rather than left to auto-detection, and that is the whole
    design. Docker and oras both gate detection on the config having no authentication in it yet
    (`ContainsAuth()` / `IsAuthConfigured()` — `credsStore`, `credHelpers` or `auths` non-empty), so
    on any machine that has ever logged in to a registry, installing the helper changes nothing at
    all. An explicit value is consulted before the detected one and does not depend on what else the
    file contains.

    Fails loudly rather than degrading, because a half-finished install is worse than none here:
    oras, unlike docker, does not check that the helper binary exists before selecting it — it
    returns a secretservice store unconditionally and fails when it execs. A machine with a helm
    registry config and a missing or unresponsive store is exactly the broken, hard-to-understand
    auth failure this exists to prevent.

    Existing plaintext `auths` entries are reported and, by default, left alone: setting `credsStore`
    does not migrate them — docker keeps reading the plaintext entry and it keeps working, which is
    the quiet half of the failure — and removing one without the user's say-so takes away access they
    may not be able to get back. `--purge-plaintext` is the deliberate removal, opt-in for the reason
    `~/AGENTS.md` reserves an inverted flag shape for: this is the genuinely-destructive-by-default
    case, so it is `rm -i`'s shape rather than apt's `-y`. It runs only after the round trip has
    passed, so a machine whose store does not answer cannot lose a credential to it.
    """
    if not util.command_exists(CREDENTIAL_HELPER):
        # Not an error: the helper is a `workstation`-tagged package, so a headless or container
        # machine legitimately has none. Saying so is the requirement — silently leaving credentials
        # in a file is the state this task exists to end.
        print(f"[docker-credentials] {CREDENTIAL_HELPER} not installed — credentials stay in {DOCKER_CONFIG}")
        return

    config = _read_docker_config()
    plaintext = _plaintext_auth_count(config)
    if util.DRY_RUN:
        configured = config.get("credsStore") == CREDS_STORE
        print(f"[docker-credentials] credsStore:{util.ok_label(configured)}  plaintext auths: {plaintext}")
        return

    if reason := _credential_round_trip(c):
        raise Exit(
            f"[docker-credentials] the credential helper is installed but the secret store did not answer: {reason}\n"
            "  Nothing was written. On a desktop this usually means the keyring is locked or the\n"
            "  Secret Service is not running; `gh auth status` reporting `(keyring)` is a quick\n"
            "  independent check that the service is up.",
            code=1,
        )

    if _write_creds_store():
        print(f"[docker-credentials] credsStore={CREDS_STORE} written to {DOCKER_CONFIG}")
    else:
        print(f"[docker-credentials] credsStore={CREDS_STORE} already set — nothing to do")
    if not purge_plaintext:
        if plaintext:
            print(
                f"[docker-credentials] {plaintext} registry credential(s) still stored as plaintext in that file.\n"
                "  Migrate each deliberately: `docker login <host>` to re-store it through the helper,\n"
                "  then `inv docker.configure-credential-store --purge-plaintext` to strip what is left.\n"
                "  docker reads the plaintext entry until you do, so nothing looks wrong until it is gone."
            )
        return

    # Runs whether or not a secret was found: the second half of the purge removes entries left
    # holding nothing, which is precisely the residue an earlier run of the first half creates.
    secrets, emptied = _purge_plaintext_auths()
    if secrets:
        print(f"[docker-credentials] purged the secret from {secrets} plaintext entr(ies)")
    if emptied:
        print(f"[docker-credentials] removed {emptied} empty `auths` entr(ies) — a logout deletes these too")
    if not secrets and not emptied:
        print("[docker-credentials] no plaintext secret and no empty entry — nothing to purge")


def _prune(c: Context, label: str, flags: str, desc: str) -> None:
    if not util.command_exists("docker"):
        print(f"[{label}] docker not installed — nothing to do")
        return
    if util.DRY_RUN:
        c.run("docker system df", warn=True)
        return
    c.run(f"docker system prune {flags}")
    print(f"[{label}] pruned {desc}")


@task
def clean(c: Context):
    """Prune stopped containers, dangling images, and unused networks/build cache
    (`docker system prune -f`). Conservative on purpose: doesn't remove images that are tagged
    but unused by any container — see `docker.clean-full` for that. Neither touches volumes —
    those can hold irreplaceable data, a different risk class than a rebuildable cache. Opt-in,
    not part of `inv setup` — see `inv clean.all`.
    """
    _prune(c, "docker.clean", "-f", "stopped containers, dangling images, unused networks/build cache")


@task
def clean_full(c: Context):
    """Prune everything `docker.clean` does, plus all images not currently used by a container
    — tagged or not (`docker system prune -af`). Still doesn't touch volumes — see `docker.clean`
    for why. Opt-in, not part of `inv setup` — see `inv clean.all-full`.
    """
    _prune(c, "docker.clean-full", "-af", "stopped containers, all unused images, unused networks/build cache")
