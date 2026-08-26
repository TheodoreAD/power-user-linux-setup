"""Normalize the `.desktop` launchers Google Chrome generates for its installed PWAs.

Chrome writes one `~/.local/share/applications/chrome-<app-id>-<Profile>.desktop` per (app,
profile) pair, and those files are unhelpful in three specific ways once more than one Chrome
profile is signed in:

1. **Every copy carries the same `Name`.** Gmail installed in three profiles produces three tiles
   all called "Gmail", indistinguishable in the app grid.
2. **Some copies carry `NoDisplay=true`**, which hides them from the grid entirely — so the apps
   belonging to the profile actually in use can be impossible to find or pin, while other
   profiles' copies are the ones on offer.
3. **None of them carry `--ozone-platform=x11`**, which matters only in the narrow case where a
   PWA tile starts the session's first Chrome process (see contributing/chrome-ozone.md).

These files belong to Chrome, not to this repo, so this module is deliberately **not** part of the
`deploy.*` family: `tasks/deploy.py` only ever writes paths PULSE created and can prove it wrote
(contributing/deploy.md), and that ownership model must not be blurred by a task that edits another
program's generated files. Chrome rewrites them whenever a PWA is installed or updated, so
`inv chrome.fix-launchers` is a re-runnable repair, never a permanent fix — which is also why it is
wired into no phase and no hook, and only ever runs when asked.

The desired state is derived rather than configured. Profile display names come from Chrome's own
`Local State`, and the profile whose apps should be visible defaults to the one Chrome itself
records as `last_used`.

`inv chrome.status` additionally reports which autostart entries can start Chrome and whether each
carries the ozone flag. That is a separate question from the launchers above and the one that
actually decides the outcome: the ozone platform is fixed by the *first* Chrome process of the
session, so an unflagged autostart entry silently discards the flag on every launcher. It is
reported and never repaired — the arrangement that makes it come out right (being the only starter)
is partly manual, and PULSE has no way to re-apply it.

Flagging the *launchers* is therefore a separate, opt-in question (`--ozone`), not something
`[packages.google-chrome-x11]` being enabled implies. It buys only the case where a PWA tile starts
the session's first Chrome process, and it costs per-profile pinning, because every copy of an app
carries the same `StartupWMClass` and X11 has no other way to tell two profiles' windows apart.
contributing/chrome-ozone.md has the measurements behind both halves.
"""

import re
from pathlib import Path
from typing import NamedTuple, cast

from invoke import Context, task

from . import util

_APPLICATIONS_DIR = Path.home() / ".local" / "share" / "applications"
_LOCAL_STATE = Path.home() / ".config" / "google-chrome" / "Local State"
_LAUNCHER_GLOB = "chrome-*.desktop"

# Separator between an app's own name and its profile label: "Gmail — Main". An em dash rather than
# a hyphen so it cannot be confused with a hyphen inside an app's real name.
_LABEL_SEP = " — "

_OZONE_FLAG = "--ozone-platform=x11"
_OZONE_PACKAGE = "google-chrome-x11"

# Component extensions Chrome installs for its own use and writes launchers for. They are hidden on
# purpose and are not apps anyone launches, so they are left exactly as found.
_INTERNAL_APP_IDS = frozenset(
    {
        "nmmhkkegccagdldgiimedpiccmgmieda",  # Chrome Web Store Payments
    }
)

_ENTRY_SECTION = "[Desktop Entry]"

# Where a Chrome launch can be triggered at login. User entries mask system ones of the same
# filename, per the XDG autostart spec, so the order here is priority order.
_AUTOSTART_DIRS: tuple[Path, ...] = (
    Path.home() / ".config" / "autostart",
    Path("/etc/xdg/autostart"),
)

# The two names an autostart entry uses to launch Chrome itself: the /usr/bin symlink and the
# /opt wrapper it points at. Chrome's PWA entries use the latter.
_CHROME_BINARIES = frozenset({"google-chrome", "google-chrome-stable"})


