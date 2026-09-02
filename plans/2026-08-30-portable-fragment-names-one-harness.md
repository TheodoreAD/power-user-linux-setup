---
status: landed
updated: 2026-09-02
---

# The fragment axis is wrong: PULSE vs machine, harness vs portable

Opened as "`portable.md` names one harness and one machine" — a leak-hunting plan against the
existing three fragments. The user's response on 2026-08-30 reframed it: the leaks are real but the
axis they leak across is the wrong one, so the plan is now about the axis. Filename kept, since
plan-docs promotes in place rather than forking a second file for one topic.

## Context

`config/agents-md/` deploys three fragments, in `order`: `this-setup.md` (10) "this machine, this
user's own repos, PULSE's own mechanisms", `claude-code.md` (20) "behavior specific to the Claude
Code harness", `portable.md` (30) "conventions that hold on any machine, with any agent".

Two findings, from opposite ends, say those descriptions do not carve the content:

- `portable.md` names Claude Code's tools and this machine's paths throughout (measured below).
- `this-setup.md` is mostly not about _this machine_ at all.

## The reframing (from the user, 2026-08-30)

Recorded close to verbatim, because it changes what every other decision in this plan is for.

[DECISION: **`this-setup.md`'s subject is PULSE, not one machine.** _"harness settings are not just
for this machine. they are for pulse as a holistic approach to development."_ Nothing in `AGENTS.md`
is meant to be personal to one box: _"i'm not planning to have anything machine-specific for myself
in terms of agents.md — everything i change in my workflows fundamental enough to require an
agents.md or skill rule will be integrated in pulse to happen by default as a prerequisite."_ So a
rule earns its place by being true of a PULSE-provisioned machine, and the fragment's name and
description should say that.]

[DECISION: **the Claude Code rules stay, and get labelled rather than generalised.** _"the Claude
rules are here to stay… what we may want to do is preface them with Claude Code so we know they are
specific, and revisit that when we try to onboard another harness."_ The anticipated future is
_adding_ a second harness's instructions, not Claude rules drifting between machines. This closes
the plan's original question — a Claude tool name is not a defect, and genericising it was the wrong
instinct. What is missing is only the label that makes the scope legible.]

[DECISION: **the setup is opinionated and will not be made generic.** _"this is an opinioniated
setup, after all, we can't make it extremely generic."_ So "does this hold for any agent on any
machine" is the wrong admission test for a fragment; "is this true of a PULSE machine, and is it
labelled with the harness it assumes" is the right one.]

[DECISION: **the disabled-prerequisite warning is `inv ai.check-rule-prerequisites`**, landed
2026-08-30. Asked for as _"on the off chance someone disables that, we might want a warning, e.g. if
someone disables direnv the Claude setup will suffer and it's a bad idea."_ It reads every
`[needs …]` label off the fragments and reports any rule whose package is undeclared, disabled, or
tag-excluded, exiting non-zero. Cheap only because the labels landed first — before them there was
nothing to read, which is why this was deferred rather than designed up front.]

[DECISION: **the deterministic half of the check runs in the quality gate; the rest stays
on-demand.** "Does `setup.toml` declare this package, and not as `enabled = false`" depends only on
committed content, so it is a unit test and CI catches it on the breaking commit. The
environment-dependent half — `overrides.toml`, `PULSE_EXCLUDE_TAGS` — stays in the task.
`verify.all` was rejected as the home: it aborts on first failure, and a container or WSL profile
excluding the `dev` tag makes `[needs direnv]` legitimately false, so gating there would break
`inv setup` on a correctly configured machine. The bar is "declared and enabled", not "declared" —
29 packages carry `enabled = false`, so declaration alone was barely a check.]

[DECISION: **the check is config-level, not presence-level.** It answers "is this still declared and
enabled", using the same precedence `inv setup` does (`setup.toml` → `overrides.toml` →
`PULSE_EXCLUDE_TAGS`). Whether the binary is physically on disk is `inv verify.all`'s job, and
keeping that out is what lets this task invoke nothing — which matters because the machine's
allowlist auto-approves `<ns>.check-*` on the strength of the naming convention alone, so a `check`
task that ran commands would run them unprompted.]

## `this-setup.md` is mostly PULSE (measured 2026-08-30)

Its 7 rules, against what `setup.toml` actually installs:

