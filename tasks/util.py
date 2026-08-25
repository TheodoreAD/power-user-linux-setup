import json
import os
import pwd
import shutil
import subprocess
import sys
import tempfile
import tomllib
from enum import StrEnum
from functools import cache
from pathlib import Path
from typing import Any, cast, overload

DRY_RUN: bool = os.environ.get("PULSE_DRY_RUN", "").lower() in ("1", "true", "yes")

# The env-var form of `--yes` for the composite entry points (`inv setup`, `inv wsl.install`) that
# have no flag of their own. tasks/deploy.py's writer defaults to *not* overwriting a destination it
# can't prove it wrote, and util.confirm() returns that default when stdin isn't a terminal — so an
# unattended run (bootstrap-devcontainer.sh, a Dockerfile) that hits a pre-existing file would
# silently skip it. Set this to get the overwrite-and-say-so behavior instead.
ASSUME_YES: bool = os.environ.get("PULSE_ASSUME_YES", "").lower() in ("1", "true", "yes")

# Use 'sudo -A' when SUDO_ASKPASS is set (non-TTY contexts like Claude Code, or a shell
# where inv zsh.configure has run). Falls back to plain 'sudo' in a fresh terminal.
SUDO: str = "sudo -A" if os.environ.get("SUDO_ASKPASS") else "sudo"

_PULSE_WIDTH = 78

_PROC_VERSION = Path("/proc/version")
_CONFIG_PATH = Path(__file__).parent.parent / "setup.toml"

# Machine-local, out-of-repo state namespace shared by identity.toml and the applied-manifest
# files tasks/ai.py and tasks/allowlist.py each track their own writes to settings.json with.
# Deliberately the full repo name, not "pulse" — "~/.config/pulse" is PulseAudio's own real config
# dir, and this namespace used to collide with it silently before this rename.
PULSE_CONFIG_DIR = Path.home() / ".config" / "power-user-linux-setup"
PULSE_STATE_DIR = Path.home() / ".local" / "state" / "power-user-linux-setup"

IDENTITY_PATH = PULSE_CONFIG_DIR / "identity.toml"
OVERRIDES_PATH = PULSE_CONFIG_DIR / "overrides.toml"
CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"


def ok_label(ok: bool) -> str:
    """The repo-wide "ok"/"MISSING" status word used in every task's dry-run and status output."""
    return "ok" if ok else "MISSING"


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


def current_user() -> str:
    """Best-effort real (non-root) username: SUDO_USER when running under sudo, else $USER,
    else the actual name of the current UID. The env-var-only version of this (duplicated
    across tasks/zsh.py, tasks/docker.py, tasks/next_steps.py before being factored out here)
    raises KeyError from pwd.getpwnam("") in environments with neither var set — a plain
    `docker build` doesn't set $USER at all, only $HOME.
    """
    return os.environ.get("SUDO_USER") or os.environ.get("USER") or pwd.getpwuid(os.getuid()).pw_name


def has_systemd() -> bool:
    """True if systemd is the running init system — the same check require_systemd() uses to
    decide whether to abort. False for containers with no init system, WSL1, and WSL2 with
    systemd=true unset in /etc/wsl.conf. Used by setup() to skip the system/desktop phases
    instead of letting require_systemd() raise partway through them.
    """
    return Path("/run/systemd/system").is_dir()


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


@overload
def prompt_text(question: str, default: str) -> str: ...
@overload
def prompt_text(question: str, default: None = None) -> str | None: ...
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


class MarkerStyle(StrEnum):
    """Which comment syntax _marker() emits — see ensure_block()/ensure_block_text()."""

    COMMENT = "comment"  # '# ╔══ PULSE::name ══╗' ... '# ╚══...══╝' — shell/ini/config files (default)
    HTML = "html"  # '<!-- PULSE::name -->' ... '<!-- /PULSE::name -->' — markdown/HTML targets, where a
    # '#'-prefixed line would render as a heading, not a comment


def _marker(name: str, open_: bool, style: MarkerStyle = MarkerStyle.COMMENT) -> str:
    if style == MarkerStyle.HTML:
        return f"<!-- PULSE::{name} -->" if open_ else f"<!-- /PULSE::{name} -->"
    tl, tr = ("╔", "╗") if open_ else ("╚", "╝")
    label = f" PULSE::{name} "
    fill = _PULSE_WIDTH - 2 - 2 - len(label)
    left = fill // 2
    right = fill - left
    return f"# {tl}{'═' * left}{label}{'═' * right}{tr}"


class BlockStatus(StrEnum):
    OK = "ok"
    ADDED = "added"
    UPDATED = "updated"


