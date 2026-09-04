---
status: idea
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

[NEEDS CLARIFICATION: **into `precommit`, or into `check`?** `docs.build` writes `site/` as a side
effect, so a gate task that builds is not purely a check — `docs.clean` exists for the same reason.
Either it goes in and the gate gains a build artifact, or a `--strict` no-write variant is needed,
or it lands in `check` only. Measure the runtime first: it felt immediate here, but the gate is run
after nearly every edit and the corpus already shows sessions reaching for `| tail` on a gate they
find slow.]

**Answered 2026-09-04 by re-breaking the anchor and running both.** `docs.link-check` exits **0** on
the dangling anchor — it resolves files, not fragments — while `docs.build` exits **1** with
`anchor does not exist`. So there is no overlap and no cheaper substitute: `docs.build` is the task
to add, and adding `link-check` instead would produce a gate that passes on exactly this bug.

[NEEDS CLARIFICATION: should the Pages workflow's failure be louder than a workflow conclusion?
Every other red signal in this repo reaches a session through the gate; this one reaches nobody
until somebody visits the site or runs a harvest. A `push`-triggered CI job that runs the same build
would fail the run people already watch, at the cost of building the docs twice.]

## Recommended direction

1. Time `inv docs.build` on a cold tree, then settle the `precommit`-vs-`check` question above with
   that number in hand.
2. Whichever it lands in, keep `docs.clean` adjacent so the gate does not leave `site/` behind for
   the next `git status` to report.
3. Note in `contributing/zensical.md` that a heading rename is an anchor change — the direction this
   repo has already documented is the opposite one (a green local build not implying a green
   deploy), and this is the same hazard from the other end.
