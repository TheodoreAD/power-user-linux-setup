---
status: idea
updated: 2026-08-23
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

## Second root cause, found 2026-08-23: auto mode instructs the opposite

The Context section above attributes the problem entirely to `Plan`/`Explore` subagents structurally
never loading `AGENTS.md`. There is a second, independent cause, and it reaches the **main
session**, not just subagents: **Claude Code's auto mode injects a system-reminder that actively
instructs the agent to prefer Bash over the dedicated tools** — the direct inverse of the
`config/global-AGENTS.md` rule this plan exists to enforce. Observed verbatim at the start of a
`power-user-linux-setup` session that day:

> While auto mode is active: Do your work through the Bash tool wherever it can accomplish the job:
> read files with cat, head, or sed -n, search with grep and find, and make file changes with sed,
> heredocs, or short scripts, rather than using the dedicated Read, Edit, or Write tools. Fall back
> to a dedicated tool only when Bash genuinely cannot do the job.

It names the same four anti-patterns `global-AGENTS.md` names, and reverses each one. The session
that observed it followed the reminder (it is a live harness directive, injected mid-conversation)
over the standing `AGENTS.md` preference.

This substantially changes the design space, so it is not just background colour:

- **A nudge hook would fire near-constantly in auto mode**, because the agent is being told to do
  the thing the hook nudges against. The "occasional legitimate `sed -n`" framing under "Confirmed
  hook mechanics" assumed the anti-pattern is rare; under auto mode it is the instructed default.
- **Two harness-level mechanisms would be contradicting each other**, with the hook losing on
  ordering — the reminder is in the system prompt for the whole turn, the nudge arrives per tool
  call. Nudging against a standing instruction is a worse position than nudging against a habit.
- **A hook cannot be the whole fix here even in principle.** For the `Plan`/`Explore` gap a hook
  works precisely because the rule can't reach the agent any other way; for this one the rule _does_
  reach the agent and is _overridden_. That is a precedence problem, not a delivery problem.

[NEEDS CLARIFICATION: which instruction should actually win when auto mode is active — the harness's
own reminder, or `global-AGENTS.md`'s preference? Deliberately left open 2026-08-23 rather than
written into `global-AGENTS.md` as a rule, since it's this plan's to decide. Worth checking first
whether the reminder is configurable or suppressible per-project (settings, or the auto-mode
classifier's own config) — if it is, that's a cleaner fix than either a hook or a precedence rule,
and it removes the contradiction instead of ranking it.]

[NEEDS CLARIFICATION: does the auto-mode reminder actually change the cost calculus the
`global-AGENTS.md` rule is built on? The rule's stated reasons are allowlist-prefix friction and the
dedicated tools having a separate permission gate from Bash. Under auto mode a background classifier
reviews Bash calls instead of prompting interactively, so "prompt friction" may be the wrong frame
there — worth measuring before assuming the rule's rationale survives unchanged.]

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
