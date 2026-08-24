"""Corporate proxy auth detection + local daemon (Px). See docs/corporate-proxy.md.

Px (https://github.com/genotrance/px, PyPI package px-proxy) is a local, unauthenticated-to-the-
client HTTP(S) proxy that authenticates to the real corporate proxy on the caller's behalf and
caches the credential in the OS keyring — apps point at 127.0.0.1:<port> and never see the real
credential. This module detects whether a proxy is present at all, what auth scheme it requires,
and drives Px's own --save/--kerberos flags plus a direct keyring write accordingly, rather than
hand-authoring px.ini or reimplementing NTLM/Kerberos negotiation (neither of which this repo's
author can test against real corporate infra — see docs/corporate-proxy.md's "Genuine limitations"
section and contributing/corporate-proxy.md for the full rationale). The credential path
specifically was verified end to end against a disposable local Squid instance, not assumed from
Px's --help text alone — see _capture_credential's docstring for what that testing found and
corrected.
"""

import getpass
import os
import re
import subprocess
import time
from collections.abc import Mapping
from pathlib import Path

from invoke import task

from . import ui, util

# Confirmed against a real `px --save` run (not guessed from --help): Px's default config
# location is XDG's user-config dir, not ~/.px/.
_PX_INI = Path.home() / ".config" / "px" / "px.ini"
_PX_BIN = Path.home() / ".local" / "bin" / "px"
_UNIT_DIR = Path.home() / ".config" / "systemd" / "user"
_UNIT_PATH = _UNIT_DIR / "pulse-proxy.service"
_ZSHENV = Path.home() / ".zshenv"
_DEFAULT_PORT = 3128

