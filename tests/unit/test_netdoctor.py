"""Unit tests for tasks/netdoctor.py's pure halves: the parsers (proxy URLs, Windows registry
output, PAC files, INI files, certificate common names), the endpoint catalog, and — the part
worth the most — `evaluate()`, which turns measurements into findings.

`evaluate()` takes every measurement as an argument (see its docstring), so a whole corporate
network can be described as a literal here: PyPI blocked while GitHub answers, a 407 from the
proxy, an untrusted issuer on the certificate, a Windows-side proxy the distro doesn't know
about. Those shapes are otherwise only reproducible against real corporate infrastructure, which
is precisely what this repo can never test against.

The socket-touching half (probe_endpoint, query_dns_server, gather_facts) is exercised in
containers instead — see plans/2026-08-31-wsl-and-container-first-run-experience.md.
"""

import ast
import sys
import time
from pathlib import Path

import pytest

from tasks import netdoctor
from tasks.netdoctor import (
    BLOCKER,
    INFO,
    WARNING,
    Endpoint,
    Facts,
    Probe,
    endpoints_for,
    evaluate,
    pac_proxy_addresses,
    parse_windows_proxy,
    split_host_port,
)

_REPO_ROOT = Path(__file__).parents[2]  # tests/unit/<this file> → repo root


def probe(host, *, port=443, dns_error=None, tcp_ok=True, tcp_error=None, tls_ok=None, issuer=None, tier="core"):
    """One measured endpoint. Defaults describe a working one."""
    return Probe(
        endpoint=Endpoint(host, port, "test", tier=tier),
        dns_error=dns_error,
        tcp_ok=tcp_ok,
        tcp_error=tcp_error,
        tls_ok=tls_ok,
        tls_issuer=issuer,
    )


def unreachable(host, *, port=443, error="ConnectionRefusedError"):
    return probe(host, port=port, tcp_ok=False, tcp_error=error)


def titles(findings):
    return [finding.title for finding in findings]


def severities(findings):
    return {finding.severity for finding in findings}


# --- parsers ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("http://proxy.corp:8080", ("proxy.corp", 8080)),
        ("proxy.corp:3128", ("proxy.corp", 3128)),
        ("http://proxy.corp", ("proxy.corp", 80)),
        ("https://proxy.corp:443/", ("proxy.corp", 443)),
        ("socks5://127.0.0.1:1080", ("127.0.0.1", 1080)),
        ("", None),
    ],
)
def test_split_host_port(value, expected):
    assert split_host_port(value) == expected


def test_split_host_port_drops_an_embedded_credential():
    """A credential in a proxy URL is parsed off and never returned — this module reports on
    proxies, and printing back a password someone left in an env var would be a leak of its own."""
    assert split_host_port("http://DOMAIN\\user:s3cret@proxy.corp:8080") == ("proxy.corp", 8080)


def test_parse_windows_proxy_reads_the_registry_output():
    reg = (
        "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings\r\n"
        "    ProxyEnable    REG_DWORD    0x1\r\n"
        "    ProxyServer    REG_SZ    proxy.corp:8080\r\n"
        "    AutoConfigURL    REG_SZ    http://wpad.corp/wpad.dat\r\n"
    )
    assert parse_windows_proxy(reg) == ("proxy.corp:8080", "http://wpad.corp/wpad.dat")


def test_parse_windows_proxy_ignores_a_disabled_proxy():
    reg = "    ProxyEnable    REG_DWORD    0x0\r\n    ProxyServer    REG_SZ    proxy.corp:8080\r\n"
    assert parse_windows_proxy(reg) == (None, None)


def test_parse_windows_proxy_falls_back_to_winhttp():
    winhttp = "Current WinHTTP proxy settings:\r\n\r\n    Proxy Server(s) :  proxy.corp:8080\r\n"
    assert parse_windows_proxy("", winhttp)[0] == "proxy.corp:8080"


def test_pac_proxy_addresses_deduplicates_in_order():
    body = """
    function FindProxyForURL(url, host) {
      if (isPlainHostName(host)) return "DIRECT";
      if (shExpMatch(host, "*.corp")) return "PROXY internal.corp:3128";
      return "PROXY edge1.corp:8080; PROXY edge2.corp:8080; PROXY edge1.corp:8080";
    }
    """
    assert pac_proxy_addresses(body) == ["internal.corp:3128", "edge1.corp:8080", "edge2.corp:8080"]


def test_ini_values_flattens_sections():
    text = "[wsl2]\nnetworkingMode=mirrored\ndnsTunneling = true\n\n[experimental]\nautoMemoryReclaim=gradual\n"
    assert netdoctor._ini_values(text) == {
        "wsl2.networkingmode": "mirrored",
        "wsl2.dnstunneling": "true",
        "experimental.automemoryreclaim": "gradual",
    }


