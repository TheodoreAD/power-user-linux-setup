---
status: idea
updated: 2026-08-22
---

## Context

Reported: a dangerous/write-classified command (e.g. `git push`, `git commit`) has silently executed
with no permission prompt, in cases involving a compound command chained via `&&`/`;` (the concrete
example given: something shaped like `cd <dir> && git push`). This is a real, observed incident, not
a hypothetical — treat it as a genuine finding to run down, not something to dismiss because the
static audit below came back clean.

**Investigation so far (same session, 2026-08-22) — static audit and live test, both clean:**

- `~/.claude/settings.json` currently has `Bash(git push:*)` and `Bash(git commit:*)` correctly in
  the `ask` bucket, not `allow`.
- `bash` itself is classified `dangerous` by PULSE's own LLM classifier
  (`cli-allowlist/rules/bash.json`: _"Bash can execute arbitrary commands with unlimited blast
  radius... without normal confirmation steps"_) and renders as `ask` — meaning
  `bash -c "<anything
  dangerous>"` should always prompt too, since the risky payload never gets a
  chance to be evaluated as its own subcommand (the outer `bash` invocation itself already gates
  it).
- No broad shadowing rule was found (no bare `Bash(git:*)` or `Bash(bash:*)`/`Bash(sh:*)` sitting in
  `allow` that could out-rank a more specific `ask` rule for the same subcommand).
- No `Bash(cd:*)` rule of any kind exists.
- **Live test, this session**: ran `cd /tmp && cat /etc/hostname` and `cd /tmp && git status` for
  real, in the actual Bash tool. Neither triggered a permission prompt — both matched their existing
  single/two-word allow rules correctly as independent subcommands, exactly as
  `code.claude.com/docs/en/permissions.md`'s "Compound commands" section says it should: _"Claude
  Code is aware of shell operators... a rule must match each subcommand independently"_ — and
  explicitly calls out that a rule like `Bash(command:rm *)` is disallowed specifically _because_ it
  "would be bypassable by a compound command," i.e. the engine is deliberately designed against
  exactly this failure mode.
- **This directly contradicts `config/global-AGENTS.md`'s current text**: _"A
  `cd some/dir && git
  status` no longer starts with `git status`, so it can't match
  `Bash(git status:*)` even though the bare command is already allowlisted."_ That claim did not
  hold up against a live test this session. **Deliberately not "fixed" as part of this plan** —
  until the reported incident's actual mechanism is understood, it's not safe to assume the doc is
  simply stale; it's equally possible the doc was correct for some case this session's two read-only
  tests didn't happen to hit (see Open Questions).

**What the clean audit does _not_ rule out**: only tested with the current global
`~/.claude/settings.json`, only with read-only subcommands (`cat`, `git status`), only in this one
main-session Bash tool call path, on whatever Claude Code version is running right now. None of that
necessarily matches the conditions under which the actual incident happened.

## Open questions

[NEEDS CLARIFICATION: forensic detail on the actual incident — which session/transcript, roughly
when, which repo, was it the main interactive session or a dispatched subagent's own Bash tool call,
was any non-default permission mode active (e.g. an auto-accept/YOLO mode,
`--dangerously-skip-
permissions`, or similar), and what Claude Code version was in use at the time?
Without this, a "fix" risks being built for the wrong mechanism entirely — the static audit above
found nothing wrong with the _current_ configuration, so whatever happened may be version-specific,
mode-specific, or specific to a code path (subagent dispatch, a project-local
`.claude/settings.json`/ `settings.local.json` override, a hook) this session's audit didn't check.]

[NEEDS CLARIFICATION: do subagent-dispatched Bash tool calls (Task/Agent tool) go through the same
interactive permission-prompt surface as the main session's own calls, or could a subagent's Bash
call execute silently under some condition without the human ever seeing a prompt? This session
independently observed subagent tool calls (`sed -n` invocations from a `Plan`-type subagent) that
were never flagged/interrupted — worth checking whether that's because the specific commands were
already allow-listed, or because subagent Bash execution has different prompt-surfacing behavior
than the main session. If the latter, that's a much more direct explanation for "dangerous command
ran silently" than anything about `&&`/`;` parsing specifically.]

[NEEDS CLARIFICATION: is there a project-local `.claude/settings.json` or `settings.local.json` in
whichever repo the incident happened in, that might carry a broader allow rule (e.g. a permissive
rule added in the heat of some other task) not present in the global config audited here? Worth
checking the specific repo before assuming the global config is the only relevant one.]

[NEEDS CLARIFICATION: once the mechanism is understood, does `config/global-AGENTS.md`'s compound-
command caution get corrected (if genuinely stale) or strengthened/clarified (if it was actually
half-right about a real edge case)? Don't resolve this before the above is answered.]

## Second, independent confirmation of the per-subcommand model (2026-08-23)

While investigating an unrelated complaint (`gh run view`/`gh run list` still prompting despite
being correctly classified read-only — see the new "parent ask/dangerous rule shadows read-only
child rules" work landed in `tasks/allowlist.py` and `contributing/cli-allowlist.md` the same
session), fetched `code.claude.com/docs/en/permissions.md` directly and read its "Compound commands"
section in full, independent of this plan's earlier live test. It states the same model explicitly:
Claude Code parses shell operators and evaluates each subcommand independently; the recognized
separators are `&&`, `||`, `;`, `|`, `|&`, `&`, and newlines — a rule must match each subcommand on
its own. Also directly answers a side question the user raised the same session: reformatting an
existing chain with `\` line continuations for readability has zero effect on matching, since
newline is already a recognized separator in its own right — whitespace/newline placement around
`&&`/`;` doesn't change how a command splits.

This doesn't chase down the open incident below — still don't know its actual mechanism — but it is
a second, independently-sourced confirmation (docs text, not just live-testing) that the
subcommand-splitting model itself is correct as documented. The `~/AGENTS.md` edit should still wait
on the open questions below, per this plan's own existing stance.

## Recommended direction

Two tracks, only one of which depends on resolving the open questions above:

1. **Build a regression-test suite now, independent of root cause.** Whatever the actual mechanism
   turns out to be, an automated check that compound commands ending in a write/dangerous-classified
   subcommand actually require approval is valuable defensively and cheap to build safely: point
   `git push`/`git commit` at a local throwaway bare repo (`git init --bare` in a tmp dir used as
   the test's own `origin`), never a real remote, and drive the check through whatever
   headless/scripted invocation surface Claude Code exposes for testing permission behavior (if none
   exists cleanly, note that as a blocker rather than improvising an unsafe workaround). Cover:
   `cmd1 && write-cmd`, `cmd1 ; write-cmd`, `cmd1 | write-cmd` (where meaningful), a `bash -c "..."`
   wrapper, an env-var-prefixed invocation (`VAR=x write-cmd`), and at least one 3-deep chain
   (`cmd1 && cmd2 && write-cmd`) — matching the actual compound-command shapes
   `config/global-AGENTS.md`'s "Bash tool discipline" section already discusses for the (unrelated)
   friction problem, so the same test fixtures could plausibly serve both purposes.

2. **Investigate the actual incident before building a targeted fix.** Don't guess at a mechanism to
   patch — get the forensic detail from the open questions above first. If it turns out to be a
   subagent-dispatch prompt-surfacing gap rather than a compound-command-parsing gap, the correct
   fix is entirely different (and likely belongs alongside
   `plans/2026-08-22-sed-read-nudge-hook.md`'s and
   `plans/2026-08-22-deployed-config-drift-guard.md`'s hook-based mechanisms, which already
   establish the pattern of enforcing things at the harness/hook level rather than relying on
   documentation an agent may or may not see).
