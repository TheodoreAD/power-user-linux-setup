---
status: idea
updated: 2026-08-29
---

## Context

`~/AGENTS.md` measured **4,326 body words, 37 rules, 446 lines** across 8 clusters immediately after
the 2026-08-26 fragment split (`plans/2026-08-26-agent-artifact-authoring-decoupling.md`). Its own
review reference points, researched and recorded in `contributing/global-agents-md.md`, are **≤200
lines and ≤15 rules**. The last leanness pass (2026-08-23) landed it at ~2,500 body words / 30 rules
/ 294 lines, so it has grown by roughly 1,800 words and 7 rules since, with no review in between.

The split did not cause the growth — it moved rules between fragments and added none. It made the
growth visible, because `contributing/global-agents-md.md`'s measurement commands now read the
**assembled** result rather than a single source file, and that was the first time the current total
had been measured at all.

Re-measured 2026-08-29: **39 rules / 530 lines**, so it has grown by a further 2 rules and 84 lines
since this plan was opened, still with no pass in between.

This plan exists because that finding currently lives as a sentence in
`contributing/global-agents-md.md` ("A leanness pass on `portable.md` specifically is the obvious
next one"), which is exactly the "don't stash future work in prose docs" failure the `plan-docs`
convention names: prose future-work has no status field, so nothing ever prompts a return visit.

## A hard ceiling, not just a reference point (measured 2026-08-29)

The ≤200-line/≤15-rule numbers are review reference points and have never forced anything. There is
also a **hard byte limit already being exceeded**, and it is silent.

Codex CLI truncates an `AGENTS.md` at 32 KiB (`PROJECT_DOC_MAX_BYTES`, default), with no warning —
instructions past the cut are simply dropped. The deployed file is **35,498 bytes**, 2,730 over.
`~/.codex/AGENTS.md` is one of the four `symlink_dest` entries on `[packages.agents-md]`.

Where the cut lands, byte-exact: mid-word inside the `## Collaboration & output` heading. Codex
would therefore lose that **entire cluster** — "A narrow check grows into design work", "Invited to
push back", "Something the user wrote looks like a typo or mental slip", "Ending a turn with a next
step", and "Caveman-style terse output". The user-facing output style and the rule about not handing
the user a shell command to run are both past the cut.

Latent today: `~/.codex` does not exist on this machine, so the symlink is correctly skipped and no
agent currently reads a truncated copy. It arms itself the day Codex is installed, and it arms
silently — nothing in `verify.all` compares a destination against a reader's size limit, because
until now no limit was known.

Two consequences for this plan:

- The ordering question below acquires a bound. Getting under 32,768 bytes is a smaller ask than
  getting to 200 lines, it is objectively checkable, and it is worth doing even if the rest of the
  pass stalls.
- Per-reader limits belong in `contributing/global-agents-md.md` alongside the review reference
  points, and plausibly in a `verify.all` check. Other agents may have their own caps; only Codex's
  has been confirmed.

## Why it matters, not just "the number is over"

The reference points are not arbitrary. From the research already in
`contributing/global-agents-md.md`: **bloated instruction files cause models to ignore instructions
wholesale**, not to selectively filter the irrelevant ones, and recall degrades as context grows.
Overlapping near-duplicate rules are a measured driver of that degradation. So the cost of being 2×
over is paid on every turn of every session in every repo, silently, and the rules most likely to be
dropped are not the ones anyone chose to sacrifice.

Where the weight sits, from the per-section measurement:

| cluster                        | words |
| ------------------------------ | ----- |
| Bash & tool use                | 919   |
| Git & commits                  | 691   |
| Research & design              | 669   |
| Verification                   | 528   |
| This machine & this setup      | 485   |
| Collaboration & output         | 433   |
| Claude Code specifics          | 432   |
| Agent instructions & knowledge | 169   |

`portable.md` holds the top four and is the obvious target; `this-setup.md` and `claude-code.md`
together are under 1,000 words and are not the problem.

## Open questions

[NEEDS CLARIFICATION: which lever first — **merge near-duplicates**, **demote to skills**, or
**shorten in place**? The research says merging overlapping rules is the change most likely to
improve adherence (real but modest, ~4–7pp), while demotion is the only one that actually removes
words from the always-loaded set. Shortening in place is the one the same research warns against
where a rule has been observed being missed: "strengthen its language rather than lengthen its
explanation" cuts both ways, and several of these rules are long precisely because a shorter version
was already tried and missed.]

[NEEDS CLARIFICATION: which rules are demotion candidates under the tier test — sharp statable
trigger, cheap and recoverable miss? `Bash & tool use` is the biggest cluster and the one with a
topic-owning skill (`session-bash-audit`) that can both hold guidance and _measure_ whether moving
it made adherence worse. That makes it the safest place to try demotion, and the riskiest to get
wrong, since its rules were rewritten specifically because they were being missed.]

[NEEDS CLARIFICATION: does the per-rule approval requirement make a pass this large impractical in
one session? `contributing/global-agents-md.md` states that moving a rule out of the always-loaded
set needs the same per-rule user approval as deleting it, and that nothing is deleted without
asking. At ~22 candidate rules in `portable.md` that is a lot of decisions. Batching them into a
handful of `AskUserQuestion` rounds by cluster is probably the shape, but it should be agreed before
starting.]

## Additions parked pending this pass

Two cross-repo preferences surfaced 2026-08-26 (harvest of the `agent-skills` scoping session) that
would otherwise be appended to `portable.md` right now. Parked here instead, per `session-harvest`'s
"destination mid-restructure → the plan reshaping it" filter: appending while the file's shape is
being decided bypasses the admission gate this pass exists to apply, and risks the addition being
restructured away unread. Both are recorded today only as `[DECISION:]` tags inside
`plans/2026-08-26-agent-artifact-authoring-decoupling.md`, which means that on that plan's
retirement they land in a PULSE `contributing/` page — and a page in this repo never fires in
`repo-tasks`, `scaffoldapy`, or a `*-polite-mcp` repo. That reach gap is the argument for admitting
them; the file's size is the argument against. Decide both at this pass's close, against
`contributing/global-agents-md.md`'s "Admitting a new rule" criteria, not before.

[DEFERRED: **"No vendor lock-in — the artifact vocabulary is `AGENTS.md`, Agent Skills and MCP;
anything vendor-specific is admissible only as harness plumbing that makes an agent work better,
never as a carrier for instructions or knowledge."** Tier-1 shaped on the face of it: it can fire on
any turn in any repo, and its miss is silent and expensive — a session designs against a vendor
mechanism and the work is thrown away, which is exactly what nearly happened before the constraint
was stated. No topic-owning skill covers it. Trigger for the heading, if admitted: "Choosing a
mechanism for agent instructions, skills, or tools".]

[DEFERRED: **"Prefer the mainstream community tool, and have PULSE verify its result rather than
reimplement it."** A _variant_ of the existing "About to author content, config, or a workaround
from scratch" rule rather than a new one — that rule already says reuse maintained upstream work;
the new half is what to do afterwards, namely check the result rather than rebuild the mechanism.
Per the admission criteria a variant extends its rule's existing section, so if admitted this is a
sentence appended there, not a heading. Concrete instance to cite: the `skills` CLI announces a
Claude Code symlink it does not create, and PULSE's own `_ensure_agents_skills` covers the gap
instead of PULSE reimplementing skill installation.]

[DEFERRED: **"A probe you write to test a library's behaviour is a sample of one, and a passing
probe reads as confirmation — when the suspicion is about precision, width or a limit, the input has
to be one that can actually fail."** A _variant_ of the existing "Generalizing from a sample to a
set" rule, which already covers samples you created yourself; the new half is that a deliberately
constructed _probe input_ is such a sample, and that a green result is the failure mode rather than
an error. Per the admission criteria a variant extends its rule's existing section, so if admitted
this is a short paragraph appended there, not a heading — rule count unchanged.

Concrete instance to cite, measured 2026-08-29 in `ingesta`: a `Decimal` round-trip through
SQLAlchemy's SQLite dialect passed on ten significant digits and silently lost the value on nineteen
(`1234567890123456789.000000001` → `…768.0000000000`, no warning). The first probe used ten, so it
read as "`Numeric` is fine", and that conclusion was one step from being written into a shared skill
doc where nobody re-derives it. Silent and expensive miss; no topic-owning skill covers how to
choose a probe input.]

[DEFERRED: **The existing "never `cd` into the session's own repo" rule causes the behaviour it
bans, and needs a clause rather than a new rule.** Measured 2026-08-29 by `session-bash-audit` after
the user corrected a session mid-task ("you don't need cd, you're in this repo"): over two days and
2,077 calls, `cd` into the session's own repo occurred **14** times — agents comply — while
`git -C <own repo>` occurred **89** times, up to 18% of one session's calls. The same rule that bans
the `cd` recommends `git -C <path>` as the directory-scoping option for a cross-repo step, so agents
reach for that flag against their own repo six times as often as they ever ran the banned form. The
fix is one clause on the existing "Composing a Bash call" rule — `git -C` at the session's own repo
is the same mistake — so rule count is unchanged and only the line count moves. Parked here rather
than appended because this pass owns the file's shape and its admission criteria; the measurement
and its method are permanent in that skill's `references/research.md` either way, so nothing is lost
by deciding it at this pass's close.]

[DEFERRED: **On this machine a local commit is not a private holding state — a parallel session's
push publishes it.** A _variant_ of the existing "Unexplained git/file state in a working tree"
rule, whose last paragraph already covers the outward direction: a commit in your ahead-count may be
another session's, so ask before your push publishes it. The missing half is the inverse. Your own
commit sits on a shared branch in a shared clone, so any other session's `git push` carries it to
the remote regardless of whether you were holding it for approval. Per the admission criteria a
variant extends its rule's existing section, so if admitted this is a short paragraph appended
there, not a heading — rule count unchanged.

Concrete instance, 2026-08-29 in `agent-skills`: a session committed two skill edits and
deliberately did not push, because another session's commits sat under them and publishing was the
user's call. Minutes later the ahead-count was zero — the other session had pushed the branch and
carried both commits with it. Nothing signalled it, and an ahead-count falling to zero reads as
"someone pushed, fine" rather than as work published without the decision that was being waited on.
Verified after a fresh fetch with `git branch -r --contains <sha>`, not inferred from the count.

Silent by construction, and it meets the confidentiality rule at its sharpest point, since that rule
turns entirely on a push being irreversible. The consequence for whatever gets written: "I will
commit but not push, and ask first" is a stated intention, not a mechanism. A session that genuinely
must withhold work has to keep it off the shared branch — or tell the user before committing that
the commit itself is the publishing decision.]

## Demotion is not relocation at current trigger rates (measured 2026-08-29)

The tier-2 lever assumes a rule moved into a skill still fires. Measured across 415 Claude Code
transcripts on this machine — every `Skill` invocation, all time, against 15,171 Bash calls:

```
58  plan-docs            (largely explicit /plan-docs, not model-chosen)
 8  session-harvest
 7  research-library
 5  update-config
 2  invoke-task-conventions
 2  python-conventions
 2  reorder-suggest
 1  session-bash-audit / skill-authoring / db-defaults
 0  mcp-server-shipping
 0  polite-mcp-conventions
```

87 invocations total. Two skills have never fired. `python-conventions` fired twice, in a repo
family that is almost entirely Python — the under-triggering `agent-skills`'
`plans/2026-08-22-skill-trigger-quality-review.md` predicted, now measured rather than suspected.

So **demoting a rule out of this file today is closer to deleting it than to relocating it**, and
the rules most likely to be nominated for demotion are the ones with sharp triggers — which is also
what makes them look safe. The plan's own framing already warns that several rules in `portable.md`
are long precisely because a shorter version was tried and missed; a demotion is a stronger version
of that same bet.

This does not kill the lever, it orders it. The trigger layer has to be fixed and shown to work
before anything is demoted into it. That work is `agent-skills`' — its trigger-quality plan plus the
contention scanner filed alongside it 2026-08-29 — so this plan now has an out-of-repo dependency it
did not have when it was opened.

External numbers that bear on the same judgement, worth recording so the next pass does not
re-research them: ETH Zurich (Gloaguen et al., 2026) measured human-written agent context files at
**+4% task success for +19% cost**, and LLM-generated ones at **−3% for +20%**. The strong exception
was non-obvious tooling instructions — an instruction naming `uv` produced 1.6 invocations per task
against 0.01 without it. That maps cleanly onto this file: `sudo -A`, `inv ssh.check`, `LC_TIME=C`
are the high-return kind and should be the last things touched; the long design-heuristic rules in
"Research & design" (669 words) are the low-return kind and should be the first.

## Recommended direction

Rough. Measure first with the two commands in `contributing/global-agents-md.md`'s "Re-measuring the
deployed file", so before/after is comparable with the 2026-08-23 numbers. Then take one cluster at
a time, largest first, and for each rule ask only the tier question — is the miss silent and
expensive, or sharp-triggered and recoverable? Merge before demoting, demote before shortening, and
re-measure after each cluster rather than at the end, so a pass that stops early still leaves the
file better than it found it.

Revised 2026-08-29, on the two measurements above: **get under 32,768 bytes first**, by merging and
shortening only. That is 2,730 bytes, it removes a live latent defect, and it needs no decision
about tiers. **Hold every demotion** until the trigger layer is measurably working — otherwise the
pass trades a bloat problem for a silent-deletion problem, and the deletions will not be the rules
anyone chose.

Do not treat the ≤200/≤15 numbers as a target to hit in one go. They are review reference points,
and the discipline that actually keeps the file small lives upstream in the admission criteria — a
pass that trims 1,000 words while the intake gate stays open just schedules the next pass.
