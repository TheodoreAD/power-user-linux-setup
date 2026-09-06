"""Where a corporate CA is already named on this machine — and where somebody switched TLS
verification off instead of installing one. Pure parsing for `inv certs.discover`; see docs/certs.md.

`certs.install --from-windows` answers "which roots exist on the Windows side that this distro does
not trust", which is a set ranked by nothing. The routes here answer a better question — *which
certificate is this machine already using, or being told to use* — and most of them name an exact
file rather than a candidate:

- an environment variable pointing at a bundle, read from this distro **and** from the Windows side,
  where IT sets it machine-wide in the registry;
- a config file naming one (npm, pip, git, curl, conda, a JVM trust store);
- verification switched off, which is the same discovery arriving as a workaround somebody applied
  instead — the most useful thing this module finds, because nothing else will ever mention it again;
- roots deployed by group policy, which is IT deployment read directly rather than inferred from
  what the public CA set happens to lack.

Everything here is a pure function over text, so a corporate machine's registry output, npmrc or
PowerShell export is a literal in a unit test. Nothing in this module runs a command or reads a file.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

# How direct the evidence is. A file somebody has already pointed a tool at beats a root that merely
# exists in a store, which beats a file found by guessing at vendor install paths.
RANK_NAMED = 3
RANK_DEPLOYED = 2
RANK_FOUND = 1


class Kind(StrEnum):
    """What a config-file match means — the same file can carry both."""

    CERT = "cert"
    BYPASS = "bypass"


@dataclass(frozen=True)
class Candidate:
    """A certificate this machine is already pointed at, or one that exists where a corporate CA
    would be. `value` is as found — possibly a Windows path, translated later."""

    value: str
    origin: str
    rank: int
    # A JVM trust store is a JKS/PKCS12, not a PEM, so openssl cannot convert it and the installer
    # would refuse it loudly. It still says *which* CA this machine trusts, which is worth printing.
    installable: bool = True


@dataclass(frozen=True)
class Bypass:
    """TLS verification switched off somewhere, and how to switch it back on."""

    setting: str
    origin: str
    fix: str


# ---------------------------------------------------------------------------
# Environment variables

CERT_ENV_VARS = (
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "CURL_CA_BUNDLE",
    "REQUESTS_CA_BUNDLE",
    "PIP_CERT",
    "HTTPLIB2_CA_CERTS",
    "NODE_EXTRA_CA_CERTS",
    "NPM_CONFIG_CAFILE",
    "GIT_SSL_CAINFO",
    "GIT_SSL_CAPATH",
    "AWS_CA_BUNDLE",
    "AZURE_CLI_CA_BUNDLE",
    "CARGO_HTTP_CAINFO",
    "DENO_CERT",
)

# A JVM takes its trust store as a system property inside one of these, not as a variable of its own.
JVM_OPTION_VARS = ("JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "MAVEN_OPTS", "GRADLE_OPTS", "SBT_OPTS")
_TRUSTSTORE_RE = re.compile(r"-Djavax\.net\.ssl\.trustStore=([^\s\"]+)")

_FALSEY = frozenset({"", "0", "false", "no", "off"})


def env_candidates(environ: Mapping[str, str], origin: str) -> list[Candidate]:
    """Every certificate path named by an environment variable in `environ`.

    This is the strongest signal the discovery has: somebody — IT, or a colleague's setup script —
    has already decided this file is the corporate CA, so there is no guessing about which of
    several roots matters. All this task has to do is put it where the OS trust store can see it.
    """
    found = [
        Candidate(value.strip(), f"{name} ({origin})", RANK_NAMED)
        for name in CERT_ENV_VARS
        if (value := environ.get(name, "")).strip()
    ]
    found += [
        Candidate(match.group(1), f"{name} -Djavax.net.ssl.trustStore ({origin})", RANK_NAMED, installable=False)
        for name in JVM_OPTION_VARS
        for match in _TRUSTSTORE_RE.finditer(environ.get(name, ""))
    ]
    return found


def env_bypasses(environ: Mapping[str, str], origin: str) -> list[Bypass]:
    """Verification switched off through the environment.

    Each of these is somebody who hit exactly the problem this task solves and turned the check off
    instead of installing the CA. It is silent from then on — no tool warns that it is not verifying
    — which is why finding them is worth as much as finding the certificate.
    """
    found: list[Bypass] = []
    if environ.get("GIT_SSL_NO_VERIFY", "").strip().lower() not in _FALSEY:
        found.append(Bypass("GIT_SSL_NO_VERIFY", origin, "unset it — git verifies again once the CA is installed"))
    if environ.get("NODE_TLS_REJECT_UNAUTHORIZED", "").strip() == "0":
        found.append(Bypass("NODE_TLS_REJECT_UNAUTHORIZED=0", origin, "unset it, or set it to 1"))
    if environ.get("PYTHONHTTPSVERIFY", "").strip() == "0":
        found.append(Bypass("PYTHONHTTPSVERIFY=0", origin, "unset it, or set it to 1"))
    return found


_ENV_LINE_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


def parse_env_assignments(text: str) -> dict[str, str]:
    """`KEY=value` lines from /etc/environment or a shell rc, quotes stripped, comments ignored.

    `export` is accepted so one parser covers both — /etc/environment has no `export` and a shell rc
    almost always does, and the two files are read in the same pass.
    """
    values: dict[str, str] = {}
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        match = _ENV_LINE_RE.match(line)
        if match:
            values[match.group(1)] = match.group(2).strip("\"'")
    return values


# ---------------------------------------------------------------------------
# The Windows side, read through WSL interop

# Where IT sets a variable machine-wide, and where the user's own live. A value here is what every
# Windows-side tool sees, and it names a file this distro can read through /mnt.
WINDOWS_ENV_KEYS = (
    (r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment", "Windows machine environment"),
    (r"HKCU\Environment", "Windows user environment"),
)

# Roots deployed by group policy and by enterprise enrolment sit in their own physical stores, and
# each subkey name under these is the certificate's SHA-1 thumbprint. Reading the registry rather
# than `certutil -grouppolicy -store Root` on purpose: certutil's output is localized, and a parser
# for it would work on an English machine and quietly find nothing on a German one.
POLICY_ROOT_KEYS = (
    (r"HKLM\SOFTWARE\Policies\Microsoft\SystemCertificates\Root\Certificates", "group policy"),
    (r"HKLM\SOFTWARE\Microsoft\EnterpriseCertificates\Root\Certificates", "enterprise enrolment"),
)

_REG_VALUE_RE = re.compile(r"^\s{4,}(\S+)\s+REG_(?:SZ|EXPAND_SZ)\s+(.*?)\s*$")
_REG_THUMBPRINT_RE = re.compile(r"\\Certificates\\([0-9A-Fa-f]{40})\s*$")


def parse_reg_values(reg_output: str) -> dict[str, str]:
    """`reg.exe query <key>` output — value names to values, CRLF and all."""
    values: dict[str, str] = {}
    for line in reg_output.replace("\r\n", "\n").splitlines():
        match = _REG_VALUE_RE.match(line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


def parse_reg_thumbprints(reg_output: str) -> set[str]:
    """The SHA-1 thumbprints of the certificates in a `reg.exe query <store key>` listing.

    The subkey name *is* the thumbprint, so nothing has to parse a certificate blob or survive a
    localized certutil banner — and this is the one signal that says "IT deployed this" outright
    rather than inferring it from the public CA set's absence.
    """
    return {
        match.group(1).upper()
        for line in reg_output.replace("\r\n", "\n").splitlines()
        if (match := _REG_THUMBPRINT_RE.search(line))
    }


_WINDOWS_PATH_RE = re.compile(r"^([A-Za-z]):[\\/](.*)$")


def windows_path_to_wsl(value: str) -> str | None:
    """`C:\\ProgramData\\corp\\root.pem` -> `/mnt/c/ProgramData/corp/root.pem`. None if `value` is
    not a drive-letter path — an already-translated `/mnt/c/...` needs no conversion, and a UNC path
    is not reachable this way at all.

    A fallback for `wslpath`, not a replacement: `wslpath -u` knows this distro's actual mount root,
    which is configurable in /etc/wsl.conf and is not always /mnt.
    """
    match = _WINDOWS_PATH_RE.match(value.strip().strip('"'))
    if not match:
        return None
    return f"/mnt/{match.group(1).lower()}/" + match.group(2).replace("\\", "/")


_WSLENV_ENTRY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(?:/([a-zA-Z]*))?$")


def parse_wslenv(value: str) -> dict[str, str]:
    """`WSLENV` — which variables Windows shares with this distro, and their flags.

    Worth reading in the same pass as the registry: a variable listed here with `/p` arrives already
    path-translated, so IT setting `NODE_EXTRA_CA_CERTS/p` means the certificate is *meant* to be
    visible in here and something else is wrong. Without the flag, the value in this distro is still
    a `C:\\` path and every Linux tool reading it fails to open it.
    """
    shared: dict[str, str] = {}
    for entry in value.split(":"):
        match = _WSLENV_ENTRY_RE.match(entry.strip())
        if match:
            shared[match.group(1)] = match.group(2) or ""
    return shared


# Vendor drop paths, and the asymmetry worth knowing: Netskope's client writes a readable PEM, while
# Zscaler's client connector injects into the Windows certificate store and documents no fixed file
# — so for Zscaler the store and the live issuer are the only routes, and hunting for a file is a
# waste of time rather than a search that failed.
VENDOR_PEM_GLOBS = (
    ("/mnt/c/ProgramData/netskope/stagent/data/nscacert*.pem", "Netskope client"),
    ("/mnt/c/ProgramData/Netskope/STAgent/data/nscacert*.pem", "Netskope client"),
)


def thumbprint_from_label(label: str) -> str | None:
    """The `[<thumbprint>]` half of an exported root's `# <subject> [<thumbprint>]` line."""
    match = re.search(r"\[([0-9A-Fa-f]{40})\]", label)
    return match.group(1).upper() if match else None


