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


FONTS_DIR = Path.home() / ".local" / "share" / "fonts"
_BASE_URL = "https://github.com/ryanoasis/nerd-fonts/releases/latest/download"

# Classic-confinement snap VS Code and deb/apt both resolve to ~/.config/Code on Ubuntu;
# add the snap path as a fallback for installs that diverge.
VSCODE_SETTINGS_PATHS = [
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


_FONT_KEYS = ("family", "family_mono", "family_short", "family_mono_short")


def _named() -> dict[str, str | int]:
    """The `[settings.fonts]` names, as the substitution variables every consumer builds from.

    Four names rather than two: fontconfig resolves the long form and the abbreviated one to the
    same file, but the JVM only enumerates the abbreviated one, so PyCharm needs `*_short` while
    everything else takes the long form. See the comment in `setup.toml`.

    Raises rather than defaulting: a missing font name would silently configure GNOME and VS Code
    with an empty family, which renders as the system fallback and looks like the Nerd Font simply
    failed to install.
    """
    cfg = _cfg()
    if missing := [k for k in _FONT_KEYS if k not in cfg]:
        raise util.missing_fields("settings.fonts", *missing)
    return {**{k: cfg[k] for k in _FONT_KEYS}, "size": cfg.get("size", 12)}  # pyright: ignore[reportTypedDictNotRequiredAccess]


def monospace_font() -> str:
    """GNOME's `<family> <size>` form, for `org.gnome.desktop.interface monospace-font-name` and
    the GNOME Terminal profile. Mono variant: both land in a terminal cell grid."""
    n = _named()
    return f"{n['family_mono']} {n['size']}"


def vscode_settings() -> util.JsonObject:
    """The VS Code keys to merge — the four font/size ones derived, plus whatever
    `[settings.fonts.vscode]` declares for anything that is not the font itself.

    `editor.fontFamily` takes a CSS-style list so VS Code has something to fall back to if the Nerd
    Font is missing; the integrated terminal takes the mono variant bare, matching every other
    terminal here.
    """
    n = _named()
    derived: util.JsonObject = {
        "editor.fontFamily": f"'{n['family']}', monospace",
        "editor.fontSize": n["size"],
        "terminal.integrated.fontFamily": n["family_mono"],
        "terminal.integrated.fontSize": n["size"],
    }
    return {**derived, **_cfg().get("vscode", {})}


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
    return any(FONTS_DIR.glob(entry.get("check", "")))


def _install_family(entry: util.FontFamily) -> int:
    name = entry["zip"]
    v3_glob = entry.get("check", "")

    # v3 files already present — nothing to do
    if v3_glob and any(FONTS_DIR.glob(v3_glob)):
        print(f"  {name}: already installed")
        return 0

    # Remove any legacy (v2) files before installing v3
    legacy = entry.get("legacy", [])
    if isinstance(legacy, str):
        legacy = [legacy]
    removed = [f for glob in legacy for f in FONTS_DIR.glob(glob)]
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
            (FONTS_DIR / src.name).write_bytes(src.read_bytes())

    print(f"{len(font_files)} files")
    return len(font_files)


@task
def install(c: Context):
    """Download and install Nerd Font families to ~/.local/share/fonts."""
    families = _families()
    if util.DRY_RUN:
        for entry in families:
            v3_glob = entry.get("check", "")
            if v3_glob and any(FONTS_DIR.glob(v3_glob)):
                status = "ok"
            elif _is_installed(entry):
                status = "ok (v2 — will upgrade)"
            else:
                status = "MISSING"
            print(f"[fonts] {entry['zip']}: {status}")
        return
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    total = sum(_install_family(entry) for entry in families)
    if total:
        print(f"[fonts] Rebuilding font cache ({total} new files)...")
        c.run("fc-cache -f", hide=True)
    print("[fonts] Done.")


@task
def configure(c: Context):  # noqa: C901
    """Set the configured monospace font as system default, GNOME Terminal, and VS Code font."""
    # All three derived from [settings.fonts]'s family/family_mono/size rather than declared
    # separately — GNOME and its terminal take the same mono string, and the VS Code keys are built
    # from the same two families. See vscode_settings().
    monospace = monospace_font()
    terminal = monospace
    settings = vscode_settings()

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

        settings_path = next((p for p in VSCODE_SETTINGS_PATHS if p.parent.exists()), None)
        if settings_path and settings_path.exists():
            existing = _load_vscode_settings(settings_path)
            vscode_ok = all(existing.get(k) == v for k, v in settings.items())
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

    settings_path = next((p for p in VSCODE_SETTINGS_PATHS if p.parent.exists()), None)
    if settings_path and settings:
        existing: util.JsonObject = {}
        if settings_path.exists() and settings_path.stat().st_size > 0:
            existing = _load_jsonc(settings_path.read_text())
        if not all(existing.get(k) == v for k, v in settings.items()):
            settings_path.write_text(json.dumps({**existing, **settings}, indent=2) + "\n")
            print(f"[fonts] VS Code → {settings_path}")
        else:
            print("[fonts] VS Code already configured")
    elif not settings_path:
        print("[fonts] VS Code settings.json not found — launch VS Code once, then re-run")


# ---------------------------------------------------------------------------
# Rendering the font into the repo-side configs that name it themselves
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent

# One rule per line that names a font in a repo-side config file: the pattern that finds it, and
# how to rebuild it from (family, family_mono, size). Four files, four formats — a regex per line
# rather than a parser per format, because each of these is this repo's own file with a known
# shape, and a Lua/XML/Qt-ini parser apiece would be far more machinery than the four lines earn.
_RENDERS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "config/terminator.conf",
        ((r"^(\s*font\s*=\s*).*$", r"\g<1>{family_mono} {size}"),),
    ),
    (
        "config/wezterm.lua",
        (
            (r'^(config\.font\s*=\s*wezterm\.font\s*")[^"]*(")', r"\g<1>{family_mono}\g<2>"),
            (r"^(config\.font_size\s*=\s*).*$", r"\g<1>{size}.0"),
        ),
    ),
    (
        "config/pycharm/editor-font.xml",
        (
            (r'(<option name="FONT_SIZE" value=")[^"]*(")', r"\g<1>{size}\g<2>"),
            (r'(<option name="FONT_SIZE_2D" value=")[^"]*(")', r"\g<1>{size}.0\g<2>"),
            (r'(<option name="FONT_FAMILY" value=")[^"]*(")', r"\g<1>{family_short}\g<2>"),
        ),
    ),
    (
        "config/pycharm/terminal-font.xml",
        (
            (r'(<option name="FONT_SIZE" value=")[^"]*(")', r"\g<1>{size}\g<2>"),
            (r'(<option name="FONT_SIZE_2D" value=")[^"]*(")', r"\g<1>{size}.0\g<2>"),
            # Mono here and the default variant in editor-font.xml above: PyCharm's embedded
            # terminal is a cell grid, its editor is not.
            (r'(<option name="FONT_FAMILY" value=")[^"]*(")', r"\g<1>{family_mono_short}\g<2>"),
        ),
    ),
)


