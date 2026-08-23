import difflib
import re
from pathlib import Path

from invoke import Exit, task

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


def _config_diff(current: bytes, desired: bytes, dst: Path, src: str) -> str:
    """Indented unified diff of a deployed config against its repo-side source."""
    try:
        before = current.decode().splitlines(keepends=True)
        after = desired.decode().splitlines(keepends=True)
    except UnicodeDecodeError:
        return "  (binary file — diff not shown)\n"
    diff = difflib.unified_diff(before, after, fromfile=str(dst), tofile=src)
    return "".join(f"  {line}" if line.endswith("\n") else f"  {line}\n" for line in diff)


def _deploy_config_file(pkg: str, mapping: dict, *, assume_yes: bool) -> None:
    src = mapping["src"]
    dst = Path(mapping["dst"]).expanduser()
    # Resolved against the repo root, not the cwd, so the task works from any directory.
    desired = (_REPO_ROOT / src).read_bytes()
    current = dst.read_bytes() if dst.exists() else None

    if current == desired:
        print(f"[configs] {pkg}: {dst} already matches {src}")
        return

    if current is None:
        if util.DRY_RUN:
            print(f"[configs] {pkg}: would create {dst}")
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(desired)
        print(f"[configs] {pkg}: created {dst}")
        return

    print(f"\n[configs] {pkg}: {dst} differs from {src}\n")
    print(_config_diff(current, desired, dst, src))
    if util.DRY_RUN:
        print(f"[configs] {pkg}: would overwrite {dst}")
        return
    # confirm() returns its default unmodified when stdin isn't a terminal, so a piped/CI run
    # without --yes skips the overwrite rather than silently clobbering a hand-edited file.
    if not assume_yes and not util.confirm(f"Overwrite {dst}?", default=False):
        print(f"[configs] {pkg}: left alone")
        return
    dst.write_bytes(desired)
    print(f"[configs] {pkg}: overwrote {dst}")


@task(
    help={
        "name": "Only deploy the config files declared by this [packages.*] section, e.g. wezterm.",
        "yes": "Overwrite drifted destinations without prompting.",
    }
)
def configs(c, name=None, yes=False):
    """Deploy every setup.toml `config_files` mapping, overwriting destinations that have drifted.

    The install tasks that also apply `config_files` (apt.base, apt.deb) only ever write a
    destination that doesn't exist yet, so editing a repo-side `config/*` source never reaches an
    already-deployed file. This is the deliberate redeploy path: it diffs each mapping and prompts
    before overwriting, so a hand-edited destination is never clobbered unasked.
    """
    packages = util.enabled_packages()
    if name is not None:
        if name not in packages:
            raise Exit(f"[configs] no enabled [packages.{name}] section in setup.toml")
        packages = {name: packages[name]}

    mappings = [(pkg, m) for pkg, cfg in packages.items() for m in cfg.get("config_files", [])]
    if not mappings:
        scope = f" for {name}" if name else ""
        print(f"[configs] no config_files declared{scope}")
        return

    for pkg, mapping in mappings:
        _deploy_config_file(pkg, mapping, assume_yes=yes)


@task
def apparmor_profiles(c):
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
def curlrc(c):
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
def locale(c, lang="en_US.UTF-8"):
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
def journal_size(c, max_use="500M"):
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
def initramfs_compression(c, algorithm="xz"):
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
def dns(c, primary="1.1.1.1", secondary="1.0.0.1", fallback="8.8.8.8"):
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