class Launcher(NamedTuple):
    """One `chrome-<app-id>-<Profile>.desktop` file, split into the parts encoded in its name."""

    path: Path
    app_id: str
    profile_dir: str


class Profiles(NamedTuple):
    """What Chrome's `Local State` says about the profiles on this machine."""

    labels: dict[str, str]  # profile directory ("Profile 2") -> display name ("Main")
    primary: str | None  # profile directory Chrome last used, if it records one


class Change(NamedTuple):
    """One edit `fix_launchers` made (or would make) to one file."""

    field: str
    detail: str


class Starter(NamedTuple):
    """One enabled autostart entry that launches Chrome itself."""

    path: Path
    exec_value: str
    has_flag: bool


def parse_launcher(path: Path) -> Launcher | None:
    """Split `chrome-<app-id>-<Profile_2>.desktop` into its app-id and profile directory.

    Returns None for any filename that isn't one of Chrome's PWA launchers. Chrome's extension ids
    are 32 lowercase letters and never contain a hyphen, so the first hyphen after the `chrome-`
    prefix is unambiguously the app-id/profile boundary even though profile names contain
    underscores.
    """
    stem = path.stem
    if not stem.startswith("chrome-"):
        return None
    app_id, _, profile = stem[len("chrome-") :].partition("-")
    if not app_id or not profile:
        return None
    # Chrome writes the profile *directory* with spaces replaced by underscores.
    return Launcher(path=path, app_id=app_id, profile_dir=profile.replace("_", " "))


def _json_object(value: object) -> dict[str, object] | None:
    """`value` as a JSON object, or None when it isn't one.

    Chrome's `Local State` is a third-party file this repo neither writes nor validates, so every
    level is checked rather than assumed — a shape change upstream should skip a launcher, not
    raise out of the whole task.
    """
    return cast("dict[str, object]", value) if isinstance(value, dict) else None


def read_profiles(local_state: Path = _LOCAL_STATE) -> Profiles:
    """Read profile display names and the last-used profile out of Chrome's `Local State`.

    Returns empty/None rather than raising when Chrome isn't installed or the file has a shape this
    doesn't recognize — a launcher whose profile has no display name is reported and skipped, which
    is more useful than aborting the whole pass.
    """
    if not local_state.exists():
        return Profiles(labels={}, primary=None)

    state = _json_object(util.load_json(local_state))
    section = _json_object(state.get("profile")) if state is not None else None
    if section is None:
        return Profiles(labels={}, primary=None)

    labels: dict[str, str] = {}
    for directory, info in (_json_object(section.get("info_cache")) or {}).items():
        entry = _json_object(info)
        name = entry.get("name") if entry is not None else None
        if isinstance(name, str) and name:
            labels[directory] = name

    last_used = section.get("last_used")
    primary = last_used if isinstance(last_used, str) and last_used else None
    return Profiles(labels=labels, primary=primary)


def strip_label(name: str, known_labels: frozenset[str]) -> str:
    """Remove a previously-applied `— <profile>` suffix, so a renamed profile relabels cleanly."""
    base, sep, suffix = name.rpartition(_LABEL_SEP)
    return base if sep and suffix in known_labels else name


def add_ozone_flag(exec_value: str) -> str:
    """Insert `--ozone-platform=x11` directly after the executable in an `Exec=` value."""
    if _OZONE_FLAG in exec_value:
        return exec_value
    binary, sep, rest = exec_value.partition(" ")
    return f"{binary} {_OZONE_FLAG}{sep}{rest}"


