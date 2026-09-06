"""Corporate TLS-inspection CA bundle installer. See docs/certs.md.

Corporate networks commonly run TLS-inspecting proxies (Zscaler, Netskope, etc.) that MITM
HTTPS with their own root CA — every TLS client on the machine needs to trust it, or TLS
verification fails everywhere. IT-provided bundles arrive in inconsistent formats (PEM, raw DER,
or a Windows PKCS#7 .p7b/.p7c) and the file extension is not a reliable indicator of which, so
this module detects format by content and converts before anything touches the trust store.
Debian's own `update-ca-certificates` silently skips a file it can't parse (just a warning, not a
failure) — the install then "succeeds" while TLS verification keeps failing with no clear signal
why. This module refuses that failure mode: an unparseable bundle raises loudly instead.

No JDK is installed or managed here — the Java cacerts step is purely conditional on `keytool`
already being on PATH, a no-op if none is present, self-activating for free if one is added
independently later.
"""

import base64
import hashlib
import re
import shlex
import subprocess
import tempfile
from pathlib import Path

from invoke import Context, Exit, task

from . import util

_CA_CERT_FILE = Path("/usr/local/share/ca-certificates/pulse-corporate.crt")
_SYSTEM_BUNDLE = "/etc/ssl/certs/ca-certificates.crt"  # what update-ca-certificates produces
ZSHENV = Path.home() / ".zshenv"

_CERT_RE = re.compile(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", re.DOTALL)


def _sudo_write(c: Context, path: Path, text: str) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".crt", delete=False) as f:
        f.write(text)
        tmp = f.name
    c.run(f"{util.SUDO} mkdir -p {path.parent} && {util.SUDO} install -m 0644 {tmp} {path} && rm {tmp}")


def _sudo_read(c: Context, path: Path) -> str | None:
    result = c.run(f"{util.SUDO} cat {path}", hide=True, warn=True)
    return result.stdout if result.ok else None


def _split_pem_certs(text: str) -> list[str]:
    return _CERT_RE.findall(text)


def _resolve_paths(bundle: str | None) -> list[Path]:
    """--bundle=path override, else the [certs] bundle field from ~/.config/power-user-linux-setup/identity.toml
    (a single string or a list). Empty if neither is configured.
    """
    if bundle:
        return [Path(bundle).expanduser()]
    raw = util.load_certs_override().get("bundle")
    if not raw:
        return []
    if isinstance(raw, str):
        return [Path(raw).expanduser()]
    return [Path(p).expanduser() for p in raw]


# ---------------------------------------------------------------------------
# Format detection/conversion — the extension is never trusted, only openssl's own parse result.


def _try_convert(c: Context, path: Path) -> str | None:
    """Detect the bundle's actual encoding by content and return it normalized to a clean,
    concatenated PEM (any header comments or openssl "subject=" banner lines stripped — only the
    BEGIN/END blocks survive). None if none of the four modes openssl understands apply. Tried in
    order: PEM passthrough, DER->PEM, PKCS#7(PEM)->PEM, PKCS#7(DER)->PEM — Windows AD Certificate
    Services commonly exports a .p7b in either PKCS#7 armor, so both are tried, not just one.
    """
    q = shlex.quote(str(path))
    raw = None

    if c.run(f"openssl x509 -in {q} -noout -inform PEM", hide=True, warn=True).ok:
        raw = path.read_text()
    else:
        result = c.run(f"openssl x509 -in {q} -inform DER -outform PEM", hide=True, warn=True)
        if result.ok and "-----BEGIN CERTIFICATE-----" in result.stdout:
            raw = result.stdout
        else:
            for inform in ("PEM", "DER"):
                result = c.run(f"openssl pkcs7 -in {q} -print_certs -inform {inform}", hide=True, warn=True)
                if result.ok and "-----BEGIN CERTIFICATE-----" in result.stdout:
                    raw = result.stdout
                    break

    if raw is None:
        return None
    certs = _split_pem_certs(raw)
    return "\n".join(certs) + "\n" if certs else None


