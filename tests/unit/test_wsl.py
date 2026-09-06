"""Unit tests for the raw DNS query packet builder (now tasks/netdoctor.py's, still exercised
here alongside tasks/wsl.py's own pure helpers) (builds a raw DNS query packet in memory — no
socket I/O) and _parse_tristate (the --dns/--wslg yes/no override parser — no subprocess/file
I/O). See tests/README.md.
"""

import struct

import pytest
from invoke import MockContext, Result

from tasks import wsl
from tasks.netdoctor import dns_query_packet as _dns_query_packet
from tasks.wsl import _parse_tristate


def test_dns_query_packet_header_round_trips_query_id():
    packet = _dns_query_packet("archive.ubuntu.com", query_id=0x1234)
    query_id, flags, qdcount, ancount, nscount, arcount = struct.unpack(">HHHHHH", packet[:12])
    assert query_id == 0x1234
    assert flags == 0x0100
    assert (qdcount, ancount, nscount, arcount) == (1, 0, 0, 0)


def test_dns_query_packet_encodes_qname_labels():
    packet = _dns_query_packet("archive.ubuntu.com", query_id=0)
    question = packet[12:]
    assert question == b"\x07archive\x06ubuntu\x03com\x00" + struct.pack(">HH", 1, 1)


def test_dns_query_packet_single_label_hostname():
    packet = _dns_query_packet("localhost", query_id=0)
    assert packet[12:] == b"\x09localhost\x00" + struct.pack(">HH", 1, 1)


@pytest.mark.parametrize("value", ["yes", "true", "1"])
def test_parse_tristate_truthy_values(value):
    assert _parse_tristate(value, "dns") is True


@pytest.mark.parametrize("value", ["no", "false", "0"])
def test_parse_tristate_falsy_values(value):
    assert _parse_tristate(value, "dns") is False


def test_parse_tristate_rejects_unknown_value_with_flag_name_in_message():
    with pytest.raises(RuntimeError, match=r"--wslg must be auto, yes, or no \(got 'maybe'\)"):
        _parse_tristate("maybe", "wslg")


def _bus_context(stdout: str, ok: bool = True) -> MockContext:
    """A Context whose dbus-send answers with `stdout`. The command is matched loosely because the
    real one is a single long line and pinning it here would test the string, not the parse."""
    return MockContext(run=Result(stdout=stdout, exited=0 if ok else 1), repeat=True)


def test_secret_service_reports_a_store_that_answers(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(wsl, "_session_bus", lambda: "unix:path=/run/user/1000/bus")
    monkeypatch.setattr(wsl.util, "command_exists", lambda _name: True)
    assert "answering" in wsl._secret_service_state(_bus_context("   boolean true\n"))


def test_secret_service_separates_installed_from_running(monkeypatch: pytest.MonkeyPatch):
    # The distinction that matters: gnome-keyring on disk with nothing holding the bus name is the
    # normal state of a WSL distro after installing it, and it is not the same as "no keyring".
    monkeypatch.setattr(wsl, "_session_bus", lambda: "unix:path=/run/user/1000/bus")
    monkeypatch.setattr(wsl.util, "command_exists", lambda _name: True)
    assert wsl._secret_service_state(_bus_context("   boolean false\n")) == "installed but not running/unlocked"


def test_secret_service_needs_a_bus_before_anything_can_answer(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(wsl, "_session_bus", lambda: None)
    assert "no session bus" in wsl._secret_service_state(MockContext())


def test_secret_service_says_unknown_rather_than_guessing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(wsl, "_session_bus", lambda: "unix:path=/run/user/1000/bus")
    monkeypatch.setattr(wsl.util, "command_exists", lambda _name: False)
    assert "unknown" in wsl._secret_service_state(MockContext())


def test_session_bus_prefers_the_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/tmp/somewhere-else")
    assert wsl._session_bus() == "unix:path=/tmp/somewhere-else"
