from pathlib import Path

from invoke import Context, task

from . import deploy, util

# Ubuntu system keys that legitimately live in trusted.gpg.d — everything else is old-style.
_SYSTEM_TRUSTED_D = frozenset(
    {
        "ubuntu-keyring-2012-cdimage.gpg",
        "ubuntu-keyring-2018-archive.gpg",
    }
)

_KEYRINGS_DIRS = [Path("/etc/apt/keyrings"), Path("/usr/share/keyrings")]

_APT_CONF = Path("/etc/apt/apt.conf.d/99-pulse")
_APT_CONF_CONTENT = 'DPkg::Progress-Fancy "false";\n'


# ---------------------------------------------------------------------------
# apt configuration
# ---------------------------------------------------------------------------


@task
def configure(c: Context):
    """Write /etc/apt/apt.conf.d/99-pulse: disable dpkg progress bars."""
    util.require_apt()
    if util.DRY_RUN:
        ok = util.sudo_read(c, _APT_CONF) == _APT_CONF_CONTENT
        print(f"[apt.configure] {util.ok_label(ok)}")
        return
    current = util.sudo_read(c, _APT_CONF)
    if current == _APT_CONF_CONTENT:
        print("[apt.configure] already configured")
        return
    _APT_CONF.parent.mkdir(parents=True, exist_ok=True)
    util.sudo_write(c, _APT_CONF, _APT_CONF_CONTENT)
    print(f"[apt.configure] written → {_APT_CONF}")


# ---------------------------------------------------------------------------
# apt (base packages)
# ---------------------------------------------------------------------------


def _install_apt_package(c: Context, name: str, cfg: util.PackageConfig) -> None:
    packages = util.apt_packages(name, cfg)
    if util.DRY_RUN:
        parts = [f"{p}:{util.ok_label(util.apt_installed(p))}" for p in packages]
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
    deploy.apply_config_files(name, cfg)


@task
def install_base(c: Context):
    """Install base apt packages from config."""
    util.require_apt()
    pkgs = util.packages_by_method(util.PackageMethod.APT)
    if util.DRY_RUN:
        for name, cfg in pkgs.items():
            _install_apt_package(c, name, cfg)
        return
    needs_update = any(not util.apt_installed(p) for name, cfg in pkgs.items() for p in util.apt_packages(name, cfg))
    if needs_update:
        c.run(f"{util.SUDO} apt update")
    for name, cfg in pkgs.items():
        _install_apt_package(c, name, cfg)


# ---------------------------------------------------------------------------
# apt-repo (external repos)
# ---------------------------------------------------------------------------


