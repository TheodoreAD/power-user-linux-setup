import tempfile
from pathlib import Path

from invoke import task

from . import util

# Ubuntu system keys that legitimately live in trusted.gpg.d — everything else is old-style.
_SYSTEM_TRUSTED_D = frozenset({
    "ubuntu-keyring-2012-cdimage.gpg",
    "ubuntu-keyring-2018-archive.gpg",
})

_KEYRINGS_DIRS = [Path("/etc/apt/keyrings"), Path("/usr/share/keyrings")]

_APT_CONF = Path("/etc/apt/apt.conf.d/99-pulse")
_APT_CONF_CONTENT = 'DPkg::Progress-Fancy "false";\n'


# ---------------------------------------------------------------------------
# apt configuration
# ---------------------------------------------------------------------------

@task
def configure(c):
    """Write /etc/apt/apt.conf.d/99-pulse: disable dpkg progress bars."""
    util.require_apt()
    if util.DRY_RUN:
        ok = _APT_CONF.exists() and c.run(f"{util.SUDO} cat {_APT_CONF}", hide=True, warn=True).stdout == _APT_CONF_CONTENT
        print(f"[apt.configure] {'ok' if ok else 'MISSING'}")
        return
    current = c.run(f"{util.SUDO} cat {_APT_CONF}", hide=True, warn=True).stdout if _APT_CONF.exists() else ""
    if current == _APT_CONF_CONTENT:
        print("[apt.configure] already configured")
        return
    _APT_CONF.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False) as f:
        f.write(_APT_CONF_CONTENT)
        tmp = f.name
    c.run(f"{util.SUDO} cp {tmp} {_APT_CONF} && rm {tmp}")
    print(f"[apt.configure] written → {_APT_CONF}")


# ---------------------------------------------------------------------------
# apt (base packages)
# ---------------------------------------------------------------------------

def _install_apt(c, name: str, cfg: dict) -> None:
    packages = util.apt_packages(name, cfg)
    if util.DRY_RUN:
        parts = [f"{p}:{'ok' if util.apt_installed(p) else 'MISSING'}" for p in packages]
        print(f"[{name}] {',  '.join(parts)}")
        return
    missing = [p for p in packages if not util.apt_installed(p)]
    if missing:
        print(f"[{name}] installing: {', '.join(missing)}")
        c.run(f"{util.SUDO} apt install -y {' '.join(missing)}")
    else:
        print(f"[{name}] already installed")
    for sym in cfg.get("symlinks", []):
        if util.ensure_symlink(sym["src"], sym["dst"]):
            print(f"[{name}] symlink: {sym['dst']} -> {sym['src']}")
    _apply_config_files(name, cfg)


@task
def base(c):
    """Install base apt packages from config."""
    util.require_apt()
    pkgs = util.packages_by_method("apt")
    if util.DRY_RUN:
        for name, cfg in pkgs.items():
            _install_apt(c, name, cfg)
        return
    needs_update = any(
        not util.apt_installed(p)
        for name, cfg in pkgs.items()
        for p in util.apt_packages(name, cfg)
    )
    if needs_update:
        c.run(f"{util.SUDO} apt update")
    for name, cfg in pkgs.items():
        _install_apt(c, name, cfg)


# ---------------------------------------------------------------------------
# apt-repo (external repos)
# ---------------------------------------------------------------------------

def _register_repo(c, name: str, cfg: dict, codename: str) -> bool:
    """Write GPG key and sources entry. Returns True if apt update is needed."""
    gpg = Path(cfg["gpg_path"])
    sources = Path(cfg["sources_path"])
    needs_update = False

    if not gpg.exists():
        result = c.run(
            f'curl -fsSL {cfg["gpg_url"]} | {util.SUDO} gpg --dearmor -o {gpg}',
            warn=True,
        )
        if not result.ok:
            print(f"[{name}] WARNING: GPG key fetch failed — skipping repo")
            return False
        needs_update = True

    entry = cfg["sources_entry"].format(gpg_path=gpg, codename=codename)
    if not sources.exists() or sources.read_text().strip() != entry.strip():
        result = c.run(
            f"printf '%s\\n' {entry!r} | {util.SUDO} tee {sources}",
            warn=True,
            hide="stdout",
        )
        if not result.ok:
            print(f"[{name}] WARNING: sources file write failed — skipping")
            return False
        needs_update = True

    return needs_update


