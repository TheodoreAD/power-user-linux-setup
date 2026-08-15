"""Stdlib pathlib, no install.

Add fsspec (+ s3fs/gcsfs) only once cloud storage is an actual plan, not a maybe.
"""

from pathlib import Path


def test_write_and_read_bytes(tmp_path: Path) -> None:
    path = tmp_path / "item.bin"
    path.write_bytes(b"hello")
    assert path.read_bytes() == b"hello"
