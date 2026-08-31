"""What this machine's network will and won't let a setup run do — and what to do about it.

Run it with nothing installed:

    python3 tasks/netdoctor.py            # human-readable report
    python3 tasks/netdoctor.py --json     # the same findings, machine-readable

or from the invoke side, once there is one, as `inv net.check` (tasks/net.py).

**Standard library only, and Python 3.10 syntax only.** That is a hard constraint, not a style
preference: this has to run on a fresh Ubuntu 22.04 WSL distro *before* uv, invoke, or this repo's
venv exist — which is exactly when a corporate network's blocks are worth knowing about, since
every one of those is itself a download. 22.04 ships Python 3.10, so no `tomllib` (3.11), no
`StrEnum`, no `datetime.UTC`. It also imports nothing from `tasks/`: `python3 tasks/netdoctor.py`
executes this file directly, without importing the `tasks` package (which would pull in invoke).
The dependency runs one way — `tasks/*.py` may import this module, never the reverse.

The question it answers is deliberately narrower than "is the internet up". It is: *which of the
specific hosts a PULSE run needs are reachable, by which route, and when one isn't, what is the
next command to type.* A corporate network that blocks pypi.org while allowing github.com is
completely ordinary — the sanctioned path is an internal mirror — and until something asks that
question per host, the symptom is a download failing somewhere deep inside `uv tool install`.
"""

from __future__ import annotations

import argparse
import configparser
import contextlib
import http.client
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import TypeAlias, cast

# ---------------------------------------------------------------------------
# The catalog: hosts a PULSE run actually needs, and what breaks without each
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Endpoint:
    host: str
    port: int
    # What stops working when this host is unreachable, in the user's terms.
    needed_for: str
    # `core` endpoints are probed by --quick and gate the summary verdict; `extra` ones are
    # probed by a full run and only ever produce warnings.
    tier: str = "core"
    path: str = "/"


ENDPOINTS: tuple[Endpoint, ...] = (
    Endpoint("pypi.org", 443, "every `uv tool install` / `pip install` (the index itself)", path="/simple/"),
    Endpoint("files.pythonhosted.org", 443, "every `uv tool install` / `pip install` (the wheels)"),
    Endpoint("astral.sh", 443, "bootstrap.sh's uv installer"),
    Endpoint("github.com", 443, "uv's managed Pythons, every deb-github package, git clones"),
    Endpoint("objects.githubusercontent.com", 443, "the actual bytes of a GitHub release asset"),
    Endpoint("raw.githubusercontent.com", 443, "install scripts fetched by the `script` method"),
    Endpoint("archive.ubuntu.com", 80, "apt — every `apt` and `apt-repo` package"),
    Endpoint("security.ubuntu.com", 80, "apt security updates"),
    Endpoint("registry.npmjs.org", 443, "npm/nvm packages", tier="extra"),
    Endpoint("nodejs.org", 443, "nvm's Node.js downloads", tier="extra"),
    Endpoint("download.docker.com", 443, "the Docker apt repo", tier="extra"),
    Endpoint("packages.microsoft.com", 443, "the VS Code / Edge apt repos", tier="extra"),
)

# Anything in setup.toml that isn't in the catalog above is still worth probing on a full run.
# Regex rather than a TOML parse on purpose — see the module docstring's 3.10 constraint.
_URL_RE = re.compile(r"https?://([A-Za-z0-9.-]+\.[A-Za-z]{2,})(?::(\d+))?")

DEFAULT_TIMEOUT = 4.0

# A JSON document. Spelled with `TypeAlias` and a string body because the alias is recursive, and
# because PEP 695's `type` statement is newer than this module's Python floor.
Json: TypeAlias = "dict[str, Json] | list[Json] | str | int | float | bool | None"
JsonObject: TypeAlias = "dict[str, Json]"


# ---------------------------------------------------------------------------
# Results and findings
# ---------------------------------------------------------------------------

# Ordered worst-first; the summary verdict is the worst severity present.
BLOCKER = "blocker"
WARNING = "warning"
INFO = "info"
_SEVERITY_ORDER = (BLOCKER, WARNING, INFO)


@dataclass
class Probe:
    """One endpoint, seen from here."""

    endpoint: Endpoint
    resolved: list[str] = field(default_factory=list)
    dns_error: str | None = None
    tcp_ok: bool = False
    tcp_error: str | None = None
    tls_ok: bool | None = None
    tls_error: str | None = None
    tls_issuer: str | None = None
    http_status: int | None = None
    via_proxy: str | None = None
    server_date: float | None = None
    seconds: float = 0.0

    @property
    def ok(self) -> bool:
        return self.tcp_ok and self.tls_ok is not False

    @property
    def summary(self) -> str:
        if self.dns_error:
            return f"DNS: {self.dns_error}"
        if not self.tcp_ok:
            return f"TCP: {self.tcp_error}"
        if self.tls_ok is False:
            return f"TLS: {self.tls_error}"
        if self.http_status is not None:
            return f"HTTP {self.http_status}" + (f" via {self.via_proxy}" if self.via_proxy else "")
        return "reachable" + (f" via {self.via_proxy}" if self.via_proxy else "")


@dataclass
class Finding:
    """Something that is wrong, why we think so, and the next command to type. `fix` is the part
    that matters — a diagnosis nobody can act on is just a longer error message."""

    severity: str
    title: str
    detail: str
    fix: list[str] = field(default_factory=list)

    def as_dict(self) -> JsonObject:
        return {
            "severity": self.severity,
            "title": self.title,
            "detail": self.detail,
            "fix": list(self.fix),
        }


