---
status: idea
updated: 2026-08-30
repo: git@github.com:TheodoreAD/power-user-linux-setup.git
---

# An agent reaching for `stash` and `rebase` to avoid one small commit

## Context

Confirmed 2026-08-29 in another repo's session, and caught by the user rather than by any rule.

The situation was trivial: a one-line improvement to a test written three commits earlier, and a
wish to fold it into the commit that introduced it — which `~/AGENTS.md` encourages, under
"Committing multi-part work", as "a bug fix found mid-implementation folds into the commit
introducing the correct behavior". Interactive rebase is unavailable in this harness, so the session
composed this instead:

```shell
git stash -q && git rebase -q --onto HEAD~3 HEAD~3 2>/dev/null; git stash pop -q; git status --short
```

Related: `plans/2026-08-23-global-agents-md-adherence-watch.md`'s session 4, which measures
adherence to the Bash cluster's head/tail rule. The same harvest that wrote this plan also piped
`git fetch` through `tail` while running the checklist that forbids it — recorded there as the third
confirmed occurrence. Both are the same shape of finding (a stated rule that a session held in
context and did not apply) under two different rules.

The user stopped it with "what's that git command stuff, looks dangerous". It never ran. Four things
were wrong with it at once, and only the fourth is about git at all:

1. **The rebase was malformed.** `--onto HEAD~3 HEAD~3` replays an empty range; it does nothing
   useful and moves HEAD for no reason.
2. **`git stash` is wrong on this machine specifically.** Parallel sessions share one working tree —
   the fact `~/AGENTS.md` already states under "Unexplained git/file state in a working tree" — so a
   stash can pick up another session's uncommitted work and pop it somewhere that session does not
   expect. Nothing in the file currently connects that fact to `stash`.
3. **`2>/dev/null` on a ref-moving command.** The rule "Reading a command's result" covers pipes
   defeating exit codes; silencing stderr on a verb that rewrites history is the same failure with a
   worse blast radius, and it is what would have made the malformed rebase invisible.
4. **The whole manoeuvre was to avoid a small honest commit.** The fold-into rule is about not
   shipping broken-then-fixed _behaviour_. This was a test-precision tweak that passed either way,
   so a separate one-line commit was always correct and reads fine in history.

## Open questions

[NEEDS CLARIFICATION: Whether this is admitted at all, given the file's size. `portable.md` stands
at 29 rules / 390 lines against reference points of ≤15 rules / ≤200 lines, so admission is a real
cost. The argument for it is the tier test in `contributing/global-agents-md.md`: the miss is silent
(a stash that absorbs another session's work surfaces as that session's edits vanishing, attributed
to anything but this) and expensive (unrecoverable, unlike a bad commit). The argument against is
that three of the four errors above are already covered by rules the session had loaded and did not
apply — which would make this an adherence problem rather than a missing rule.]

[NEEDS CLARIFICATION: Whether the "don't rewrite history to tidy a small commit" half belongs with
"Committing multi-part work" instead, since that is the rule whose fold-into guidance was being
over-applied. Splitting it across two sections would duplicate; putting it all under force-pushing
keeps one home but files it under a heading whose trigger is a push.]

## Recommended direction

Extend `### Force-pushing, or asking what a remote actually has` with a short paragraph rather than
adding a heading — criterion 2 of "Admitting a new rule" makes a variant extend the section it
varies, and the trigger here (about to rewrite history) is that section's subject. Rule count
unchanged; roughly six lines added.

End it on the command that replaces the habit, not on the warning, per the same document's lever:
**the fix for "this belongs in an earlier commit" is a new commit saying what it does.** Interactive
rebase is unavailable here, `git stash` is unsafe in a shared tree, and neither is worth risking for
tidiness. Where a fold genuinely matters — broken-then-fixed behaviour, not a tweak — `--amend`
reaches the tip commit only, and anything deeper is the user's call.

Evidence for `contributing/global-agents-md.md`, under a matching heading: the command above, the
date, and that it was stopped by the user rather than by a rule.
