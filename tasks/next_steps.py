import os
import pwd
import shutil
import subprocess
from pathlib import Path

from . import git, ssh, ui, util

_IDENTITY_PATH = Path.home() / ".config" / "pulse" / "identity.toml"


def _current_shell() -> str:
    current_user = os.environ.get("SUDO_USER") or os.environ.get("USER", "")
    try:
        return pwd.getpwnam(current_user).pw_shell if current_user else ""
    except KeyError:
        return ""


def _git_settings_applied() -> bool:
    for key, want in git._SETTINGS.items():
        result = subprocess.run(["git", "config", "--global", key], capture_output=True, text=True)
        if result.stdout.strip() != want:
            return False
    return True


def _git_profiles_applied(identity: dict) -> bool:
    profiles = identity.get("git_profiles", [])
    return all((git._PROJECTS_ROOT / p["directory"]).exists() for p in profiles)


def _missing_ssh_keys(identity: dict) -> list[str]:
    node = ssh._node()
    emails = sorted({h["email"] for h in identity.get("ssh_hosts", [])})
    return [email for email in emails if not ssh._key_path(email, node).exists()]


def _ssh_config_applied(identity: dict) -> bool:
    if not ssh._SSH_CONFIG.exists():
        return False
    node = ssh._node()
    blocks = []
    for h in identity.get("ssh_hosts", []):
        key = ssh._key_path(h["email"], node)
        blocks.append(
            f"Host {h['alias']}\n"
            f"  HostName {h['hostname']}\n"
            f"  IdentityFile {key}\n"
            f"  User {h['user']}"
        )
    blocks.append(ssh._HOST_STAR)
    content = "\n\n".join(blocks)
    text = ssh._SSH_CONFIG.read_text()
    _, status = util.ensure_block_text(text, "ssh", content)
    return status == "ok"


def _ssh_keys_loaded() -> bool:
    if not util.command_exists("ssh-add"):
        return True  # nothing to check — don't block the chain on a missing optional tool
    result = subprocess.run(["ssh-add", "-l"], capture_output=True, text=True)
    return result.returncode == 0


def _gh_authenticated() -> bool | None:
    """None if gh isn't installed — caller should skip this check, not treat None as "no"."""
    if not util.command_exists("gh"):
        return None
    result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    return result.returncode == 0


def print_next_steps(extra_note: str | None = None) -> None:
    """Print the single next concrete manual step after setup.setup or wsl.install: shell, then
    identity.toml, then the git/ssh/gh chain once identity.toml exists.

    Checks real state each time rather than a stored "did we already tell you" flag: a flag can
    drift from reality (exactly the bug that made system.dns() unreliable — see git history), a
    fresh check can't. Safe to re-run after doing what it suggests; it just reports whatever's
    still outstanding, one step at a time so it's never ambiguous what to run next.

    In tasks/next_steps.py rather than tasks/util.py because it needs to check git/ssh state —
    both of those import util, so util importing them back would be circular.
    """
    zsh_path = shutil.which("zsh")
    current_shell = _current_shell()
    # Name-based, not exact-path: a machine can have more than one zsh on disk (e.g. an apt one
    # at /usr/bin/zsh plus another earlier on PATH) — what matters is the registered shell is
    # *a* zsh, not that it's byte-for-byte the one `shutil.which` happens to find right now.
    if zsh_path and Path(current_shell).name != "zsh":
        ui.block(
            f"Your login shell isn't zsh yet (currently: {current_shell or 'unknown'}).",
            "zsh.set_default_shell just tried to set it — if that succeeded, close this "
            "terminal, open a new one, and re-run this command to continue.",
            f"If it's still not zsh after that, run: sudo usermod -s {zsh_path} $USER",
            label="next steps",
        )
        return

    if not _IDENTITY_PATH.exists():
        ui.block(
            f"1. cp config/identity.toml.example {_IDENTITY_PATH}",
            "   — edit it with your name/email/GitHub account details",
            "2. Then re-run this command to continue.",
            label="next steps",
        )
        return

    identity = util.load_identity()

    if not _git_settings_applied() or not _git_profiles_applied(identity):
        ui.block("Run: inv git.configure git.settings", label="next steps")
        return

    missing_keys = _missing_ssh_keys(identity)
    if missing_keys:
        ui.block(
            f"SSH key(s) missing for: {', '.join(missing_keys)}",
            "Run: inv ssh.keys   (prompts for a passphrase per key)",
            label="next steps",
        )
        return

    if not _ssh_config_applied(identity):
        ui.block("Run: inv ssh.configure", label="next steps")
        return

    if not _ssh_keys_loaded():
        ui.block(
            "SSH keys aren't loaded into the agent yet.",
            "Run: inv ssh.add",
            label="next steps",
        )
        return

    if _gh_authenticated() is False:
        ui.block("gh CLI is installed but not authenticated. Run: gh auth login", label="next steps")
        return

    lines = ["Nothing left that's automatable."]
    if extra_note:
        lines.append(f"Reminder: {extra_note}")
    ui.note(*lines)