def render_text(source: str, rules: tuple[tuple[str, str], ...]) -> str:
    """Apply one file's substitution rules to its text, with the configured font values.

    Pure, so the test suite can assert the four committed files already match what this would
    produce without writing anything — which is what catches a `[settings.fonts]` change that was
    never rendered.

    Raises when a rule matches nothing: a silently-skipped substitution would leave the old font in
    a file this claims to have updated, and a rename upstream (PyCharm changing an option name, say)
    is exactly how that would happen.
    """
    names = _named()
    for pattern, template in rules:
        replacement = template.format(**names)
        source, count = re.subn(pattern, replacement, source, flags=re.MULTILINE)
        if not count:
            raise RuntimeError(f"[fonts] pattern {pattern!r} matched nothing — has the file's shape changed?")
    return source


def rendered() -> dict[Path, str]:
    """What every repo-side config that names a font should contain, keyed by absolute path."""
    return {_REPO_ROOT / rel: render_text((_REPO_ROOT / rel).read_text(), rules) for rel, rules in _RENDERS}


@task(name="render-configs")
def render_configs(c: Context):
    """Rewrite the repo-side configs that name a font from `[settings.fonts]`.

    `inv fonts.configure` covers GNOME, GNOME Terminal and VS Code, which are settings applied to a
    live machine. Terminator, WezTerm and PyCharm read a config file instead, so their copy of the
    font lives in this repo and has to be rewritten rather than set — this is that half.

    Deliberately its own command, and deliberately not wired into `fix`/`check`/`precommit`: the
    output is committed and reviewed like any other change (`~/AGENTS.md`, "Regenerating a file from
    a canonical source"). Run it after changing `[settings.fonts]`, commit the diff, then
    `inv deploy.all` to push the new files to `~`. `PULSE_DRY_RUN=1` reports without writing.

    A test asserts the committed files already match this output, so a font change that skips this
    step fails CI rather than leaving one application on the old font.
    """
    changed = [path for path, text in rendered().items() if path.read_text() != text]
    if not changed:
        print(f"[fonts] {len(_RENDERS)} config(s) already match [settings.fonts]")
        return
    for path in changed:
        rel = path.relative_to(_REPO_ROOT)
        if util.DRY_RUN:
            print(f"[fonts] would rewrite {rel}")
            continue
        path.write_text(rendered()[path])
        print(f"[fonts] rewrote {rel}")
    if not util.DRY_RUN:
        print(f"[fonts] {len(changed)} file(s) rewritten — commit them, then `inv deploy.all`")


