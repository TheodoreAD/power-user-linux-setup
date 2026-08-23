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
