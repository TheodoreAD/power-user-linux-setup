---
status: blocked on plans/2026-08-23-global-agents-md-leanness-pass.md landing
updated: 2026-08-23
---

## Context

`config/global-AGENTS.md`'s guidance on running a command against a directory other than the
session's own is wrong in a way that made an agent decline real work rather than do it. Observed
live 2026-08-23, in a `repo-tasks` session that legitimately needed to edit and test this repo (the
`plan-docs` skill is authored here).

Deliberately **not** fixed on the spot. `plans/2026-08-23-global-agents-md-leanness-pass.md` §6 is
already going to rewrite exactly these paragraphs ("Collapse the five allowlist paragraphs …`cd`,
scoping flags, chaining, `bash -c`, and parallel-means-separate-calls become one line each"), and
"Bash tool discipline" is its single largest section at 878 words. Correcting the text now would
create a merge conflict with that pass and risk the corrections being re-collapsed away; landing a
one-line-per-topic rewrite of claims that are themselves false would bake the errors in more
compactly. So this waits, and the leanness plan carries a pointer back here.

### What the file currently claims, and what actually happens

[PITFALL: **cwd does not persist between Bash tool calls.** `config/global-AGENTS.md:50` states "The
working directory persists between Bash tool calls (only shell state resets)". In this harness it
does not — the tool resets cwd to the session's primary working directory after every call. Observed
twice: a standalone `cd /home/tdumitrescu/.agents/skills` returned
`Shell cwd was reset to …/repo-tasks`, and a later chained `cd <repo> && .venv/bin/inv …` printed
the same reset line after the command ran.]

That single false premise invalidates the remedy built on it. `config/global-AGENTS.md:65-68`
prescribes: run the `cd` as its own Bash call, "never chained with `&&`", then the target command as
a separate call, then `cd` back. Step two lands back in the original directory, so **the prescribed
procedure cannot work at all** — it is not merely more awkward than chaining.

The stated reason for banning `&&` is allowlist prefix matching, i.e. an approval prompt. That is a
friction cost, not a correctness or safety one — but the text reads as a prohibition, and was
followed as one: the agent concluded the work could not be done and reported it as a limitation,
when a single chained command (costing one prompt) would have completed it. That is the actual harm
here, and it is worse than any number of prompts.

Two further claims in the same passage are already contradicted elsewhere and should be resolved
together rather than piecemeal:

- `config/global-AGENTS.md:48-49` — "A `cd some/dir && git status` no longer starts with
  `git status`, so it can't match `Bash(git status:*)`."
  `plans/2026-08-22-compound-command-permission-audit.md` found this contradicted twice: by a live
  test (`cd /tmp && git status`, no prompt) and by `code.claude.com/docs/en/permissions.md`'s
  "Compound commands" section, which states each subcommand is evaluated independently. That plan
  deliberately holds off on editing `~/AGENTS.md` pending forensics on a separate reported incident
  — see Open questions for how the two interact.
- `config/global-AGENTS.md:53-63` — "Don't reach for a directory-scoping flag … as a reflexive
  substitute either." In practice the scoping flags were the thing that worked.

### Scoping flags: what was actually exercised

Every one of these ran against this repo from a `repo-tasks` session with no `cd` at all, and all
succeeded:

| invocation                                        | used for                         |
| ------------------------------------------------- | -------------------------------- |
| `git -C <path> status` / `log` / `add` / `commit` | full commit workflow, repeatedly |
| `dprint fmt --config <path> <files>`              | markdown formatting              |
| `ruff check --config <path> <files>`              | lint                             |
| `ruff format --config <path> <files>`             | format                           |
| `basedpyright --project <path>`                   | type check, exit 0               |
| `<venv>/bin/pytest <abs test path>`               | 215 tests                        |

[DECISION: prefer a directory-scoping flag over any form of `cd` when targeting another directory.
It leaves no cwd state behind, works regardless of whether cwd persists, and — per the sibling
audit's finding that subcommands are matched independently — the allowlist objection the current
text raises against it is questionable anyway. This inverts the current guidance, which discourages
scoping flags and prescribes `cd` instead.]

[PITFALL: `inv` (invoke) is the one real exception found, and it is not a matter of preference —
invoke discovers `tasks.py` by walking up from **cwd**, independent of which venv's `inv` binary
executes, so no flag can redirect it. `cd <repo> && <repo>/.venv/bin/inv <task>` chained in one call
is the only form that works: the `cd` supplies task discovery, the absolute venv path supplies the
dependencies. `pytest` is explicitly _not_ in this category — an absolute path to the target repo's
own `pytest` resolves site-packages correctly with no `cd`, which this session confirmed against a
215-test suite. The existing text already draws this pytest/invoke distinction correctly and it must
survive the rewrite.]

## Open questions

[NEEDS CLARIFICATION: is the cwd reset universal, or specific to something about this setup — a
Claude Code version, a setting, a sandbox/permission mode, the fact that the session had additional
working directories configured? The current text was presumably accurate when written, which
suggests behavior changed rather than the author being wrong. Worth pinning down before writing "cwd
does not persist" as a flat fact, since a version-dependent claim needs different phrasing (and
belongs in tier 3 per the leanness plan's tier model, not as an always-loaded rule).]

[NEEDS CLARIFICATION: do subagents see the same reset? The leanness plan §5 is already promoting
"`Plan`/`Explore` subagents don't load this file" to a preamble, so a subagent's cwd behavior is
worth knowing for the same reason — a rule that only holds for the main session should say so.]

[NEEDS CLARIFICATION: how does this interact with
`plans/2026-08-22-compound-command-permission-audit.md`'s hold on editing the compound-command text?
That plan won't correct line 48-49 until the reported silent-execution incident is understood. This
plan needs those same lines rewritten. Options: (a) this plan corrects only the cwd/scoping-flag
claims and leaves the prefix-matching sentence for that plan; (b) both fold into the leanness pass's
§6 rewrite, with the prefix-matching claim stated conservatively until forensics land; (c) that plan
resolves first. (a) looks cleanest — the cwd finding is independent of the incident — but the
paragraphs are adjacent enough that one rewrite touching both is likely in practice.]

[NEEDS CLARIFICATION: should any of this be a hard rule at all, versus a short decision table? The
leanness plan's tier model would put "prefer a scoping flag; invoke needs a chained `cd`" in tier 1
(cheap, fires often enough, silent-ish miss) and the reasoning/evidence in tier 3. But cross-repo
work is supposed to be rare — the file's own "Testing a different repo's code" section (556 words)
opens by saying it should be avoided entirely. A rare situation may not earn always-loaded space,
even when getting it wrong is expensive.]

## Recommended direction

Rough, and deliberately not designed until the leanness pass has settled the section boundaries.

Replace the three `cd`-related paragraphs with a short decision table rather than prose: scoping
flag if the tool has one (with the exercised list above as the concrete examples); chained
`cd path && <abs venv binary> <task>` for invoke specifically; and a plain statement that cwd does
not persist, so a standalone `cd` accomplishes nothing. Keep the pytest-vs-invoke distinction, which
is the one part of the current text that proved exactly right.

Frame the `&&` guidance as a cost, not a prohibition — "expect an approval prompt" rather than
"never" — since the observed failure was an agent treating a friction rule as a blocker and
abandoning the task. Per the leanness plan §2's "trigger + rule + one clause of why", the evidence
above belongs in `contributing/global-agents-md.md`, not inline.

Reassess whether the "Testing a different repo's code" section and this material should merge. They
answer the same question and currently disagree with each other; the leanness plan already groups
both into its "Bash / allowlist / tooling" cluster (1,738 words, the largest).
