---
status: in-progress
updated: 2026-08-30
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

## The pass as agreed (2026-08-30)

Three decisions taken with the user, which close the three questions this plan opened with.

[DECISION: **no rule is cut, and size is not the target.** Asked to choose a byte target, the user
declined one outright: "we have to figure out a way to keep all these hard-earned rules." So the
pass keeps every rule and every distinct claim, and any byte reduction is a by-product to be
measured rather than a goal to hit. This retires the "shorten in place" lever except where a claim
is genuinely stated twice, and it defers demotion-to-skills indefinitely rather than rejecting it.]

[DECISION: **merge near-duplicates first**, chosen by the user over demotion and over shortening.
This is the lever the research already favoured for adherence (~4–7pp, SCALEDIF) and it is the only
one compatible with the decision above — merging removes a claim's second statement, never the
claim.]

[DECISION: **one approval round per cluster**, not per rule and not one diff at the end. At ~22
candidate rules a per-rule pass was judged impractical, and a single end-of-pass review would defer
every "nothing is deleted without asking" judgement to one large read.]

The Codex 32 KiB cut recorded above is **latent, not live** — `~/.codex` does not exist on this
machine, so nothing is being truncated today. It is a reason to keep the file's growth visible, not
a reason to cut, and treating it as a deadline is what the decision above rejects.

## The merge inventory

Six claims stated more than once across the assembled file, found by reading all three fragments in
full. The first three were done in round 1; the last three are round 2.

| #     | the claim stated twice or more                                                             | rules involved                                                                            |
| ----- | ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| A     | the tool already reports the exit code; `echo $?`/redirect add nothing; a pipe destroys it | Composing a Bash call · Viewing, searching, or editing files · Reading a command's result |
| B     | don't `\| head` your own search; count first                                               | Viewing, searching, or editing files · Generalizing from a sample to a set                |
| **C** | **whether cwd persists between Bash calls — a contradiction**                              | Composing a Bash call · Running a command against a different repo                        |
| D     | `git commit` ships the index, not the paths you named                                      | Committing multi-part work · Unexplained git/file state in a working tree                 |
| E     | a ref handed to git is read (`rev-parse`), never derived by eye                            | Force-pushing · Unexplained git/file state in a working tree                              |
| F     | parallel sessions on this machine share one working tree                                   | Force-pushing · Unexplained git/file state · Running a command against a different repo   |

[PITFALL: **C was a contradiction, not a duplication, and had gone unnoticed because the two halves
sat in different clusters.** "Composing a Bash call" asserted that cwd persists "on current builds";
"Running a command against a different repo" recorded both behaviours observed in one session on one
build and said to assume neither. A reader scanning for a cwd answer got whichever rule they hit
first. Finding it took reading all three fragments end to end — no per-rule review would have
surfaced it, because neither rule is wrong when read alone.]

Deliberately **not** merge candidates, checked and rejected: the Bash rules restated inside "Which
sessions load this file" (a deliberate paste-in for `Plan`/`Explore` subagents, which never load
this file, so the restatement is the only copy that reaches them), and the auto-mode paragraph's
reference to the `rg`/`fd` preferences (a pointer, not a second statement).

## Round 1 — Bash & tool use + Verification (landed 2026-08-30)

Taken as one round rather than two because both A and B straddle the cluster boundary: the
duplicated claims are Bash rules restated in Verification rules.

- **A** — canonical home is "Reading a command's result", unchanged. "Composing a Bash call" keeps
  the imperative and points at it (85 → 40 words); "Viewing, searching, or editing files" keeps the
  prohibition alone (55 → 15).
- **B** — canonical home is "Viewing, searching, or editing files", unchanged. "Generalizing from a
  sample to a set" keeps what is distinctive to it, the _inference_ that a truncated result stops
  being evidence about the set, and points at the other rule for the mechanics.
- **C** — resolved in favour of the researched position; "Composing a Bash call" now says to treat
  cwd as unknown after a cross-repo chain.

Measured before and after, assembled: **39,536 → 39,176 bytes** (−360), 6,343 → 6,274 words, 597 →
595 lines, 38 rules unchanged. The byte yield is far below the ~1,150 estimated from the removed
prose, because the pointers added back and dprint reflowed; worth knowing before anyone plans a
round around a predicted saving.

[UNVERIFIED: whether round 1 helped, hurt, or did nothing to adherence. A is the interesting one —
its `echo $?` shape was measured at 10–11% of Fable/Opus calls in the day a contradictory version
was live, so it is a rule with a known miss rate whose explanation now exists in one place instead
of three. `session-bash-audit` can measure the `echo-exit` and `redirect-then-filter` rates after
this has been deployed a while; that measurement is what closes this tag.]

## Round 2 — Git & commits (landed 2026-08-30)

D and E applied; **F deliberately skipped**.

- **D** — the merge that improved both rules rather than only shortening one. The subject had been
  split down the middle: "Committing multi-part work" named the failure (`git commit` ships the
  index) and offered only "stage late" against it, while "Unexplained git/file state" held the
  remedy (`git commit -m "…" -- <path>`) framed purely as parallel-session defence. The remedy moved
  to the commit-splitting rule, which is the heading a session constructing a commit actually
  consults; the parallel-session rule keeps what is specific to it and points.