def rewrite(
    text: str, *, label: str, known_labels: frozenset[str], unhide: bool, ozone: bool
) -> tuple[str, list[Change]]:
    """Apply the three normalizations to one launcher's text. Pure; returns the new text + changes.

    Only the `[Desktop Entry]` section's `Name` is relabelled. A PWA's file also carries
    `[Desktop Action ...]` sections whose own `Name=` lines are the right-click shortcut labels
    ("Search", "Shorts", "Subscriptions" on YouTube) — relabelling those would corrupt the menu.
    `Exec=` lines, in contrast, need the ozone flag in *every* section, since each action is its own
    launch path.
    """
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    changes: list[Change] = []
    in_entry = False
    named = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("["):
            in_entry = stripped == _ENTRY_SECTION

        if in_entry and not named and stripped.startswith("Name="):
            named = True
            current = stripped[len("Name=") :]
            wanted = f"{strip_label(current, known_labels)}{_LABEL_SEP}{label}"
            if current != wanted:
                changes.append(Change("Name", f"{current!r} -> {wanted!r}"))
                out.append(f"Name={wanted}\n")
                continue

        if in_entry and unhide and stripped == "NoDisplay=true":
            changes.append(Change("NoDisplay", "removed (hidden from the app grid)"))
            continue

        if ozone and stripped.startswith("Exec="):
            current = stripped[len("Exec=") :]
            wanted = add_ozone_flag(current)
            if current != wanted:
                changes.append(Change("Exec", f"added {_OZONE_FLAG}"))
                out.append(f"Exec={wanted}\n")
                continue

        out.append(line)

    return "".join(out), changes


def entry_exec(text: str) -> str | None:
    """The `[Desktop Entry]` section's `Exec=` value — the one autostart actually runs.

    A PWA's file also carries `[Desktop Action ...]` sections with their own `Exec=` lines, which
    autostart never runs, so taking the first `Exec=` anywhere in the file would report a
    right-click shortcut as if it were a startup launch.
    """
    in_entry = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_entry = stripped == _ENTRY_SECTION
            continue
        if in_entry and stripped.startswith("Exec="):
            return stripped[len("Exec=") :]
    return None


def autostart_disabled(text: str) -> bool:
    """True when an autostart entry is present on disk but switched off.

    Two independent mechanisms, either of which is enough: `Hidden=true` is the XDG spec's
    "treat this as deleted", and `X-GNOME-Autostart-enabled=false` is what GNOME's Startup
    Applications writes when you untick an entry.
    """
    in_entry = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_entry = stripped == _ENTRY_SECTION
            continue
        if in_entry and stripped in ("Hidden=true", "X-GNOME-Autostart-enabled=false"):
            return True
    return False


def launches_chrome(exec_value: str) -> bool:
    """True when an `Exec=` value starts the Chrome browser itself.

    Matches on any token's basename rather than just the first, so an `env VAR=x /usr/bin/…`
    form is still recognized. A PWA entry counts too: `--app-id` still starts the browser
    process, and it is the browser process that fixes the ozone platform for the whole session.
    """
    return any(Path(token).name in _CHROME_BINARIES for token in exec_value.split())


def chrome_starters(dirs: tuple[Path, ...] = _AUTOSTART_DIRS) -> list[Starter]:
    """Every enabled autostart entry that launches Chrome, nearest directory winning.

    Filename masking is part of the XDG autostart spec: a `~/.config/autostart/foo.desktop`
    replaces `/etc/xdg/autostart/foo.desktop` outright rather than adding to it, so a file that
    has been masked must not be counted as a second starter.
    """
    starters: list[Starter] = []
    seen: set[str] = set()
    for directory in dirs:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.desktop")):
            if path.name in seen:
                continue
            seen.add(path.name)
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            exec_value = entry_exec(text)
            if exec_value is None or not launches_chrome(exec_value) or autostart_disabled(text):
                continue
            starters.append(Starter(path, exec_value, _OZONE_FLAG in exec_value))
    return starters


def _report_starters(ozone: bool) -> int:
    """Print the autostart picture and return how many entries would claim the wrong platform.

    Whichever Chrome process starts first fixes the ozone platform for every window that follows,
    so what matters is not that *a* flagged entry exists but that no unflagged one can beat it.
    See contributing/chrome-ozone.md — a filename chosen to sort first was measured losing this
    race, because gnome-session starts autostart entries in parallel.
    """
    starters = chrome_starters()
    print(f"[chrome] autostart entries launching Chrome: {len(starters)}")
    for starter in starters:
        print(f"[chrome]   {starter.path.name:<40} {'flag ok' if starter.has_flag else 'NO FLAG'}")

    if not ozone:
        return 0
    if not starters:
        print("[chrome] nothing autostarts Chrome — the flag then depends on which launcher you click")
        return 0

    unflagged = [s for s in starters if not s.has_flag]
    if unflagged:
        print(f"[chrome] DRIFT: {len(unflagged)} of {len(starters)} can start Chrome without {_OZONE_FLAG}")
        print("[chrome] whichever starts first fixes the platform for the whole session — see docs/chrome.md")
    else:
        print("[chrome] ok — every Chrome autostart entry carries the flag")
    return len(unflagged)