| rule                                          | PULSE installs the fact                                      |
| --------------------------------------------- | ------------------------------------------------------------ |
| `sudo`                                        | `[packages.askpass-zenity]` — the helper and the export both |
| git fetch/push needing an SSH key             | the `~/.zprofile` agent-picker block, and `SSH_ASKPASS`      |
| Installing a tool on this machine             | it _is_ `setup.toml`                                         |
| Invoking a venv tool in the session's project | `[packages.direnv]` plus the zsh hook                        |
| Installing agent instructions and skills      | `inv ai.install-skills`                                      |
| Formatting a date or decimal                  | **no** — a desktop regional setting                          |
| Pushing to a personal repo's default branch   | **no** — repo ownership                                      |

Five of seven are PULSE-provisioned, which is what makes the user's point about direnv general
rather than a one-off. The two that are not are also not alike: the locale one is an environment
fact PULSE does not create but already works around in its own code (`config/statusline-command.sh`
uses `LC_TIME=C`/`LC_NUMERIC=C` throughout, and `tasks/system.py` manages `LANG` but not `LC_TIME`),
while the branch-protection one is about which repos the user owns.

[PITFALL: **the earlier move in this plan landed the right rule in a wrongly-named fragment.**
"Invoking a venv tool in the session's own project" was moved out of `portable.md` because its
content is entirely about direnv — correct — into `this-setup.md`, described as "this machine". But
direnv is on the machine _because PULSE put it there_, so the rule was never machine-specific
either. The move stands; the destination's name is what is wrong, and the same is true of four of
its neighbours.]

## `portable.md` names Claude Code (measured 2026-08-30)

Across its 29 rules, seven name Claude Code tools as tools. Under the reframing these are no longer
defects to fix but rules to **label**:

| rule                                    | what it names                                      |
| --------------------------------------- | -------------------------------------------------- |
| Composing a Bash call                   | `Read` of a log, `Grep`/`Read` as a second call    |
| Viewing, searching, or editing files    | `Read`/`Grep`/`Glob`/`Edit`/`Write`, "the harness" |
| Reading a command's result              | "the Bash tool", `run_in_background`               |
| About to ask the user something factual | `AskUserQuestion`                                  |
| Ending a turn with a next step          | `AskUserQuestion`                                  |
| A narrow check grows into design work   | "plan mode"                                        |
| Committing multi-part work              | "the scratchpad"                                   |

They differ in how load-bearing the name is, which matters for how a label should read:

- **Incidental** — the name swaps out for free: "a `Read` of the log", "copy to the scratchpad".
- **Mechanism-named** — the action is portable, the tool is not: both `AskUserQuestion` rules.
- **Harness-factual** — the claim is about one harness and genericising makes it false or vague:
  "the Bash tool reports it whenever it is non-zero", the whole of "Viewing, searching, or editing
  files", "don't reach for plan mode".

Three apparent hits are ordinary English and must not be "fixed" — "Write about that work by its
shape", "Read the SHA", "Read-only `git -C` verbs". A mechanical sweep over capitalised tool names
flags all three, which is the standing argument against doing any of this as a sweep.

[PITFALL: **a rule may not live half in one fragment and half in another** — `config/agents-md/`'s
own README, and the assembler contributes whole `##` sections. So the tidy-looking fix of putting a
rule's portable principle in one fragment and its Claude instantiation in another is not available
without changing that convention first. It is why labelling, not splitting, is the cheap move.]

## Done — the remit renamed (2026-08-30)

The cluster is now `## What this setup provisions`, with an intro stating the admission test as a
dependency question (does this hold because PULSE put something there?) rather than a location one.
The fragment README's "which fragment a rule belongs in" section was reworded to match: filed by
what a rule depends on, not what it is about, and "this machine" explicitly is not a category.

Description only — no rule moved, and the assembled output still carries 38 rules.

The filename question this raised — `this-setup.md` lagging its own contents — was answered by the
re-cut a few hours later rather than by a rename: that file no longer exists. Deferring it was right
for the reason given at the time, that the category set might not leave a fragment to rename into,
which is exactly what happened.

## The category set, measured (2026-08-30)

All 38 rules classified by what they depend on rather than by where they sit. Three structural facts
fall out, and they constrain the answer more than any preference does.

**A clean partition by dependency does not exist.** Roughly ten of the 38 are a portable principle
wearing a local instantiation: "About to commit" is universal and names `inv quality.precommit`;
"Committing to a repo that is or might become public" is universal and names `plans.py scan`;
"Running a command against a different repo" mixes portable cwd reasoning with direnv and `.venv`;
"Naming around a collision" is universal with a PULSE example. Because a rule may not live half in
one fragment and half in another, any dependency-partition forces each of those to a side — and
filing "About to commit" under PULSE because it names an `inv` task tells a reader the wrong thing
about when it fires.

