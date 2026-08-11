import subprocess
from pathlib import Path

from invoke import task

from . import util

_PROJECTS_ROOT = Path.home() / "projects"

_SETTINGS = {
    "core.autocrlf": "input",
    "core.fileMode": "true",
    "core.ignorecase": "false",
    "core.preloadindex": "true",
    "core.editor": "code --wait",
    "push.default": "current",
    "push.autoSetupRemote": "true",
    "pull.rebase": "false",
    "rebase.autoStash": "true",
    "log.decorate": "auto",
}


@task
def settings(c):
    """Apply global git configuration (idempotent, no identity data required)."""
    if util.DRY_RUN:
        for key, want in _SETTINGS.items():
            result = subprocess.run(
                ["git", "config", "--global", key],
                capture_output=True,
                text=True,
            )
            current = result.stdout.strip()
            status = "ok" if current == want else f"WRONG (current: {current!r})"
            print(f"[git] {key}: {status}")
        return
    for key, val in _SETTINGS.items():
        c.run(f"git config --global {key} {val!r}", hide=True)
    print("[git] global settings applied")


@task
def configure(c):
    """Set up per-directory git identities from ~/.config/pulse/identity.toml."""
    identity = util.load_identity()
    profiles = identity.get("git_profiles", [])
    if not profiles:
        print("[git] no git_profiles in identity.toml — skipping")
        return

    if util.DRY_RUN:
        for p in profiles:
            project_dir = _PROJECTS_ROOT / p["directory"]
            exists = "ok" if project_dir.exists() else "MISSING"
            print(f"[git] {p['directory']} ({exists}) → {p['name']} <{p['email']}>")
        return

    c.run("git config --global --unset user.name", warn=True, hide=True)
    c.run("git config --global --unset user.email", warn=True, hide=True)

    for p in profiles:
        project_dir = _PROJECTS_ROOT / p["directory"]
        project_dir.mkdir(parents=True, exist_ok=True)
        gitconfig = project_dir / ".gitconfig"
        c.run(
            f'git config --global includeIf.gitdir:"{project_dir}/".path "{gitconfig}"',
            hide=True,
        )
        c.run(f'git config --file "{gitconfig}" user.name "{p["name"]}"', hide=True)
        c.run(f'git config --file "{gitconfig}" user.email "{p["email"]}"', hide=True)
        print(f"[git] {p['directory']} → {p['name']} <{p['email']}>")
