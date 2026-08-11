import os
import shutil
import subprocess
import sys
import tomllib
from functools import cache
from pathlib import Path

DRY_RUN: bool = os.environ.get("PULSE_DRY_RUN", "").lower() in ("1", "true", "yes")

# Use 'sudo -A' when SUDO_ASKPASS is set (non-TTY contexts like Claude Code, or a shell
# where inv zsh.configure has run). Falls back to plain 'sudo' in a fresh terminal.
SUDO: str = "sudo -A" if os.environ.get("SUDO_ASKPASS") else "sudo"

_PULSE_WIDTH = 78

_PROC_VERSION = Path("/proc/version")


def is_wsl() -> bool:
    """True if running under any WSL version (1 or 2) — see tasks/wsl.py for version-specific
    checks and the rest of the WSL-aware tasks."""
    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
        return True
    try:
        return "microsoft" in _PROC_VERSION.read_text().lower()
    except FileNotFoundError:
        return False


def is_docker_desktop_wsl_integration() -> bool:
    """True if the `docker` CLI is present but there's no local `dockerd` — Docker Desktop's WSL
    integration, not a native install. In that case the daemon isn't running inside this distro at
    all (it's Windows-side), so docker.py's daemon.json/systemctl calls have nothing to act on —
    manage Docker Desktop's own settings from Windows instead. Previously duplicated independently
    in tasks/docker.py and tasks/wsl.py; factored out here so the two checks can't drift.
    """
    return command_exists("docker") and not command_exists("dockerd")


def is_devcontainer() -> bool:
    """True if running inside a dev container / Codespace — used by tasks/proxy.py to skip
    systemd-`--user`-daemon assumptions and prefer the Windows/host-proxy discovery path over
    installing a second local daemon. `/.dockerenv` alone isn't enough (any Docker container has
    it, including plain CI runners) — pair it with an env var a dev-container tool actually sets.
    """
    return Path("/.dockerenv").exists() and bool(
        os.environ.get("REMOTE_CONTAINERS") or os.environ.get("CODESPACES") or os.environ.get("DEVCONTAINER")
    )


def interactive() -> bool:
    """True if stdin is a real terminal and this isn't a dry run — the gate for whether it's
    safe to prompt with input() at all, vs. a piped/scripted/CI invocation that would just hang.
    """
    return sys.stdin.isatty() and not DRY_RUN


def confirm(question: str, default: bool = True) -> bool:
    """Prompt a yes/no question on stdin. Returns `default` unmodified if stdin isn't a real
    terminal — call interactive() yourself first if the caller needs to skip prompting (and any
    surrounding explanation) entirely rather than silently falling back to the default.
    """
    if not sys.stdin.isatty():
        return default
    suffix = " [Y/n] " if default else " [y/N] "
    while True:
        answer = input(question + suffix).strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please answer y or n.")


def prompt_text(question: str, default: str | None = None) -> str | None:
    """Prompt for a line of free text on stdin. Returns `default` unmodified (may be None) if
    stdin isn't a real terminal — same non-interactive gate as confirm(); call interactive()
    yourself first if the caller needs to skip prompting entirely. Re-prompts on an empty answer
    unless a default is given, so callers never get "" back for a required field.
    """
    if not sys.stdin.isatty():
        return default
    suffix = f" [{default}] " if default else " "
    while True:
        answer = input(question + suffix).strip()
        if answer:
            return answer
        if default is not None:
            return default
        print("This can't be empty.")


def _marker(name: str, open_: bool) -> str:
    tl, tr = ("╔", "╗") if open_ else ("╚", "╝")
    label = f" PULSE::{name} "
    fill = _PULSE_WIDTH - 2 - 2 - len(label)
    left = fill // 2
    right = fill - left
    return f"# {tl}{'═' * left}{label}{'═' * right}{tr}"


def ensure_block_text(text: str, name: str, content: str) -> tuple[str, str]:
    """Return (new_text, status) with a named PULSE block applied. Does not write."""
    start = _marker(name, open_=True)
    end = _marker(name, open_=False)
    block = f"{start}\n{content.strip()}\n{end}"
    if start in text:
        s = text.index(start)
        e = text.index(end) + len(end)
        if text[s:e] == block:
            return text, "ok"
        return text[:s] + block + text[e:], "updated"
    return text.rstrip("\n") + f"\n\n{block}\n", "added"


def ensure_block(path: Path, name: str, content: str) -> str:
    """Idempotently write a named PULSE block to a file. Returns 'added', 'updated', or 'ok'."""
    text = path.read_text() if path.exists() else ""
    new_text, status = ensure_block_text(text, name, content)
    if status != "ok":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_text)
    return status


_CONFIG_PATH = Path(__file__).parent.parent / "setup.toml"
_IDENTITY_PATH = Path.home() / ".config" / "pulse" / "identity.toml"


@cache
def load_config() -> dict:
    with _CONFIG_PATH.open("rb") as f:
        return tomllib.load(f)


