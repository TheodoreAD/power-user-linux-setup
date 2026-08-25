---
status: landed
updated: 2026-08-25
---

# One way to write a file into `~`

## Context

**Origin.** `plans/2026-08-22-memory-to-agents-md-migration-sweep.md` — its "Recommended direction"
item 1 ("Deployed-vs-source drift guard for `~/AGENTS.md`... mechanical, no LLM needed") and its
finding that `~/AGENTS.md` was found drifted from `config/global-AGENTS.md` _twice_ in one session
(once a same-session hand-edit to the deployed file, once older pre-existing drift nobody had
caught). A third, independent instance the same day, in an unrelated `scaffoldapy` session: a rule
added to the deployed `~/AGENTS.md` via the Edit tool, which the next `inv tools.install` would have
silently wiped, caught only by chance.

**Reframing, 2026-08-24.** This plan previously offered four comparable approaches (A: a real-time
`PostToolUse` hook nagging the agent; B: a mechanical check in `inv verify.all`; C: a pre-push git
hook; D: A+B). That framing treated the problem as _detection at a distance_ — catch the edit before
the next install destroys it. The user's reframing, which this rewrite adopts wholesale, is that the
problem is the **writer**: PULSE decides to overwrite a file in `~` without ever establishing
whether it put the current content there. Fix the writer so it cannot silently destroy, and the loss
window closes — nothing is lost, only deferred until a human sees a diff and decides. Detection at a
distance becomes a nice-to-have, not the mechanism.

The second half of the reframing: **there are too many ways to write into `~`.** That is measurably
true (inventory below), and any design that adds a fifth writer — Approach A's hook plus its own
`guard-map.json` would have been exactly that — makes the underlying problem worse while patching
one symptom of it.

[DECISION: Approach A (`PostToolUse` hook) and Approach C (pre-push git hook) are dropped, not
deferred. A existed only because the writer could destroy content unseen; once it can't, A's whole
value is catching the edit slightly earlier, at the cost of a fifth home-dir writer, a second
mapping file, and a per-Edit interpreter startup machine-wide. C was already pre-declined by
`plans/2026-08-23-git-hooks-for-quality-gate.md` (git hooks considered and rejected for this repo)
and by `config/global-AGENTS.md`'s "Proposing an enforcement mechanism for agent behavior" rule —
teach the agent what to run, don't fire behind its back. Approach B survives, demoted from
standalone mechanism to a read-only call into the shared classifier.]

### Inventory: what writes into `~` today

**Whole-file deploy from a repo-side source — three implementations, four policies:**

| writer                                   | ownership check                        | behavior on an existing destination                                        |
| ---------------------------------------- | -------------------------------------- | -------------------------------------------------------------------------- |
| `tasks/tools.py:_install_wrapper_script` | none                                   | **unconditional overwrite** — the actual loss mechanism                    |
| `tasks/ai.py:_install_local_skill`       | `.pulse-source` marker + `_dir_digest` | foreign → warn and leave; ours+stale → `ui.ask()`; ours+identical → silent |
| `tasks/apt.py:_apply_config_files`       | none                                   | skip-if-exists, silently                                                   |
| `tasks/system.py:_deploy_config_file`    | none                                   | diff → `util.confirm(default=False)` → overwrite; `--yes` skips the prompt |

Same operation, four answers, and the `config_files` mechanism alone is split across two modules
with opposite behavior. `_install_local_skill` is the most evolved of the four and already
implements almost exactly the policy this plan generalizes: a marker recording who installed it, a
digest comparison, and a refusal to touch anything it didn't install. The design below is largely
"promote that policy into one shared writer and make the other three use it," not a new invention.

**Two other ownership models that must NOT be folded in:**

- `util.ensure_block` / `util.ensure_block_text` — a marker-delimited region inside a file the
  **user** owns. ~12 call sites (`certs`, `ssh`, `proxy`,
  `system.curlrc/dns/disable_ipv6/
  journal_size/initramfs_compression`, `zsh`, `devcontainer`,
  `next_steps`). Whole-file deploy semantics here would destroy user content on first run.
