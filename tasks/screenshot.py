import ast
import os
import re
import shutil
from pathlib import Path
from typing import cast

from invoke import task

from . import util

# GNOME 46 (Ubuntu 24.04) keeps screenshot keybindings in org.gnome.shell.keybindings, not the
# older org.gnome.settings-daemon.plugins.media-keys schema (that schema's screenshot/-clip/
# window-screenshot/-clip/area-screenshot/-clip keys no longer exist on this GNOME version).
_SHELL_KEYBINDINGS_SCHEMA = "org.gnome.shell.keybindings"
_MEDIA_KEYS_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
_CUSTOM_SCHEMA = f"{_MEDIA_KEYS_SCHEMA}.custom-keybinding"
_CUSTOM_PATH_PREFIX = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings"

# Only these 2 are handed to Flameshot. `screenshot-window` (Alt+PrtSc) is deliberately left
# alone: reading gnome-shell 46.0's js/ui/screenshot.js confirms it already saves to
# ~/Pictures/Screenshots AND copies to the clipboard by default (_storeScreenshot() does both
# unconditionally) — Flameshot has no window-capture mode to offer instead, and none is needed.
# `show-screen-recording-ui` (Ctrl+Shift+Alt+R, screencast) is untouched for the same
# no-equivalent reason — Flameshot has no video/recording capability at all.
_MANAGED_SHELL_KEYS = ["show-screenshot-ui", "screenshot"]

_SCREENSHOTS_DIR = Path.home() / "Pictures" / "Screenshots"
_FLAMESHOT_INI = Path.home() / ".config" / "flameshot" / "flameshot.ini"
_DESKTOP_FILE = Path("/usr/share/applications/org.flameshot.Flameshot.desktop")


def _is_wayland() -> bool:
    return os.environ.get("XDG_SESSION_TYPE") == "wayland"


def _flameshot_bin() -> str:
    return shutil.which("flameshot") or "/usr/bin/flameshot"


def _bindings() -> list[dict]:
    """The 2 custom keybindings that take over from GNOME's show-screenshot-ui/screenshot."""
    prefix = f"QT_QPA_PLATFORM=wayland {_flameshot_bin()}" if _is_wayland() else _flameshot_bin()
    return [
        {
            "name": "Flameshot GUI",
            "binding": "Print",
            "command": f'bash -c "{prefix} gui -p {_SCREENSHOTS_DIR} -c"',
        },
        {
            "name": "Flameshot full",
            "binding": "<Shift>Print",
            "command": f'bash -c "{prefix} full -p {_SCREENSHOTS_DIR} -c"',
        },
    ]


# ---------------------------------------------------------------------------
# ini file surgery (flameshot.ini uses Qt's QSettings ini format, not stdlib configparser-safe)
# ---------------------------------------------------------------------------


def _set_ini_key(path: Path, key: str, value: str) -> bool:
    """Idempotently set `key=value` under [General] in a Qt-style ini file. Returns True if changed."""
    text = path.read_text() if path.exists() else ""
    new_line = f"{key}={value}"
    line_re = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    match = line_re.search(text)
    if match:
        if match.group(0) == new_line:
            return False
        new_text = line_re.sub(new_line, text, count=1)
    elif "[General]" in text:
        new_text = text.replace("[General]", f"[General]\n{new_line}", 1)
    else:
        new_text = text.rstrip("\n") + ("\n\n" if text.strip() else "") + f"[General]\n{new_line}\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_text)
    return True