def _register_repo(c: Context, name: str, cfg: util.PackageConfig, codename: str) -> bool:
    """Write GPG key and sources entry. Returns True if apt update is needed."""
    if "gpg_path" not in cfg or "gpg_url" not in cfg or "sources_path" not in cfg or "sources_entry" not in cfg:
        raise util.missing_fields(name, "gpg_path", "gpg_url", "sources_path", "sources_entry")
    gpg = Path(cfg["gpg_path"])
    sources = Path(cfg["sources_path"])
    needs_update = False

    if not gpg.exists():
        result = c.run(
            f"curl -fsSL {cfg['gpg_url']} | {util.SUDO} gpg --dearmor -o {gpg}",
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


def _install_repo_packages(c: Context, name: str, cfg: util.PackageConfig) -> None:
    missing = [p for p in util.apt_packages(name, cfg) if not util.apt_installed(p)]
    if missing:
        print(f"[{name}] installing: {', '.join(missing)}")
        result = c.run(f"{util.SUDO} apt install -y {' '.join(missing)}", warn=True)
        if not result.ok:
            print(f"[{name}] WARNING: apt install failed — check repo or run manually")
    else:
        print(f"[{name}] already installed")
    if post_install := cfg.get("post_install"):
        c.run(post_install, warn=True)


def _status_repo(name: str, cfg: util.PackageConfig) -> None:
    if "gpg_path" not in cfg or "sources_path" not in cfg:
        raise util.missing_fields(name, "gpg_path", "sources_path")
    gpg = Path(cfg["gpg_path"])
    sources = Path(cfg["sources_path"])
    repo_ok = gpg.exists() and sources.exists()
    packages = util.apt_packages(name, cfg)
    pkg_parts = [f"{p}:{util.ok_label(util.apt_installed(p))}" for p in packages]
    print(f"[{name}] repo:{util.ok_label(repo_ok)}  {',  '.join(pkg_parts)}")


@task
def install_repos(c: Context):
    """Set up external apt repos and install their packages."""
    util.require_apt()
    pkgs = util.packages_by_method(util.PackageMethod.APT_REPO)

    if util.DRY_RUN:
        for name, cfg in pkgs.items():
            _status_repo(name, cfg)
        return

    # lsb_release (package lsb-release) and gpg (package gnupg) aren't guaranteed present on a
    # fresh/minimal install, and this runs before apt.install_base — which is where setup.toml's other
    # apt packages get installed — ever gets a chance to. Not declared as [packages.*] entries for
    # that reason: they wouldn't install in time to help here anyway, so they're ensured directly.
    # gnupg matters because _register_repo() below pipes each repo's signing key through
    # `gpg --dearmor`; without it that fails silently (caught by warn=True) and apt falls back to
    # whatever stale version, if any, ships in Ubuntu's own repos. `apt update` first since a
    # minimal/container base image (or one that's had /var/lib/apt/lists cleaned in an earlier
    # Docker layer) may have no package index at all yet — `apt install` would 404 on "Unable to
    # locate package" otherwise.
    missing_prereqs = [
        pkg for pkg, cmd in [("lsb-release", "lsb_release"), ("gnupg", "gpg")] if not util.command_exists(cmd)
    ]
    if missing_prereqs:
        c.run(f"{util.SUDO} apt update")
        c.run(f"{util.SUDO} apt install -y {' '.join(missing_prereqs)}")
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
# deb-github / deb-url
# ---------------------------------------------------------------------------


def _resolve_version(c: Context, name: str, cfg: util.PackageConfig) -> str | None:
    """Return the version/tag string for a deb-github package, or None on failure."""
    if "tag" in cfg:
        return cfg["tag"]
    if "repo" not in cfg:
        raise util.missing_fields(name, "repo")
    result = c.run(
        f"curl -fsSL https://api.github.com/repos/{cfg['repo']}/releases/latest"
        " | grep '\"tag_name\"'"
        ' | sed -E \'s/.*"v?([^"]+)".*/\\1/\'',
        hide=True,
        warn=True,
    )
    version = result.stdout.strip()
    if not version:
        print(f"[{name}] WARNING: could not fetch latest release — skipping")
        return None
    return version


def _dpkg_install(c: Context, name: str, cfg: util.PackageConfig, version: str) -> bool:
    """Download and dpkg-install a deb-github asset. Returns True on success.

    Some projects (e.g. flameshot's CI artifacts) publish the .deb wrapped in a .zip rather than
    as a bare asset — unzip to a scratch dir and install whatever .deb is inside.
    """
    if "repo" not in cfg or "asset" not in cfg:
        raise util.missing_fields(name, "repo", "asset")
    tag_prefix = cfg.get("tag_prefix", "v")
    asset = cfg["asset"].format(version=version)
    downloaded = f"/tmp/{asset}"
    result = c.run(
        f"curl -fsSL https://github.com/{cfg['repo']}/releases/download/{tag_prefix}{version}/{asset} -o {downloaded}",
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
        c.run(f"{util.SUDO} dpkg -i {downloaded}", warn=True)
        c.run(f"rm -f {downloaded}")
    return True


def _dpkg_install_and_report(
    c: Context, name: str, cfg: util.PackageConfig, version: str, verb: str, past_verb: str
) -> None:
    """Download+dpkg-install `version` and print a "<verb>..."/"<past_verb>" pair around it —
    shared by the first-install path (installing/installed) and upgrade_debs() (upgrading/upgraded)."""
    tag_prefix = cfg.get("tag_prefix", "v")
    print(f"[{name}] {verb} {tag_prefix}{version}...")
    if _dpkg_install(c, name, cfg, version):
        print(f"[{name}] {past_verb} {tag_prefix}{version}")


def _install_github_deb(c: Context, name: str, cfg: util.PackageConfig) -> None:
    if util.DRY_RUN:
        ok = util.command_exists(cfg.get("check_cmd", name))
        print(f"[{name}] {util.ok_label(ok)}")
        return

    if not util.command_exists(cfg.get("check_cmd", name)):
        version = _resolve_version(c, name, cfg)
        if version is None:
            return
        _dpkg_install_and_report(c, name, cfg, version, "installing", "installed")
    else:
        print(f"[{name}] already installed")

    deploy.apply_config_files(name, cfg)


def _install_deb_url(c: Context, name: str, cfg: util.PackageConfig) -> None:
    if util.DRY_RUN:
        ok = util.command_exists(cfg.get("check_cmd", name))
        print(f"[{name}] {util.ok_label(ok)}")
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
        if "version_cmd" not in cfg:
            raise util.missing_fields(name, "version_cmd")
        version = c.run(cfg["version_cmd"], hide=True).stdout.strip()
        url = url.format(version=version)
    print(f"[{name}] installing...")
    deb = f"/tmp/{name}.deb"
    c.run(f'curl -fsSL "{url}" -o {deb}')
    c.run(f"{util.SUDO} dpkg -i {deb} && rm {deb}")
    print(f"[{name}] installed")


def _cache_size_report(c: Context, label: str) -> None:
    result = c.run("du -sh /var/cache/apt/archives", hide=True, warn=True)
    size = result.stdout.split()[0] if result.ok and result.stdout.split() else "0"
    print(f"[{label}] archive cache: {size}")


@task
def clean_cache(c: Context):
    """Remove apt's downloaded .deb cache for packages no longer available at their cached
    version (`apt-get autoclean`) — conservative, keeps .debs for currently-installed versions
    cached for reinstall. Opt-in, not part of `inv setup`/`apt.install-base` — see `inv clean.caches`.
    For a full wipe of /var/cache/apt/archives instead, see `apt.clean-cache-full`.
    """
    util.require_apt()
    if util.DRY_RUN:
        _cache_size_report(c, "apt.clean-cache")
        return
    c.run(f"{util.SUDO} apt-get autoclean")
    print("[apt.clean-cache] obsolete entries removed from /var/cache/apt/archives")


@task
def clean_cache_full(c: Context):
    """Remove apt's entire downloaded .deb cache (/var/cache/apt/archives), including .debs for
    currently-installed packages — apt just re-downloads them if reinstalled. Opt-in, not part of
    `inv setup`/`apt.install-base` — see `inv clean.all-full`.
    """
    util.require_apt()
    if util.DRY_RUN:
        _cache_size_report(c, "apt.clean-cache-full")
        return
    c.run(f"{util.SUDO} apt-get clean")
    print("[apt.clean-cache-full] /var/cache/apt/archives cleared")


@task
def install_debs(c: Context):
    """Install packages sourced from GitHub releases or direct deb URLs."""
    util.require_apt()
    for name, cfg in util.packages_by_method(util.PackageMethod.DEB_GITHUB).items():
        _install_github_deb(c, name, cfg)
    for name, cfg in util.packages_by_method(util.PackageMethod.DEB_URL).items():
        _install_deb_url(c, name, cfg)

    if not util.DRY_RUN:
        # Both loops above install via plain `dpkg -i`, which doesn't resolve dependencies — a
        # .deb needing a package not already on the system (e.g. google-chrome-stable needing
        # fonts-liberation/libasound2/libnspr4/libnss3, unremarkable on an aged daily-driver
        # machine but missing on a fresh install) leaves dpkg with that package "unconfigured"
        # instead of actually installed. `apt-get install -f` resolves and installs whatever's
        # currently missing for any package dpkg left in that state; cheap no-op if nothing broke.
        c.run(f"{util.SUDO} apt-get install -f -y", warn=True)


@task
def uninstall(c: Context, name: str):
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
def upgrade_debs(c: Context):
    """Upgrade all deb-github packages to their latest versions (re-downloads and reinstalls each)."""
    for name, cfg in util.packages_by_method(util.PackageMethod.DEB_GITHUB).items():
        version = _resolve_version(c, name, cfg)
        if version is None:
            continue
        _dpkg_install_and_report(c, name, cfg, version, "upgrading to", "upgraded to")


@task
def refresh_keys(c: Context):
    """Re-download GPG keys for all enabled apt-repo sources."""
    for name, cfg in util.packages_by_method(util.PackageMethod.APT_REPO).items():
        if "gpg_path" not in cfg or "gpg_url" not in cfg:
            raise util.missing_fields(name, "gpg_path", "gpg_url")
        gpg = Path(cfg["gpg_path"])
        c.run(f"curl -fsSL {cfg['gpg_url']} | {util.SUDO} gpg --dearmor -o {gpg}")
        print(f"[{name}] key refreshed → {gpg}")


def _report_stale_backup(c: Context, f: Path, label: str) -> None:
    if util.DRY_RUN:
        print(f"[apt/keys] {label}/{f.name}: stale backup")
    else:
        c.run(f"{util.SUDO} rm {f}", hide=True)
        print(f"[apt/keys] {label}/{f.name}: removed stale backup")


def _audit_trusted_gpg(c: Context) -> bool:
    """trusted.gpg must be empty; any key here implicitly trusts ALL repos (no signed-by
    scoping). Returns True if clean."""
    trusted = Path("/etc/apt/trusted.gpg")
    if not (trusted.exists() and trusted.stat().st_size > 0):
        print("[apt/keys] trusted.gpg: empty ✓")
        return True
    result = c.run(
        f"gpg --no-default-keyring --keyring {trusted} --list-keys 2>/dev/null",
        hide=True,
        warn=True,
    )
    count = len([line for line in result.stdout.splitlines() if line.startswith("pub ")])
    if util.DRY_RUN:
        print(f"[apt/keys] trusted.gpg: {count} key(s) present — should be empty (trusts all repos)")
    else:
        c.run(f"{util.SUDO} truncate -s 0 {trusted}", hide=True)
        print(f"[apt/keys] trusted.gpg: cleared {count} legacy key(s)")
    return False


def _audit_trusted_gpg_d(c: Context) -> bool:
    """Ubuntu system keys are expected; anything else is old-style (not signed-by). Returns True
    if clean."""
    trusted_d = Path("/etc/apt/trusted.gpg.d")
    if not trusted_d.exists():
        return True
    clean = True
    for f in sorted(trusted_d.iterdir()):
        if f.name.endswith("~"):
            clean = False
            _report_stale_backup(c, f, "trusted.gpg.d")
        elif f.name not in _SYSTEM_TRUSTED_D:
            clean = False
            print(f"[apt/keys] trusted.gpg.d/{f.name}: old-style key (not signed-by) — check if repo still active")
    return clean


def _audit_keyrings(c: Context) -> bool:
    """Check for ~ backup files (safe to remove) in the modern keyrings dirs. Returns True if clean."""
    clean = True
    for keyrings_dir in _KEYRINGS_DIRS:
        if not keyrings_dir.exists():
            continue
        for f in sorted(keyrings_dir.iterdir()):
            if f.name.endswith("~"):
                clean = False
                _report_stale_backup(c, f, keyrings_dir.name)
    return clean


@task
def audit_keys(c: Context):
    """Audit apt key hygiene — report legacy keys, old-style trust, stale backups.

    Safe fixes (clear trusted.gpg, remove ~ backups) run automatically in live mode.
    Old-style trusted.gpg.d entries are reported only — they need manual review.
    """
    trusted_gpg_clean = _audit_trusted_gpg(c)
    trusted_gpg_d_clean = _audit_trusted_gpg_d(c)
    keyrings_clean = _audit_keyrings(c)

    if trusted_gpg_clean and trusted_gpg_d_clean and keyrings_clean:
        print("[apt/keys] all key locations clean ✓")