**The file already carries two axes, and the assembler entangles them.** Fragment is dependency
(`this-setup` / `claude-code` / `portable`); cluster is subject (Git & commits, Bash & tool use,
Research & design, Verification, Collaboration & output). Since a fragment contributes whole
clusters, the two cannot vary independently: changing which fragment owns a rule necessarily changes
which subject-cluster a reader finds it under, and vice versa.

**The skills category already exists and is scattered** — five rules across three clusters in two
fragments:

| rule                                                     | currently in                              |
| -------------------------------------------------------- | ----------------------------------------- |
| Setting up a repo's agent instructions and skills        | portable / Agent instructions & knowledge |
| Where durable knowledge goes                             | portable / Agent instructions & knowledge |
| Writing conventions into a shareable skill or template   | portable / Research & design              |
| Proposing an enforcement mechanism for agent behavior    | portable / Research & design              |
| Installing agent instructions and skills on this machine | this-setup / What this setup provisions   |

[PITFALL: **consolidating the skills cluster pulls a PULSE rule out of the PULSE fragment.** Four of
the five are already in `portable.md`; the fifth is PULSE-dependent (`inv ai.install-skills`). A
cluster cannot span fragments, so gathering them puts either that rule outside the fragment its
dependency belongs to, or the other four inside a fragment whose remit they do not meet. This is the
entanglement above showing up on the first concrete case, not a special difficulty of this cluster.]

## The design: fragment is subject, label is dependency (2026-08-30)

