# How PULSE writes into `~` — `tasks/deploy.py`

Design rationale and pitfalls behind the one home-directory writer. `docs/configuration.md` ("Whole-
file configs") is the user-facing page; `tasks/deploy.py`'s docstrings carry the code contract. This
page keeps the reasoning that isn't visible from either — extracted from the now-retired
`plans/2026-08-22-deployed-config-drift-guard.md` when it landed (2026-08-25).

## The problem was the writer, not detection

`~/.agents/AGENTS.md` was found hand-edited-then-overwritten three times in two days (2026-08-22):
twice in one session, once in an unrelated `scaffoldapy` session that added a rule to the deployed
file via the Edit tool — an edit the next `inv tools.install` would have silently wiped, caught only
by chance. The first design offered four detection mechanisms (a `PostToolUse` hook nagging the
agent, a check in `inv verify.all`, a pre-push git hook, or a combination). The reframing that
stuck: PULSE was deciding to overwrite a file in `~` without ever establishing whether it had put
the current content there. Fix the writer so it cannot silently destroy, and the loss window closes
— nothing is lost, only deferred until a human sees a diff and decides. Detection at a distance
becomes a nice-to-have.

The second half of the reframing: there were **too many ways to write into `~`** — three
implementations of "deploy a whole file from a repo-side source" with four different answers to "the
destination already exists" (unconditional overwrite, skip-if-exists, diff-then-prompt, and
marker-checked prompt). Any design adding a fifth writer (the hook plus its own mapping file would
have been exactly that) made the underlying problem worse while patching one symptom.

**Dropped, not deferred:** the `PostToolUse` hook (its whole value once the writer can't destroy is
catching the edit slightly earlier, at the cost of a fifth writer, a second mapping file, and a
per-Edit interpreter startup machine-wide) and the pre-push git hook (`~/.agents/AGENTS.md`'s
"Proposing an enforcement mechanism for agent behavior" — teach the agent what to run, don't fire
behind its back). The hook mechanics were verified before being discarded, and are kept here so
nobody re-researches them: `PostToolUse` with matcher `"Edit|Write"` may exit 0 and print
`{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "..."}}` to inject a
non-blocking instruction into the calling agent's context; printing nothing and exiting 0 is a valid
no-op. Also relevant: Claude Code's built-in `Plan`/`Explore` subagents skip `CLAUDE.md`/
`AGENTS.md` entirely, so no wording in `~/.agents/AGENTS.md` can reach them — another reason the fix
had to be in the writer, not in instructions.

## One writer per ownership model, not one writer for everything

Three ownership models are legitimate because they differ in _who owns what_, not in style:

- **Whole-file deploy** — `wrapper-script` `content_file`s, `config_files`, skill directories.
  Unified in `deploy.py`.
- **Marker-delimited block inside a file the user owns** — `util.ensure_block` (`~/.zshrc`,
  `~/.ssh/config`, `/etc/sysctl.conf`, ...). Whole-file semantics here would destroy user content on
  first run.
- **Structured merge into a co-owned JSON** — `util.write_claude_settings`, `fonts.py`'s VS Code
  settings merge. PULSE owns some keys; the user and other tools own others.

Only the first is unified. The other two keep their own writers; `deploy.status --path` at least
_detects_ a block-owned file (any file containing a `PULSE::` marker) and says PULSE owns only the
marked regions — detection, not drift classification, which they still lack (tracked in
`plans/2026-08-24-machine-local-setup-toml-overrides.md`).

## Five states, and why not four

`classify()` returns `ABSENT` / `CLEAN` / `STALE` / `DIRTY` / `UNKNOWN`. `STALE` vs `DIRTY` is the
distinction a plain deployed-vs-source comparison (all that existed before) cannot express, and it
is what makes the user-facing message accurate: "we wrote it, the source moved on — safe redeploy"
vs "edited since we wrote it — the edit is what you'd lose".

`UNKNOWN` had to be separate from `DIRTY`: on a machine where the state manifest was never written
(a fresh clone, a wiped state dir, a base image shipping its own `~/.zshrc`) every managed path
would otherwise classify `DIRTY` and prompt. **Backfill** resolves most of it: a destination with no
manifest entry that matches its source byte-for-byte is `CLEAN`, not `UNKNOWN`. Confirmed in
practice — 13 of 14 managed paths on the first machine classified `CLEAN` with no manifest at all.

## The manifest: where, and what it records

`~/.local/state/power-user-linux-setup/deployed.json`, keyed by absolute destination path, storing a
**content hash of what PULSE wrote** plus package, source, mechanism and a timestamp.