# ---------------------------------------------------------------------------
# Primitives: DNS, TCP, TLS, HTTP, proxies
# ---------------------------------------------------------------------------


def dns_query_packet(hostname: str, query_id: int) -> bytes:
    """A minimal DNS A-record query — 12-byte header, then the QNAME as length-prefixed labels.

    Hand-built because the whole point is to ask *one named server* whether it answers, which
    getaddrinfo() can't express: it consults the resolver stack, so a "yes" from it says nothing
    about which server replied. Originally written in tasks/wsl.py; it lives here now so the
    zero-install entrypoint has it too, and wsl.py imports it back.
    """
    header = query_id.to_bytes(2, "big") + b"\x01\x00" + b"\x00\x01" + b"\x00\x00" * 3
    qname = b"".join(bytes([len(part)]) + part.encode() for part in hostname.split(".")) + b"\x00"
    return header + qname + b"\x00\x01\x00\x01"


def query_dns_server(server: str, hostname: str = "archive.ubuntu.com", timeout: float = 2.0) -> bool:
    """True if `server` answers a UDP/53 query for `hostname` at all."""
    query_id = os.getpid() & 0xFFFF
    packet = dns_query_packet(hostname, query_id)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(packet, (server, 53))
            data = sock.recvfrom(512)[0]  # sender address discarded (typeshed types it loosely)
    except OSError:
        return False
    # Any well-formed response counts, NXDOMAIN included: the question is whether the path to
    # that resolver is open at all, not whether the name exists. A timeout or a connection error
    # is the corporate-VPN/firewall signature this is looking for.
    return len(data) >= 2 and data[:2] == packet[:2]


def _resolve(host: str, timeout: float) -> tuple[list[str], str | None]:
    socket.setdefaulttimeout(timeout)
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        return [], f"{exc.strerror or exc}"
    except OSError as exc:  # pragma: no cover — defensive
        return [], str(exc)
    seen: list[str] = []
    for info in infos:
        addr = str(info[4][0])
        if addr not in seen:
            seen.append(addr)
    return seen, None


def _der_common_names(der: bytes) -> list[str]:
    """Every commonName in a DER certificate, in encoding order (issuer's come before the
    subject's in a TBSCertificate).

    A deliberate small hack instead of a real X.509 parse: `ssl` only hands back a parsed dict for
    a certificate it *validated*, and the interesting case here is precisely the one that failed
    validation. Rather than add a dependency (`cryptography`) this scans for the commonName OID
    (2.5.4.3, DER `06 03 55 04 03`) and reads the string that follows it. Good enough to answer
    "who signed this, if not a public CA" — which is the only question asked of it.
    """
    names: list[str] = []
    needle = b"\x06\x03\x55\x04\x03"
    index = der.find(needle)
    while index != -1:
        pos = index + len(needle)
        if pos + 2 <= len(der):
            length = der[pos + 1]
            value = der[pos + 2 : pos + 2 + length]
            try:
                text = value.decode("utf-8")
            except UnicodeDecodeError:
                text = ""
            if text and text.isprintable():
                names.append(text)
        index = der.find(needle, index + 1)
    return names


def _connect(host: str, port: int, timeout: float) -> socket.socket:
    return socket.create_connection((host, port), timeout=timeout)


def _proxy_tunnel(proxy: tuple[str, int], host: str, port: int, timeout: float) -> tuple[socket.socket, int, list[str]]:
    """CONNECT through an HTTP proxy. Returns the socket, the CONNECT status code, and the auth
    schemes the proxy offered on a 407 (RFC 7235 allows one comma-joined header or one per
    scheme; both shapes are handled). No credentials are ever sent — this only asks what the
    proxy wants."""
    sock = _connect(proxy[0], proxy[1], timeout)
    request = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n"
    sock.sendall(request.encode())
    raw = b""
    sock.settimeout(timeout)
    while b"\r\n\r\n" not in raw and len(raw) < 8192:
        chunk = sock.recv(1024)
        if not chunk:
            break
        raw += chunk
    text = raw.decode("latin-1", "replace")
    status_match = re.match(r"HTTP/\d\.\d\s+(\d{3})", text)
    status = int(status_match.group(1)) if status_match else 0
    schemes: list[str] = []
    for line in text.splitlines():
        header = re.match(r"(?i)proxy-authenticate:\s*(.+)", line)
        if not header:
            continue
        for part in header.group(1).split(","):
            token = part.strip().split(" ")[0].strip()
            if token and token not in schemes:
                schemes.append(token)
    return sock, status, schemes


