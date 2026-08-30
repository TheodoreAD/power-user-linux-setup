from pathlib import Path

from invoke import Context, task

from . import deploy

_CONFIG_FILES = [
    ("config/pycharm/editor-font.xml", "options/editor-font.xml"),
    ("config/pycharm/terminal-font.xml", "options/terminal-font.xml"),
]


def _pycharm_dir() -> Path | None:
    """Return the most recent PyCharm config directory, or None if not found."""
    candidates = sorted(Path.home().joinpath(".config/JetBrains").glob("PyCharm*"))
    return candidates[-1] if candidates else None


def managed_files() -> list[deploy.Managed]:
    """The font-settings files, resolved against whichever PyCharm is installed here.

    Empty when PyCharm isn't installed — the destination is discovered on the machine rather than
    declared in setup.toml, which is why these can't be `config_files` entries: a `[packages.*]`
    mapping needs a literal `dst`, and a declared destination is one `inv verify.all` requires to
    exist.

    MANAGED_FILE, not CONFIG_FILE: PULSE owns these, so an edit is drift to report rather than a
    customization to keep. Before this went through deploy.py they were an unconditional
    `write_bytes` — no manifest entry, no diff, and a hand edit (or a change PyCharm itself made)
    was destroyed in silence.
    """
    pycharm = _pycharm_dir()
    if pycharm is None:
        return []
    return [
        deploy.Managed(path=pycharm / dst, package="pycharm", source=src, mechanism=deploy.Mechanism.MANAGED_FILE)
        for src, dst in _CONFIG_FILES
    ]


@task
def configure_pycharm(c: Context):
    """Copy font settings into the active PyCharm config directory."""
    files = managed_files()
    if not files:
        print("[pycharm] no PyCharm config directory found — is PyCharm installed?")
        return
    print(f"[pycharm] configuring {files[0].path.parent.parent.name}")
    for managed in files:
        deploy.deploy(managed)
