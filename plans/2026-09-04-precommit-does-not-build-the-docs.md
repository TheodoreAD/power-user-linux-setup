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

Since answered in `repo_tasks/docs.py` itself, which says it out loud: the fragment-stripping
helper's docstring is "`file.md#heading` verifies the file, never the heading, so a renamed heading
still passes." The gate's blindness here is documented behaviour, not an oversight to report
upstream.

[PITFALL: that helper was read as `_broken_link` and is `_bad_link` on `repo-tasks` `main` — the
pinned revision here was 119 commits behind at the time, and the rename is inside that gap. The
behaviour and the docstring are identical, so nothing above changes; the name is not cited here any
more precisely because a private helper's name is the least stable thing to hang a citation on.
**The copy of `2026-09-04-docs-build-in-the-quality-gate.md` now absorbed into `repo-tasks` still
says `_broken_link`** and is in that repo's tree rather than this one, so correcting it belongs to a
session working there.]

## Decision, 2026-09-04: it joins `check`, and `precommit` gets it for free — SUPERSEDED

**Read the revision below before acting on this section.** Its placement conclusion is overturned;
its measurements, its coverage bound and its dependency finding all still stand, which is why it is
kept rather than rewritten.

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

## Revision, 2026-09-04: `check` must not mutate, so it goes in `precommit` instead

**Raised by the user, and it overturns the decision above.** The earlier reasoning dismissed the
`site/` write because `.gitignore` covers it — that is the weak form of the objection. The strong
form is that `check` is the CI-style, read-only half by construction: it should be safe to run
concurrently, on a read-only checkout, twice with the same answer. "Nothing _tracked_ moves" is not
the same property, and building 3.3 MB into the working tree from a task documented as "no changes
written" is a category error whatever git thinks of the output.

### What the community does

The user's instinct is the mainstream design, not a purist preference. Three of the major static
site generators ship a parse-and-validate mode that is explicitly distinct from build:

| tool   | mode                      | what it does                                                                                                   |
| ------ | ------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Zola   | `zola check`              | "build all pages just like the build command would, but without writing any of the results to disk"            |
| Sphinx | `sphinx-build -b dummy`   | "produces no output. The input is only parsed and checked for consistency" — documented as the linting builder |
| Hugo   | `--renderToMemory` / `-M` | renders without writing; `-d/--destination` redirects output when it does write                                |

So "the checker validates, the builder writes" is a shape these tools converged on independently.

### Except that our tool cannot do it, measured rather than assumed

**MkDocs has no check or dry-run mode at all** — its only lever is `-d`/`--site-dir` to redirect
output elsewhere. **Zensical 0.0.44 has neither.** `zensical build` takes exactly
`-f/--config-file`, `-c/--clean` and `-s/--strict`; there is no output-directory flag. Probed on
2026-09-04:

- `site_dir` is an `mkdocs.yml` key, and `config.py` rejects only a `..` in it — an absolute path
  passes validation. **It then panics**: `invariant: Format(Path(RootDir))` at
  `crates/zensical/src/workflow.rs:238`, a Rust invariant violation rather than a clean error. Worth
  reporting upstream on its own account.
- A _relative_ alternate `site_dir` works fine (built clean into `.zensical-check`), but that is
  still a write inside the repo.
- The alternate config file has to sit in the repo root regardless: `project_root` is
  `os.path.dirname(config_path)`, so a config in `/tmp` makes `docs_dir` resolve under `/tmp` too
  and the build fails on a missing docs directory.

**So there is no way to make this check non-mutating with zensical today.** The achievable property
is "leaves no net change", not "writes nothing".

### The comparison shape does not transfer here

The user's own framing — "not sure how we can do check without comparison" — names the pattern this
repo already uses for `catalog.render-tasks` and `devcontainer.render-docs`: `fix` regenerates,
`check` re-renders and fails on a diff. **That works only because those outputs are committed.**
`site/` is deliberately gitignored, so there is nothing to compare a fresh build against, and
committing a 3.3 MB build output to get a comparison target would be a far worse trade than the one
being avoided.

