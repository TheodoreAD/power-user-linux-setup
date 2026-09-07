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
from dataclasses import dataclass
from pathlib import Path

from invoke import Context, task

from . import deploy, netdoctor, ui, util

# Confirmed against a real `px --save` run (not guessed from --help): Px's default config
# location is XDG's user-config dir, not ~/.px/.
_PX_INI = Path.home() / ".config" / "px" / "px.ini"
UNIT_PATH = Path.home() / ".config" / "systemd" / "user" / "pulse-proxy.service"
ZSHENV = Path.home() / ".zshenv"
_DEFAULT_PORT = 3128

# Read by the systemd unit's EnvironmentFile= and by pulse-proxy-start; holds the keyring backend
# and nothing else. Never a credential — the credential is in the keyring that this names.
ENV_FILE = util.PULSE_CONFIG_DIR / "proxy.env"
# keyring's own name for the non-recommended file backend, and the package that supplies it.
_FALLBACK_BACKEND = "keyrings.alt.file.PlaintextKeyring"
_FALLBACK_PACKAGE = "keyrings.alt"
# Nothing real is stored: the service name resolves to nothing, and the secret is a constant that
# is compared against what comes back and then deleted. Same shape as docker.py's store probe.
_PROBE_SERVICE = "pulse-proxy-keyring-check"
_PROBE_ACCOUNT = "pulse-check"
_PROBE_SECRET = "pulse-round-trip"
# What install() writes into ~/.zshenv once the daemon verifies, named for util.login_shell_warning.
# A bash login shell reads none of it, and the symptom is the daemon running perfectly with nothing
# pointed at it — every tool goes straight out to a proxy that wants a credential they do not have.
_PROXY_EXPORTS = "http_proxy, https_proxy and their uppercase twins"


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


def _wsl_host_ip(c: Context) -> str | None:
    result = c.run("ip route show default", hide=True, warn=True)
    if not result.ok:
        return None
    m = re.search(r"default via (\S+)", result.stdout)
    return m.group(1) if m else None


def _gsettings_proxy(c: Context) -> tuple[str, int] | None:
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


def _discover_candidate(c: Context) -> tuple[str, int, str] | None:  # noqa: C901
    """Returns (host, port, source_description) for the best-guess upstream proxy, or None if
    nothing was found. Environment-specific priority order — see docs/corporate-proxy.md.
    """
    override = util.load_proxy_override()
    if (host := override.get("host")) and (port := override.get("port")):
        return (host, int(port), "~/.config/power-user-linux-setup/identity.toml [proxy]")

    if util.is_wsl():
        host_ip = _wsl_host_ip(c)
        if host_ip:
            probe = _probe(c, host_ip, _DEFAULT_PORT)
            if probe is not None and not probe:
                return (host_ip, _DEFAULT_PORT, "Windows host — unauthenticated Px already running")
        env = _parse_env_proxy(os.environ)
        if env:
            return (*env, "environment (inside WSL guest)")
        # Ask Windows what proxy *it* uses. On a corporate laptop that setting is the real answer
        # and nothing copies it into the distro unless .wslconfig's autoProxy=true is set — so
        # without this, discovery inside WSL comes back empty on exactly the machines that most
        # need a proxy. Read through netdoctor, which owns the reg.exe/netsh.exe/PAC parsing and
        # is the same code the zero-install `python3 tasks/netdoctor.py` uses.
        windows_proxy, pac_url = netdoctor.windows_proxy()
        candidates = [windows_proxy] if windows_proxy else []
        if pac_url:
            candidates += netdoctor.pac_proxies(pac_url, timeout=3.0)
        for candidate in candidates:
            parsed = netdoctor.split_host_port(candidate)
            if parsed and _probe(c, *parsed) is not None:
                source = "Windows host's own proxy setting" + (f" (PAC: {pac_url})" if pac_url else "")
                return (*parsed, source)
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


def _probe(c: Context, host: str, port: int) -> list[str] | None:
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


def _probe_with_retries(c: Context, host: str, port: int, attempts: int = 5, delay: float = 1.0) -> list[str] | None:
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