def _launchers() -> list[Launcher]:
    found = (parse_launcher(path) for path in sorted(_APPLICATIONS_DIR.glob(_LAUNCHER_GLOB)))
    return [launcher for launcher in found if launcher is not None]


def _is_hidden(text: str) -> bool:
    return re.search(r"^NoDisplay=true$", text, re.MULTILINE) is not None


def _entry_name(text: str) -> str:
    match = re.search(r"^Name=(.*)$", text, re.MULTILINE)
    return match.group(1) if match else "?"


def _summarize(changes: list[Change]) -> str:
    """One status word per launcher: "ok", or each drifted field once with a count if repeated.

    A single file can need the same fix several times — a PWA with right-click shortcuts has one
    `Exec=` per action — and listing "Exec drift" four times says nothing "Exec drift x4" doesn't.
    """
    if not changes:
        return "ok"
    counts: dict[str, int] = {}
    for change in changes:
        counts[change.field] = counts.get(change.field, 0) + 1
    return ", ".join(f"{field} drift{f' x{n}' if n > 1 else ''}" for field, n in counts.items())


def _ozone_required() -> bool:
    """True when [packages.google-chrome-x11] is enabled — Chrome is meant to run on X11 here."""
    return _OZONE_PACKAGE in util.enabled_packages()


def _ozone_for_launchers(opt_in: bool) -> bool:
    """Whether to treat a launcher's missing ozone flag as drift. Opt-in, and only when required.

    Asking for the flag on a machine that doesn't want X11 at all would write a flag that is simply
    wrong, so the package still gates it — but the reverse does not hold, and that asymmetry is the
    whole point: see this module's docstring for why the launchers are left unflagged by default.
    """
    if not opt_in:
        return False
    if not _ozone_required():
        print(f"[chrome] --ozone ignored: [packages.{_OZONE_PACKAGE}] is not enabled, so x11 isn't wanted here")
        return False
    return True


def _plan(
    launchers: list[Launcher], profiles: Profiles, *, primary: str | None, ozone: bool
) -> list[tuple[Launcher, str, list[Change]]]:
    """Work out every launcher's new text without writing anything. Skips internal and unknown ones."""
    known_labels = frozenset(profiles.labels.values())
    planned: list[tuple[Launcher, str, list[Change]]] = []
    for launcher in launchers:
        if launcher.app_id in _INTERNAL_APP_IDS:
            continue
        label = profiles.labels.get(launcher.profile_dir)
        if label is None:
            print(f"[chrome] skipping {launcher.path.name} — no display name for {launcher.profile_dir!r}")
            continue
        new_text, changes = rewrite(
            launcher.path.read_text(encoding="utf-8"),
            label=label,
            known_labels=known_labels,
            unhide=launcher.profile_dir == primary,
            ozone=ozone,
        )
        if changes:
            planned.append((launcher, new_text, changes))
    return planned


