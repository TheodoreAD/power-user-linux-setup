import os
import shutil
import subprocess
import tomllib
from functools import lru_cache
from pathlib import Path

DRY_RUN: bool = os.environ.get("PULSE_DRY_RUN", "").lower() in ("1", "true", "yes")

# Use 'sudo -A' when SUDO_ASKPASS is set (non-TTY contexts like Claude Code, or a shell
# where inv zsh.configure has run). Falls back to plain 'sudo' in a fresh terminal.
SUDO: str = "sudo -A" if os.environ.get("SUDO_ASKPASS") else "sudo"

_PULSE_WIDTH = 78


def _marker(name: str, open_: bool) -> str:
    tl, tr = ("╔", "╗") if open_ else ("╚", "╝")
    label  = f" PULSE::{name} "
    fill   = _PULSE_WIDTH - 2 - 2 - len(label)
    left   = fill // 2
    right  = fill - left
    return f"# {tl}{'═' * left}{label}{'═' * right}{tr}"


def ensure_block_text(text: str, name: str, content: str) -> tuple[str, str]:
    """Return (new_text, status) with a named PULSE block applied. Does not write."""
    start = _marker(name, open_=True)
    end   = _marker(name, open_=False)
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

_CONFIG_PATH   = Path(__file__).parent.parent / "setup.toml"
_IDENTITY_PATH = Path.home() / ".config" / "pulse" / "identity.toml"


@lru_cache(maxsize=None)
def load_config() -> dict:
    with open(_CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


@lru_cache(maxsize=None)
def load_identity() -> dict:
    if not _IDENTITY_PATH.exists():
        raise FileNotFoundError(
            f"Identity file not found: {_IDENTITY_PATH}\n"
            f"Copy config/identity.toml.example to {_IDENTITY_PATH} and fill in your details."
        )
    with open(_IDENTITY_PATH, "rb") as f:
        return tomllib.load(f)


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
        if cfg.get("method") == method
        and cfg.get("enabled", True)
        and not (excluded & set(cfg.get("tags", [])))
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