def _install_px(c: Context) -> None:
    if util.DRY_RUN:
        print(f"[proxy] px: {util.ok_label(util.command_exists('px'))}")
        return
    if util.command_exists("px"):
        return
    if not util.command_exists("uv"):
        raise RuntimeError("uv not found — run ./bootstrap.sh first")
    # Extras come from setup.toml rather than being spelled out here, so this and
    # `inv python.install-tools` cannot install two different pxs. keyrings.alt is what makes
    # --keyring-fallback possible: the backend has to be importable inside px's own tool venv.
    extras = "".join(f" --with {extra}" for extra in util.load_config()["packages"]["px-proxy"].get("extras", []))
    print("[proxy] installing px (uv tool)...")
    c.run(f"uv tool install --upgrade{extras} px-proxy")
    print("[proxy] px installed")


# Px's own defaults, from its configuration docs: listen=127.0.0.1, gateway=0, allow=*.*.*.*. The
# first is why a container cannot reach the daemon at all; the third is why the obvious fix for that
# is dangerous — `gateway=1` overrides `listen`, and the stock allow-list accepts every client that
# can route here. So gateway is only ever enabled alongside a narrowed allow-list, and a value that
# narrows nothing is refused rather than passed through.
_ALLOW_EVERYTHING = frozenset({"*", "*.*", "*.*.*", "*.*.*.*", "0.0.0.0/0"})


@dataclass(frozen=True)
class _Exposure:
    """Who may talk to the local daemon. Default is Px's own: this machine, and nothing else."""

    gateway: bool = False
    allow: str = ""


def _exposure(section: util.ProxySection) -> _Exposure:
    """The `[proxy] gateway`/`allow` pair from identity.toml, validated.

    Refusing `gateway` without a narrowed `allow` is the whole point of reading these through a
    validator rather than passing them to Px. The daemon is unauthenticated to its clients by design
    — that is what makes the credential safe to hold in one place — so opening it to remote clients
    with Px's stock allow-list hands anyone who can route to this machine authenticated egress
    through the user's own corporate account.
    """
    gateway = bool(section.get("gateway", False))
    allow = str(section.get("allow", "")).strip()
    if gateway and not allow:
        raise RuntimeError(
            "[proxy] gateway = true needs an allow list: the daemon is unauthenticated to its "
            "clients, and Px's default allow of *.*.*.* would let anything that can route here "
            "reach the corporate proxy as you. Set [proxy] allow to the range that needs it — "
            "172.17.0.0/16 for docker's default bridge (see docs/corporate-proxy.md)."
        )
    if gateway and allow in _ALLOW_EVERYTHING:
        raise RuntimeError(
            f"[proxy] allow = {allow!r} narrows nothing, which is the same exposure as leaving it "
            "unset. Name the range that actually needs the daemon, e.g. 172.17.0.0/16."
        )
    return _Exposure(gateway, allow)


def _px_save_command(
    host: str,
    port: int,
    noproxy: str | None,
    username: str | None,
    use_kerberos: bool,
    exposure: _Exposure,
) -> str:
    """The `px --save` invocation that writes px.ini. Pure, so what ends up in that file is
    assertable without running Px or having a proxy to point it at."""
    cmd = f"px --proxy={host}:{port} --save"
    if noproxy:
        cmd += f" --noproxy={noproxy}"
    if username:
        cmd += f" --username={username}"
    if use_kerberos:
        cmd += " --kerberos=1"
    if exposure.gateway:
        cmd += " --gateway=1"
    if exposure.allow:
        cmd += f" --allow={exposure.allow}"
    return cmd


def _parse_gateway(px_ini: str) -> bool:
    """Whether px.ini has the daemon accepting remote clients."""
    return bool(re.search(r"^\s*gateway\s*=\s*1\b", px_ini, re.MULTILINE))


def accepts_remote_clients() -> bool:
    """Whether the local daemon, as configured, answers anything but this machine's loopback.

    Public because docker.py needs it: a container-side proxy pointing at the bridge gateway is
    configuration that looks right and cannot work while Px is listening on 127.0.0.1 only.
    """
    return _PX_INI.exists() and _parse_gateway(_PX_INI.read_text())


