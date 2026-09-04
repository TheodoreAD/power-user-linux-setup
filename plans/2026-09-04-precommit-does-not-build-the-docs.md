---
status: planned
updated: 2026-09-04
---

# `inv quality.precommit` does not build the docs, so a heading rename ships a red deploy

## Context

Found by a harvest sweep 2026-09-04, after it had already happened twice.

`docs/claude-code.md`'s global-instructions heading was renamed in `e7b481e` as part of moving the
deployed file to `~/.agents/AGENTS.md`. That changed the heading's anchor, and `docs/index.md:63`
still linked to the old one. The gate passed, both commits pushed, and
**`Deploy docs to GitHub
Pages` failed on `2a4de19` and again on `ae59318`** while `CI` passed green
on both — so `master` moved twice while the published site kept serving the last good build.

Nothing in the session surfaced it. `git push` succeeded, `inv quality.precommit` was green (551
passed), and the only signal was a workflow conclusion nobody reads unless they look.

## The gap, precisely

The repo already owns the command that catches this:

```shell
inv docs.build        # zensical build --strict — exactly what the Pages workflow runs
inv docs.link-check   # relative links
```

`inv docs.build` on the fix reported `No issues found`, and on the broken tree it is what CI
printed: `Warning: anchor does not exist … Aborted because --strict flag is set`. **It is simply not
in `quality.precommit`.** So the check exists, runs locally, is fast, and is the one thing that
would have caught a class of error the rest of the gate structurally cannot see — `dprint` formats
markdown and `pytest` never renders it.

[PITFALL: **a dangling anchor is invisible to every other check, including a careful reader.** The
link's path is still correct — `claude-code.md` exists — and only the fragment after `#` is wrong,
which no link checker that resolves files will catch and which reads as fine in review. The rename
that breaks it happens in a different file from the link, usually in a commit about something else.
`plan-docs`' retirement procedure already states the general form ("a valid path aimed at a renamed
heading still dangles") and this session quoted it earlier the same day, then did it.]

## Open questions

**Answered 2026-09-04 by re-breaking the anchor and running both.** `docs.link-check` exits **0** on
the dangling anchor — it resolves files, not fragments — while `docs.build` exits **1** with
`anchor does not exist`. So there is no overlap and no cheaper substitute: `docs.build` is the task
to add, and adding `link-check` instead would produce a gate that passes on exactly this bug.

Since answered in `repo_tasks/docs.py` itself, which says it out loud: `_broken_link`'s docstring is
"`file.md#heading` verifies the file, never the heading, so a renamed heading still passes." The
gate's blindness here is documented behaviour, not an oversight to report upstream.

## Decision, 2026-09-04: it joins `check`, and `precommit` gets it for free

**Timed first, as asked.** On this repo (41 pages under `docs/`, warm venv):

| command                 | wall              | note                                   |
| ----------------------- | ----------------- | -------------------------------------- |
| `inv docs.build`        | 1.54 s and 1.59 s | zensical's own figure: 1.20 s / 1.25 s |
| `inv quality.precommit` | 6.76 s            | 551 tests, all green                   |

So +23% on the gate, ~1.5 s absolute. That is under the threshold the question was really about —
nobody reaches for `| tail` over a second and a half. **There is also no cold tree to measure:**
`docs.build` carries `pre=[clean]`, so every run is already a full rebuild and the cold and warm
numbers above are the same number twice.

**`precommit`-vs-`check` turned out to be a false choice.** `precommit` is `pre=[fix, check]`, so
anything in `check` is in `precommit` already; the only thing "in `precommit` only" would buy is
_exempting CI_, which is the opposite of what the second open question wanted. It goes in `check`.

**Which answers the second open question at no extra cost.** CI's `quality` job runs
`inv quality.check` on every push to `master` and every PR, so a broken anchor fails the run people
already watch, with no new workflow and no `push`-triggered duplicate job. The price is building the
docs twice on a `master` push — once in `check`, once in `Deploy docs to GitHub Pages` — which is
1.5 s of runner time against a failure mode that has already shipped twice.

**The `site/` objection dissolves.** `.gitignore:123` has `/site`, so no `git status` ever reports
it, and `build` cleans on _entry_ rather than on exit — the `docs.clean` adjacency recommended below
already exists, on the side that matters. It leaves 3.3 MB of ignored output behind, and nothing
accumulates across runs.

**The real obstacle is the dependency, not the runtime.** `repo_tasks/docs.py`'s module docstring is
explicit that this was a deliberate line: zensical "isn't a dependency of this package", and
`link_check` is "the exception: it needs no zensical, no dependency at all, and runs in the gate."
Here, zensical is a machine-wide `uv tool` install (`[packages.zensical]` in `setup.toml`,
`~/.local/bin/zensical`) plus a `requirements-docs.txt` the Pages workflow `pip install`s. It is in
no dependency group, so `.github/ci-bootstrap.sh`'s `uv run inv dev-env.setup` would leave CI's
`quality` job failing on a missing command rather than on the anchor.

## Recommended direction

Two changes, in two repos — the second is the one that actually closes the gap, and it cannot be
made from here.

1. **This repo: make zensical resolvable from its own venv.** A `docs` dependency group in
   `pyproject.toml` (the shape `repo_tasks/docs.py` already assumes, `uv sync --group docs`), which
   also retires `requirements-docs.txt` as a second place the pin lives — the Pages workflow can
   sync the group instead of `pip install`ing a parallel file. Correct on its own merits whether or
   not the upstream change lands.
2. **`repo-tasks`: add `docs.build` to `quality.check`'s pre-chain**, guarded so it no-ops on a
   consumer with no `mkdocs.yml` (`scaffoldapy`'s template makes the docs site conditional on
   `with_docs`, so the docs-less consumer is real) — the graceful-degradation shape `shell_check`
   already uses for a repo with zero `.sh` files, per this repo's cross-repo family convention.
   **Filed as `plans/2026-09-04-docs-build-in-the-quality-gate.md` in the plans store's `repo-tasks`
   mirror** rather than implemented, since writing into another repo's tree is out.
3. Note in `contributing/zensical.md` that a heading rename is an anchor change — the direction this
   repo has already documented is the opposite one (a green local build not implying a green
   deploy), and this is the same hazard from the other end.
