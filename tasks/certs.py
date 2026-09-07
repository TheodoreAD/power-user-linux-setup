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
import os
import re
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from invoke import Context, Exit, task

from . import cert_sources, netdoctor, util

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


def _capture(args: list[str]) -> str | None:
    """Run a command and return its stdout, or None on any failure — a distro with interop
    disabled, a PowerShell execution policy that refuses, a host that never answers, a missing
    binary.

    subprocess rather than c.run: the output needs `errors="replace"` (a certificate subject or a
    registry value can carry anything) and the argv needs to reach PowerShell without a shell in
    between.
    """
    try:
        result = subprocess.run(args, capture_output=True, text=True, errors="replace", timeout=60, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def _windows_root_export() -> str | None:
    """The raw PowerShell export of both Windows root stores. None if interop couldn't produce it.
    Separate from the caller because `discover` reads the same text for a different purpose."""
    return _capture(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", _ENCODED_EXPORT])


def _policy_thumbprints() -> set[str]:
    """SHA-1 thumbprints of every root deployed by group policy or enterprise enrolment.

    This is the signal `--from-windows`'s fingerprint subtraction cannot produce: "absent from the
    public CA set" catches a corporate root and equally any other locally-added one, while a
    certificate in these stores was put there by IT, by construction.
    """
    found: set[str] = set()
    for key, _origin in cert_sources.POLICY_ROOT_KEYS:
        if output := _capture(["reg.exe", "query", key]):
            found |= cert_sources.parse_reg_thumbprints(output)
    return found


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

    export = _windows_root_export()
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
# Discovery: what this machine is already using, or being told to use. Parsing lives in
# tasks/cert_sources.py; this half is the I/O and the ranking. See docs/certs.md.

# /etc/environment first because it applies to every session, then the shell rc files in the order
# a login shell would read them. ~/.zshenv specifically is where this repo's own certs block goes,
# so a re-run sees what a previous install wrote and says so rather than proposing it again.
_ENV_FILES = ("/etc/environment", "~/.zshenv", "~/.zshrc", "~/.bashrc", "~/.profile")


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(errors="replace")
    except OSError:
        return None


def _env_findings() -> tuple[list[cert_sources.Candidate], list[cert_sources.Bypass]]:
    """This distro's own environment: the live shell, then the files that populate it."""
    candidates = cert_sources.env_candidates(os.environ, "this shell")
    bypasses = cert_sources.env_bypasses(os.environ, "this shell")
    for name in _ENV_FILES:
        path = Path(name).expanduser()
        text = _read_text(path) if path.is_file() else None
        if text is None:
            continue
        values = cert_sources.parse_env_assignments(text)
        candidates += cert_sources.env_candidates(values, str(path))
        bypasses += cert_sources.env_bypasses(values, str(path))
    return candidates, bypasses


def _config_findings() -> tuple[list[cert_sources.Candidate], list[cert_sources.Bypass]]:
    """Config files that name a certificate, or that turned verification off."""
    candidates: list[cert_sources.Candidate] = []
    bypasses: list[cert_sources.Bypass] = []
    for rule in cert_sources.CONFIG_RULES:
        path = Path(rule.relative) if rule.relative.startswith("/") else Path.home() / rule.relative
        text = _read_text(path) if path.is_file() else None
        if text is None:
            continue
        for value in cert_sources.scan_config_text(rule, text):
            if rule.kind is cert_sources.Kind.CERT:
                candidates.append(cert_sources.Candidate(value, f"{rule.label} in {path}", cert_sources.RANK_NAMED))
            else:
                bypasses.append(cert_sources.Bypass(rule.label, str(path), rule.fix))
    return candidates, bypasses


def _windows_env_findings() -> tuple[list[cert_sources.Candidate], list[cert_sources.Bypass]]:
    """The Windows side's own environment, read out of the registry.

    This is the route that pays under WSL: IT sets NODE_EXTRA_CA_CERTS or REQUESTS_CA_BUNDLE
    machine-wide for the Windows half of the laptop, nothing carries it across the boundary, and the
    value it holds is an exact path this distro can read through /mnt.
    """
    candidates: list[cert_sources.Candidate] = []
    bypasses: list[cert_sources.Bypass] = []
    for key, origin in cert_sources.WINDOWS_ENV_KEYS:
        output = _capture(["reg.exe", "query", key])
        if not output:
            continue
        values = cert_sources.parse_reg_values(output)
        candidates += cert_sources.env_candidates(values, origin)
        bypasses += cert_sources.env_bypasses(values, origin)
    return candidates, bypasses


def _vendor_findings() -> list[cert_sources.Candidate]:
    return [
        cert_sources.Candidate(str(match), f"{vendor} install directory", cert_sources.RANK_FOUND)
        for pattern, vendor in cert_sources.VENDOR_PEM_GLOBS
        for match in sorted(Path("/").glob(pattern.lstrip("/")))
    ]


def _local_path(value: str) -> Path | None:
    """A candidate's value as a path this distro can open, translating a Windows one. None when it
    doesn't resolve to an existing file — a stale config entry pointing at a deleted bundle is
    ordinary, and is exactly what makes an unchecked candidate list misleading."""
    translated = value
    if not value.startswith("/"):
        # wslpath knows this distro's real mount root, which /etc/wsl.conf can move; the pure
        # fallback assumes /mnt only when wslpath isn't there to ask.
        translated = (_capture(["wslpath", "-u", value]) or "").strip() or (
            cert_sources.windows_path_to_wsl(value) or ""
        )
    if not translated:
        return None
    path = Path(translated)
    return path if path.is_file() else None


def _windows_store_findings() -> list[tuple[str, bool]]:
    """Roots in the Windows stores this distro doesn't trust, each flagged with whether IT deployed
    it by policy. Empty outside WSL, or when interop can't answer."""
    export = _windows_root_export()
    if not export:
        return []
    system_bundle = Path(_SYSTEM_BUNDLE)
    extras = _windows_extra_roots(export, system_bundle.read_text(errors="replace") if system_bundle.exists() else "")
    labels = _windows_labels(export)
    policy = _policy_thumbprints()
    found: list[tuple[str, bool]] = []
    for pem in extras:
        label = labels.get(_pem_fingerprint(pem) or "", "")
        thumbprint = cert_sources.thumbprint_from_label(label)
        found.append((label or "<unnamed certificate>", bool(thumbprint and thumbprint in policy)))
    return found


def _report_wslenv() -> None:
    """Say when Windows shares a certificate variable across the boundary without translating it.

    `WSLENV`'s `/p` flag is what turns `C:\\corp\\root.pem` into a path this distro can open. Shared
    without it, the variable arrives set — so every tool reading it looks correct and every one of
    them fails to open the file, which reads as a broken certificate rather than a missing flag.
    """
    shared = cert_sources.parse_wslenv(os.environ.get("WSLENV", ""))
    for name, flags in shared.items():
        if name in cert_sources.CERT_ENV_VARS and "p" not in flags:
            print(f"[certs] {name} is shared through WSLENV without /p — its value stays a Windows path in here")


def _live_issuer() -> tuple[str, str | None, bool] | None:
    """Who signed the certificate this machine is served right now: (host, issuer, verified). None
    when the probe couldn't run at all.

    **`verified` is the half that matters, and the issuer name alone reads as interception when it
    is nothing of the kind** — netdoctor fills `tls_issuer` in either case, scanning the DER for the
    common name on success and re-reading the chain without verification on failure. So a clean
    connection to a public host reports its ordinary public CA. An issuer with `verified` false is
    the actionable one: something is re-signing traffic with a root this distro does not trust.
    """
    endpoints = netdoctor.endpoints_for("core")
    if not endpoints:
        return None
    endpoint = endpoints[0]
    probe = netdoctor.probe_endpoint(endpoint, netdoctor.DEFAULT_TIMEOUT)
    if not probe.tcp_ok:
        return None
    return endpoint.host, probe.tls_issuer, probe.tls_ok is not False


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


# What the block below exports, named for util.login_shell_warning — a bash login shell reads none
# of it, and nothing here writes a file bash does read (see docs/wsl.md, "Assumptions this repo
# makes about WSL"). Silent by construction: an unverified TLS chain looks like a network fault.
_CERT_EXPORTS = "SSL_CERT_FILE, REQUESTS_CA_BUNDLE, NODE_EXTRA_CA_CERTS and AWS_CA_BUNDLE"


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
    if note := util.login_shell_warning(_CERT_EXPORTS):
        print(f"[certs] {note}")


@dataclass(frozen=True)
class _Discovered:
    """One certificate this machine points at, after every place that named it has been merged.
    `path` is None when nothing at that value exists — a stale pointer, which is a finding of its
    own rather than a candidate to install."""

    value: str
    path: Path | None
    origins: tuple[str, ...]
    installable: bool


def _merge_candidates(candidates: list[cert_sources.Candidate]) -> list[_Discovered]:
    """Group candidates by the file they actually resolve to, so one certificate named by four
    tools is one row with four origins. Merging on the resolved path rather than the raw value is
    the point: `C:\\corp\\root.pem` and `/mnt/c/corp/root.pem` are the same file, and under WSL both
    spellings turn up in the same run."""
    merged: dict[str, _Discovered] = {}
    for candidate in candidates:
        path = _local_path(candidate.value)
        key = str(path) if path else candidate.value
        previous = merged.get(key)
        origins = (*previous.origins, candidate.origin) if previous else (candidate.origin,)
        installable = candidate.installable and (previous.installable if previous else True)
        merged[key] = _Discovered(candidate.value, path, origins, installable)
    return sorted(merged.values(), key=lambda found: (found.path is None, str(found.path or found.value)))


def _report_discovery(
    found: list[_Discovered], store: list[tuple[str, bool]], bypasses: list[cert_sources.Bypass]
) -> None:
    for item in found:
        where = ", ".join(item.origins)
        if item.path is None:
            print(f"[certs] named but missing: {item.value} — {where}")
        elif not item.installable:
            print(f"[certs] evidence (not a PEM): {item.path} — {where}")
        else:
            print(f"[certs] candidate: {item.path} — {where}")
    for label, by_policy in store:
        print(f"[certs] windows store: {label}" + ("  ← deployed by policy" if by_policy else ""))
    for bypass in bypasses:
        print(f"[certs] VERIFICATION OFF: {bypass.setting} in {bypass.origin} — fix: {bypass.fix}")
    if bypasses:
        print(
            "[certs] each of those turns off certificate checking for good and says nothing "
            "afterwards. Install the CA first, then undo them — in that order, or the tool that "
            "works today breaks and the bypass goes back permanently."
        )
    if not found and not store and not bypasses:
        print("[certs] nothing found — no environment variable, config file or store names a corporate CA here")


def _install_discovered(c: Context, found: list[_Discovered], store: list[tuple[str, bool]]) -> None:
    """Ask per certificate, then install what was accepted in one pass.

    Never installs without being told to, and defaults to no: adding a root CA means trusting
    whoever holds its private key for every TLS connection this machine makes, so it is a decision
    to put in front of somebody rather than a step to complete. `util.confirm` returns the default
    when stdin isn't a terminal, so a non-interactive run installs nothing.
    """
    # Ask first, authenticate second. `ensure_sudo` opens a GUI password dialog, and running it
    # ahead of the questions means a non-interactive run — where every confirm returns its default
    # of no — asks for a root password to then install nothing.
    paths = [
        item.path
        for item in found
        if item.path and item.installable and util.confirm(f"Trust {item.path} ({item.origins[0]})?", default=False)
    ]
    if (
        store
        and util.confirm(f"Trust the {len(store)} Windows-store root(s) listed above?", default=False)
        and (exported := _export_windows_roots())
    ):
        paths.append(exported)
    if not paths:
        print("[certs] nothing accepted — trust store unchanged")
        return

    util.ensure_sudo()  # standalone-safe: no sudo call inside c.run may prompt
    util.require_apt()
    if not util.command_exists("openssl"):
        raise RuntimeError("openssl not found — run `sudo apt install openssl` first")
    _install_bundle(c, paths)


@task(
    help={
        "install": (
            "Ask about each certificate found and install the ones you accept. Off by default: "
            "trusting a root CA is a decision, not a step."
        )
    }
)
def discover(c: Context, install: bool = False):
    """Find the corporate CA this machine already uses or is told to use, and report where TLS
    verification was switched off instead.

    Looks at environment variables (this distro's, and under WSL the Windows side's own, read from
    the registry), config files for npm/pip/git/curl/conda/JVM tooling, vendor install directories,
    and the Windows certificate store — flagging roots that group policy deployed, which is IT
    deployment read directly rather than guessed. Read-only unless --install. See docs/certs.md.
    """
    candidates, bypasses = _env_findings()
    config_candidates, config_bypasses = _config_findings()
    candidates += config_candidates
    bypasses += config_bypasses

    store: list[tuple[str, bool]] = []
    if util.is_wsl():
        windows_candidates, windows_bypasses = _windows_env_findings()
        candidates += windows_candidates + _vendor_findings()
        bypasses += windows_bypasses
        store = _windows_store_findings()
        _report_wslenv()

    found = _merge_candidates(candidates)
    if probed := _live_issuer():
        host, issuer, verified = probed
        signed_by = f" (signed by {issuer})" if issuer else ""
        if verified:
            print(f"[certs] live: {host} verifies against this machine's trust store{signed_by}")
        else:
            print(f"[certs] live: {host} does NOT verify here{signed_by} — that issuer is the root to install")

    _report_discovery(found, store, bypasses)
    if install and not util.DRY_RUN:
        _install_discovered(c, found, store)


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

    _install_bundle(c, paths)


def _install_bundle(c: Context, paths: list[Path]) -> None:
    """Convert, install into the OS trust store, export the env vars, import into Java. Shared by
    `install` and by `discover --install`, which resolves its paths a different way and then has
    exactly the same work to do."""
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

    # The block is written either way — it is correct, idempotent, and right for the moment the
    # shell changes. What is not said either way is "open a new terminal", which on bash would be
    # advice to go and watch nothing happen.
    if note := util.login_shell_warning(_CERT_EXPORTS):
        print(f"[certs] {note}")
    else:
        print("[certs] open a new terminal for the ~/.zshenv changes to take effect")
