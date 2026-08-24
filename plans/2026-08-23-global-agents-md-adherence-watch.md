---
status: in-progress
updated: 2026-08-23
---

## Context

Split out of the retired `plans/2026-08-23-global-agents-md-leanness-pass.md` at its closure. That
pass restructured `config/global-AGENTS.md` (deployed as `~/AGENTS.md`) from 6,053 body words / 30
flat sections to ~2,500 words / 6 clusters / 30 trigger-named rules, all landed 2026-08-23 — its
intended one-cluster pilot window was skipped, so the whole file is effectively piloting at once.
The one open item was its live-adherence verification:

[UNVERIFIED: do the rules still fire from the compressed trigger + rule + one-clause-why form over
the following working sessions? Highest-value watch list: git/commit rules (granular commits without
asking how to split; neutral handling of unexplained state), Bash/allowlist (simple separate calls,
scoping flags for cross-repo, `sudo -A`), verification (real exit codes, tests over ad-hoc scripts),
and the caveman register.]

## Recommended direction

- Watch passively across normal sessions in at least two repos — routine work exercises most rules;
  no dedicated drill needed.
- On an observed miss: re-expand the affected rule's wording in `config/global-AGENTS.md`
  (strengthen language, add the concrete tell — per the "strengthen, don't lengthen" finding in
  `contributing/global-agents-md.md`'s design-rationale section), record the miss here, redeploy.
  Never revert the cluster structure for a single rule's miss.
- Close as `landed` once a handful of sessions pass with no rule regressions; a clean watch leaves
  nothing to migrate.

## Observed misses

### Session 1 — `repo-tasks`, 2026-08-24 (long implementation session)

Four misses, all mine, all in the two clusters this watch flagged as highest-value. None caused
lasting damage; each cost a detour, and three were caught only because a later step happened to
surface them.

1. **Verification — truncated my own search output and treated it as complete.** Ran a
   `rg ... | head -20` to find every reference to a directory being moved, acted on the visible
   subset, and missed a file. It failed a test one step later. Then repeated the same shape a second
   time in the same session. `### Generalizing from a sample to a set` covers sampling _files_; it
   does not name the case where the sample is the tail of your own truncated output. That is the
   concrete tell worth adding — `| head` on a search whose purpose is completeness is the
   anti-pattern, and `rg -c` or a bare count first is the cheap check.

2. **Verification — verified commits against the wrong source.** Checked out three commits in a
   worktree and ran their tests, but the venv's _editable install_ resolves the package to the main
   working tree, so every run tested current code rather than the checkout. Produced one false pass
   and one false fail before I noticed. `PYTHONPATH=<worktree>/src` fixed it. The rule's existing
   framing ("clean stdout is not proof") did fire eventually; what was missing is that a _green test
   run_ is also not proof when the import path is not what you assume.

3. **Git — `git commit` commits the index, not the files just named.** Staged a specific file list
   for one commit while `git mv` renames sat in the index from earlier, so the renames landed in the
   wrong commit and a later commit was left referencing a module it did not yet contain. Unwound
   with `reset --soft` and restaged. Nothing in the git cluster states this; it is arguably plain
   git literacy rather than a rule gap.

4. **Quality gate — committed a plan edit without re-running it.** Pushed a dprint-unformatted
   markdown file to `main`; CI would have failed. Both `plan-docs` and `session-harvest` state this
   explicitly ("Markdown is not exempt"), and it is the single most common CI-failure cause recorded
   across these repos. So: not a rule-wording gap, a rule-adherence gap — the strongest signal in
   this batch, because the rule is already as explicit as it can be.

[DECISION: two of the four got re-expanded wording, 2026-08-24. (1) extended
`### Generalizing from a sample to a set` — the same failure applied to a sample you created
yourself by truncating your own search. (2) extended
`### Verifying behavior in a repo with test
coverage` — a green suite is only evidence about the
code that was actually imported. Both are one-sentence additions to sections that already framed the
principle, per "a variant extends the existing rule's section". Evidence in
`contributing/global-agents-md.md` under matching headings.

(3) was left out as plain git literacy rather than a personal-rules concern. (4) was left out
deliberately for the opposite reason: the rule is already as explicit as it can be and was still
missed, so more wording is the wrong lever — `plans/2026-08-23-git-hooks-for-quality-gate.md` is.]