# ---------------------------------------------------------------------------
# Config files


@dataclass(frozen=True)
class ConfigRule:
    """One thing worth finding in one config file. `relative` is under $HOME unless it starts with
    a slash; `pattern`'s first group is the value to report."""

    relative: str
    label: str
    pattern: re.Pattern[str]
    kind: Kind
    fix: str = ""


_PATHY = r"([^\s\"';]+)"

CONFIG_RULES = (
    ConfigRule(".npmrc", "npm cafile", re.compile(rf"^\s*cafile\s*=\s*{_PATHY}", re.MULTILINE), Kind.CERT),
    ConfigRule(
        ".npmrc",
        "npm strict-ssl=false",
        re.compile(r"^\s*strict-ssl\s*=\s*(false)\b", re.MULTILINE | re.IGNORECASE),
        Kind.BYPASS,
        "npm config delete strict-ssl",
    ),
    ConfigRule(".config/pip/pip.conf", "pip cert", re.compile(rf"^\s*cert\s*=\s*{_PATHY}", re.MULTILINE), Kind.CERT),
    ConfigRule(
        ".config/pip/pip.conf",
        "pip trusted-host",
        re.compile(rf"^\s*trusted-host\s*=\s*{_PATHY}", re.MULTILINE),
        Kind.BYPASS,
        "remove trusted-host from ~/.config/pip/pip.conf",
    ),
    ConfigRule(".pip/pip.conf", "pip cert", re.compile(rf"^\s*cert\s*=\s*{_PATHY}", re.MULTILINE), Kind.CERT),
    ConfigRule(
        ".gitconfig",
        "git http.sslCAInfo",
        re.compile(rf"^\s*sslCAInfo\s*=\s*{_PATHY}", re.MULTILINE | re.IGNORECASE),
        Kind.CERT,
    ),
    ConfigRule(
        ".gitconfig",
        "git http.sslVerify=false",
        re.compile(r"^\s*sslVerify\s*=\s*(false)\b", re.MULTILINE | re.IGNORECASE),
        Kind.BYPASS,
        "git config --global --unset http.sslVerify",
    ),
    ConfigRule(".curlrc", "curl cacert", re.compile(rf"^\s*cacert\s*[= ]\s*\"?{_PATHY}", re.MULTILINE), Kind.CERT),
    ConfigRule(
        ".curlrc",
        "curl insecure",
        re.compile(r"^\s*(-k|--insecure)\s*$", re.MULTILINE),
        Kind.BYPASS,
        "remove the insecure line from ~/.curlrc",
    ),
    # conda's one key is both: a path means a CA, `false` means the check is off.
    ConfigRule(
        ".condarc",
        "conda ssl_verify",
        re.compile(r"^\s*ssl_verify\s*:\s*([^\s#]*[/\\][^\s#]*)", re.MULTILINE),
        Kind.CERT,
    ),
    ConfigRule(
        ".condarc",
        "conda ssl_verify: false",
        re.compile(r"^\s*ssl_verify\s*:\s*(false)\b", re.MULTILINE | re.IGNORECASE),
        Kind.BYPASS,
        "set ssl_verify back to true in ~/.condarc",
    ),
    ConfigRule(
        "gradle.properties",
        "gradle trustStore",
        re.compile(rf"^\s*systemProp\.javax\.net\.ssl\.trustStore\s*=\s*{_PATHY}", re.MULTILINE),
        Kind.CERT,
    ),
)


def scan_config_text(rule: ConfigRule, text: str) -> list[str]:
    """Every value `rule` finds in `text`. Empty when the file says nothing about certificates,
    which is the common case and is why this returns a list rather than raising."""
    return [match.group(1) for match in rule.pattern.finditer(text)]