### What actually changed the answer: CI already catches it, and can now be seen doing so

The original argument for `check` was that it "fails the run people already watch". That was
under-weighted twice over. **`Deploy docs to GitHub Pages` already runs `zensical build --strict` on
every push to `master`** — CI has always caught this; the complaint was only that a workflow
conclusion nobody reads is a poor signal. And as of this same day `inv ci.status` is wired into this
repo (`633be03`), which prints the latest run's **annotations and failures across every workflow** —
so the Pages failure is now visible from the terminal, which is the gap that made moving the build
into the gate look necessary.

[DECISION: **`docs.build` joins `quality.precommit`'s pre-chain, not `quality.check`'s.**
`precommit` is `pre=[fix, check]` and already mutates by construction, so a build there is
consistent; `check` stays read-only and CI's `quality` job stays clean. The local pre-commit catch —
the one that would have prevented both red deploys — is fully preserved, since nobody pushes without
running `precommit`. This reverses the "it goes in `check`" decision above, which was made on the
gitignore argument before the read-only principle was raised.]

[PITFALL: **the cost is pull requests.** `Deploy docs to GitHub Pages` triggers on push to
`master`/`main` only, so a PR gets no docs build from either side once `check` is out of the
picture. Low impact here — this repo pushes direct to `master` by its own stated convention — but it
is a real hole for any consumer that reviews by PR, and it is the one thing the `check` placement
would have covered. A consumer that wants it adds `pull_request` to its Pages workflow's triggers,
or runs `inv docs.build` as its own CI step, rather than putting a mutating task in the shared
gate.]

[UNVERIFIED: whether a later zensical grows a real check mode, which would retire all of this. None
was found in its issue tracker on 2026-09-04, and the pin here is 0.0.44 against a current 0.0.59 —
so the probes above should be re-run at the next version bump before the workaround is treated as
permanent. `invalid_link_anchors` is on by default and is the check that catches the dangling
anchor, per zensical's validation docs, so the behaviour being relied on is documented rather than
incidental.]

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
2. **`repo-tasks`: add `docs.build` to `quality.precommit`'s pre-chain — _not_ `check`'s** (see the
   revision above; `check` must stay read-only and zensical offers no way to build without writing).
   Guarded so it no-ops on a consumer with no `mkdocs.yml` (`scaffoldapy`'s template makes the docs
   site conditional on `with_docs`, so the docs-less consumer is real) — the graceful-degradation
   shape `shell_check` already uses for a repo with zero `.sh` files, per this repo's cross-repo
   family convention. Concretely `pre=[fix, check, docs_build_if_configured]` rather than a new
   member of `check`'s list.

   **Filed as `plans/2026-09-04-docs-build-in-the-quality-gate.md`, now absorbed into `repo-tasks`'
   own `plans/`** rather than implemented here, since writing into another repo's tree is out.
   **That filed copy still says `check`** — it was written before this revision — so it needs the
   correction along with its stale `_broken_link` citation, and both belong to a session working
   there.
3. ~~Note in `contributing/zensical.md` that a heading rename is an anchor change.~~ **Landed
   2026-09-04**, as a subsection under `--strict is aggressive, in a good way` — the two red
   deploys, why `link-check`/`dprint`/`pytest`/a reviewer each structurally miss it, and the manual
   grep-plus-`docs.build` step that stands in until step 2. `CONTRIBUTING.md`'s existing gate
   warning points at it.

   The framing this step was written with is stale, and worth saying so: it expected to contrast
   with a documented "green local build does not imply a green deploy", which was the _version
   drift_ warning step 1 deleted. What is left to contrast with is the gate warning — a green
   `precommit` not implying a green deploy — which is the same hazard and a narrower one.
