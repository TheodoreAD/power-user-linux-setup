"""pip install ladybug

The actively-maintained continuation of Kuzu (forked 3 days after Kuzu's Oct 2025 archival) — same
underlying engine, Cypher query language, embedded/no server. Still under a year old as a project
name, so treat as promising-but-young.

Lightweight alternative for relationship modeling that doesn't need real graph-traversal
performance: a plain edges(src, dst, relation) table in your relational store instead.
"""

import ladybug as lb


def test_create_and_traverse() -> None:
    db = lb.Database(":memory:")
    conn = lb.Connection(db)

    # schema
    conn.execute("CREATE NODE TABLE User(name STRING PRIMARY KEY)")
    conn.execute("CREATE REL TABLE Follows(FROM User TO User)")

    # data
    conn.execute("CREATE (:User {name: 'alice'})")
    conn.execute("CREATE (:User {name: 'bob'})")
    conn.execute("MATCH (a:User {name: 'alice'}), (b:User {name: 'bob'}) CREATE (a)-[:Follows]->(b)")

    # query — Cypher, the same query language Neo4j uses
    response = conn.execute("MATCH (a:User)-[:Follows]->(b:User) RETURN a.name, b.name")
    rows = list(response)
    assert rows == [["alice", "bob"]]
