import json
import re
import subprocess
import urllib.request
import zipfile
from functools import cache
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from invoke import Context, task

from . import util

# Match either a quoted string (kept) or a // line comment (removed).
_JSONC_COMMENT_RE = re.compile(r'"(?:[^"\\]|\\.)*"|(//.*)')
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


def _load_jsonc(text: str) -> util.JsonObject:
    """Parse JSON-with-comments (JSONC) as used by VS Code settings.json."""
    text = _JSONC_COMMENT_RE.sub(lambda m: "" if m.group(1) else m.group(0), text)
    text = _TRAILING_COMMA_RE.sub(r"\1", text)
    return cast(util.JsonObject, util.parse_json(text))


_FONTS_DIR = Path.home() / ".local" / "share" / "fonts"
_BASE_URL = "https://github.com/ryanoasis/nerd-fonts/releases/latest/download"

# Classic-confinement snap VS Code and deb/apt both resolve to ~/.config/Code on Ubuntu;
# add the snap path as a fallback for installs that diverge.
_VSCODE_SETTINGS_PATHS = [
    Path.home() / ".config" / "Code" / "User" / "settings.json",
    Path.home() / "snap" / "code" / "current" / ".config" / "Code" / "User" / "settings.json",
]


def _load_vscode_settings(path: Path) -> util.JsonObject:
    """Parse VS Code settings.json, which is JSONC (comments + trailing commas allowed)."""
    text = path.read_text() if path.exists() and path.stat().st_size > 0 else ""
    if not text:
        return {}
    return _load_jsonc(text)


def _cfg() -> util.FontsSettings:
    return util.load_config().get("settings", {}).get("fonts", {})


def _families() -> list[util.FontFamily]:
    return _cfg().get("families", [])


@cache
def _fc_list() -> str:
    """Return full fc-list output, lower-cased. Cached — called once per process."""
    return subprocess.run(["fc-list"], capture_output=True, text=True, check=False).stdout.lower()


def _is_installed(entry: util.FontFamily) -> bool:
    """Check via fc-list (primary) or file glob (fallback if family not set).

    fc-list is agnostic to filename format, so it correctly detects v2 fonts
    (spaced filenames like "JetBrains Mono Regular Nerd Font Complete.ttf") and
    v3 fonts (compact filenames like "JetBrainsMonoNerdFont-Regular.ttf") alike —
    both register under the same OpenType family names in the font database.
    """
    family = entry.get("family")
    if family:
        terms = [family] if isinstance(family, str) else family
        fc = _fc_list()
        return any(term.lower() in fc for term in terms)
    return any(_FONTS_DIR.glob(entry.get("check", "")))


def _install_family(entry: util.FontFamily) -> int:
    name = entry["zip"]
    v3_glob = entry.get("check", "")

    # v3 files already present — nothing to do
    if v3_glob and any(_FONTS_DIR.glob(v3_glob)):
        print(f"  {name}: already installed")
        return 0

    # Remove any legacy (v2) files before installing v3
    legacy = entry.get("legacy", [])
    if isinstance(legacy, str):
        legacy = [legacy]
    removed = [f for glob in legacy for f in _FONTS_DIR.glob(glob)]
    for f in removed:
        f.unlink(missing_ok=True)
    if removed:
        print(f"  {name}: removed {len(removed)} legacy v2 files")

    # No v3_glob and fc-list already shows the family — skip (no migration needed)
    if not v3_glob and _is_installed(entry):
        print(f"  {name}: already installed")
        return 0

    url = f"{_BASE_URL}/{name}.zip"
    print(f"  {name}: downloading...", end=" ", flush=True)

    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / f"{name}.zip"
        urllib.request.urlretrieve(url, zip_path)

        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_path)

        font_files = list(tmp_path.glob("*.ttf")) or list(tmp_path.glob("*.otf"))
        for src in font_files:
            (_FONTS_DIR / src.name).write_bytes(src.read_bytes())

    print(f"{len(font_files)} files")
    return len(font_files)