def _configure_px(
    c: Context, host: str, port: int, noproxy: str | None, username: str | None = None, use_kerberos: bool = False
) -> bool:
    """Persist the upstream address + bypass list + exposure (+ username, if a credential was just
    captured) via Px's own --save — px.ini's schema is deliberately not hand-authored here, see the
    plan doc's "genuine unknowns". Returns True if this changed anything on disk (callers use that
    to decide whether to restart the daemon).
    """
    exposure = _exposure(util.load_proxy_override())
    if util.DRY_RUN:
        print(f"[proxy] px.ini ({host}:{port}): {util.ok_label(_PX_INI.exists())}")
        return False
    before = _PX_INI.read_text() if _PX_INI.exists() else None
    c.run(_px_save_command(host, port, noproxy, username, use_kerberos, exposure), hide=True)
    after = _PX_INI.read_text() if _PX_INI.exists() else None
    return before != after


def _user_systemd_available(c: Context) -> bool:
    if not Path("/run/systemd/system").is_dir():
        return False
    return c.run("systemctl --user status", hide=True, warn=True).ok


UNIT = deploy.Managed(
    path=UNIT_PATH,
    package="px-proxy",
    source="config/pulse-proxy.service",
    mechanism=deploy.Mechanism.MANAGED_FILE,
)


def _write_unit(c: Context) -> bool:
    """Deploy ~/.config/systemd/user/pulse-proxy.service. Returns True if it changed.

    No existing tasks/*.py installs a systemd --user unit (only system-level ones, see
    tasks/system.py); user-owned path, no sudo needed. The content used to be an f-string in this
    module interpolating the px binary path, so the file had no repo-side source, no manifest
    entry, no diff and no redeploy path. It is now `config/pulse-proxy.service` — static, because
    systemd's own `%h` specifier expands the home directory — deployed through the one writer,
    which is what makes a hand edit to it something PULSE reports rather than silently overwrites.

    Constructed here rather than declared in setup.toml on purpose: every declared destination is
    one `inv verify.all` requires to exist at the end of the packages phase, and this unit is
    written only on a machine that actually configures a corporate proxy. MANAGED_FILE rather than
    a wrapper-script `dest` because a unit file must not be executable.
    """
    action = deploy.deploy(UNIT)
    changed = action in (deploy.Action.CREATED, deploy.Action.UPDATED)
    if changed and not util.DRY_RUN:
        c.run("systemctl --user daemon-reload")
    return changed


def _restart_daemon(c: Context) -> None:
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
# The keyring Px reads its credential back out of, and the fallback for a machine that has none.


def _keyring_command(fallback: bool, snippet: str) -> list[str]:
    """A one-shot `uv run` that can talk to the keyring. `--no-project` because this has nothing to
    do with the repo the task happens to be running from: without it, uv resolves the project's
    interpreter and will silently delete and recreate its .venv when the answer differs from what
    is already there (plans/2026-08-30-uv-run-destroys-the-project-venv.md).
    """
    with_flags = ["--with", "keyring"] + (["--with", _FALLBACK_PACKAGE] if fallback else [])
    return ["uv", "run", "--no-project", *with_flags, "python", "-c", snippet]


def _keyring_env(fallback: bool) -> dict[str, str]:
    """PYTHON_KEYRING_BACKEND, per process, only when the fallback is in play. Deliberately not
    ~/.config/python_keyring/keyringrc.cfg: that file selects the backend for every keyring
    consumer on the machine, would quietly downgrade unrelated tools to a plaintext store, and
    would keep doing so after a Secret Service provider appeared.
    """
    env = dict(os.environ)
    if fallback:
        env["PYTHON_KEYRING_BACKEND"] = _FALLBACK_BACKEND
    return env


# The delete is in a finally, not in a line after the read: a store that accepts a write and then
# raises on the read is exactly the half-broken state this probe exists to find, and the linear
# version left its throwaway entry behind on that path. docker.py's equivalent already erases
# before it judges the result, for the same reason.
_ROUND_TRIP = (
    "import keyring, sys\n"
    "service, account, secret = sys.argv[1:4]\n"
    "keyring.set_password(service, account, secret)\n"
    "try:\n"
    "    got = keyring.get_password(service, account)\n"
    "finally:\n"
    "    keyring.delete_password(service, account)\n"
    "print(keyring.get_keyring())\n"
    "sys.exit(0 if got == secret else 3)\n"
)


