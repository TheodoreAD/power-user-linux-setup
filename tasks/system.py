import re
from pathlib import Path

from invoke import task

from . import util

_REPO_ROOT = Path(__file__).parent.parent
_SYSCTL_CONF = Path("/etc/sysctl.conf")
_APPARMOR_DIR = Path("/etc/apparmor.d")
_INITRAMFS_CONF = Path("/etc/initramfs-tools/initramfs.conf")
_JOURNALD_CONF_DIR = Path("/etc/systemd/journald.conf.d")
_JOURNALD_SIZE_CONF = _JOURNALD_CONF_DIR / "size.conf"
_RESOLVED_CONF_DIR = Path("/etc/systemd/resolved.conf.d")
_RESOLVED_CONF = _RESOLVED_CONF_DIR / "pulse-dns.conf"
_CURLRC = Path.home() / ".config" / "curlrc"

_IPV6_KEYS = [
    "net.ipv6.conf.all.disable_ipv6",
    "net.ipv6.conf.default.disable_ipv6",
    "net.ipv6.conf.lo.disable_ipv6",
]


@task
def install_apparmor_profiles(c):
    """Install AppArmor profiles declared in setup.toml with method = 'apparmor-profile'."""
    profiles = util.packages_by_method(util.PackageMethod.APPARMOR_PROFILE)
    if not profiles:
        if util.DRY_RUN:
            print("[apparmor] no profiles declared")
        return
    for name, cfg in profiles.items():
        path = Path(cfg["profile"])
        content = cfg["content"].strip() + "\n"
        existing = util.sudo_read(c, path)
        if util.DRY_RUN:
            print(f"[apparmor] {name}: {util.ok_label(existing == content)}")
            continue
        if existing == content:
            print(f"[apparmor] {name}: already installed")
            continue
        util.sudo_write(c, path, content)
        c.run(f"{util.SUDO} apparmor_parser -r {path}", warn=True)
        print(f"[apparmor] {name}: installed and loaded")


@task
def write_curlrc(c):
    """Write ~/.config/curlrc: silent, show errors, follow redirects. Idempotent."""
    content = "--silent\n--show-error\n--location"
    if util.DRY_RUN:
        text = _CURLRC.read_text() if _CURLRC.exists() else ""
        _, status = util.ensure_block_text(text, "curlrc", content)
        print(f"[curlrc] {util.ok_label(status == util.BlockStatus.OK)}")
        return
    result = util.ensure_block(_CURLRC, "curlrc", content)
    if result != util.BlockStatus.OK:
        print(f"[curlrc] {result.value}")
    else:
        print("[curlrc] already configured — nothing to do")


@task
def set_locale(c, lang="en_US.UTF-8"):
    """Set system locale via localectl (default: en_US.UTF-8). Idempotent."""
    util.require_systemd()
    current = c.run("localectl status", hide=True).stdout
    ok = f"System Locale: LANG={lang}" in current
    if util.DRY_RUN:
        print(f"[locale] {'ok' if ok else f'MISSING  (would set: {lang})'}")
        return
    if ok:
        print(f"[locale] already set to {lang} — nothing to do")
        return
    c.run(f"{util.SUDO} localectl set-locale LANG={lang}")
    print(f"[locale] set to {lang}")


@task
def disable_ipv6(c):
    """Ensure IPv6 is disabled in /etc/sysctl.conf and apply immediately."""
    content = "\n".join(f"{k} = 1" for k in _IPV6_KEYS)
    text = util.sudo_read(c, _SYSCTL_CONF)
    new_text, status = util.ensure_block_text(text, "ipv6-disable", content)
    if util.DRY_RUN:
        print(f"[sysctl] IPv6 disable: {util.ok_label(status == util.BlockStatus.OK)}")
        return
    if status == util.BlockStatus.OK:
        print("[sysctl] IPv6 already disabled — nothing to do")
        return
    util.sudo_write(c, _SYSCTL_CONF, new_text)
    c.run(f"{util.SUDO} sysctl -p")
    print(f"[sysctl] IPv6 disabled ({status.value})")


@task
def cap_journal_size(c, max_use="500M"):
    """Cap persistent journal size (default: 500M) and restart journald if changed."""
    util.require_systemd()
    content = f"[Journal]\nSystemMaxUse={max_use}"
    text = util.sudo_read(c, _JOURNALD_SIZE_CONF)
    new_text, status = util.ensure_block_text(text, "journal-size", content)
    if util.DRY_RUN:
        print(f"[journal] SystemMaxUse={max_use}: {util.ok_label(status == util.BlockStatus.OK)}")
        return
    if status == util.BlockStatus.OK:
        print(f"[journal] already capped at {max_use} — nothing to do")
        return
    c.run(f"{util.SUDO} mkdir -p {_JOURNALD_CONF_DIR}")
    util.sudo_write(c, _JOURNALD_SIZE_CONF, new_text)
    c.run(f"{util.SUDO} systemctl restart systemd-journald")
    print(f"[journal] SystemMaxUse set to {max_use} ({status.value})")


@task
def set_initramfs_compression(c, algorithm="xz"):
    """Set initramfs compression algorithm (default: xz) and rebuild if changed."""
    text = util.sudo_read(c, _INITRAMFS_CONF)
    pattern = re.compile(r"^([ \t]*#?[ \t]*COMPRESS[ \t]*=[ \t]*)(\S+)$", re.MULTILINE)
    m = pattern.search(text)
    if not m:
        print("[initramfs] COMPRESS line not found in config — check manually")
        return
    current = m.group(2)
    already_set = current == algorithm and not m.group(0).strip().startswith("#")
    if util.DRY_RUN:
        print(f"[initramfs] compression: {'ok' if already_set else f'MISSING  (current: {current})'}")
        return
    if already_set:
        print(f"[initramfs] already using {algorithm} — nothing to do")
        return
    new_text = pattern.sub(f"COMPRESS={algorithm}", text)
    util.sudo_write(c, _INITRAMFS_CONF, new_text)
    print(f"[initramfs] COMPRESS set to {algorithm} (was: {current})")
    c.run(f"{util.SUDO} update-initramfs -u -k all")


@task
def configure_dns(c, primary="1.1.1.1", secondary="1.0.0.1", fallback="8.8.8.8"):
    """Configure DNS via systemd-resolved drop-in (Cloudflare + Google fallback). Idempotent."""
    util.require_systemd()
    content = f"[Resolve]\nDNS={primary} {secondary}\nFallbackDNS={fallback}\nDNSSEC=no"
    text = util.sudo_read(c, _RESOLVED_CONF)
    new_text, status = util.ensure_block_text(text, "dns", content)
    if util.DRY_RUN:
        print(f"[dns] {primary}/{secondary} (fallback {fallback}): {util.ok_label(status == util.BlockStatus.OK)}")
        return
    if status != util.BlockStatus.OK:
        c.run(f"{util.SUDO} mkdir -p {_RESOLVED_CONF_DIR}")
        util.sudo_write(c, _RESOLVED_CONF, new_text)
    # Always restart, even when the drop-in file already matched: the file matching on disk
    # doesn't mean the *running* systemd-resolved has actually loaded it — e.g. under WSL2, a
    # fresh VM boot can leave resolved running with no DNS servers configured at all even though
    # the drop-in from a previous session is still sitting there untouched (`resolvectl status`
    # shows no Global/per-link DNS servers in that state). Restarting is cheap and this task's
    # actual contract is "DNS works", not just "the file is correct".
    c.run(f"{util.SUDO} systemctl restart systemd-resolved")
    print(f"[dns] {primary}, {secondary}, fallback {fallback} ({status.value})")