def probe_endpoint(endpoint: Endpoint, timeout: float, proxy: tuple[str, int] | None = None) -> Probe:
    """DNS → TCP → TLS → HTTP for one endpoint, stopping at the first failure.

    When a proxy is configured, the connection is made through it and the *proxy's* name is what
    DNS has to resolve — so a direct-DNS failure for the target host is expected and not reported
    as the problem.
    """
    probe = Probe(endpoint=endpoint)
    started = time.monotonic()
    target = proxy or (endpoint.host, endpoint.port)
    if proxy:
        probe.via_proxy = f"{proxy[0]}:{proxy[1]}"

    probe.resolved, probe.dns_error = _resolve(target[0], timeout)
    if probe.dns_error:
        probe.seconds = time.monotonic() - started
        return probe

    sock: socket.socket | None = None
    try:
        if proxy and endpoint.port == 443:
            sock, status, schemes = _proxy_tunnel(proxy, endpoint.host, endpoint.port, timeout)
            probe.tcp_ok = status == 200
            if status != 200:
                offered = f" (offers {', '.join(schemes)})" if schemes else ""
                probe.tcp_error = f"proxy answered {status} to CONNECT{offered}"
                return probe
        else:
            sock = _connect(target[0], target[1], timeout)
            probe.tcp_ok = True
    except OSError as exc:
        probe.tcp_error = f"{type(exc).__name__}: {exc}"
        probe.seconds = time.monotonic() - started
        return probe
    finally:
        probe.seconds = time.monotonic() - started

    try:
        if endpoint.port == 443:
            context = ssl.create_default_context()
            try:
                with context.wrap_socket(sock, server_hostname=endpoint.host) as tls:
                    probe.tls_ok = True
                    der = tls.getpeercert(True)
                    names = _der_common_names(der) if der else []
                    probe.tls_issuer = names[0] if names else None
                    probe.http_status, probe.server_date = _http_head(tls, endpoint)
            except ssl.SSLError as exc:
                probe.tls_ok = False
                probe.tls_error = getattr(exc, "reason", None) or str(exc)
                probe.tls_issuer = _issuer_without_verification(endpoint, timeout, proxy)
            except OSError as exc:
                probe.tls_ok = False
                probe.tls_error = f"{type(exc).__name__}: {exc}"
        else:
            probe.http_status, probe.server_date = _http_head(sock, endpoint, via_proxy=proxy is not None)
            if probe.http_status == 407:
                probe.tcp_ok = False
                probe.tcp_error = "proxy answered 407 to a plain HTTP request"
    finally:
        with contextlib.suppress(OSError):  # already closed by the TLS wrapper
            sock.close()
        probe.seconds = time.monotonic() - started
    return probe


def _http_head(sock: socket.socket, endpoint: Endpoint, via_proxy: bool = False) -> tuple[int | None, float | None]:
    """A HEAD request on an already-connected socket, for the status code and the Date header
    (which is also the only clock reference available without trusting anything local).

    A proxy is spoken to in absolute form (`HEAD http://host/path`) — origin form is what makes a
    proxy answer about *itself* instead of the target, which reads as a working endpoint when
    nothing was actually fetched.
    """
    try:
        target = f"http://{endpoint.host}{endpoint.path}" if via_proxy else endpoint.path
        request = (
            f"HEAD {target} HTTP/1.1\r\nHost: {endpoint.host}\r\n"
            "User-Agent: pulse-netdoctor\r\nConnection: close\r\n\r\n"
        )
        sock.sendall(request.encode())
        raw = b""
        while b"\r\n\r\n" not in raw and len(raw) < 16384:
            chunk = sock.recv(2048)
            if not chunk:
                break
            raw += chunk
    except OSError:
        return None, None
    text = raw.decode("latin-1", "replace")
    status_match = re.match(r"HTTP/\d\.\d\s+(\d{3})", text)
    status = int(status_match.group(1)) if status_match else None
    date_value: float | None = None
    date_match = re.search(r"(?im)^date:\s*(.+)$", text)
    if date_match:
        try:
            date_value = parsedate_to_datetime(date_match.group(1).strip()).timestamp()
        except (TypeError, ValueError):
            date_value = None
    return status, date_value


