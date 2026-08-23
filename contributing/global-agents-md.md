# config/global-AGENTS.md — rationale and evidence

Companion to [`config/global-AGENTS.md`](../config/global-AGENTS.md), the source of `~/AGENTS.md`
(and its `~/.claude/CLAUDE.md` symlink) on this machine — `[packages.claude-global-md]` in
`setup.toml`, redeployed by `inv tools.install`. The deployed file is never edited directly.

That file is loaded whole into every session in every repo, so each rule there holds only what earns
always-loaded space: trigger + rule + one clause of why. Everything else about a rule — dated
confirmations, reproductions, rejected alternatives, the story of how it was learned — lives here,
under a heading matching the rule's own, so rule and evidence stay findable from each other by name.
This file is deliberately exactly one reference hop from `~/AGENTS.md`; don't chain it onward to a
third file (per Anthropic's skill-authoring guidance, files reached through nested references get
partially read).

Design and research behind the split (including the external evidence that oversized instruction
files degrade adherence to _everything_ in them, and that inline narrative next to rules costs
adherence independent of token count): `plans/2026-08-23-global-agents-md-leanness-pass.md`.

## Admitting a new rule

A new rule enters `config/global-AGENTS.md` only if it:

1. **States its trigger** — the situation that fires it, named in its heading. A heading is a
   retrieval cue, not navigation; "Project conventions" is a topic, "sudo" is a trigger.
2. **Doesn't duplicate an existing rule** — a variant extends the existing rule's section rather
   than adding a new one. Overlapping near-duplicate rules are a measured driver of degraded
   adherence, not just clutter.
3. **Puts its evidence here, not inline** — dated confirmations and reproductions go in this file
   under a matching heading.

There is no word budget or mechanical gate; the external reference points for review are ≤200 lines
and ≤15 rules. Tier placement: a rule whose miss is silent and expensive stays in `~/AGENTS.md`
regardless of size pressure; a rule with a sharp, statable trigger whose miss is cheap and
recoverable may live in a skill instead — but moving an existing rule out of the always-loaded set
needs the same per-rule user approval as deleting it. Nothing in the file is deleted without asking.

The intake side of this — deciding whether a candidate is durable at all and which home (repo
`AGENTS.md`, skill, plan, this file) it belongs to — is
`plans/2026-08-22-memory-to-agents-md-migration-sweep.md`'s taxonomy; these criteria are the
admission gate for the candidates that taxonomy routes here.

## Contents