[DECISION: **fragments stop being the dependency axis.** A fragment owns one subject cluster, and
each rule carries a label naming what it assumes — the harness, or a PULSE-installed prerequisite —
with no label meaning it holds anywhere. Chosen by the user over a four-way dependency partition,
over consolidating only the skills cluster, and over dropping the whole-cluster constraint. It is
the only option under which the ~10 mixed rules do not have to pick a side, and it is what the
user's own "preface them with Claude Code" instinct already described.]

**The whole-`##`-section constraint stops binding.** With fragment and cluster both keyed to
subject, each fragment contributes exactly one cluster, so "a fragment contributes whole `##`
sections" is satisfied trivially rather than fought. The constraint does not need dropping — it
needed the two axes to stop disagreeing.

Six fragments, one cluster each, 38 rules preserved:

| fragment             | cluster                        | rules |
| -------------------- | ------------------------------ | ----- |
| `agent-knowledge.md` | Agent instructions & knowledge | 6     |
| `git.md`             | Git & commits                  | 8     |
| `bash.md`            | Bash & tool use                | 8     |
| `research.md`        | Research & design              | 8     |
| `verification.md`    | Verification                   | 3     |
| `collaboration.md`   | Collaboration & output         | 5     |

The two dependency-clusters dissolve, and their rules redistribute by what they are _about_:

- `What this setup provisions` → `sudo`, the venv/direnv rule and the locale rule to **Bash & tool
  use**; the ssh-key rule and the personal-repo push rule to **Git & commits**; "Installing a tool
  on this machine" to **Research & design**; "Installing agent instructions and skills" to **Agent
  instructions & knowledge**.
- `Claude Code specifics` → "Which sessions load this file" to **Agent instructions & knowledge**;
  "The permission model in force" and the auto-mode settings.json rule to **Bash & tool use**.

[PITFALL: **this is the change that finally makes the file names honest, so it should not be done in
the same commit as the content.** Six new fragment files means six new `src` entries in
`setup.toml`'s `agents_md` list and six new `PULSE::agents-md/<stem>` provenance markers in the
deployed output. The rules themselves are moving unchanged; the deployment plumbing is a separate
concern and a separate failure mode, and `deploy.status` compares against what PULSE last wrote.]

## Landed 2026-08-30

Three fragments became seven, and 15 of 38 rules gained a dependency label.

- **Fragments by subject.** `preamble.md` (5), `agent-knowledge.md` (10), `git.md` (20), `bash.md`
  (30), `research.md` (40), `verification.md` (50), `collaboration.md` (60), each owning the one
  `##` cluster named after it. The preamble carries the title, the assembly note that
  `this-setup.md` used to hold, and the label legend.
- **Labels.** `[Claude Code]` on nine rules, `[needs <thing>]` on six. The vocabulary is closed at
  those two shapes, and three tests hold it: the shapes themselves, that a package-shaped label
  names a real `[packages.*]` entry, and that heading comparisons strip labels so relabelling never
  reads as renaming.

[DECISION: **the label vocabulary is closed at two shapes.** An open one is how a label set stops
meaning anything — nothing tells a reader whether `[Claude]` and `[Claude Code]` are the same claim,
and no grep can either. Chosen over a coarse `[PULSE]`, because a coarse label cannot be checked
against anything, and the prerequisite warning deferred above needs a checkable claim to read.]

[PITFALL: **`[needs plan-docs]` looked like a package name and was a skill.** Caught by the test
within a minute of writing it: skills are not declared individually in `setup.toml` — they arrive as
a bundle through `[packages.agent-skills]` — so the label named nothing checkable. Relabelled to the
package, losing no precision because the rule's own text already names the `plan-docs` script by
path. A label whose form implies a check it does not pass is worse than no label.]

[PITFALL: **the old fragments stayed tracked after being deleted from disk, and the gate caught it
rather than the tests.** `repo-tasks`' `link_check` walks `git ls-files "*.md"`, so it tried to read
`config/agents-md/claude-code.md` and raised `FileNotFoundError`. Staging the deletions fixed it.
The lesson generalises past this repo: a "which files exist" check sourced from the index disagrees
with the working tree for exactly as long as a deletion sits unstaged.]

Verification that no rule text was lost: all 38 rule bodies were snapshotted before the move and
diffed against the assembled output afterwards — same 38 headings, zero bodies differing once
leading whitespace was normalised.

[PITFALL: **the first run of that diff reported all 38 bodies changed, and it was the diff that was
wrong.** The deployed format leaves an extra leading newline the source fragments do not.
"Everything changed" is nearly always a measurement bug rather than 38 real changes, and reading one
diff concretely settled it in one command — the same reflex the "generalizing from a sample" rule
asks for, applied to a result that looked alarming rather than reassuring.]

## Open questions

Both of the questions this section opened with are answered above and closed: the categories are the
six subject fragments, and the label is a bracketed suffix on the rule's heading. The skills
category the user asked for exists as `agent-knowledge.md`, gathering the five rules that had been
scattered across three clusters in two fragments.

The locale rule's fate has its own plan now — `plans/2026-08-30-english-iso-locale-defaults.md`,
opened when the question turned out to be about what this machine's locale _should_ be rather than
about which fragment holds a rule.

[DECISION: **the locale rule keeps its imperative and loses its machine fact**, 2026-08-30 — so it
needs no label and is not an exception after all. Its premise ("this machine's `LC_TIME` defaults to
`ro_RO`") stopped being true when `inv system.set-locale` took ownership of the locale
(`plans/2026-08-30-english-iso-locale-defaults.md`). The instruction was always the portable half:
forcing the C locale for output a script parses is correct wherever it runs, merely unnecessary on a
single-locale machine. It depends on nothing PULSE installs and describes no machine — ordinary
defensive scripting that this machine happened to teach.]

## Recommended direction

Rename before re-cutting — done. Next is the category set, then the Claude Code label, then the
re-cut, then the file rename that the re-cut may make moot anyway.

Do not sweep, and do not genericise: the reframing above settles that Claude tool names stay, and
several of these rules are worded the way they are because a shorter or vaguer version was measured
being missed.

## Migrated to

Every step above landed on 2026-08-30 and both open questions closed the same day, so this retires
as a whole rather than leaving a residue.

- `contributing/global-agents-md.md`, "Fragments are subjects, dependency is a label" — the design
  and why a dependency partition lost (already there since the re-cut), and now also the three ways
  a rule can name a harness and why a mechanical sweep is the wrong instrument, the prerequisite
  check's config-level and gate-split decisions, the method that proved no rule text was lost, and
  the tracked-deletion pitfall.
- `contributing/global-agents-md.md`, "What this setup provisions (cluster intro, retired
  2026-08-30)" — the user's reframing in their own words, and the 5-of-7 measurement that made it
  general rather than a one-off.
- The result itself is `config/agents-md/` (seven fragments, one cluster each) and its `README.md`;
  the label vocabulary is held by `tests/unit/test_agents_md.py` rather than by prose.
- The locale rule's fate went to `plans/2026-08-30-english-iso-locale-defaults.md` while this plan
  was open, and is not carried here.

Deliberately not migrated: the two measurement tables (`this-setup.md`'s 7 rules against
`setup.toml`, `portable.md`'s 7 harness-naming rules). Both describe a file layout that no longer
exists, and the conclusions each supports are recorded above without them. The `[needs plan-docs]`
pitfall is kept, since a label whose form implies a check it does not pass is a mistake available
again tomorrow; the "all 38 bodies changed" one is kept for the same reason.
