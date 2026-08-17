---
name: db-defaults
description: "Use when adding local data persistence to a Python project — caching, relational storage (simple, complex/OLTP, or analytical/OLAP), document storage, full-text search, vector/embedding search, background job queues, cron/scheduled tasks, pub/sub/event streaming, graph data, blob storage, or time-series data — and no explicit \"evaluate the best DB for this\" request was made. Gives the default technology per category, chosen for permissive licensing, pytest-local testability with no docker/cloud, and low-boilerplate LLM-agent-friendly APIs, so picks stay consistent across projects instead of drifting session to session."
---

# Default storage tech per use case

Personal, Python-first, local-first projects. Applies when starting a storage/caching need without
an explicit request to analyze alternatives — pick from this table, don't re-litigate from scratch
each session. Deviating is fine when a category genuinely doesn't fit or scale requirements outgrow
the default (see each category's "Escalate to" line) — the point is to stop a fresh session/model
from silently picking something different for no reason, not to forbid judgment calls.

**Selection criteria for every entry below**: MIT/Apache-2.0/BSD-style permissive license only;
popular and actively maintained (verified via real GitHub/PyPI activity, not vibes); testable fully
inside a plain `pytest` run — in-memory or `tmp_path`-scoped, no Docker/cloud account/CI services;
low-boilerplate API a coding agent can use correctly without much ceremony or indirection. Picks
favor the best-fit tool per concern over minimizing the number of technologies in a project — don't
force a consolidation the categories below don't call for.

**Security is deliberately not a selection factor.** Every default here is chosen for local,
personal-scale use — nothing on this page should be treated as a production/multi-tenant/internet-
facing recommendation. Each category's "Escalate to" line is the pick for that situation instead.

## In-process ephemeral state

- Snippet: [`references/snippets/in-process-state.py`](references/snippets/in-process-state.py)
- Default: plain stdlib (`threading.Lock`, `time.monotonic`, a dict) — no library
- Why: no persistence needed; a library would be pure overhead for "hold one number, guarded by one
  lock"
- Escalate to: n/a — once it needs to survive a restart, it's the Cache or Relational category
  instead

## Cache (TTL / eviction)

- Snippet: [`references/snippets/cache.py`](references/snippets/cache.py)
- Default: `diskcache` (Apache-2.0, pure Python)
- Why: disk-backed, handles TTL/eviction so you don't hand-roll it; trivial pytest `tmp_path`
  fixture
- Escalate to: Redis — once multiple processes/machines need to share one cache

## Relational — simple (few tables, KV-shaped)

- Snippet: [`references/snippets/relational-simple.py`](references/snippets/relational-simple.py)
- Default: stdlib `sqlite3`, raw SQL
- Why: zero dependency, no ORM ceremony for a shape this small; `:memory:` or `tmp_path` in pytest
- Escalate to: Postgres

## Relational — complex / OLTP (many tables, real joins, migrations, frequent writes)

- Snippet: [`references/snippets/relational-oltp.py`](references/snippets/relational-oltp.py)
- Default: `sqlalchemy` + `alembic` (both MIT)
- Why: real Engine/Session/declarative-model ceremony, but it buys migration and relationship safety
  that nothing lighter offers for a genuinely transactional multi-table shape
- Escalate to: Postgres

## Analytical / OLAP (read/aggregate-heavy queries over structured data)

- Snippet: [`references/snippets/analytical-olap.py`](references/snippets/analytical-olap.py)
- Default: `duckdb` (MIT — IP held by a nonprofit foundation specifically to keep it MIT "in
  perpetuity")
- Why: `duckdb.connect(":memory:")` gives native SQL over a plain connection, zero ORM ceremony —
  much lower-boilerplate than SQLAlchemy for this shape, and genuinely fast at joins/aggregation.
  Single-writer (fine for personal-scale local use); a multi-writer "Quack" protocol shipped May
  2026 but is still new
- Escalate to: Postgres+DuckDB extension, or MotherDuck

## Document store (schemaless / semi-structured JSON)

- Snippet: [`references/snippets/document-store.py`](references/snippets/document-store.py)
- Default: `tinydb` (MIT, pure Python)
- Why: real dict-like API (`db.insert({...})`, `db.search(Query().field == x)`) — no SQL anywhere;
  `MemoryStorage()` or `tmp_path` for pytest. Maintainer calls it "maintenance mode"
  (feature-complete and stable) — still gets bugfix releases, not abandoned
- Alternative: `sqlitedict` (Apache-2.0) for pure key→object storage with no field queries needed —
  flag its multi-year commit gap before reaching for it
- Escalate to: MongoDB

## Full-text search

- Snippet: [`references/snippets/full-text-search.py`](references/snippets/full-text-search.py)
- Default: SQLite `FTS5` virtual tables — ships with stdlib `sqlite3`, zero new dependency, built-in
  `bm25()` ranking
- Alternative: `bm25s` (MIT) for a standalone RAG-style scorer decoupled from a datastore; `tantivy`
  (MIT, Python bindings to the Rust `tantivy` search engine — `pip install tantivy`, not
  `tantivy-py`, which is a different, stale package) for heavier Lucene-like search once FTS5's
  feature set is genuinely too thin
- Avoid: `Whoosh` — long-unmaintained
- Escalate to: Elasticsearch or Meilisearch (both need a running server, so are excluded as local
  defaults)

## Vector / embedding similarity search

- Snippet: [`references/snippets/vector-search.py`](references/snippets/vector-search.py)
- Default: `qdrant-client` (Apache-2.0)
- Why: `QdrantClient(":memory:")` or `QdrantClient(path=tmp_path)` needs no server at all, and
  escalating later is a literal constructor-arg swap (`url=...`/cloud creds) — same class, same
  methods, verified against Qdrant's own docs. Handles vectors + metadata + persistence in one API
- Alternative: `chromadb` (Apache-2.0) — far bigger community/mindshare, arguably an even simpler
  first-touch API (`add()`/`query()`); reasonable pick if onboarding ease matters more than a
  verified no-rewrite escalation path
- Escalate to: Qdrant Cloud (client code unchanged) or Pinecone/Weaviate

## Background job / message queue

- Snippet: [`references/snippets/job-queue.py`](references/snippets/job-queue.py)
- Default: `huey` (MIT)
- Why: `SqliteHuey(..., immediate=True)` runs `@huey.task()` functions synchronously in-process — no
  consumer subprocess, no orchestration, a plain pytest test just calls the function directly. Small
  decorator-based API, 15-year track record, near-zero open-issue backlog
- Escalate to: Celery/RQ/Dramatiq — all need a real broker (Redis/RabbitMQ), which is the point once
  you need multiple worker processes/machines

## Cron / scheduled recurring tasks

- Snippet: [`references/snippets/cron-scheduler.py`](references/snippets/cron-scheduler.py)
- Default: `apscheduler` 3.x (MIT)
- Why: `SQLAlchemyJobStore` pointed at a `sqlite:///` URL persists schedules across restarts, no
  external broker, usable purely as a queue if scheduling isn't even needed. Genuine bus-factor risk
  to know about, not a reason to avoid it outright: single dominant maintainer (1,134 commits vs.
  next-highest contributor's 6), ~2-year-old unreviewed PRs, and v4 has been in alpha since 2020
  with no stable release — 3.x is still the only practical choice and remains actively patched
  (releases as recently as Jun 2026)
- Alternative: `schedule` (MIT) — zero-dependency, trivial in-process API, but no persistence (a
  restart loses all schedules) and itself hasn't been pushed since May 2024; a lightweight escape
  hatch for pure in-process cases, not a governance-driven replacement
- Escalate to: a managed scheduler (e.g. cloud cron) once recurring jobs need to survive beyond one
  machine

## Pub/sub / event streaming

- Snippet: [`references/snippets/pubsub.py`](references/snippets/pubsub.py)
- Default: `blinker` (MIT) — in-process signal/observer dispatch (`signal.connect(receiver)`,
  `signal.send(sender)`)
- Why: the same library Flask itself uses for signals; zero ceremony, fans out to multiple
  subscribers in-process, no server, trivially testable
- Escalate to: NATS (Apache-2.0) — genuinely different tool, not a bigger version of this one: needs
  a separately-provisioned `nats-server` process, and no official/maintained Python pytest-fixture
  package exists for local testing (the two community attempts are both abandoned), so it doesn't
  qualify as a local default here even though it's a strong product once you're actually running a
  server

## Graph data

- Snippet: [`references/snippets/graph-data.py`](references/snippets/graph-data.py)
- Default: `ladybug` (MIT, `pip install ladybug`) — embedded, Cypher query language, no server
- Why: this is the actively-maintained continuation of Kuzu, forked by the community 3 days after
  Kuzu's Oct 2025 archival (Apple acquisition) — same underlying engine, new stewardship, not a
  rewrite. Daily commits, MIT license, named active maintainers. Still under a year old as a project
  name, so treat as promising-but-young rather than as battle-tested as, say, SQLite
- Lightweight alternative: for relationship modeling that doesn't need real graph-traversal
  performance or a query language, a plain `edges(src, dst, relation)` table in your relational
  store is still simpler — reach for `ladybug` specifically when you need actual graph algorithms/
  traversal at more than toy scale. Pair either with `networkx` (BSD-3-Clause) for in-memory graph
  algorithms over already-loaded data
- Escalate to: Neo4j Aura, Amazon Neptune

## Blob / object storage

- Snippet: [`references/snippets/blob-storage.py`](references/snippets/blob-storage.py)
- Default: plain `pathlib.Path` file writes — no library
- Why: zero dependency, trivial `tmp_path` testing; adding an abstraction for cloud storage you
  don't have a concrete plan for yet is exactly the case YAGNI is for
- Escalate to: `fsspec` (BSD-3-Clause) + `s3fs`/`gcsfs` once cloud storage is an actual plan, not a
  maybe — same `fs.open()`/`fs.ls()` calls, only the protocol string changes

## Time-series data

- Snippet: [`references/snippets/time-series.py`](references/snippets/time-series.py)
- Default: `duckdb` (MIT) — same tool as the Analytical/OLAP category above
- Why: DuckDB's window functions, `time_bucket`, gap-filling, and ASOF joins are genuinely strong
  for time-series analysis and meaningfully cut boilerplate versus hand-rolling the same queries in
  raw SQL — the better tool for this concern specifically, independent of whether a project also
  needs it for OLAP work
- Lightweight alternative: a plain SQLite table with a timestamp-indexed column, if the need is
  truly just "store timestamped rows and filter by range," with no resampling/windowing
- Escalate to: InfluxDB, TimescaleDB

## Editing this table

This file is _copied_, not symlinked, into `~/.agents/skills/db-defaults` by `inv ai.skills`
(`setup.toml`'s `[packages.db-defaults]`). Edit the source at
`power-user-linux-setup/skills/db-defaults/SKILL.md`, then re-run `inv ai.skills` to refresh every
project's copy — editing a deployed copy in place is local drift, the exact thing this skill exists
to prevent.

## Starter snippets

`references/snippets/` has one real, ruff-clean, self-contained Python file per category above —
each a verified `pip install` command in its docstring plus a working `test_*` function showing the
pytest-local pattern, directly copy-pasteable rather than a tutorial to adapt. Each category's
"Snippet:" line above links straight to its own file, so there's no need to open the others. This is
also where two real naming traps caught while writing them are documented at the point they matter:
`full-text-search.py` (the `tantivy` vs `tantivy-py` PyPI mixup) and `cron-scheduler.py` (the
nonexistent `SQLiteJobStore` class name).

## Full rationale

See [`references/rationale.md`](references/rationale.md) — the GitHub/PyPI evidence, the options
that were considered and rejected per category, and the reasoning behind every branch/alternative
above.
