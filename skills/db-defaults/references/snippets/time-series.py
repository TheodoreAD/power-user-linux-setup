"""pip install duckdb

Same tool as analytical-olap.py — window functions, time_bucket, ASOF joins cut real boilerplate
versus hand-rolled SQL. Lightweight alternative if the need is only "store timestamped rows, filter
by range" with no windowing: a plain SQLite table with an index on the timestamp column.
"""

import duckdb


def test_time_bucket_average() -> None:
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE readings (ts TIMESTAMP, value DOUBLE)")
    con.execute(
        "INSERT INTO readings VALUES "
        "('2026-01-01 00:10:00', 1.0), ('2026-01-01 00:50:00', 3.0), ('2026-01-01 01:10:00', 5.0)"
    )
    rows = con.sql(
        "SELECT time_bucket(INTERVAL '1 hour', ts) AS bucket, avg(value) AS avg_value "
        "FROM readings GROUP BY bucket ORDER BY bucket"
    ).fetchall()
    assert len(rows) == 2
