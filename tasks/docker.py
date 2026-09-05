import json
import tempfile
from pathlib import Path
from typing import cast

from invoke import Context, Exit, task

from . import util

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


def _configure_daemon_json(c: Context) -> None:
    existing = _read_daemon_json(c)
    if _is_subset(_DEFAULTS, existing):
        print("[docker] daemon.json already configured — nothing to do")
        _ensure_running(c)
        return

    updated = json.dumps(_merge(existing, _DEFAULTS), indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write(updated)
        tmp = f.name
    c.run(f"{util.SUDO} mkdir -p {_DAEMON_JSON.parent} && {util.SUDO} install -m 0644 {tmp} {_DAEMON_JSON} && rm {tmp}")
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


def _purge_plaintext_auths() -> int:
    """Strip the secret fields from every `auths` entry that has them, leaving the entry itself.

    That is what `docker logout` leaves behind under a `credsStore`, so the result is a state docker
    produces itself rather than one only this task knows how to make. Returns how many hosts changed.
    """
    config = _read_docker_config()
    hosts = _plaintext_secret_hosts(config)
    if not hosts:
        return 0
    auths = cast(util.JsonObject, config["auths"])
    for host in hosts:
        entry = cast(util.JsonObject, auths[host])
        for field in _SECRET_FIELDS:
            entry.pop(field, None)
    DOCKER_CONFIG.write_text(json.dumps(config, indent=2) + "\n")
    return len(hosts)


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
            "Also strip the secret out of every `auths` entry that still has one. Destructive: the "
            "credential is gone from this machine unless it is also in the keyring or you can log in "
            "again."
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
    if not plaintext:
        return
    if not purge_plaintext:
        print(
            f"[docker-credentials] {plaintext} registry credential(s) still stored as plaintext in that file.\n"
            "  Migrate each deliberately: `docker login <host>` to re-store it through the helper,\n"
            "  then `inv docker.configure-credential-store --purge-plaintext` to strip what is left.\n"
            "  docker reads the plaintext entry until you do, so nothing looks wrong until it is gone."
        )
        return
    print(f"[docker-credentials] purged the secret from {_purge_plaintext_auths()} plaintext entr(ies)")


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