- structured merge into a co-owned JSON — `util.write_claude_settings` (`ai.py`, `allowlist.py`),
  `fonts.py`'s VS Code settings merge. PULSE owns some keys; the user and other tools own others.

[DECISION: "one way to write into `~`" means **one way per ownership model**, not one writer for
everything. Three models are legitimate — whole-file deploy, marker-delimited block, structured
merge — because they differ in who owns what, not in style. Only the first is unified here. The
other two get a shared _registry_ entry (so "is this path PULSE-managed?" has one answer for all
three) but keep their own writers.]

### Grounding facts (do not re-derive)

- `~/AGENTS.md` (+ `~/.claude/CLAUDE.md` via `symlink_dest`) deploys from `config/global-AGENTS.md`
  through the generic `wrapper-script` method — a **plain copy** (`dest.write_text(content)`), where
  `content` is the source file `.strip() + "\n"`.
- Skills under `~/.agents/skills/<name>/` deploy from `skills/<name>/` via `shutil.copytree`, with a
  `.pulse-source` marker file recording the installing `repo_path`.
- Both are **deliberately** copies, not symlinks — skills were switched from symlink to copy to stay
  symmetric with the npx-sourced remote-skill installer. Copy-based deployment is a fixed
  constraint, not something to revert.
- `config_files` is a **third** mechanism, declarable by any `method`, keyed `dst` (not `dest`) — so
  any lookup keyed on `dest` alone silently skips it. Currently `wezterm` and `terminator`. Its
  install-time write is skip-if-exists: the destination is _expected_ to diverge, because the user
  owns it after first install.
