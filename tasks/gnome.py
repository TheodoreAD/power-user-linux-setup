import shlex
import shutil
from pathlib import Path

from invoke import task

from . import util

# System extensions that conflict with certain PULSE extensions.
# When a PULSE extension is enabled, its listed conflicts are disabled first.
CONFLICTS: dict[str, list[str]] = {
    # ubuntu-dock ships enabled by default; dash-to-panel replaces it entirely
    "dash-to-panel@jderose9.github.com": ["ubuntu-dock@ubuntu.com"],
    # tiling-assistant ships enabled on fresh Ubuntu 24.04; conflicts with tiling-shell
    # (both write to the same gsettings keys — tiling shortcuts get silently overwritten)
    "tilingshell@ferrarodomenico.com": ["tiling-assistant@ubuntu.com"],
}

# User extension directory — managed by gext and PULSE.
# System extensions live at /usr/share/gnome-shell/extensions/ and are never touched here.
_USER_EXT_DIR = Path.home() / ".local/share/gnome-shell/extensions"


def _installed_uuids(c) -> set[str]:
    result = c.run("gnome-extensions list", hide=True, warn=True)
    return set((result.stdout or "").splitlines())


def _enabled_uuids(c) -> set[str]:
    result = c.run("gnome-extensions list --enabled", hide=True, warn=True)
    return set((result.stdout or "").splitlines())


def _user_extensions_disabled(c) -> bool:
    result = c.run("gsettings get org.gnome.shell disable-user-extensions", hide=True, warn=True)
    return (result.stdout or "").strip() == "true"


def _apply_dconf(c, name: str, cfg: dict) -> None:
    """Write dconf keys declared in an extension's 'dconf' table. Values are GVariant strings."""
    for key, value in cfg.get("dconf", {}).items():
        result = c.run(f"dconf read {key}", hide=True, warn=True)
        current = (result.stdout or "").strip()
        if current == value:
            continue
        c.run(f"dconf write {key} {shlex.quote(value)}", warn=True)
        print(f"[{name}] dconf: {key.split('/')[-1]} = {value}")


@task
def extensions(c):  # noqa: C901
    """Install and enable GNOME Shell extensions declared in setup.toml via gext."""
    pkgs = util.packages_by_method(util.PackageMethod.GNOME_EXTENSION)
    if not pkgs:
        print("[gnome-extensions] no extensions enabled — set enabled = true in setup.toml")
        return

    if util.DRY_RUN:
        if _user_extensions_disabled(c):
            print("[gnome-extensions] WARNING: disable-user-extensions = true — all user extensions suppressed")
        installed = _installed_uuids(c)
        enabled = _enabled_uuids(c)
        for name, cfg in pkgs.items():
            uuid = cfg.get("uuid", "")
            if not uuid:
                print(f"[{name}] ego:{cfg.get('ego_id', '?')}: no uuid — cannot check")
                continue
            if uuid in enabled:
                status = "ok (enabled)"
            elif uuid in installed:
                status = "installed but NOT enabled"
            else:
                status = "MISSING"
            print(f"[{name}] {uuid}: {status}")
            for key, value in cfg.get("dconf", {}).items():
                result = c.run(f"dconf read {key}", hide=True, warn=True)
                current = (result.stdout or "").strip()
                dconf_status = "ok" if current == value else f"MISSING (would set: {value})"
                print(f"[{name}]   dconf {key.split('/')[-1]}: {dconf_status}")
        return

    if not util.command_exists("gext"):
        print("[gnome-extensions] gext not found — run 'inv python.tools' first")
        return

    # Ubuntu ships with disable-user-extensions = true in some configurations;
    # without this, gnome-extensions enable writes to dconf but nothing activates.
    if _user_extensions_disabled(c):
        print("[gnome-extensions] user extensions globally disabled — enabling...")
        c.run("gsettings set org.gnome.shell disable-user-extensions false", warn=True)

    installed = _installed_uuids(c)
    enabled = _enabled_uuids(c)

    for name, cfg in pkgs.items():
        uuid = cfg.get("uuid") or str(cfg.get("ego_id", ""))
        if not uuid:
            print(f"[{name}] no uuid or ego_id — skipping")
            continue

        # Disable any system extensions that conflict with this one.
        for conflict_uuid in CONFLICTS.get(uuid, []):
            if conflict_uuid in enabled:
                print(f"[{name}] disabling conflicting system extension: {conflict_uuid}")
                c.run(f"gnome-extensions disable {conflict_uuid}", warn=True)

        if uuid not in installed:
            # Some UUIDs have mixed case that confuses gext's EGO API lookup;
            # the numeric ego_id is unambiguous.
            install_ref = str(cfg.get("ego_id", "")) or uuid
            print(f"[{name}] installing {uuid}...")
            c.run(f"gext install {install_ref}", warn=True)
        else:
            print(f"[{name}] already installed")

        # gnome-extensions enable writes to dconf and persists across sessions;
        # gext enable only activates for the current session.
        if uuid not in enabled:
            c.run(f"gnome-extensions enable {uuid}", warn=True)
            print(f"[{name}] enabled")
        else:
            print(f"[{name}] already enabled")

        _apply_dconf(c, name, cfg)

    print("[gnome-extensions] complete")