- **Never in `setup.toml`.** That file is a tracked, git-shared _declaration_; per-machine runtime
  timestamps in it would churn the diff on every install on every machine, make `git blame` on the
  declaration useless, and be exactly the auto-mutation of a tracked artifact
  `~/.agents/AGENTS.md`'s "Regenerating a file from a canonical source" exists to prevent.
  `PULSE_STATE_DIR` already held this kind of per-machine generated metadata (`ai.py`'s
  static-permissions manifest, `allowlist.py`'s applied manifest).
- **A hash, not a date.** "When did we last write this" cannot answer "has it been edited since";
  only the hash can. `deployed_at` is human-facing — never consulted by `classify()`.
- **The `.pulse-source` marker stays.** It lives _inside_ the deployed skill directory, so it
  survives a wiped state dir, and it is how the skill installer tells "the skill we installed" from
  "a hand-installed skill that happens to share a name". Marker answers _whose is this_; manifest
  answers _what did we write and when_. Two questions, two records.

## Two policies on one classification

`MANAGED` (wrapper-script, skills): PULSE owns the content; `DIRTY` is a problem, reported as one.
`SEEDED` (`config_files`): PULSE seeds once, the user owns it afterwards; `DIRTY` is the expected
steady state, reported for information, never a warning, never a `verify.all` failure.

This is a severity/messaging distinction on a shared classification, not a separate writer or an
"informational tier" bolted on. Before the manifest existed, "deployed != source" was genuinely
unclassifiable for a skip-if-exists mechanism and would have cried wolf on every customized config —
which is why an earlier design proposed excluding `config_files` from the check entirely.

The standing live example: `~/.config/terminator/config`. Terminator rewrites its own config on
preference and layout changes, so a deployed terminator config will _always_ diverge from its seed —
the purest case of `SEEDED`, where the app itself is a second writer on top of the user. It was
re-flagged as a "finding" by a session that had no way to tell it was known and expected, which is
itself the argument for the messaging split. Not a reason to redeploy: `config_files` is
skip-if-exists precisely so the user (and the app) own the file after first install.

## Copies, not symlinks — a fixed constraint

Skills were deliberately switched from symlink to copy to stay symmetric with the npx-sourced
remote-skill installer; `wrapper-script` has always been a plain copy. Copy-based deployment is what
makes a manifest necessary at all, and it is not something to revert.

## The one real regression risk: unattended runs

Converting `_install_wrapper_script` from unconditional-overwrite to prompt-on-`DIRTY`/`UNKNOWN`
changed behavior on every non-interactive path: `util.confirm()` returns its default when stdin
isn't a tty, and the default is `False`, so a container or CI bootstrap hitting a pre-existing
destination would silently **not deploy** — an image that looks like it built fine but is missing a
dotfile, no error anywhere. `PULSE_ASSUME_YES=1` (`util.ASSUME_YES`) is the env-var form of `--yes`
for the composite entry points that have no flag; `bootstrap-devcontainer.sh` sets it, and a test
asserts that every `inv setup` line in that script carries it. `verify.all` stays read-only inside
`inv setup` for the same reason — a batch nobody is watching line by line is the wrong moment to ask
a destructive question; `deploy.all` is the deliberate, human-invoked moment for that.

## Pitfalls hit while building it

- **`inv verify.all` already compared wrapper-script content byte-for-byte** when the first design
  was written; an earlier revision asserted it checked existence only, and that stale claim survived
  into the four-approach design as "unbuilt work". Read the code before designing around it. (That
  comparison has since been replaced by `deploy.classify()` — see `contributing/verify.md`.)
- **The unmanaged-path message was confidently wrong on the most-likely-asked path.** The first live
  `inv deploy.status --path ~/.zshrc` said "not deployed by PULSE — nothing here deploys, tracks, or
  restores it", which is false: `zsh.configure` writes marked blocks into exactly that file. Found
  by running the command against a real home directory, not by review or unit tests — the tests only
  ever asked about paths the fixtures had invented.
- **A marker-owned skill with no manifest entry classifies `UNKNOWN`, not `DIRTY`.** The skill
  installer's sharper "edited since PULSE deployed it — overwrite?" prompt (default no) can only
  fire for copies made after the manifest existed; older copies that differ from source get the
  plain "update?" prompt, because there is no record to prove they were edited rather than stale.
- **`--yes` was inert on exactly the paths it exists for.** The `SEEDED` branch returned
  `LEFT_ALONE` before ever reading `assume_yes`, so a customized `config_files` destination could
  not be overwritten at all — while the message that branch prints names the command
  (`inv deploy.all --name <pkg> --yes`) and `all_()`'s docstring says such a destination is "left
  alone unless `--yes`". Both documented an escape hatch the code did not have. Found 2026-08-30 by
  running the command the message suggested, after a font rename changed `config/wezterm.lua`; the
  existing tests covered the leave-it-alone path thoroughly and never asserted the documented way
  out of it. The general shape worth remembering: a branch that prints advice is a branch whose
  advice nobody has executed.
- **`deploy.all` must show the diff before it asks, never just prompt.** Both real exercises of the
  mechanism before the writers were converted had the same value: telling a human _which_ files to
  look at before overwriting — five stale deployed sources after a task-rename pass, and a
  `~/.agents/AGENTS.md` diff that was purely repo-side with nothing existing only at the
  destination.
- **The silent-wipe window was closed, and what closed it was a question rather than a failure.**
  Until 2026-08-25 `inv tools.install` overwrote a hand-edited deployed path with no diff and no
  prompt. It was caught live exactly once, and not by anything failing — the user asked "would this
  actually be installed?" of a file they had edited. Every PULSE writer now classifies first and
  asks; the reason this is worth recording is that nothing in the gate, the tests or the output
  would have surfaced it, which is the same shape as the `prune` orphan above.
- **Two rejections, a day apart, are why `deploy.all` exists as a task at all.** 2026-08-23:
  `config/wezterm.lua` had no redeploy path whatsoever, because the install-time writer skips any
  destination that already exists — a one-off `cp` was proposed and rejected with "there should be a
  pulse invoke task that deploys the wezterm config". 2026-08-24: redeploying `~/.agents/AGENTS.md`
  by calling `tools._install_wrapper_script` from `python -c`, specifically to avoid
  `inv tools.install` re-running every installer, was rejected the same way. Both are the same
  principle from two directions — a manual copy and an ad-hoc call into a private writer are equally
  changes nobody can re-run, and the whole point of the repo is that every change this machine has
  is reproducible from a declared command.
- **Rename the in-flight task before it lands, not after.** `deploy.sync` was renamed to
  `deploy.all` by the task-naming pass while still unwritten — "deploy sync" doesn't read as an
  imperative and `deploy` is an action namespace like `verify`/`clean` (see the
  `invoke-task-conventions` skill).

## Removing a destination: `inv deploy.prune`

Dropping a destination from `setup.toml` stops it being rewritten and removes nothing. The stale
file then outlives the declaration on every machine that ever had it, while a fresh machine never
grows one — so `deploy.status` and `home.list-claims`, which both answer from the declaration, go on
reporting a clean home directory that isn't. That is the same divergence this whole module exists to
catch, arriving from the one direction the writers can't see.

**It grew as a command rather than shipping as a one-off `rm`** during the `~/AGENTS.md` retirement,
for the reason the repo exists: a manual deletion is a change nobody can re-run. It reuses the
manifest instead of adding configuration — an orphan is a recorded path `setup.toml` no longer
declares, and it is only deleted while it still matches the digest recorded when PULSE wrote it,
which is the same rule `deploy()` follows before overwriting. So the command removes its own output
and nothing else, and the rest is reported and kept.

### Retiring a destination can retire a config feature, and half of that is worse than neither

`~/AGENTS.md` was the only `always = true` destination on the machine. The flag was carried end to
end — a field on `MirrorDest`, a branch in the table-vs-string parser, two conditionals deciding
whether a missing parent directory means "create it" or "that agent isn't installed" — and with the
declaration gone, every one of those was dead code along with the tests pinning it.

**Removing the entry and keeping the mechanism is strictly worse than either whole option**: a
documented config field that no declaration uses reads as supported, so the next person to want that
behaviour finds a feature that has never been exercised. Check whether a destination you are
retiring is the last user of anything before deciding the change is a one-line delete.

### What a dry run caught, and what only a person could

Three near-misses, and the order is the useful part — the first two were mechanical and the third
was not.

- **The manifest holds directories, not only files.** `~/.agents/skills/<name>` entries were written
  by the skill copier this module deleted on 2026-09-07 and have been undeclared ever since, so
  every one of them reached prune. Crashing on `read_bytes()` was the _good_ outcome: the `skills`
  CLI owns those directories now, and a version that had handled directories gracefully would have
  deleted live installed skills.
- **Ownership cannot be decided from the registry alone.** `lookup()` answers False for
  `~/.claude/CLAUDE.md` even while `setup.toml` declares it, because a mirror is neither a `dest`
  nor a `dst` — so `declared_paths()` has to union the registry with the mirrors or every agent's
  instruction file is an orphan.
- **The third source has no declaration to union with, and that one shipped.** A run-time
  destination — the PyCharm options directory found by glob, the corporate-only proxy unit — is
  deliberately absent from `setup.toml`, because a declared destination is one `inv verify.all`
  demands exist. `prune` was written without it and reported
  `~/.config/JetBrains/…/options/editor-font.xml` as abandoned while `inv ide.configure-pycharm` was
  maintaining it; on a machine with the proxy configured it would have offered to delete
  `pulse-proxy.service`. The list now lives in `home.runtime_managed()` and both callers read it —
  it had already been a literal inside `home.py`'s claim enumeration, and prune was written without
  noticing, which is the second-place-to-forget this module keeps arguing against.

[PITFALL: **that third one was invisible to every check that ran.** The gate was green, the dry run
looked plausible, and the report was wrong in a way only someone who knew what the repo was _for_
could see — the user asked why a font this setup deliberately configures was being called abandoned.
Nothing in the test suite was positioned to ask that question, and nothing added since is either;
what closed it was reading the report against the repo's purpose rather than against its fixtures.]

## Deliberately not built

- Auto-porting a deployed edit back into the repo source. PULSE reports and asks; the human decides
  and commits.
- Telling the agent at _edit time_ that it dirtied a deployed file — only whoever next runs a PULSE
  task learns. Accepted: the actual harm was silent loss, which is closed; "port it back to the
  repo" is ergonomics, and `~/.agents/AGENTS.md`'s own header already says it. Revisit a real-time
  hook only if drift keeps happening after this, with evidence rather than on prediction.