@task(help={"ozone": f"Also treat a launcher missing {_OZONE_FLAG} as drift (off by default)."})
def status(c: Context, ozone: bool = False):
    """Report who starts Chrome at login, then every PWA launcher's profile, visibility and flag.

    Strictly read-only — `inv chrome.fix-launchers` is the repair path for the launchers. Chrome
    regenerates those whenever a PWA is installed or updated, so drift reported there is expected
    over time rather than a sign anything is broken. The autostart section has no repair path at
    all and is reported only.
    """
    profiles = read_profiles()
    launchers = _launchers()
    required = _ozone_required()
    ozone = _ozone_for_launchers(ozone)

    print(f"[chrome] {_OZONE_FLAG}: {'required' if required else 'not required'} ([packages.{_OZONE_PACKAGE}])")
    _report_starters(required)

    if not launchers:
        print(f"[chrome] no PWA launchers found in {_APPLICATIONS_DIR}")
        return

    primary = profiles.primary
    print(f"[chrome] {len(launchers)} launcher(s) in {_APPLICATIONS_DIR}")
    print(f"[chrome] primary profile: {primary or 'unknown'} ({profiles.labels.get(primary or '', '?')})")

    known_labels = frozenset(profiles.labels.values())
    drifted = 0
    for launcher in launchers:
        label = profiles.labels.get(launcher.profile_dir)
        text = launcher.path.read_text(encoding="utf-8")
        name = _entry_name(text)
        if launcher.app_id in _INTERNAL_APP_IDS:
            print(f"[chrome]   {name:<32} internal (left alone)")
            continue
        if label is None:
            print(f"[chrome]   {name:<32} UNKNOWN PROFILE {launcher.profile_dir!r}")
            continue
        _, changes = rewrite(
            text,
            label=label,
            known_labels=known_labels,
            unhide=launcher.profile_dir == primary,
            ozone=ozone,
        )
        if changes:
            drifted += 1
        hidden = " [hidden]" if _is_hidden(text) else ""
        print(f"[chrome]   {name:<32} {launcher.profile_dir:<12} {_summarize(changes)}{hidden}")

    print(f"[chrome] {drifted} launcher(s) need fixing — inv chrome.fix-launchers" if drifted else "[chrome] all ok")
    if required and not ozone:
        print(f"[chrome] launchers are not checked for {_OZONE_FLAG} — it costs per-profile pinning.")
        print("[chrome] pass --ozone to include it; see contributing/chrome-ozone.md")


@task(
    help={
        "yes": "Skip the confirmation prompt.",
        "profile": "Treat this profile directory as primary instead of Chrome's last_used, e.g. 'Profile 2'.",
        "ozone": f"Also add {_OZONE_FLAG} to every Exec (off by default — it costs per-profile pinning).",
    }
)
def fix_launchers(c: Context, yes: bool = False, profile: str | None = None, ozone: bool = False):
    """Label every Chrome PWA launcher by profile and unhide the primary profile's.

    Filenames are never changed: `org.gnome.shell favorite-apps` pins launchers by filename, so a
    rename would silently drop every pinned PWA from the dash.

    Chrome owns these files and rewrites them on PWA install/update, so this is a repair to re-run,
    not a fix that sticks. Run `inv chrome.status` first to see what would change.
    """
    profiles = read_profiles()
    launchers = _launchers()
    if not launchers:
        print(f"[chrome] no PWA launchers found in {_APPLICATIONS_DIR}")
        return

    primary = profile or profiles.primary
    if primary is not None and primary not in profiles.labels:
        print(f"[chrome] unknown profile {primary!r} — known: {', '.join(sorted(profiles.labels)) or 'none'}")
        return

    planned = _plan(launchers, profiles, primary=primary, ozone=_ozone_for_launchers(ozone))

    if not planned:
        print("[chrome] every launcher already normalized — nothing to do")
        return

    for launcher, _, changes in planned:
        print(f"[chrome] {launcher.path.name}")
        for change in changes:
            print(f"[chrome]     {change.field}: {change.detail}")

    if util.DRY_RUN:
        print(f"[chrome] would rewrite {len(planned)} launcher(s)")
        return

    if not (yes or util.ASSUME_YES or util.confirm(f"[chrome] rewrite {len(planned)} launcher(s)?")):
        print("[chrome] aborted")
        return

    for launcher, new_text, _ in planned:
        launcher.path.write_text(new_text, encoding="utf-8")
    print(f"[chrome] rewrote {len(planned)} launcher(s)")

    if util.command_exists("update-desktop-database"):
        c.run(f"update-desktop-database {_APPLICATIONS_DIR}", warn=True, hide=True)
    print("[chrome] note: Chrome rewrites these files on PWA install/update — re-run then")