def _issuer_without_verification(endpoint: Endpoint, timeout: float, proxy: tuple[str, int] | None) -> str | None:
    """Who signed the certificate we were just given, when it failed to verify. That name is the
    whole diagnosis: a corporate root here means TLS interception, not a broken server."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        if proxy and endpoint.port == 443:
            sock, status, _ = _proxy_tunnel(proxy, endpoint.host, endpoint.port, timeout)
            if status != 200:
                sock.close()
                return None
        else:
            sock = _connect(endpoint.host, endpoint.port, timeout)
        with context.wrap_socket(sock, server_hostname=endpoint.host) as tls:
            der = tls.getpeercert(True)
    except OSError:
        return None
    names = _der_common_names(der) if der else []
    return names[0] if names else None


# ---------------------------------------------------------------------------
# What this machine already believes about proxies, indexes, DNS and CAs
# ---------------------------------------------------------------------------

_PROXY_VARS = ("https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY")


def split_host_port(value: str, default_port: int = 80) -> tuple[str, int] | None:
    """host/port out of a proxy URL, tolerating a scheme and a userinfo prefix. The credential in
    a `http://user:pass@host:port` value is deliberately parsed off and dropped — this module
    never reads, stores or prints one."""
    match = re.match(r"^(?:[a-z][a-z0-9+.\-]*://)?(?:[^@/]+@)?([^:/\s]+)(?::(\d+))?", value.strip(), re.IGNORECASE)
    if not match or not match.group(1):
        return None
    return match.group(1), int(match.group(2)) if match.group(2) else default_port


def _read(path: str | Path) -> str:
    try:
        return Path(path).expanduser().read_text(errors="replace")
    except OSError:
        return ""


def _run(argv: list[str], timeout: float = 5.0) -> str:
    """A command whose absence or failure is an expected answer, not an error."""
    if not shutil.which(argv[0]):
        return ""
    try:
        result = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.decode("utf-8", "replace")


@dataclass
class Facts:
    """Everything read off the machine, before any judgement is applied to it."""

    is_wsl: bool = False
    is_container: bool = False
    distro: str = ""
    python: str = ""
    env_proxy: dict[str, str] = field(default_factory=dict)
    etc_environment_proxy: dict[str, str] = field(default_factory=dict)
    apt_proxy: list[str] = field(default_factory=list)
    pip_index: str | None = None
    uv_index: str | None = None
    npm_registry: str | None = None
    git_proxy: str | None = None
    nameservers: list[str] = field(default_factory=list)
    resolv_conf_kind: str = ""
    extra_ca_files: list[str] = field(default_factory=list)
    ca_env: dict[str, str] = field(default_factory=dict)
    wsl_conf: dict[str, str] = field(default_factory=dict)
    wslconfig: dict[str, str] = field(default_factory=dict)
    wslconfig_path: str | None = None
    windows_proxy: str | None = None
    windows_pac: str | None = None
    pac_proxies: list[str] = field(default_factory=list)

    def as_dict(self) -> JsonObject:
        """Only what was actually found: an empty value here means "nothing configured", and a
        report full of nulls hides the handful of lines that matter."""
        readable: JsonObject = {}
        for key in sorted(self.__dataclass_fields__):
            value = cast(Json, getattr(self, key))
            if value not in (None, "", [], {}) or key == "is_wsl":
                readable[key] = value
        return readable


def _ini_values(text: str) -> dict[str, str]:
    """Flatten an INI file to `section.key` → value. `/etc/wsl.conf` and `.wslconfig` are both
    this shape, and both are small enough that flattening loses nothing."""
    parser = configparser.ConfigParser(strict=False)
    values: dict[str, str] = {}
    try:
        parser.read_string(text)
    except configparser.Error:
        return values
    sections: list[str] = parser.sections()
    for section in sections:
        for key, value in parser.items(section):
            values[f"{section}.{key}"] = value.strip()
    return values


def _windows_user_profile() -> str | None:
    """The Windows-side %USERPROFILE%, as a path inside the distro. Asking cmd.exe is exact;
    globbing /mnt/c/Users is the fallback for a distro with interop switched off."""
    out = _run(["cmd.exe", "/c", "echo %USERPROFILE%"]).strip()
    match = re.match(r"^([A-Za-z]):\\\\?(.*)$", out.replace("\r", ""))
    if match:
        drive = match.group(1).lower()
        rest = match.group(2).replace("\\", "/")
        return f"/mnt/{drive}/{rest}"
    candidates = sorted(Path("/mnt/c/Users").glob("*")) if Path("/mnt/c/Users").is_dir() else []
    for candidate in candidates:
        if candidate.is_dir() and (candidate / ".wslconfig").exists():
            return str(candidate)
    return None


def windows_proxy() -> tuple[str | None, str | None]:
    """The Windows host's own proxy settings, read from inside the distro.

    This is the single most useful thing WSL can ask that a plain Linux box cannot: the proxy the
    corporate machine is actually configured with lives on the Windows side, and nothing copies it
    into the distro unless `.wslconfig`'s `autoProxy=true` is set or someone exports it by hand.
    """
    key = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    return parse_windows_proxy(_run(["reg.exe", "query", key]), _run(["netsh.exe", "winhttp", "show", "proxy"]))


def parse_windows_proxy(reg_output: str, winhttp_output: str = "") -> tuple[str | None, str | None]:
    """(proxy, PAC URL) out of `reg.exe query`'s and `netsh.exe winhttp show proxy`'s output.

    Split from the subprocess call so the parsing is testable against captured output — there is
    no Windows on the machine this repo is developed on, which is exactly the kind of code that
    otherwise ships unverified.
    """
    out = reg_output.replace("\r", "")
    enabled = re.search(r"ProxyEnable\s+REG_DWORD\s+0x(\w+)", out)
    server = re.search(r"ProxyServer\s+REG_SZ\s+(.+)", out)
    autoconfig = re.search(r"AutoConfigURL\s+REG_SZ\s+(.+)", out)
    proxy = server.group(1).strip() if server and enabled and int(enabled.group(1), 16) else None
    if not proxy:
        match = re.search(r"(?im)^\s*Proxy Server\(s\)\s*:\s*(\S+)", winhttp_output.replace("\r", ""))
        if match:
            proxy = match.group(1).strip()
    return proxy, autoconfig.group(1).strip() if autoconfig else None


def pac_proxies(url: str, timeout: float) -> list[str]:
    """Fetch a PAC file and pull the `PROXY host:port` literals out of it. Not an interpreter for
    its JavaScript — just the addresses it names, which is what a human would grep for."""
    parsed = split_host_port(url, default_port=443 if url.lower().startswith("https") else 80)
    if not parsed:
        return []
    path = re.sub(r"^[a-z]+://[^/]+", "", url, flags=re.IGNORECASE) or "/"
    try:
        cls = http.client.HTTPSConnection if url.lower().startswith("https") else http.client.HTTPConnection
        conn = cls(parsed[0], parsed[1], timeout=timeout)
        conn.request("GET", path)
        body = conn.getresponse().read(200_000).decode("utf-8", "replace")
        conn.close()
    except (OSError, http.client.HTTPException):
        return []
    return pac_proxy_addresses(body)


def pac_proxy_addresses(body: str) -> list[str]:
    """The `PROXY host:port` literals a PAC file names, deduplicated, in order.

    Not an interpreter for the file's JavaScript — the addresses are what a human would grep for,
    and running a corporate PAC's logic would need a JS engine this deliberately doesn't have.
    """
    found: list[str] = []
    for match in re.finditer(r"PROXY\s+([A-Za-z0-9.\-]+:\d+)", body):
        if match.group(1) not in found:
            found.append(match.group(1))
    return found


def _platform_facts(facts: Facts) -> None:
    facts.python = ".".join(str(part) for part in sys.version_info[:3])
    in_wsl_env = bool(os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"))
    facts.is_wsl = in_wsl_env or "microsoft" in _read("/proc/version").lower()
    facts.is_container = Path("/.dockerenv").exists() or "docker" in _read("/proc/1/cgroup")
    pretty = re.search(r'(?m)^PRETTY_NAME="?([^"\n]+)', _read("/etc/os-release"))
    facts.distro = pretty.group(1) if pretty else ""


def _proxy_facts(facts: Facts) -> None:
    facts.env_proxy = {name: os.environ[name] for name in _PROXY_VARS if os.environ.get(name)}
    for line in _read("/etc/environment").splitlines():
        key, _, value = line.strip().partition("=")
        if key in _PROXY_VARS and value:
            facts.etc_environment_proxy[key] = value.strip().strip('"').strip("'")

    for conf in sorted(Path("/etc/apt/apt.conf.d").glob("*")) if Path("/etc/apt/apt.conf.d").is_dir() else []:
        if conf.is_file() and re.search(r"(?i)Acquire::(http|https)::Proxy", _read(conf)):
            facts.apt_proxy.append(str(conf))


def _index_facts(facts: Facts) -> None:
    """Where this machine already thinks packages come from. When PyPI turns out to be blocked,
    an internal index configured here is the answer to print back."""
    pip_conf = _read("~/.config/pip/pip.conf") or _read("/etc/pip.conf")
    pip_index = re.search(r"(?m)^\s*index[-_]url\s*=\s*(\S+)", pip_conf)
    facts.pip_index = os.environ.get("PIP_INDEX_URL") or (pip_index.group(1) if pip_index else None)
    uv_conf = _read("~/.config/uv/uv.toml")
    uv_index = re.search(r'(?m)^\s*(?:index-url|default-index)\s*=\s*"([^"]+)"', uv_conf)
    facts.uv_index = (
        os.environ.get("UV_DEFAULT_INDEX")
        or os.environ.get("UV_INDEX_URL")
        or (uv_index.group(1) if uv_index else None)
    )
    npm_registry = re.search(r"(?m)^\s*registry\s*=\s*(\S+)", _read("~/.npmrc"))
    facts.npm_registry = npm_registry.group(1) if npm_registry else None
    git_proxy = _run(["git", "config", "--get", "http.proxy"]).strip()
    facts.git_proxy = git_proxy or None


def _resolver_and_ca_facts(facts: Facts) -> None:
    resolv = _read("/etc/resolv.conf")
    facts.nameservers = re.findall(r"(?m)^\s*nameserver\s+(\S+)", resolv)
    resolv_path = Path("/etc/resolv.conf")
    if "generated by WSL" in resolv:
        facts.resolv_conf_kind = "generated by WSL"
    elif resolv_path.is_symlink():
        facts.resolv_conf_kind = f"symlink → {resolv_path.readlink()}"
    elif resolv:
        facts.resolv_conf_kind = "static file"

    ca_dir = Path("/usr/local/share/ca-certificates")
    facts.extra_ca_files = [str(p) for p in sorted(ca_dir.glob("*.crt"))] if ca_dir.is_dir() else []
    facts.ca_env = {
        name: os.environ[name]
        for name in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "NODE_EXTRA_CA_CERTS")
        if os.environ.get(name)
    }


def _wsl_facts(facts: Facts, timeout: float) -> None:
    """The Windows side of a WSL distro's networking — the half no Linux-only diagnostic can see,
    and the half that usually holds the answer on a corporate machine."""
    facts.wsl_conf = _ini_values(_read("/etc/wsl.conf"))
    profile = _windows_user_profile()
    if profile:
        candidate = Path(profile) / ".wslconfig"
        if candidate.exists():
            facts.wslconfig_path = str(candidate)
            facts.wslconfig = _ini_values(_read(candidate))
    facts.windows_proxy, facts.windows_pac = windows_proxy()
    if facts.windows_pac:
        facts.pac_proxies = pac_proxies(facts.windows_pac, timeout)


def gather_facts(timeout: float = DEFAULT_TIMEOUT) -> Facts:
    """Everything read off the machine, in one pass, before any judgement is applied."""
    facts = Facts()
    _platform_facts(facts)
    _proxy_facts(facts)
    _index_facts(facts)
    _resolver_and_ca_facts(facts)
    if facts.is_wsl:
        _wsl_facts(facts, timeout)
    return facts


def configured_proxy(facts: Facts) -> tuple[str, int] | None:
    """The proxy this machine's own tools would use right now, if any."""
    for name in _PROXY_VARS:
        value = facts.env_proxy.get(name) or facts.etc_environment_proxy.get(name)
        if value:
            parsed = split_host_port(value)
            if parsed:
                return parsed
    return None


