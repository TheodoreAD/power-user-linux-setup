"""Unit tests for tasks/cert_sources.py — the whole module, since all of it is pure text parsing.
A corporate machine's registry output, npmrc or WSLENV is a literal here, which is the only way any
of this gets exercised: none of it can be produced on the machine it was written on. See
tests/README.md.
"""

import re

from tasks import cert_sources
from tasks.cert_sources import (
    Bypass,
    ConfigRule,
    Kind,
    env_bypasses,
    env_candidates,
    parse_env_assignments,
    parse_reg_thumbprints,
    parse_reg_values,
    parse_wslenv,
    scan_config_text,
    thumbprint_from_label,
    windows_path_to_wsl,
)


def _rule(label: str) -> ConfigRule:
    """The shipped rule with this label — tests assert against the real patterns, not copies of
    them, so a pattern edited in the module is an edit the tests see."""
    return next(rule for rule in cert_sources.CONFIG_RULES if rule.label == label)


def test_env_candidates_finds_a_named_bundle():
    found = env_candidates({"NODE_EXTRA_CA_CERTS": " /etc/corp/root.pem "}, "this shell")
    assert [(c.value, c.installable) for c in found] == [("/etc/corp/root.pem", True)]
    assert "NODE_EXTRA_CA_CERTS" in found[0].origin
    assert "this shell" in found[0].origin


def test_env_candidates_ignores_an_empty_or_absent_variable():
    assert env_candidates({"REQUESTS_CA_BUNDLE": "", "SSL_CERT_FILE": "   "}, "x") == []


def test_env_candidates_reads_a_jvm_truststore_as_evidence_not_a_bundle():
    # A JKS is not a PEM: openssl cannot convert it and the installer would refuse it loudly. It
    # still names the CA this machine trusts, so it is reported rather than dropped.
    found = env_candidates({"JAVA_TOOL_OPTIONS": "-Xmx2g -Djavax.net.ssl.trustStore=/opt/corp.jks"}, "x")
    assert [(c.value, c.installable) for c in found] == [("/opt/corp.jks", False)]


def test_env_bypasses_reads_the_off_value_not_merely_the_variable():
    assert env_bypasses({"NODE_TLS_REJECT_UNAUTHORIZED": "0"}, "x")
    assert env_bypasses({"NODE_TLS_REJECT_UNAUTHORIZED": "1"}, "x") == []
    assert env_bypasses({"PYTHONHTTPSVERIFY": "0"}, "x")
    assert env_bypasses({"PYTHONHTTPSVERIFY": "1"}, "x") == []


def test_env_bypasses_treats_git_no_verify_as_a_boolean():
    assert env_bypasses({"GIT_SSL_NO_VERIFY": "true"}, "x")
    assert env_bypasses({"GIT_SSL_NO_VERIFY": "1"}, "x")
    assert env_bypasses({"GIT_SSL_NO_VERIFY": "false"}, "x") == []
    assert env_bypasses({"GIT_SSL_NO_VERIFY": ""}, "x") == []


def test_env_bypasses_carries_the_undo_and_where_it_was_found():
    found = env_bypasses({"GIT_SSL_NO_VERIFY": "true"}, "/etc/environment")
    assert found == [Bypass(found[0].setting, "/etc/environment", found[0].fix)]
    assert found[0].fix


def test_parse_env_assignments_handles_both_file_shapes():
    text = '# a comment\nhttps_proxy="http://p:8080"\nexport NODE_EXTRA_CA_CERTS=/etc/corp.pem\n'
    assert parse_env_assignments(text) == {
        "https_proxy": "http://p:8080",
        "NODE_EXTRA_CA_CERTS": "/etc/corp.pem",
    }


def test_parse_env_assignments_ignores_a_commented_out_setting():
    assert parse_env_assignments('# export SSL_CERT_FILE="/old.pem"\n') == {}


_REG_ENV = (
    "\r\nHKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment\r\n"
    "    NODE_EXTRA_CA_CERTS    REG_SZ    C:\\ProgramData\\corp\\root.pem\r\n"
    "    Path    REG_EXPAND_SZ    %SystemRoot%\\system32\r\n"
    "    NUMBER_OF_PROCESSORS    REG_DWORD    0x8\r\n"
)


def test_parse_reg_values_reads_string_values_across_crlf():
    values = parse_reg_values(_REG_ENV)
    assert values["NODE_EXTRA_CA_CERTS"] == "C:\\ProgramData\\corp\\root.pem"
    assert values["Path"] == "%SystemRoot%\\system32"


def test_parse_reg_values_skips_the_key_header_and_non_string_types():
    values = parse_reg_values(_REG_ENV)
    assert "NUMBER_OF_PROCESSORS" not in values
    assert not any(name.startswith("HKEY_") for name in values)


