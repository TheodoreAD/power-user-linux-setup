---
status: idea
updated: 2026-09-05
---

# What the docs-site usability pass left open: cross-cutting navigation, and ten `mkdocs.yml` TODOs

## Context

Split out of `2026-08-27-docs-site-usability.md` on 2026-09-05 so that plan can retire. That pass
landed its seven-step direction; these are the two things it named and deliberately did not settle,
and they had no home outside a `landed` plan — which is exactly the content a retirement would have
dropped.

Its third open item, the doubly-declared zensical pin, **was** closed on 2026-09-04 (a `docs`
dependency group in `pyproject.toml`, `requirements-docs.txt` deleted) and needs no home here.

## What is open

**1. Search carries all cross-cutting navigation, because zensical has no `tags` plugin.** The
usability review named this as problem 7. A reader who wants "everything about fonts" or "everything
corporate-network" has the site's search box and nothing else — no tag index, no see-also.
`zensical`'s plugin support is a small hardcoded allowlist rather than the mkdocs plugin ecosystem
(`search`, `offline`, `autorefs`, `mkdocstrings`, `markdown-exec`, `glightbox`, `macros` — see
`contributing/zensical.md`), and `tags` is not in it, so this cannot be closed by adding a plugin.
Either it stays search-only, or cross-cutting entry points are hand-written pages.

**2. Ten `mkdocs.yml` TODOs.** The original pass classified these as "the author's own open
intentions rather than defects", which is why they were not actioned. They are still in the file.

## Open questions

[NEEDS CLARIFICATION: is problem 7 worth solving at all, or is search genuinely sufficient for a
41-page site? The review asserted the gap; nothing has measured whether a reader hits it. A
hand-written index is real maintenance, and the failure mode of a stale one is worse than no index.
Worth deciding before doing, since the doing is cheap and the upkeep is not.]

[NEEDS CLARIFICATION: do the ten TODOs still reflect current intentions? They predate the zensical
migration, the nav re-cut, the package catalog and the `docs` job — several may already be done,
moot, or contradicted. Read them against the current file before treating the count as work.]

## Recommended direction

1. Read the ten TODOs and sort them into done / moot / real, which is likely to shrink the list
   substantially and costs one pass over `mkdocs.yml`.
2. Decide problem 7 on evidence rather than on the review's assertion — if the site's own search
   answers "fonts" and "corporate network" acceptably, record that and close it.
3. Anything real that survives both becomes its own step here, or its own plan if it grows.
