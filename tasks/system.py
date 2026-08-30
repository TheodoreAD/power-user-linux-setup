import re
from pathlib import Path

from invoke import Context, task

from . import util

_REPO_ROOT = Path(__file__).parent.parent
_SYSCTL_CONF = Path("/etc/sysctl.conf")
_APPARMOR_DIR = Path("/etc/apparmor.d")
_INITRAMFS_CONF = Path("/etc/initramfs-tools/initramfs.conf")
_JOURNALD_CONF_DIR = Path("/etc/systemd/journald.conf.d")
_JOURNALD_SIZE_CONF = _JOURNALD_CONF_DIR / "size.conf"
_RESOLVED_CONF_DIR = Path("/etc/systemd/resolved.conf.d")
_RESOLVED_CONF = _RESOLVED_CONF_DIR / "pulse-dns.conf"
CURLRC = Path.home() / ".config" / "curlrc"

_IPV6_KEYS = [
    "net.ipv6.conf.all.disable_ipv6",
    "net.ipv6.conf.default.disable_ipv6",
    "net.ipv6.conf.lo.disable_ipv6",
]


@task
def install_apparmor_profiles(c: Context):
    """Install AppArmor profiles declared in setup.toml with method = 'apparmor-profile'."""
    profiles = util.packages_by_method(util.PackageMethod.APPARMOR_PROFILE)
    if not profiles:
        if util.DRY_RUN:
            print("[apparmor] no profiles declared")
        return
    for name, cfg in profiles.items():
        if "profile" not in cfg or "content" not in cfg:
            raise util.missing_fields(name, "profile", "content")
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
def write_curlrc(c: Context):
    """Write ~/.config/curlrc: silent, show errors, follow redirects. Idempotent."""
    content = "--silent\n--show-error\n--location"
    if util.DRY_RUN:
        text = CURLRC.read_text() if CURLRC.exists() else ""
        _, status = util.ensure_block_text(text, "curlrc", content)
        print(f"[curlrc] {util.ok_label(status == util.BlockStatus.OK)}")
        return
    result = util.ensure_block(CURLRC, "curlrc", content)
    if result != util.BlockStatus.OK:
        print(f"[curlrc] {result.value}")
    else:
        print("[curlrc] already configured — nothing to do")


def parse_system_locale(status: str) -> dict[str, str]:
    """The `System Locale:` block of `localectl status`, as a dict.

    The block is one `VAR=value` per line, the first on the `System Locale:` line itself and the
    rest below it. Delimited by field headers rather than by indentation: localectl right-aligns its
    keys, so `System Locale:` is flush left only while a longer key (`VC Keymap:`) is present, and a
    continuation line is indented exactly as far as the next field's label. What separates them is
    the colon — `LC_TIME=en_DK.UTF-8` has none, `X11 Options: grp_led:scroll` starts with one.

    Pure, so the parsing is unit-testable without systemd — and it is what makes `set_locale` safe,
    since localed replaces the whole locale configuration and anything missed here would be dropped.
    """
    field = re.compile(r"^(?P<key>[A-Za-z0-9][A-Za-z0-9 ]*): ?(?P<rest>.*)$")
    out: dict[str, str] = {}
    in_block = False
    for raw in status.splitlines():
        line = raw.strip()
        if header := field.match(line):
            in_block = header["key"] == "System Locale"
            line = header["rest"]
        if in_block and "=" in line:
            key, _, value = line.partition("=")
            out[key] = value
    return out


@task
def set_locale(
    c: Context,
    lang: str = "en_US.UTF-8",
    lc_time: str = "en_DK.UTF-8",
    lc_numeric: str = "C.UTF-8",
):
    """Set the system locale via localectl, preserving every variable not named here. Idempotent.

    The defaults are deliberate and measured (see
    plans/2026-08-30-english-iso-locale-defaults.md). `en_DK.UTF-8` is the only stock locale giving
    English weekday and month names, a 24-hour clock and `YYYY-MM-DD` dates at once — `en_CA` gets
    the date right and the clock wrong, `en_GB` the reverse — and it keeps Monday as the first day
    of the week, which `en_US` would silently flip to Sunday in the desktop calendar. `LC_NUMERIC`
    is separate because `en_DK` is comma-decimal like a European locale, so it would leave
    `awk`/`printf` emitting `1,50`; `C.UTF-8` is the dot-decimal answer developer tooling expects.

    Read-modify-write rather than a bare `set-locale LANG=…`: localed takes the whole locale
    configuration, so naming only some variables risks dropping the rest. The regional ones a
    machine legitimately keeps — `LC_MONETARY`, `LC_PAPER`, `LC_MEASUREMENT` — survive because they
    are read back and passed through untouched.
    """
    util.require_systemd()
    current = parse_system_locale(c.run("localectl status", hide=True).stdout)
    desired = current | {"LANG": lang, "LC_TIME": lc_time, "LC_NUMERIC": lc_numeric}
    changes = {k: v for k, v in desired.items() if current.get(k) != v}

    if util.DRY_RUN:
        summary = ", ".join(f"{k}={v}" for k, v in changes.items())
        print(f"[locale] {'ok' if not changes else f'MISSING  (would set: {summary})'}")
        return
    if not changes:
        print(f"[locale] already LANG={lang} LC_TIME={lc_time} LC_NUMERIC={lc_numeric} — nothing to do")
        return

    assignments = " ".join(f"{k}={v}" for k, v in sorted(desired.items()))
    c.run(f"{util.SUDO} localectl set-locale {assignments}")
    print(f"[locale] set {', '.join(f'{k}={v}' for k, v in changes.items())}")
    print("[locale] running shells and the desktop session keep the old values until you log out")


@task
def disable_ipv6(c: Context):
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
def cap_journal_size(c: Context, max_use: str = "500M"):
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
def set_initramfs_compression(c: Context, algorithm: str = "xz"):
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
def configure_dns(c: Context, primary: str = "1.1.1.1", secondary: str = "1.0.0.1", fallback: str = "8.8.8.8"):
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
