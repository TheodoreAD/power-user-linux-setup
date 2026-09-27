---
status: idea
updated: 2026-09-26
---

# Adherence sample 21: the session that automated hand-rolling, and hand-rolled throughout

Evidence for `plans/2026-08-23-global-agents-md-adherence-watch.md`, whose sample corpus ends at
session 20. Filed rather than appended because it was measured from an `agent-skills` session, and a
plan another repo owns is read and cited, never edited from outside.

## The sample

`agent-skills`, 2026-09-22 to 2026-09-26, `claude-opus-5`, auto mode. **261 Bash calls** to the
harvest boundary, its own sweep excluded.

| row              | this session | corpus (session 17 baseline) |
| ---------------- | ------------ | ---------------------------- |
| `chain`          | **71%**      | 46%                          |
| `head/tail`      | **60%**      | 31%                          |
| `exit-masked`    | **44%**      | —                            |
| `heredoc`        | 15%          | —                            |
| `sed-n`          | 8%           | —                            |
| `cd-own-repo`    | 3 calls      | —                            |
| `git-C-own-repo` | 0            | —                            |
| `rg-replace`     | 0            | —                            |
| `git-add-all`    | 0            | —                            |
| `cut-message`    | 0 of 13      | —                            |

11 of 17 expectations met. The six misses are `chain`, `head/tail`, `redirect-then-filter`, `sed-n`,
`heredoc` and `cd-own-repo`.

[PITFALL: **the comparison straddles the instrument.** The baseline used was `2026-09-12.json`,
whose `instrument` field is `null` — it predates the field — and three commits landed on `audit.py`
between it and this run (`28099cd` replay dedupe, `26f823b`, `adaad81`). `audit.py` prints the
warning itself: the baseline counted a resumed transcript's calls once per copy. So the `+37pp` and
`+40pp` deltas should not be quoted as figures. What survives the caveat is the direction and the
magnitude — 71% against a corpus norm near 46% is far outside anything a dedupe artefact produces —
and that is the claim this sample makes.]

## Why this one is worth a row

**The session's entire subject was removing hand-rolled work, and it hand-rolled at the highest rate
in the corpus.** Four days spent building `plans.py commit` subject derivation, `pending`,
`migrate`, `rename` and `push` — every one of them justified by measurements of sessions
hand-rolling git — in a session that chained 71% of its own calls and piped 60% through
`head`/`tail`.

This is the shape session 14 already recorded ("three breaches by the session editing the rules") at
a much larger magnitude, and it suggests the pattern is not incidental. A plausible mechanism, which
the corpus can test rather than assume: **the work that breaks these rules hardest is measurement
work.** This session ran thirteen throwaway analysis scripts over the transcript store and the git
histories of five repos, and the natural shape of that is a long pipeline whose output is then cut
to a readable window. None of it was editing or deploying; nearly all of it was reading.

[DECISION: recorded as a sample, not as a proposed rewording. The watch plan's own standard is that
a rule broken repeatedly is a measurement question before it is a wording question, and one session
does not establish the mechanism above. What it does establish is that the rate can go this high in
a session with no unusual constraints and full knowledge of the rules.]

## Two rows that did hold, and are worth the contrast

- **`cut-message` 0 of 13.** Thirteen calls carried a message for the user to read and none was
  truncated — the rule with the sharpest consequence held perfectly.
- **`git-C-own-repo` 0, `git-add-all` 0, `git-undo-relative` 0, `store-write-by-git` 0.** Every rule
  about _mutating_ git state held. The misses are concentrated entirely in reading and inspection,
  which is consistent with the mechanism above and is the part a rewording pass would need to
  target.

[UNVERIFIED: **`pipefail` was in force for the whole session**, confirmed by `setopt` at harvest
time, so the 66 masked calls that wrapped a gate still reported real exit codes and no green claim
rested on a discarded status. Two green-gate claims were made in the session and both stand. This
does not retire the `exit-masked` row — `| head` still discards output, and the guard is
harness-local — but it means this sample carries no false green.]

## Evidence

Session `75b2bcd7-afca-40c8-a408-11bc54871f0a` in
`-home-tdumitrescu-projects-github-com-personal-agent-skills`. Re-derive with:

```shell
python3 <audit.py> --session 75b2bcd7-afca-40c8-a408-11bc54871f0a \
  --until 2026-09-26T11:58:23+03:00
```

Transcripts are kept 30 days, so the raw calls are readable until late October; the rates above
stand without them.