@task
def enable(c):  # noqa: C901
    """Re-enable installed GNOME extensions from setup.toml without reinstalling missing ones."""
    pkgs = util.packages_by_method(util.PackageMethod.GNOME_EXTENSION)
    if not pkgs:
        print("[gnome-enable] no extensions enabled — set enabled = true in setup.toml")
        return

    if _user_extensions_disabled(c):
        if util.DRY_RUN:
            print("[gnome-enable] WARNING: disable-user-extensions = true — would fix")
        else:
            print("[gnome-enable] user extensions globally disabled — enabling...")
            c.run("gsettings set org.gnome.shell disable-user-extensions false", warn=True)

    installed = _installed_uuids(c)
    enabled = _enabled_uuids(c)

    for name, cfg in pkgs.items():
        uuid = cfg.get("uuid", "")
        if not uuid:
            print(f"[{name}] no uuid — skipping")
            continue

        if uuid not in installed:
            print(f"[{name}] not installed — run inv gnome.extensions to install")
            continue

        for conflict_uuid in CONFLICTS.get(uuid, []):
            if conflict_uuid in enabled:
                if util.DRY_RUN:
                    print(f"[{name}] (dry) would disable conflicting extension: {conflict_uuid}")
                else:
                    print(f"[{name}] disabling conflicting extension: {conflict_uuid}")
                    c.run(f"gnome-extensions disable {conflict_uuid}", warn=True)

        if uuid not in enabled:
            if util.DRY_RUN:
                print(f"[{name}] (dry) would enable {uuid}")
            else:
                c.run(f"gnome-extensions enable {uuid}", warn=True)
                print(f"[{name}] enabled")
        else:
            print(f"[{name}] already enabled")

    if not util.DRY_RUN:
        print("[gnome-enable] complete — if extensions are still inactive, try logout/login")


@task
def configure(c):
    """Apply dconf settings for all enabled extensions — re-run without reinstalling."""
    pkgs = util.packages_by_method(util.PackageMethod.GNOME_EXTENSION)
    any_config = False
    for name, cfg in pkgs.items():
        if not cfg.get("dconf"):
            continue
        any_config = True
        if util.DRY_RUN:
            for key, value in cfg["dconf"].items():
                result = c.run(f"dconf read {key}", hide=True, warn=True)
                current = (result.stdout or "").strip()
                state = "ok" if current == value else f"MISSING (would set: {value})"
                print(f"[{name}] dconf {key.split('/')[-1]}: {state}")
        else:
            _apply_dconf(c, name, cfg)
    if not any_config:
        print("[gnome-configure] no dconf settings declared")
    elif not util.DRY_RUN:
        print("[gnome-configure] done")


@task
def status(c):
    """Show GNOME extension diagnostic: dconf flags, active state, and setup.toml alignment."""
    shell_ver = c.run("gnome-shell --version", hide=True, warn=True).stdout.strip()
    print(f"GNOME Shell: {shell_ver}")

    disabled_globally = _user_extensions_disabled(c)
    flag = "true  ← WARNING: all user extensions suppressed" if disabled_globally else "false  ✓"
    print(f"disable-user-extensions: {flag}")

    active = _enabled_uuids(c)
    all_configs = {
        name: cfg
        for name, cfg in util.load_config()["packages"].items()
        if cfg.get("method") == util.PackageMethod.GNOME_EXTENSION
    }

    print("\nPULSE extensions (all declared):")
    for name, cfg in all_configs.items():
        uuid = cfg.get("uuid", "")
        want = cfg.get("enabled", True)
        installed = ((_USER_EXT_DIR / uuid).is_dir()) if uuid else False
        is_active = uuid in active

        if not want:
            state = "skip (disabled in setup.toml)"
        elif disabled_globally:
            state = "blocked (disable-user-extensions=true)"
        elif is_active:
            state = "✓ active"
        elif installed:
            state = "installed, NOT active — logout/login needed?"
        else:
            state = "MISSING — run inv gnome.extensions"

        marker = "[ ]" if not want else "[x]"
        print(f"  {marker} {name}: {state}")

    conflicts_active = [uuid for uuids in CONFLICTS.values() for uuid in uuids if uuid in active]
    if conflicts_active:
        print(f"\nActive conflicts: {', '.join(conflicts_active)}")
        print("  → run inv gnome.extensions to resolve")


@task
def clean(c):
    """Remove user extensions not enabled in setup.toml (system/apt extensions are untouched)."""
    pkgs = util.packages_by_method(util.PackageMethod.GNOME_EXTENSION)
    keep = {cfg["uuid"] for cfg in pkgs.values() if cfg.get("uuid")}

    if not _USER_EXT_DIR.exists():
        print("[gnome-clean] ~/.local/share/gnome-shell/extensions not found — nothing to do")
        return

    removed = 0
    for path in sorted(_USER_EXT_DIR.iterdir()):
        if not path.is_dir():
            continue
        uuid = path.name
        if uuid in keep:
            print(f"[gnome-clean] keep    {uuid}")
        else:
            tag = "(dry) " if util.DRY_RUN else ""
            print(f"[gnome-clean] {tag}remove  {uuid}")
            if not util.DRY_RUN:
                shutil.rmtree(path)
                removed += 1

    if removed:
        print(f"[gnome-clean] removed {removed} extension(s) — logout/login to apply")
    elif not util.DRY_RUN:
        print("[gnome-clean] nothing to remove")


@task
def update(c):
    """Update all gext-managed GNOME Shell extensions."""
    if not util.command_exists("gext"):
        print("[gnome-update] gext not found — run 'inv python.tools' first")
        return
    if util.DRY_RUN:
        print("[gnome-update] dry run — would run: gext update")
        return
    c.run("gext update", warn=True)
    print("[gnome-update] done — logout/login to activate updated extensions")