def _convert_bundle(c: Context, path: Path) -> str:
    converted = _try_convert(c, path)
    if converted is None:
        raise RuntimeError(
            f"{path}: not recognized as PEM, DER, or PKCS#7 (.p7b) — tried all four openssl "
            f"modes. Inspect it manually: `file {path}` or `openssl asn1parse -in {path}`. "
            "Refusing to hand this to update-ca-certificates, which would otherwise silently "
            "skip it (a warning, not a failure) and leave TLS verification broken with no clear "
            "signal why."
        )
    return converted


def corporate_bundle_text(c: Context) -> str | None:
    """The configured corporate CA, normalized to PEM — or None when none is configured.

    Public because docker.py needs the same certificate for a different destination: docker doesn't
    read the OS trust store, so a corporate registry behind the same inspecting proxy needs its own
    /etc/docker/certs.d/<host>/ca.crt. One resolver, so the two can't disagree about which file is
    the corporate CA, or about how a .p7b becomes PEM.
    """
    paths = [p for p in _resolve_paths(None) if p.exists()]
    return "".join(_convert_bundle(c, path) for path in paths) if paths else None


def _desired_bundle_text(c: Context, paths: list[Path]) -> str:
    parts: list[str] = []
    for path in paths:
        if not path.exists():
            raise RuntimeError(f"{path}: configured bundle file not found")
        parts.append(f"# {path} (PULSE certs.install)\n{_convert_bundle(c, path)}")
    return "".join(parts)


# ---------------------------------------------------------------------------
# The Windows root store, from inside a WSL distro. WSL2's trust store is fully independent of
# Windows', so a root IT deployed by Group Policy/Intune is present on the host and absent here —
# see docs/certs.md's WSL section. tasks/netdoctor.py already crosses this boundary for the proxy
# half of the same problem (reg.exe, netsh.exe); this is the CA half.

_WINDOWS_ROOTS_PEM = util.PULSE_STATE_DIR / "windows-root-extras.pem"
_WINDOWS_STORES = ("Cert:\\LocalMachine\\Root", "Cert:\\CurrentUser\\Root")

# One `# <subject> [<thumbprint>]` line per certificate, then its PEM. The OutputEncoding line is
# first for a reason: a redirected PowerShell 5.1 stream otherwise emits the console's OEM codepage,
# which turns a non-ASCII subject into mojibake (the base64 itself is ASCII either way).
_PS_EXPORT_SCRIPT = (
    "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
    f"Get-ChildItem -Path {', '.join(_WINDOWS_STORES)} | ForEach-Object {{\n"
    '  "# $($_.Subject) [$($_.Thumbprint)]"\n'
    "  '-----BEGIN CERTIFICATE-----'\n"
    "  [Convert]::ToBase64String($_.RawData, [Base64FormattingOptions]::InsertLineBreaks)\n"
    "  '-----END CERTIFICATE-----'\n"
    "}\n"
)


def _encoded_command(script: str) -> str:
    """A PowerShell -EncodedCommand payload: UTF-16LE, then base64.

    Not a quoted -Command string. The script contains backslashes (`Cert:\\LocalMachine\\Root`),
    `$()` interpolation and both kinds of quote, and it would have to survive invoke's shell *and*
    PowerShell's own parser intact. Encoding removes the quoting question entirely, and leaves a
    pure function that can be tested without a Windows host to run it against.
    """
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


_ENCODED_EXPORT = _encoded_command(_PS_EXPORT_SCRIPT)


def _pem_fingerprint(pem: str) -> str | None:
    """The certificate's SHA-256 fingerprint — the same value `openssl x509 -fingerprint -sha256`
    prints, computed here because the fingerprint *is* the digest of the DER. The alternative is one
    openssl subprocess per certificate, and the system bundle holds ~140 of them. None if the block's
    body isn't valid base64.
    """
    body = "".join(line.strip() for line in pem.splitlines() if "-----" not in line)
    try:
        der = base64.b64decode(body, validate=True)
    except ValueError:  # binascii.Error subclasses it
        return None
    return hashlib.sha256(der).hexdigest().upper()


def _fingerprints(text: str) -> dict[str, str]:
    """Every PEM block in `text`, keyed by fingerprint. First occurrence wins — the two Windows
    stores overlap, and a root present in both is one certificate, not two."""
    found: dict[str, str] = {}
    for pem in _split_pem_certs(text):
        fingerprint = _pem_fingerprint(pem)
        if fingerprint:
            found.setdefault(fingerprint, pem)
    return found