def ensure_block_text(
    text: str, name: str, content: str, *, style: MarkerStyle = MarkerStyle.COMMENT
) -> tuple[str, BlockStatus]:
    """Return (new_text, status) with a named PULSE block applied. Does not write."""
    start = _marker(name, open_=True, style=style)
    end = _marker(name, open_=False, style=style)
    # Markdown requires a blank line between adjacent block-level elements (here: the HTML-comment
    # marker and the content, e.g. a table) to parse/format as intended — dprint enforces this and
    # would otherwise fight ensure_block's own idempotency by re-inserting the blank lines on every
    # `inv quality.fix` pass. The comment-style marker has no such requirement (shell/config files).
    sep = "\n\n" if style == MarkerStyle.HTML else "\n"
    block = f"{start}{sep}{content.strip()}{sep}{end}"
    if start in text:
        s = text.index(start)
        e = text.index(end) + len(end)
        if text[s:e] == block:
            return text, BlockStatus.OK
        return text[:s] + block + text[e:], BlockStatus.UPDATED
    return text.rstrip("\n") + f"\n\n{block}\n", BlockStatus.ADDED


def ensure_block(path: Path, name: str, content: str, *, style: MarkerStyle = MarkerStyle.COMMENT) -> BlockStatus:
    """Idempotently write a named PULSE block to a file. Returns BlockStatus.{ADDED,UPDATED,OK}."""
    text = path.read_text() if path.exists() else ""
    new_text, status = ensure_block_text(text, name, content, style=style)
    if status != BlockStatus.OK:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_text)
    return status


def sudo_write(c, path: Path, text: str) -> None:
    """Write `text` to a root-owned `path` via a tempfile + `sudo cp` — direct `path.write_text()`
    can't reach root-owned locations, and `sudo tee` from Python would need the text piped through
    a subprocess shell instead of written directly."""
    with tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False) as f:
        f.write(text)
        tmp = f.name
    c.run(f"{SUDO} cp {tmp} {path} && rm {tmp}")


def sudo_read(c, path: Path) -> str:
    """Read a root-owned `path` via `sudo cat`, or "" if it doesn't exist / can't be read."""
    if not path.exists():
        return ""
    result = c.run(f"{SUDO} cat {path}", hide=True, warn=True)
    return result.stdout if result.ok else ""


@cache
def load_config() -> dict:
    with _CONFIG_PATH.open("rb") as f:
        return tomllib.load(f)


@cache
def load_identity() -> dict:
    if not IDENTITY_PATH.exists():
        raise FileNotFoundError(
            f"Identity file not found: {IDENTITY_PATH}\n"
            "Run `inv identity.init` (interactive wizard) or copy config/identity.toml.example "
            f"to {IDENTITY_PATH} and fill in your details by hand."
        )
    with IDENTITY_PATH.open("rb") as f:
        return tomllib.load(f)


def load_proxy_override() -> dict:
    """Optional [proxy] table from ~/.config/power-user-linux-setup/identity.toml (host/port/noproxy). Unlike
    load_identity(), tolerant of a missing file — proxy detection has to degrade gracefully on the
    common case of a personal, non-corporate machine, not require identity.toml to exist just to
    run `inv proxy.check`. Not cached like load_identity()/load_config(): this is re-read on every
    proxy.* invocation on the assumption it's edited far more often mid-troubleshooting than the
    machine's own identity ever is.
    """
    if not IDENTITY_PATH.exists():
        return {}
    with IDENTITY_PATH.open("rb") as f:
        return cast(dict[str, Any], tomllib.load(f).get("proxy", {}))


def load_certs_override() -> dict:
    """Optional [certs] table from ~/.config/power-user-linux-setup/identity.toml (corporate CA bundle path(s)).
    Same tolerant-of-missing-file, not-cached rationale as load_proxy_override() — see there.
    """
    if not IDENTITY_PATH.exists():
        return {}
    with IDENTITY_PATH.open("rb") as f:
        return cast(dict[str, Any], tomllib.load(f).get("certs", {}))


