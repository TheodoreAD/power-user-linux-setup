---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/agent-skills
source_session: c7d58945-4709-4fa6-9253-1140af86d9c0.jsonl
source_moment: 2026-09-28
source_plan: plans/2026-09-28-store-push-says-too-little.md
---

# The global "ask before pushing a foreign commit" rule needs an explicit plans-store exception

## Context

The global instructions, in the "Unexplained git/file state in a working tree" section, say: before
pushing, read `git log origin/<branch>..HEAD`; a commit there you did not make belongs to another
live session, so say so and ask before your push publishes it.

For a plans store the user has decided the opposite: `plans.py push` names every outgoing commit,
including other sessions', and publishes them without stopping or asking. A store is a shared log
that every session commits into and pushes wholesale, and every outgoing commit passes the same
confidentiality scan, so asking per foreign commit is friction protecting nothing.

That exception is now written in agent-skills' `plan-conveyor` SKILL.md, in the section on pushing a
store. The global rule still reads as if it applies everywhere, so a session holding both will see
them conflict, and the global file is the one loaded into every session.

## Evidence

- The user's answer, verbatim, in the session named above: "name foreign commits, don't stop the
  push".
- The ingesta incident that raised the question is in agent-skills'
  `plans/2026-09-28-store-push-says-too-little.md`, under "Success path": a store push published a
  parallel session's absorption commit, and the pusher learned whose it was only afterwards.

## Recommended direction

Add one sentence to that rule in the agents-md fragment that owns it: the rule does not apply to a
plans store pushed with `plans.py push`, which lists every outgoing commit and publishes them all by
design; report the foreign ones rather than asking. Then deploy it the usual way.