def test_der_common_names_reads_the_commonname_oid():
    """The extractor's contract, against a hand-built DER fragment: OID 2.5.4.3, a length, then
    the string. (It is also exercised against a real self-signed certificate in a container — see
    this module's docstring.)"""
    der = b"\x30\x0d" + b"\x06\x03\x55\x04\x03" + b"\x0c\x04Corp" + b"\x06\x03\x55\x04\x03" + b"\x0c\x08pypi.org"
    assert netdoctor._der_common_names(der) == ["Corp", "pypi.org"]


# --- the endpoint catalog --------------------------------------------------


def test_quick_scope_is_the_bootstrap_critical_subset():
    quick = {endpoint.host for endpoint in endpoints_for("quick")}
    assert "pypi.org" in quick
    assert "registry.npmjs.org" not in quick  # `extra` tier — nothing bootstraps through npm


def test_the_catalog_covers_what_a_bootstrap_cannot_proceed_without():
    """These six are what `bootstrap.sh` plus the first `inv setup` actually pull from, and the
    reason the catalog is hand-written rather than derived: pypi.org and files.pythonhosted.org
    appear nowhere in setup.toml — they are where `uv tool install` goes implicitly, which is
    exactly why a block there is so confusing when it happens."""
    core = {endpoint.host for endpoint in endpoints_for("quick")}
    assert core >= {
        "pypi.org",
        "files.pythonhosted.org",
        "astral.sh",
        "github.com",
        "archive.ubuntu.com",
        "security.ubuntu.com",
    }


def test_a_full_run_probes_hosts_declared_in_the_real_setup_toml():
    """The anti-drift mechanism for everything the catalog doesn't name: a full run reads
    setup.toml itself, so a newly declared apt repo or .deb URL is probed without anyone
    remembering to add it here."""
    hosts = {endpoint.host for endpoint in endpoints_for("full", _REPO_ROOT / "setup.toml")}
    assert "developer.download.nvidia.com" in hosts or len(hosts) > len(netdoctor.ENDPOINTS)


def test_full_scope_picks_up_extra_hosts_from_setup_toml(tmp_path):
    setup_toml = tmp_path / "setup.toml"
    setup_toml.write_text('url = "https://downloads.example.org/thing.deb"\n')
    hosts = {endpoint.host for endpoint in endpoints_for("full", setup_toml)}
    assert "downloads.example.org" in hosts


# --- evaluate: the corporate networks this repo can't otherwise test against ---


def test_dns_failure_everywhere_reports_one_cause_not_eight_symptoms():
    probes = [probe(host, dns_error="Temporary failure in name resolution", tcp_ok=False) for host in ("a.io", "b.io")]
    findings = evaluate(Facts(), probes, None)
    assert titles(findings) == ["DNS resolves nothing"]


def test_dns_failure_under_wsl_points_at_the_windows_side():
    facts = Facts(is_wsl=True, resolv_conf_kind="generated by WSL", nameservers=["172.20.0.1"])
    probes = [probe("a.io", dns_error="no", tcp_ok=False)]
    finding = evaluate(facts, probes, None)[0]
    assert "generated by WSL" in finding.detail
    assert any("wslconfig" in line for line in finding.fix)
    assert any("dnsTunneling=true" in line for line in finding.fix)


def test_pypi_blocked_while_github_answers_is_named_as_such():
    probes = [
        unreachable("pypi.org"),
        unreachable("files.pythonhosted.org"),
        probe("github.com"),
        probe("archive.ubuntu.com", port=80),
        probe("security.ubuntu.com", port=80),
    ]
    findings = evaluate(Facts(nameservers=["10.0.0.1"]), probes, None, public_dns_ok=True)
    pypi = [finding for finding in findings if "PyPI is blocked" in finding.title]
    assert len(pypi) == 1
    assert pypi[0].severity == BLOCKER
    assert any("UV_DEFAULT_INDEX" in line for line in pypi[0].fix)


def test_pypi_blocked_reuses_an_index_this_machine_already_has():
    facts = Facts(nameservers=["10.0.0.1"], uv_index="https://nexus.internal/repository/pypi/simple")
    probes = [unreachable("pypi.org"), unreachable("files.pythonhosted.org"), probe("github.com")]
    finding = next(f for f in evaluate(facts, probes, None) if "PyPI is blocked" in f.title)
    assert any("nexus.internal" in line for line in finding.fix)


def test_a_tls_trust_failure_is_not_reported_as_a_blocked_index():
    """Interception and a block need different fixes; reporting both sends people to configure an
    internal index they don't need."""
    probes = [
        probe("pypi.org", tls_ok=False, issuer="Corp Root Inspection CA"),
        probe("files.pythonhosted.org", tls_ok=False, issuer="Corp Root Inspection CA"),
        probe("github.com"),
    ]
    findings = evaluate(Facts(), probes, None)
    assert "TLS is being intercepted and the signer isn't trusted here" in titles(findings)
    assert not any("PyPI is blocked" in title for title in titles(findings))


def test_tls_interception_names_the_issuer_and_the_certs_task():
    probes = [probe("pypi.org", tls_ok=False, issuer="Corp Root Inspection CA")]
    finding = evaluate(Facts(), probes, None)[0]
    assert "Corp Root Inspection CA" in finding.detail
    assert any("inv certs.install" in line for line in finding.fix)


