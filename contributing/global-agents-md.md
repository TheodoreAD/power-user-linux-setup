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

Design and research behind the split: the "Why the deployed file is shaped this way" section below
(extracted from the now-retired `plans/2026-08-23-global-agents-md-leanness-pass.md`).

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

## Why the deployed file is shaped this way

Researched 2026-08-23 for the leanness pass that restructured the file from 30 flat sections / 6,053
body words to 6 trigger-clustered sections of trigger-named rules. The findings that drove each
structural choice:

- **Size.** [Anthropic's CLAUDE.md guidance](https://claude.com/blog/using-claude-md-files) says
  concise and human-readable; secondary write-ups of Anthropic engineers' practice put the working
  limit near **200 lines / 15 rules**
  ([XDA](https://www.xda-developers.com/your-claude-md-is-probably-wrong-how-anthropics-engineers-structure/),
  [betterclaw](https://www.betterclaw.io/blog/agents-md-best-practices)). The load-bearing finding:
  **bloated instruction files cause models to ignore instructions wholesale**, not selectively
  filter the irrelevant ones ([morphllm](https://www.morphllm.com/agents-md-guide)); and
  [Anthropic's context-engineering post](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  — recall degrades as context grows, so aim for the minimal set that fully outlines expected
  behavior ("minimal does not necessarily mean short"). Those numbers are review reference points,
  not a gate — the discipline lives upstream, in the admission criteria above.
- **Clustering.** Clear markdown section boundaries measurably improve adherence and prevent
  "instruction bleed" between rules sharing vocabulary. Position is **not** a lever: the
  instruction-following literature found no consistent relationship between position and follow rate
  ([arXiv 2511.13900](https://arxiv.org/pdf/2511.13900),
  [arXiv 2510.10276](https://arxiv.org/html/2510.10276v1)) — don't reorder for primacy/recency.
- **Merging near-duplicates.** Conflict between overlapping instructions is a primary driver of
  degradation as instruction count grows ([arXiv 2510.14842](https://arxiv.org/abs/2510.14842),
  SCALEDIF) — real but modest (~4–7pp), so dedup/merge is the change most likely to improve
  adherence, worth doing without overselling.
- **Evidence out of the deployed file.** Instructions compete for attention with inline narrative
  ([arXiv 2601.03269](https://arxiv.org/html/2601.03269v1)) — relocating provenance here buys
  adherence independent of the token saving. This file exists because of that finding.
- **What transfers from
  [skill authoring](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices):**
  progressive disclosure (the deployed file is the overview, this file the on-demand detail);
  references one level deep (why this file must not chain onward — nested references get partially
  read); a TOC for reference files over 100 lines; consistent terminology; no time-sensitive info
  inline; concrete examples over abstract prose; degrees of freedom matched to fragility (`sudo -A`
  is low-freedom/exact, design rules are high-freedom/heuristic); and when a rule is observed being
  missed, **strengthen its language rather than lengthen its explanation**.
- **Three tiers.** Tier 1, `~/AGENTS.md`: rules that can fire on any turn or whose miss is silent
  and expensive — paid every session. Tier 2, a skill: sharp statable trigger, cheap recoverable
  miss — kept small because skill descriptions under-trigger
  (`plans/2026-08-22-skill-trigger-quality-review.md`). Tier 3, this file: free until read.

## Re-measuring the deployed file

The two commands behind every measurement in the leanness pass, so a later review compares like with
like. Landed shape 2026-08-23: ~2,500 body words, 6 clusters, 30 rules, 294 lines, provenance share
0%.

```shell
# per-section word count, largest first
python3 -c "
import re
from pathlib import Path
secs = re.split(r'^## ', Path('config/global-AGENTS.md').read_text(), flags=re.M)[1:]
rows = [(len(s.split(chr(10), 1)[1].split()), s.split(chr(10), 1)[0]) for s in secs]
for w, h in sorted(rows, reverse=True): print(f'{w:5d}  {h[:70]}')
print(f'--- {sum(w for w, _ in rows)} words in {len(rows)} sections')
"

# share of words in provenance-bearing sentences (sentence-granularity: treat as a floor)
python3 -c "
import re
from pathlib import Path
body = re.sub(r'\`\`\`.*?\`\`\`', '', Path('config/global-AGENTS.md').read_text(), flags=re.S)
sents = re.split(r'(?<=[.!?])\s+', body.replace(chr(10), ' '))
prov = re.compile(r'2026-\d\d-\d\d|Confirmed|Reaffirmed|Validated|Observed as a real|Caught live|Concrete instance|Example:')
tw = sum(len(s.split()) for s in sents)
pw = sum(len(s.split()) for s in sents if prov.search(s))
print(f'{pw} of {tw} words ({pw*100//tw}%) in provenance sentences')
"
```

## Contents

- [Composing a Bash call](#composing-a-bash-call)
- [Running a command against a different repo than the session's project](#running-a-command-against-a-different-repo-than-the-sessions-project)
- [Editing `~/.claude/settings.json` (or similar) in auto mode](#editing-claudesettingsjson-or-similar-in-auto-mode)
- [Saving to cross-session memory](#saving-to-cross-session-memory)
- [Designing a uv tool-install or shared-dependency mechanism](#designing-a-uv-tool-install-or-shared-dependency-mechanism)
- [About to author content, config, or a workaround from scratch](#about-to-author-content-config-or-a-workaround-from-scratch)
- [Choosing a tool or library](#choosing-a-tool-or-library)
- [About to ask the user something factual](#about-to-ask-the-user-something-factual)
- [Writing conventions into a shareable skill or template](#writing-conventions-into-a-shareable-skill-or-template)
- [Adding a CLI flag](#adding-a-cli-flag)
- [Proposing an enforcement mechanism for agent behavior](#proposing-an-enforcement-mechanism-for-agent-behavior)
- [Naming around a collision](#naming-around-a-collision)
- [Reading a command's result](#reading-a-commands-result)
- [Generalizing from a sample to a set](#generalizing-from-a-sample-to-a-set)
- [Formatting a date or decimal in a shell script](#formatting-a-date-or-decimal-in-a-shell-script)
- [Committing multi-part work](#committing-multi-part-work)
- [Invoking a venv tool in the session's own project](#invoking-a-venv-tool-in-the-sessions-own-project)
- [Something the user wrote looks like a typo or mental slip](#something-the-user-wrote-looks-like-a-typo-or-mental-slip)

## Editing `~/.claude/settings.json` (or similar) in auto mode

Confirmed directly 2026-08-23: a `python3 -c "..."` one-liner making a temporary, explicitly
user-approved edit to `~/.claude/settings.json` was denied outright by auto mode's background
classifier both before and after the user said "I will approve it" — auto mode has no per-call
interactive step for that approval to land on. The Edit tool, which goes through a separate
permission path, was not blocked for the identical change.

## Saving to cross-session memory

Confirmed 2026-08-22: auto-memory is a separate `memory/` folder per project directory —
`repo-tasks`, `power-user-linux-setup`, `scaffoldapy`, and the `*-polite-mcp` repos each had their
own, none shared — so even a general cross-repo preference saved there is invisible everywhere else.
The same session found ~30 accumulated entries, several duplicating `~/AGENTS.md` or existing skills
verbatim; the full migration story is `plans/2026-08-22-memory-to-agents-md-migration-sweep.md`. The
underlying reason `AGENTS.md` beats memory (reviewable, one source of truth instead of N per-project
copies) applies across repos exactly as it does within one.

## Composing a Bash call

The rule's earlier form claimed a chained command can never match an allow rule
("`cd some/dir &&
git status` no longer starts with `git status`, so it can't match
`Bash(git status:*)`") and banned `&&` outright. Corrected 2026-08-23 on two independent sources: a
live test (`cd /tmp && git
status` and `cd /tmp && cat /etc/hostname`, neither prompted) and
`code.claude.com/docs/en/permissions.md`'s "Compound commands" section, read in full twice in
separate sessions — Claude Code splits on `&&`, `||`, `;`, `|`, `|&`, `&`, and newlines, and
evaluates each subcommand against the rules independently (newline being a recognized separator also
means `\` line continuations have zero effect on matching). The `bash -c` claim survives because the
outer `bash` is itself classified dangerous (`cli-allowlist/rules/bash.json`) and renders as `ask`.

Held conservative rather than loosened further:
`plans/2026-08-22-compound-command-permission-audit.md` still carries an unexplained report of a
write-classified command executing without a prompt inside a compound command — until that
incident's mechanism is understood, the guidance stays "prefer simple separate calls" even though
the documented per-subcommand model would permit more chaining.

The "friction cost, never a prohibition" clause exists because the old ban was obeyed literally: an
agent in a `repo-tasks` session concluded legitimate cross-repo work was impossible (the fix needed
one chained command, chaining was "banned") and reported it as a limitation instead of paying one
approval prompt — abandoning real work to dodge friction, strictly worse than any number of prompts
(`plans/2026-08-23-cross-directory-command-execution.md`, retired).

## Running a command against a different repo than the session's project

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

The rule's earlier form prescribed the opposite of what now stands: it discouraged directory-scoping
flags and prescribed "run `cd` as its own call, then the command, then `cd` back" — which cannot
work, because the harness resets cwd to the session's primary directory after every Bash call.
Observed twice 2026-08-23: a standalone `cd` into another directory returned "Shell cwd was reset",
and a chained `cd <repo> && .venv/bin/inv …` printed the same reset line after the command ran (i.e.
the chain worked precisely because the `cd` and the command shared one call). Whether the reset is
universal or specific to this harness version/configuration is unpinned; the current guidance holds
either way, which is why it no longer depends on cwd persistence.

Scoping flags were validated live the same day, all against this repo from a `repo-tasks` session
with no `cd`: `git -C <path> status`/`log`/`add`/`commit` (full commit workflow),
`dprint fmt --config <path>`, `ruff check --config <path>`, `ruff format --config <path>`,
`basedpyright --project <path>` (exit 0), and `<venv>/bin/pytest <abs path>` over a 215-test suite.

Corrected 2026-08-24, a third layer: `cd <repo> && <repo>/.venv/bin/inv <task>` — the form this rule
previously called "the only working form" — still ran the wrong tools. Invoke's tasks are thin
wrappers around `c.run("pytest …")`, `c.run("ruff check .")`, `c.run("basedpyright")`; `c.run`
inherits the caller's environment, so every bare tool name resolved through the **primary** repo's
direnv-activated `.venv/bin`. The result was a phantom test failure that cost real time before the
mismatch was spotted: the target repo's task list running the session repo's `pytest`, its
dependencies, and its plugins. Prefixing PATH is the fix that reaches the subprocesses; pointing at
the `inv` binary never could, because the binary's location says nothing about what its children
resolve. Note this is the case the "Composing a Bash call" rule means by "unless the step genuinely
needs them" — the leading env assignment is load-bearing here, and the approval prompt is the price.

Not every repo has `inv` in its own venv (`scaffoldapy` did not, 2026-08-24), which is why the
`~/.local/bin` fallback clause survives the rewrite rather than being replaced by the PATH prefix.

The "bare `inv` may be either uv tool" clause: `repo-tasks` and standalone `invoke` both provide
`inv`/`invoke` console scripts, and whichever was `--force`-installed last owns the `~/.local/bin`
symlinks (`plans/2026-08-23-invoke-repo-tasks-tool-conflict.md`). The two `inv` failure modes
compose: cwd decides which `tasks.py` is found; the binary decides whether that `tasks.py` can
import `repo_tasks`. Both misses are silent, and `<repo>/.venv/bin/inv` addresses the second for
free.

## About to author content, config, or a workaround from scratch

Reuse-upstream, validated concretely: designing `.gitignore` ownership for a shared dev-tooling
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

Tool-native over hand-rolled, the defining instance: choosing `uv python install --default` (which
creates an unversioned `python3` shim shadowing apt's `/usr/bin/python3` on `PATH`) over a
hand-rolled `python`-only symlink that would have preserved a "system `python3` never shadowed"
invariant byte-for-byte. The tool-managed option won after the shadowing risk was verified
theoretical — every `#!/usr/bin/env python3` script on the system was grepped, none needed
distro-specific bindings — citing rule of least surprise, and that the tool's own shim is understood
by `uv python uninstall`/`--reinstall`/upgrades while a raw `ln -sf` is one more thing to
hand-maintain.

## Choosing a tool or library

Research depth, observed as a real pattern rather than a one-off: the user pushed for more depth
twice in one planning session on a monorepo-versioning tool choice, both times because a
search-summary-level survey wasn't considered sufficient to close out the decision.

The agent-audience exception's concrete instance: a data-modeling decision table trimmed from six
routine choices (Pydantic/dataclass/attrs/NamedTuple/TypedDict/msgspec) to two (Pydantic for
boundaries, frozen dataclass for everything else). "Best tool per concern" argued for more
specialized tools; "fewer options for an agent to mimic incorrectly" argued for fewer routine
defaults — the second won because the stated audience was agent-authored code specifically.

## About to ask the user something factual

Confirmed directly 2026-08-23: asked the user to pick a color tier for a newly-released Claude model
("Fable") in a statusline script, framing it as a stylistic choice. The user's reply — "look it up
online, come on" — was a real correction: Fable's actual capability tier (above Opus, per
Anthropic's own docs) was one search away, not something only the user could supply. Re-ran the
research, found the answer, applied it without another round-trip.

## Writing conventions into a shareable skill or template

Piloting researched typing/lint/format tool choices on one real repo before writing them into a
skill surfaced real mistakes pure research couldn't have caught: a lint rule that was pure noise
against that repo's actual deliberate style, a rule that didn't fit the repo's shape at all, and two
config-file footguns that would have silently misconfigured every repo copying the config verbatim.
A skill built straight from research, with no pilot step, would have shipped all of these to every
consumer.

## Adding a CLI flag

The bypass-flag clause's originating incident (2026-08-23): a `--force` on `inv ai.install-skills`
that would have overwritten foreign content was rejected because the `.pulse-source` marker _is_ the
ownership model — a flag overriding it would make ownership mean one thing with the flag and another
without. Stated by the user as "we shouldn't have hacks that make the mental model difficult, unless
something is utterly impractical." Folded into this rule (which previously covered only flag
_shape_) during the leanness pass, as the second §11 candidate admission.

## Proposing an enforcement mechanism for agent behavior

Originating decision (2026-08-23): researched git-hook enforcement of the quality gate was rejected
in favor of skill-level guidance — the user: "i've always been against companies imposing git
precommit hooks for devs. i see no reason to treat a dev differently from an agent." Recorded in
`plans/2026-08-23-git-hooks-for-quality-gate.md`'s decision context; routed here by
`session-harvest` the same day as the leanness pass's third candidate admission, because the
principle is broader than that one plan and outlives its retirement.

## Naming around a collision

The originating incident: "pulse-setup" was proposed to disambiguate a `~/.config/pulse` clash with
PulseAudio; the full canonical name "power-user-linux-setup" was the right answer — a short alias
that half-repeats the disambiguating word reads as awkward rather than clean.

## Reading a command's result

`basedpyright` hard-errors (exit 3) on a config error while still printing a clean
`"0 errors, N warnings, 0 notes"` summary line — a real regression across three repos went unnoticed
for a stretch of a session because every check was read via `... | tail -N`, and `tail`/`grep` in a
pipeline return their own exit code, not the upstream command's.

## Generalizing from a sample to a set

Confirmed live 2026-08-23 — nine modified `cli-allowlist` files were reported as "timestamp-only
churn" after reading one of them (`vim.json`) in full; five carried real upstream version bumps
(`dprint` 0.54.0 → 0.56.1, `twine` 6.2.0 → 7.0.0, and three more), and `--stat` had already shown 27
changed lines against `vim.json`'s 6. Harmless that time only because the conclusion was "leave it
alone" — the identical reasoning behind a discard would have thrown away real data.

Extended 2026-08-24 (`repo-tasks`): the same failure with a self-inflicted sample. A
`rg ... | head -20` run to find every reference to a directory being moved was treated as the
complete list; a file it cut off kept a stale path and failed a test one step later. Repeated in the
same session — the truncation, not the reading, was the constant.

## Verifying behavior in a repo with test coverage

Confirmed 2026-08-24 (`repo-tasks`): three commits were checked out in a worktree and their tests
run, to verify each stood alone. Every run tested the _working tree_ instead — the venv's editable
install resolves the package there, not to the checkout — producing one false pass and one false
fail before the contradiction was noticed. `PYTHONPATH=<worktree>/src` fixed it. A passing suite had
felt like proof; it was proof about the wrong code.

## Formatting a date or decimal in a shell script

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

## Invoking a venv tool in the session's own project

Confirmed live 2026-08-23 in `repo-tasks`: used `.venv/bin/python -m pytest tests/integration/` out
of habit while direnv was already active and plain `pytest tests/integration/` would have resolved
to the identical binary; corrected mid-session. The absolute path added nothing except a novel
command string that breaks Bash-allowlist prefix matching.

## Designing a uv tool-install or shared-dependency mechanism

Both traps confirmed live 2026-08-23 while building `repo-tasks`' shared-tool-list mechanism. The
`--with-executables-from` failure presents as "No executables are provided by package `X`; removing
tool" — and must be verified against the real target package, not a sandboxed fixture: a fixture
package having its own console script (even accidentally) hides it. The dependency-groups trap's
consequence spelled out: bumping the shared package's own dev/quality group changes nothing for any
project that merely depends on it, because PEP 735 groups aren't pulled in transitively the way
`[project.dependencies]`/extras are.

## Something the user wrote looks like a typo or mental slip

Concrete instance: a name used consistently across two messages while designing a naming convention
was read as deliberate and written into a plan doc as a genuine undecided design fork — it was
actually a slip, and the user had to correct it explicitly: "remember to push back on typos and
apparent mental slips. people, unlike machines, get tired and their brains connect the wrong things
despite good intentions." Repetition across messages is not proof of intent — repetition is exactly
what a tired mental slip looks like too.
