---
status: idea
updated: 2026-08-22
---

## Context

Origin: while working the `plans/2026-08-22-deployed-config-drift-guard.md` design in a Claude Code
session, a built-in `Plan` subagent used `sed -n` to view files twice, instead of the Read tool —
despite `config/global-AGENTS.md` already stating "prefer a dedicated harness tool over its Bash
equivalent."

Root cause confirmed the same session (see `deployed-config-drift-guard.md`'s Context section, and
`config/global-AGENTS.md`'s "Built-in `Plan`/`Explore` subagents don't see this file at all" note,
added as a direct result): Claude Code's built-in `Plan`/`Explore` agent types deliberately skip
loading `CLAUDE.md`/`AGENTS.md` entirely (documented exception, for speed/cost). This is not a
one-off model lapse — no rewording of the `AGENTS.md` rule fixes it for those two agent types, since
they structurally never see the file. A hook enforces the rule at the harness level instead,
independent of which agent/system-prompt is active — the same class of fix as
`deployed-config-drift-guard.md`'s Approach A, applied to a different problem.

## Confirmed hook mechanics

`PreToolUse` hook, matcher `"Bash"`, supports the same non-blocking pattern `PostToolUse` does: exit
0 + JSON stdout
`{"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext":
"..."}}` injects a
reminder into the calling agent's context **without** blocking or denying the tool call. Verified
against live Claude Code docs (`code.claude.com/docs/en/hooks.md`) the same session. Deliberately
non-blocking, not a hard deny: `sed -n` is occasionally legitimate (e.g. one step of a larger pipe
the Read tool can't express) — the existing `AGENTS.md` rule itself carves out that exception, and a
hard block would fight it.

## Design sketch

- **Detect**: `tool_input.command` matching a "`sed -n` used for viewing, standalone" shape — not
  part of a larger pipe (`|`) or chain (`&&`/`;`), not paired with `-i`. Exact regex/heuristic is an
  implementation detail; false positives are low-cost since the hook never blocks, so err toward
  over-matching rather than under-matching.
- **Nudge text**: something like "sed -n was used to view a file — Read (with offset/limit) does the
  same job with zero Bash-allowlist friction and no subagent-CLAUDE.md-inheritance gap. Prefer it
  unless this sed call is genuinely part of a larger pipeline Read can't express."
- **Deployment**: same infrastructure as `deployed-config-drift-guard.md`'s pulse-guard hook — a
  `wrapper-script`-deployed script + a merge into the global `~/.claude/settings.json`
  `hooks.PreToolUse` array, matcher `"Bash"`. If that plan's hook-registration task lands first,
  reuse it rather than duplicating the `settings.json`-merge logic a second time.
- **Scope**: global (fires on every Bash call machine-wide, not just this repo) — same global-hook
  precedent as the pulse-guard design.

## Open questions

[NEEDS CLARIFICATION: exact detection regex/heuristic for "`sed -n` used for viewing" vs. "`sed -n`
legitimately part of a larger pipe" — needs a handful of real positive/negative examples to validate
against before considering it done.]

[NEEDS CLARIFICATION: should this hook and `deployed-config-drift-guard.md`'s `PostToolUse` hook
share one deployed script/registration task (two matchers, one file) or stay fully independent?
Unrelated problems solved by the same mechanism class — worth deciding once one of the two is
actually being implemented, not before.]

[NEEDS CLARIFICATION: worth generalizing beyond `sed -n` to the other Bash-vs-harness-tool
anti-patterns `config/global-AGENTS.md` already names (`cat`/`head`/`tail` instead of Read,
`grep`/`find` instead of Grep/Glob, `sed -i`/heredocs instead of Edit/Write) — one hook with several
independent checks, or one hook per anti-pattern? Leaning toward one hook, several checks, given
they'd share the same "nudge, don't block" mechanism and the marginal cost of an extra regex check
is near-zero next to an already-paid Python startup.]

## Recommended direction

Build as a `PreToolUse`/`Bash` hook, non-blocking (exit 0 + `additionalContext`), generalized to
cover the several Bash-vs-harness-tool anti-patterns `config/global-AGENTS.md` already names (not
just `sed -n`) in one script with several independent checks. Reuse
`deployed-config-drift-guard.md`'s hook-deployment/registration infrastructure if that lands first,
rather than building a second copy of the `settings.json`-merge logic.

## Parallel track landed (2026-08-23): allowlist-level fix for when `sed -n` is genuinely called

This plan reduces _how often_ `sed -n` gets called at all — the hook above is still open/unbuilt. A
separate, complementary fix landed the same session that reduces _the cost_ when `sed -n` is still
genuinely needed (a subagent that hasn't gotten the nudge yet, or a real pipe step `Read` can't
express): see `contributing/cli-allowlist.md`'s new "`sed` — deliberately unreviewed,
hand-maintained rules instead" section. Summary: `cli-allowlist/rules/sed.json` was marked
`"reviewed": false` by hand (taking `sed` out of the generated pipeline, which structurally can't
split `-n` from `-i` in one prefix-glob rule), and three rules are now hand-maintained directly in
`~/.claude/settings.json`: `Bash(sed -n *)` allow, `Bash(sed -i*)`/`Bash(sed --in-place*)` ask.
Grounded in real data, not guessing: every `sed` call Claude Code has ever issued on this machine,
across every project's transcripts, was a `sed -n '<range>p' <file>` view — zero `-i` calls.

Neither track replaces the other: this one doesn't reduce how often the model reaches for `sed -n`
over `Read` (the nudge hook's whole point), and the nudge hook won't help the cases where `sed -n`
is the genuinely right call (a real pipe step, or a subagent Read can't reach via `AGENTS.md`). Both
should still land.
