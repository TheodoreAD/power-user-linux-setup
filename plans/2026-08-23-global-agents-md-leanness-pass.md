---
status: idea
updated: 2026-08-23
---

## Context

`config/global-AGENTS.md` (deployed to `~/AGENTS.md` + `~/.claude/CLAUDE.md`) is loaded
unconditionally into every session in every repo on this machine. It is now **563 lines / 6,053 body
words across 30 `##` sections** — roughly 8–9k tokens paid on turn zero, everywhere, forever.

No existing plan covers this. The two adjacent ones are about what _lands_ in the file and whether
the deployed copy matches its source, not about the file's own shape:

- `plans/2026-08-22-memory-to-agents-md-migration-sweep.md` — routing memory entries into
  `AGENTS.md`/skills/docs. It is the reason the file grew: ~20 promoted memories landed here in one
  sweep. It never asked whether they should have landed as full sections.
- `plans/2026-08-22-deployed-config-drift-guard.md` — deployed-vs-source drift, mechanical.

The trigger for this pass: the file's own growth rate. Six of its sections were added or extended on
2026-08-23 alone.

### What the measurement actually says

Measured, not eyeballed — the first hypothesis was wrong and worth recording as such.

**Hypothesis going in:** the bulk is dated anecdote ("Confirmed live 2026-08-22: …"), so moving
provenance to a reference doc is the main lever.

**Measured:** sentences carrying dated/provenance markers are **813 words, ~13%** of the file. Real,
worth relocating, but nowhere near the dominant cost. The five largest sections carry **zero** dated
provenance between them:

| words | dated provenance | section                                         |
| ----: | ---------------: | ----------------------------------------------- |
|   878 |                0 | Bash tool discipline                            |
|   556 |               76 | Testing a different repo's code (multi-workdir) |
|   411 |              135 | Verify what actually happened                   |
|   276 |              132 | Reuse maintained upstream work                  |
|   263 |               46 | Granular commits                                |
|   256 |                0 | Concurrent sessions                             |
|   234 |                0 | Project conventions                             |

**The real cost is explanatory redundancy, not storytelling.** Each rule is stated, re-justified,
then restated with a caveat. "Bash tool discipline" says "don't produce a novel command prefix" in
five paragraphs — `cd`, directory-scoping flags, `cd`-as-its-own-call, chained commands, and
"parallel means separate tool calls" are all the same principle applied to five surfaces, each
re-deriving the principle from scratch.

### Second finding: 30 flat sections are really 6 clusters

Grouping by theme, with no section counted twice:

| cluster                      | words | sections                                                                                                                                              |
| ---------------------------- | ----: | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bash / allowlist / tooling   | 1,738 | Bash discipline, multi-workdir, direnv-vs-`uv run`, preferred search tools                                                                            |
| Research & design method     | 1,292 | reuse upstream, tool-native, best-tool-per-concern, deep research, research-before-asking, pilot, composable, CLI flag conventions, naming collisions |
| Environment facts            |   969 | sudo, ssh askpass, auto-mode, uv traps, project conventions, cross-session memory                                                                     |
| Git & commits                |   909 | push on personal repos, granular commits, incidental lint, regenerated artifacts, concurrent sessions                                                 |
| Verification                 |   633 | verify-what-happened, locale                                                                                                                          |
| Collaboration & output style |   512 | pushback, typos/slips, caveman, move-to-plan                                                                                                          |

Flatness has a measurable cost: it forces cross-reference paragraphs that exist _only_ because
related rules are far apart. "Reuse maintained upstream work" spends 40 words explaining how it
differs from "Tool-native over hand-rolled" four sections later. Adjacent bullets need no such
paragraph.

### Third finding: headings are inconsistent as triggers

The whole file is in context, so a heading isn't a navigation aid — it's a **retrieval cue**, the
thing that makes the model notice a rule applies right now. Judged on that:

- Strong (name the situation): `sudo`, `Preferred search tools`, `Granular commits`,
  `Check for direnv before reflexively prefixing uv run`, `Caveman-style terse output`.
- Weak (name a topic, not a trigger): `Project conventions`, `Composable design, UX designed first`,
  `Tool-native over hand-rolled`, `Reuse maintained upstream work`,
  `Best tool per concern, not fewer technologies for their own sake`.

A rule whose heading doesn't state when it fires needs its body read to find out — which for an
always-loaded file means it competes with everything else for attention at the wrong moment.

### Misfiled and low-yield content spotted in the pass

- **`Plan`/`Explore` subagents don't load this file** (108 words) sits inside "Bash tool discipline"
  and has nothing to do with the allowlist. It's arguably the single highest-consequence fact in the
  file — it says a third of the rules here silently don't apply to a subagent — and it's buried.
