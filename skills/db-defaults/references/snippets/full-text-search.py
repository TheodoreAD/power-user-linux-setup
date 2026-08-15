"""Stdlib sqlite3 FTS5, no install.

Zero new dependency, built-in bm25() ranking. Alternatives: bm25s (standalone RAG scorer) or
tantivy (Lucene-like, heavier) once FTS5's feature set is genuinely too thin.

Naming trap: the tantivy package is `pip install tantivy` — NOT `tantivy-py`, which is a
different, stale package (0.11.0-rc.7) despite matching the GitHub repo's name.
"""

import sqlite3


def test_match_ranked_by_bm25() -> None:
    con = sqlite3.connect(":memory:")
    con.execute("CREATE VIRTUAL TABLE docs USING fts5(title, body)")
    con.execute("INSERT INTO docs VALUES (?, ?)", ("Widget guide", "How to use the widget"))
    row = con.execute("SELECT title FROM docs WHERE docs MATCH ? ORDER BY bm25(docs)", ("widget",)).fetchone()
    assert row == ("Widget guide",)
