"""pip install diskcache

Disk-backed cache with TTL/eviction built in — don't hand-roll it.
"""

from pathlib import Path

import diskcache


def test_cache_set_and_get(tmp_path: Path) -> None:
    cache = diskcache.Cache(tmp_path)
    cache.set("key", {"value": 1}, expire=3600)  # seconds
    assert cache.get("key") == {"value": 1}
