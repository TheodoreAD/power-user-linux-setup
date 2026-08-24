"""Unit tests for tasks/certs.py's pure helpers — the only part of that module that doesn't shell
out to openssl/keytool or touch the filesystem/trust store. See tests/README.md.
"""

from tasks.certs import _split_pem_certs

_CERT_A = "-----BEGIN CERTIFICATE-----\nAAAA\nAAAA\n-----END CERTIFICATE-----"
_CERT_B = "-----BEGIN CERTIFICATE-----\nBBBB\nBBBB\n-----END CERTIFICATE-----"


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
