---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/agent-skills
source_session: 7edc112d-9033-4253-b9ff-0c75fd61c23e.jsonl
source_moment: 2026-09-18T14:40:00+03:00
source_plan: plans/2026-09-13-repo-visual-assets-process.md
---

# Pilot the visual-assets process here, and settle what a NightCafe download actually carries

## Context

`agent-skills` is designing a skill that tracks what images each repo needs, which prompt produced
each candidate, and **why the rejected ones were rejected** — the record the user asked for on
2026-09-13, and the one thing none of the three repos that met this problem separately currently
keeps. The design is in that repo's `plans/2026-09-13-repo-visual-assets-process.md`.

**This repo is the first pilot, by the house rule that a convention is applied to one real,
already-working repo before it becomes a shareable artifact.** It was chosen because it already has
the most-developed brief: three visual directions, roughly twenty prompts, a measured palette,
NightCafe-specific prompt rules, and the licence audit in which only four marks of twenty clear a
zero-risk bar. Those live in `plans/2026-09-02-project-imagery-prompts.md` here.

Settled in `agent-skills` on 2026-09-18, so the pilot does not need to re-decide it: **the images
are their own skill.** `trigger.py split` over 19 cases at 3 runs each scored a proposed
`repo-assets` description against the whole installed set — 21 of its 24 runs at precision 1.0, no
case contested with `repo-pitch`, and no false positive on any should-not-trigger case.

## Evidence

- The design, the catalogue of surfaces and the manifest sketch:
  `agent-skills/plans/2026-09-13-repo-visual-assets-process.md`.
- The brief this pilot runs against: `plans/2026-09-02-project-imagery-prompts.md` here, with the
  licence audit in commit `7d555ce` and the NightCafe prompt rules in `437e347`.
- The prior-art pass, done over the research library's clones 2026-09-18: 27 `SKILL.md` files across
  eleven skill corpora name a visual surface and a tracking word, and **none tracks a repo's image
  needs or records which candidate was kept**. `openai/codex`'s `imagegen` sample states the
  opposite policy outright — _"Discarded variants do not need to be kept unless requested."_

## What a NightCafe download carries: nothing

**Answered 2026-09-20**, in the `agent-skills` session that wrote the design, from three creation
links the user supplied. The answer **refutes** the premise this section was written on. The plan
had expected the file to carry a C2PA manifest or an SD-style text chunk, so that `model`,
`generated` and `prompt` could be read from it; that claim was search-summary depth. Merged here
2026-09-28 from the filed `2026-09-22-nightcafe-metadata-answered-start-with-style-reference.md`,
which is now deleted.

- **The delivered file carries no provenance at all.** It is a JPEG, not a PNG. Walked segment by
  segment: `FF D8 FF DB`, straight from start-of-image to a quantisation table, with no EXIF, no
  XMP, no JUMBF/C2PA and no text chunk. Requesting the untransformed original with `?tr=orig-true`
  returns a larger file (627,995 bytes against 310,931). Its only extra segments are a JFIF header
  and a comment reading `CREATOR: gd-jpeg v1.0 (using IJG JPEG v6…)`. **The served file is a GD
  re-encode**, which is where any generator metadata was lost.
- **So prompt, seed and model cannot be read from the download.** The creation page carries the
  prompt, the model and the aspect ratio publicly, but **no seed**. A batch therefore has to be
  recorded when the prompt is handed out, not reconstructed at triage from the files.
- **Two hosts, two access rules.** `images.nightcafe.studio` serves a plain unauthenticated request
  (stdlib `urllib` is enough). `creator.nightcafe.studio` refuses one with 403 and needs a
  browser-shaped fetch. A fetch script downloads bytes and must not plan to scrape the page.
- **Durability holds**: a three-year-old creation still resolves with its prompt and model, which is
  what the design's "the generator is the archive" decision rests on.
- **1600 on the long edge is what came back**, for a 1:1 creation at the account's `High` initial
  resolution, in both URL forms.

So the design's §2 and §4 keep the user typing the record at handoff, and what matters most is still
**why this one and not that one**.

## Open questions

[NEEDS CLARIFICATION: **does NightCafe offer a start image or style reference on the models in use,
and at what strength?** This is now the question that decides whether "one theme, variations per
module" is a procedure or a hope. The user's stated direction is a banner-sized evocative scene per
repo, with variations for bare metal, WSL and dev container. NightCafe's terms discuss input images
explicitly, so the feature exists in some form. Which models accept one is unchecked, and only the
account holder can see it inside the app.]

[NEEDS CLARIFICATION: **what a 16:9 generation returns, and what the upscale step produces.** The
1600 ceiling above was measured on a square creation. It matters only if a docs site appears:
`agent-skills`' design cut the hero and the oversized targets, and every surface that renders today
fits inside 1600 with no upscale.]

[NEEDS CLARIFICATION: **where tried-but-not-kept images live.** Not in git — binary churn that is
not an asset. The candidates named in the design are `plans.py attach --local` (already copies a
file outside every repo and records a sha256, but ties it to a plan that will retire), an XDG data
directory keyed by repo, or keeping only the reason and not the file. The pilot is what decides
this, because it is the first time anyone actually has rejects in hand.]

[NEEDS CLARIFICATION: **the manifest's format and path** — TOML matches this family, YAML sits
beside `_brand.yml` which has a schema and consumers; `assets/`, `docs/assets/` or
`.github/assets/`. Decide by writing one here by hand and seeing what reads it.]

## Recommended direction

1. **Answer the style-reference question, in the app.** The metadata dump that used to be step 1 is
   done (above), and this is now the step that can change the design.
2. **Write this repo's manifest by hand** — its real slots are the social preview, the docs hero,
   the card set, the logomark and the drift banner — with the prompt files beside it, joined and
   paste-ready rather than composed from three parts at use time.
3. **Run one real handoff**: generate, accept one, reject the rest **with reasons**, and note every
   step that was tedious. The tedium is the specification for the script.
4. **Only then** does `agent-skills` script it. Report back by filing a plan there rather than
   editing that repo.
5. **Do not move the references yet.** The design wants this repo's marks-tier table and NightCafe
   notes to become the skill's `references/` when `plans/2026-09-02-project-imagery-prompts.md`
   retires. That is a copy at retirement time, not now, and this note exists so that plan's session
   knows the destination.
