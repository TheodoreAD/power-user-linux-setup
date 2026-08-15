import subprocess
from pathlib import Path

from invoke import task

from . import util

PROJECTS_ROOT = Path.home() / "projects"


def resolve_project_dir(directory: str) -> Path:
    """A profile's `directory` is either a bare relative name — joined under PROJECTS_ROOT, the
    multi-account convention in identity.toml.example (e.g. "github.com-personal") — or an
    absolute path, optionally starting with `~` (expanded), used as-is for a custom location.
    This is what lets the simple wizard default straight to ~/projects/ itself instead of forcing
    an extra subdirectory under it.
    """
    expanded = Path(directory).expanduser()
    if expanded.is_absolute():
        return expanded
    return PROJECTS_ROOT / directory


SETTINGS = {
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
        for key, want in SETTINGS.items():
            result = subprocess.run(
                ["git", "config", "--global", key],
                capture_output=True,
                text=True,
            )
            current = result.stdout.strip()
            status = "ok" if current == want else f"WRONG (current: {current!r})"
            print(f"[git] {key}: {status}")
        return
    for key, val in SETTINGS.items():
        c.run(f"git config --global {key} {val!r}", hide=True)
    print("[git] global settings applied")


@task
def configure(c):
    """Set up per-directory git identities from ~/.config/power-user-linux-setup/identity.toml."""
    identity = util.load_identity()
    profiles = identity.get("git_profiles", [])
    if not profiles:
        print("[git] no git_profiles in identity.toml — skipping")
        return

    if util.DRY_RUN:
        for p in profiles:
            project_dir = resolve_project_dir(p["directory"])
            exists = util.ok_label(project_dir.exists())
            print(f"[git] {project_dir} ({exists}) → {p['name']} <{p['email']}>")
        return

    c.run("git config --global --unset user.name", warn=True, hide=True)
    c.run("git config --global --unset user.email", warn=True, hide=True)

    for p in profiles:
        project_dir = resolve_project_dir(p["directory"])
        project_dir.mkdir(parents=True, exist_ok=True)
        gitconfig = project_dir / ".gitconfig"
        c.run(
            f'git config --global includeIf.gitdir:"{project_dir}/".path "{gitconfig}"',
            hide=True,
        )
        c.run(f'git config --file "{gitconfig}" user.name "{p["name"]}"', hide=True)
        c.run(f'git config --file "{gitconfig}" user.email "{p["email"]}"', hide=True)
        print(f"[git] {project_dir} → {p['name']} <{p['email']}>")
