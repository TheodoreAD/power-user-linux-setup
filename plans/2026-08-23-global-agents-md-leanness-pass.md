---
status: in-progress
updated: 2026-08-23
---

## Progress

2026-08-23, later the same day — **all clusters converted** (user directed continuing past the
live-with-it window), terminology pass done, redeployed:

- Final shape: **2,499 body words, 6 `##` clusters, 29 `###` trigger-named rules, 288 lines** — from
  6,053 words / 30 flat sections / 563 lines. Well under the ~3,200–3,500 projection.
  Provenance-sentence share by the plan's own metric: 13% → **0%** (all evidence in
  `contributing/global-agents-md.md`).
- Environment cluster (`## This machine & the harness`, 6 rules), Verification (4 rules — the old
  verify-what-happened section split into its 3 real triggers, locale merged in per §7), Research &
  design (7 rules — reuse-upstream + tool-native merged, deep-research + best-tool merged, §11
  candidate 2 admitted as the bypass-flag clause of "Adding a CLI flag"), Collaboration & output (4
  rules, caveman kept near-verbatim). One commit each, per sequencing step 3.
- Terminology pass (§8): H1 renamed "Global agent instructions" (old title said "Claude Code" —
  contradicted the file's own cross-tool rule), "plan mode" casing unified.
- Section-inventory check (verification 2): 30 old sections → 29 rules + preamble; merges
  reuse+tool-native, deep+best-tool, granular+incidental; splits verify→3; subagent fact → preamble.
  No rule deleted; no rule moved to tier 2.
- All three §11 candidates decided: 1 and 2 as clause admissions into existing rules; the third
  (skills-over-enforcement, parked by a concurrent session mid-conversion) admitted as its own rule,
  `### Proposing an enforcement mechanism for agent behavior` — 30 rules total.

[UNVERIFIED: verification item 5 — live adherence over the following sessions. Do the converted
rules (git/commit especially, now also allowlist/research/verification) still fire from the
compressed trigger+rule form? This is the only thing keeping this plan from `landed`; regression
here outweighs the size win and would mean re-expanding the affected rule, not reverting the
structure.]

### Earlier the same day — sequencing steps 1–2:

- `contributing/global-agents-md.md` written: intro, admission criteria (§9), TOC, one section per
  rule with relocatable evidence (15 rules carry any; the rest have none recorded). Pointer preamble
  added to `config/global-AGENTS.md` naming the repo path and framing the rationale file as a
  precondition for changing it.
- **Git & commits cluster piloted**: 5 sections → `## Git & commits` with 4 trigger-named `###`
  rules (granular-commits + incidental-lint merged per §7). 909 → 385 words; file 6,053 → 5,529
  words, 30 → 26 top-level sections. Provenance (scaffoldapy reaffirmation) relocated.
- Now in the live-with-it window (sequencing step 2): watch whether the git/commit rules still fire
  over the next sessions before converting remaining clusters.
- **Bash cluster converted** (same day, user-directed): 4 sections (Bash tool discipline,
  multi-workdir testing, preferred search tools, direnv-vs-`uv run`) →
  `## Bash & the CLI
  allowlist` with 4 trigger-named `###` rules. 1,738 → ~460 words. Took the
  `cross-directory-command-execution` corrections (that plan is now retired): per-subcommand rule
  matching stated (conservatively, pending `plans/2026-08-22-compound-command-permission-audit.md`'s
  forensics), cwd-reset replaces the false cwd-persists premise, scoping flags now preferred,
  chained `cd && <venv>/bin/inv` is the documented invoke form. §5 done — the `Plan`/`Explore` fact
  is a document preamble now. §11 candidate 1 (friction-vs-prohibition) resolved: folded as one
  clause into the cluster intro ("a prompt is a friction cost, never a prohibition"), no new section
  — its general form is adequately covered there plus the harness's own finish-the-task instruction.
- Deferred to its own cluster: §11 candidate 2 (bypass-flag/ownership-marker) → Research & design
  cluster's `CLI flag conventions`.
- Note: non-Git rules' evidence now exists in both the contributing file and inline in the source —
  deliberate transitional duplication; each cluster conversion deletes its inline copies.

## Context

`config/global-AGENTS.md` (deployed to `~/AGENTS.md` + `~/.claude/CLAUDE.md`) is loaded
unconditionally into every session in every repo on this machine. It is now **563 lines / 6,053 body
words across 30 `##` sections** — roughly 8–9k tokens paid on turn zero, everywhere, forever.

No existing plan covers its shape. The two adjacent ones:

- `plans/2026-08-22-memory-to-agents-md-migration-sweep.md` — routing memory entries into
  `AGENTS.md`/skills/docs. It is _why_ the file grew: ~20 promoted memories landed here in one
  sweep. It never asked whether they should land as full sections.
- `plans/2026-08-22-deployed-config-drift-guard.md` — deployed-vs-source drift, mechanical.

Trigger for this pass: growth rate. Six sections were added or extended on 2026-08-23 alone.

### What the measurement says — the starting hypothesis was wrong

**Hypothesis going in:** the bulk is dated anecdote, so relocating provenance is the main lever.

**Measured:** provenance-bearing sentences are **813 words, ~13%**. Real, worth relocating, not the
dominant cost. The largest sections carry little or no dated provenance:

| words | dated provenance | section                                         |
| ----: | ---------------: | ----------------------------------------------- |
|   878 |                0 | Bash tool discipline                            |
|   556 |               76 | Testing a different repo's code (multi-workdir) |
|   411 |              135 | Verify what actually happened                   |
|   276 |              132 | Reuse maintained upstream work                  |
|   263 |               46 | Granular commits                                |
|   256 |                0 | Concurrent sessions                             |
|   234 |                0 | Project conventions                             |

**The real cost is explanatory redundancy.** "Bash tool discipline" states one principle — a novel
command prefix forfeits an existing allow rule — across five paragraphs, re-deriving it each time
for `cd`, scoping flags, `cd`-as-own-call, chaining, and parallel-means-separate-calls.

### 30 flat sections are really 6 clusters

| cluster                      | words | sections                                                                                                                                              |
| ---------------------------- | ----: | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bash / allowlist / tooling   | 1,738 | Bash discipline, multi-workdir, direnv-vs-`uv run`, preferred search tools                                                                            |
| Research & design method     | 1,292 | reuse upstream, tool-native, best-tool-per-concern, deep research, research-before-asking, pilot, composable, CLI flag conventions, naming collisions |
| Environment facts            |   969 | sudo, ssh askpass, auto-mode, uv traps, project conventions, cross-session memory                                                                     |
| Git & commits                |   909 | push on personal repos, granular commits, incidental lint, regenerated artifacts, concurrent sessions                                                 |
| Verification                 |   633 | verify-what-happened, locale                                                                                                                          |
| Collaboration & output style |   512 | pushback, typos/slips, caveman, move-to-plan                                                                                                          |

Flatness forces cross-reference paragraphs that exist _only_ because related rules sit far apart:
"Reuse maintained upstream work" spends 40 words explaining how it differs from "Tool-native over
hand-rolled" four sections later.

### Headings are inconsistent as triggers

The whole file is in context, so a heading is not navigation — it is a **retrieval cue**, the thing
that makes the model notice a rule applies right now.

- Strong (name the situation): `sudo`, `Preferred search tools`, `Granular commits`,
  `Check for direnv before reflexively prefixing uv run`, `Caveman-style terse output`.
- Weak (name a topic): `Project conventions`, `Composable design, UX designed first`,
  `Tool-native over hand-rolled`, `Reuse maintained upstream work`,
  `Best tool per concern, not fewer technologies for their own sake`.

### Misfiled and low-yield content

- **`Plan`/`Explore` subagents don't load this file** (108 words) is buried inside "Bash tool
  discipline" and has nothing to do with the allowlist. It governs whether every other rule applies
  at all.
- **Two `uv` traps** (196 words) is pure reference; its trigger has fired once, ever.
- **Naming collisions** (73 words) generalizes from a single incident.
- **Composable design, UX designed first** (141 words) states no trigger and no concrete test.
- **`Check for direnv…`'s second paragraph** re-derives the allowlist-prefix argument already made
  in full under "Bash tool discipline".

## Research: what actually makes an always-loaded instruction file work

Run 2026-08-23 per `~/AGENTS.md`'s own "Reuse maintained upstream work" and "Deep research" rules,
and because the size target and the structure question both needed an external answer rather than an
invented one.

### Size and rule count

- [Anthropic's CLAUDE.md guidance](https://claude.com/blog/using-claude-md-files) — keep it concise
  and human-readable; secondary write-ups of Anthropic's own engineers' practice put the working
  limit at **under 200 lines**, with teams running well under that.
  ([XDA summary](https://www.xda-developers.com/your-claude-md-is-probably-wrong-how-anthropics-engineers-structure/),
  [betterclaw](https://www.betterclaw.io/blog/agents-md-best-practices))
- **"Keep this section under 15 rules. If you have more than 15, you have not done the work of
  deciding which rules are genuinely load-bearing."** This file has 30 sections.
- **Bloated instruction files cause models to ignore instructions _wholesale_ rather than
  selectively filtering the irrelevant ones**
  ([morphllm's AGENTS.md guide](https://www.morphllm.com/agents-md-guide)). This is the load-bearing
  finding: the failure mode isn't "the file is expensive", it's "past some size, adherence falls off
  a cliff for everything in it, including the rules that matter."
- [Anthropic, _Effective context engineering for AI agents_](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  — models have a finite "attention budget"; "as the number of tokens in the context window
  increases, the model's ability to accurately recall information from that context decreases." Aim
  for "the minimal set of information that fully outlines your expected behavior" — and explicitly,
  **"minimal does not necessarily mean short."**

### Structure — does clustering help? (resolves the old open question 2)

Yes, and the mechanism is not the one assumed.

- Structured prompts with markdown/XML section boundaries produce measurably better adherence than
  free-form text; **clear section boundaries prevent "instruction bleed", where rules from one
  context contaminate another**, and help the model differentiate sections that share vocabulary.
  That is exactly this file's situation: four separate sections all discuss `cd`, three discuss
  commits, two discuss `uv`.
- **Position is not the lever.** "Lost in the middle" is real for _retrieval_ (>30% degradation),
  but the instruction-following literature found **no consistent relationship between instruction
  position and follow rate** — middle instructions were not followed less often
  ([arXiv 2511.13900](https://arxiv.org/pdf/2511.13900),
  [arXiv 2510.10276](https://arxiv.org/html/2510.10276v1)). So don't reorder for primacy/recency.
- **Conflict between instructions is a primary driver of degradation as instruction count grows**
  ([_Boosting Instruction Following at Scale_, arXiv 2510.14842](https://arxiv.org/abs/2510.14842) —
  introduces a conflict-scoring tool and the SCALEDIF benchmark). Deduplication and merging are
  therefore not just cosmetic: overlapping near-duplicate rules are the thing that measurably
  degrades adherence. Absolute effects are modest (their mitigation buys ~7pp at two instructions,
  ~4pp at ten), so the honest claim is "real but not dramatic" — worth doing, not worth overselling.
- Attention dilutes when "instructions compete for attention with lengthy knowledge snippets"
  ([arXiv 2601.03269](https://arxiv.org/html/2601.03269v1)) — i.e. narrative evidence sitting inline
  with rules actively costs adherence, independent of token count. This is the strongest argument
  for relocating provenance, stronger than the token saving.

### What transfers from skill authoring (the user's framing: "as it does when loading a matching skill description")

From
[Anthropic's Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices).
The honest answer first: **an always-loaded file has no trigger mechanism at all.** A skill gets
description-matched before its body is ever loaded; `~/AGENTS.md` is simply present, always, in
full. So the file cannot be made to work "like" a skill description — but three things do transfer:

1. **Progressive disclosure.** SKILL.md is an overview pointing at detail loaded on demand. Maps
   directly to AGENTS.md + a rationale doc.
2. **"Keep references one level deep."** Claude may _partially_ read a file reached through a nested
   reference (previewing with `head -100` instead of reading it whole). So AGENTS.md → the rationale
   doc must be one hop, and the rationale doc must not chain onward to a third file.
3. **"For reference files longer than 100 lines, include a table of contents at the top"** — so the
   rationale file needs a TOC even though AGENTS.md itself does not (AGENTS.md is always loaded
   whole; the rationale file may be previewed).

Four content rules transfer verbatim and are already this file's weak points:

- **Use consistent terminology.** "Choose one term and use it throughout… Mixing 'API endpoint',
  'URL', 'API route', 'path' hurts parsing." Directly matches the requirement to keep terminology
  consistent and correct.
- **Avoid time-sensitive information**, with historical context in an explicit "old patterns"
  section rather than inline. Every "Confirmed live 2026-08-23:" passage is this anti-pattern.
- **Concrete examples beat abstract prose.**
- **Match degrees of freedom to fragility** — low freedom (exact command, no deviation) for fragile
  operations, high freedom (heuristics) where many paths work. `sudo -A` is a low-freedom rule;
  "Composable design" is a high-freedom one; the file currently writes both in the same register.

Also: **"avoid offering too many options — provide a default with an escape hatch"**, and when a
rule is observed being missed, **strengthen its language** ("MUST" over "always") rather than
lengthening its explanation. The current file's instinct has been to add another paragraph.

### The three-tier consequence

The research implies a tier assignment this plan did not previously have:

| tier                                       | holds                                                                                                  | cost                           |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------ | ------------------------------ |
| **1 — `~/AGENTS.md`**                      | rules that can fire on any turn, or whose miss is silent and expensive (`sudo -A`, caveman, allowlist) | paid every session             |
| **2 — a skill**                            | rules with a sharp, statable trigger (`CLI flag conventions`, `Two uv traps`, `Composable design`)     | free until description-matched |
| **3 — `contributing/global-agents-md.md`** | provenance, reproductions, rejected alternatives                                                       | free until read                |

**Caveat that keeps tier 2 small:** this repo has already established that skill description
matching under-triggers (`plans/2026-08-22-skill-trigger-quality-review.md`). A rule only moves to
tier 2 if missing it is cheap and recoverable. Anything whose miss is silent stays in tier 1
regardless of how sharp its trigger is.

## Design

### 1. `contributing/global-agents-md.md` — the rationale file

Lives in this repo, not deployed. Decided by the user: **`~/AGENTS.md` is a deployed artifact and
must never be worked on directly**, so its rationale belongs where the file is actually developed. A
deployed sibling would additionally have to live under `~/.agents/` with a symlink, per this
machine's own convention — more moving parts for no benefit.

Matches the existing `docs/` (usage) vs `contributing/` (rationale) split already used by
`contributing/verify.md` and `contributing/cli-allowlist.md`. Structure: a TOC at the top (>100
lines, per the skill-authoring rule), then one `##` section per AGENTS.md rule, same heading text,
so a rule and its evidence are findable from each other by name.

`~/AGENTS.md` gets one pointer line near the top, framed as a precondition for _changing_ the file
rather than as optional reading, and naming the absolute path on this machine.

### 2. Rewrite each rule to "trigger + rule + one clause of why"

Everything else — dated confirmations, reproductions, tool versions, rejected alternatives, the
story of discovery — moves to tier 3. No rule loses force; the register changes.

### 3. Cluster the 30 sections into the 6 groups above

`##` per cluster, `###` per rule. Justified by the instruction-bleed finding, not by position
effects. Each merge deletes a cross-reference paragraph that only existed because the two halves
were far apart.

### 4. Headings become triggers

Every `###` names the situation that fires it. `Project conventions` →
`AGENTS.md over CLAUDE.md; skills live in .agents/skills/`. `Composable design, UX designed first` →
`Designing a generator or multi-mode tool`.

### 5. Promote the `Plan`/`Explore` subagent fact to a preamble

It states that a large fraction of the file silently does not apply to those subagents. That is a
precondition on the whole document, not a footnote inside the allowlist section.

### 6. Collapse the five allowlist paragraphs

Principle stated once; `cd`, scoping flags, chaining, `bash -c`, and parallel-means-separate-calls
become one line each.

**Overlap (resolved 2026-08-23):** the now-retired `cross-directory-command-execution` plan found
three of these paragraphs factually wrong, not merely verbose — cwd does **not** persist between
Bash tool calls, and the scoping flags the text discouraged are what actually works — and
`plans/2026-08-22-compound-command-permission-audit.md` separately contradicted the
`cd x && git status` prefix-matching claim. The Bash-cluster conversion took all of these
corrections rather than only shortening; the evidence lives in `contributing/global-agents-md.md`
("Composing a Bash call", "Running a command against a different repo than the session's project").

### 7. Merge the pairs that already cross-reference each other

reuse-upstream + tool-native; granular-commits + incidental-lint-fixes; verify-what-happened + the
locale rule (whose own text says it is "the same underlying lesson"). Per the conflict finding, this
is the change most likely to improve adherence rather than just shrink the file.

### 8. Terminology pass

One term per concept throughout, checked against what the referenced tools/files are actually
called. Standing requirement, not a one-off step: correct and consistent terminology, no informal
coinages where a canonical name exists — consistent with `~/AGENTS.md`'s own "Naming collisions"
rule and Anthropic's "Use consistent terminology".

### 9. No word budget, no mechanical gate

Decided by the user: a budget adds complexity and would be arbitrary. Instead the external
benchmarks above (≤200 lines, ≤15 rules, "conciseness is a public good") serve as **review reference
points**, and the discipline moves upstream to what gets _admitted_: a new rule must state its
trigger, must not duplicate an existing rule, and must put its evidence in tier 3. Re-review as the
file grows rather than failing a build.

### 10. Nothing is deleted without asking

Standing constraint for this work, per the user: a rule may carry intent that isn't visible in its
text. `Naming collisions` and `Composable design` — the two flagged as low-yield — are **kept**;
they get sharper triggers and their evidence relocated, nothing more. Moving a rule to tier 2 is a
form of removal from the always-loaded set and needs the same per-rule approval.

### 11. Candidate admissions raised while this plan was open

Deliberately parked here rather than appended to `config/global-AGENTS.md`, so they go through §9's
admission criteria (state a trigger, don't duplicate an existing rule, evidence to tier 3) instead
of growing the file by two more sections while this pass is trying to shrink it. Routed here by
`session-harvest` 2026-08-23; decide them as part of the relevant cluster's conversion, not
separately.

[DECISION: **"A rule whose stated rationale is a friction cost is not a prohibition"** — admitted as
one clause in the Bash cluster's intro ("An approval prompt is a friction cost, never a prohibition
— pay the prompt and do the work"), not as its own section: the observed harm was
allowlist-specific, and the general form is already carried by the harness's standing
finish-the-whole-task instruction. Evidence (an agent read the `&&` ban as a prohibition and
declined real cross-repo work) is in `contributing/global-agents-md.md`, "Composing a Bash call";
the plan that captured it (`cross-directory-command-execution`) is retired.]

[NEEDS CLARIFICATION: **"Don't add a bypass flag that gives an ownership marker two meanings."**
Trigger: designing an escape hatch that overrides a marker/manifest the tool uses to decide what it
owns. Evidence: rejecting a `--force` on `inv ai.skills` for foreign content (2026-08-23) — the
`.pulse-source` marker _is_ the ownership model, so a flag overriding it would make ownership mean
one thing with the flag and another without. Stated by the user as "we shouldn't have hacks that
make the mental model difficult, unless something is utterly impractical." Likely extends the
existing `CLI flag conventions` section rather than earning its own, per the variant-not-new-section
rule — but that section is currently about flag _shape_ (`-y` vs a bespoke opt-in), and this is
about whether the flag should exist at all, so the fit needs checking.]

[DECISION: **"Skills are the mainstay of directing agents"** — admitted 2026-08-23 (the third
candidate, parked by a concurrent session mid-conversion) as
`### Proposing an enforcement mechanism for agent behavior` in the Research & design cluster. It
passed §9 cleanly: sharp trigger, no overlap with any existing rule, and the user's position is
explicit in the evidence. Evidence (the git-hooks-for-quality-gate rejection and the user's
dev-standard quote) is in `contributing/global-agents-md.md` under the matching heading.]

## Files touched

- `config/global-AGENTS.md` — restructured; the deliverable.
- `contributing/global-agents-md.md` — new; rationale, TOC-first, one section per rule.
- `~/AGENTS.md` + `~/.claude/CLAUDE.md` — redeployed from source, never edited directly.
- `plans/2026-08-22-memory-to-agents-md-migration-sweep.md` — add a pointer: its intake taxonomy is
  the upstream half of §9's admission rules.

## Verification

1. Re-measure words/sections after each cluster; record actual against the ~3,200–3,500 projection
   rather than trusting it. The two commands that produced every number in Context above, so a later
   pass compares like with like instead of re-inventing the metric:

   ```shell
   # per-section word count, largest first (the 6,053 / 30-section figures)
   python3 -c "
   import re
   from pathlib import Path
   secs = re.split(r'^## ', Path('config/global-AGENTS.md').read_text(), flags=re.M)[1:]
   rows = [(len(s.split(chr(10), 1)[1].split()), s.split(chr(10), 1)[0]) for s in secs]
   for w, h in sorted(rows, reverse=True): print(f'{w:5d}  {h[:70]}')
   print(f'--- {sum(w for w, _ in rows)} words in {len(rows)} sections')
   "

   # share of words in provenance-bearing sentences (the 813 / ~13% figure)
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

   Known limit of the second one, worth stating so a later pass doesn't over-trust it: it matches at
   sentence granularity, so narrative that continues past the sentence carrying the marker is
   undercounted. Treat 13% as a floor, not a measurement.
2. Every rule in the old file maps to exactly one rule in the new file or to an approved tier move —
   checked by diffing section inventories, not by reading impressions.
3. `inv quality.precommit` clean.
4. Deployed copy byte-identical to `source.strip() + "\n"` after redeploy, and `~/.claude/CLAUDE.md`
   still a symlink to `~/AGENTS.md`.
5. Live check on the pilot cluster: over the following sessions, do the git/commit rules still fire
   when they should? Regression here outweighs any size win — a smaller file that stops working is a
   failure, not a trade-off.

## Sequencing

1. Write `contributing/global-agents-md.md` with the provenance already relocatable today.
2. Pilot the **Git & commits** cluster alone — 5 sections, 909 words, self-contained — and live with
   it for several sessions before converting anything else (`~/AGENTS.md`'s own "Pilot before
   generalizing").
3. Convert remaining clusters, one commit each, so any single one can be reverted alone.
4. Terminology pass across the whole file last, once section boundaries have settled.
5. Redeploy and verify; `plans/2026-08-22-deployed-config-drift-guard.md` is the mechanism if it has
   landed by then, a manual diff if not.
