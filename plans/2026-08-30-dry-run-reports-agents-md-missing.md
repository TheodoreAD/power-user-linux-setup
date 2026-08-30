---
status: idea
updated: 2026-08-30
---

# `PULSE_DRY_RUN=1 inv tools.install` reports `agents-md` MISSING when it is fine

## Context

Noticed 2026-08-30 while dry-running `inv tools.install` after an unrelated change (the ad-hoc
whole-file writers being folded into `deploy.py`). The line is:

```
[agents-md] MISSING
```

while `inv deploy.status --name agents-md` on the same machine says `ok`, and the deployed
`~/AGENTS.md` is genuinely correct.

The cause is `tools._install_wrapper_script`'s dry-run branch:

```python
ok = deploy.classify(managed) == deploy.State.CLEAN and all(_link_ok(link, dest) for link in links)
```

`_link_ok` is `link.is_symlink() and link.resolve() == dest.resolve()`, evaluated over every
`symlink_dest`. `[packages.agents-md]` declares four — `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`,
`~/.copilot/copilot-instructions.md`, `~/.gemini/GEMINI.md` — and on this machine Codex and Gemini
are not installed, so `~/.codex/` and `~/.gemini/` do not exist.

**The real installer is right and only the report is wrong.** `_ensure_symlink`'s own docstring
states the rule deliberately: it never creates the parent directory, because a missing `~/.codex/`
is how an absent agent is detected, and it says so rather than skipping in silence. `verify.py`'s
`_symlink_checks` applies the same rule — "Links whose parent directory doesn't exist are skipped
for the same reason the installer skips creating them". The dry-run branch is the one place that
doesn't, so it counts a correctly-absent link as a failure.

## Open questions

[NEEDS CLARIFICATION: is `MISSING` for the whole package the right shape even once the parent-less
links are excluded? A wrapper-script package can be wrong in three separable ways — content not
deployed, content stale, a link pointing somewhere else — and one `ok`/`MISSING` word for all of
them is what made this ambiguous enough to need investigating. `deploy.status` already distinguishes
the content states; the dry run may want to defer to it rather than compute its own.]

[NEEDS CLARIFICATION: how many other dry-run branches compute their own version of a check that a
real task does differently? This one drifted from `_ensure_symlink` and from `verify.py` at the same
time, which suggests the pattern rather than the instance is the problem. Cheap to look for: every
`if util.DRY_RUN:` block in `tasks/` that re-implements a condition instead of calling the same
helper the write path uses.]

## Recommended direction

Skip a `symlink_dest` whose parent directory is absent, exactly as `_ensure_symlink` and
`verify._symlink_checks` already do — a one-line change in the dry-run branch, plus a test asserting
that a package whose only unsatisfied link has no parent directory reports `ok`.

Low urgency: nothing is broken, and the failure mode is a false alarm rather than a silent pass. But
a dry run that cries wolf on a healthy machine is the kind of output people learn to ignore, which
is expensive later.