# ---------------------------------------------------------------------------
# Does the live machine actually agree?
# ---------------------------------------------------------------------------


def _gsettings(c: Context, args: str) -> str | None:
    """A gsettings value with its quoting stripped, or None when the schema isn't there."""
    result = c.run(f"gsettings get {args}", hide=True, warn=True)
    return result.stdout.strip().strip("'") if result.ok else None


def _file_font_rows(c: Context) -> list[tuple[str, str]]:
    """One `(label, verdict)` per deployed file that names a font.

    Asks the narrow question — does this file name the configured font — rather than "is it
    byte-identical to its source", which is `inv deploy.status`'s job and a different answer: a
    `config_files` destination is the user's to customize, so it may legitimately differ everywhere
    except the font line. Re-rendering the *deployed* text answers exactly that: if the
    substitutions change nothing, the file already names the right font.
    """
    from . import deploy, ide  # noqa: PLC0415 — avoids an import cycle at module load

    sources = {m.source: m.path for m in deploy.managed_paths().values() if m.source}
    sources.update({m.source: m.path for m in ide.managed_files() if m.source})

    rows: list[tuple[str, str]] = []
    for rel, rules in _RENDERS:
        path = sources.get(rel)
        if path is None:
            rows.append((rel, "not deployed here"))
            continue
        if not path.exists():
            rows.append((rel, f"MISSING — {path} not there"))
            continue
        text = path.read_text()
        try:
            rows.append((rel, "ok" if render_text(text, rules) == text else f"DIFFERS — {path}"))
        except RuntimeError:
            # render_text raises when a pattern matches nothing. Here that means the deployed file
            # has no font line where one is expected — worth reporting, never worth aborting.
            rows.append((rel, f"no font line found in {path}"))
    return rows


@task
def check(c: Context):
    """Report every place on this machine that names a font, and whether it agrees.

    Read-only, and the answer `inv deploy.status` cannot give: that one compares whole files, so a
    `config_files` destination the user has customized differs for reasons that have nothing to do
    with the font, and a stale font inside an otherwise-untouched file looks the same as any other
    edit. Confirmed worth having 2026-08-30 — `~/.config/terminator/config` sat on a different font
    for three months while every other consumer agreed, and nothing reported it.

    Covers both halves: the settings `inv fonts.configure` applies (GNOME, GNOME Terminal, VS Code)
    and the files `inv fonts.render-configs` writes (Terminator, WezTerm, PyCharm), read at their
    deployed paths rather than in the repo.
    """
    monospace = monospace_font()
    print(f"[fonts] [settings.fonts] → {monospace}\n")

    rows: list[tuple[str, str]] = []

    current = _gsettings(c, "org.gnome.desktop.interface monospace-font-name")
    if current is None:
        rows.append(("system monospace", "no GNOME schema here"))
    else:
        rows.append(("system monospace", "ok" if current == monospace else f"DIFFERS — {current!r}"))

    profile = _gsettings(c, "org.gnome.Terminal.ProfilesList default")
    if profile is None:
        rows.append(("GNOME Terminal", "not installed"))
    else:
        schema = f"org.gnome.Terminal.Legacy.Profile:/org/gnome/terminal/legacy/profiles/:/{profile}/"
        current = _gsettings(c, f"{schema} font")
        rows.append(("GNOME Terminal", "ok" if current == monospace else f"DIFFERS — {current!r}"))

    settings_path = next((p for p in VSCODE_SETTINGS_PATHS if p.parent.exists()), None)
    if settings_path is None or not settings_path.exists():
        rows.append(("VS Code", "not installed"))
    else:
        existing = _load_vscode_settings(settings_path)
        stale = [k for k, v in vscode_settings().items() if existing.get(k) != v]
        rows.append(("VS Code", "ok" if not stale else f"DIFFERS — {', '.join(stale)}"))

    rows.extend(_file_font_rows(c))

    width = max(len(label) for label, _ in rows)
    for label, verdict in rows:
        print(f"  {label:<{width}}  {verdict}")

    disagreeing = [label for label, verdict in rows if verdict.startswith(("DIFFERS", "MISSING", "no font"))]
    print()
    if disagreeing:
        print(f"[fonts] {len(disagreeing)} disagree: {', '.join(disagreeing)}")
        print("[fonts] settings: `inv fonts.configure`")
        print("[fonts] files:    `inv fonts.render-configs`, then `inv deploy.all` / `inv ide.configure-pycharm`")
    else:
        print(f"[fonts] all {len(rows)} agree")