def _install_repo_packages(c, name: str, cfg: dict) -> None:
    missing = [p for p in util.apt_packages(name, cfg) if not util.apt_installed(p)]
    if missing:
        print(f"[{name}] installing: {', '.join(missing)}")
        result = c.run(f"{util.SUDO} apt install -y {' '.join(missing)}", warn=True)
        if not result.ok:
            print(f"[{name}] WARNING: apt install failed — check repo or run manually")
    else:
        print(f"[{name}] already installed")
    for cmd in cfg.get("post_install", []):
        c.run(cmd, warn=True)


def _status_repo(name: str, cfg: dict) -> None:
    gpg = Path(cfg["gpg_path"])
    sources = Path(cfg["sources_path"])
    repo_ok = gpg.exists() and sources.exists()
    packages = util.apt_packages(name, cfg)
    pkg_parts = [f"{p}:{'ok' if util.apt_installed(p) else 'MISSING'}" for p in packages]
    print(f"[{name}] repo:{'ok' if repo_ok else 'MISSING'}  {',  '.join(pkg_parts)}")


@task
def repos(c):
    """Set up external apt repos and install their packages."""
    util.require_apt()
    pkgs = util.packages_by_method("apt-repo")

    if util.DRY_RUN:
        for name, cfg in pkgs.items():
            _status_repo(name, cfg)
        return

    codename = c.run("lsb_release -cs", hide=True).stdout.strip()

    # Phase 1: register all repos, then one apt update.
    needs_update = False
    for name, cfg in pkgs.items():
        needs_update |= _register_repo(c, name, cfg, codename)
    if needs_update:
        c.run(f"{util.SUDO} apt update", warn=True)

    # Phase 2: install packages from all repos.
    for name, cfg in pkgs.items():
        _install_repo_packages(c, name, cfg)


# ---------------------------------------------------------------------------
# Config file deployment (shared across methods)
# ---------------------------------------------------------------------------

def _apply_config_files(name: str, cfg: dict) -> None:
    """Copy config_files entries to their destinations, skipping any that already exist."""
    for mapping in cfg.get("config_files", []):
        src = Path(mapping["src"])
        dst = Path(mapping["dst"]).expanduser()
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
            print(f"[{name}] config: {dst}")


# ---------------------------------------------------------------------------
# deb-github / deb-url
# ---------------------------------------------------------------------------

def _resolve_version(c, name: str, cfg: dict) -> str | None:
    """Return the version/tag string for a deb-github package, or None on failure."""
    if "tag" in cfg:
        return cfg["tag"]
    result = c.run(
        f'curl -fsSL https://api.github.com/repos/{cfg["repo"]}/releases/latest'
        ' | grep \'"tag_name"\''
        ' | sed -E \'s/.*"v?([^"]+)".*/\\1/\'',
        hide=True,
        warn=True,
    )
    version = result.stdout.strip()
    if not version:
        print(f"[{name}] WARNING: could not fetch latest release — skipping")
        return None
    return version


def _dpkg_install(c, name: str, cfg: dict, version: str) -> bool:
    """Download and dpkg-install a deb-github asset. Returns True on success.

    Some projects (e.g. flameshot's CI artifacts) publish the .deb wrapped in a .zip rather than
    as a bare asset — unzip to a scratch dir and install whatever .deb is inside.
    """
    tag_prefix = cfg.get("tag_prefix", "v")
    asset = cfg["asset"].format(version=version)
    downloaded = f"/tmp/{asset}"
    result = c.run(
        f'curl -fsSL https://github.com/{cfg["repo"]}/releases/download/{tag_prefix}{version}/{asset} -o {downloaded}',
        warn=True,
    )
    if not result.ok:
        print(f"[{name}] WARNING: download failed — skipping")
        return False

    if downloaded.endswith(".zip"):
        extract_dir = f"/tmp/{name}-deb-extract"
        c.run(f"rm -rf {extract_dir} && mkdir -p {extract_dir}")
        c.run(f"unzip -oq {downloaded} -d {extract_dir}")
        deb_result = c.run(f"find {extract_dir} -name '*.deb' | head -1", hide=True)
        deb = deb_result.stdout.strip()
        if not deb:
            print(f"[{name}] WARNING: no .deb found inside {asset} — skipping")
            c.run(f"rm -rf {downloaded} {extract_dir}", warn=True)
            return False
        c.run(f"{util.SUDO} dpkg -i {deb}", warn=True)
        c.run(f"rm -rf {downloaded} {extract_dir}", warn=True)
    else:
        c.run(f"{util.SUDO} dpkg -i {downloaded} && rm {downloaded}", warn=True)
    return True


