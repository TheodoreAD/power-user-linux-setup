---
name: research-library
description: 'Use when working with, adding to, or updating the shared cross-project research library at $RESEARCH_HOME (vendor repo clones, reference PDFs/epubs, mirrored docs pages) — before fetching the same material from the web, when cloning a reference repo for a project, or when asked to update/refresh the library.'
---

# Research library

`$RESEARCH_HOME` (default `~/research`) is a shared, cross-project store for reference material
that shouldn't live inside any single git repo: vendor repo clones, PDFs/epubs, mirrored docs-site
snapshots. It exists to avoid two things: (1) agents reading unvetted third-party content
ambiently just because it happens to sit inside a repo's working tree, and (2) every project
re-cloning the same reference material into its own gitignored folder.

## Before fetching anything from the web

Check `$RESEARCH_HOME/repos/`, `$RESEARCH_HOME/docs/`, and `$RESEARCH_HOME/pages/` for existing
material on the topic before reaching for WebFetch/WebSearch or cloning a fresh copy. A project's
own `AGENTS.md` may already point at the specific entry relevant to that project.

## Layout

```
$RESEARCH_HOME/
  repos/<host>--<owner>--<repo>/   # shallow git clones
  docs/<file>.pdf|.epub            # downloaded reference docs
  pages/<slug>/                    # mirrored/llms.txt-derived doc site snapshots
  README.md                        # full conventions + rationale
```

## Naming (repos)

Always `<host>--<owner>--<repo>` — every repo, every host, no exceptions, no GitHub special case.
Check the actual `origin` remote rather than assuming from the URL you were given; self-hosted
instances (e.g. `gitlab.gnome.org`) can look like they might be GitHub and aren't.

## Adding an entry

```
git clone --depth 1 <url> "$RESEARCH_HOME/repos/<host>--<owner>--<repo>"
```

Then write that entry's `SOURCE.md` (or a `<file>.source.md` sibling for a flat `docs/` file):

```
url: <repo or docs URL actually fetched from>
kind: repo-clone | llms-txt-mirror | site-mirror
ref: <branch/tag/commit for a repo-clone, or fetch date for a mirror>
fetched: <date>
note: <only when non-obvious — e.g. docs publish from a different branch/repo than what's cloned>
```

## Updating

Run `research-update` (on PATH via `~/.local/bin`) to refresh every clone under `repos/` to its
default branch's latest commit — a shallow fetch + hard reset, since these are disposable
reference clones, not working copies with local commits to preserve. If an entry looks
suspiciously stale after running it, check `git config --get-all remote.origin.fetch` in that
clone: a repo originally cloned with an explicit `--branch <tag>` keeps tracking only that pinned
ref forever, not the moving default branch, until the fetch refspec is corrected (find the real
default branch via `git ls-remote --symref origin HEAD`).

## No symlinks into project repos

Never symlink `$RESEARCH_HOME` or any entry in it into a project's working tree. That would put
this content back in the ambient read path of anything scoped to that repo — the entire reason it
lives outside every repo. Reach it by its `$RESEARCH_HOME` path directly, only when a task
actually calls for it.

## Full design rationale

See `reference/research-library-plan.md` in the `power-user-linux-setup` repo for the complete
design discussion — why this exists, alternatives considered and rejected (Context7, RAG/
embeddings), and the reasoning behind each convention above.
