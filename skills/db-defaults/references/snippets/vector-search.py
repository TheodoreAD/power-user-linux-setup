"""pip install qdrant-client

QdrantClient(":memory:") needs no server at all. Escalating later is a constructor-arg swap
(url=..., cloud creds) — same class, same methods.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


def test_upsert_and_query() -> None:
    client = QdrantClient(":memory:")
    # size must match your embedding model's output dimension (e.g. 1536 for OpenAI
    # text-embedding-3-small) — 3 here is only to keep the example short.
    client.create_collection("docs", vectors_config=VectorParams(size=3, distance=Distance.COSINE))
    client.upsert("docs", points=[PointStruct(id=1, vector=[0.1, 0.2, 0.3], payload={"src": "a"})])
    results = client.query_points("docs", query=[0.1, 0.2, 0.3], limit=5)
    assert results.points[0].id == 1
