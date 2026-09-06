"""Unit tests for tasks/proxy.py's pure parsing helpers — the only part of that module that
doesn't shell out or touch the filesystem/keyring. See tests/README.md.
"""

from pathlib import Path

import pytest

from tasks import proxy, util
from tasks.proxy import (
    _keyring_command,
    _keyring_env,
    _needs_negotiate,
    _parse_env_proxy,
    _parse_etc_environment,
    _parse_proxy_authenticate,
    _split_host_port,
)

_REPO = Path(util.__file__).parent.parent


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


def test_needs_negotiate_true_for_negotiate_or_kerberos():
    assert _needs_negotiate(["Negotiate"]) is True
    assert _needs_negotiate(["NTLM", "Kerberos"]) is True


def test_needs_negotiate_false_without_negotiate_scheme():
    assert _needs_negotiate(["Basic", "NTLM"]) is False
    assert _needs_negotiate([]) is False


def test_keyring_command_never_resolves_the_project_environment():
    # Without --no-project, uv resolves this repo's interpreter and will delete and recreate its
    # .venv when the answer differs from what is there — see
    # plans/2026-08-30-uv-run-destroys-the-project-venv.md.
    assert "--no-project" in _keyring_command(False, "print(1)")
    assert "--no-project" in _keyring_command(True, "print(1)")


def test_keyring_command_only_installs_the_fallback_backend_when_asked():
    assert "keyrings.alt" not in _keyring_command(False, "print(1)")
    assert "keyrings.alt" in _keyring_command(True, "print(1)")


def test_keyring_env_only_pins_a_backend_for_the_fallback(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("PYTHON_KEYRING_BACKEND", raising=False)
    assert "PYTHON_KEYRING_BACKEND" not in _keyring_env(False)
    assert _keyring_env(True)["PYTHON_KEYRING_BACKEND"] == "keyrings.alt.file.PlaintextKeyring"


def test_the_fallback_backend_is_installed_into_px_own_venv():
    # The backend has to be importable inside px's tool venv, not PULSE's: px reads the credential
    # at its own startup. Declared in setup.toml so this and `inv python.install-tools` cannot
    # install two different pxs.
    assert util.load_config()["packages"]["px-proxy"].get("extras") == ["keyrings.alt"]


def test_both_daemon_start_paths_read_the_env_file_that_pins_the_backend():
    # Three files have to agree on one path, and a drift here is silent: px falls back to the
    # default backend, finds no credential, and answers 407 as though the password were wrong.
    relative = str(proxy.ENV_FILE).removeprefix(str(Path.home()))
    assert f"EnvironmentFile=-%h{relative}" in (_REPO / "config" / "pulse-proxy.service").read_text()
    assert relative in (_REPO / "config" / "pulse-proxy-start.sh").read_text()