def _keyring_round_trip(*, fallback: bool = False) -> tuple[bool, str]:
    """Store a throwaway secret, read it back, delete it. Returns (worked, backend-or-reason).

    Whether `keyring` imports is not the question — it always does. Whether a backend answers is,
    and on a minimal WSL2 distro or a from-scratch container with no Secret Service provider the
    answer is NoKeyringError. Probing for that here is what stops `install` from discovering it
    only after a password has been typed. Same rationale as docker.py's `_credential_round_trip`.
    """
    proc = subprocess.run(
        [*_keyring_command(fallback, _ROUND_TRIP), _PROBE_SERVICE, _PROBE_ACCOUNT, _PROBE_SECRET],
        capture_output=True,
        text=True,
        env=_keyring_env(fallback),
        check=False,
    )
    if proc.returncode == 0:
        backend = proc.stdout.strip().splitlines()
        return True, backend[-1] if backend else "ok"
    reason = (proc.stderr or proc.stdout).strip().splitlines()
    return False, reason[-1] if reason else f"exit {proc.returncode}"


ENV_MANAGED = deploy.Managed(
    path=ENV_FILE,
    package="px-proxy",
    source="config/pulse-proxy.env",
    mechanism=deploy.Mechanism.MANAGED_FILE,
)


def _write_env_file() -> None:
    """Pin the fallback backend for Px's own process, through the file both start paths read.

    Deployed rather than written: this used to be a bare `write_text` of an f-string, so the file
    had no repo-side source, no manifest entry and no diff — the same gap `_write_unit` documents,
    in the same feature, missed because one line of generated content does not look like a
    deployment. It can be static because its content never varied: the backend name is a constant.

    Undeclared in setup.toml for the reason the unit beside it is: every declared destination is one
    `inv verify.all` requires to exist, and this one is written only where a machine chose
    `--keyring-fallback`.
    """
    if deploy.deploy(ENV_MANAGED) in (deploy.Action.CREATED, deploy.Action.UPDATED):
        print(f"[proxy] keyring backend pinned for the daemon in {ENV_FILE}")


def _keyring_status(c: Context, *, fallback: bool) -> bool:
    """Report the keyring, and say what to do about it when it doesn't answer. True if usable."""
    ok, detail = _keyring_round_trip(fallback=fallback)
    if ok:
        print(f"[proxy] keyring: {detail}")
        return True
    print(f"[proxy] keyring: no usable backend — {detail}")
    print(
        "[proxy] Px reads its credential from the keyring at its own startup, so this has to work "
        f"before a password is worth capturing: {util.secret_store_remedy(c)}"
    )
    print(
        '[proxy] PULSE never unlocks a store unattended (docs/wsl.md, "The secret store, and '
        'unlocking it") — `inv proxy.install --keyring-fallback` stores the credential in a 0600 '
        "file instead, which is the unattended option."
    )
    return False


def _use_fallback_keyring() -> bool:
    """Switch to the file backend, having said plainly what that costs. False if it doesn't work
    either — `keyrings.alt` may not be installed alongside px, and pretending otherwise would fail
    later, inside the daemon, where the error is much harder to read.
    """
    ui.block(
        "The credential will be stored base64-encoded in a 0600 file under "
        "~/.local/share/python_keyring/, not in a locked keyring. Anything running as this user "
        "can read it. That is the same exposure as PULSE_PROXY_PASSWORD_FILE, and still better "
        "than a password embedded in http_proxy — but it is a downgrade, and it is why this is a "
        "flag rather than an automatic fallback.",
        label="keyring fallback",
    )
    ok, detail = _keyring_round_trip(fallback=True)
    if not ok:
        print(f"[proxy] fallback keyring did not work either — {detail}")
        return False
    print(f"[proxy] keyring: {detail} (fallback)")
    _write_env_file()
    return True


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


def _capture_credential(*, fallback: bool = False) -> str | None:
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
    write = "import keyring, sys; keyring.set_password('Px', sys.argv[1], sys.stdin.read())"
    proc = subprocess.run(
        [*_keyring_command(fallback, write), username],
        input=password,
        capture_output=True,
        text=True,
        env=_keyring_env(fallback),
        check=False,
    )
    if proc.returncode != 0:
        print(f"[proxy] keyring write failed:\n{proc.stderr}")
        return None
    print(f"[proxy] credential saved to the system keyring for {username}")
    return username