- **E** — "Force-pushing" now opens by stating the principle (every ref you hand git is one you
  read, never one you derived) with the lease as its first instance, so "Unexplained git/file state"
  can cite it instead of restating `rev-parse` and claiming kinship.

[DECISION: **F was rejected, not deferred.** "Parallel sessions share one working tree" is stated in
about eight words in each of two rules, as the premise for two different consequences. Replacing
either with a pointer costs the reader the premise at the moment they need it, to save under a line
— the merge criterion is a claim stated twice, not a fact mentioned twice, and a premise short
enough to restate is cheaper in place than behind a reference.]

[PITFALL: **a rule can have no entry in `contributing/global-agents-md.md` at all, and nothing
reports it.** "Force-pushing, or asking what a remote actually has" had none — its evidence sat
inline in the deployed file, which is the arrangement the whole split exists to prevent. Found only
because round 2 went looking for the heading to write under. The `## Contents` list in that file is
also incomplete by several sections, so it cannot be used to answer "does this rule have evidence?"
either.]

## Open questions

## Rules with no evidence section (measured 2026-08-30)

Run after round 2 turned one up by accident. Comparing the `###` headings across the three fragments
against the `##` headings in `contributing/global-agents-md.md`: **11 of 38 rules have no matching
section.** Two of those carry dated provenance inline in the deployed file, which is precisely the
arrangement the fragment/evidence split exists to prevent:

| rule                                                | inline provenance     |
| --------------------------------------------------- | --------------------- |
| Committing to a repo that is or might become public | `Measured 2026-08-28` |
| The permission model in force                       | `Measured 2026-08-30` |

The other nine carry none, and most are correctly evidence-free — `sudo` is a two-line exact
instruction with its own worked example, "Caveman-style terse output" and "Invited to push back" are
stated user preferences rather than findings, and "Where durable knowledge goes" has evidence filed
under the evidence file's older heading for it ("Saving to cross-session memory"), so the heading
correspondence the file's own convention asks for has drifted through a rename rather than gone
missing.

### Done 2026-08-30, immediately after the merge pass

Both blocks relocated, the drifted headings reconciled, and the check made mechanical as
`tests/unit/test_agents_md.py` — four tests reading the real repo files, since the invariant is
about this repo's content rather than any function's behaviour:

- every rule has an evidence section, or is named in an `_EVIDENCE_FREE` list of rules that rest on
  no measurement (8 of 38: exact instructions carrying their own example, and stated preferences);
- every evidence section still matches a live rule — the direction that catches a rename;
- `_EVIDENCE_FREE` names no rule that has since been deleted, so an exemption cannot outlive its
  rule and hide the next one;
- no _new_ dated provenance appears inline in a fragment.

`Committing to a repo that is or might become public` and `The permission model in force` now have
sections of their own, with `Data flowing outward to a vendor` and `Auto mode withdraws Grep` folded
under them as `###` subsections — both had been clause-named `##` headings, which is why the
correspondence check could not see the rules they belonged to. `Saving to cross-session memory` was
retitled to `Where durable knowledge goes`, the rule's name since it moved out of the Claude Code
cluster. The `## Contents` list lost its three stale rows and gained the new sections.

[PITFALL: **the heading check and the inline-provenance check find disjoint problems, and only
running both gives the real count.** The heading comparison found 2 rules carrying provenance
inline; the regex over the fragments then found 4 more, all in rules that _do_ have evidence
sections — invisible to the first check by construction. The first estimate was therefore wrong by
3× in the direction that reads as "nearly clean".]

[DEFERRED: **the four grandfathered inline-provenance sites** — one in "Reading a command's result"
(the `gh` poll loop), two in "git fetch/push needing an SSH key", one in "Installing a tool on this
machine". They are a different shape from the two that moved: each is woven into the sentence
carrying the instruction rather than being a standalone incident paragraph, and in the ssh case the
incident is plausibly what does the deterring — a session that has just read about three passphrase
dialogs behaves differently from one that has read a reference to them. Moving them is a content
decision the user has not been asked for; they are enumerated in the test so the list cannot grow
while it is open.]

[NEEDS CLARIFICATION: does merging alone reach a shape worth stopping at? Six merges is the whole
inventory, and round 1's three yielded 360 bytes. If D–F land in the same range the file finishes
this pass around 38 KB with 38 rules — every rule kept, which is what was asked for, but still ~2×
the review reference points and still over the latent Codex cut. Decide at the close whether that is
the intended resting state or whether a further lever gets reopened.]

[NEEDS CLARIFICATION: which rules are demotion candidates under the tier test — sharp statable
trigger, cheap and recoverable miss? Deferred rather than answered by the decisions above, and worth
keeping only if the question above reopens it. `Bash & tool use` is the biggest cluster and the one
with a topic-owning skill (`session-bash-audit`) that can both hold guidance and _measure_ whether
moving it made adherence worse. That makes it the safest place to try demotion, and the riskiest to
get wrong, since its rules were rewritten specifically because they were being missed.]

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
