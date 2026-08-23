import json
import tempfile
from pathlib import Path

from invoke import task

from . import util

_DAEMON_JSON = Path("/etc/docker/daemon.json")

_DEFAULTS = {
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "50m",
        "max-file": "3",
    },
    "dns": ["1.1.1.1", "1.0.0.1", "8.8.8.8"],
}


def _is_subset(defaults: dict, existing: dict) -> bool:
    for key, value in defaults.items():
        if isinstance(value, dict):
            if not isinstance(existing.get(key), dict) or not _is_subset(value, existing[key]):
                return False
        elif existing.get(key) != value:
            return False
    return True


def _merge(base: dict, updates: dict) -> dict:
    result = {**base}
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _ensure_running(c) -> None:
    if not util.has_systemd():
        print("[docker] no systemd — daemon.json/group updated, but nothing to restart here")
        return
    if c.run("systemctl is-enabled docker", hide=True, warn=True).stdout.strip() == "masked":
        c.run(f"{util.SUDO} systemctl unmask docker")
        print("[docker] daemon was masked — unmasked")
    c.run(f"{util.SUDO} systemctl restart docker")


def _read_daemon_json(c) -> dict:
    return json.loads(c.run(f"{util.SUDO} cat {_DAEMON_JSON}", hide=True).stdout) if _DAEMON_JSON.exists() else {}


def _configure_group(c, user: str) -> None:
    groups = c.run(f"id -nG {user}", hide=True).stdout.split()
    if "docker" not in groups:
        c.run(f"{util.SUDO} usermod -aG docker {user}")
        print(f"[docker] {user} added to docker group — open a new terminal to pick it up")


def _configure_daemon_json(c) -> None:
    existing = _read_daemon_json(c)
    if _is_subset(_DEFAULTS, existing):
        print("[docker] daemon.json already configured — nothing to do")
        _ensure_running(c)
        return

    updated = json.dumps(_merge(existing, _DEFAULTS), indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write(updated)
        tmp = f.name
    c.run(f"{util.SUDO} mkdir -p {_DAEMON_JSON.parent} && {util.SUDO} cp {tmp} {_DAEMON_JSON} && rm {tmp}")
    _ensure_running(c)
    print("[docker] daemon.json updated, daemon restarted")


@task
def configure(c):
    """Merge log limits and DNS into /etc/docker/daemon.json, add user to docker group."""
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


def _prune(c, label: str, flags: str, desc: str) -> None:
    if not util.command_exists("docker"):
        print(f"[{label}] docker not installed — nothing to do")
        return
    if util.DRY_RUN:
        c.run("docker system df", warn=True)
        return
    c.run(f"docker system prune {flags}")
    print(f"[{label}] pruned {desc}")


@task
def clean(c):
    """Prune stopped containers, dangling images, and unused networks/build cache
    (`docker system prune -f`). Conservative on purpose: doesn't remove images that are tagged
    but unused by any container — see `docker.clean-full` for that. Neither touches volumes —
    those can hold irreplaceable data, a different risk class than a rebuildable cache. Opt-in,
    not part of `inv setup` — see `inv clean.all`.
    """
    _prune(c, "docker.clean", "-f", "stopped containers, dangling images, unused networks/build cache")


@task
def clean_full(c):
    """Prune everything `docker.clean` does, plus all images not currently used by a container
    — tagged or not (`docker system prune -af`). Still doesn't touch volumes — see `docker.clean`
    for why. Opt-in, not part of `inv setup` — see `inv clean.all-full`.
    """
    _prune(c, "docker.clean-full", "-af", "stopped containers, all unused images, unused networks/build cache")
