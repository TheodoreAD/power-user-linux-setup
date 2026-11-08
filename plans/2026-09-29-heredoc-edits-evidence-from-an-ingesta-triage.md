---
status: idea
updated: 2026-09-29
source_repo: github.com-personal/ingesta
source_session: e15f97a5-8323-4308-8b25-c2648bc833a4.jsonl
source_moment: 2026-09-29T01:06:39+03:00
source_plan:
---

# Heredoc edits: a third session's evidence

**Belongs to `2026-08-28-auto-mode-contradicts-bash-rules.md`**, whose open question asks whether
`heredoc edits` are the same failure as the other rows or a case the rule never considered. Filed
separately rather than edited in, per the harvest rule for another repo's plan; merge it there.

## Evidence

- Session: an `ingesta` plan triage and a feature build, auto mode's Bash note in context.
  `audit.py --until 2026-09-29T01:06:39+03:00`: **303 calls, `heredoc` 61 (20%)**, and every other
  row at 0–1% (`chain` 1%, `head/tail` 0%, `exit-masked` 0%, `sed-n` 0%, `cat-view` 0%).
- **Almost all 61 were `python3 - <<'EOF'` blocks doing multi-site replacement** — moving several
  passages between plans in one call, appending `## Migrated to` sections to four plans at once,
  threading one new keyword argument through a model, three tables and three store methods. That is
  the owner plan's second session's explanation again: work `Edit` needs several calls for. Sessions
  now: three, one explanation.
- **But it carried a cost the owner plan does not record yet.** One multi-file regex rewrite
  (turning markdown links into plain text) let its capture group span back to an earlier `[`, and
  deleted the opening bracket of `[DECISION:`/`[NEEDS CLARIFICATION:` blocks in seven plans. It was
  caught only by reading the output and reverted with `git checkout`. `Edit`'s
  exact-match-and-unique contract makes that class of error impossible, because an ambiguous or
  wider-than-intended match fails instead of applying. So the gap is real in one direction (several
  calls) and the rule's protection is real in the other (no silent over-match).
- Second cost, measurement-side: `harvest.py sweep` reports
  `67 call(s) … ran an inline script …
  writes inside those are invisible here`, so its
  files-written-outside-a-repo check is a floor for exactly these sessions.

## What it suggests for the open question

Neither of the owner plan's two readings alone: the multi-site rewrites are a real gap **and** the
rule is protecting something. A stated exception would want a condition — every heredoc edit
followed by a diff read before the gate, say — rather than a blanket carve-out.
