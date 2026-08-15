"""pip install duckdb

Read/aggregate-heavy queries over structured data — native SQL, no ORM ceremony. Don't cache a
*relation* object across pytest tests, only the connection (see duckdb/duckdb#14771).
"""

import duckdb


def test_group_by_aggregate() -> None:
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE sales (region TEXT, amount DOUBLE)")
    con.execute("INSERT INTO sales VALUES ('east', 100.0), ('west', 250.0)")
    rows = con.sql("SELECT region, sum(amount) AS total FROM sales GROUP BY region ORDER BY region").fetchall()
    assert rows == [("east", 100.0), ("west", 250.0)]
