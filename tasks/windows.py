"""Native Windows host settings that a package needs and no other mechanism here writes: today, the
user PATH entries declared by `windows_path` (first user: [packages.venv-shims]).

The user PATH lives in the registry (HKCU\\Environment, value `Path`), not in a file, so the deploy
manifest cannot track it. `configure-path` puts each declared directory first, in declaration
order, and leaves every other entry where it was; `check-path` reports without changing anything.
Entries are written as `%USERPROFILE%\\...` in a REG_EXPAND_SZ value, so no username is spelled out.

Programs read the environment when they start, so a terminal, VS Code or Claude Code that was
already running keeps the old PATH until it is restarted.
"""

import ntpath
import os
import sys
from pathlib import Path
from typing import cast

from invoke import Context, Exit, task

from . import util

_ENV_KEY = "Environment"


def _require_windows() -> None:
    if sys.platform != "win32":
        raise Exit("[windows] runs on native Windows only")


def declared_dirs() -> list[str]:
    """Every enabled package's `windows_path` entries, as `%USERPROFILE%`-relative strings."""
    dirs: list[str] = []
    for cfg in util.enabled_packages().values():
        for entry in cfg.get("windows_path", []):
            spelled = entry.replace("/", "\\")
            if spelled.startswith("~\\"):
                spelled = "%USERPROFILE%" + spelled[1:]
            if spelled not in dirs:
                dirs.append(spelled)
    return dirs


def _same(a: str, b: str, expand: dict[str, str]) -> bool:
    def norm(p: str) -> str:
        for var, value in expand.items():
            p = p.replace(f"%{var}%", value)
        return ntpath.normcase(ntpath.normpath(p)).rstrip("\\")

    return norm(a) == norm(b)


def with_dirs_first(entries: list[str], dirs: list[str], expand: dict[str, str]) -> list[str]:
    """`entries` with `dirs` moved or added to the front, in order; everything else keeps its order.

    `expand` maps variable names to values for comparison only, so an entry already present as an
    absolute path and declared as `%USERPROFILE%\\...` is recognised as the same directory.
    """
    rest = [e for e in entries if e and not any(_same(e, d, expand) for d in dirs)]
    return [*dirs, *rest]


def _read_user_path() -> tuple[str, int]:
    if sys.platform != "win32":
        return "", 0
    import winreg  # noqa: PLC0415 — Windows-only module, imported after the platform check

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _ENV_KEY) as key:
        try:
            value = cast(object, winreg.QueryValueEx(key, "Path")[0])
        except FileNotFoundError:
            return "", winreg.REG_EXPAND_SZ
    return (value if isinstance(value, str) else ""), winreg.REG_EXPAND_SZ


def _write_user_path(value: str) -> None:
    if sys.platform != "win32":
        return
    import ctypes  # noqa: PLC0415 — the broadcast below exists on Windows only
    import winreg  # noqa: PLC0415 — Windows-only module, imported after the platform check

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _ENV_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, value)
    # Tell running programs (Explorer, and so anything started from it) that the environment changed.
    hwnd_broadcast, wm_settingchange, smto_abortifhung = 0xFFFF, 0x001A, 0x0002
    ctypes.windll.user32.SendMessageTimeoutW(
        hwnd_broadcast, wm_settingchange, 0, "Environment", smto_abortifhung, 5000, None
    )


def _expansions() -> dict[str, str]:
    return {"USERPROFILE": os.environ.get("USERPROFILE", str(Path.home()))}


@task
def check_path(c: Context):
    """Report whether every declared `windows_path` directory is first on the user PATH. Read-only."""
    _require_windows()
    dirs = declared_dirs()
    entries = _read_user_path()[0].split(";")
    wanted = with_dirs_first(entries, dirs, _expansions())
    ok = [e for e in entries if e] == wanted
    print(f"[windows] user PATH: {'ok' if ok else 'needs `inv windows.configure-path`'} ({len(dirs)} declared)")
    for d in dirs:
        print(f"[windows]   {d}")
    if not ok:
        raise Exit(code=1)


@task
def configure_path(c: Context):
    """Put every declared `windows_path` directory first on the user PATH (HKCU), in order.

    Every other entry keeps its place. Restart terminals, editors and Claude Code afterwards: a
    running program keeps the PATH it started with.
    """
    _require_windows()
    dirs = declared_dirs()
    current, _ = _read_user_path()
    entries = current.split(";")
    wanted = with_dirs_first(entries, dirs, _expansions())
    if [e for e in entries if e] == wanted:
        print(f"[windows] user PATH already starts with the {len(dirs)} declared director(y/ies)")
        return
    if util.DRY_RUN:
        print(f"[windows] would set the user PATH to start with: {'; '.join(dirs)}")
        return
    _write_user_path(";".join(wanted))
    print(f"[windows] user PATH now starts with: {'; '.join(dirs)} (restart programs to pick it up)")