- `tasks/util.py` already provides `PULSE_STATE_DIR` (`~/.local/state/power-user-linux-setup`),
  `confirm()` (returns its default unmodified when stdin isn't a tty), `DRY_RUN`,
  `enabled_packages()` (method-agnostic), `packages_by_method()`.
- `PULSE_STATE_DIR` already holds exactly this kind of per-machine generated metadata:
  `ai.py:_STATIC_PERMS_MANIFEST`, `allowlist.py:_APPLIED_MANIFEST`.

[PITFALL: `inv verify.all` **already** does a byte-exact content comparison of every
`wrapper-script` package against its `content_file` (`verify.py:_resolve_wrapper_script` /
`_wrapper_script_up_to_date`), and it runs as the last step of `inv setup`. An earlier revision of
this plan asserted it checked `dest` existence only, and that stale claim survived into the
four-approach design — it is why "Approach B" was written up as unbuilt work. Detection for the
wrapper-script mechanism already ships. What does not exist is (a) coverage for skill dirs and
`config_files`, (b) the stale-vs-dirty distinction, and (c) a writer that acts on any of it.]

### Confirmed hook mechanics — recorded, then discarded

`PostToolUse` with matcher `"Edit|Write"` can exit 0 and print
`{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "..."}}` to inject a
non-blocking instruction into the calling agent's context; printing nothing and exiting 0 is a valid
no-op. Verified against live docs 2026-08-22. Kept here only so a future revisit doesn't re-research
it. Also confirmed and still relevant as context: Claude Code's built-in `Plan`/`Explore` subagent
types deliberately skip loading `CLAUDE.md`/`AGENTS.md` entirely, so no wording fix in `~/AGENTS.md`
can reach those two agent types — which is why the fix has to live in the writer rather than in
instructions.

## Design

### 1. `tasks/deploy.py` — the registry, the classifier, the writer

New module. Holds both the shared functions (no `@task`) and the two user-facing tasks (§5), in the
shape of `system.py`/`ai.py` rather than the pure-helper shape of `util.py`/`ui.py`.

**Registry.** `managed_paths() -> dict[Path, Managed]` resolves every home-directory path PULSE
claims, from `setup.toml` alone:

- every enabled `[packages.*]` with `method = "wrapper-script"` and a `content_file` → its `dest`,
  **and its `symlink_dest` if declared** (both map to the same repo source, so a lookup matches
  whichever of `~/.claude/CLAUDE.md` / `~/AGENTS.md` is asked about);
- every enabled `[packages.*]` declaring `config_files`, whatever its `method` → each mapping's
  `dst` (via `util.enabled_packages()`, not `packages_by_method()`);
- every `skills = [...]` entry → its installed directory under `<base>/.agents/skills/<name>`.

`Managed` carries `package`, `source` (repo-relative), `kind` (`FILE` | `DIR`), and `policy` (§3).

**Classifier.** `classify(path) -> State`, four states, computed from the destination, the repo
source, and the state manifest (§2):

| state     | signal                                                   | meaning                                      |
| --------- | -------------------------------------------------------- | -------------------------------------------- |
| `ABSENT`  | destination doesn't exist                                | first install                                |
| `CLEAN`   | destination hash == manifest hash == current source hash | nothing to do                                |
| `STALE`   | destination hash == manifest hash != current source hash | we wrote it, source moved on — safe redeploy |
| `DIRTY`   | destination hash != manifest hash                        | edited since we wrote it                     |
| `UNKNOWN` | destination exists, no manifest entry                    | provenance unknown — never assume it's ours  |

`STALE` vs `DIRTY` is the distinction that makes the user-facing message accurate, and it is exactly
what a plain deployed-vs-source comparison (all that exists today) cannot express.

[DECISION: five states, not the four originally sketched. `UNKNOWN` has to be separate from `DIRTY`:
on a machine where the state manifest was never written (a fresh clone, a wiped state dir, a base
image that shipped its own `~/.zshrc`) every managed path would otherwise classify as `DIRTY` and
prompt. `UNKNOWN` is also what §8's backfill resolves.]

**Writer.** `deploy(managed, *, assume_yes) -> Action` — the single whole-file writer:

- `ABSENT` → create, silently. Record in the manifest.
- `CLEAN` → no-op, no output beyond a status line. Routine re-runs stay quiet.
- `STALE` → overwrite, silently. This is a redeploy of content we own; nothing is lost.
- `DIRTY` → **never silent.** Print the unified diff (reuse `system.py:_config_diff`), then
  `util.confirm(f"Overwrite {dst}?", default=False)`. `--yes` skips the prompt and overwrites.
- `UNKNOWN` → same as `DIRTY` for a `MANAGED` policy; leave alone with a note for `SEEDED` (§3).

Post-write verification is preserved from both current writers: re-read/re-hash and raise if the
written content doesn't match, before recording the manifest entry, so a partial copy is never
recorded as clean.

**Unmanaged paths.** `classify()` on a path with no registry entry returns nothing, and the
user-facing task reports it as the user asked for: _not managed by PULSE — if you want this file
deployed and version-controlled, add a `[packages.*]` entry for it_. This is the teaching moment
that replaces Approach A's hook: an agent or human running the task learns both what happened and
what to do, from PULSE itself.

### 2. State manifest

`~/.local/state/power-user-linux-setup/deployed.json`:

```json
{
  "version": 1,
  "entries": {
    "/home/tdumitrescu/AGENTS.md": {
      "package": "claude-global-md",
      "source": "config/global-AGENTS.md",
      "hash": "sha256:...",
      "deployed_at": "2026-08-24T09:14:02+00:00"
    }
  }
}
```

Absolute paths on the key side (no path-joining in any consumer). `hash` is of **what PULSE wrote**,
not of the source — that is the whole point; for a `DIR` entry it is `ai.py:_dir_digest`, reused
as-is.

[DECISION: the deploy record goes in `PULSE_STATE_DIR`, never into `setup.toml`. `setup.toml` is a
tracked, git-shared _declaration_; writing per-machine runtime timestamps into it would churn the
diff on every install on every machine, make `git blame` on the declaration useless, and constitute
auto-mutation of a tracked artifact — the thing `~/AGENTS.md`'s "Regenerating a file from a
canonical source" rule exists to prevent. `PULSE_STATE_DIR` is the established home for exactly this
(`_STATIC_PERMS_MANIFEST`, `_APPLIED_MANIFEST`).]

[DECISION: store a content hash, with the timestamp as a human-facing extra — not a date alone.
"When did we last write this" cannot answer "has it been edited since"; only the hash can.
`deployed_at` earns its place in the message ("deployed 2026-08-14, edited since") and in debugging,
never in the branching logic.]

[DECISION: keep `.pulse-source` as well; the manifest does not replace it. The marker lives _inside_
the deployed artifact, so it survives a wiped state dir, and it is how `_install_local_skill`
distinguishes "the skill we installed" from "a hand-installed skill that happens to share a name."
Marker answers _whose is this_; manifest answers _what did we write and when_. Two questions, two
records, no working code ripped out.]

### 3. Two ownership policies, one writer

The three mechanisms differ in one real way, and it is not the write itself:

- `MANAGED` — `wrapper-script`, skill dirs. PULSE owns the content. `DIRTY` is a **problem**: the
  edit will be lost on redeploy and hasn't reached the repo. Message says so and names the repo-side
  source to port it into.
- `SEEDED` — `config_files`. PULSE seeds the file once; the user owns it afterwards. `DIRTY` is the
  **expected steady state**. Message is informational: _your copy differs from `config/wezterm.lua`;
  `inv deploy.all --name wezterm` would overwrite it._ Never a warning, never a `verify.all`
  failure.

[DECISION: the policy is a severity/messaging distinction on a shared classification, not a
different writer or a separate "informational tier" bolted on. An earlier revision proposed either
excluding `config_files` from the check or reporting it separately, because without a manifest
"deployed != source" is genuinely unclassifiable for a skip-if-exists mechanism and would cry wolf
on every customized config. The manifest removes that constraint: `SEEDED` + `DIRTY` is precisely
"the user customized what we seeded," and is now sayable.]

### 3a. The one `SEEDED`/`DIRTY` instance standing today

Recorded so sessions stop rediscovering it and reporting it as a new problem. It was re-flagged as a
finding on 2026-08-24 by a session that had no way to tell it was known and expected — which is
itself the argument for §3's messaging split.

`deploy.status` reports:

```
[deploy] terminator: ~/.config/terminator/config — differs from its source — either edited here, or the source moved on
[deploy] wezterm:    ~/.config/wezterm/wezterm.lua — ok
```

Terminator's actual divergence, measured 2026-08-24 — the deployed file is _older_ (2026-06-09) than
`config/terminator.conf` (2026-08-08), so this is not a recent hand-edit:

- font differs: source `CaskaydiaCove Nerd Font Mono 12`, deployed `JetBrainsMono Nerd Font 13`
- deployed has four sections the source lacks: `[global_config]`, `[keybindings]` (a `hide_window`
  binding), `[layouts]`, `[plugins]`

Most of that is terminator writing its own config back — it rewrites the file on preference and
layout changes, so a deployed terminator config will _always_ diverge from a seed. That is the
purest possible example of `SEEDED`: the app itself is a second writer, on top of the user.

[DECISION: nothing to fix here, and specifically **not** a reason to redeploy. `config_files` is
skip-if-exists precisely so the user (and the app) own the file after first install, so overwriting
it would destroy real customization to make a status line quieter. The correct outcome is §3's
messaging change, which turns this line from "differs — either edited here, or the source moved on"
into an informational "your copy differs from `config/terminator.conf`". Until that lands, this
entry is the answer to "is the terminator drift a problem?" — no.]

[NEEDS CLARIFICATION: separately from the messaging, does the source seed want updating? It carries
a font this machine no longer uses, so a fresh install would seed something immediately overwritten
by hand. That is a content question about `config/terminator.conf`, independent of the writer design
this plan owns, and possibly worth its own small change rather than being bundled here.]

### 4. Converting the call sites

- `tools.py:_install_wrapper_script` → resolves its `Managed` entry and calls `deploy.deploy()`.
  Keeps its own `symlink_dest` handling (creating/validating the symlink is not a content write).
  **Behavior change:** unconditional overwrite becomes classify-then-act. See §7.
- `apt.py:_apply_config_files` → calls `deploy.deploy()`. Its skip-if-exists behavior is now
  expressed as the `SEEDED` policy rather than an unconditional `if not dst.exists()`, so a
  first-install on a machine where the file already exists is _reported_ instead of silently
  skipped.
- `system.py:_deploy_config_file` → deleted; `system.configs` becomes `deploy.all` (§5).
- `ai.py:_install_local_skill` → keeps its `.pulse-source`/`_dir_digest` logic, but reports through
  the same `State` vocabulary and records to the same manifest, so `deploy.status` covers skills
  without a second scan. Its existing `ui.ask()` prompt stays as the `DIRTY`/`STALE` prompt for
  dirs.

[DECISION: `_install_local_skill` is adapted rather than replaced. It is the only one of the four
writers whose policy is already right, its `foreign` branch is a real behavior worth preserving
verbatim, and directory deployment has genuine mechanics (rmtree-then-copytree, per-file digest)
that a file writer doesn't. Sharing the classifier and manifest is where the value is; sharing the
byte-level write is not.]

### 5. Task surface

`inv deploy.status` — read-only. Every registry entry, its state, and for `DIRTY` the diff. Never
writes, never prompts, honors `--name`. This is the "what happened / what should I do" surface.

`inv deploy.all` — the repair path. Same flags as today's `system.configs` (`--name`, `--yes`), same
interactive contract.

[DECISION: `inv system.configs` (landed 2026-08-23) is renamed and generalized into `inv
deploy.all`
rather than kept alongside. It is the same operation with a narrower registry, and keeping both
would restore the exact duplication this plan exists to remove. Two extra reasons: `configs` is
_already_ a top-level namespace imported from `repo-tasks` in `tasks/__init__.py`, so
`inv configs.*` and `inv system.configs` currently coexist as unrelated things; and the task no
longer deals only with the `config_files` mechanism, so its name would be actively wrong. This is a
one-day-old task in a single-user repo — cheap to rename now, expensive later. Reversible on
request.]

Register `deploy` in `tasks/__init__.py`'s `Collection`.

### 6. `verify.all` integration

`verify.py` calls `deploy.classify()` read-only for every registry entry, replacing
`_resolve_wrapper_script`/`_wrapper_script_up_to_date`'s bespoke comparison and extending coverage
to skill dirs and `config_files`. `MANAGED` + (`DIRTY` | `UNKNOWN`) fails, consistent with
`verify.py`'s existing fail-fast contract. `SEEDED` + `DIRTY` reports and passes.

[DECISION: read-only inside `verify.all` — it never prompts and never fixes. The user's stated
aversion is to auto-_mutating_ tracked artifacts, which a report doesn't do; and `verify.all` runs
inside `inv setup` as part of a batch nobody is watching line by line, which is the wrong moment to
ask a destructive question. `deploy.all` is the deliberate, human-invoked moment for that.]

### 7. Unattended paths — the one real regression risk

`_install_wrapper_script` going from unconditional-overwrite to prompt-on-`DIRTY`/`UNKNOWN` changes
behavior on every non-interactive path. `util.confirm()` returns its default when stdin isn't a tty,
and the default is `False` — so a container or CI bootstrap that hits a pre-existing destination
would silently **not deploy**, where today it overwrites. That is a genuine regression, and it fails
quietly, which is the worst shape.

Every unattended entry point must pass `--yes` (or set `PULSE_ASSUME_YES`) explicitly and be tested
for it: `bootstrap.sh`, `bootstrap-devcontainer.sh`, `docker/Dockerfile`, and the CI workflows.

[PITFALL: this is the one change in the plan that can break something that works today. The failure
mode is a container image that looks like it built fine but is missing a deployed dotfile — no error
anywhere. Cover it with an explicit test asserting that a non-tty run without `--yes` leaves a
`DIRTY` destination alone _and_ says so on stdout, and one asserting the unattended entry points
pass the flag.]

### 8. Backfill on first run

Every currently-deployed path has no manifest entry, so a naive first run classifies the whole
machine as `UNKNOWN` and prompts for each one.

On first run (`deployed.json` absent, or a path missing from it): if the destination's content
matches its current repo source byte-for-byte, record it as ours and classify `CLEAN` — no prompt.
Only a genuine mismatch stays `UNKNOWN` and asks. This makes the upgrade a no-op on a machine that
is already in sync, which this one currently is for every `MANAGED` path.

### 9. Docs

- `docs/claude-code.md`'s `## ~/AGENTS.md` section: amend the "a manual edit gets silently
  overwritten" sentence — it is no longer true once §4 lands.
- `AGENTS.md`'s "Deployed dotfiles are generated" redeploy table: `inv system.configs` →
  `inv
deploy.all`, and the `content_file` row gains it too (`inv tools.install` deploys;
  `inv
deploy.all` repairs).
- `docs/configuration.md`: note that `wrapper-script` and `config_files` destinations differ in
  ownership policy, not just in field name.

## Files touched

| file                                                                           | change                                                         |
| ------------------------------------------------------------------------------ | -------------------------------------------------------------- |
| `tasks/deploy.py`                                                              | new — registry, classifier, writer, `status`/`sync` tasks      |
| `tasks/__init__.py`                                                            | register the `deploy` collection                               |
| `tasks/tools.py`                                                               | `_install_wrapper_script` delegates the content write          |
| `tasks/apt.py`                                                                 | `_apply_config_files` delegates                                |
| `tasks/ai.py`                                                                  | `_install_local_skill` reports/records through `deploy`        |
| `tasks/system.py`                                                              | `_deploy_config_file`/`configs` removed (moved to `deploy.py`) |
| `tasks/verify.py`                                                              | wrapper-script check → `deploy.classify()`, coverage extended  |
| `bootstrap.sh`, `bootstrap-devcontainer.sh`, `docker/Dockerfile`, CI workflows | pass `--yes`                                                   |
| `tests/test_deploy.py`                                                         | new — absorbs `tests/test_system.py`'s config-deploy tests     |
| `AGENTS.md`, `docs/claude-code.md`, `docs/configuration.md`                    | §9                                                             |

## Verification

- Unit: each of the five states, for `FILE` and `DIR`, for both policies, via `tmp_path` +
  monkeypatched `util.load_config()` (the shape `tests/test_ai.py` and `tests/test_system.py`
  already use).
- Backfill: a fixture with a deployed file matching source and no manifest classifies `CLEAN`
  without prompting; one that differs stays `UNKNOWN`.
- Non-tty: a `DIRTY` destination with stdin not a terminal and no `--yes` is left alone, and says so
  on stdout (§7).
- `PULSE_DRY_RUN=1` reports every state without writing or prompting.
- Live: hand-edit `~/AGENTS.md`, run `inv tools.install`, confirm it shows the diff and asks rather
  than overwriting; answer no; confirm the edit survives. Then port it to `config/global-AGENTS.md`
  and confirm the next run classifies `STALE` and redeploys silently.
- `inv verify.all` passes on this machine with no new failures (§8's backfill is what makes this
  true).

## Progress — steps 1 and 2 landed 2026-08-24

`tasks/deploy.py` exists with the registry, the five-state classifier, the state manifest at
`~/.local/state/power-user-linux-setup/deployed.json`, the writer, and `inv deploy.status`.
`tests/test_deploy.py` covers it. `d7cbcbd` (module + tests, wired to nothing), `5a9ff15`
(`deploy.status`), plus wording/naming corrections in `48eb699` and `d70877a`.

What a session picking up step 3 should know:

- **`deploy()` is written and tested but has no caller.** Step 3 is a task wrapping it; step 4 is
  converting the three existing writers to call it. Nothing in `tools.py`/`apt.py`/`ai.py` has
  changed behavior yet — `_install_wrapper_script` still overwrites unconditionally.
- **`inv deploy.all`, not `deploy.sync`** — renamed by
  `plans/2026-08-24-invoke-task-naming-convention.md` before step 3 was written. `deploy.status`
  keeps its name under that convention's community-convention clause.
- **The backfill works in practice, not just in tests.** On this machine, 13 of 14 managed paths
  classified `CLEAN` with no manifest at all. The single outlier is `~/.config/terminator/config` —
  `SEEDED`, rewritten by terminator itself, recorded as known-and-expected in `73e3a81`. Expect
  `inv deploy.status` to show exactly that one line.
- **`ai.py` already shares this module's `SKILL_MARKER`/`dir_digest`**, so step 4's conversion of
  `_install_local_skill` starts from shared primitives rather than a second copy.

[PITFALL: the mechanism has now been exercised twice for real, and both times its value was telling
a human _which_ files to look at before overwriting: after the task renames it flagged exactly the
five deployed sources that had gone stale, and before redeploying `~/AGENTS.md` it showed the diff
was purely repo-side with nothing existing only at the destination. Keep that property in step 3 —
`deploy.all` should show the diff before it asks, never just prompt.]

## Progress — step 3 landed 2026-08-24

`inv deploy.all [--name <pkg>] [--yes]` wraps `deploy()` over `_scoped(name)` and prints an action
summary; `system.configs` and its tests are gone, and every doc that named it (`AGENTS.md`'s
redeploy table, `docs/configuration.md`, `docs/terminal.md`, `docs/claude-code.md`, the `setup.toml`
header, `apt.py`'s docstring) now names `deploy.all`. Trigger, same day: `~/AGENTS.md` was
redeployed by calling `tools._install_wrapper_script` from `python -c` to avoid `inv tools.install`
re-running every installer — rejected as an ad-hoc write nobody can re-run, and recorded as the
second live confirmation in `AGENTS.md`. Exercised for real: `deploy.status` clean except the known
terminator line; `deploy.all --name claude-global-md` reports the file already matches. Step 4
(converting the writers) is still open — `inv tools.install`'s wrapper-script writer still
overwrites unconditionally.

## Progress — step 4 landed 2026-08-25

All three install-time writers now call `deploy.deploy()`: `tools._install_wrapper_script` keeps
only its `symlink_dest` handling, `apt._apply_config_files` is the `SEEDED` policy rather than a
bare `if not dst.exists()`, and `ai._install_local_skill` keeps its foreign check and its own
install/update prompt but hands the copy, verification, marker and manifest record to the shared
writer (calling it with `assume_yes=True` so the DIRTY case isn't asked twice; its own prompt now
says "edited since PULSE deployed it" and defaults to no for that case). The loss window this plan
opened with is closed: `inv tools.install` against a hand-edited `~/AGENTS.md` prints the diff and
leaves it alone.

§7's unattended path: `util.ASSUME_YES` (`PULSE_ASSUME_YES=1`), honored by `deploy()`, is the
env-var form of `--yes` for `inv setup`, which has no flag of its own; `bootstrap-devcontainer.sh`
sets it, and `docker/Dockerfile` + `.devcontainer/devcontainer.json` both reach `inv setup` only
through that script. CI workflows only ever run `PULSE_DRY_RUN=1`, so nothing to wire there. Tests:
`tests/unit/test_tools.py` (rewritten — non-tty-without-yes leaves the edit and says so, assume-yes
overwrites, dry-run still prints `MISSING` for `phases.py`'s probe, symlink handling), new
`tests/unit/test_apt.py`, two new `_install_local_skill` cases in `test_ai.py`, and a
`test_devcontainer.py` check that every `inv setup` line in the bootstrap script carries the flag.

[PITFALL: `ai._local_skill_plan`'s old `up_to_date` input was "ours and digests match"; the shared
classifier's backfill rule means a marker-owned directory with no manifest entry classifies
`UNKNOWN` when it differs from source, which the plan function maps to "update" (prompted, as
before), not "overwrite" — there is no record to prove it was edited rather than simply stale. Only
a real manifest entry can produce `DIRTY`, so the sharper prompt only fires for copies made after
step 1 landed.]

## Progress — step 5 landed 2026-08-25

`verify.py`'s bespoke `_wrapper_script_expected`/`_wrapper_script_up_to_date` comparison is gone;
the `"content"` check kind became `"deploy"`, a read-only `deploy.classify()` call on the registry
entry (`_classify_deploy`), with `_deploy_check` turning the state into a verdict: MANAGED must be
CLEAN, SEEDED fails only when ABSENT. `_all_checks` sweeps `deploy.managed_paths()` for every
non-wrapper-script entry, so `config_files` (act, terminator, wezterm) and all nine skills now
appear in `inv verify.all`; wrapper-script paths still come through `_resolve` so `verify_cmd`/
`verify = false` keep applying. `deploy._SUMMARY` became public `SUMMARY` for the failure message.
`PULSE_DRY_RUN=1 inv verify.all` on this machine: terminator reports ok (seeded, customized), every
skill ok. Evidence for the design choices is in `contributing/verify.md`.

All five steps are done. What remains is the two `[DEFERRED]` items below (the declared-but-disabled
orphan, tracked in `plans/2026-08-24-machine-local-setup-toml-overrides.md`, and drift
classification for `ensure_block`/`write_claude_settings` targets), neither of which blocks retiring
this plan once its durable content is confirmed to live in `docs/configuration.md`,
`contributing/verify.md` and `tasks/deploy.py`'s docstring.

## Sequencing

Five steps, each independently committable and independently useful — all landed (see Progress
above):

1. **`tasks/deploy.py` + manifest + tests**, wired to nothing. Pure addition, no behavior change.
2. **`inv deploy.status`** — read-only. Immediately answers "what's drifted on this machine right
   now" and validates the classifier against reality before anything can overwrite.
3. **`inv deploy.all`**, absorbing `system.configs` (+ the `AGENTS.md` table update). Repair path
   available before any writer changes behavior.
4. **Convert the writers** (`tools.py`, `apt.py`, `ai.py`) + the `--yes` wiring on unattended paths.
   This is the step that actually closes the loss window, and the one carrying §7's risk — land it
   on its own so a bisect points straight at it.
5. **`verify.py`** → shared classifier, coverage extended to skills and `config_files`. Docs.

## Explicitly not building

- The `PostToolUse` hook (old Approach A) and the pre-push git hook (old Approach C) — see the
  `[DECISION:]` in Context.
- Any auto-porting of a deployed edit back into the repo source. PULSE reports and asks; the human
  decides and commits.
- Folding `ensure_block` or `write_claude_settings` into the shared writer — different ownership
  models, see the `[DECISION:]` in Context.

[DEFERRED: the agent that dirties a deployed file still learns nothing _at edit time_ — only whoever
next runs a PULSE task does. Accepted: the actual harm was silent loss, which this closes; "port it
back to the repo" is ergonomics, and `~/AGENTS.md`'s own header already says it. If drift keeps
happening after this lands, revisit the real-time hook _then_, with evidence rather than on
prediction.]

[DEFERRED: `ensure_block` and `write_claude_settings` call sites get registry entries (so "is this
path PULSE-managed?" has one answer) but no drift classification of their own — a marker-delimited
block and a merged JSON key each need their own notion of "dirty" that this plan doesn't design.
**Narrowed in step 2:** `inv deploy.status --path` now at least _detects_ a block-owned file (any
file containing a `PULSE::` marker, covering both `MarkerStyle`s in one scan) and says PULSE owns
only the marked regions inside it. That's detection, not classification — it still can't say whether
a block has drifted from what the task would write. `write_claude_settings` targets remain entirely
undetected.]

[PITFALL: the first live run of `inv deploy.status --path ~/.zshrc` reported "not deployed by PULSE
— nothing here deploys, tracks, or restores it", which is false: `zsh.configure` writes marked
blocks into that exact file. The unmanaged-path message is the whole teaching moment this mechanism
exists for, and it was confidently wrong in the most-likely-to-be-asked case. Found by running the
command against a real home directory, not by review or by any unit test — the tests only ever asked
about paths the fixtures had invented.]
