---
status: idea
updated: 2026-09-01
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

## Open questions

[NEEDS CLARIFICATION: where the parked-note content goes. Two shapes — `blocked on <reason>` is the
vocabulary's own slot for "stalled on something external", and this is arguably stalled on the
deployed `~/AGENTS.md` rule having run long enough to re-measure; or plain `idea` with the note as a
first paragraph in the body. The second is more honest if nobody is actually waiting on anything,
since a `blocked on` plan reads as owed to someone.]

[DECISION: **not an occurrence of the hand-edit bypass, checked rather than assumed.** The string
arrived in `ea41fac`, 2026-08-25 01:46, which also added a `[DECISION:` block to the body — the
exact mid-edit shape
`agent-skills/plans/2026-08-30-plan-docs-status-gate-bypassed-by-hand-editing.md` describes, so it
looked like a third occurrence. It is not: `set-status` first appears in `plans.py` on
**2026-08-28** (`a6585a2`), three days later. There was no command to bypass and no gate to skip;
hand-editing the frontmatter was the only way to change a status at the time. Do not cite this as a
third data point — that plan still stands at two.]

[NEEDS CLARIFICATION: whether other plans predating 2026-08-28 carry states `set-status` would now
refuse. This one was found only because it broke the vocabulary loudly enough for the family-scope
drift check to see it; a plan that hand-landed a valid-looking status before the gate existed is
invisible to every check there is. Whether that matters depends on how many plans predate the
command and how many have moved status since — both cheap to count, neither counted.]

## Recommended direction

Fix it with `plans.py set-status`, not by editing the frontmatter. The string predates that command
so nothing was bypassed when it was written — but editing it back by hand now, with the command
sitting there, would be the bypass, and this is a plan about a status field.

Move the note into the body first, then set the status, then check whether the plan's substance is
still true before leaving it at `idea`: the note says the `~/AGENTS.md` rule was deployed 2026-08-25
and should be re-measured "after it has run a while", and a week has passed. The re-measure it names
is the `gh run list` sweep already written into the plan's Observation section, and its result may
close this plan rather than park it again.
