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

import re
import shlex
import tempfile
from pathlib import Path

from invoke import task

from . import util

_CA_CERT_FILE = Path("/usr/local/share/ca-certificates/pulse-corporate.crt")
_SYSTEM_BUNDLE = "/etc/ssl/certs/ca-certificates.crt"  # what update-ca-certificates produces
_ZSHENV = Path.home() / ".zshenv"

_CERT_RE = re.compile(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", re.DOTALL)


def _sudo_write(c, path: Path, text: str) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".crt", delete=False) as f:
        f.write(text)
        tmp = f.name
    c.run(f"{util.SUDO} mkdir -p {path.parent} && {util.SUDO} cp {tmp} {path} && rm {tmp}")


def _sudo_read(c, path: Path) -> str | None:
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


def _try_convert(c, path: Path) -> str | None:
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


def _convert_bundle(c, path: Path) -> str:
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


def _desired_bundle_text(c, paths: list[Path]) -> str:
    parts = []
    for path in paths:
        if not path.exists():
            raise RuntimeError(f"{path}: configured bundle file not found")
        parts.append(f"# {path} (PULSE certs.install)\n{_convert_bundle(c, path)}")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Java cacerts — purely conditional, never installs a JDK. See module docstring.


def _cacerts_path(c) -> str | None:
    result = c.run("readlink -f $(command -v java)", hide=True, warn=True)
    if not result.ok or not result.stdout.strip():
        return None
    java_home = Path(result.stdout.strip()).parent.parent
    return str(java_home / "lib" / "security" / "cacerts")


def _keytool_alias_exists(c, cacerts: str, alias: str) -> bool:
    return c.run(
        f"{util.SUDO} keytool -list -alias {alias} -keystore {shlex.quote(cacerts)} -storepass changeit",
        hide=True,
        warn=True,
    ).ok


def _java_status(c) -> str:
    if not util.command_exists("keytool"):
        return "skip"
    cacerts = _cacerts_path(c)
    if not cacerts:
        return "MISSING"
    return util.ok_label(_keytool_alias_exists(c, cacerts, "pulse-corporate-0"))


def _configure_java(c, desired: str) -> None:
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
    text = _ZSHENV.read_text() if _ZSHENV.exists() else ""
    _, status = util.ensure_block_text(text, "certs", _env_block_content())
    return util.ok_label(status == util.BlockStatus.OK)


def _status(c, paths: list[Path]) -> dict[str, str]:
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


def _require_bundle_paths(bundle: str | None, command: str, *, raise_on_missing: bool) -> list[Path] | None:
    """Resolve and validate configured bundle paths, shared by check()/install(). Returns None
    (having already printed an explanatory message) if nothing is configured, or if a configured
    file is missing and raise_on_missing is False. Raises RuntimeError instead of returning None
    if a file is missing and raise_on_missing is True."""
    paths = _resolve_paths(bundle)
    if not paths:
        print(_missing_source_message(command))
        return None
    missing = [p for p in paths if not p.exists()]
    if missing:
        message = f"configured bundle file(s) not found: {', '.join(str(p) for p in missing)}"
        if raise_on_missing:
            raise RuntimeError(message)
        print(f"[certs] {message}")
        return None
    return paths


@task
def check(c, bundle=None):
    """Read-only diagnostic: bundle install status, ~/.zshenv env vars, Java cacerts. Never
    mutates. --bundle=path overrides the [certs] table in ~/.config/power-user-linux-setup/identity.toml. See
    docs/certs.md.
    """
    util.require_apt()
    paths = _require_bundle_paths(bundle, "check", raise_on_missing=False)
    if paths is None:
        return
    status = _status(c, paths)
    print(f"[certs] bundle:{status['bundle']}  zshenv:{status['zshenv']}  java:{status['java']}")


@task
def install(c, bundle=None):
    """Install the corporate CA bundle into the OS trust store and export it for
    python/node/awscli. --bundle=path overrides the [certs] table in
    ~/.config/power-user-linux-setup/identity.toml. See docs/certs.md.
    """
    util.require_apt()
    if not util.command_exists("openssl"):
        raise RuntimeError("openssl not found — run `sudo apt install openssl` first")

    paths = _require_bundle_paths(bundle, "install", raise_on_missing=True)
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

    zshenv_status = util.ensure_block(_ZSHENV, "certs", _env_block_content())
    print(f"[certs] ~/.zshenv certs block: {zshenv_status.value}")

    _configure_java(c, desired)

    print("[certs] open a new terminal for the ~/.zshenv changes to take effect")
