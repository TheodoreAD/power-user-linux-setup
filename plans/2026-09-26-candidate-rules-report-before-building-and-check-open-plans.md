---
status: idea
updated: 2026-09-26
---

# Candidate rules: report before building, and read the open plans before designing

## Context

Two misses in one session (transcript `10d0c6cd-12d8-42ff-9048-1da4b65afcc8.jsonl`, the allowlist
rework of 2026-09-26), both caught by the user rather than by any rule. Filed as candidates for
`contributing/global-agents-md.md`'s admission process, not written into a fragment.

1. **Built one option of an open question without reporting the conclusions first.** The user asked
   for "a more creative solution" for `git -C`; the session probed five strategies, then implemented
   and committed per-repository rules across several commits before summarising anything. The user,
   verbatim: "did you settle on adding all the repos by path? i recall asking for a more creative
   solution than that, and i didn't see any conclusions yet. stop and give me a report on everything
   you've done so far, i was expecting a summary earlier". The implementation was later withdrawn
   (commit c724175) for the sandbox route the report surfaced. The existing rule "A narrow check
   grows into design work" covers writing a plan, not returning to the user with findings when the
   question they asked was open-ended.
2. **Designed without reading this repo's open plans.** An existing plan,
   `plans/2026-09-05-web-tool-permissions-and-what-auto-actually-buys.md`, had already concluded
   "The actual answer is the Bash sandbox" — the answer this session reached hours later, and only
   because the user pointed at the permissions docs. `plans.py list` was run for filing, never read
   as "has this been designed already". `plan-docs` says to read incoming titles as a set during
   `absorb`; nothing says to do it before starting design work.

## Open questions

[NEEDS CLARIFICATION: whether (1) passes the admission test — the miss here was expensive (several
commits built and withdrawn) but loud (the user noticed), and the always-loaded file is over its
reference size. A candidate phrasing: "When the user asks an open question with alternatives, report
the alternatives with evidence and stop; build only the one they pick."]

[NEEDS CLARIFICATION: whether (2) belongs in `plan-docs` (agent-skills) as a design-start step —
"`plans.py list`, and read the titles against the problem before designing" — rather than the global
file; if so, file it `--for agent-skills`.]

## Recommended direction

Decide each against the admission criteria; (2) looks like a skill change, (1) like a collaboration
fragment candidate.
