---
status: idea
updated: 2026-08-23
---

## Context

**Required reading before picking this up:**
`plans/2026-08-22-memory-to-agents-md-migration-sweep.md` — its "Recommended direction" item 1
("Deployed-vs-source drift guard for `~/AGENTS.md`... mechanical, no LLM needed") and its second
finding (`~/AGENTS.md` found drifted from `config/global-AGENTS.md` _twice_ in one session — once
from a same-session hand-edit to the deployed file, once from an older, pre-existing drift nobody
had caught) are this plan's direct origin. This plan exists to work that open item into concrete,
comparable designs rather than leaving it as a single bullet.

A second, independent live instance of the same failure happened in a separate session the same day
(a `scaffoldapy`-focused Claude Code session, unrelated to the memory-sweep work): a rule got added
to the deployed `~/AGENTS.md` directly via the Edit tool, and would have been silently lost on the
next `inv tools.install` had it not been caught by chance. Two independent sessions hitting the same
failure mode on the same day is real signal, not a hypothetical.

**Deployment mechanics** (grounding facts, not to be re-derived by whoever picks this up):

- `~/AGENTS.md` (+ `~/.claude/CLAUDE.md` symlinked to it) deploys from `config/global-AGENTS.md` via
  `tasks/tools.py:_install_wrapper_script`, the generic `wrapper-script` method every `[packages.*]`
  entry with a `content_file` uses (`askpass-zenity`, etc.) — a **plain copy**,
  `dest.write_text(content)`, not a symlink.
- Skills under `~/.agents/skills/<name>/` deploy from `skills/<name>/` via
  `tasks/ai.py:_install_local_skill` — also a **plain copy** (`shutil.copytree`), with a
  `.pulse-source` marker file (`_SKILL_MARKER = ".pulse-source"`) recording the `repo_path` that
  installed it, so re-runs can tell "ours" from "foreign."
- Both are **deliberately** copies, not symlinks — skills used to be symlinked and were
  intentionally switched to copying (to match the npx-sourced remote-skill installer's own copy
  behavior and keep local/remote skills symmetric; see the comment above `_install_local_skill`).
  Any drift-guard design needs to work with copy-based deployment as a fixed constraint, not propose
  reverting it.
- State-dir convention already exists for exactly this kind of generated/tracked metadata:
  `tasks/util.py:PULSE_STATE_DIR` (`~/.local/state/power-user-linux-setup`), already home to
  `_STATIC_PERMS_MANIFEST` in `tasks/ai.py`.
- `tasks/util.py:load_claude_settings()`/`write_claude_settings()` already do generic, backed-up
  read/write of the global `~/.claude/settings.json` (used by `ai.py`/`allowlist.py`) — reuse rather
  than re-deriving JSON I/O, for any approach that touches Claude Code hook config.
- `tasks/verify.py` currently verifies `wrapper-script` packages generically, by `dest` existence
  only (`_PATH_ONLY`) — it does not currently check deployed content against repo source at all.
- **There is a _third_ deployment mechanism this plan's scope originally missed: `config_files`.**
  Any `[packages.*]` entry, whatever its `method`, may declare
  `config_files = [{ src = "config/<file>", dst = "~/..." }]` — currently `wezterm` and
  `terminator`. Applied by `tasks/apt.py:_apply_config_files`, called from `apt.base` and both deb
  installers. Two differences from `wrapper-script` that matter to any generalized design: the field
  name is `dst`, **not** `dest` (so a lookup keyed on `dest` silently skips these packages
  entirely), and the install-time write is **skip-if-exists**, not an unconditional overwrite — a
  deployed `config_files` destination is _expected_ to drift, because the user owns it after first
  install. "Deployed content != repo source" is therefore not on its own an error for this mechanism
  the way it is for `wrapper-script`.

