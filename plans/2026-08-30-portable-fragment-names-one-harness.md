---
status: idea
updated: 2026-08-30
---

# `portable.md` names one harness and one machine

## Context

`config/agents-md/`'s three fragments divide by audience: `this-setup.md` for this machine and this
user's repos, `claude-code.md` for one harness's behaviour, and `portable.md` for "conventions that
hold on any machine, with any agent". The 2026-08-26 split moved rules between clusters but
deliberately did not rewrite their wording, so `portable.md` inherited rules written when there was
one flat file and no such distinction to violate.

This was recorded as a "Still to do on the content itself" section in
[`config/agents-md/README.md`](../config/agents-md/README.md) — prose future-work in a doc that
otherwise describes current state, which is the failure the `plan-docs` convention names: no status
field, so nothing ever prompts a return visit. Moved here 2026-08-30 and the README trimmed to what
is true now.

## What is actually in there (measured 2026-08-30)

The README said "about a dozen rules". Across `portable.md`'s 29 rules the aggregate is close, but
the composition is not what that sentence implies, and the two halves want different fixes.

**Seven rules name Claude Code tools as tools**, which is the half that genuinely does not survive a
different agent:

| rule                                    | what it names                                      |
| --------------------------------------- | -------------------------------------------------- |
| Composing a Bash call                   | `Read` of a log, `Grep`/`Read` as a second call    |
| Viewing, searching, or editing files    | `Read`/`Grep`/`Glob`/`Edit`/`Write`, "the harness" |
| Reading a command's result              | "the Bash tool", `run_in_background`               |
| About to ask the user something factual | `AskUserQuestion`                                  |
| Ending a turn with a next step          | `AskUserQuestion`                                  |
| A narrow check grows into design work   | "plan mode"                                        |
| Committing multi-part work              | "the scratchpad"                                   |

**Nine name this machine** — the absolute `python3 ~/.agents/skills/plan-docs/scripts/plans.py`
path, `inv quality.precommit`, direnv and `.venv/bin`, the `plan-docs` convention by name, and
`power-user-linux-setup`/`pulse-setup` as the worked example in "Naming around a collision".

Three apparent hits are false positives and should not be "fixed" — the ordinary verbs in "Write
about that work by its shape", "Read the SHA", and the hyphenated adjective in "Read-only `git -C`
verbs". A mechanical sweep over capitalised tool names flags all three, which is the argument
against doing this as a sweep.

[PITFALL: **`Invoking a venv tool in the session's own project` is misfiled, not merely
un-generalised.** Its whole content is "most of this user's repos put `.venv/bin` on `PATH` via
direnv (`.envrc`)" — a fact about this machine, in the fragment whose stated remit is conventions
that hold on any machine. The README's framing ("rules that name this user's setup in passing") does
not cover a rule that is nothing but this user's setup. Its neighbour "Running a command against a
different repo" has the same problem in one bullet rather than throughout.]

## Open questions

[NEEDS CLARIFICATION: is a Claude-specific tool name actually a defect here? The fragment's remit
says any agent, but the file is deployed on a machine where the harness in use is Claude Code, and
`~/AGENTS.md`'s whole "Viewing, searching, or editing files" rule was worded the way it is _because_
that wording was measured against real transcripts. Generalising "Read over `cat`" to "your
harness's file-reading tool over `cat`" is strictly vaguer, and the design rationale warns that a
rule observed being missed wants stronger language, not softer. The alternative reading is that
these rules belong in `claude-code.md` and `portable.md` should carry the principle without the tool
names.]

[NEEDS CLARIFICATION: does the machine-specific half want generalising at all, or a pointer? An
absolute path like `python3 ~/.agents/skills/plan-docs/scripts/plans.py scan` is unusable on another
machine but is exactly what makes the rule actionable on this one, and the rule's value is that the
command can be run without thinking. "Run your plans store's scan command" is portable and useless.]

[NEEDS CLARIFICATION: should `Invoking a venv tool in the session's own project` simply move to
`this-setup.md`? That is a smaller, more obviously-correct change than rewording anything, and it
would test whether the fragment boundary is worth enforcing before any rule is reworded for it.]

## Recommended direction

Move first, reword second, and do not sweep. The misfiled rule is one `git mv`-shaped edit between
two fragments with no wording change, and it is the cheapest way to find out whether the boundary is
real. Only then decide whether a tool name in a rule is a defect or a deliberate concession to the
harness this machine actually runs — and if it is a defect, whether the fix is generalising the
wording or relocating the rule.

Per `contributing/global-agents-md.md`, rewrite these one at a time rather than in a sweep: each
rule's exact wording was tuned for adherence, several of them after being measured as missed, and
the three false positives above show what a mechanical pass would do to the ones that are already
correct.
