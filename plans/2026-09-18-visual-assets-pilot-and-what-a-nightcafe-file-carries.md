---
status: idea
updated: 2026-09-18
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

## The one question only this repo can answer

**Does a real NightCafe download already carry the record?** Major generators now embed a signed
C2PA manifest (tool, model, timestamp) and Stable-Diffusion-family pipelines write the prompt,
negative prompt, seed, sampler and model into a PNG text chunk. NightCafe runs SD-family models. If
that holds for the user's own downloads, then `model`, `generated` and possibly `prompt` in the
manifest's `tried` blocks are **read from the file** rather than typed, and the only thing the
handoff genuinely needs from the user is **why this one and not that one**.

That changes the design's §2 and §4, so it is worth answering before anything is scripted, and it
needs exactly one file that only this machine's user has.

[UNVERIFIED: **the claim above is search-summary depth and no better.** The searches behind it
returned mostly metadata-remover SEO pages. Do not write it into any skill until a real file is
read.]

**The check, and the constraint on it.** No `exiftool`, no `c2patool` and no Pillow are installed on
this machine (verified 2026-09-18), so a stdlib PNG chunk walk is the only zero-install route: read
the 8-byte signature, then each chunk's length and 4-byte type, and print the types with the
contents of any `tEXt`/`iTXt`/`zTXt`. A `caBX` chunk is the C2PA manifest's container — its presence
is detectable this way, and **its signature is not verifiable without `c2patool`**, so a check must
not claim the credential is valid, only that one is there.

## Open questions

[NEEDS CLARIFICATION: **where tried-but-not-kept images live.** Not in git — binary churn that is
not an asset. The candidates named in the design are `plans.py attach --local` (already copies a
file outside every repo and records a sha256, but ties it to a plan that will retire), an XDG data
directory keyed by repo, or keeping only the reason and not the file. The pilot is what decides
this, because it is the first time anyone actually has rejects in hand.]

[NEEDS CLARIFICATION: **the manifest's format and path** — TOML matches this family, YAML sits
beside `_brand.yml` which has a schema and consumers; `assets/`, `docs/assets/` or
`.github/assets/`. Decide by writing one here by hand and seeing what reads it.]

## Recommended direction

1. **Dump one real NightCafe download's metadata** and answer the question above. It is the cheapest
   step and the only one that can change the design.
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
