"""Unit tests for tasks/wsl.py's _dns_query_packet (builds a raw DNS query packet in memory — no
socket I/O) and _parse_tristate (the --dns/--wslg yes/no override parser — no subprocess/file
I/O). See tests/README.md.
"""

import struct

import pytest

from tasks.wsl import _dns_query_packet, _parse_tristate


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