def _install_github_deb(c, name: str, cfg: dict) -> None:
    if util.DRY_RUN:
        ok = util.command_exists(cfg.get("check_cmd", name))
        print(f"[{name}] {'ok' if ok else 'MISSING'}")
        return

    if not util.command_exists(cfg.get("check_cmd", name)):
        version = _resolve_version(c, name, cfg)
        if version is None:
            return
        tag_prefix = cfg.get("tag_prefix", "v")
        print(f"[{name}] installing {tag_prefix}{version}...")
        if _dpkg_install(c, name, cfg, version):
            print(f"[{name}] installed {tag_prefix}{version}")
    else:
        print(f"[{name}] already installed")

    _apply_config_files(name, cfg)


def _install_deb_url(c, name: str, cfg: dict) -> None:
    if util.DRY_RUN:
        ok = util.command_exists(cfg.get("check_cmd", name))
        print(f"[{name}] {'ok' if ok else 'MISSING'}")
        return
    if util.command_exists(cfg.get("check_cmd", name)):
        print(f"[{name}] already installed")
        return
    url = cfg.get("url", "")
    if not url:
        page = cfg.get("download_page", "")
        if not page:
            print(f"[{name}] skipped — no url or download_page set")
            return
        print(f"\n[{name}] Manual download required.")
        print(f"  Download the .deb from: {page}")
        path = input("  Path to downloaded .deb (or Enter to skip): ").strip()
        if not path:
            print(f"[{name}] skipped")
            return
        c.run(f"{util.SUDO} dpkg -i {path}")
        print(f"[{name}] installed")
        return
    if "{version}" in url:
        version = c.run(cfg["version_cmd"], hide=True).stdout.strip()
        url = url.format(version=version)
    print(f"[{name}] installing...")
    deb = f"/tmp/{name}.deb"
    c.run(f'curl -fsSL "{url}" -o {deb}')
    c.run(f"{util.SUDO} dpkg -i {deb} && rm {deb}")
    print(f"[{name}] installed")


@task
def deb(c):
    """Install packages sourced from GitHub releases or direct deb URLs."""
    util.require_apt()
    for name, cfg in util.packages_by_method("deb-github").items():
        _install_github_deb(c, name, cfg)
    for name, cfg in util.packages_by_method("deb-url").items():
        _install_deb_url(c, name, cfg)


@task
def uninstall(c, name):
    """Purge the apt packages declared for a setup.toml section (any method), e.g. inv apt.uninstall citrix-workspace.

    Also removes any `cleanup_paths` declared on the section — leftover files/dirs that aren't
    dpkg-owned (vendor installers under /opt, stale logs, orphaned dconf locks, etc.) and so
    survive a plain `apt purge`.
    """
    cfg = util.load_config()["packages"].get(name)
    if not cfg:
        print(f"[apt.uninstall] no such section: {name}")
        return
    packages = util.apt_packages(name, cfg)
    installed = [p for p in packages if util.apt_installed(p)]
    cleanup_paths = [Path(p).expanduser() for p in cfg.get("cleanup_paths", [])]

    if util.DRY_RUN:
        print(f"[{name}] would purge: {', '.join(installed)}" if installed else f"[{name}] not installed")
        for path in cleanup_paths:
            # lexists / is_symlink: a broken symlink still needs removing but path.exists() follows
            # the link and reports False for it, which would silently skip it here.
            present = path.exists() or path.is_symlink()
            print(f"[{name}] {'would remove' if present else 'clean'}: {path}")
        return

    if installed:
        c.run(f"{util.SUDO} apt purge -y {' '.join(installed)}")
        c.run(f"{util.SUDO} apt autoremove -y", warn=True)
        print(f"[{name}] purged: {', '.join(installed)}")
    else:
        print(f"[{name}] not installed")

    dconf_touched = False
    for path in cleanup_paths:
        if not (path.exists() or path.is_symlink()):
            continue
        c.run(f"{util.SUDO} rm -rf {path}")
        print(f"[{name}] removed: {path}")
        dconf_touched |= path.is_relative_to("/etc/dconf")
    if dconf_touched:
        c.run(f"{util.SUDO} dconf update", warn=True)
        print(f"[{name}] dconf database recompiled")


