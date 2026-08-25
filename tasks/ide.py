from pathlib import Path

from invoke import Context, task

_CONFIG_FILES = [
    ("config/pycharm/editor-font.xml", "options/editor-font.xml"),
    ("config/pycharm/terminal-font.xml", "options/terminal-font.xml"),
]


def _pycharm_dir() -> Path | None:
    """Return the most recent PyCharm config directory, or None if not found."""
    candidates = sorted(Path.home().joinpath(".config/JetBrains").glob("PyCharm*"))
    return candidates[-1] if candidates else None


@task
def configure_pycharm(c: Context):
    """Copy font settings into the active PyCharm config directory."""
    pycharm = _pycharm_dir()
    if not pycharm:
        print("[pycharm] no PyCharm config directory found — is PyCharm installed?")
        return
    print(f"[pycharm] configuring {pycharm.name}")
    for src_rel, dst_rel in _CONFIG_FILES:
        src = Path(src_rel)
        dst = pycharm / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        print(f"[pycharm] wrote {dst_rel}")