def _read_ini_key(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    match = re.search(rf"^{re.escape(key)}=(.*)$", path.read_text(), re.MULTILINE)
    return match.group(1) if match else None


# ---------------------------------------------------------------------------
# gsettings custom-keybindings list (shared across all GNOME custom shortcuts, not just ours)
# ---------------------------------------------------------------------------


def _get_custom_keybindings(c) -> list[str]:
    result = c.run(f"gsettings get {_MEDIA_KEYS_SCHEMA} custom-keybindings", hide=True, warn=True)
    stdout = (result.stdout or "").strip()
    if not stdout or stdout in ("@as []", "[]"):
        return []
    return cast(list[str], ast.literal_eval(stdout))


def _set_custom_keybindings(c, paths: list[str]) -> None:
    literal = "[" + ", ".join(f"'{p}'" for p in paths) + "]" if paths else "@as []"
    c.run(f'gsettings set {_MEDIA_KEYS_SCHEMA} custom-keybindings "{literal}"', hide=True)


def _slot_name(c, path: str) -> str:
    result = c.run(f"gsettings get {_CUSTOM_SCHEMA}:{path} name", hide=True, warn=True)
    return (result.stdout or "").strip().strip("'")


def _next_free_index(paths: list[str]) -> int:
    used = {int(m.group(1)) for p in paths if (m := re.search(r"/custom(\d+)/$", p))}
    i = 0
    while i in used:
        i += 1
    return i


# ---------------------------------------------------------------------------
# tasks
# ---------------------------------------------------------------------------


@task
def enable(c):  # noqa: C901
    """Bind PrtSc/Shift+PrtSc to Flameshot (save + clipboard, no dialog), disabling the matching
    GNOME defaults.

    Alt+PrtSc is left alone — GNOME's own `screenshot-window` action already saves to
    ~/Pictures/Screenshots and copies to the clipboard by default (verified in gnome-shell source),
    and Flameshot has no active-window capture mode to offer instead. The screencast shortcut
    (Ctrl+Shift+Alt+R) is untouched too — Flameshot has no video capability.
    """
    if not util.command_exists("flameshot"):
        print(
            "[screenshot] flameshot not installed — enable [packages.flameshot] in setup.toml "
            "and run inv apt.install-base"
        )
        return

    bindings = _bindings()

    if util.DRY_RUN:
        for key in _MANAGED_SHELL_KEYS:
            result = c.run(f"gsettings get {_SHELL_KEYBINDINGS_SCHEMA} {key}", hide=True, warn=True)
            bound = (result.stdout or "").strip() not in ("@as []", "[]")
            print(f"[screenshot] GNOME {key}: {'would disable' if bound else 'ok (already disabled)'}")
        paths = _get_custom_keybindings(c)
        existing_names = {_slot_name(c, p) for p in paths}
        for b in bindings:
            state = "ok (already bound)" if b["name"] in existing_names else "would bind"
            print(f"[screenshot] {b['binding']} -> {b['name']}: {state}")
        save_ok = _read_ini_key(_FLAMESHOT_INI, "savePath") == str(_SCREENSHOTS_DIR)
        print(f"[screenshot] flameshot savePath: {'ok' if save_ok else f'would set -> {_SCREENSHOTS_DIR}'}")
        return

    _SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    if _set_ini_key(_FLAMESHOT_INI, "savePath", str(_SCREENSHOTS_DIR)):
        print(f"[screenshot] flameshot savePath -> {_SCREENSHOTS_DIR}")

    if _is_wayland() and _DESKTOP_FILE.exists():
        content = _DESKTOP_FILE.read_text()
        if "QT_QPA_PLATFORM=wayland" not in content:
            c.run(
                f"{util.SUDO} sed -i 's|Exec=flameshot|Exec=env QT_QPA_PLATFORM=wayland flameshot|g' {_DESKTOP_FILE}",
            )
            print("[screenshot] applied Wayland fix to Flameshot .desktop launcher")

    for key in _MANAGED_SHELL_KEYS:
        result = c.run(f"gsettings get {_SHELL_KEYBINDINGS_SCHEMA} {key}", hide=True, warn=True)
        if (result.stdout or "").strip() not in ("@as []", "[]"):
            c.run(f'gsettings set {_SHELL_KEYBINDINGS_SCHEMA} {key} "[]"', hide=True)
            print(f"[screenshot] disabled GNOME default: {key}")

    paths = _get_custom_keybindings(c)
    existing_by_name = {_slot_name(c, p): p for p in paths}
    list_changed = False
    for b in bindings:
        path = existing_by_name.get(b["name"])
        if path is None:
            path = f"{_CUSTOM_PATH_PREFIX}/custom{_next_free_index(paths)}/"
            paths.append(path)
            list_changed = True
        c.run(f'gsettings set {_CUSTOM_SCHEMA}:{path} name "{b["name"]}"', hide=True)
        c.run(f"gsettings set {_CUSTOM_SCHEMA}:{path} command '{b['command']}'", hide=True)
        c.run(f'gsettings set {_CUSTOM_SCHEMA}:{path} binding "{b["binding"]}"', hide=True)
        print(f"[screenshot] {b['binding']} -> {b['name']}")
    if list_changed:
        _set_custom_keybindings(c, paths)

    print("[screenshot] done — Alt+PrtSc (window capture) and the screencast shortcut are untouched")


@task
def disable(c):
    """Remove the 2 Flameshot keybindings and restore GNOME's shipped screenshot defaults."""
    if util.DRY_RUN:
        paths = _get_custom_keybindings(c)
        names = {b["name"] for b in _bindings()}
        bound = [p for p in paths if _slot_name(c, p) in names]
        print(
            f"[screenshot] would remove {len(bound)} custom keybinding(s)"
            if bound
            else "[screenshot] no custom keybindings to remove"
        )
        for key in _MANAGED_SHELL_KEYS:
            print(f"[screenshot] would reset GNOME default: {key}")
        return

    names = {b["name"] for b in _bindings()}
    paths = _get_custom_keybindings(c)
    keep, removed = [], []
    for p in paths:
        (removed if _slot_name(c, p) in names else keep).append(p)

    if removed:
        _set_custom_keybindings(c, keep)
        for p in removed:
            c.run(f"dconf reset -f {p}", warn=True)
        print(f"[screenshot] removed {len(removed)} custom keybinding(s)")
    else:
        print("[screenshot] no custom keybindings to remove")

    for key in _MANAGED_SHELL_KEYS:
        c.run(f"gsettings reset {_SHELL_KEYBINDINGS_SCHEMA} {key}", hide=True, warn=True)
    print("[screenshot] restored GNOME default screenshot shortcuts")


@task
def status(c):
    """Show current screenshot shortcut state: GNOME defaults vs the Flameshot bindings."""
    installed = util.command_exists("flameshot")
    print(f"[screenshot] flameshot installed: {'yes' if installed else 'no'}")

    for key in _MANAGED_SHELL_KEYS:
        result = c.run(f"gsettings get {_SHELL_KEYBINDINGS_SCHEMA} {key}", hide=True, warn=True)
        val = (result.stdout or "").strip()
        state = "disabled" if val in ("@as []", "[]") else f"bound ({val})"
        print(f"[screenshot] GNOME {key}: {state}")
    result = c.run(f"gsettings get {_SHELL_KEYBINDINGS_SCHEMA} screenshot-window", hide=True, warn=True)
    print(f"[screenshot] GNOME screenshot-window (untouched, always save+clipboard): {(result.stdout or '').strip()}")

    paths = _get_custom_keybindings(c)
    names = {_slot_name(c, p) for p in paths}
    for b in _bindings():
        print(f"[screenshot] {b['binding']} ({b['name']}): {'bound' if b['name'] in names else 'not bound'}")

    save_path = _read_ini_key(_FLAMESHOT_INI, "savePath")
    if save_path is None:
        print("[screenshot] flameshot.ini: not found (never configured)")
    else:
        ok = save_path == str(_SCREENSHOTS_DIR)
        print(f"[screenshot] flameshot savePath: {'ok' if ok else f'MISMATCH ({save_path})'}")
