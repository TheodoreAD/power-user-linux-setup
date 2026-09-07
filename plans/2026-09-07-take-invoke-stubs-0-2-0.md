---
status: idea
updated: 2026-09-07
source_repo: github.com-personal/repo-tasks
source_session: 52905ee0-50ff-4376-bd19-5ab4d9ca0a24.jsonl
source_moment: 2026-09-07T11:15:05Z
---

## Context

This repo's `uv.lock` pins `invoke-stubs` at `ad052ca` — the distribution's first commit, 0.1.0.
0.2.0 (`13bcc9e`, on `main`) declares every module `invoke/__init__.py` re-exports from plus `util`
— 16 in all — and fixes three annotations invoke has wrong rather than missing.

`repo-tasks` took it 2026-09-07 with a green gate, which was the verification `invoke-stubs`' own
plan listed as owed before any consumer bumped. Filed from that session; nothing here was touched.

The same lock also pins `repo-tasks` at `7bb880b`, which is well behind that repo's `main`. Whether
to move both in one pass is this repo's call — they are separate git pins and neither forces the
other.

## Evidence

Session transcript `52905ee0-50ff-4376-bd19-5ab4d9ca0a24.jsonl` under
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-repo-tasks/`, 2026-09-07, from
"we just finished upgrading the invoke stubs".

The one cost that session paid: `collection.pyi` declares `collections: Lexicon` and `util.pyi`
declares `Lexicon(dict[str, Any])`, so `Collection.collections["x"]` is now honestly `Any`. Under
0.1.0 it fell through to invoke's untyped vendored `Lexicon` and was `Unknown | None` — silenced by
the tests tier, where `reportAny` is not. 37 errors in one file, fixed with `cast(Collection, ...)`.

Measured for this repo before filing: **no file here indexes `.collections[`**, and 5 lines carry a
`pyright: ignore`. This repo has the largest task tree in the family after `repo-tasks`, though, so
it is the most likely place for a stubbed-but-`Any` member other than `collections` to surface.

## Open questions

[NEEDS CLARIFICATION: this repo's own `pyrightconfig.json` is the origin of the family's, per
`repo-tasks`' `contributing/type-checking.md`. If the bump does turn up new `reportAny` hits, is the
answer a cast at the call site (what `repo-tasks` did) or a rule change here that every consumer
then inherits? The first was chosen there deliberately — the type is honest and the cast is local.]

## Recommended direction

`inv deps.lock --package invoke-stubs`, `inv venv.sync`, `inv quality.precommit`. Keep the
`repo-tasks` pin bump, if wanted, as its own commit — it is a different decision with a different
blast radius.
