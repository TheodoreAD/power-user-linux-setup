---
status: idea
updated: 2026-09-05
---

# RETRACTED, and replaced: this machine runs auto mode, so there was never a control group

The filename and the original claim are kept because both were committed and pushed before the error
was found, and a retraction that hides what it retracts is worse than the error.

## What was claimed, and why it was wrong

The claim, committed 2026-09-05 as `64757d7`: auto mode withdraws `Grep`/`Glob`, so comparing
auto-mode sessions against normal ones is a natural experiment for the `Grep`-over-`grep`
preference; standalone Bash searches came out at 19% in auto and 18% in normal, so the preference
was inoperative.

**There was no normal group.** Auto-mode sessions were detected by grepping transcripts for the
system note `"While auto mode is active"`, which is present in only a fraction of them — 11 of 64.
The remaining ~53 auto sessions fell into the "normal" bucket, so the comparison was auto against
auto and the matching rates are exactly what that predicts. The user said so directly on reading the
result: _"i've been running auto mode almost all the time"_.

[PITFALL: **the transcript records `permissionMode` on its own records, and that is the field to
use.** Attributing each Bash call to the mode in force at its timestamp — bisect the session's
`permissionMode` timeline, since the mode changes mid-session — gives the real picture for the seven
days to 2026-09-05:

| mode in force | Bash calls | share   |
| ------------- | ---------- | ------- |
| `auto`        | 13,193     | **96%** |
| `acceptEdits` | 547        | 4%      |
| unknown       | 14         | 0%      |

By session: **51 of 61 purely auto**, 7 mixed, 2 purely `acceptEdits`. A prose grep for a system
note is not a mode detector, and the failure is silent — it produces a plausible minority rather
than an error.]

## What the corrected number actually means, which is bigger than the retracted claim

[DECISION: **`setup.toml` declares a default mode that governs 4% of this machine's Bash calls.**
`claude_default_mode = "acceptEdits"`, with a comment naming it as _"the model the cli-allowlist
pipeline, `mode_covered`, and the scratch directories below are designed around"_ and recording that
`auto` _"was dropped 2026-08-24 after a 4-day transcript audit"_. `~/.claude/settings.json` agrees:
`defaultMode: acceptEdits`. The machine has nonetheless run auto for 96% of its Bash calls since.
The declared configuration and the operating reality have diverged, and every design that rests on
the declared one needs re-reading against the real one.]

[PITFALL: **the `cli-allowlist` allow/ask table is largely not what decides.** In auto mode a
classifier decides instead. Measured: **43 of 46 `find` calls ran under auto**, so `Bash(find:*)` —
which classifies `dangerous` for `-delete`/`-exec` and renders as `ask` — governed at most the 3
that did not. This corrects a claim made earlier the same day in
`plans/2026-08-29-fd-clause-adherence-and-search-tool-pricing.md`, that the pricing lever had
already been pulled and failed. It has not been pulled in the mode that actually runs. What the
pipeline still buys under auto, and whether that justifies its size, is now an open question rather
than an assumption.]

[PITFALL: **every Bash-versus-tool rate in this corpus was measured under a system reminder asking
for the opposite.** Auto mode's note asks the agent to read with `cat`/`head`/`sed -n`, search with
`grep`/`find`, and edit with `sed`/heredocs rather than Read/Edit/Write. At 96% that is not a
confound to correct for, it is the condition the whole corpus was measured in. `sed-n` (754),
`cat-view` (203), `heredoc` (1,641) and `grep/find` (3,220) are therefore **not** clean adherence
figures against `~/AGENTS.md`; they are the sum of a rule and a live instruction pulling opposite
ways, and no split of that sum has been measured.]

## Open questions

[NEEDS CLARIFICATION: **whether the `fd` reword landed earlier today is fighting a live system
reminder**, which `session-bash-audit`'s own routing table says not to do — "the harness itself
instructs the opposite (auto mode's 'prefer Bash' reminder) → the mode, not the wording". Auto mode
names `find` explicitly. `~/AGENTS.md` already anticipates this and says the `rg`/`fd` preferences
still govern how a search is spelled, so the reword is not straightforwardly void — but it is now a
rule competing with a reminder in 96% of calls rather than in a minority, and the 2026-09-12 reading
has to be interpreted in that light.]

[NEEDS CLARIFICATION: **whether the declared default should change, or the practice.** Setting
`claude_default_mode = "auto"` would make the declaration honest and let the allowlist pipeline be
re-scoped to what it actually governs. Leaving it and changing the practice keeps the pipeline's
design intact. The 2026-08-24 audit that dropped `auto` reached its conclusion for reasons that are
written down in `session-bash-audit`'s `references/research.md`; those reasons need re-reading
before either answer, because they were about the same Bash-versus-tool behaviour this note has just
shown was never cleanly measured.]

[NEEDS CLARIFICATION: **the user's stated reason for staying in auto — web search and retrieval
going through the classifier — has not been characterised.** Stated 2026-09-05: _"i don't know how
to solve the web searches and retrievals, which now go through the model classifier in auto"_. Until
it is known whether that is denials, latency, or prompts, no recommendation about the mode is worth
making, because the mode is being chosen to work around it.]

## Recommended direction

Re-run every adherence figure in this cluster with per-call mode attribution before drawing anything
further from it, and treat the `2026-09-12` readings promised by today's two rule changes as
auto-mode readings rather than machine-wide ones. Then characterise the web-search friction, because
the mode question cannot be answered underneath it.