**Prior art now in-repo, added 2026-08-23** (`inv system.configs`, `tasks/system.py`, tests in
`tests/test_system.py`): Approach B's diff already exists for the `config_files` mechanism, and it
does fix rather than only report. It resolves each declared mapping, compares deployed against
source, and either reports a match, creates a missing destination without prompting, or prints a
unified diff and asks before overwriting. `--name <pkg>` scopes it, `-y`/`--yes` skips the prompt,
`PULSE_DRY_RUN=1` reports without writing. Whoever picks this plan up should treat it as the
reference implementation of B's diff half and extend/unify with it rather than writing a second,
parallel deployed-vs-source comparison.

[DECISION: an interactive, human-invoked drift fixer defaults to _not_ overwriting — prompt is on by
default, answers no on empty input, and `-y`/`--yes` skips it, matching apt/dnf rather than an
opt-in `--confirm`. `util.confirm()` returns its default when stdin isn't a terminal, so a piped or
CI run without `-y` skips the overwrite instead of clobbering unattended. Chosen over an
auto-sync-on-detect design because the deployed file is the one carrying the edit that would be
lost, so the diff has to be seen by a human before it's discarded.]

**Confirmed Claude Code hook mechanics** (verified against live docs this session, relevant to any
approach involving a Claude Code hook specifically — not relevant to a pure `inv verify.all`
mechanical check):

- `PostToolUse` hooks, matcher `"Edit|Write"`, can exit 0 and print
  `{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "..."}}` on stdout
  to inject a **non-blocking** instruction into the calling agent's own context, right after the
  edit completes — the edit itself is never blocked or undone. Printing nothing and exiting 0 is
  sufficient for "no match, nothing to say."
- Separately confirmed, relevant background: Claude Code's **built-in** `Plan`/`Explore` subagent
  types deliberately skip loading `CLAUDE.md`/`AGENTS.md` entirely (documented exception, for
  speed/cost) — so a written instruction in `AGENTS.md` alone ("don't hand-edit `~/AGENTS.md`
  directly") structurally cannot reach those two agent types. A hook-based guard does not have this
  gap, since hooks gate the tool call at the harness level, independent of which system prompt is
  active. This is direct evidence that a docs-only fix is insufficient here, not just a preference.

## Open questions

[NEEDS CLARIFICATION: real-time, agent-facing (Approach A below) vs. mechanical periodic/verify-time
check (Approach B) vs. both together (Approach D) — see "Recommended direction" for the full
tradeoffs. The memory-sweep plan's own open question ("should this hook into `inv verify.all` or a
pre-push hook") already leans toward B/D existing in some form; A is additive, not a replacement, if
the goal is to catch drift regardless of which tool caused it.]

[NEEDS CLARIFICATION: if a verify-time check (B) is built, does it belong in `inv verify.all` proper
(implying it runs at whatever cadence/CI-adjacency `verify.all` already runs at) or as its own
explicitly-invoked task? The memory-sweep plan flags the user's stated aversion to auto-triggered
mutation of _tracked artifacts_ specifically (`~/AGENTS.md`'s own "Commit regenerated artifacts
deliberately" section) — note this is about auto-_writing_, not auto-_reporting_; a read-only diff
check folded into `verify.all` doesn't mutate anything and may not trigger the same concern that an
auto-sync action would.]

[NEEDS CLARIFICATION: should a verify-time drift check ever offer to _fix_ the drift
(deployed→source, interactively confirmed via the same `ui.ask()` pattern `_install_local_skill`
already uses for "Update skill?"), or only report/fail and leave the human to diff and copy by hand?
Note this re-opens a question that was already answered _for the real-time hook case specifically_ —
no auto-copy, ever, because the PULSE repo could be mid-edit when an agent triggers the hook
mid-session. That rationale is weaker for a deliberate, human-invoked "check for drift now" moment —
worth deciding fresh rather than assuming the earlier answer transfers. **Narrowed 2026-08-23:** the
deliberate human-invoked half now has a shipped answer in `inv system.configs` (yes, it fixes;
diff-then-confirm, prompt defaults to no — see the `[DECISION:]` above). What's still open is
whether a check running inside `verify.all` should offer the same thing, or stay strictly
report-only because it runs as part of a broader batch nobody is watching closely.]

[NEEDS CLARIFICATION: scope — just `~/AGENTS.md`, or generalize to every `wrapper-script`-deployed
package (`askpass-zenity`, etc.) plus PULSE-authored skill directories under `~/.agents/skills/`?
Recommend generalizing (the underlying mechanism is generic either way — iterate
`util.packages_by_method(util.PackageMethod.WRAPPER_SCRIPT)` for the first kind,
`.pulse-source`-marked dirs for the second) but flagging since it's not forced by anything above.
**Extended 2026-08-23:** `config_files` destinations are a third kind, reachable via the new
`util.enabled_packages()` (method-agnostic, since any method may declare the field). Whether they
belong in the same check at all is a genuine question, not a given: unlike `wrapper-script`, their
install-time write is skip-if-exists, so drift there is the expected steady state rather than a
warning sign — a check that flags them the same way would cry wolf on every `config_files` package
the user has ever customized. Options are excluding them, or reporting them in a separate,
informational "your local copy differs, `inv system.configs` would overwrite it" tier.]

## Recommended direction

Not implementing here — this plan exists to lay out comparable concrete approaches for whoever picks
it up, per explicit instruction to be creative and not converge on one. All four reuse the same
grounding facts above; they differ in _when_ drift is caught and _who_ it's surfaced to.

### Approach A — real-time, agent-facing `PostToolUse` hook ("nag the agent")

Fires the instant Claude Code edits a PULSE-deployed path; injects a non-blocking instruction
telling _Claude_ (not the human) to read the current repo-side file and mirror the edit there,
leaving commit/push to the human. Concrete design, grounded in the real code
(`tasks/tools.py:_install_wrapper_script`, `tasks/ai.py:_install_local_skill`/`_SKILL_MARKER`,
`tasks/util.py:PULSE_STATE_DIR`/`load_claude_settings`/`write_claude_settings`):

- **New shared module `tasks/pulse_guard.py`** (no `@task`s of its own, like `ui.py`/`util.py` — no
  `tasks/__init__.py` wiring needed):
  - `_SKILL_MARKER = ".pulse-source"` — moved here from `tasks/ai.py`; `ai.py` imports it from here.
  - `wrapper_script_mappings() -> dict[str, str]`: abs deployed path (`dest`, and `symlink_dest` if
    declared — both map to the same repo source, so a hook lookup matches whichever of
    `~/.claude/CLAUDE.md` / `~/AGENTS.md` Claude Code reports) → abs repo-side `content_file` path,
    for every enabled `[packages.*]` entry with `method = "wrapper-script"` and a `content_file`.
    Include all such packages unconditionally (not just `claude-global-md`) — generic and harmless.
  - `installed_skill_dir_mappings(base: Path) -> dict[str, str]`: abs deployed skill dir → abs
    repo-side skill dir, for every currently-installed `.pulse-source`-marked directory under
    `<base>/.agents/skills/` (reads the marker's own recorded `repo_path`).
  - `sync_wrapper_scripts()` / `sync_skill_dirs(base)`: regenerate the `"files"`/`"dirs"` section of
    the map (each fully replaces its own section, leaves the other untouched), then call
    `register_hook()`. No-op under `util.DRY_RUN`. `sync_skill_dirs` only called for the global run
    (`base == home`) — mirrors the existing `if dir is None:` gate that already skips
    `_apply_static_claude_permissions`/`_note_copilot_permissions` for `--dir` runs.
  - `register_hook()`: idempotently merge a `PostToolUse`/`"Edit|Write"` hook entry into the global
    `~/.claude/settings.json` (command = deployed path of `pulse-guard-hook`, read from
    `util.load_config()["packages"]["pulse-guard-hook"]["dest"]`, not hardcoded a second time) using
    `util.load_claude_settings()`/`write_claude_settings()`. Same merge-without-clobbering shape as
    the `repo_tasks.agents.claude_hook` precedent (find-or-create the matcher group, append only if
    the exact entry isn't already `in` that group's `"hooks"` list).
  - **Wiring**: `tools.py:install()` calls `pulse_guard.sync_wrapper_scripts()` after its existing
    wrapper-script loop; `ai.py:skills()` calls `pulse_guard.sync_skill_dirs(base)` alongside the
    existing `if dir is None:` block.

- **Mapping file** `~/.local/state/power-user-linux-setup/guard-map.json`:
  ```json
  {
    "version": 1,
    "generated_at": "2026-08-22T12:34:56+00:00",
    "repo_root": "/home/.../power-user-linux-setup",
    "files": { "/home/.../AGENTS.md": "/home/.../config/global-AGENTS.md" },
    "dirs": { "/home/.../.agents/skills/research-library": "/home/.../skills/research-library" }
  }
  ```
  Both sides absolute (no path-joining logic needed in the hook script itself). `repo_root` is for
  human debugging only, not read by the hook.

- **New `setup.toml` package**:
  ```toml
  [packages.pulse-guard-hook]
  description = "PostToolUse hook that nags Claude Code to mirror an edit of a PULSE-deployed file back into this repo's own source"
  method = "wrapper-script"
  tags = ["shell", "ai"]
  dest = "~/.local/bin/pulse-guard-hook"
  content_file = "config/pulse-guard-hook.py"
  ```
  No `symlink_dest`. Being a `wrapper-script` entry itself, it's automatically picked up by
  `wrapper_script_mappings()` too.

- **Hook script `config/pulse-guard-hook.py`** — stdlib-only Python (first Python `wrapper-script`
  content file in the repo; every existing one is `.sh`, but `_install_wrapper_script` is
  content-agnostic and already `chmod`s to `0o755`). Reads stdin JSON, extracts
  `tool_input.file_path`, resolves it (`Path.resolve()` — handles the `CLAUDE.md`/`AGENTS.md`
  symlink case), looks it up against `guard-map.json` (exact match in `"files"`, then
  directory-prefix match in `"dirs"`). No match → print nothing, exit 0 (confirmed sufficient — not
  in the docs' "stdout shown to Claude" exception list). Match → print
  `{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "<path> is a
  PULSE-managed deployed copy of <repo path> — a deliberate plain copy, not a symlink, silently lost
  on the next inv tools.install/ai.skills. Read the CURRENT repo-side content first (it may have its
  own uncommitted changes), decide whether the same edit still makes sense, and if so make it there
  instead. Leave commit/push/re-running inv tools.install/ai.skills to the human."}}`.
  Exit code always 0 — `PostToolUse` exit 2 has no blocking effect since the tool call already
  completed.

- **Docs**: new `## pulse-guard` section in `docs/claude-code.md`, same placement/style as the
  existing `## direnv auto-activation...`/`## ~/AGENTS.md` sections; amend the `## ~/AGENTS.md`
  section's "a manual edit gets silently overwritten..." sentence to note `pulse-guard` catches this
  specifically when Claude Code itself makes the edit.

- **Tests**: `tests/test_pulse_guard.py` (tmp_path fixtures, monkeypatched `util.load_config`, same
  shape as `tests/test_ai.py`) for the mapping/sync/register functions;
  `tests/test_pulse_guard_hook.py` loading `config/pulse-guard-hook.py` via
  `importlib.util.spec_from_file_location` to unit-test its match logic directly (no other
  `config/*.sh` content file is tested today, but this one has real branching logic worth covering).

- **Already-resolved design defaults** (no need to re-decide): matcher `"Edit|Write"` only, no
  `MultiEdit` (not a documented current tool name); include _all_ `wrapper-script` packages in the
  map, not just `claude-global-md`; `--dir` project-local `ai.skills` runs never populate `"dirs"`.

- **Catches:** drift caused by Claude Code specifically, the moment it happens, before it's
  forgotten.
- **Misses:** drift from a human hand-edit, a different AI tool/agent, or any edit made outside a
  Claude Code Edit/Write tool call (e.g. a raw `vim ~/AGENTS.md`). Also only as good as the mapping
  file being fresh (regenerated at `inv tools.install`/`inv ai.skills` time).
- **Cost:** one Python interpreter startup + small JSON read on _every_ Edit/Write tool call
  machine-wide (not just PULSE-related edits) — accepted as cheap (~10-20ms) but non-zero and
  global.

### Approach B — mechanical drift check in `inv verify.all` ("catch it whoever caused it")

A new check alongside `tasks/verify.py`'s existing package verification: for every `wrapper-script`
package with a `content_file`, and every `.pulse-source`-marked skill dir, diff live deployed
content against the repo source; report (or fail) on mismatch. No LLM, no hook, no
Claude-Code-specific mechanism at all — a plain `Path.read_text()` comparison, same shape
`_install_wrapper_script`/`_install_local_skill` already do internally to decide "already installed"
vs. "needs update" (reuse that comparison logic rather than reimplementing it).

- **Catches:** drift from _any_ cause — human hand-edit, any AI agent/tool, partial/interrupted
  installs, filesystem corruption — the moment `inv verify.all` (or whatever wraps it, e.g. a
  pre-push hook) next runs.
- **Misses:** anything between runs — if `verify.all` only runs before a push, an edit made and lost
  between pushes is never caught. Cadence entirely depends on when the check is invoked (see open
  question above).
- **Cost:** cheap, one-time, only pays when `verify.all` actually runs — no standing per-edit cost.

### Approach C — PULSE-repo-side pre-push warning ("last safe moment before it's easy to lose track")

Narrower variant of B: instead of (or in addition to) `verify.all`, a git hook in the PULSE repo
itself, firing on `git push`, that diffs the _live deployed_ `~/AGENTS.md` (and other tracked
dotfiles/skills) against what's about to be pushed — warning specifically "the deployed copy has
content not reflected in what you're about to push, did you forget to port an edit back?" This is
the last moment before the human's own PULSE work solidifies a state that no longer matches what's
actually deployed — closer to the actual moment of loss than a generic `verify.all` run might be if
that's invoked rarely.

- **Catches:** the same drift as B, but specifically framed around the moment it's cheapest to
  notice and fix (right before a push, when the diff is fresh in the pusher's mind).
- **Misses:** anyone who doesn't push often, or drift that's introduced and then further overwritten
  by a _subsequent_ legitimate `inv tools.install` run before any push happens (the original edit is
  already gone by push time in that case — nothing left to warn about).
- **Cost:** same diff logic as B, wired to a different trigger (a git hook instead of an `inv` task)
  — largely a packaging/trigger choice layered on B's core check, not a separate implementation.

### Approach D — combine A + B (or A + C): defense in depth

Real-time agent nag (A) for the common case (Claude Code causes the drift, catch it immediately,
teach the agent to fix its own mess) plus a periodic mechanical check (B or C) as a safety net for
everything A structurally can't see (human edits, other tools, a missed/stale hook registration,
drift introduced before the hook mechanism existed). Marginal cost of building both is small since
B/C's diff logic and A's mapping-generation logic overlap heavily (both need "deployed path → repo
source path" for every `wrapper-script` package and skill dir) — a shared mapping/lookup module
could serve both, avoiding two independent implementations of the same lookup.

Given the memory-sweep plan already treats "drift guard" as one clearly-wanted mechanism and A's
concrete design already exists from prior work, D (build B or C as a lightweight complement to the
already-designed A) is probably the lowest-total-effort path to closing this gap completely — but
that's a lean, not a decision; genuinely fine to land just B alone first if the mechanical check
alone feels sufficient for now and A gets deferred.
