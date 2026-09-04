---
status: blocked on the repo-tasks change filed as 2026-09-04-docs-build-in-the-quality-gate
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

| command                 | wall              | note                                           |
| ----------------------- | ----------------- | ---------------------------------------------- |
| `inv docs.build`        | 1.54 s and 1.59 s | on the machine-wide unpinned zensical 0.0.57   |
| `inv docs.build`        | 2.00 s, twice     | on the pinned 0.0.44 — the version that counts |
| `inv quality.precommit` | 6.76 s            | 551 tests, all green                           |

So +30% on the gate, 2 s absolute. That is under the threshold the question was really about —
nobody reaches for `| tail` over two seconds. **There is also no cold tree to measure:**
`docs.build` carries `pre=[clean]`, so every run is already a full rebuild and each pair of numbers
above is the same number twice.

The two `docs.build` rows are the point of step 1 below, and were not separable until it landed: the
first measures a version CI never runs, and 0.0.44 is ~30% slower than 0.0.57, so timing the
machine-wide tool would have under-reported the gate's real cost.

**`precommit`-vs-`check` turned out to be a false choice.** `precommit` is `pre=[fix, check]`, so
anything in `check` is in `precommit` already; the only thing "in `precommit` only" would buy is
_exempting CI_, which is the opposite of what the second open question wanted. It goes in `check`.

**Which answers the second open question at no extra cost.** CI's `quality` job runs
`inv quality.check` on every push to `master` and every PR, so a broken anchor fails the run people
already watch, with no new workflow and no `push`-triggered duplicate job. The price is building the
docs twice on a `master` push — once in `check`, once in `Deploy docs to GitHub Pages` — which is 2
s of runner time against a failure mode that has already shipped twice.

**The `site/` objection dissolves.** `.gitignore:123` has `/site`, so no `git status` ever reports
it, and `build` cleans on _entry_ rather than on exit — the `docs.clean` adjacency recommended below
already exists, on the side that matters. It leaves 3.3 MB of ignored output behind, and nothing
accumulates across runs.

**But `--strict` only covers `docs_dir`, so this buys less than the whole repo.** `mkdocs.yml` sets
`docs_dir: docs`, and zensical never renders `AGENTS.md`, `CONTRIBUTING.md`, `contributing/*.md` or
`plans/*.md` — so an anchor written in one of those is checked by nothing, before or after step 2.
Measured 2026-09-04: three such links exist, all of them pointing _into_ `docs/` (`AGENTS.md:154`
and `contributing/verify.md:5` at `dev-container.md`'s functional-verification heading,
`contributing/zensical.md:6` at `python.md#system-wide-tools`). All three resolve today, checked by
hand because there is no other way to check them. Three is small enough that the answer is "know
about it", not "build a second checker" — and small enough that a fourth should be weighed against
just naming the section in prose, which is what `CONTRIBUTING.md` now does when pointing at the
zensical page.

**The real obstacle is the dependency, not the runtime.** `repo_tasks/docs.py`'s module docstring is
explicit that this was a deliberate line: zensical "isn't a dependency of this package", and
`link_check` is "the exception: it needs no zensical, no dependency at all, and runs in the gate."
Here, zensical **was** a machine-wide `uv tool` install (`[packages.zensical]` in `setup.toml`,
`~/.local/bin/zensical`) plus a `requirements-docs.txt` the Pages workflow `pip install`ed. It was
in no dependency group, so `.github/ci-bootstrap.sh`'s `uv run inv dev-env.setup` would have left
CI's `quality` job failing on a missing command rather than on the anchor. Step 1 below fixes that
and has landed.

## Recommended direction

Steps 1 and 3 have landed here. Step 2 is the one that actually closes the gap, it is in another
repo, and until it lands the manual grep-plus-`docs.build` after a heading rename is the whole
defence.

1. ~~**This repo: make zensical resolvable from its own venv.**~~ **Landed 2026-09-04.**
   `pyproject.toml` gained a `docs = ["zensical==0.0.44"]` group — the shape `repo_tasks/docs.py`
   already assumes — and `[tool.uv] default-groups = ["dev", "docs"]`, since `inv dev-env.setup`
   (and `ci-bootstrap.sh`, which is only `uv run inv dev-env.setup`) is the one thing that populates
   the venv, so an opt-in group is a group CI never gets. `requirements-docs.txt` is deleted and the
   Pages workflow resolves the same pin from `uv.lock` via
   `uv run --only-group docs --frozen zensical build --strict`, verified on a scratch copy.

   This closed a `DEFERRED` item in `2026-08-27-docs-site-usability.md` with a third option neither
   of the two it weighed had named: it wanted either a pinned `[packages.zensical]` (a downgrade for
   the whole machine) or an unpinned CI, and a dependency group pays neither cost.
   `[packages.zensical]` stays for other repos and for the human at the shell; inside this repo
   direnv's `.venv/bin` shadows it.
2. **`repo-tasks`: add `docs.build` to `quality.check`'s pre-chain**, guarded so it no-ops on a
   consumer with no `mkdocs.yml` (`scaffoldapy`'s template makes the docs site conditional on
   `with_docs`, so the docs-less consumer is real) — the graceful-degradation shape `shell_check`
   already uses for a repo with zero `.sh` files, per this repo's cross-repo family convention.
   **Filed as `plans/2026-09-04-docs-build-in-the-quality-gate.md` in the plans store's `repo-tasks`
   mirror** rather than implemented, since writing into another repo's tree is out.
3. ~~Note in `contributing/zensical.md` that a heading rename is an anchor change.~~ **Landed
   2026-09-04**, as a subsection under `--strict is aggressive, in a good way` — the two red
   deploys, why `link-check`/`dprint`/`pytest`/a reviewer each structurally miss it, and the manual
   grep-plus-`docs.build` step that stands in until step 2. `CONTRIBUTING.md`'s existing gate
   warning points at it.

   The framing this step was written with is stale, and worth saying so: it expected to contrast
   with a documented "green local build does not imply a green deploy", which was the _version
   drift_ warning step 1 deleted. What is left to contrast with is the gate warning — a green
   `precommit` not implying a green deploy — which is the same hazard and a narrower one.
