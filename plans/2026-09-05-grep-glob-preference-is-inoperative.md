---
status: idea
updated: 2026-09-05
---

# Sessions shell out to search at the same rate whether or not Grep exists

## Context

`~/AGENTS.md`'s "Viewing, searching, or editing files" opens with `Grep`/`Glob` over `grep`/`find`,
reasoned as _"dedicated tools have their own permission gate and keep the whole result"_. Auto mode
supplies a natural experiment for it, and nobody had run it: **auto mode withdraws `Grep` and
`Glob`** — confirmed again 2026-09-05, they are absent from an auto-mode session's tool list — so
every search there **must** go through Bash, while a normal session has the choice.

Seven days, 13,754 Bash calls, 747 transcripts. Auto mode is detectable in a transcript by its own
system note, `"While auto mode is active"`:

|               | sessions | Bash calls | search via Bash | standalone searches |
| ------------- | -------- | ---------- | --------------- | ------------------- |
| normal        | 52       | 11,929     | 2,791 (**23%**) | 2,158 (**18%**)     |
| auto (forced) | 9        | 1,825      | 429 (**24%**)   | 342 (**19%**)       |

Per-session, sessions with ≥40 calls: auto ranges **18–29%**, normal **9–40%**. The auto
distribution sits entirely inside the normal one — no separation at any point.

"Standalone" excludes the two legitimate shapes: a `grep` used as a filter inside a pipeline (20% of
the tagged calls), and `rg -c`/`--count`/`--files` used for counting, which the rules explicitly
recommend (3%).

[DECISION: **the preference is inoperative, and this is as clean a test of it as the corpus can
offer.** In auto mode the 342 standalone searches are compelled — there is no `Grep` to reach for,
and `~/AGENTS.md` itself tells auto-mode sessions to search with `rg`. In normal mode the 2,158 are
chosen, with `Grep` and `Glob` sitting available. **Sessions behave identically whether the
dedicated tool exists or not**, which is what "the rule is not reaching the decision" looks like
when it is measured rather than argued.]

[PITFALL: **half the rule's stated reason is void on this machine, and that is a candidate cause
rather than a detail.** "Their own permission gate" buys nothing for `rg`, `grep` or `fd`: all three
classify `read_only` and render as `Bash(rg:*)` etc. in `allow`, so a Bash search prompts exactly as
often as `Grep` does — never. It is true only for `find`, which is `ask`. So an agent weighing the
rule finds one reason that does not apply and one — "keeps the whole result" — that applies to Bash
output too, since the harness truncates and persists both. A rule whose reason does not survive
inspection is the shape "Reading a command's result" was in before `PIPE_FAIL`, and it got rewritten
rather than restated.]

## Open questions

[NEEDS CLARIFICATION: **what the rule's reason should be, if it is kept.** The strongest one
available is new and comes from this same week's measurements rather than from the tool's design:
**a Bash search has a flag string to get wrong and `Grep`/`Glob` do not.** Every silently-wrong
search measured this week was only possible through a shell — 32 `rg -r` calls where the bundle ate
the flags and the matched text came back rewritten, plus `fd`'s silent zero on gitignored or
dot-directory targets. `Grep` takes typed parameters; there is no `-rn` to mistype and no ignore
default to forget. Whether that is worth stating, or whether it merely adds a third clause to a
paragraph already carrying two rewrites from today, is the question.]

[NEEDS CLARIFICATION: **whether the rule should be narrowed instead of re-reasoned.** A defensible
reading of the data is that agents are right and the rule is over-broad: a Bash search composes into
a pipeline, takes flags `Grep` does not expose, and — decisively — **works in both permission
modes**, where `Grep` disappears in one of them. A behaviour that is correct under every mode
beating one that is correct under a subset is not a discipline failure. If that is accepted, the
rule should say `Grep`/`Glob` where they are genuinely better and stop implying a general
preference. What it must not stay is a general preference nobody follows, which costs credibility
across the whole cluster.]

[NEEDS CLARIFICATION: **whether 9 auto-mode sessions are enough.** They are 1% of transcripts but
13% of calls — auto sessions average 203 calls against 229 for normal, so they are not atypical in
size, but they are few and may be self-selected by task. The per-session spread is the reassurance:
9 sessions spanning 18–29% against 48 normal sessions spanning 9–40% is not a subtle difference
being missed, it is no difference at all. Worth re-running when the auto-mode session count grows.]

## Recommended direction

**Do not change the rule in this session.** Two clauses of the same paragraph were rewritten today —
`rg -r` as a translation, and `fd` with its exemption list cut — and both carry `[UNVERIFIED:]` tags
whose whole point is a clean reading in a week. A third edit to the same paragraph makes all three
uninterpretable, which is the mistake the `head`/`tail` cluster made four times before anyone
noticed the readings could not be attributed.

So: bank the finding, take the answer to the two questions above, and land whichever change is
chosen **after** the 2026-09-12 reading, not before it.
