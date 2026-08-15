"""Stdlib sqlite3, no install.

Raw SQL — no ORM ceremony for a few-table/KV-shaped store.
"""

import sqlite3


def test_insert_and_query() -> None:
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
    con.execute("INSERT INTO items (name) VALUES (?)", ("widget",))
    con.commit()
    row = con.execute("SELECT name FROM items WHERE name = ?", ("widget",)).fetchone()
    assert row == ("widget",)