# ---------------------------------------------------------------------------
# Judgement: facts + probes → findings, each with the command that fixes it
# ---------------------------------------------------------------------------

_WSLCONFIG_BLOCK = (
    "[wsl2]\n"
    "networkingMode=mirrored   # VPN-compatible networking (Windows 11 22H2+, WSL 2.0.9+)\n"
    "dnsTunneling=true         # resolve through Windows instead of a NAT'd DNS packet\n"
    "autoProxy=true            # inherit Windows' own HTTP proxy inside the distro\n"
    "firewall=true"
)


def evaluate(  # noqa: C901
    facts: Facts,
    probes: list[Probe],
    proxy: tuple[str, int] | None,
    public_dns_ok: bool | None = None,
) -> list[Finding]:
    """Turn what was measured into what to do about it.

    Deliberately pure — every probe result and every fact is an argument, including
    `public_dns_ok` (whether 1.1.1.1 answered directly), which the caller measures. That is what
    makes the whole judgement layer testable against synthetic corporate networks without one.
    """
    findings: list[Finding] = []
    by_host = {probe.endpoint.host: probe for probe in probes}
    core = [probe for probe in probes if probe.endpoint.tier == "core"]
    failed = [probe for probe in probes if not probe.ok]
    dns_failures = [probe for probe in probes if probe.dns_error]

    # --- DNS ------------------------------------------------------------
    if core and len(dns_failures) == len(probes):
        detail = "Not one hostname resolved. Nothing that downloads anything can work until DNS does."
        fix = ["cat /etc/resolv.conf   # what the resolver is actually pointed at"]
        if facts.is_wsl:
            detail += (
                f" /etc/resolv.conf is {facts.resolv_conf_kind or 'missing'}"
                f" and lists {', '.join(facts.nameservers) or 'no nameserver'}."
            )
            fix += [
                "inv wsl.check                          # the WSL-specific half of this",
                "# then, on the Windows side, in %USERPROFILE%\\.wslconfig:",
                _WSLCONFIG_BLOCK,
                "wsl.exe --shutdown                     # from Windows, to apply it",
            ]
        # Nothing below can say anything a reader doesn't already know from this line: every
        # other check failed for this one reason, and listing them as separate findings buries
        # the cause under its own symptoms.
        return [Finding(BLOCKER, "DNS resolves nothing", detail, fix)]
    if dns_failures and len(dns_failures) < len(probes):
        hosts = ", ".join(probe.endpoint.host for probe in dns_failures)
        findings.append(
            Finding(
                WARNING,
                "Some hostnames don't resolve",
                f"{hosts} did not resolve while others did — a split-horizon resolver, or those "
                "names are simply blocked at the DNS layer.",
                ["inv net.check --json   # the per-host detail behind this line"],
            )
        )

    # A resolver that answers for public names but not internal ones (or the reverse) is worth
    # knowing before anyone "fixes" DNS by pointing it at 1.1.1.1 and loses the internal half.
    if facts.nameservers and not dns_failures and public_dns_ok is False:
        findings.append(
            Finding(
                INFO,
                "Public DNS is blocked, the local resolver works",
                "A direct UDP/53 query to 1.1.1.1 got no answer, while this machine's own "
                "resolver answers — the normal shape of a corporate network. Do not override "
                "DNS with public resolvers here: internal hostnames would stop resolving.",
                ["inv wsl.install --dns=no   # (the default) leave DNS to WSL/the host"],
            )
        )

    # --- TLS interception ------------------------------------------------
    intercepted = [probe for probe in probes if probe.tls_ok is False and probe.tls_issuer]
    if intercepted:
        issuers = sorted({probe.tls_issuer or "" for probe in intercepted})
        findings.append(
            Finding(
                BLOCKER,
                "TLS is being intercepted and the signer isn't trusted here",
                f"The certificate for {intercepted[0].endpoint.host} was issued by "
                f"{', '.join(issuers)}, which this machine's CA store doesn't trust. That is a "
                "TLS-inspecting proxy: every https download fails until its root CA is installed. "
                "The certificate itself is usually on the corporate intranet or already on the "
                "Windows machine (certmgr.msc → Trusted Root Certification Authorities).",
                [
                    "inv certs.install --bundle /path/to/corporate-root.crt",
                    "# see docs/certs.md — it also wires up Java, Node and the *_CA_BUNDLE vars",
                ],
            )
        )

    # --- proxies ---------------------------------------------------------
    tcp_failures = [probe for probe in probes if not probe.dns_error and not probe.tcp_ok]
    proxy_407 = [probe for probe in tcp_failures if probe.tcp_error and "407" in probe.tcp_error]
    if proxy_407:
        offered = proxy_407[0].tcp_error or ""
        findings.append(
            Finding(
                BLOCKER,
                "The proxy requires authentication",
                f"CONNECT through {proxy_407[0].via_proxy} was refused: {offered}. PULSE has a "
                "task for exactly this — it runs a local unauthenticated-to-the-client daemon "
                "that holds the credential in the OS keyring, so no password ends up in an "
                "environment variable.",
                ["inv proxy.check", "inv proxy.install", "# see docs/corporate-proxy.md"],
            )
        )
    elif not proxy and tcp_failures and facts.is_wsl and (facts.windows_proxy or facts.pac_proxies):
        candidates = [facts.windows_proxy] if facts.windows_proxy else facts.pac_proxies
        first = split_host_port(str(candidates[0]))
        export = f"http://{first[0]}:{first[1]}" if first else "http://<proxy>:<port>"
        findings.append(
            Finding(
                BLOCKER,
                "Windows has a proxy configured; this distro doesn't",
                f"The Windows host is configured to reach the internet through "
                f"{', '.join(str(c) for c in candidates)}"
                + (f" (from the PAC file at {facts.windows_pac})" if facts.pac_proxies else "")
                + ", but nothing inside this distro is pointed at it — which is why direct "
                "connections fail here and work on Windows.",
                [
                    "# the durable fix, on the Windows side, in %USERPROFILE%\\.wslconfig:",
                    _WSLCONFIG_BLOCK,
                    "wsl.exe --shutdown",
                    "# or, right now, in this shell:",
                    f'export http_proxy="{export}" https_proxy="{export}" no_proxy=localhost,127.0.0.1',
                ],
            )
        )
    elif not proxy and len(tcp_failures) >= max(2, len(probes) // 2) and not facts.is_wsl:
        findings.append(
            Finding(
                BLOCKER,
                "Connections are refused and no proxy is configured",
                f"{len(tcp_failures)} of {len(probes)} endpoints refused or timed out with no "
                "proxy set anywhere (environment, /etc/environment, apt, git). If this network "
                "requires one, nothing here knows about it yet.",
                ["inv proxy.check   # discovers a candidate and reports what auth it wants"],
            )
        )

    if proxy and any(probe.ok for probe in probes) and not proxy_407:
        findings.append(
            Finding(
                INFO,
                "Traffic is going through a proxy",
                f"Reachable endpoints were reached via {proxy[0]}:{proxy[1]}.",
                [],
            )
        )

    # --- the asymmetry that started this: PyPI blocked, GitHub allowed ----
    pypi = [by_host.get("pypi.org"), by_host.get("files.pythonhosted.org")]
    pypi_probes = [probe for probe in pypi if probe is not None]
    github_ok = by_host.get("github.com") is not None and (by_host["github.com"].ok)
    pypi_unreachable = pypi_probes and all(probe.dns_error is not None or not probe.tcp_ok for probe in pypi_probes)
    if pypi_unreachable and github_ok:
        blocked = ", ".join(probe.endpoint.host for probe in pypi_probes)
        index = facts.uv_index or facts.pip_index
        if index:
            fix = [
                f"# an index is already configured here: {index}",
                "# make uv use it for everything, including tool installs:",
                f'export UV_DEFAULT_INDEX="{index}"',
                f'export PIP_INDEX_URL="{index}"',
            ]
        else:
            fix = [
                "# ask for the internal index URL (Artifactory/Nexus 'pypi-remote' or similar), then:",
                'export UV_DEFAULT_INDEX="https://<internal-host>/artifactory/api/pypi/pypi/simple"',
                'export PIP_INDEX_URL="$UV_DEFAULT_INDEX"',
                "# and persist it: ~/.config/uv/uv.toml and ~/.config/pip/pip.conf",
            ]
        findings.append(
            Finding(
                BLOCKER,
                "PyPI is blocked, but GitHub is not",
                f"{blocked} unreachable while github.com answers. This is the standard corporate "
                "posture: public PyPI is blocked and an internal mirror is the sanctioned path. "
                "uv will still install a managed Python (that comes from GitHub) and then fail on "
                "the first package — which reads as 'uv is broken' and isn't.",
                fix,
            )
        )

    # --- apt --------------------------------------------------------------
    apt_probes = [by_host.get("archive.ubuntu.com"), by_host.get("security.ubuntu.com")]
    apt_failed = [probe for probe in apt_probes if probe is not None and not probe.tcp_ok]
    if apt_failed and len(apt_failed) == len([p for p in apt_probes if p is not None]):
        findings.append(
            Finding(
                BLOCKER,
                "The Ubuntu archives are unreachable",
                "apt can't reach archive.ubuntu.com/security.ubuntu.com, so every apt-installed "
                "package in setup.toml will fail. Corporate networks usually mirror these too.",
                [
                    "# point apt at the internal mirror:",
                    "sudo sed -i 's|http://archive.ubuntu.com|https://<internal-mirror>|' "
                    "/etc/apt/sources.list /etc/apt/sources.list.d/*.sources",
                    "# or give apt the proxy, if that's the sanctioned route:",
                    "echo 'Acquire::http::Proxy \"http://<proxy>:<port>\";' | "
                    "sudo tee /etc/apt/apt.conf.d/99pulse-proxy",
                ],
            )
        )

    # --- possible MTU black hole -----------------------------------------
    stalled = [
        probe
        for probe in probes
        if probe.tcp_ok and probe.tls_ok is False and probe.tls_error and "timed out" in probe.tls_error.lower()
    ]
    if stalled:
        findings.append(
            Finding(
                WARNING,
                "TCP connects but TLS stalls — looks like an MTU problem",
                "The handshake starts and then hangs, which is what a path-MTU black hole looks "
                "like: small packets pass, the certificate-sized ones don't. Classic on a VPN in "
                "front of WSL's NAT.",
                [
                    "ip link show eth0 | grep mtu",
                    "sudo ip link set dev eth0 mtu 1400   # try it; mirrored networking fixes it properly",
                    "# on the Windows side, %USERPROFILE%\\.wslconfig:",
                    _WSLCONFIG_BLOCK,
                ],
            )
        )

    # --- clock ------------------------------------------------------------
    skews = [
        abs(probe.server_date - time.time())
        for probe in probes
        if probe.server_date is not None  # only endpoints that answered
    ]
    if skews and min(skews) > 300:
        findings.append(
            Finding(
                WARNING,
                "This machine's clock is off by more than five minutes",
                f"A reachable server reports a time {min(skews) / 60:.0f} minutes away from this "
                "machine's. Certificate validation fails on clock skew, and a WSL distro's clock "
                "drifts after the Windows host sleeps.",
                ["sudo hwclock -s   # resync from the hardware clock (WSL: after a host resume)"],
            )
        )

    # --- WSL configuration worth having anyway ----------------------------
    if facts.is_wsl and failed:
        mode = facts.wslconfig.get("wsl2.networkingmode", "").lower()
        if mode != "mirrored":
            findings.append(
                Finding(
                    INFO,
                    "WSL is in NAT networking mode",
                    "Mirrored mode, DNS tunneling and auto-proxy are Microsoft's own recommended "
                    "settings for enterprise/VPN networks, and they fix most of the failures "
                    "above at the source (Windows 11 22H2+, WSL 2.0.9+). "
                    + (
                        f"Current file: {facts.wslconfig_path}"
                        if facts.wslconfig_path
                        else "There is no .wslconfig yet — create one."
                    ),
                    ["# %USERPROFILE%\\.wslconfig, then `wsl.exe --shutdown`:", _WSLCONFIG_BLOCK],
                )
            )

    if not findings and probes:
        findings.append(
            Finding(
                INFO,
                "Everything this setup needs is reachable",
                f"{len([p for p in probes if p.ok])} of {len(probes)} endpoints answered"
                + (f" via {proxy[0]}:{proxy[1]}" if proxy else " directly")
                + ".",
                [],
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Running it
# ---------------------------------------------------------------------------


def endpoints_for(scope: str, extra_from: Path | None = None) -> list[Endpoint]:
    chosen = [endpoint for endpoint in ENDPOINTS if scope != "quick" or endpoint.tier == "core"]
    if scope == "full" and extra_from and extra_from.exists():
        known = {endpoint.host for endpoint in chosen}
        matches: list[tuple[str, str]] = _URL_RE.findall(_read(extra_from))
        for host, port in sorted(set(matches)):
            if host not in known:
                known.add(host)
                chosen.append(Endpoint(host, int(port) if port else 443, "a URL declared in setup.toml", tier="extra"))
    return chosen


@dataclass
class Report:
    """One run's whole answer. A dataclass rather than the JSON dict it can become: everything
    downstream (the renderer, the invoke task, the tests) then reads typed attributes instead of
    string keys of `Any`."""

    verdict: str
    facts: Facts
    probes: list[Probe]
    findings: list[Finding]

    def as_dict(self) -> JsonObject:
        return {
            "verdict": self.verdict,
            "facts": self.facts.as_dict(),
            "probes": [
                {
                    "host": probe.endpoint.host,
                    "port": probe.endpoint.port,
                    "ok": probe.ok,
                    "result": probe.summary,
                    "needed_for": probe.endpoint.needed_for,
                    "issuer": probe.tls_issuer,
                    "seconds": round(probe.seconds, 2),
                }
                for probe in self.probes
            ],
            "findings": [finding.as_dict() for finding in self.findings],
        }


def run(scope: str = "core", timeout: float = DEFAULT_TIMEOUT, repo_root: Path | None = None) -> Report:
    facts = gather_facts(timeout)
    proxy = configured_proxy(facts)
    targets = endpoints_for(scope, (repo_root / "setup.toml") if repo_root else None)

    def probe_one(endpoint: Endpoint) -> Probe:
        return probe_endpoint(endpoint, timeout, proxy)

    with ThreadPoolExecutor(max_workers=8) as pool:
        probes = list(pool.map(probe_one, targets))
    public_dns_ok = query_dns_server("1.1.1.1") if facts.nameservers else None
    findings = evaluate(facts, probes, proxy, public_dns_ok)
    worst = next((level for level in _SEVERITY_ORDER if any(f.severity == level for f in findings)), INFO)
    return Report(verdict=worst, facts=facts, probes=probes, findings=findings)


def _colour(text: str, code: str, enabled: bool) -> str:
    return f"\033[{code}m{text}\033[0m" if enabled else text


def render(report: Report, colour: bool = True) -> str:
    severity_colour = {BLOCKER: "31;1", WARNING: "33;1", INFO: "36"}
    lines: list[str] = ["", _colour("── network doctor ─────────────────────────────────────────", "36", colour)]
    facts = report.facts
    where = [facts.distro] if facts.distro else []
    where.append("WSL" if facts.is_wsl else ("container" if facts.is_container else "native"))
    where.append(f"python {facts.python or '?'}")
    lines.append("  " + " · ".join(where))
    lines.append("")
    for probe in report.probes:
        mark = _colour("ok  ", "32", colour) if probe.ok else _colour("FAIL", "31;1", colour)
        lines.append(f"  {mark} {probe.endpoint.host}:{probe.endpoint.port:<4} {probe.summary}")
    for finding in report.findings:
        code = severity_colour.get(finding.severity, "36")
        lines.append("")
        lines.append(_colour(f"  [{finding.severity}] {finding.title}", code, colour))
        lines.extend(f"    {line}" for line in _wrap(finding.detail, 74))
        if finding.fix:
            lines.append("")
            for line in finding.fix:
                lines.extend(f"      {part}" for part in line.split("\n"))
    lines.append("")
    return "\n".join(lines)


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    out: list[str] = []
    line = ""
    for word in words:
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(line)
    return out


def _flag(namespace: argparse.Namespace, name: str) -> bool:
    return bool(cast(object, getattr(namespace, name)))


def _number(namespace: argparse.Namespace, name: str) -> float:
    value = cast(object, getattr(namespace, name))
    return float(value) if isinstance(value, (int, float, str)) else DEFAULT_TIMEOUT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="netdoctor",
        description="Which hosts a PULSE run needs are reachable here, and what to do when one isn't.",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--quick", action="store_true", help="only the endpoints that gate a bootstrap")
    parser.add_argument("--full", action="store_true", help="also probe every URL declared in setup.toml")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="per-probe seconds (default: 4)")
    parser.add_argument(
        "--advisory",
        action="store_true",
        help="always exit 0 — for a preflight that should report, not block",
    )
    args = parser.parse_args(argv)

    # argparse hands back an untyped namespace; _flag/_number pin each value to a real type once,
    # here, so everything below stays checkable.
    as_json = _flag(args, "json")
    advisory = _flag(args, "advisory")
    scope = "quick" if _flag(args, "quick") else ("full" if _flag(args, "full") else "core")
    report = run(scope=scope, timeout=_number(args, "timeout"), repo_root=Path(__file__).resolve().parent.parent)
    if as_json:
        print(json.dumps(report.as_dict(), indent=2))
    else:
        print(render(report, colour=sys.stdout.isatty()))
    if advisory:
        return 0
    return 1 if report.verdict == BLOCKER else 0


if __name__ == "__main__":
    sys.exit(main())
