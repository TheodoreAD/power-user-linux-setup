---
status: landed
updated: 2026-09-28
source_repo: github.com-personal/invoke-stubs
source_session: 65f8437a-a90e-41c6-9b1f-9b43d713ed9b.jsonl
source_moment: 2026-09-27T19:47:51Z
---

# In auto mode, the classifier denies `plans.py new <topic>` as irreversible local destruction

## Context

A harvest running in auto mode tried to create one plan in its own repo and was refused:

```
Permission for this action was denied by the Claude Code auto mode classifier.
Reason: [Irreversible Local Destruction]
```

The command was
`python3 <agent-skills checkout>/skills/plan-conveyor/scripts/plans.py new no-ci-on-a-repo-whose-push-is-a-release`.
It creates one markdown file and deletes nothing. Reproduced twice, about ten minutes apart, with
three successful invocations of the **same script** in between — all of which carried
`--for <repo>`. So the denial tracks the bare `new <topic>` form, which is the one that writes into
the session's own `plans/`.

Two consequences, and the second is the one that matters:

- The finding that plan was to carry went unrecorded in its own repo and had to be carried in a
  harvest report instead, which is exactly the fate `plan-docs` exists to prevent.
- The denial text is explicit that the _outcome_ is denied, not the command — "don't pursue the same
  outcome through another tool, interpreter, host, encoding, sub-agent or later turn". So a session
  that respects it, as this one did, cannot fall back to `Write`. A false positive here is therefore
  not friction to be paid around; it removes the capability for the rest of the turn.

The classifier is Anthropic-side rather than this repo's allowlist, so this is filed here because
this repo owns the permission-model rules in `~/.agents/AGENTS.md` and the `cli-allowlist` pipeline
— not because the fix is necessarily an allowlist entry.

## Evidence

Session `65f8437a-a90e-41c6-9b1f-9b43d713ed9b.jsonl` under
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-invoke-stubs/`, 2026-09-27,
between roughly 22:52 and 23:05 +03:00.

Sequence, in order, all in auto mode:

1. `rm -r /home/tdumitrescu/plans-sensitive/github.com-personal && git -C … status --short` —
   denied, same reason string. **Correct**: a real `rm -r`, and chained, so the whole compound was
   judged as one.
2. `plans.py new no-ci-on-a-repo-whose-push-is-a-release` — denied, same reason. False positive.
3. `plans.py new … --for github.com-personal/agent-skills` — allowed (prompted).
4. Two further `--for` invocations — one user-rejected at the prompt, one allowed.
5. `plans.py new no-ci-on-a-repo-whose-push-is-a-release`, retried after the user asked for the work
   to continue — denied again, same reason.

The user's own reading of the run: _"why did i get blocked 4 times for the latest command?"_

A separate observation from the same sequence, which is ordinary rather than a defect: the `--for`
calls prompted at all because the session had switched from the installed
`~/.agents/skills/plan-docs/scripts/plans.py` to the checkout's `plan-conveyor` path, and an
allowlist rule matches on literal command prefix. That part is the documented model working.

## Open questions

[DECISION: the allow rule wins. code.claude.com's `auto-mode-config` page says narrow Bash allow
rules "resolve … before the classifier runs". No `plans.py` rule is added now, though. The denial
was context-driven (see below), two denials in one session is no pattern, and a blanket `plans.py`
rule would also wave through `push`, which publishes.]

[DECISION: neither the token nor the path; context. Probed 2026-09-28 in auto mode, with no rule
covering `plans.py`. The exact denied command, bare `new no-ci-on-a-repo-whose-push-is-a-release`,
was approved under both the installed and the checkout path. The docs say the classifier sees user
messages, non-read-only tool calls and CLAUDE.md.]

[PITFALL: the Evidence list above over-counts. The transcript holds exactly two denials of `new`,
both that topic under the checkout path, and one of the `rm -r` chain. The same topic under the
installed path was not denied; it failed on a missing config. No `--for` call was denied. Searching
tool results for "classifier" miscounts once the session's own plans discuss the classifier.]

## Migrated to

- **The rule fix**: `config/agents-md/bash.md`, "The permission model in force", `ef0a47e`,
  deployed. A classifier denial is not a prompt, is judged in context, gets reported and asked about
  rather than retried, and the durable fix for a routine command is an allow rule in `tools.toml`.
- **The evidence and the probe**: `contributing/global-agents-md.md`, the section "A classifier
  denial is context-dependent, and the rule said the opposite of what applied", with the
  over-counting pitfall.
- Not done: an allow rule for `plans.py`, for the reason in the first DECISION above.

## Recommended direction

Probe the two questions above before proposing anything, since both possible fixes rest on an
assumption neither is currently tested. In the meantime the working shape is known and costs
nothing: `plans.py new <topic> --for <this repo>` files into the store mirror and the next session
here absorbs it, which is a longer path to the same file and is not denied.

Worth noting in whichever rule ends up describing this: a classifier denial is not the same object
as a permission prompt. `~/.agents/AGENTS.md` currently says "an approval prompt is a friction cost,
never a prohibition", which is true of the allowlist and false of this — and a session reading that
line while holding a classifier denial has been told the opposite of what applies.