- **Two `uv` traps** (196 words) is pure reference: factual gotchas whose trigger ("designing a
  uv-based shared-tool-install mechanism") has fired once, ever.
- **Naming collisions** (73 words) generalizes from a single past incident that is unlikely to
  recur.
- **Composable design, UX designed first** (141 words) has no stated trigger and no concrete test —
  the hardest kind of rule to act on.
- **`Check for direnv…`'s second paragraph** re-derives the allowlist-prefix argument already made
  in full under "Bash tool discipline".

## Open questions

- [NEEDS CLARIFICATION: where does the relocated provenance live? (a) a new deployed sibling —
  `config/agents-md-rationale.md` → `~/.claude/agents-md-rationale.md` via its own `wrapper-script`
  package, so it exists wherever `~/AGENTS.md` does; or (b) `contributing/global-agents-md.md` in
  this repo, matching the `docs/` vs `contributing/` split already used for `verify` and
  `cli-allowlist`, with `~/AGENTS.md` naming its absolute path. (b) is cheaper and conventional; (a)
  survives a machine where the repo isn't checked out. Lean: (b), since `~/AGENTS.md` only exists on
  machines this repo has provisioned anyway.]
- [NEEDS CLARIFICATION: does clustering into 6 `##` groups with `###` rules underneath actually help
  retrieval, or does burying rules one level deeper hurt it? No evidence either way. Cheapest test:
  restructure one cluster (Git & commits — 5 sections, 909 words, self-contained) and live with it
  before converting the rest.]
- [NEEDS CLARIFICATION: what's the target size, and is there a check that keeps it there? A word
  budget is enforceable (`inv` task, or a `verify.all` step) but arbitrary; no budget means this
  pass gets repeated in three months. Lean: measure after the rewrite, set the budget at that number
  plus headroom, fail loudly rather than silently.]
- [NEEDS CLARIFICATION: cut or keep the low-yield sections named above (`Naming collisions`,
  `Composable design`)? Deleting a rule the user deliberately added is a different decision from
  relocating its evidence, and isn't mine to make unilaterally.]

## Recommended direction

**Two files, one rule per trigger, evidence one hop away.** Not a rewrite of the rules themselves —
every rule stays, in force, with its meaning unchanged. What changes is where the _justification_
lives and how the rule is phrased.

1. **`~/AGENTS.md` keeps: trigger + rule + the one clause that makes the rule make sense.** Target
   the shape "when X, do Y (because Z, in one clause)". Dated confirmations, reproduction details,
   tool versions, and the story of how a rule was discovered all move out.
2. **The rationale file keeps everything else**, section-for-section, so a rule and its evidence are
   findable from each other by heading. It's read on demand — before editing, removing, or arguing
   with a rule, which is exactly when the provenance matters and the only time it's worth its
   tokens.
3. **`~/AGENTS.md` opens with one line pointing at it**, framed as a precondition for changing the
   file rather than as optional background.
4. **Headings become triggers.** Every `##`/`###` names the situation that fires it, not the topic
   it covers. `Project conventions` → `AGENTS.md over CLAUDE.md; skills live in .agents/skills/`.
   `Composable design, UX designed first` → `Designing a generator or multi-mode tool`.
5. **Promote the `Plan`/`Explore` subagent fact out of "Bash tool discipline"** to its own top-level
   rule. It governs whether every other rule in the file applies at all, which makes it a preamble,
   not a footnote to one section.
6. **Collapse the five allowlist paragraphs into one principle plus a bullet per surface.** The
   principle ("anything that changes the command's leading text forfeits an existing allow rule") is
   stated once; `cd`, scoping flags, chaining, `bash -c`, and parallel-means-separate-calls become
   one line each.
7. **Merge the pairs that already cross-reference each other**: reuse-upstream with tool-native;
   granular-commits with incidental-lint-fixes; verify-what-happened with the locale rule (whose own
   text already says it's "the same underlying lesson"). Each merge deletes a disambiguation
   paragraph that exists only because the two halves are far apart.

Rough projection, to be measured rather than trusted: **~6,050 → ~3,200–3,500 words** in the
always-loaded file, with ~2,500 words of evidence relocated and nothing deleted outright except what
question 4 resolves.

### Sequencing

1. Resolve the four open questions (only the first two block starting).
2. Pilot on the **Git & commits** cluster alone — 5 sections, 909 words, no dependencies on the rest
   — and live with it for a few sessions before converting anything else (`~/AGENTS.md`'s own "Pilot
   before generalizing").
3. Convert the remaining clusters one commit each, so any single one can be reverted on its own.
4. Re-measure, set the budget, and decide whether it's worth enforcing mechanically.
5. Redeploy and verify the deployed copy matches source —
   `plans/2026-08-22-deployed-config-drift-guard.md` is the mechanism if it has landed by then, a
   manual diff if not.
