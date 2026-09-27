---
status: idea
updated: 2026-09-22
source_repo: github.com-personal/agent-skills
source_session: 7edc112d-9033-4253-b9ff-0c75fd61c23e.jsonl
source_moment: 2026-09-20T13:20:00+03:00
source_plan: plans/2026-09-13-repo-visual-assets-process.md
---

# The pilot's first step is already answered; start it at the style-reference question instead

**Belongs to `2026-09-18-visual-assets-pilot-and-what-a-nightcafe-file-carries.md`**, absorbed into
this repo. Merge this into it rather than keeping two files.

## What changed

That plan's step 1 was "dump one real NightCafe download's metadata", called the cheapest step and
the only one that could change the design. **It was done on 2026-09-20**, in the `agent-skills`
session that wrote the design, using three creation links the user supplied — so the pilot should
not spend its first move on it.

## What the dump found

- **The delivered file carries no provenance at all.** Walked segment by segment: `FF D8 FF DB`,
  straight from start-of-image to a quantisation table. No EXIF, no XMP, no JUMBF/C2PA, no text
  chunk. Requesting the untransformed original with `?tr=orig-true` returns a larger file (627,995
  bytes against 310,931) whose only extra segments are a JFIF header and a comment reading
  `CREATOR: gd-jpeg v1.0 (using IJG JPEG v6…)` — **the served file is a GD re-encode**, which is
  where any generator metadata was lost.
- **So prompt, seed and model cannot be read from the download.** The creation page carries the
  prompt, the model and the aspect ratio publicly — and **no seed**. A batch therefore has to be
  recorded when the prompt is handed out, rather than reconstructed at triage from the files.
- **Two hosts, two access rules.** `images.nightcafe.studio` serves a plain unauthenticated request
  (stdlib `urllib` is enough); `creator.nightcafe.studio` refuses one with 403 and needs a
  browser-shaped fetch. A fetch script downloads bytes and must not plan to scrape the page.
- **Durability holds**: a three-year-old creation still resolves with its prompt and model, which is
  what the "the generator is the archive" decision rests on.
- **1600 on the long edge is what came back**, for a 1:1 creation at the account's `High` initial
  resolution, in both URL forms.

## What the pilot should start with instead

[NEEDS CLARIFICATION: **does NightCafe offer a start image or style reference on the models in use,
and at what strength?** This is now the question that decides whether "one theme, variations per
module" is a procedure or a hope — the user's stated direction is a banner-sized evocative scene per
repo, with variations for bare metal, WSL and dev container. NightCafe's terms discuss input images
explicitly, so the feature exists in some form; which models accept one is unchecked and is visible
only inside the app.]

[NEEDS CLARIFICATION: **what a 16:9 generation returns, and what the upscale step produces.** The
1600 ceiling above was measured on a square creation. It matters only if a docs site appears —
`agent-skills`' design cut the hero and the oversized targets, and every surface that renders today
fits inside 1600 with no upscale.]

## Recommended direction

1. Merge this into the pilot plan and delete it.
2. Start the pilot at the style-reference question, in the app, since only the account holder can
   see it.
3. Then the manifest by hand, and one real handoff with reasons recorded for the rejects — unchanged
   from the pilot plan.