@task
def install(c: Context):
    """Download and install Nerd Font families to ~/.local/share/fonts."""
    families = _families()
    if util.DRY_RUN:
        for entry in families:
            v3_glob = entry.get("check", "")
            if v3_glob and any(_FONTS_DIR.glob(v3_glob)):
                status = "ok"
            elif _is_installed(entry):
                status = "ok (v2 — will upgrade)"
            else:
                status = "MISSING"
            print(f"[fonts] {entry['zip']}: {status}")
        return
    _FONTS_DIR.mkdir(parents=True, exist_ok=True)
    total = sum(_install_family(entry) for entry in families)
    if total:
        print(f"[fonts] Rebuilding font cache ({total} new files)...")
        c.run("fc-cache -f", hide=True)
    print("[fonts] Done.")


@task
def configure(c: Context):  # noqa: C901
    """Set the configured monospace font as system default, GNOME Terminal, and VS Code font."""
    cfg = _cfg()
    monospace = cfg.get("monospace", "")
    terminal = cfg.get("terminal", monospace)
    vscode_settings = cfg.get("vscode", {})

    if util.DRY_RUN:
        mono_result = c.run(
            "gsettings get org.gnome.desktop.interface monospace-font-name",
            hide=True,
            warn=True,
        )
        current_mono = mono_result.stdout.strip().strip("'") if mono_result.ok else "not set"
        mono_ok = current_mono == monospace
        print(f"[fonts] system monospace: {'ok' if mono_ok else f'MISSING  (current: {current_mono!r})'}")

        term_result = c.run(
            "gsettings get org.gnome.Terminal.ProfilesList default",
            hide=True,
            warn=True,
        )
        if term_result.ok:
            profile = term_result.stdout.strip().strip("'")
            schema = f"org.gnome.Terminal.Legacy.Profile:/org/gnome/terminal/legacy/profiles/:/{profile}/"
            font_result = c.run(f"gsettings get {schema} font", hide=True, warn=True)
            current_term = font_result.stdout.strip().strip("'") if font_result.ok else "not set"
            term_ok = current_term == terminal
            print(f"[fonts] GNOME Terminal: {'ok' if term_ok else f'MISSING  (current: {current_term!r})'}")
        else:
            print("[fonts] GNOME Terminal: not found")

        settings_path = next((p for p in _VSCODE_SETTINGS_PATHS if p.parent.exists()), None)
        if settings_path and settings_path.exists():
            existing = _load_vscode_settings(settings_path)
            vscode_ok = all(existing.get(k) == v for k, v in vscode_settings.items())
            print(f"[fonts] VS Code: {util.ok_label(vscode_ok)}")
        else:
            print("[fonts] VS Code: not found")
        return

    if monospace:
        result = c.run(
            f'gsettings set org.gnome.desktop.interface monospace-font-name "{monospace}"',
            hide=True,
            warn=True,
        )
        if result.ok:
            print(f"[fonts] System monospace → {monospace}")
        else:
            print("[fonts] no org.gnome.desktop.interface schema (no GNOME) — skipping")

    result = c.run(
        "gsettings get org.gnome.Terminal.ProfilesList default",
        hide=True,
        warn=True,
    )
    if result.ok:
        profile = result.stdout.strip().strip("'")
        schema = f"org.gnome.Terminal.Legacy.Profile:/org/gnome/terminal/legacy/profiles/:/{profile}/"
        c.run(f"gsettings set {schema} use-system-font false", hide=True)
        c.run(f'gsettings set {schema} font "{terminal}"', hide=True)
        print(f"[fonts] GNOME Terminal → {terminal}")
    else:
        print("[fonts] GNOME Terminal not found — skipping")

    settings_path = next((p for p in _VSCODE_SETTINGS_PATHS if p.parent.exists()), None)
    if settings_path and vscode_settings:
        existing: util.JsonObject = {}
        if settings_path.exists() and settings_path.stat().st_size > 0:
            existing = _load_jsonc(settings_path.read_text())
        if not all(existing.get(k) == v for k, v in vscode_settings.items()):
            settings_path.write_text(json.dumps({**existing, **vscode_settings}, indent=2) + "\n")
            print(f"[fonts] VS Code → {settings_path}")
        else:
            print("[fonts] VS Code already configured")
    elif not settings_path:
        print("[fonts] VS Code settings.json not found — launch VS Code once, then re-run")