@cache
def load_identity() -> dict:
    if not _IDENTITY_PATH.exists():
        raise FileNotFoundError(
            f"Identity file not found: {_IDENTITY_PATH}\n"
            "Run `inv identity.init` (interactive wizard) or copy config/identity.toml.example "
            f"to {_IDENTITY_PATH} and fill in your details by hand."
        )
    with _IDENTITY_PATH.open("rb") as f:
        return tomllib.load(f)


def load_proxy_override() -> dict:
    """Optional [proxy] table from ~/.config/pulse/identity.toml (host/port/noproxy). Unlike
    load_identity(), tolerant of a missing file — proxy detection has to degrade gracefully on the
    common case of a personal, non-corporate machine, not require identity.toml to exist just to
    run `inv proxy.check`. Not cached like load_identity()/load_config(): this is re-read on every
    proxy.* invocation on the assumption it's edited far more often mid-troubleshooting than the
    machine's own identity ever is.
    """
    if not _IDENTITY_PATH.exists():
        return {}
    with _IDENTITY_PATH.open("rb") as f:
        return tomllib.load(f).get("proxy", {})


def load_certs_override() -> dict:
    """Optional [certs] table from ~/.config/pulse/identity.toml (corporate CA bundle path(s)).
    Same tolerant-of-missing-file, not-cached rationale as load_proxy_override() — see there.
    """
    if not _IDENTITY_PATH.exists():
        return {}
    with _IDENTITY_PATH.open("rb") as f:
        return tomllib.load(f).get("certs", {})


def _excluded_tags() -> set[str]:
    val = os.environ.get("PULSE_EXCLUDE_TAGS", "")
    if not val:
        return set()
    return {t.strip() for t in val.split(",") if t.strip()}


def packages_by_method(method: str) -> dict:
    excluded = _excluded_tags()
    return {
        name: cfg
        for name, cfg in load_config()["packages"].items()
        if cfg.get("method") == method and cfg.get("enabled", True) and not (excluded & set(cfg.get("tags", [])))
    }


def apt_packages(name: str, cfg: dict) -> list[str]:
    """Return the apt package list for a section, defaulting to [name] if not specified."""
    return cfg.get("packages", [name])


def apt_installed(pkg: str) -> bool:
    result = subprocess.run(
        ["dpkg-query", "-W", "-f=${Status}", pkg],
        capture_output=True,
        text=True,
    )
    return "install ok installed" in result.stdout


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def require_systemd() -> None:
    """Abort immediately if systemd isn't the running init system.

    Any task that shells out to systemctl/localectl needs this — fails the same way whether the
    cause is WSL1 (no real kernel, systemd never runs at all), WSL2 with `systemd=true` unset in
    /etc/wsl.conf, or a minimal/container environment with no init system. This repo only
    supports WSL2 with systemd enabled; WSL1 is not a supported target.
    """
    if not Path("/run/systemd/system").is_dir():
        raise RuntimeError(
            "systemd is not running (no /run/systemd/system) — this task shells out to "
            "systemctl/localectl and needs it.\n"
            "On WSL2, add to /etc/wsl.conf:\n"
            "  [boot]\n"
            "  systemd=true\n"
            "then run `wsl.exe --shutdown` from Windows and reopen the terminal. WSL1 cannot run "
            "systemd at all and isn't a supported target.\n"
            "Run `inv wsl.check` for a full diagnostic."
        )


def require_apt() -> None:
    """Abort immediately if apt/dpkg aren't available — this repo only targets Debian/Ubuntu."""
    missing = [name for name in ("apt", "dpkg") if not command_exists(name)]
    if missing:
        raise RuntimeError(
            f"{' and '.join(missing)} not found — this repo only supports Debian/Ubuntu (apt, "
            "apt-repo, deb-github, deb-url methods all shell out to apt/dpkg).\n"
            "On WSL this usually means a non-Ubuntu distro (Alpine, Fedora Remix, etc.) — install "
            "Ubuntu-24.04 from the Microsoft Store instead: wsl.exe --install Ubuntu-24.04\n"
            "Run `inv wsl.check` for a full diagnostic."
        )


def file_contains(path: str | Path, text: str) -> bool:
    try:
        return text in Path(path).expanduser().read_text()
    except FileNotFoundError:
        return False


def ensure_symlink(src_cmd: str, link_name: str) -> bool:
    """Create ~/.local/bin/<link_name> -> which(<src_cmd>) if not already present."""
    src = shutil.which(src_cmd)
    if not src:
        return False
    return ensure_symlink_path(src, link_name)


def ensure_symlink_path(src_path: str | Path, link_name: str) -> bool:
    """Create ~/.local/bin/<link_name> -> <src_path> if not already present."""
    src = Path(src_path).expanduser()
    if not src.exists():
        return False
    link = Path.home() / ".local" / "bin" / link_name
    link.parent.mkdir(parents=True, exist_ok=True)
    if not link.exists():
        link.symlink_to(src)
        return True
    return False
