"""Unit tests for tasks/wsl.py's _dns_query_packet — the only part of its DNS-reachability probe
that doesn't open a real socket. See tests/README.md.
"""
import struct

from tasks.wsl import _dns_query_packet


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
