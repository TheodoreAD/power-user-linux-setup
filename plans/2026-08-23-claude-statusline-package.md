---
status: landed
updated: 2026-08-23
---

## Migrated to

Implemented as designed below — `[packages.claude-statusline]` in `setup.toml`,
`_apply_declared_statusline()` in `tasks/ai.py`, and the "Declaring the statusline" section in
`docs/claude-code.md`. The design rationale (why this deliberately has no manifest/diff bookkeeping,
unlike `_apply_static_claude_permissions()` — `statusLine` is a single scalar with one desired
state, not a list many packages contribute to over time) lives in
`_apply_declared_statusline()`'s own docstring, right next to the code it explains — no separate
`contributing/*.md` entry needed. Verified: 179/179 tests pass, `quality.precommit` clean (commits
`e0821af`/`7e019e9`/`c900ee4`).

## Context

Over a long Claude Code session, a custom statusline script was built up interactively at
`~/.claude/statusline-command.sh` (dir/git-status/python-env/model/context-window/rate-limit/cost,
color-coded, ~200 lines, fully self-documented in its own header comment). It currently exists only
as a hand-edited file plus a hand-edited `statusLine` key in `~/.claude/settings.json` — neither is
tracked anywhere, so both would be lost on a reinstall or a new machine. It needs to land in this
repo as a package that's installed **by default**, no opt-in flag, matching how e.g.
`pulse-proxy-start` and `claude-global-md` are already deployed.

An initial design pass proposed mirroring the existing `_apply_static_claude_permissions()`
mechanism exactly — a generic any-package `claude_statusline` field, scanned across all packages,
safe-merged into settings.json via a manifest file tracking "what we last wrote," with a guard
against multiple packages declaring it. That was pushback-corrected: that mechanism's manifest/diff
complexity exists to solve _list_-merge problems (`permissions.allow` gets contributions from many
packages over time, and entries need to be added/removed as setup.toml changes) — `statusLine` is a
single scalar value with exactly one desired state, so none of that complexity earns its keep here.
Simplified to a direct three-way check (absent / matches / conflicts) with an interactive prompt on
conflict — no manifest, no generic multi-package scan.

## Design

### 1. `config/statusline-command.sh` — new tracked source file

Copy the live script in as-is (its content/logic is out of scope for this change — only its
deployment is being tracked): `cp ~/.claude/statusline-command.sh config/statusline-command.sh`.

### 2. `setup.toml` — new package entry

```toml
[packages.claude-statusline]
description = """
Custom Claude Code statusline — dir/git-status (p10k-style), python env, model tier,
context-window fill, both 5h/7d rate-limit windows, and session cost, all color-coded by a shared
muted "weight" palette. See the script's own header comment for the full color/icon/threshold
rationale — this repo only deploys it, never edits its logic.
"""
method = "wrapper-script"
tags = ["ai"]
dest = "~/.claude/statusline-command.sh"
content_file = "config/statusline-command.sh"
claude_statusline = { type = "command", command = "bash ~/.claude/statusline-command.sh" }
```

- `enabled` omitted → defaults to `true` (`util.packages_by_method`, `setup.toml` doc comment line
  8) — satisfies "installed by default, no opt-in."
- `tools.install`'s existing `WRAPPER_SCRIPT` loop (`tasks/tools.py` ~line 165-177) picks this up
  automatically; no code change needed there.
- `claude_statusline` is a **new**, single-purpose field — deliberately _not_ modeled on the
  any-package `claude_permissions_allow` scan (see Context above). Read directly off this one
  package, not scanned across all packages.

### 3. `tasks/ai.py` — new statusLine sync function (no manifest)

Add, near `_apply_static_claude_permissions()`:

```python
def _apply_declared_statusline() -> None:
    """Point ~/.claude/settings.json's top-level `statusLine` key at the managed script, declared
    via `[packages.claude-statusline]`'s `claude_statusline` field.

    Unlike `_apply_static_claude_permissions`, no manifest/diff bookkeeping: `statusLine` is a
    single scalar value with exactly one desired state, not a list multiple packages contribute
    to over time, so there's nothing to distinguish "ours to remove" from "user's to keep." Three
    outcomes only: absent -> set it; already matches -> no-op; set to something else -> ask before
    overwriting (default: leave it alone).
    """
    declared = util.load_config()["packages"].get("claude-statusline", {}).get("claude_statusline")
    if not declared:
        return

    settings = util.load_claude_settings()
    current = settings.get("statusLine")

    if util.DRY_RUN:
        print(f"[ai.skills] statusLine: {util.ok_label(current == declared)}")
        return

    if current == declared:
        print("[ai.skills] statusLine: already up to date")
        return

    if current is not None:
        if not ui.ask(
            f"~/.claude/settings.json already has a custom statusLine ({current!r}) — replace it with the managed one?",
            default=False,
        ):
            print("[ai.skills] statusLine: left existing custom value in place")
            return

    settings["statusLine"] = declared
    util.write_claude_settings(settings)
    print(f"[ai.skills] {util.CLAUDE_SETTINGS}: statusLine updated")
```

