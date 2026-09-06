"""Unit tests for tasks/certs.py's pure helpers — the only part of that module that doesn't shell
out to openssl/keytool or touch the filesystem/trust store. See tests/README.md.
"""

import base64

from tasks.certs import (
    _PS_EXPORT_SCRIPT,
    _encoded_command,
    _pem_fingerprint,
    _split_pem_certs,
    _windows_extra_roots,
    _windows_labels,
)

_CERT_A = "-----BEGIN CERTIFICATE-----\nAAAA\nAAAA\n-----END CERTIFICATE-----"
_CERT_B = "-----BEGIN CERTIFICATE-----\nBBBB\nBBBB\n-----END CERTIFICATE-----"
_CERT_C = "-----BEGIN CERTIFICATE-----\nCCCC\nCCCC\n-----END CERTIFICATE-----"

# A real self-signed CA, and the fingerprint `openssl x509 -noout -fingerprint -sha256` printed for
# it. openssl is the oracle here on purpose: computing the expected value with hashlib in the test
# would only assert that the implementation agrees with itself.
_REAL_CERT = """-----BEGIN CERTIFICATE-----
MIIDFTCCAf2gAwIBAgIUZuIK5l2RXQqqyhICkbF3+mDwzJ0wDQYJKoZIhvcNAQEL
BQAwGjEYMBYGA1UEAwwPRXhhbXBsZSBSb290IENBMB4XDTI2MDkwNjAxMDQ0NloX
DTM2MDkwMzAxMDQ0NlowGjEYMBYGA1UEAwwPRXhhbXBsZSBSb290IENBMIIBIjAN
BgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAodWvAsPhWYy2YdtDC0w8du2s6xQk
/Q6BSHpbBaxO3XnOb+VNSiZyvPtl73uFYmCTmkkf1uXdQYSQNHoSstvTiE6kAO2d
nuRjktqHGtmHTLkX2BUYgQ7401YuwN35okRpB8XKBeBxDb8rS/uZTzoSkjYY5XmX
fGb3env5T3UIjDNtSMwcsmMbSTDAUmq5hT/El1w/4Ywl/s6fEl2flN5w4y3Apw3e
N2HTIpdRoYgDKKuccgCQw9NPW9tG0Hp8BIaYUlY5GOHC8BPzSSfqFoAb3KFDBWs5
MOJxAgppwrHiDrUA0fuyOWPsksq1f97Wsz50H9Zr3LCr/j8wJubp3u+9bwIDAQAB
o1MwUTAdBgNVHQ4EFgQU6akpqM4O5CErRgAZZUxe6iVvUkEwHwYDVR0jBBgwFoAU
6akpqM4O5CErRgAZZUxe6iVvUkEwDwYDVR0TAQH/BAUwAwEB/zANBgkqhkiG9w0B
AQsFAAOCAQEAM0q+yshd96XxD7smfSc3WxeTCekYYA2PIVK96RZPj/l+QQszYLJ1
g2EpbjoWSp4OClmkTsSSiO9XD7J85Kc5cHZ80dZkFtlMbcBGlhf3pKsmLydIcG5K
pZGloUt/+kiaqHNOz1UtW2ICQX02ieu+HoLcc0Gc04b9jIUkzluDgx6hXq7WbALp
m6tjbKlvwV2ybObluWl5C8M0TwI9RGnQaOouwZLXp99TvdyV3FakciO+Qqd9OYD8
knpfe57JtEtdxcDsHUBlLzGP3R85ISXBO/VmGWM2RKf9/DC4V8UveynIGpaGWDOm
aygkyTRk1X4FskeIuhi/uV1Y+5RhKywqCA==
-----END CERTIFICATE-----"""
_REAL_CERT_SHA256 = "9BC95EFC62952908A63EBF5560CC4D2758A5DE9633184D0C4D950F89090C254F"


def _fingerprint(pem: str) -> str:
    """_pem_fingerprint, narrowed — it returns None for an unparseable block, and every fixture
    here is parseable by construction."""
    fingerprint = _pem_fingerprint(pem)
    assert fingerprint is not None
    return fingerprint


def test_split_pem_certs_single():
    assert _split_pem_certs(_CERT_A) == [_CERT_A]


