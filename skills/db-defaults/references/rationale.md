# Rationale for the db-defaults table

Research passes: 2026-08-15 (initial 11 categories) and 2026-08-15 (follow-up: OLAP split,
cron/scheduler category, pub/sub category, Kuzu fork check). Stats below (GitHub stars/forks/
issues, PyPI release dates) were pulled live via the GitHub and PyPI APIs at research time, not
recalled from training data — recheck before trusting a number that looks stale by the time you're
reading this.

## Why this skill exists

Across a chat session, or across different models/sessions working on the same repo family, the
"right" storage tech for a given need gets re-litigated each time — SQLite vs SQLAlchemy vs a cache
library, TinyDB vs raw SQL, Chroma vs Qdrant — with no memory of what was already decided elsewhere.
That's real, observed drift, not a hypothetical: the `*-polite-mcp` family (`olx-polite-mcp`,
`freshful-polite-mcp`, `temu-polite-mcp`) independently arrived at the same cache/relational split
purely because each pass happened to reason it through carefully — nothing enforced that
consistency, and a less careful session could easily have reached for something else.

This skill exists to short-circuit that re-litigation for common cases, not to forbid a real
analysis when one is actually warranted (see SKILL.md's "Escalate to" lines). Picks favor the
best-fit tool per concern over minimizing the number of technologies in a project — e.g. DuckDB is
recommended separately for both Analytical/OLAP and Time-series even though that's two categories
using one tool, because it's the better tool for both, not because of a drive to consolidate.

## In-process ephemeral state / Cache / Relational-simple

Confirmed by reading the actual code across all three `*-polite-mcp` repos: `diskcache` for TTL'd
HTTP-response caching (24h TTL, keyed by URL, identical in all three), raw stdlib `sqlite3` for
`freshful-polite-mcp`'s structured product/order stores, and a bare `threading.Lock` + `float` for
`olx-polite-mcp`'s in-process rate limiter. No library beats "nothing" for the last one, and no ORM
was needed for the two/three-table SQLite stores.

## Relational — complex/OLTP vs. Analytical/OLAP

| Option                   | License                                                                             | Notes                                                                                                       |
| ------------------------ | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `sqlalchemy` + `alembic` | MIT (both)                                                                          | real Engine/Session/declarative-model ceremony, but Alembic's migration story has no real DuckDB equivalent |
| `duckdb`                 | MIT (IP held by a nonprofit foundation specifically to keep it MIT "in perpetuity") | `duckdb.connect(":memory:")` gives native SQL over a plain connection, zero ORM ceremony                    |

DuckDB is explicitly OLAP-shaped, not OLTP (confirmed via DuckDB's own blog and community
discussion) — single-writer, optimized for analytical scans/aggregation rather than many small
frequent updates. It shipped a multi-writer "Quack" protocol in May 2026, but it's still new. One
pytest gotcha: a DuckDB _relation_ object (not the connection) reused across fixture scope can hit
a "connection closed" error (tracked as duckdb/duckdb#14771) — re-run queries per test rather than
caching relation objects across tests.

These are now two separate categories rather than one branching entry: **Relational — complex/OLTP**
(transactional multi-table apps, real migrations) → SQLAlchemy+Alembic; **Analytical/OLAP**
(read/aggregate-heavy structured data) → DuckDB. DuckDB's 2025/2026 additions (stream windowing
functions, `time_bucket`, ASOF joins) also make it the Time-series default (see below) — the same
tool serves both because it's genuinely the better fit for each, not out of a preference for fewer
technologies.

Sources: [Is DuckDB Open Source? MIT License explained](https://www.definite.app/blog/duckdb-open-source),
[DuckDB FAQ](https://duckdb.org/faq), [DuckDB Python DB API docs](https://duckdb.org/docs/current/clients/python/dbapi),
[relation-as-fixture issue #14771](https://github.com/duckdb/duckdb/issues/14771),
[HN: DuckDB is OLAP not OLTP like SQLite](https://news.ycombinator.com/item?id=26683957),
[DuckDB Concurrency docs](https://duckdb.org/docs/current/connect/concurrency),
[Stream Windowing Functions — DuckDB blog](https://duckdb.org/2025/05/02/stream-windowing-functions).

## Document store

| Library                                       | Stars | Forks | Open issues | Last push  | Latest release     | License              |
| --------------------------------------------- | ----- | ----- | ----------- | ---------- | ------------------ | -------------------- |
| `tinydb` (msiemens/tinydb)                    | 7,550 | 624   | 5           | 2026-08-10 | 4.9.0 (2026-08-06) | MIT                  |
| `sqlitedict` (piskvorky/sqlitedict)           | 1,244 | 140   | 38          | 2022-12-07 | 2.1.0 (2022-12-03) | Apache-2.0           |
| `diskcache.Index` (already in the cache pick) | 2,903 | 178   | 75          | 2024-08-10 | 5.6.3 (2023-08-31) | Apache-2.0           |
| `mongomock`                                   | 1,003 | 358   | 185         | 2025-06-30 | 4.3.0 (2024-11-16) | ISC (MIT-equivalent) |

TinyDB's own README, quoted verbatim: _"This project is in maintenance mode. It has reached a
mature, stable state where significant new features or architectural changes are not planned."_
That's "feature-complete and stable," not abandoned — the push/release/issue numbers above back
that up. Its API is genuinely SQL-free: `db.insert({...})`, `db.search(Query().field == x)`,
`MemoryStorage()`/`tmp_path` for pytest.

`sqlitedict` gives a plain `dict`-like interface (`d[key] = value`) fully hiding SQL from app code
even though SQLite is the engine underneath — a real fallback if field-level queries aren't needed
— but it hasn't been touched since Dec 2022 with 38 open issues sitting unaddressed.

`diskcache.Index` is confirmed key-only (its own docs describe it as "persistent mutable mapping
with insertion-order iteration" — `__getitem__`/`keys`/`items`, no `Query()`-style field matching).
Free bonus since `diskcache` is already in the stack for caching, but not a document-store
substitute.

`mongomock` is confirmed purely in-memory with no disk-persistence option — its own README calls it
"a small library to help testing Python code that interacts with MongoDB via Pymongo," not a
database in its own right. Not a real candidate here.

Also checked and rejected: `unqlite-python` bindings exist, but the underlying UnQLite C library
hasn't been developed since 2014 (its own docs recommend switching to SQLite); `ZODB` is real and
actively maintained but its transaction-manager/`Persistent`-subclassing API conflicts with the
low-boilerplate requirement; `offtheshelf` has been dead since 2012. Honest bottom line: SQLite's
JSON1 functions have eaten most of the embedded-document-store niche, and TinyDB is the one
sizable holdout with a clean, non-SQL surface.

Sources: [TinyDB](https://github.com/msiemens/tinydb), [TinyDB README maintenance-mode note](https://github.com/msiemens/tinydb#readme),
[sqlitedict](https://github.com/piskvorky/sqlitedict), [diskcache Index docs](https://grantjenks.com/docs/diskcache/api.html),
[mongomock](https://github.com/mongomock/mongomock), [unqlite-python](https://github.com/coleifer/unqlite-python).

## Full-text search

SQLite `FTS5` ships with stdlib `sqlite3`'s bundled SQLite build — zero new dependency, built-in
`bm25()` ranking function, lowest possible boilerplate for an agent to generate correct code
against.

`bm25s` (github.com/xhluca/bm25s, ~2k stars, 1M+ PyPI downloads/mo, MIT) is a fast pure-Python/NumPy
BM25 scorer popular in RAG pipelines — a standalone scoring library, not a datastore, so you still
own indexing/persistence yourself; worth it only when you specifically want that decoupling.

`tantivy-py` (project/repo name; MIT, Python bindings to Rust's `tantivy`, v0.26.0 released Apr
2026) ships prebuilt wheels for major platforms but falls back to requiring a Rust toolchain on
unmatched platforms/Python versions — a real risk of confusing an agent's install step. Also a real
naming trap independent of that: the correct install command is `pip install tantivy` — `pip
install tantivy-py` resolves to a different, stale package (`0.11.0-rc.7`, years old), confirmed by
checking PyPI directly. More Lucene-like and powerful than FTS5, but reserve it as a step-up, not
the default.

`Whoosh` confirmed still unmaintained as of 2026 (an inactive/unofficial community revival exists,
nothing official) — do not use. `Meilisearch` confirmed to still require a standalone running
server process, no embedded-library mode, so it's correctly excluded from local defaults and lives
only in the escalation note.

Sources: [SQLite FTS5](https://www.sqlite.org/fts5.html), [bm25s](https://github.com/xhluca/bm25s),
[tantivy-py](https://github.com/quickwit-oss/tantivy-py), [Whoosh](https://github.com/mchaput/whoosh),
[Meilisearch self-hosting docs](https://www.meilisearch.com/docs/resources/self_hosting/configuration/reference).

## Vector / embedding similarity search

| Library                  | Stars  | Forks | Open issues | Last push  | Latest release              | License             |
| ------------------------ | ------ | ----- | ----------- | ---------- | --------------------------- | ------------------- |
| `chromadb`               | 29,063 | 2,439 | 792         | 2026-08-15 | 1.5.9 (2026-05-05)          | Apache-2.0          |
| `lancedb`                | 11,153 | 1,004 | 614         | 2026-08-15 | 0.37.1 (2026-08-10)         | Apache-2.0          |
| `sqlite-vec`             | 8,015  | 349   | 202         | 2026-05-18 | 0.1.9 (2026-03-31, pre-1.0) | MIT/Apache-2.0 dual |
| `qdrant-client`          | 1,343  | 267   | 184         | 2026-08-12 | 1.19.0 (2026-08-04)         | Apache-2.0          |
| `faiss` (reference only) | 40,744 | 4,493 | 277         | 2026-08-15 | —                           | MIT                 |

Qdrant's own docs confirm a genuine embedded local mode built into `qdrant-client` itself — no
separate server: `QdrantClient(":memory:")` for pure in-memory (ideal for pytest), or
`QdrantClient(path=tmp_path)` for on-disk persistence. Quoted directly: _"Python client allows you
to run same code in local mode without running Qdrant server."_ Escalating later is a constructor-
arg swap to `QdrantClient(url=...)` or cloud credentials — same class, same method calls. (There's
also a separate, newer, unrelated product called "Qdrant Edge" with its own distinct API — don't
confuse it with `qdrant-client`'s built-in local mode, which is the mature and relevant one here.)

`chromadb` has by far the largest community (29k stars vs Qdrant's 1.3k on the client repo, though
that understates real Qdrant adoption since most of it lives in the main `qdrant/qdrant` server
repo). `EphemeralClient()`/`PersistentClient(path=...)` are equally simple to pytest-test, and its
`add()`/`query()` surface is arguably the simplest first-touch API of the four. Its local-to-Cloud
client-swap story (`EphemeralClient`/`PersistentClient`/`HttpClient`/`CloudClient` sharing the same
collection API) is plausible from its class design but wasn't independently verified to the same
depth as Qdrant's in this research pass.

`sqlite-vec` (successor to the now-archived `sqlite-vss`) stays interesting for SQLite-centric
stacks but is still pre-1.0 with placeholder docs per PyPI, the least mature of the four. `faiss`
(MIT, Meta) is too low-level for this use case: no metadata/collections/filtering layer, no ID
management, no persistence story beyond raw index serialization — a similarity-search kernel, not a
store.

Sources: [chromadb](https://github.com/chroma-core/chroma), [lancedb](https://github.com/lancedb/lancedb),
[sqlite-vec](https://github.com/asg017/sqlite-vec), [qdrant-client](https://github.com/qdrant/qdrant-client),
[Qdrant local-mode quickstart](https://qdrant.tech/documentation/quickstart/), [faiss](https://github.com/facebookresearch/faiss).

## Background job / message queue

huey's own docs, quoted directly: _"Huey can be run in a special mode called immediate mode, which
is very useful during testing and development. In immediate mode, Huey will execute task functions
immediately rather than enqueueing them, while still preserving the APIs and behaviors one would
expect when running a dedicated consumer process,"_ and _"By default, enabling immediate mode will
switch your Huey instance to using in-memory storage."_ One flag (`SqliteHuey('app',
immediate=True)`) makes `@huey.task()`-decorated calls run synchronously in-process — no
`huey_consumer` subprocess, no fixture orchestration. `huey`: 6,007 stars, 401 forks, 0 open issues,
MIT, pushed 2026-08-05, 15-year-old project (created 2011).

Also checked and rejected: `procrastinate` is Postgres-backed by design — no SQLite/in-memory mode
exists at all, disqualifying it against the local-only constraint. `Rocketry` had a promising
decorator API but shows no new PyPI release in the trailing 12 months despite steady downloads —
fails "actively maintained." `dramatiq`/`RQ`/`Celery` all need a real broker process
(Redis/RabbitMQ) — confirmed still true, which is exactly why they're the escalation pick rather
than a local default.

Sources: [huey](https://github.com/coleifer/huey), [huey immediate-mode docs](https://huey.readthedocs.io/).

## Cron / scheduled recurring tasks

This was split out from the job-queue category — a scheduler is trigger/time-shaped (`add_job(func,
trigger=...)`), a queue is work-item-shaped, and conflating them was hiding a real decision.

`apscheduler` (agronholm/apscheduler): 7,606 stars, 772 forks, 57 open issues, MIT, pushed
2026-08-01, latest stable release 3.11.3 (2026-06-28).

**v4 status**: still not stable. PyPI's version history tops out at `4.0.0a6` (2025-04-27); no
`4.0.0` final exists as of this research. [Issue #465, "APScheduler 4.0 progress tracking"](https://github.com/agronholm/apscheduler/issues/465)
has been open since 2020-09-29 — nearly 6 years, no merge/ETA. Pre-releases are explicitly marked
"do NOT use in production." **3.x remains the only practical choice for new projects right now.**

**Governance/bus-factor** — a real, evidence-backed concern, not overstated hearsay: `agronholm` has
1,134 commits; the next-highest human contributor has 6. Single-maintainer project, no co-maintainer
with meaningful share. [PR #983](https://github.com/agronholm/apscheduler/pull/983) (opened
2024-11-04) has exactly one comment — a coverage bot — 21 months later; several other PRs sit
unreviewed since late 2024. Counter-evidence it isn't abandoned: commits as recently as 2026-04-04,
3.11.x patch releases in Oct 2025/Dec 2025/Jun 2026, repo pushed within the last two weeks of this
research. Reads as "slow/selective," not abandoned. No organized public community complaint
specifically about the maintainer turned up (Reddit/HN/blog) — the pattern only shows up in raw
GitHub activity data.

**Verdict**: keep APScheduler 3.x as the default, document the bus-factor risk explicitly rather
than pretending it isn't there. `schedule` (dbader/schedule, MIT, 12.3k stars) is real and dead
simple but its own repo hasn't been pushed since 2024-05-25 either, so it isn't "more actively
maintained" — and it's in-process-only with zero persistence (a restart loses all schedules),
unlike APScheduler's `SQLAlchemyJobStore` (pointed at a `sqlite:///` URL — there's no class
literally named `SQLiteJobStore`, a mistake worth flagging since it's an easy one to make when
paraphrasing). Treat `schedule` as a lightweight escape hatch for pure in-process cases, not a
governance-driven replacement.

Sources: [PyPI apscheduler JSON](https://pypi.org/pypi/apscheduler/json), [agronholm/apscheduler](https://github.com/agronholm/apscheduler),
[issue #465](https://github.com/agronholm/apscheduler/issues/465), [PR #983](https://github.com/agronholm/apscheduler/pull/983),
[dbader/schedule](https://github.com/dbader/schedule).

## Pub/sub / event streaming

New category — surfaced by researching whether NATS fits anywhere in this table. It doesn't fit
"background job queue": NATS is fundamentally a subject-based pub/sub message bus, not a task
queue. Per NATS's own docs: _"NATS is an open source messaging system. Applications connect to a
NATS server and exchange messages by subject, without knowing each other's network addresses."_
Core NATS is ephemeral at-most-once pub/sub; its JetStream layer adds durable, replayable,
Kafka-like persistence on the same server process.

**Local-testability check, NATS**: no true in-process embed for Python. Requires the real
`nats-server` binary as a separate process — a single static Go binary, so it's
`subprocess.Popen`-able without Docker in principle — but there's no official nats-io Python
package for this (the `nats-server` PyPI name is a reserved, unimplemented placeholder), and the
two community attempts at a pytest-fixture wrapper (`quara-dev/nats-tools`,
`charbonats/nats-test-server`) are both effectively abandoned (0 stars each, last pushed 2023/2024).
That disqualifies it as _this table's local default_ even though it's a strong, actively maintained
product (`nats-server`: 20,514 stars, Apache-2.0, pushed today at research time;
`nats.py`: 1,241 stars, Apache-2.0). Its Python client API is genuinely low-boilerplate for core
pub/sub (`await nc.publish(...)`/`await nc.subscribe(...)`); JetStream adds real ceremony
(streams, durable consumer names, fetch/ack loops) comparable to Kafka consumer-group setup.

**Local default instead**: `blinker` (MIT) — 2,086 stars, the same signal/observer library Flask
itself uses internally. `signal.connect(receiver)` / `signal.send(sender)` fans out to multiple
in-process subscribers with zero ceremony and no external process, satisfying the actual "pub/sub"
shape (multiple listeners per event) that a single `asyncio.Queue` or SQLite polling table doesn't
naturally provide (those are single-consumer-shaped, matching the job-queue category instead).

**Verdict**: `blinker` for local, in-process pub/sub; NATS as the escalate-to-production pick once
you need a real distributed multi-consumer message bus — genuinely a different tool for a different
scale, not a bigger version of the same one.

Sources: [NATS: What is NATS](https://docs.nats.io/nats-concepts/what-is-nats), [NATS server installation](https://docs.nats.io/nats-server/installation),
[nats-io/nats-server](https://github.com/nats-io/nats-server), [nats-io/nats.py](https://github.com/nats-io/nats.py),
[pallets-eco/blinker](https://github.com/pallets-eco/blinker).

## Graph data

`kuzu` (MIT, genuinely embedded, no server process) looked like the strongest candidate but was
**archived by its own maintainers on GitHub, Oct 10 2025**, after Apple's acquisition of Kùzu Inc.

**Fork check**: literal GitHub-button forks (`korczis/kuzu`, `ColinLeeo/kuzu`, etc.) are single-
person personal builds with 0 stars each — not real successors. **[LadybugDB/ladybug](https://github.com/LadybugDB/ladybug)**
is the genuine one: created 2025-10-07, three days after the archival. Confirmed directly via its
own README: _"The database was formerly known as Kuzu."_ Same underlying engine, new stewardship —
not a rewrite from scratch, so it inherits Kuzu's engine-level maturity even though the project
name is under a year old. 1,581 stars, MIT, commits daily including the day of this research,
`pip install ladybug`, named active maintainers (not the original Kuzu/Apple team), a small
ecosystem already forming around it (bindings for multiple languages, a Postgres extension, a
visualizer). An HN thread ["KuzuDB, now in maintenance mode... quite annoyed"](https://news.ycombinator.com/item?id=47472646)
confirms community frustration with the archival is what drove the fork.

`networkx` (BSD-3-Clause, v3.6.1 released Dec 2025, extremely popular) is a pure in-memory graph
_library_, not a persistent database — needs pairing with pickle/JSON/gexf for persistence. Its
real value-add is graph algorithms (shortest path, centrality) over already-loaded data.

**Verdict**: promoted `ladybug` to the default for real graph-traversal/query-language needs (its
Cypher support and embedded no-server story match what made Kuzu attractive in the first place).
Kept the plain `edges(src, dst, relation)` table as the lightweight alternative for relationship
modeling that doesn't need real traversal performance — no reason to add a dependency for that
case. `networkx` pairs with either when you specifically need graph algorithms.

Sources: [kuzudb/kuzu](https://github.com/kuzudb/kuzu), [LadybugDB/ladybug](https://github.com/LadybugDB/ladybug),
[LadybugDB README, "formerly known as Kuzu"](https://github.com/LadybugDB/ladybug#readme),
[ladybugdb.com](https://ladybugdb.com/), [HN #47472646](https://news.ycombinator.com/item?id=47472646),
[networkx/networkx](https://github.com/networkx/networkx).

## Blob / object storage

`fsspec` is an abstract filesystem _interface_ — one API (`fs.open()`, `fs.ls()`, `fs.exists()`,
...) that many separately-installed backend packages implement underneath, so the same calls can
target local disk, S3, GCS, Azure, HTTP, and more, selected purely by a protocol string. `s3fs` and
`gcsfs` are exactly that: separate packages that register the `s3://`/`gs://` protocols with
fsspec — no code change beyond the protocol string:

```python
import fsspec

fs = fsspec.filesystem("file")  # local
# fs = fsspec.filesystem("s3")               # same calls, S3 backend (pip install s3fs)
with fs.open("data/out.json", "w") as f:
    f.write(payload)
```

| Package  | Stars | Forks | Open issues | License      | Last push  | Latest release |
| -------- | ----- | ----- | ----------- | ------------ | ---------- | -------------- |
| `fsspec` | 1,342 | 465   | 354         | BSD-3-Clause | 2026-07-30 | 2026.7.0       |
| `s3fs`   | 1,046 | 301   | 175         | BSD-3-Clause | 2026-08-13 | 2026.7.0       |
| `gcsfs`  | 395   | 180   | 100         | BSD-3-Clause | 2026-08-14 | 2026.8.0       |

All three are genuinely active. The call against defaulting to fsspec anyway: its own open-issue
count (354, ~26% of its stars) reflects the real complexity tax of unifying many storage backends —
complexity worth importing only once cloud storage is an actual plan, not "just in case." Plain
`pathlib`/`tmp_path` stays simplest for genuinely local-only projects; swapping to `fsspec` later is
a small, mechanical migration best done when the requirement is real.

Sources: [fsspec](https://github.com/fsspec/filesystem_spec), [fsspec docs](https://filesystem-spec.readthedocs.io/),
[s3fs](https://github.com/fsspec/s3fs), [gcsfs](https://github.com/fsspec/gcsfs).

## Time-series data

Originally documented as "SQLite by default, DuckDB only if already adopted for OLAP" — revised to
default straight to DuckDB given the explicit preference for best-fit-per-concern over minimizing
technology count. DuckDB's 2025/2026 additions (stream windowing functions, `time_bucket`, ASOF
joins, gap-filling) cut real boilerplate versus hand-rolling the same queries in raw SQL, so it's
the better tool for this concern on its own merits, independent of whether a project also uses it
for Analytical/OLAP work. A plain timestamp-indexed SQLite table remains a reasonable lighter-weight
choice if the actual need is only "store timestamped rows, filter by range" with no
resampling/windowing.

Sources: [Temporal Analysis with Stream Windowing Functions — DuckDB blog](https://duckdb.org/2025/05/02/stream-windowing-functions),
[The Complete Guide to Time Series Analysis with DuckDB](https://duckdblab.org/en/post/duckdb-time-series-guide/).