Call site — `skills()`, alongside the existing permissions call (`tasks/ai.py` ~line 322-324):

```python
if dir is None:
    _apply_static_claude_permissions()
    _apply_declared_statusline()
    _note_copilot_permissions()
```

`ui.ask(question, default=False)` (`tasks/ui.py` line 95) already auto-skips (returns `default`) in
non-interactive/CI/dry-run contexts via `util.interactive()` — matches the same convention used by
the skills-install prompts, so this never hangs an unattended `inv setup`.

Reused as-is, no changes needed: `util.load_config()`, `util.load_claude_settings()`,
`util.write_claude_settings()`, `util.DRY_RUN`, `util.ok_label()`.

### 4. `docs/claude-code.md` — new section

Append after the existing "Declaring static permission rules" section (after its closing GitHub
Copilot paragraph, current end of file ~line 258) rather than splitting that paragraph away from its
section — it's a wrap-up note about what else `ai.skills` does, not something to interrupt.

```markdown
## Declaring the statusline — the `claude_statusline` field

`[packages.claude-statusline]` deploys the custom Claude Code statusline script
(`config/statusline-command.sh` → `~/.claude/statusline-command.sh`, a `wrapper-script`-method
entry, chmod 0o755 — same mechanism as `claude-global-md`/`pulse-proxy-start`) and declares
`claude_statusline = { type = "command", command = "bash ~/.claude/statusline-command.sh" }` on that
same package entry. `inv ai.skills` reads that value directly (not a scanned any-package field like
`claude_permissions_allow` above — there's only ever one statusline, so no merge/manifest mechanism
is needed) and syncs it into `~/.claude/settings.json`'s top-level `statusLine` key: absent → set
it; already correct → no-op; set to something else → ask before overwriting (declines by default,
same `ui.ask` convention used elsewhere, auto-skipped non-interactively).

Edit `config/statusline-command.sh` and re-run `inv tools.install` to change the script's behavior —
its own header comment documents the color palette, icon sources (powerlevel10k's nerdfont icon
table), and threshold rationale in full; this doc only covers how it's _deployed_.
```

### 5. Tests — `tests/test_ai.py`

- Extend the existing `_stub_skills_task_helpers`-style fixture with a stub for
  `_apply_declared_statusline`, and assert it's called in the default-dir test / skipped in the
  `--dir` variant — same shape as the existing `perms`/`copilot` assertions.
- Add direct unit tests for `_apply_declared_statusline` (monkeypatching `util.load_config`,
  `util.load_claude_settings`, `util.write_claude_settings`, `ui.ask`): fresh write when absent,
  no-op when already correct, prompts-and-respects-declined-default when different, writes when user
  confirms overwrite, dry-run prints without writing.

## Files touched

- `config/statusline-command.sh` (new, copied from the live file)
- `setup.toml` (new `[packages.claude-statusline]` entry)
- `tasks/ai.py` (new `_apply_declared_statusline()`, new call site in `skills()`)
- `docs/claude-code.md` (new section)
- `tests/test_ai.py` (new/extended tests)

## Verification

1. `cd ~/projects/github.com-personal/power-user-linux-setup && uv run pytest tests/test_ai.py` —
   new + existing tests pass.
2. `PULSE_DRY_RUN=1 inv ai.skills` (or the repo's equivalent dry-run invocation) — confirms
   `statusLine: already up to date` against the current live (already-correct) settings.json,
   proving the idempotent no-op path works without needing to actually touch files.
3. Temporarily rename `~/.claude/statusline-command.sh` deployment / edit `statusLine` in
   settings.json to something else, re-run `inv ai.skills` interactively, confirm the prompt appears
   and both accept/decline paths behave as designed; restore afterward.