def _windows_extra_roots(windows_export: str, system_bundle: str) -> list[str]:
    """The exported Windows roots this distro doesn't already trust, ordered by fingerprint.

    The Windows Root store carries ~50 public CAs alongside whatever the corporate one is, and
    installing all of them would add trust Debian's own ca-certificates deliberately doesn't carry.
    So the public set is subtracted rather than filtered by name — an issuer's common name is a
    label, not an identity.

    Sorted, not in enumeration order: `_desired_bundle_text` compares the assembled text against
    what's installed to decide whether to touch the trust store at all, and PowerShell makes no
    ordering promise, so an unsorted export would re-trigger update-ca-certificates on every run.
    """
    system = _fingerprints(system_bundle)
    extras = {fp: pem for fp, pem in _fingerprints(windows_export).items() if fp not in system}
    return [extras[fp] for fp in sorted(extras)]


def _windows_labels(export: str) -> dict[str, str]:
    """Each exported certificate's fingerprint mapped to the `# <subject> [<thumbprint>]` line above
    it, so the roots about to be trusted can be named on screen. A block with no label is kept with
    an empty one — the certificate still installs; only the report loses a name.
    """
    labels: dict[str, str] = {}
    label = ""
    block: list[str] = []
    for line in export.replace("\r\n", "\n").splitlines():
        if line.startswith("# "):
            label = line[2:].strip()
        elif line.startswith("-----BEGIN CERTIFICATE-----"):
            block = [line]
        elif block:
            block.append(line)
            if line.startswith("-----END CERTIFICATE-----"):
                fingerprint = _pem_fingerprint("\n".join(block))
                if fingerprint:
                    labels[fingerprint] = label
                block = []
    return labels