- [Auto mode blocks self-editing `~/.claude/settings.json` via Bash](#auto-mode-blocks-self-editing-claudesettingsjson-via-bash)
- [Testing a different repo's code in a multi-working-directory session](#testing-a-different-repos-code-in-a-multi-working-directory-session)
- [Reuse maintained upstream work](#reuse-maintained-upstream-work)
- [Tool-native over hand-rolled](#tool-native-over-hand-rolled)
- [Best tool per concern](#best-tool-per-concern)
- [Deep research for real tool/library choices](#deep-research-for-real-toollibrary-choices)
- [Research before asking](#research-before-asking)
- [Pilot before generalizing](#pilot-before-generalizing)
- [Naming collisions](#naming-collisions)
- [Verify what actually happened](#verify-what-actually-happened)
- [This machine's locale breaks `date`/`awk` formatting](#this-machines-locale-breaks-dateawk-formatting)
- [Committing multi-part work](#committing-multi-part-work)
- [Check for direnv before prefixing `uv run`](#check-for-direnv-before-prefixing-uv-run)
- [Two `uv` traps](#two-uv-traps)
- [Flag apparent typos and mental slips](#flag-apparent-typos-and-mental-slips)

## Auto mode blocks self-editing `~/.claude/settings.json` via Bash

Confirmed directly 2026-08-23: a `python3 -c "..."` one-liner making a temporary, explicitly
user-approved edit to `~/.claude/settings.json` was denied outright by auto mode's background
classifier both before and after the user said "I will approve it" — auto mode has no per-call
interactive step for that approval to land on. The Edit tool, which goes through a separate
permission path, was not blocked for the identical change.

## Testing a different repo's code in a multi-working-directory session

Confirmed directly 2026-08-22/23: running plain `inv`/`pytest` after `cd`-ing into a secondary repo
silently exercised the primary repo's pinned dependency copy of a package under active development
in the secondary repo — direnv's shell hook fires on an interactive shell's prompt/precmd, not
inside a non-interactive `bash -c` invocation, so PATH stayed the primary project's direnv-activated
`.venv/bin`.

Confirmed again 2026-08-23, one layer deeper: even invoking `/path/to/other-repo/.venv/bin/inv` by
absolute path, without changing cwd, still silently ran the **primary** repo's own tasks — invoke
discovers `tasks.py`/`tasks/` by walking up from the current working directory, independent of which
venv's `inv` binary executes. The `pytest` fix (absolute-path binary is enough, because
site-packages resolution depends on the interpreter, not cwd) and the `inv` fix (an actual `cd` is
required) are not the same fix.

## Reuse maintained upstream work

Validated concretely, not just asserted: designing `.gitignore` ownership for a shared dev-tooling
package (`power-user-linux-setup`'s `repo-tasks`/`scaffoldapy`), a prior-art check before drafting a
Python `.gitignore` in-house found that PyCharm's own bundled `.ignore` plugin
(`JetBrains/idea-gitignore`) doesn't maintain its own list either — it generates from
`github/gitignore`, GitHub's officially-maintained template repo. A mainstream, widely-used tool had
already made the identical "don't roll your own" call.

Caught live designing `session-harvest`: an initial internal search (`skills find`/repo grep)
surfaced one loosely-related hit and looked conclusive enough to justify building from scratch — a
real web search then turned up a much closer match (`melodykoh/learning-loop-skill`) that
meaningfully changed the design. A single narrow tool's "nothing relevant" is a weak signal, not a
conclusion.

## Tool-native over hand-rolled

The defining instance: choosing `uv python install --default` (which creates an unversioned
`python3` shim shadowing apt's `/usr/bin/python3` on `PATH`) over a hand-rolled `python`-only
symlink that would have preserved a "system `python3` never shadowed" invariant byte-for-byte. The
tool-managed option won after the shadowing risk was verified theoretical — every
`#!/usr/bin/env python3` script on the system was grepped, none needed distro-specific bindings —
citing rule of least surprise, and that the tool's own shim is understood by
`uv python uninstall`/`--reinstall`/upgrades while a raw `ln -sf` is one more thing to
hand-maintain.

## Best tool per concern

The concrete instance of the exception: a data-modeling decision table trimmed from six routine
choices (Pydantic/dataclass/attrs/NamedTuple/TypedDict/msgspec) to two (Pydantic for boundaries,
frozen dataclass for everything else). "Best tool per concern" argued for more specialized tools;
"fewer options for an agent to mimic incorrectly" argued for fewer routine defaults — the second won
because the stated audience was agent-authored code specifically.

## Deep research for real tool/library choices

Observed as a real pattern, not a one-off: the user pushed for more depth twice in one planning
session on a monorepo-versioning tool choice, both times because a search-summary-level survey
wasn't considered sufficient to close out the decision.

## Research before asking

Confirmed directly 2026-08-23: asked the user to pick a color tier for a newly-released Claude model
("Fable") in a statusline script, framing it as a stylistic choice. The user's reply — "look it up
online, come on" — was a real correction: Fable's actual capability tier (above Opus, per
Anthropic's own docs) was one search away, not something only the user could supply. Re-ran the
research, found the answer, applied it without another round-trip.

## Pilot before generalizing

Piloting researched typing/lint/format tool choices on one real repo before writing them into a
skill surfaced real mistakes pure research couldn't have caught: a lint rule that was pure noise
against that repo's actual deliberate style, a rule that didn't fit the repo's shape at all, and two
config-file footguns that would have silently misconfigured every repo copying the config verbatim.
A skill built straight from research, with no pilot step, would have shipped all of these to every
consumer.

## Naming collisions

The originating incident: "pulse-setup" was proposed to disambiguate a `~/.config/pulse` clash with
PulseAudio; the full canonical name "power-user-linux-setup" was the right answer — a short alias
that half-repeats the disambiguating word reads as awkward rather than clean.

## Verify what actually happened

Exit codes: `basedpyright` hard-errors (exit 3) on a config error while still printing a clean
`"0 errors, N warnings, 0 notes"` summary line — a real regression across three repos went unnoticed
for a stretch of a session because every check was read via `... | tail -N`, and `tail`/`grep` in a
pipeline return their own exit code, not the upstream command's.

Sampling: confirmed live 2026-08-23 — nine modified `cli-allowlist` files were reported as
"timestamp-only churn" after reading one of them (`vim.json`) in full; five carried real upstream
version bumps (`dprint` 0.54.0 → 0.56.1, `twine` 6.2.0 → 7.0.0, and three more), and `--stat` had
already shown 27 changed lines against `vim.json`'s 6. Harmless that time only because the
conclusion was "leave it alone" — the identical reasoning behind a discard would have thrown away
real data.

## This machine's locale breaks `date`/`awk` formatting

Confirmed concretely 2026-08-23, twice in one script (`~/.claude/statusline-command.sh`):
`date -d ... '+%a'` returned `"Ma"` (Marți, Tuesday) instead of `"Tue"`, and
`awk '{printf "%.2f", c}'` rendered `1,23` instead of `1.23` — `LC_TIME`/`LC_NUMERIC` default to
`ro_RO.UTF-8` while `LANG`/`LC_MESSAGES` stay `en_US.UTF-8`. Both were caught only by piping real
output through `xxd`/`cat -A` and reading the literal bytes; a rendered terminal glyph or a quick
"does this look like a number" glance would have caught neither.

## Committing multi-part work

Reaffirmed 2026-08-23 in `scaffoldapy` ("we should use granular commits, that should be a general
rule") after a "want this split into three commits?" question — the second time the rule needed
restating, which is the signal it was being treated as a per-task preference rather than a standing
one. The conflation to avoid: needing permission to commit at all (the harness's own default) is
separate from how to split once committing is authorized.

## Check for direnv before prefixing `uv run`

Confirmed live 2026-08-23 in `repo-tasks`: used `.venv/bin/python -m pytest tests/integration/` out
of habit while direnv was already active and plain `pytest tests/integration/` would have resolved
to the identical binary; corrected mid-session. The absolute path added nothing except a novel
command string that breaks Bash-allowlist prefix matching.

## Two `uv` traps

Both confirmed live 2026-08-23 while building `repo-tasks`' shared-tool-list mechanism. For the
`--with-executables-from` trap specifically: verify against the real target package, not a sandboxed
fixture — a fixture package having its own console script (even accidentally) hides the failure.

## Flag apparent typos and mental slips

Concrete instance: a name used consistently across two messages while designing a naming convention
was read as deliberate and written into a plan doc as a genuine undecided design fork — it was
actually a slip, and the user had to correct it explicitly: "remember to push back on typos and
apparent mental slips. people, unlike machines, get tired and their brains connect the wrong things
despite good intentions." Repetition across messages is not proof of intent — repetition is exactly
what a tired mental slip looks like too.