def test_split_pem_certs_multiple():
    text = f"{_CERT_A}\n{_CERT_B}\n"
    assert _split_pem_certs(text) == [_CERT_A, _CERT_B]


def test_split_pem_certs_ignores_surrounding_noise():
    # openssl pkcs7 -print_certs can prepend subject=/issuer= banner lines ahead of each block —
    # only the BEGIN/END blocks themselves should survive.
    text = f"subject=CN=Test Corp Root CA\nissuer=CN=Test Corp Root CA\n{_CERT_A}\n"
    assert _split_pem_certs(text) == [_CERT_A]


def test_split_pem_certs_no_certs():
    assert _split_pem_certs("not a cert") == []


def test_split_pem_certs_empty_string():
    assert _split_pem_certs("") == []


def test_encoded_command_is_utf16le_base64():
    assert base64.b64decode(_encoded_command(_PS_EXPORT_SCRIPT)).decode("utf-16-le") == _PS_EXPORT_SCRIPT


def test_encoded_command_payload_is_pure_ascii():
    # The whole point of encoding: what reaches the command line carries no backslash, quote or $,
    # so neither invoke's shell nor PowerShell's own parser can reinterpret any of it.
    assert _encoded_command(_PS_EXPORT_SCRIPT).isascii()
    assert not set(_encoded_command(_PS_EXPORT_SCRIPT)) & set("\\'\"$")


def test_pem_fingerprint_matches_openssl():
    assert _pem_fingerprint(_REAL_CERT) == _REAL_CERT_SHA256


def test_pem_fingerprint_ignores_surrounding_whitespace():
    assert _pem_fingerprint(f"\n  {_REAL_CERT}  \n") == _REAL_CERT_SHA256


def test_pem_fingerprint_rejects_a_body_that_is_not_base64():
    assert _pem_fingerprint("-----BEGIN CERTIFICATE-----\nnot base64!\n-----END CERTIFICATE-----") is None


def test_windows_extra_roots_subtracts_what_the_distro_already_trusts():
    assert _windows_extra_roots(f"{_CERT_A}\n{_CERT_B}\n", f"{_CERT_A}\n") == [_CERT_B]


def test_windows_extra_roots_dedupes_a_root_present_in_both_stores():
    # LocalMachine\Root and CurrentUser\Root overlap; the same certificate exported twice is one
    # certificate, and installing it twice would put two copies in the bundle.
    assert _windows_extra_roots(f"{_CERT_B}\n{_CERT_B}\n", "") == [_CERT_B]


def test_windows_extra_roots_is_ordered_by_fingerprint_not_export_order():
    # Idempotency depends on this: _desired_bundle_text compares the assembled text against what is
    # installed, so an order that follows PowerShell's enumeration would re-run
    # update-ca-certificates on every invocation.
    forward = _windows_extra_roots(f"{_CERT_A}\n{_CERT_B}\n{_CERT_C}\n", "")
    reverse = _windows_extra_roots(f"{_CERT_C}\n{_CERT_B}\n{_CERT_A}\n", "")
    assert forward == reverse
    assert sorted(forward, key=lambda pem: _pem_fingerprint(pem) or "") == forward


def test_windows_extra_roots_empty_when_everything_is_already_trusted():
    assert _windows_extra_roots(f"{_CERT_A}\n", f"{_CERT_B}\n{_CERT_A}\n") == []


def test_windows_labels_maps_fingerprints_to_subjects_across_crlf():
    export = (
        "# CN=Example Root CA, O=Example [ABCD]\r\n"
        + _REAL_CERT.replace("\n", "\r\n")
        + "\r\n# CN=Other [EF01]\r\n"
        + _CERT_A.replace("\n", "\r\n")
        + "\r\n"
    )
    labels = _windows_labels(export)
    assert labels[_REAL_CERT_SHA256] == "CN=Example Root CA, O=Example [ABCD]"
    assert labels[_fingerprint(_CERT_A)] == "CN=Other [EF01]"


def test_windows_labels_keeps_an_unlabelled_block():
    assert _windows_labels(f"{_CERT_A}\n") == {_fingerprint(_CERT_A): ""}