def _run_windows(args: list[str]) -> str | None:
    """Run a Windows-side executable through WSL interop. None on any failure — a distro with
    interop disabled, a PowerShell execution policy that refuses, a host that never answers.

    subprocess rather than c.run: the output needs `errors="replace"` (a subject line can carry
    anything) and the argv needs to reach PowerShell without a shell in between.
    """
    try:
        result = subprocess.run(args, capture_output=True, text=True, errors="replace", timeout=60, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def _export_windows_roots() -> Path | None:
    """Export the Windows root stores and keep only what this distro doesn't already trust, at a
    stable path so re-running is idempotent. None when there's nothing to add.
    """
    # Exit, not RuntimeError: both of these are "wrong machine for this flag", which is a message
    # to read, not a traceback to page through. The failure below is a different thing — something
    # answered and its answer was unusable — and keeps its stack.
    if not util.is_wsl():
        raise Exit(
            "[certs] --from-windows reads the Windows certificate store through WSL interop, and "
            "this isn't a WSL distro. Pass --bundle=path, or set [certs] bundle in identity.toml.",
            code=1,
        )
    if not util.command_exists("powershell.exe"):
        raise Exit(
            "[certs] powershell.exe not found — WSL interop is what makes the Windows side "
            "reachable. Check /etc/wsl.conf's [interop] enabled=true (see `inv wsl.check`), or "
            "copy the bundle over /mnt/c by hand and pass --bundle=path.",
            code=1,
        )

    export = _run_windows(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", _ENCODED_EXPORT])
    if export is None:
        raise RuntimeError(
            "powershell.exe returned no certificate data — the store may be empty, or an execution "
            "policy may have refused. Nothing was installed."
        )

    system_bundle = Path(_SYSTEM_BUNDLE)
    extras = _windows_extra_roots(export, system_bundle.read_text(errors="replace") if system_bundle.exists() else "")
    total = len(_split_pem_certs(export))
    if not extras:
        print(f"[certs] windows: {total} root(s) in the Windows store, all already trusted here — nothing to add")
        return None

    labels = _windows_labels(export)
    for pem in extras:
        print(f"[certs] windows: + {labels.get(_pem_fingerprint(pem) or '') or '<unnamed certificate>'}")
    if util.DRY_RUN:
        print(f"[certs] windows: would write {len(extras)} root(s) to {_WINDOWS_ROOTS_PEM}")
        return _WINDOWS_ROOTS_PEM if _WINDOWS_ROOTS_PEM.exists() else None

    _WINDOWS_ROOTS_PEM.parent.mkdir(parents=True, exist_ok=True)
    _WINDOWS_ROOTS_PEM.write_text("\n".join(extras) + "\n")
    print(f"[certs] windows: {len(extras)} of {total} root(s) not already trusted -> {_WINDOWS_ROOTS_PEM}")
    return _WINDOWS_ROOTS_PEM


# ---------------------------------------------------------------------------
# Java cacerts — purely conditional, never installs a JDK. See module docstring.


def _cacerts_path(c: Context) -> str | None:
    result = c.run("readlink -f $(command -v java)", hide=True, warn=True)
    if not result.ok or not result.stdout.strip():
        return None
    java_home = Path(result.stdout.strip()).parent.parent
    return str(java_home / "lib" / "security" / "cacerts")


def _keytool_alias_exists(c: Context, cacerts: str, alias: str) -> bool:
    return c.run(
        f"{util.SUDO} keytool -list -alias {alias} -keystore {shlex.quote(cacerts)} -storepass changeit",
        hide=True,
        warn=True,
    ).ok


def _java_status(c: Context) -> str:
    if not util.command_exists("keytool"):
        return "skip"
    cacerts = _cacerts_path(c)
    if not cacerts:
        return "MISSING"
    return util.ok_label(_keytool_alias_exists(c, cacerts, "pulse-corporate-0"))


def _configure_java(c: Context, desired: str) -> None:
    if not util.command_exists("keytool"):
        print(
            "[certs] java: no JDK found — skipping (this repo doesn't manage a JDK; activates "
            "automatically if one is added later, see docs/certs.md#java)"
        )
        return
    cacerts = _cacerts_path(c)
    if not cacerts:
        print("[certs] java: keytool found but JAVA_HOME could not be resolved — skipping")
        return

    certs = _split_pem_certs(desired)
    imported = 0
    for i, cert in enumerate(certs):
        alias = f"pulse-corporate-{i}"
        if _keytool_alias_exists(c, cacerts, alias):
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as f:
            f.write(cert)
            tmp = f.name
        c.run(
            f"{util.SUDO} keytool -importcert -noprompt -trustcacerts -alias {alias} "
            f"-file {tmp} -keystore {shlex.quote(cacerts)} -storepass changeit"
        )
        c.run(f"rm {tmp}")
        imported += 1
    if imported:
        print(f"[certs] java: imported {imported} cert(s) into {cacerts}")
    else:
        print(f"[certs] java: already up to date ({len(certs)} cert(s) in {cacerts})")


# ---------------------------------------------------------------------------
# ~/.zshenv env vars — unconditional (inert exports, no "wrong" state to guard against the way
# the Java import above must be gated on keytool actually existing before it acts).


def _env_block_content() -> str:
    return (
        f'export SSL_CERT_FILE="{_SYSTEM_BUNDLE}"\n'
        f'export REQUESTS_CA_BUNDLE="{_SYSTEM_BUNDLE}"\n'
        f'export NODE_EXTRA_CA_CERTS="{_SYSTEM_BUNDLE}"\n'
        f'export AWS_CA_BUNDLE="{_SYSTEM_BUNDLE}"\n'
    )


def _zshenv_status() -> str:
    text = ZSHENV.read_text() if ZSHENV.exists() else ""
    _, status = util.ensure_block_text(text, "certs", _env_block_content())
    return util.ok_label(status == util.BlockStatus.OK)


def _status(c: Context, paths: list[Path]) -> dict[str, str]:
    bundle_status = "MISSING"
    try:
        desired = _desired_bundle_text(c, paths)
        bundle_status = util.ok_label(_sudo_read(c, _CA_CERT_FILE) == desired)
    except RuntimeError as e:
        print(f"[certs] bundle format error: {e}")
    return {"bundle": bundle_status, "zshenv": _zshenv_status(), "java": _java_status(c)}


def _missing_source_message(command: str) -> str:
    return (
        "[certs] no corporate CA bundle configured — nothing to "
        f"{command}. If this network uses one, pass --bundle=path to `inv certs.install`, or add "
        "a [certs] bundle to ~/.config/power-user-linux-setup/identity.toml (see config/identity.toml.example)."
    )


# ---------------------------------------------------------------------------
# Tasks


def _require_bundle_paths(
    bundle: str | None, command: str, *, raise_on_missing: bool, from_windows: bool = False
) -> list[Path] | None:
    """Resolve and validate configured bundle paths, shared by check()/install(). Returns None
    (having already printed an explanatory message) if nothing is configured, or if a configured
    file is missing and raise_on_missing is False. Raises RuntimeError instead of returning None
    if a file is missing and raise_on_missing is True.

    --from-windows *adds* the exported Windows roots to whatever else is configured rather than
    replacing it: a machine can legitimately have both an IT-provided file and a root that only
    ever reached the Windows store."""
    paths = _resolve_paths(bundle)
    missing = [p for p in paths if not p.exists()]
    if missing:
        message = f"configured bundle file(s) not found: {', '.join(str(p) for p in missing)}"
        if raise_on_missing:
            raise RuntimeError(message)
        print(f"[certs] {message}")
        return None
    if from_windows and (exported := _export_windows_roots()):
        paths.append(exported)
    if not paths:
        print(_missing_source_message(command))
        return None
    return paths


@task
def check(c: Context, bundle: str | None = None, from_windows: bool = False):
    """Read-only diagnostic: bundle install status, ~/.zshenv env vars, Java cacerts. Never
    mutates. --bundle=path overrides the [certs] table in ~/.config/power-user-linux-setup/identity.toml.
    --from-windows reports which Windows-side roots this WSL distro doesn't trust yet. See
    docs/certs.md.
    """
    util.require_apt()
    paths = _require_bundle_paths(bundle, "check", raise_on_missing=False, from_windows=from_windows)
    if paths is None:
        return
    status = _status(c, paths)
    print(f"[certs] bundle:{status['bundle']}  zshenv:{status['zshenv']}  java:{status['java']}")


@task
def install(c: Context, bundle: str | None = None, from_windows: bool = False):
    """Install the corporate CA bundle into the OS trust store and export it for
    python/node/awscli. --bundle=path overrides the [certs] table in
    ~/.config/power-user-linux-setup/identity.toml. --from-windows (WSL only) additionally exports
    the Windows root store and installs whatever this distro doesn't already trust. See
    docs/certs.md.
    """
    util.ensure_sudo()  # standalone-safe: no sudo call inside c.run may prompt
    util.require_apt()
    if not util.command_exists("openssl"):
        raise RuntimeError("openssl not found — run `sudo apt install openssl` first")

    paths = _require_bundle_paths(bundle, "install", raise_on_missing=True, from_windows=from_windows)
    if paths is None:
        return

    if util.DRY_RUN:
        status = _status(c, paths)
        print(f"[certs] bundle:{status['bundle']}  zshenv:{status['zshenv']}  java:{status['java']}")
        return

    # Not wrapped in try/except: an unparseable bundle must raise loudly here, never be silently
    # skipped — see module docstring.
    desired = _desired_bundle_text(c, paths)

    if _sudo_read(c, _CA_CERT_FILE) == desired:
        print("[certs] bundle already up to date")
    else:
        _sudo_write(c, _CA_CERT_FILE, desired)
        result = c.run(f"{util.SUDO} update-ca-certificates", hide=True)
        # Only match a skip naming our own file — update-ca-certificates also prints a benign,
        # unrelated "skipping ca-certificates.crt, it does not contain exactly one certificate"
        # warning about its own merged *output* bundle on essentially every run (confirmed
        # against a real run while testing this task); a bare "skipping" substring check would
        # false-positive on that every single time.
        if re.search(rf"skipping[^\n]*{re.escape(_CA_CERT_FILE.stem)}", result.stdout + result.stderr, re.IGNORECASE):
            raise RuntimeError(
                f"update-ca-certificates skipped our bundle:\n{result.stdout}{result.stderr}\n"
                "This shouldn't happen — it was already format-validated above. Inspect "
                f"{_CA_CERT_FILE} manually."
            )
        print("[certs] bundle installed, update-ca-certificates run")

    zshenv_status = util.ensure_block(ZSHENV, "certs", _env_block_content())
    print(f"[certs] ~/.zshenv certs block: {zshenv_status.value}")

    _configure_java(c, desired)

    print("[certs] open a new terminal for the ~/.zshenv changes to take effect")