_UNIT_CONTENT = f"""[Unit]
Description=PULSE local proxy (Px) - unauthenticated localhost front for the corporate proxy
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={_PX_BIN}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""


# ---------------------------------------------------------------------------
# Pure helpers — unit-tested in tests/unit/test_proxy.py, see tests/README.md for why these and not
# the rest of this module (everything else shells out or touches the filesystem/keyring).


def _parse_proxy_authenticate(curl_verbose_output: str) -> list[str]:
    """Extract auth scheme tokens (Basic/NTLM/Negotiate/Digest/...) from `curl -v`'s stderr.
    Handles both a repeated `Proxy-Authenticate:` header per scheme and a single comma-joined
    header — RFC 7235 permits either, and which one a given corporate proxy actually sends is
    unverified (see plan doc). Order in the returned list follows header order, deduplicated.
    """
    schemes: list[str] = []
    for line in curl_verbose_output.splitlines():
        m = re.search(r"[Pp]roxy-[Aa]uthenticate:\s*(.+)", line)
        if not m:
            continue
        for part in m.group(1).split(","):
            token = part.strip().split(" ")[0].strip()
            if token and token not in schemes:
                schemes.append(token)
    return schemes


def _split_host_port(url: str, default_port: int = 80) -> tuple[str, int] | None:
    """Parse a host[:port] out of a proxy URL/value, tolerating a scheme and userinfo prefix
    (http://host:port, host:port, or a stray http://user:pass@host:port some other tool left
    behind — parsed only to extract host/port, never to reuse the embedded credential).
    """
    m = re.match(r"^(?:https?://)?(?:[^@/]+@)?([^:/\s]+)(?::(\d+))?", url.strip())
    if not m or not m.group(1):
        return None
    return (m.group(1), int(m.group(2)) if m.group(2) else default_port)


def _parse_env_proxy(environ: Mapping[str, str]) -> tuple[str, int] | None:
    """Highest-confidence discovery source: whatever's already in the current shell's proxy env
    vars is literally what every CLI tool already reads."""
    for key in ("https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY"):
        val = environ.get(key)
        if val:
            parsed = _split_host_port(val)
            if parsed:
                return parsed
    return None


def _parse_etc_environment(text: str) -> tuple[str, int] | None:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        if key.strip() in ("https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY"):
            parsed = _split_host_port(val.strip().strip('"').strip("'"))
            if parsed:
                return parsed
    return None


# ---------------------------------------------------------------------------
# Environment + address discovery (shells out — not unit-tested, see tests/README.md)


def _wsl_host_ip(c) -> str | None:
    result = c.run("ip route show default", hide=True, warn=True)
    if not result.ok:
        return None
    m = re.search(r"default via (\S+)", result.stdout)
    return m.group(1) if m else None


def _gsettings_proxy(c) -> tuple[str, int] | None:
    mode = c.run("gsettings get org.gnome.system.proxy mode", hide=True, warn=True)
    if not mode.ok or "manual" not in mode.stdout:
        return None
    host = c.run("gsettings get org.gnome.system.proxy.http host", hide=True, warn=True)
    port = c.run("gsettings get org.gnome.system.proxy.http port", hide=True, warn=True)
    if not (host.ok and port.ok):
        return None
    host_val = host.stdout.strip().strip("'")
    port_val = port.stdout.strip()
    if not host_val or not port_val.isdigit():
        return None
    return (host_val, int(port_val))


def _discover_candidate(c) -> tuple[str, int, str] | None:  # noqa: C901
    """Returns (host, port, source_description) for the best-guess upstream proxy, or None if
    nothing was found. Environment-specific priority order — see docs/corporate-proxy.md.
    """
    override = util.load_proxy_override()
    if override.get("host") and override.get("port"):
        return (override["host"], int(override["port"]), "~/.config/power-user-linux-setup/identity.toml [proxy]")

    if util.is_wsl():
        host_ip = _wsl_host_ip(c)
        if host_ip:
            probe = _probe(c, host_ip, _DEFAULT_PORT)
            if probe is not None and not probe:
                return (host_ip, _DEFAULT_PORT, "Windows host — unauthenticated Px already running")
        env = _parse_env_proxy(os.environ)
        if env:
            return (*env, "environment (inside WSL guest)")
        return None

    if util.is_devcontainer():
        env = _parse_env_proxy(os.environ)
        if env:
            return (*env, "inherited environment")
        for guess_port in (_DEFAULT_PORT, 8080):
            probe = _probe(c, "host.docker.internal", guess_port)
            if probe is not None:
                return ("host.docker.internal", guess_port, "host.docker.internal (guess)")
        return None

    env = _parse_env_proxy(os.environ)
    if env:
        return (*env, "environment")
    etc_env = _parse_etc_environment(Path("/etc/environment").read_text() if Path("/etc/environment").exists() else "")
    if etc_env:
        return (*etc_env, "/etc/environment")
    gnome = _gsettings_proxy(c)
    if gnome:
        return (*gnome, "GNOME proxy setting (low confidence — confirm before trusting)")
    return None


def _probe(c, host: str, port: int) -> list[str] | None:
    """Send an unauthenticated request through the candidate and read the schemes offered on the
    resulting 407. None means the candidate wasn't reachable at all (connection-level failure —
    curl itself still exits ok on a 407, since that's a valid HTTP response, not a curl error).
    Empty list means reachable but no proxy auth was requested.
    """
    result = c.run(
        f"curl -sv -o /dev/null --max-time 3 --proxy http://{host}:{port} http://example.com",
        hide=True,
        warn=True,
    )
    if not result.ok:
        return None
    return _parse_proxy_authenticate(result.stderr)


def _probe_with_retries(c, host: str, port: int, attempts: int = 5, delay: float = 1.0) -> list[str] | None:
    """Same as _probe, but retried briefly — used only for the post-restart verification in
    install(). `systemctl --user restart`/a freshly-forked px process returning doesn't mean the
    port is bound yet (confirmed in practice: an immediate probe here saw a connection refused
    that a 1-second-later retry did not), so a single immediate probe is not reliable evidence of
    failure the way it is everywhere else this module probes an already-running proxy.
    """
    result = None
    for attempt in range(attempts):
        result = _probe(c, host, port)
        if result is not None:
            return result
        if attempt < attempts - 1:
            time.sleep(delay)
    return result


# ---------------------------------------------------------------------------
# Px install / config / daemon lifecycle


def _install_px(c) -> None:
    if util.DRY_RUN:
        print(f"[proxy] px: {util.ok_label(util.command_exists('px'))}")
        return
    if util.command_exists("px"):
        return
    if not util.command_exists("uv"):
        raise RuntimeError("uv not found — run ./bootstrap.sh first")
    print("[proxy] installing px (uv tool)...")
    c.run("uv tool install --upgrade px-proxy")
    print("[proxy] px installed")


def _configure_px(
    c, host: str, port: int, noproxy: str | None, username: str | None = None, use_kerberos: bool = False
) -> bool:
    """Persist the upstream address + bypass list (+ username, if a credential was just captured)
    via Px's own --save — px.ini's schema is deliberately not hand-authored here, see the plan
    doc's "genuine unknowns". Returns True if this changed anything on disk (callers use that to
    decide whether to restart the daemon).
    """
    if util.DRY_RUN:
        print(f"[proxy] px.ini ({host}:{port}): {util.ok_label(_PX_INI.exists())}")
        return False
    before = _PX_INI.read_text() if _PX_INI.exists() else None
    cmd = f"px --proxy={host}:{port} --save"
    if noproxy:
        cmd += f" --noproxy={noproxy}"
    if username:
        cmd += f" --username={username}"
    if use_kerberos:
        cmd += " --kerberos=1"
    c.run(cmd, hide=True)
    after = _PX_INI.read_text() if _PX_INI.exists() else None
    return before != after


def _user_systemd_available(c) -> bool:
    if not Path("/run/systemd/system").is_dir():
        return False
    return c.run("systemctl --user status", hide=True, warn=True).ok


def _write_unit(c) -> bool:
    """Write ~/.config/systemd/user/pulse-proxy.service — a genuinely new pattern in this repo,
    no existing tasks/*.py installs a systemd --user unit (only system-level units, see
    tasks/system.py). User-owned path, no sudo needed. Returns True if changed.
    """
    if util.DRY_RUN:
        ok = _UNIT_PATH.exists() and _UNIT_PATH.read_text() == _UNIT_CONTENT
        print(f"[proxy] systemd --user unit: {util.ok_label(ok)}")
        return False
    changed = not (_UNIT_PATH.exists() and _UNIT_PATH.read_text() == _UNIT_CONTENT)
    if changed:
        _UNIT_DIR.mkdir(parents=True, exist_ok=True)
        _UNIT_PATH.write_text(_UNIT_CONTENT)
        c.run("systemctl --user daemon-reload")
    return changed


def _restart_daemon(c) -> None:
    """Always called after any config/unit change — file-correct doesn't imply the running
    process picked it up, same rationale tasks/system.py's dns() task documents for
    systemd-resolved. Falls back to the devcontainer wrapper script when systemd --user isn't
    available (see docs/corporate-proxy.md — no crash auto-restart in that fallback, a real,
    documented limitation, not silently papered over).
    """
    if util.DRY_RUN:
        return
    if _user_systemd_available(c):
        c.run("systemctl --user enable --now pulse-proxy.service")
        c.run("systemctl --user restart pulse-proxy.service")
    else:
        if not util.command_exists("pulse-proxy-start"):
            print(
                "[proxy] systemd --user unavailable and pulse-proxy-start not installed — "
                "run `inv tools.install` first, then re-run `inv proxy.fix`."
            )
            return
        c.run("pulse-proxy-start", warn=True)


# ---------------------------------------------------------------------------
# Credential capture (proxy.install only — proxy.fix never prompts)


def _capture_password(prompt: str) -> str | None:
    """GUI prompt (askpass-zenity, if installed and a display is present) with a getpass()
    fallback for a real terminal. Returns None in a non-interactive context (headless/CI/
    postCreateCommand) — those need PULSE_PROXY_PASSWORD_FILE set instead, see
    docs/corporate-proxy.md; PULSE never guesses or silently skips credential capture there.
    """
    askpass = Path.home() / ".local" / "bin" / "askpass-zenity"
    if os.environ.get("DISPLAY") and askpass.exists():
        result = subprocess.run([str(askpass), prompt], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.rstrip("\n")
    if util.interactive():
        return getpass.getpass(prompt + " ")
    password_file = os.environ.get("PULSE_PROXY_PASSWORD_FILE")
    if password_file and Path(password_file).exists():
        return Path(password_file).read_text().strip()
    return None


def _capture_credential(c) -> str | None:
    """Capture a username+password once and store the password in the same keyring entry Px
    itself reads at its own startup (service "Px", account <username>). Returns the username on
    success, None on failure — the caller (install()) still needs the username to pass to
    `px --save` alongside the proxy address, so this doesn't call px itself.

    Originally this shelled out to `px --username=... --save --password`, matching --help's
    documented "--password: Collect and save password to default keyring." Verified against a
    disposable local Squid instance (see contributing/corporate-proxy.md) that this does NOT work
    non-interactively: --password calls Python's
    getpass.getpass(), which opens /dev/tty directly and raises EOFError with no controlling
    terminal — piping input, a pty via `script`, or setting PX_PASSWORD in the subprocess env all
    failed to produce a stored password in this repo's own testing. PX_PASSWORD *does* work, but
    only as an ephemeral value Px reads at its own process startup — verified separately that it
    is NOT what --password consumes to populate the keyring.

    So PULSE writes the keyring entry directly instead (verified working end-to-end: written this
    way, Px's own runtime keyring.get_password() picks it up and successfully authenticates to a
    real upstream proxy).
    """
    default_user = os.environ.get("USER", "")
    username = util.prompt_text("Corporate proxy username (domain\\username, or just username):", default=default_user)
    if not username:
        print("[proxy] no username given — aborting credential capture")
        return None
    password = _capture_password(f"Corporate proxy password for {username}:")
    if password is None:
        print(
            "[proxy] no password source available (no GUI, no TTY, and PULSE_PROXY_PASSWORD_FILE "
            "not set) — set PULSE_PROXY_PASSWORD_FILE and re-run `inv proxy.install`."
        )
        return None

    if util.DRY_RUN:
        print(f"[proxy] would save keyring credential for {username}")
        return username
    # Password goes over stdin to a short-lived subprocess, never argv (visible in `ps`) or a
    # file — `uv run --with keyring` is a one-off dependency needed only for this single call,
    # not worth adding to the project's `pyproject.toml`. subprocess.run directly, not c.run:
    # invoke's Runner doesn't offer a clean way to pass stdin bytes without echoing them through
    # the terminal-mirroring machinery it otherwise provides.
    proc = subprocess.run(
        [
            "uv",
            "run",
            "--with",
            "keyring",
            "python",
            "-c",
            "import keyring, sys; keyring.set_password('Px', sys.argv[1], sys.stdin.read())",
            username,
        ],
        input=password,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(f"[proxy] keyring write failed:\n{proc.stderr}")
        return None
    print(f"[proxy] credential saved to the system keyring for {username}")
    return username


def _needs_negotiate(schemes: list[str]) -> bool:
    return any(s.lower() in ("negotiate", "kerberos") for s in schemes)


def _has_kerberos_ticket(c) -> bool:
    if not util.command_exists("klist"):
        return False
    return c.run("klist -s", hide=True, warn=True).ok


# ---------------------------------------------------------------------------
# Tasks


@task
def check(c, proxy="auto"):
    """Diagnose corporate-proxy state: environment, candidate address, auth scheme, Px/daemon
    status. Read-only — never mutates. --proxy=host:port overrides auto-discovery, e.g. to probe
    a specific address without it being live in the environment yet. See docs/corporate-proxy.md.
    """
    kind = "WSL" if util.is_wsl() else "dev container" if util.is_devcontainer() else "native Linux"
    print(f"[proxy] environment: {kind}")

    if proxy == "auto":
        candidate = _discover_candidate(c)
    else:
        parsed = _split_host_port(proxy, default_port=_DEFAULT_PORT)
        candidate = (parsed[0], parsed[1], "--proxy") if parsed else None
    if candidate is None:
        print(
            "[proxy] no candidate proxy address found — nothing to configure. If this network "
            "does use a corporate proxy, pass --proxy=host:port to `inv proxy.install`, or add a "
            "[proxy] host/port to ~/.config/power-user-linux-setup/identity.toml (see config/identity.toml.example)."
        )
        return
    host, port, source = candidate
    print(f"[proxy] candidate: {host}:{port} (source: {source})")

    schemes = _probe(c, host, port)
    if schemes is None:
        print(f"[proxy] {host}:{port} not reachable from here — nothing to configure")
        return
    if not schemes:
        print(f"[proxy] {host}:{port} reachable, no proxy auth required")
    else:
        print(f"[proxy] {host}:{port} requires: {', '.join(schemes)}")
        if _needs_negotiate(schemes):
            print(f"[proxy] Kerberos ticket cached: {'✓' if _has_kerberos_ticket(c) else 'no (klist -s)'}")

    if util.command_exists("px"):
        print("[proxy] px: installed ✓")
        # px.ini always has a "username =" line, even blank — only a non-empty value means a
        # credential was actually captured (confirmed against a real px --save run).
        saved = _PX_INI.exists() and bool(re.search(r"^username\s*=\s*\S", _PX_INI.read_text(), re.MULTILINE))
        print(f"[proxy] px.ini: {'username saved (credential likely cached)' if saved else 'no saved username yet'}")
    else:
        print("[proxy] px: not installed  ← `inv proxy.install` installs it (uv tool)")

    if _user_systemd_available(c):
        active = c.run("systemctl --user is-active pulse-proxy.service", hide=True, warn=True).stdout.strip()
        print(f"[proxy] pulse-proxy.service: {active or 'not found'}")
    else:
        print("[proxy] systemd --user: not available here — devcontainer fallback (pulse-proxy-start) applies")


@task
def fix(c, proxy="auto", noproxy=None):
    """Install px if missing and (re)write its config + daemon, without touching credentials.
    Idempotent, non-interactive. Run `inv proxy.install` instead for the full flow including
    credential capture. See docs/corporate-proxy.md.
    """
    if proxy == "auto":
        candidate = _discover_candidate(c)
        if candidate is None:
            print("[proxy] no proxy address resolved — pass --proxy=host:port or run `inv proxy.check` first")
            return
        host, port, _source = candidate
    else:
        parsed = _split_host_port(proxy, default_port=_DEFAULT_PORT)
        if parsed is None:
            raise RuntimeError(f"--proxy must be host:port (got {proxy!r})")
        host, port = parsed

    _install_px(c)
    unit_changed = _write_unit(c)
    ini_changed = _configure_px(c, host, port, noproxy)

    if util.DRY_RUN:
        return
    if unit_changed or ini_changed:
        _restart_daemon(c)
    print(f"[proxy] configured for {host}:{port}" + (f", bypass: {noproxy}" if noproxy else ""))


@task
def install(c, proxy="auto", noproxy=None):
    """Full flow: detect, capture a credential if the probe requires one, configure + start the
    daemon, then verify it actually authenticates before pointing every terminal at it. See
    docs/corporate-proxy.md.
    """
    ui.block(
        "About to: detect a corporate proxy, install px if missing, capture a credential if "
        "needed (GUI prompt or terminal), start a local daemon at 127.0.0.1, and — only once "
        "verified working — export http_proxy/https_proxy in ~/.zshenv.",
        label="proxy.install",
    )
    if not ui.ask("Proceed?", default=True):
        print("[proxy] aborted")
        return

    check(c, proxy=proxy)

    if proxy == "auto":
        candidate = _discover_candidate(c)
    else:
        parsed = _split_host_port(proxy, default_port=_DEFAULT_PORT)
        candidate = (parsed[0], parsed[1], "--proxy") if parsed else None
    if candidate is None:
        print("[proxy] nothing to configure — no proxy detected on this network")
        return
    host, port, _source = candidate

    schemes = _probe(c, host, port)
    if schemes is None:
        print(f"[proxy] {host}:{port} not reachable — nothing to configure")
        return

    _install_px(c)

    has_negotiate = _needs_negotiate(schemes)
    needs_credential = bool(schemes) and not (has_negotiate and _has_kerberos_ticket(c))
    username = None
    if needs_credential:
        username = _capture_credential(c)
        if username is None:
            print("[proxy] credential capture failed or was skipped — stopping before daemon start")
            return
    elif has_negotiate:
        print("[proxy] existing Kerberos ticket found — no password needed")

    _configure_px(c, host, port, noproxy, username=username, use_kerberos=has_negotiate)
    _write_unit(c)
    _restart_daemon(c)

    verify = _probe_with_retries(c, "127.0.0.1", _DEFAULT_PORT)
    if verify is None:
        print("[proxy] daemon did not come up on 127.0.0.1:3128 — check `systemctl --user status pulse-proxy.service`")
        return
    if verify:
        print(f"[proxy] daemon is up but still requesting auth ({', '.join(verify)}) — credential may be wrong")
        return
    print("[proxy] verified: 127.0.0.1:3128 authenticates through to the upstream proxy")

    content = (
        f'export http_proxy="http://127.0.0.1:{_DEFAULT_PORT}"\n'
        f'export https_proxy="http://127.0.0.1:{_DEFAULT_PORT}"\n'
        f'export HTTP_PROXY="http://127.0.0.1:{_DEFAULT_PORT}"\n'
        f'export HTTPS_PROXY="http://127.0.0.1:{_DEFAULT_PORT}"\n'
        + (f'export no_proxy="{noproxy}"\nexport NO_PROXY="{noproxy}"\n' if noproxy else "")
    )
    status = util.ensure_block(_ZSHENV, "proxy", content)
    print(f"[proxy] ~/.zshenv proxy block: {status.value} — open a new terminal for it to take effect")