@cache
def load_overrides() -> dict[str, bool]:
    """Machine-local `enabled` flips from ~/.config/power-user-linux-setup/overrides.toml, keyed by
    package name.

    setup.toml's `enabled` is the *default* for every machine that clones this repo; a package like
    google-chrome-x11 (an NVIDIA+Wayland workaround) has to ship off for everyone while being on
    here. This file is how one machine says otherwise, in setup.toml's own shape:

        [packages.google-chrome-x11]
        enabled = true

    Deliberately out of git, and deliberately not backed up by anything here: preserving a home
    directory is the user's own job, not this repo's. What PULSE guarantees is the stability of its
    defaults, not of any one machine's customizations on top of them.

    Only `enabled` is honoured, and only for a package setup.toml already declares — every package
    *definition* stays in git where it can be reviewed. Tolerant of a missing file, like
    load_proxy_override()/load_certs_override(), since the common case is a machine with no
    overrides at all. Cached like load_identity(): unlike the proxy/certs tables this is read on
    every enabled_packages() call, which happens many times per task run.
    """
    if not OVERRIDES_PATH.exists():
        return {}
    with OVERRIDES_PATH.open("rb") as f:
        # `object`, not `Any`, as the value type: every field here is read back through bool()
        # below, and Any would silently disable type checking on it.
        raw = cast(dict[str, dict[str, object]], tomllib.load(f).get("packages", {}))

    declared = load_config()["packages"]
    overrides: dict[str, bool] = {}
    for name, cfg in raw.items():
        if name not in declared:
            # A typo here would otherwise do nothing at all, silently — the whole file is
            # unvalidated by anything else, so this is the only place it can be caught.
            print(f"[overrides] no [packages.{name}] in setup.toml — ignoring (typo?)")
            continue
        enabled = cfg.get("enabled")
        if enabled is not None:
            overrides[name] = bool(enabled)
    return overrides


def load_claude_settings() -> dict:
    """Read CLAUDE_SETTINGS (~/.claude/settings.json), or {} if it doesn't exist yet."""
    return json.loads(CLAUDE_SETTINGS.read_text()) if CLAUDE_SETTINGS.exists() else {}


def write_claude_settings(settings: dict) -> None:
    """Backup CLAUDE_SETTINGS (if present) then overwrite it with `settings`. Shared by
    tasks/ai.py and tasks/allowlist.py, which each merge their own slice of permissions into the
    same file and must never clobber the other's — see their callers for the merge logic."""
    if CLAUDE_SETTINGS.exists():
        CLAUDE_SETTINGS.with_suffix(".json.bak").write_text(CLAUDE_SETTINGS.read_text())
    CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    CLAUDE_SETTINGS.write_text(json.dumps(settings, indent=2) + "\n")


def _excluded_tags() -> set[str]:
    val = os.environ.get("PULSE_EXCLUDE_TAGS", "")
    if not val:
        return set()
    return {t.strip() for t in val.split(",") if t.strip()}


class PackageMethod(StrEnum):
    """The `method` field of a `[packages.*]` section in setup.toml — see its header comment for
    what each one means."""

    APT = "apt"
    APT_REPO = "apt-repo"
    DEB_GITHUB = "deb-github"
    DEB_URL = "deb-url"
    APPARMOR_PROFILE = "apparmor-profile"
    ARCHIVE = "archive"
    UV_TOOL = "uv-tool"
    NVM = "nvm"
    SCRIPT = "script"
    BINARY = "binary"
    GIT_CLONE = "git-clone"
    WRAPPER_SCRIPT = "wrapper-script"
    GNOME_EXTENSION = "gnome-extension"


def enabled_packages() -> dict:
    """Every [packages.*] section that isn't disabled or excluded by PULSE_EXCLUDE_TAGS, whatever
    its method — the entry point for cross-method concerns like `config_files`, which any method
    may declare. Method-specific install tasks want packages_by_method() instead.

    Precedence is setup.toml → overrides.toml → PULSE_EXCLUDE_TAGS, environment last and absolute.
    Tags describe *capability* (no display server means a gui package genuinely cannot work), while
    an override describes *intent* — so an excluded tag wins over a machine that asked for the
    package, and the container/WSL profiles stay authoritative about what they can run.
    """
    excluded = _excluded_tags()
    overrides = load_overrides()
    return {
        name: cfg
        for name, cfg in load_config()["packages"].items()
        if overrides.get(name, cfg.get("enabled", True)) and not (excluded & set(cfg.get("tags", [])))
    }


def packages_by_method(method: PackageMethod) -> dict:
    return {name: cfg for name, cfg in enabled_packages().items() if cfg.get("method") == method}


def apt_packages(name: str, cfg: dict) -> list[str]:
    """Return the apt package list for a section, defaulting to [name] if not specified."""
    return cfg.get("packages", [name])


def apt_installed(pkg: str) -> bool:
    result = subprocess.run(
        ["dpkg-query", "-W", "-f=${Status}", pkg],
        capture_output=True,
        text=True,
        check=False,
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
    if not has_systemd():
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
