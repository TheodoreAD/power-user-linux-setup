---
status: landed
updated: 2026-09-02
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

## Fixed 2026-09-02

The one-line change plus the test the recommendation below asked for: the dry-run branch now filters
`links` on `link.parent.is_dir()`, matching `_ensure_symlink` and `verify._symlink_checks`. The test
deploys the content for real, then dry-runs with one `symlink_dest` whose parent does not exist, and
asserts the report is not `MISSING`; it was confirmed to fail with the production change reverted,
so it is testing the fix rather than the fixture.

Both questions this plan opened with survive the fix and are worth carrying, but neither blocks it —
they are about the shape of dry-run reporting generally rather than this defect:

**Is one `ok`/`MISSING` word the right report at all?** A wrapper-script package can be wrong in
three separable ways — content not deployed, content stale, a link pointing elsewhere — and
collapsing them is what made this ambiguous enough to need investigating in the first place.
`deploy.status` already distinguishes the content states, so the dry run could defer to it rather
than compute its own verdict. Not done here: it changes an output `phases.py` greps for.

**How many other dry-run branches re-derive a check the write path already owns?** This one drifted
from two different implementations of the same rule at once, which points at the pattern rather than
the instance. Cheap to look for — every `if util.DRY_RUN:` block in `tasks/` that re-implements a
condition instead of calling the helper the writer uses.

Filed as a fresh idea rather than kept open here, since the defect is closed and those two are a
different subject: `plans/2026-09-02-dry-run-branches-that-re-derive-their-own-checks.md`.

## Migrated to

- The fix and its reasoning are in `tasks/tools.py`'s dry-run branch (comment) and
  `tests/unit/test_tools.py`'s `..._dry_run_ignores_a_link_whose_parent_doesnt_exist` docstring,
  which carries the false-alarm argument.
- The two open questions went to the new plan named above, which is where they can be worked on as
  one subject.

Deliberately not migrated: the diagnosis narrative (which line, which four `symlink_dest` entries),
since the code and the test now state the rule directly and the entry points are one grep away.