@task
def upgrade_debs(c):
    """Upgrade all deb-github packages to their latest versions (re-downloads and reinstalls each)."""
    for name, cfg in util.packages_by_method("deb-github").items():
        version = _resolve_version(c, name, cfg)
        if version is None:
            continue
        tag_prefix = cfg.get("tag_prefix", "v")
        print(f"[{name}] upgrading to {tag_prefix}{version}...")
        if _dpkg_install(c, name, cfg, version):
            print(f"[{name}] upgraded to {tag_prefix}{version}")


@task
def refresh_keys(c):
    """Re-download GPG keys for all enabled apt-repo sources."""
    for name, cfg in util.packages_by_method("apt-repo").items():
        gpg = Path(cfg["gpg_path"])
        c.run(f'curl -fsSL {cfg["gpg_url"]} | {util.SUDO} gpg --dearmor -o {gpg}')
        print(f"[{name}] key refreshed → {gpg}")


@task
def audit_keys(c):
    """Audit apt key hygiene — report legacy keys, old-style trust, stale backups.

    Safe fixes (clear trusted.gpg, remove ~ backups) run automatically in live mode.
    Old-style trusted.gpg.d entries are reported only — they need manual review.
    """
    clean = True

    # trusted.gpg — must be empty; any key here implicitly trusts ALL repos (no signed-by scoping)
    trusted = Path("/etc/apt/trusted.gpg")
    if trusted.exists() and trusted.stat().st_size > 0:
        result = c.run(
            f"gpg --no-default-keyring --keyring {trusted} --list-keys 2>/dev/null",
            hide=True, warn=True,
        )
        count = len([l for l in result.stdout.splitlines() if l.startswith("pub ")])
        clean = False
        if util.DRY_RUN:
            print(f"[apt/keys] trusted.gpg: {count} key(s) present — should be empty (trusts all repos)")
        else:
            c.run(f"{util.SUDO} truncate -s 0 {trusted}", hide=True)
            print(f"[apt/keys] trusted.gpg: cleared {count} legacy key(s)")
    else:
        print("[apt/keys] trusted.gpg: empty ✓")

    # trusted.gpg.d — Ubuntu system keys are expected; anything else is old-style (not signed-by)
    trusted_d = Path("/etc/apt/trusted.gpg.d")
    if trusted_d.exists():
        for f in sorted(trusted_d.iterdir()):
            if f.name.endswith("~"):
                clean = False
                if util.DRY_RUN:
                    print(f"[apt/keys] trusted.gpg.d/{f.name}: stale backup")
                else:
                    c.run(f"{util.SUDO} rm {f}", hide=True)
                    print(f"[apt/keys] trusted.gpg.d/{f.name}: removed stale backup")
            elif f.name not in _SYSTEM_TRUSTED_D:
                clean = False
                print(f"[apt/keys] trusted.gpg.d/{f.name}: old-style key (not signed-by) — check if repo still active")

    # keyrings dirs — check for ~ backup files (safe to remove)
    for keyrings_dir in _KEYRINGS_DIRS:
        if not keyrings_dir.exists():
            continue
        for f in sorted(keyrings_dir.iterdir()):
            if f.name.endswith("~"):
                clean = False
                if util.DRY_RUN:
                    print(f"[apt/keys] {keyrings_dir.name}/{f.name}: stale backup")
                else:
                    c.run(f"{util.SUDO} rm {f}", hide=True)
                    print(f"[apt/keys] {keyrings_dir.name}/{f.name}: removed stale backup")

    if clean:
        print("[apt/keys] all key locations clean ✓")