def test_a_proxy_asking_for_authentication_points_at_the_proxy_task():
    refused = "proxy answered 407 to CONNECT (offers Negotiate, NTLM)"
    probes = [unreachable("pypi.org", error=refused), unreachable("github.com", error=refused)]
    for item in probes:
        item.via_proxy = "proxy.corp:8080"
    findings = evaluate(Facts(), probes, ("proxy.corp", 8080))
    finding = next(f for f in findings if "requires authentication" in f.title)
    assert "Negotiate, NTLM" in finding.detail
    assert any("inv proxy.install" in line for line in finding.fix)
    # …and it must not also claim the proxy is working.
    assert not any("Traffic is going through a proxy" in title for title in titles(findings))


def test_windows_has_a_proxy_but_the_distro_does_not():
    facts = Facts(is_wsl=True, nameservers=["172.20.0.1"], windows_proxy="proxy.corp:8080")
    probes = [unreachable("pypi.org"), unreachable("github.com")]
    finding = next(f for f in evaluate(facts, probes, None) if "Windows has a proxy" in f.title)
    assert "proxy.corp:8080" in finding.detail
    assert any("autoProxy=true" in line for line in finding.fix)
    assert any("export http_proxy=" in line for line in finding.fix)


def test_a_pac_file_counts_as_a_windows_proxy():
    facts = Facts(
        is_wsl=True,
        nameservers=["172.20.0.1"],
        windows_pac="http://wpad.corp/wpad.dat",
        pac_proxies=["edge1.corp:8080"],
    )
    probes = [unreachable("pypi.org"), unreachable("github.com")]
    finding = next(f for f in evaluate(facts, probes, None) if "Windows has a proxy" in f.title)
    assert "wpad.corp" in finding.detail


def test_public_dns_blocked_is_advice_not_a_failure():
    facts = Facts(nameservers=["10.0.0.1"])
    findings = evaluate(facts, [probe("github.com")], None, public_dns_ok=False)
    finding = next(f for f in findings if "Public DNS is blocked" in f.title)
    assert finding.severity == INFO
    assert any("--dns=no" in line for line in finding.fix)


def test_tls_stalling_after_a_successful_connect_reads_as_an_mtu_problem():
    stalled = probe("pypi.org", tls_ok=False)
    stalled.tls_error = "The handshake operation timed out"
    findings = evaluate(Facts(), [stalled, probe("github.com")], None)
    finding = next(f for f in findings if "MTU" in f.title)
    assert finding.severity == WARNING
    assert any("mtu" in line for line in finding.fix)


def test_clock_skew_is_reported_because_it_breaks_certificate_validation():
    skewed = probe("github.com")
    skewed.server_date = time.time() + 3600
    findings = evaluate(Facts(), [skewed], None)
    assert any("clock is off" in title for title in titles(findings))


def test_wsl_in_nat_mode_gets_the_recommended_wslconfig_when_something_failed():
    facts = Facts(is_wsl=True, nameservers=["172.20.0.1"])
    findings = evaluate(facts, [unreachable("pypi.org"), probe("github.com")], None)
    finding = next(f for f in findings if "NAT networking mode" in f.title)
    assert "networkingMode=mirrored" in "\n".join(finding.fix)


def test_a_healthy_machine_says_so_and_nothing_else():
    probes = [probe("pypi.org"), probe("github.com"), probe("archive.ubuntu.com", port=80)]
    findings = evaluate(Facts(nameservers=["10.0.0.1"]), probes, None, public_dns_ok=True)
    assert titles(findings) == ["Everything this setup needs is reachable"]
    assert severities(findings) == {INFO}


# --- the constraints that let it run before anything is installed -----------


def test_netdoctor_imports_only_the_standard_library():
    """The zero-install entrypoint is only zero-install while this holds. A third-party import
    here would make `python3 tasks/netdoctor.py` fail on the machine that needs it most: a fresh
    WSL distro with nothing on it yet."""
    tree = ast.parse((_REPO_ROOT / "tasks" / "netdoctor.py").read_text())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "a relative import would pull in tasks/__init__.py, and invoke with it"
            if node.module:
                imported.add(node.module.split(".")[0])
    assert imported <= set(sys.stdlib_module_names), sorted(imported - set(sys.stdlib_module_names))


def test_netdoctor_parses_as_python_310():
    """Ubuntu 22.04 — still a supported WSL image — ships Python 3.10, and this has to run on it
    before uv can install anything newer. (Also run end to end under 22.04's own interpreter in a
    container; see this module's docstring.)"""
    source = (_REPO_ROOT / "tasks" / "netdoctor.py").read_text()
    tree = ast.parse(source, feature_version=(3, 10))
    # Names, not a substring search: the module's own docstring talks about what it may not use.
    banned = {"tomllib", "StrEnum", "batched", "UTC"}
    used = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    used |= {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            used.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            used.update(alias.name for alias in node.names)
            if node.module:
                used.add(node.module)
    assert not (used & banned), f"newer than the Python 3.10 floor: {sorted(used & banned)}"