def test_parse_reg_thumbprints_reads_the_subkey_names():
    # The subkey name *is* the SHA-1 thumbprint, which is why this reads the registry rather than
    # certutil: no certificate blob to parse and no localized banner to survive.
    output = (
        "HKEY_LOCAL_MACHINE\\SOFTWARE\\Policies\\Microsoft\\SystemCertificates\\Root\\Certificates\r\n"
        "HKEY_LOCAL_MACHINE\\SOFTWARE\\Policies\\Microsoft\\SystemCertificates\\Root\\Certificates"
        "\\9b1c5efc62952908a63ebf5560cc4d2758a5de96\r\n"
    )
    assert parse_reg_thumbprints(output) == {"9B1C5EFC62952908A63EBF5560CC4D2758A5DE96"}


def test_parse_reg_thumbprints_empty_when_the_store_has_none():
    assert parse_reg_thumbprints("ERROR: The system was unable to find the specified registry key\r\n") == set()


def test_windows_path_to_wsl_translates_a_drive_letter():
    assert windows_path_to_wsl("C:\\ProgramData\\corp\\root.pem") == "/mnt/c/ProgramData/corp/root.pem"
    assert windows_path_to_wsl('"D:/certs/root.pem"') == "/mnt/d/certs/root.pem"


def test_windows_path_to_wsl_declines_what_it_cannot_translate():
    assert windows_path_to_wsl("/mnt/c/already/translated.pem") is None
    assert windows_path_to_wsl("\\\\server\\share\\root.pem") is None
    assert windows_path_to_wsl("") is None


def test_parse_wslenv_reads_the_flags():
    shared = parse_wslenv("NODE_EXTRA_CA_CERTS/p:REQUESTS_CA_BUNDLE:USERPROFILE/up")
    assert shared == {"NODE_EXTRA_CA_CERTS": "p", "REQUESTS_CA_BUNDLE": "", "USERPROFILE": "up"}


def test_parse_wslenv_empty_value():
    assert parse_wslenv("") == {}


def test_thumbprint_from_label():
    assert thumbprint_from_label("CN=Corp Root [9b1c5efc62952908a63ebf5560cc4d2758a5de96]") == (
        "9B1C5EFC62952908A63EBF5560CC4D2758A5DE96"
    )
    assert thumbprint_from_label("CN=Corp Root") is None


def test_npmrc_rules_separate_a_certificate_from_a_disabled_check():
    text = "cafile=/etc/corp/root.pem\nstrict-ssl=false\nregistry=https://registry.corp/\n"
    assert scan_config_text(_rule("npm cafile"), text) == ["/etc/corp/root.pem"]
    assert scan_config_text(_rule("npm strict-ssl=false"), text) == ["false"]


def test_gitconfig_rules_are_case_insensitive_like_git_itself():
    text = "[http]\n\tsslcainfo = /etc/corp/root.pem\n\tsslVerify = false\n"
    assert scan_config_text(_rule("git http.sslCAInfo"), text) == ["/etc/corp/root.pem"]
    assert scan_config_text(_rule("git http.sslVerify=false"), text) == ["false"]


def test_gitconfig_ssl_verify_true_is_not_a_finding():
    assert scan_config_text(_rule("git http.sslVerify=false"), "[http]\n\tsslVerify = true\n") == []


def test_conda_ssl_verify_is_read_as_both_kinds_without_confusing_them():
    # One key, two meanings: a path is the CA, `false` is the check switched off. Each rule has to
    # ignore the other's value or every corporate machine reports a bypass it does not have.
    path_text = "ssl_verify: /etc/corp/root.pem\n"
    off_text = "ssl_verify: false\n"
    assert scan_config_text(_rule("conda ssl_verify"), path_text) == ["/etc/corp/root.pem"]
    assert scan_config_text(_rule("conda ssl_verify"), off_text) == []
    assert scan_config_text(_rule("conda ssl_verify: false"), off_text) == ["false"]
    assert scan_config_text(_rule("conda ssl_verify: false"), path_text) == []


def test_pip_rules_find_the_cert_and_the_trusted_host():
    text = "[global]\ncert = /etc/corp/root.pem\ntrusted-host = pypi.corp.example.com\n"
    assert scan_config_text(_rule("pip cert"), text) == ["/etc/corp/root.pem"]
    assert scan_config_text(_rule("pip trusted-host"), text) == ["pypi.corp.example.com"]


def test_curlrc_finds_both_shapes():
    assert scan_config_text(_rule("curl cacert"), 'cacert = "/etc/corp/root.pem"\n') == ["/etc/corp/root.pem"]
    assert scan_config_text(_rule("curl insecure"), "--insecure\n") == ["--insecure"]


def test_every_bypass_rule_carries_a_fix():
    # A bypass reported with no way to undo it is a warning nobody can act on, which is the failure
    # mode this whole route exists to correct.
    assert all(rule.fix for rule in cert_sources.CONFIG_RULES if rule.kind is Kind.BYPASS)


def test_every_config_rule_captures_a_group():
    # scan_config_text reads group(1); a pattern without one raises at scan time, on a real
    # machine, in a task that is supposed to be read-only.
    assert all(rule.pattern.groups >= 1 for rule in cert_sources.CONFIG_RULES)
    assert all(isinstance(rule.pattern, re.Pattern) for rule in cert_sources.CONFIG_RULES)
