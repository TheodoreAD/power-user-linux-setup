---
status: landed
updated: 2026-09-02
source_repo: github.com-personal/agent-skills
source_session: 2312636b-3f89-4cb5-95e8-48f986fb9ecb.jsonl
source_moment: 2026-09-01T17:20:53.485Z
---

# A plan's status has drifted out of the vocabulary, and nothing inside this repo can see it

## Context

`plans/2026-08-23-git-hooks-for-quality-gate.md` in this repo carries a free-form paragraph where
the status enum belongs:

```yaml
status:
  idea — hooks still unadopted; `~/AGENTS.md` "About to commit" rule deployed 2026-08-25 as the next
  step, re-measure after it has run a while
```

The note itself is useful and should be kept — it says why the plan is parked and what would restart
it. What is wrong is where it lives: everything after `idea` is body content sitting in a field that
`plan-docs` treats as an enum.

**The reason this is filed rather than left to be noticed: no session working in this repo can see
it.** `plans.py list` computes status drift only at `--scope family`, because a single repo's own
listing has nothing to compare a status against — it just renders whatever string it finds as a
group heading, so the drift reads as a deliberate `blocked on …`-style status and looks intentional.
Running `list` inside power-user-linux-setup, however carefully, will not report it. It surfaced
here only because a session in another repo ran the machine-wide view.

## Evidence

- Transcript:
  `~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-agent-skills/2312636b-3f89-4cb5-95e8-48f986fb9ecb.jsonl`,
  session start `2026-09-01T17:20:53.485Z`. The turn to find is the user asking **"anything left to
  absorb or retire or fix in the plans?"**, and the `plans.py list --scope family` call that answers
  it.
- What that run reported, verbatim:

  ```text
  status drift (1) — not in the vocabulary: in-progress | planned | idea | landed | abandoned | blocked on … | superseded by …
    'idea — hooks still unadopted; `~/AGENTS.md` "About to commit" rule deployed 2026-08-25 as the next step, re-measure after it has run a while':
    github.com-personal/power-user-linux-setup/2026-08-23-git-hooks-for-quality-gate.md
  ```

- The repro: `plans.py list` from inside power-user-linux-setup does **not** report it;
  `plans.py list --scope family` from anywhere does. Same corpus, same plan, one view blind.
- Not performed here: this session was working in `agent-skills`, and writing into another repo's
  tree is out. The fix is two minutes of work for a session that belongs to this repo.

## Resolved 2026-09-02

**Both questions are answered and the drift is fixed.** `2026-08-23-git-hooks-for-quality-gate.md`
now carries the parked note as its opening body paragraph and `idea` as its status, set by
`set-status` rather than by hand.

**Where the parked-note content went: plain `idea`, not `blocked on`.** The choice turned on the
re-measure the note itself asked for, which this session ran — eight days of CI across all three
repos, zero recurrences of the shape. Nothing was waiting on anything, so `blocked on` would have
advertised a debt that did not exist. Had the sweep come back dirty, `blocked on` would have been
the honest answer instead; the question was decidable only by doing the work the note described.

**No other plan carries a state `set-status` would refuse.** Counted machine-wide rather than
sampled: `list --scope family --all --limit 0` over **135 plans** returns `idea`, `in-progress`,
`planned`, `landed`, `abandoned` and nine distinct `blocked on …` strings, and nothing else. The
family-scope drift section is empty. So the two found here were the whole population, and the worry
that a plan could have hand-landed a valid-looking status before the gate existed turns out to be
untested rather than untrue — such a plan would be invisible to this count by construction.

[PITFALL: **the second drift was not the one this plan was filed about, and looked nothing like
it.** `2026-08-27-docs-site-usability.md` sat at `done` — a single plausible word, not a free-form
paragraph, and it read as a deliberate status right up until the family-scope listing grouped it on
its own. It was also the more consequential of the two: `done` conceals that the vocabulary's real
terminal status is gated, and the gate refused `landed` on an open `UNVERIFIED` the moment it was
asked. A drift that looks like a typo hides less than a drift that looks like a synonym.]

## The original open questions

[DECISION: **not an occurrence of the hand-edit bypass, checked rather than assumed.** The string
arrived in `ea41fac`, 2026-08-25 01:46, which also added a `[DECISION:` block to the body — the
exact mid-edit shape
`agent-skills/plans/2026-08-30-plan-docs-status-gate-bypassed-by-hand-editing.md` describes, so it
looked like a third occurrence. It is not: `set-status` first appears in `plans.py` on
**2026-08-28** (`a6585a2`), three days later. There was no command to bypass and no gate to skip;
hand-editing the frontmatter was the only way to change a status at the time. Do not cite this as a
third data point — that plan still stands at two.]

~~[NEEDS CLARIFICATION: whether other plans predating 2026-08-28 carry states `set-status` would now
refuse.]~~ **Answered above** — none do, across 135 plans. The residual worry the question named
stands and is not answerable by counting: a plan that hand-landed a _valid-looking_ status before
the gate existed is invisible to the drift check, because the drift check compares against the
vocabulary and such a status is in it.

## Recommended direction

Fix it with `plans.py set-status`, not by editing the frontmatter. The string predates that command
so nothing was bypassed when it was written — but editing it back by hand now, with the command
sitting there, would be the bypass, and this is a plan about a status field.

Move the note into the body first, then set the status, then check whether the plan's substance is
still true before leaving it at `idea`: the note says the `~/AGENTS.md` rule was deployed 2026-08-25
and should be re-measured "after it has run a while", and a week has passed. The re-measure it names
is the `gh run list` sweep already written into the plan's Observation section, and its result may
close this plan rather than park it again.
