---
status: idea
updated: 2026-09-02
source_repo: github.com-personal/agent-skills
source_session: 2312636b-3f89-4cb5-95e8-48f986fb9ecb.jsonl
source_moment: 2026-09-01T17:20:53.485Z
---

# Adherence sample: the first session measured with the sweep excluded

For the `~/AGENTS.md` adherence watch. One sample, from a long `agent-skills` session (331 Bash
calls before the harvest boundary), and it is the first taken under two rules that landed the same
day, which is what makes it worth filing rather than just another row.

## The numbers

`audit.py --session … --until <harvest boundary> --compare 2026-08-24-auto-mode.json`, **9/11
expectations met**:

| tag                  | rate | vs baseline           |
| -------------------- | ---: | --------------------- |
| `chain`              |  34% | −33pp, OK             |
| `head/tail`          |  24% | −6pp, OK              |
| `heredoc`            |   6% | −10pp, OK             |
| `sed-n`              |   2% | −6pp, OK              |
| `cd-own-repo`        |   0% | −3pp, OK              |
| **`git-C-own-repo`** |  23% | **+23pp, MISS**       |
| **`git-C-mutating`** |  16% | **+13pp, MISS**       |
| `exit-masked`        |  19% | (not in EXPECTATIONS) |

**Only 6 calls were excluded by `--until`**, because the boundary is taken at step 0 and this
harvest had barely started — so unlike the two 2026-09-01 samples, the figure here is essentially
all working session. That is the flag behaving as intended rather than a null result: the exclusion
is small when the harvest is young, and the point is that it is no longer unknown.

## What is new, beyond the row

- **`git -C <own repo>` at 23% is this session's dominant miss**, and the mechanism is visible in
  the transcript rather than inferred: the session worked in one repo all day and reached for
  `git -C <that same repo>` as its default shape for every status, log, add and commit. The rule
  calls this "the ban on `cd` wearing the recommended flag", and the session never typed `cd` at all
  — `cd-own-repo` is 0%. So the habit the rule was written against was fully avoided, and its
  replacement scored worse.
- **`exit-masked` at 19%, with the consequence checked rather than assumed.** `session-harvest`
  gained a rule that day: a non-zero `exit-masked` means the session's own green results are
  unverified, so re-run the gate unpiped. Done — `inv quality.precommit` came back `EXIT=0`, so the
  greens were real. The value is that it is now measured: the session had run the gate as
  `… | tail -3` perhaps fifteen times, which could not have reported a failure.

[UNVERIFIED: whether 23% `git -C <own repo>` is characteristic of this machine or of this session's
shape. One session working in a single repo for ten hours is close to the worst case for that
pattern, and a session that moves between repos would produce legitimate `git -C` calls that the tag
cannot distinguish from the banned ones. Worth a `--days` run across sessions before treating the
rate as a trend; the tag counts the target being the session's own project, so the distinction is
available but was not measured here.]

## Also worth recording, since it changes older rows

`audit.py`'s `compare` treated a tag **missing** from the baseline as `0.0`, so a "down" expectation
on a pattern added after the baseline was saved evaluated `0.0 < 0.0` and reported **MISS at a 0%
rate** — while other absent tags collected an equally unearned **OK**. This run first printed 9/12
for that reason; the honest figure is 9/11. Fixed in `agent-skills` on 2026-09-02, with `"zero"`
expectations still judged (they are absolute and need no baseline) and only `"down"` ones skipped as
`(new)`.

**Any adherence figure quoted from a run where the baseline predates a pattern is affected**, in
both directions. Re-read rather than re-trusted, if an older sample's score is ever compared against
a newer one.