def _capture_with_keyring(c: Context, *, keyring_fallback: bool) -> str | None:
    """Check the keyring can hold a credential, then capture one. None if either half fails.

    The two steps are one function because their order is the whole point: Px reads the credential
    back out of the keyring at its own startup, so a machine with no backend cannot hold one, and
    asking for a password before finding that out is exactly what this used to do. A machine that
    chose the fallback once keeps it — proxy.env existing is that decision, recorded.
    """
    fallback = keyring_fallback or ENV_FILE.exists()
    usable = _use_fallback_keyring() if fallback else _keyring_status(c, fallback=False)
    if not usable:
        print("[proxy] no keyring to store the credential in — stopping before asking for one")
        return None
    return _capture_credential(fallback=fallback)


def _export_proxy_env(noproxy: str | None) -> None:
    """Point every shell at the verified local daemon, and say whether that will reach anything.

    The last step of install() and the only one whose failure is silent: on a bash login shell the
    block is written correctly and read by nothing, so the daemon runs perfectly with no client
    while every tool goes straight out to a proxy that wants a credential they do not have.
    """
    content = (
        f'export http_proxy="http://127.0.0.1:{_DEFAULT_PORT}"\n'
        f'export https_proxy="http://127.0.0.1:{_DEFAULT_PORT}"\n'
        f'export HTTP_PROXY="http://127.0.0.1:{_DEFAULT_PORT}"\n'
        f'export HTTPS_PROXY="http://127.0.0.1:{_DEFAULT_PORT}"\n'
        + (f'export no_proxy="{noproxy}"\nexport NO_PROXY="{noproxy}"\n' if noproxy else "")
    )
    status = util.ensure_block(ZSHENV, "proxy", content)
    if note := util.login_shell_warning(_PROXY_EXPORTS):
        print(f"[proxy] ~/.zshenv proxy block: {status.value}")
        print(f"[proxy] {note}")
    else:
        print(f"[proxy] ~/.zshenv proxy block: {status.value} — open a new terminal for it to take effect")


def _needs_negotiate(schemes: list[str]) -> bool:
    return any(s.lower() in ("negotiate", "kerberos") for s in schemes)


def _has_kerberos_ticket(c: Context) -> bool:
    if not util.command_exists("klist"):
        return False
    return c.run("klist -s", hide=True, warn=True).ok


# ---------------------------------------------------------------------------
# Tasks


@task
def check(c: Context, proxy: str = "auto"):
    """Diagnose corporate-proxy state: environment, candidate address, auth scheme, Px/daemon
    status. Changes no configuration — with one exception worth stating rather than burying, since
    "read-only" was claimed here while it was untrue: the keyring probe stores a throwaway secret
    under a service name that resolves to nothing and deletes it again in a `finally`. There is no
    way to ask a keyring whether it can hold a credential except by holding one, and the alternative
    — reporting only what the D-Bus name owner says — cannot see a store that accepts a write and
    fails the read, which is the state this exists to catch.

    --proxy=host:port overrides auto-discovery, e.g. to probe
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
        if accepts_remote_clients():
            print("[proxy] listen: remote clients allowed (gateway) — check [proxy] allow narrows who")
        else:
            print("[proxy] listen: 127.0.0.1 only — containers and other hosts cannot reach this daemon")
    else:
        print("[proxy] px: not installed  ← `inv proxy.install` installs it (uv tool)")

    _keyring_status(c, fallback=ENV_FILE.exists())

    if note := util.login_shell_warning(_PROXY_EXPORTS):
        print(f"[proxy] {note}")

    if _user_systemd_available(c):
        active = c.run("systemctl --user is-active pulse-proxy.service", hide=True, warn=True).stdout.strip()
        print(f"[proxy] pulse-proxy.service: {active or 'not found'}")
    else:
        print("[proxy] systemd --user: not available here — devcontainer fallback (pulse-proxy-start) applies")


@task
def fix(c: Context, proxy: str = "auto", noproxy: str | None = None):
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


@task(
    help={
        "keyring_fallback": (
            "Store the proxy password in a 0600 file (keyrings.alt's plaintext backend) instead of "
            "the OS keyring, for a distro or container with no Secret Service provider. A real "
            "downgrade — anything running as this user can read it — so it is never automatic."
        )
    }
)
def install(c: Context, proxy: str = "auto", noproxy: str | None = None, keyring_fallback: bool = False):
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
        username = _capture_with_keyring(c, keyring_fallback=keyring_fallback)
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

    _export_proxy_env(noproxy)
