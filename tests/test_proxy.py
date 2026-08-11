"""Unit tests for tasks/proxy.py's pure parsing helpers — the only part of that module that
doesn't shell out or touch the filesystem/keyring. See tests/README.md.
"""

from tasks.proxy import _parse_env_proxy, _parse_etc_environment, _parse_proxy_authenticate, _split_host_port


def test_parse_proxy_authenticate_single_scheme():
    raw = '< HTTP/1.1 407 Proxy Authentication Required\n< Proxy-Authenticate: Basic realm="proxy"\n'
    assert _parse_proxy_authenticate(raw) == ["Basic"]


def test_parse_proxy_authenticate_repeated_headers():
    raw = '< Proxy-Authenticate: Negotiate\n< Proxy-Authenticate: NTLM\n< Proxy-Authenticate: Basic realm="proxy"\n'
    assert _parse_proxy_authenticate(raw) == ["Negotiate", "NTLM", "Basic"]


def test_parse_proxy_authenticate_comma_joined():
    raw = '< Proxy-Authenticate: Negotiate, NTLM, Basic realm="proxy"\n'
    assert _parse_proxy_authenticate(raw) == ["Negotiate", "NTLM", "Basic"]


def test_parse_proxy_authenticate_dedupes():
    raw = "< Proxy-Authenticate: NTLM\n< Proxy-Authenticate: NTLM\n"
    assert _parse_proxy_authenticate(raw) == ["NTLM"]


def test_parse_proxy_authenticate_no_match():
    raw = "< HTTP/1.1 200 OK\n< Content-Type: text/html\n"
    assert _parse_proxy_authenticate(raw) == []


def test_split_host_port_with_scheme_and_port():
    assert _split_host_port("http://proxy.example.com:8080") == ("proxy.example.com", 8080)


def test_split_host_port_no_scheme_no_port():
    assert _split_host_port("proxy.example.com", default_port=3128) == ("proxy.example.com", 3128)


def test_split_host_port_strips_embedded_credentials():
    # Parsed only to extract host/port — the anti-pattern this feature exists to avoid is never
    # reused, just tolerated if some other tool already left it in an env var.
    assert _split_host_port("http://user:pass@proxy.example.com:8080") == ("proxy.example.com", 8080)


def test_split_host_port_empty_string():
    assert _split_host_port("") is None


def test_parse_env_proxy_prefers_https_over_http():
    env = {"http_proxy": "http://a:80", "https_proxy": "http://b:443"}
    assert _parse_env_proxy(env) == ("b", 443)


def test_parse_env_proxy_missing():
    assert _parse_env_proxy({}) is None


def test_parse_etc_environment_finds_https_proxy():
    text = 'PATH="/usr/bin"\nhttps_proxy="http://proxy.corp.com:8080"\n'
    assert _parse_etc_environment(text) == ("proxy.corp.com", 8080)


def test_parse_etc_environment_ignores_comments():
    text = '# https_proxy="http://ignored:1"\nhttp_proxy="http://real.proxy:3128"\n'
    assert _parse_etc_environment(text) == ("real.proxy", 3128)


def test_parse_etc_environment_no_proxy_lines():
    assert _parse_etc_environment('PATH="/usr/bin"\n') is None
