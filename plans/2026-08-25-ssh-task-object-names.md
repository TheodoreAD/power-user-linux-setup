---
status: idea
updated: 2026-08-25
---

# `ssh.add` / `ssh.forward` don't name their object

## Context

Inherited from the retired `plans/2026-08-24-invoke-task-naming-convention.md`, which left this out
deliberately: it is a readability improvement, not a convention fix, and folding it into the rename
pass would have blurred what that plan was for.

`ssh.add` adds this node's keys to the agent; `ssh.forward` copies public keys to the remote non-git
hosts in `identity.toml`. Both lead with a verb and so satisfy the family's verb-first rule
(`skills/invoke-task-conventions/`), but neither says what it acts on — `inv ssh.add` reads as "add
what?". `ssh.add-keys` / `ssh.forward-keys` would read better, and would match their sibling
`ssh.create-keys`.

## Open questions

[NEEDS CLARIFICATION: is the rename worth its blast radius? Task names are cited in `docs/ssh.md`,
`setup.toml`'s header, `tasks/next_steps.py`'s printed suggestions and possibly `identity.toml`
prose — the same checklist the naming skill records. Two short tasks that a user runs by hand a few
times per machine may not earn it.]

## Recommended direction

If done, do it as one small commit series following the skill's rename checklist (function names
change too; grep the snake spelling inside string literals afterwards). No transitional aliases, per
the same skill.
