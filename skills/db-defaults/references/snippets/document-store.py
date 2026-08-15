"""pip install tinydb

Dict-like API, no SQL anywhere. Maintainer calls it "maintenance mode" (stable, bugfix-only
releases) — not abandoned.
"""

from tinydb import Query, TinyDB
from tinydb.storages import MemoryStorage


def test_insert_and_search() -> None:
    db = TinyDB(storage=MemoryStorage)
    db.insert({"name": "widget", "price": 9.99})
    item = Query()
    results = db.search(item.name == "widget")
    assert results == [{"name": "widget", "price": 9.99}]
