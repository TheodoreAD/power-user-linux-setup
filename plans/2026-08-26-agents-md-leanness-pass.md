---
status: in-progress
updated: 2026-09-02
---

## Context

`~/AGENTS.md` measured **4,326 body words, 37 rules, 446 lines** across 8 clusters immediately after
the 2026-08-26 fragment split (`plans/2026-08-26-agent-artifact-authoring-decoupling.md`). Its own
review reference points, researched and recorded in `contributing/global-agents-md.md`, are **≤200
lines and ≤15 rules**. The last leanness pass (2026-08-23) landed it at ~2,500 body words / 30 rules
/ 294 lines, so it has grown by roughly 1,800 words and 7 rules since, with no review in between.

The split did not cause the growth — it moved rules between fragments and added none. It made the
growth visible, because `contributing/global-agents-md.md`'s measurement commands now read the
**assembled** result rather than a single source file, and that was the first time the current total
had been measured at all.

Re-measured 2026-08-29: **39 rules / 530 lines**, so it has grown by a further 2 rules and 84 lines
since this plan was opened, still with no pass in between.

This plan exists because that finding currently lives as a sentence in
`contributing/global-agents-md.md` ("A leanness pass on `portable.md` specifically is the obvious
next one"), which is exactly the "don't stash future work in prose docs" failure the `plan-docs`
convention names: prose future-work has no status field, so nothing ever prompts a return visit.

## The Codex 32 KiB cut — corrected 2026-09-02, it never applied to this file

This section previously said Codex truncates `~/AGENTS.md` at 32 KiB and would silently drop the
whole `## Collaboration & output` cluster, and that finding shaped the rest of the plan: it supplied
the "get under 32,768 bytes first" ordering and a bound the leanness argument otherwise lacked. **It
was wrong about which file the cap governs.** Read from `openai/codex` source rather than from the
docs, which are stubs pointing at a site that does not state it:

- **The global file is read whole, uncapped.** `codex-rs/codex-home/src/instructions/mod.rs` tries
  `<codex_home>/AGENTS.override.md` then `<codex_home>/AGENTS.md`, `tokio::fs::read`s whichever it
  finds, trims it, and returns it. There is no length check anywhere in that path.
- **`project_doc_max_bytes = 32768` governs _project_ docs** — `codex-rs/config/defaults.toml` for
  the value, `codex-rs/core/src/agents_md.rs` for its use. It is a **shared budget** across every
  `AGENTS.md` walked from the project root down to cwd, spent in order, and a file that overruns is
  `data.truncate(remaining)`-ed.
- **Nor is it silent.** That truncation emits
  `tracing::warn!("project doc exceeds remaining budget;
  truncating")`. The original claim of a
  silent cut was wrong twice over.

Two things follow, and the second is the one that survives:

- **The bound this plan carried does not exist.** No byte target is owed on `~/AGENTS.md` for
  Codex's sake, at 47 KB or at any size. That removes the one objectively-checkable deadline the
  pass had, and leaves the ≤200-line/≤15-rule reference points as what they always were: review
  prompts that have never forced anything.
- **The cap is real for a repo's own `AGENTS.md`**, and for a monorepo the budget is shared across
  the nested ones. That is a constraint on the family repos rather than on this file, and it is
  worth carrying somewhere those repos' authors will meet it.

[PITFALL: **the original finding was byte-exact and confidently wrong, which is what made it
persuasive.** It named the constant, computed the overrun to the byte (35,498 against 32,768), and
located where the cut would land — mid-word inside a named heading — and every one of those
computations was correct about a cap that does not apply to the file being measured. Precision
downstream of an unchecked premise reads as rigour. The check that settled it was one grep of the
loader for the global path, available the whole time; what was actually read instead was the
constant's name, which contains the word `project` and says so.]

[PITFALL: **the docs could not have settled it.** `openai/codex`'s `docs/config.md` and
`docs/agents_md.md` are three-line stubs redirecting to a docs site, and the config-reference page
there describes `project_doc_max_bytes` as "maximum bytes read from `AGENTS.md`" without stating a
default or distinguishing global from project. Two vendor-doc fetches returned that same
under-specified sentence. The source was the only thing that could answer it, and reading it took
one API call more than the fetches did.]

## Why it matters, not just "the number is over"

The reference points are not arbitrary. From the research already in
`contributing/global-agents-md.md`: **bloated instruction files cause models to ignore instructions
wholesale**, not to selectively filter the irrelevant ones, and recall degrades as context grows.
Overlapping near-duplicate rules are a measured driver of that degradation. So the cost of being 2×
over is paid on every turn of every session in every repo, silently, and the rules most likely to be
dropped are not the ones anyone chose to sacrifice.

Where the weight sits, from the per-section measurement:

| cluster                        | words |
| ------------------------------ | ----- |
| Bash & tool use                | 919   |
| Git & commits                  | 691   |
| Research & design              | 669   |
| Verification                   | 528   |
| This machine & this setup      | 485   |
| Collaboration & output         | 433   |
| Claude Code specifics          | 432   |
| Agent instructions & knowledge | 169   |

`portable.md` holds the top four and is the obvious target; `this-setup.md` and `claude-code.md`
together are under 1,000 words and are not the problem.

## The pass as agreed (2026-08-30)

Three decisions taken with the user, which close the three questions this plan opened with.

[DECISION: **no rule is cut, and size is not the target.** Asked to choose a byte target, the user
declined one outright: "we have to figure out a way to keep all these hard-earned rules." So the
pass keeps every rule and every distinct claim, and any byte reduction is a by-product to be
measured rather than a goal to hit. This retires the "shorten in place" lever except where a claim
is genuinely stated twice, and it defers demotion-to-skills indefinitely rather than rejecting it.]

[DECISION: **merge near-duplicates first**, chosen by the user over demotion and over shortening.
This is the lever the research already favoured for adherence (~4–7pp, SCALEDIF) and it is the only
one compatible with the decision above — merging removes a claim's second statement, never the
claim.]

[DECISION: **one approval round per cluster**, not per rule and not one diff at the end. At ~22
candidate rules a per-rule pass was judged impractical, and a single end-of-pass review would defer
every "nothing is deleted without asking" judgement to one large read.]

These decisions were taken while the Codex cut above was still believed to bound the file, and the
correction does not disturb them — the user had already declined a byte target outright, so the one
lever the cut supplied was the one that had just been rejected. What the correction removes is the
argument a later session could have used to reopen it.

## The merge inventory

Six claims stated more than once across the assembled file, found by reading all three fragments in
full. The first three were done in round 1; the last three are round 2.

| #     | the claim stated twice or more                                                             | rules involved                                                                            |
| ----- | ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| A     | the tool already reports the exit code; `echo $?`/redirect add nothing; a pipe destroys it | Composing a Bash call · Viewing, searching, or editing files · Reading a command's result |
| B     | don't `\| head` your own search; count first                                               | Viewing, searching, or editing files · Generalizing from a sample to a set                |
| **C** | **whether cwd persists between Bash calls — a contradiction**                              | Composing a Bash call · Running a command against a different repo                        |
| D     | `git commit` ships the index, not the paths you named                                      | Committing multi-part work · Unexplained git/file state in a working tree                 |
| E     | a ref handed to git is read (`rev-parse`), never derived by eye                            | Force-pushing · Unexplained git/file state in a working tree                              |
| F     | parallel sessions on this machine share one working tree                                   | Force-pushing · Unexplained git/file state · Running a command against a different repo   |

[PITFALL: **C was a contradiction, not a duplication, and had gone unnoticed because the two halves
sat in different clusters.** "Composing a Bash call" asserted that cwd persists "on current builds";
"Running a command against a different repo" recorded both behaviours observed in one session on one
build and said to assume neither. A reader scanning for a cwd answer got whichever rule they hit
first. Finding it took reading all three fragments end to end — no per-rule review would have
surfaced it, because neither rule is wrong when read alone.]

Deliberately **not** merge candidates, checked and rejected: the Bash rules restated inside "Which
sessions load this file" (a deliberate paste-in for `Plan`/`Explore` subagents, which never load
this file, so the restatement is the only copy that reaches them), and the auto-mode paragraph's
reference to the `rg`/`fd` preferences (a pointer, not a second statement).

## Round 1 — Bash & tool use + Verification (landed 2026-08-30)

Taken as one round rather than two because both A and B straddle the cluster boundary: the
duplicated claims are Bash rules restated in Verification rules.

- **A** — canonical home is "Reading a command's result", unchanged. "Composing a Bash call" keeps
  the imperative and points at it (85 → 40 words); "Viewing, searching, or editing files" keeps the
  prohibition alone (55 → 15).
- **B** — canonical home is "Viewing, searching, or editing files", unchanged. "Generalizing from a
  sample to a set" keeps what is distinctive to it, the _inference_ that a truncated result stops
  being evidence about the set, and points at the other rule for the mechanics.
- **C** — resolved in favour of the researched position; "Composing a Bash call" now says to treat
  cwd as unknown after a cross-repo chain.

Measured before and after, assembled: **39,536 → 39,176 bytes** (−360), 6,343 → 6,274 words, 597 →
595 lines, 38 rules unchanged. The byte yield is far below the ~1,150 estimated from the removed
prose, because the pointers added back and dprint reflowed; worth knowing before anyone plans a
round around a predicted saving.

[UNVERIFIED: whether round 1 helped, hurt, or did nothing to adherence. A is the interesting one —
its `echo $?` shape was measured at 10–11% of Fable/Opus calls in the day a contradictory version
was live, so it is a rule with a known miss rate whose explanation now exists in one place instead
of three. `session-bash-audit` can measure the `echo-exit` and `redirect-then-filter` rates after
this has been deployed a while; that measurement is what closes this tag.]

## Round 2 — Git & commits (landed 2026-08-30)

D and E applied; **F deliberately skipped**.

- **D** — the merge that improved both rules rather than only shortening one. The subject had been
  split down the middle: "Committing multi-part work" named the failure (`git commit` ships the
  index) and offered only "stage late" against it, while "Unexplained git/file state" held the
  remedy (`git commit -m "…" -- <path>`) framed purely as parallel-session defence. The remedy moved
  to the commit-splitting rule, which is the heading a session constructing a commit actually
  consults; the parallel-session rule keeps what is specific to it and points.
- **E** — "Force-pushing" now opens by stating the principle (every ref you hand git is one you
  read, never one you derived) with the lease as its first instance, so "Unexplained git/file state"
  can cite it instead of restating `rev-parse` and claiming kinship.

[DECISION: **F was rejected, not deferred.** "Parallel sessions share one working tree" is stated in
about eight words in each of two rules, as the premise for two different consequences. Replacing
either with a pointer costs the reader the premise at the moment they need it, to save under a line
— the merge criterion is a claim stated twice, not a fact mentioned twice, and a premise short
enough to restate is cheaper in place than behind a reference.]

[PITFALL: **a rule can have no entry in `contributing/global-agents-md.md` at all, and nothing
reports it.** "Force-pushing, or asking what a remote actually has" had none — its evidence sat
inline in the deployed file, which is the arrangement the whole split exists to prevent. Found only
because round 2 went looking for the heading to write under. The `## Contents` list in that file is
also incomplete by several sections, so it cannot be used to answer "does this rule have evidence?"
either.]

## Round 3 — Git & commits (landed 2026-09-02)

Taken because the Git cluster had become **36% of the file**: 16,180 bytes across 8 rules, against
`bash.md`'s 9,649 across the same count. It had roughly doubled since round 2, entirely through
additions (the commit-body rule, the `-F` reversal, the one-`-m` clause, regenerate-from-canonical).

Two merges, both of a premise stated more than once:

- **The approval prompt is what the user reads** was argued three times inside "About to commit" —
  once per correction the rule has taken, since each correction re-derived the premise before naming
  its new shape. The premise now leads and the three defeating shapes hang off it: `-F` behind a
  path, a chain burying it mid-command, a series of `-m` flags running together. The chaining half
  points at "Composing a Bash call", which owns that cost and carries the user's own words for it —
  the same cross-fragment duplication round 1 found between Bash and Verification.
- **`git log` is a future agent's only access** opened "Committing multi-part work" and was derived
  again fifteen lines later under the body rule. Stated once now, with granularity and body as its
  two consequences.

Measured: **16,180 → 15,870 bytes** (−310), 226 → 223 lines, 8 rules unchanged.

[PITFALL: **the yield is the finding, not the saving.** Round 1 removed 360 bytes, round 3 removed
310, and between them the file gained 5,161. Merging returns roughly 2% per cluster because the
duplication left is premise-shaped — eight to thirty words restated where a pointer would cost
nearly as much — while growth arrives as whole new claims that no merge can touch. The lever is not
failing; it is finished. Any future reduction has to come from the intake gate or from a lever this
pass has ruled out, and a fourth round would be work whose result is already known.]

## The parked additions, decided (2026-09-02)

The pass's close. All five were put to the user in one round, per the "one approval round" decision;
four were admitted and landed the same day, one was not asked and is still parked below.

| addition                           | shape                         | destination                          |
| ---------------------------------- | ----------------------------- | ------------------------------------ |
| `git -C` at the session's own repo | clause on an existing rule    | `bash.md`, Composing a Bash call     |
| a local commit is not private      | paragraph on an existing rule | `git.md`, Unexplained git/file state |
| a probe is a sample of one         | paragraph on an existing rule | `verification.md`, Generalizing…     |
| no vendor lock-in                  | **new rule**                  | `agent-knowledge.md`                 |

Rule count 38 → 39, the first change since the fragments were re-cut. Evidence for each is in
`contributing/global-agents-md.md` under the section its rule keys to, three of them as `###`
subsections since a variant extends a section rather than taking one.

[DECISION: **the vendor-lock-in rule took a heading, and the reason generalises.** It is the general
form of "never a harness's own memory store", which is filed under where knowledge goes — a rule a
session consults when it already has something to file, not when it is choosing what to build on. A
constraint that has to fire _before_ a design exists cannot live inside a rule about where finished
work goes, however closely the two are related. That is a different admission argument from "it is
tier 1", and it is the one that made a 39th rule worth its bytes.]

## Open questions

## Rules with no evidence section (measured 2026-08-30)

Run after round 2 turned one up by accident. Comparing the `###` headings across the three fragments
against the `##` headings in `contributing/global-agents-md.md`: **11 of 38 rules have no matching
section.** Two of those carry dated provenance inline in the deployed file, which is precisely the
arrangement the fragment/evidence split exists to prevent:

| rule                                                | inline provenance     |
| --------------------------------------------------- | --------------------- |
| Committing to a repo that is or might become public | `Measured 2026-08-28` |
| The permission model in force                       | `Measured 2026-08-30` |

The other nine carry none, and most are correctly evidence-free — `sudo` is a two-line exact
instruction with its own worked example, "Caveman-style terse output" and "Invited to push back" are
stated user preferences rather than findings, and "Where durable knowledge goes" has evidence filed
under the evidence file's older heading for it ("Saving to cross-session memory"), so the heading
correspondence the file's own convention asks for has drifted through a rename rather than gone
missing.

### Done 2026-08-30, immediately after the merge pass

Both blocks relocated, the drifted headings reconciled, and the check made mechanical as
`tests/unit/test_agents_md.py` — four tests reading the real repo files, since the invariant is
about this repo's content rather than any function's behaviour:

- every rule has an evidence section, or is named in an `_EVIDENCE_FREE` list of rules that rest on
  no measurement (8 of 38: exact instructions carrying their own example, and stated preferences);
- every evidence section still matches a live rule — the direction that catches a rename;
- `_EVIDENCE_FREE` names no rule that has since been deleted, so an exemption cannot outlive its
  rule and hide the next one;
- no _new_ dated provenance appears inline in a fragment.

`Committing to a repo that is or might become public` and `The permission model in force` now have
sections of their own, with `Data flowing outward to a vendor` and `Auto mode withdraws Grep` folded
under them as `###` subsections — both had been clause-named `##` headings, which is why the
correspondence check could not see the rules they belonged to. `Saving to cross-session memory` was
retitled to `Where durable knowledge goes`, the rule's name since it moved out of the Claude Code
cluster. The `## Contents` list lost its three stale rows and gained the new sections.

[PITFALL: **the heading check and the inline-provenance check find disjoint problems, and only
running both gives the real count.** The heading comparison found 2 rules carrying provenance
inline; the regex over the fragments then found 4 more, all in rules that _do_ have evidence
sections — invisible to the first check by construction. The first estimate was therefore wrong by
3× in the direction that reads as "nearly clean".]

### The remaining four, resolved the same day

Checked before deciding, and they were not one case:

- **The `gh` poll loop** was a genuine duplicate — the evidence file already carries the incident in
  full (the process sweep, four loops alive ~36 hours, ~26,000 API calls), and the rule retold a
  compressed version. Compressed to its mechanism, like any other merge in this pass.
- **The two ssh incidents and the PyPI-wrapper measurement had no evidence section at all.** Moving
  them wholesale would have removed the narrative from the only place it existed.

[DECISION: **the date is provenance; the failure narrative is instruction.** So all four lose the
`Confirmed <date>:` / `Measured <date>,` framing and keep the story. "A session read the failure as
a missing key, ran `ssh-add`, and had the user type a passphrase into three dialogs for a key that
was already loaded elsewhere" stays in the rule, because it names the wrong move the reader is about
to make and nobody takes a reference hop before making it; the dated attribution goes to the
evidence file, because "who confirmed this, and when" is a question no session is asking mid-task.
This reads criterion 3 as being about dated confirmations specifically, which is what it says,
rather than about incident prose generally.]

With no exceptions left, the test dropped its grandfather list and asserts the invariant outright.

[PITFALL: **the check that found the four had been passing while missing two more, because `dprint`
reflows prose and a pattern spelled with a literal space cannot span the line break it inserts.**
`Measured 2026-08-29` sat in the file as `Measured\n2026-08-29`, and the regex read clean. Switching
the space to `\s+` immediately surfaced two further sites (in "Force-pushing" and the backgrounding
half of "Reading a command's result"). The general form: in a repo whose formatter owns line breaks,
any pattern spanning two words is wrong unless it allows one — and it fails _silently_, in the
reassuring direction, exactly like the truncation and empty-filter cases the rules themselves warn
about.]

[PITFALL: **stripping a date orphans every relative date pointing at it.** "Confirmed the same day"
in "Force-pushing" had referred to the `2026-08-29` two paragraphs above; moving that date left the
phrase pointing at nothing, and it still read as though it meant something. Caught by grepping the
fragments for relative-date phrases after the edit, not by reading the paragraph. There is now a
test for it, anchored to a provenance verb — "the same session" appears twice in these files as the
substance of a claim ("`Read`, `Edit` and `Write` all stay available in the same session"), and a
pattern matching the bare phrase flagged both.]

[PITFALL: **"they are all the same kind of exception" was wrong, and one command showed it.** The
four had been filed together as woven-in provenance to be decided as a unit. Grepping the evidence
file for each incident split them 1–3: one was already documented there and the other three existed
nowhere else, which inverts what "move it to the evidence file" costs in each case. Sorting by how a
passage _looks_ grouped a duplicate with three uniques.]

### Does merging alone reach a shape worth stopping at? — answered, no (2026-09-02)

Three rounds of data now say it does not, and the reason is not that the merges were done badly.

| moment                          | assembled bytes | rules |
| ------------------------------- | --------------: | ----- |
| pass opened (2026-08-26)        |          ~35.5k | 37    |
| after round 1 (2026-08-30)      |          39,176 | 38    |
| **before round 3 (2026-09-02)** |      **44,337** | 38    |
| after round 3 + admissions      |          46,911 | 39    |

Merging returned 670 bytes across three rounds. The file gained **5,161 in the three days between
rounds 2 and 3**, from four admissions nobody would want back, and 2,574 more from the four this
pass had itself parked. So the pass's premise — that a leanness problem is a duplication problem —
was true of the file it opened on and is not true of the file now. Every remaining claim is stated
once.

That leaves the resting state as a real choice rather than an outcome, and the honest options are
narrower than they were:

- **the intake gate**, which is where the pass's own closing sentence already pointed and the only
  lever that acts on the cause;
- **shortening claims**, explicitly rejected by the user at this pass's opening and not reopened
  here;
- **demotion**, still blocked on the trigger layer below.

[DECISION: **stop merging.** The inventory is exhausted, the yield is ~2% per cluster, and a fourth
round is work whose result is known. The pass closes as a merging pass; what it does not do is
declare the file finished at 46.9 KB, which is 1.4× the latent Codex cut and 3.5× the ≤200-line
review reference point. Those numbers are now the intake gate's problem, not this pass's.]

[NEEDS CLARIFICATION: which rules are demotion candidates under the tier test — sharp statable
trigger, cheap and recoverable miss? Deferred rather than answered by the decisions above, and worth
keeping only if the question above reopens it. `Bash & tool use` is the biggest cluster and the one
with a topic-owning skill (`session-bash-audit`) that can both hold guidance and _measure_ whether
moving it made adherence worse. That makes it the safest place to try demotion, and the riskiest to
get wrong, since its rules were rewritten specifically because they were being missed.]

## Additions parked pending this pass — all five admitted

Five accumulated here between 2026-08-26 and 2026-08-29, the first two from the harvest of the
`agent-skills` scoping session. Parking them was `session-harvest`'s "destination mid-restructure →
the plan reshaping it" filter: appending while the file's shape is being decided bypasses the
admission gate this pass exists to apply, and risks the addition being restructured away unread.

**All five were admitted at the close, 2026-09-02** — four in one approval round and the fifth
immediately after, since the round could carry only four options. The parking was worth it: the
vendor-lock-in entry changed shape while parked, from "tier 1, silent and expensive" to the sharper
argument that a constraint firing before a design exists cannot live inside a rule about where
finished work goes. A month of sitting is what produced the second reading.

Four of the five extend an existing section and leave the rule count alone; only vendor lock-in took
a heading. Rule count 38 → 39.

**Admitted and landed 2026-09-02** — "No vendor lock-in", as the new rule "Choosing a mechanism for
agent instructions, skills, or tools" in `agent-knowledge.md`, the trigger this entry proposed.
Evidence under the matching heading in `contributing/global-agents-md.md`.

**Admitted and landed 2026-09-02** — verify rather than reimplement, as a paragraph on "About to
author content, config, or a workaround from scratch" in `research.md`. Asked separately from the
other four because the approval round could carry only four options; taken on the same criteria.
Evidence in `contributing/global-agents-md.md`, including the asymmetry that carries it — the gap is
bounded and observable, the reimplementation is unbounded and permanent — and the observation that
the parent rule reads as a yes/no gate, so a partial yes had no branch and fell through to "no".

**Admitted and landed 2026-09-02** — the probe clause, as a paragraph on "Generalizing from a sample
to a set" in `verification.md`. The `Decimal`/SQLite instance and the reason a constructed probe
differs from a handed sample are in `contributing/global-agents-md.md`.

**Admitted and landed 2026-09-02** — the `git -C <own repo>` clause, on "Composing a Bash call" in
`bash.md`. The 89-against-14 measurement went to the evidence file, along with two later samples
showing the rate is a per-session disposition (23% and 0% in the same repo) rather than a trend.

**Admitted and landed 2026-09-02** — the local-commit clause, as a paragraph on "Unexplained
git/file state in a working tree" in `git.md`. The `agent-skills` incident and the argument that it
is where the confidentiality rule is sharpest are in the evidence file.

## Demotion is not relocation at current trigger rates (measured 2026-08-29)

The tier-2 lever assumes a rule moved into a skill still fires. Measured across 415 Claude Code
transcripts on this machine — every `Skill` invocation, all time, against 15,171 Bash calls:

```
58  plan-docs            (largely explicit /plan-docs, not model-chosen)
 8  session-harvest
 7  research-library
 5  update-config
 2  invoke-task-conventions
 2  python-conventions
 2  reorder-suggest
 1  session-bash-audit / skill-authoring / db-defaults
 0  mcp-server-shipping
 0  polite-mcp-conventions
```

87 invocations total. Two skills have never fired. `python-conventions` fired twice, in a repo
family that is almost entirely Python — the under-triggering `agent-skills`'
`plans/2026-08-22-skill-trigger-quality-review.md` predicted, now measured rather than suspected.

So **demoting a rule out of this file today is closer to deleting it than to relocating it**, and
the rules most likely to be nominated for demotion are the ones with sharp triggers — which is also
what makes them look safe. The plan's own framing already warns that several rules in `portable.md`
are long precisely because a shorter version was tried and missed; a demotion is a stronger version
of that same bet.

This does not kill the lever, it orders it. The trigger layer has to be fixed and shown to work
before anything is demoted into it. That work is `agent-skills`' — its trigger-quality plan plus the
contention scanner filed alongside it 2026-08-29 — so this plan now has an out-of-repo dependency it
did not have when it was opened.

External numbers that bear on the same judgement, worth recording so the next pass does not
re-research them: ETH Zurich (Gloaguen et al., 2026) measured human-written agent context files at
**+4% task success for +19% cost**, and LLM-generated ones at **−3% for +20%**. The strong exception
was non-obvious tooling instructions — an instruction naming `uv` produced 1.6 invocations per task
against 0.01 without it. That maps cleanly onto this file: `sudo -A`, `inv ssh.check`, `LC_TIME=C`
are the high-return kind and should be the last things touched; the long design-heuristic rules in
"Research & design" (669 words) are the low-return kind and should be the first.

## Recommended direction

Rough. Measure first with the two commands in `contributing/global-agents-md.md`'s "Re-measuring the
deployed file", so before/after is comparable with the 2026-08-23 numbers. Then take one cluster at
a time, largest first, and for each rule ask only the tier question — is the miss silent and
expensive, or sharp-triggered and recoverable? Merge before demoting, demote before shortening, and
re-measure after each cluster rather than at the end, so a pass that stops early still leaves the
file better than it found it.

Revised 2026-08-29 to "get under 32,768 bytes first", and **that revision is withdrawn**: the cut it
was chasing governs project docs, not this file (see the correction above). Nothing replaces it as a
numeric target, which is the honest position — the user declined one, and the only number that
looked externally imposed turned out not to be. **Hold every demotion** until the trigger layer is
measurably working, which is unaffected: otherwise the pass trades a bloat problem for a
silent-deletion problem, and the deletions will not be the rules anyone chose.

Do not treat the ≤200/≤15 numbers as a target to hit in one go. They are review reference points,
and the discipline that actually keeps the file small lives upstream in the admission criteria — a
pass that trims 1,000 words while the intake gate stays open just schedules the next pass.

[DEFERRED: **a candidate admission signal the criteria do not currently name — "the user believes
this rule is already recorded".** Moved here 2026-09-05 from
`2026-09-05-least-surprise-is-not-written-down-anywhere.md` — landed the same day and awaiting
retirement once its commits are pushed — whose own case is the evidence: the user wrote _"i'm sure
i've mentioned this is important in our projects"_ about a principle that `rg -in 'least surprise'`
could not find, after a session had already shipped and pushed the design it would have prevented.
Arguably that is direct evidence for admission and belongs in `contributing/global-agents-md.md`'s
criteria. Kept as an observation rather than a proposal, which is how it was filed — it is that
document's call, and this plan is where it waits because the intake gate is this plan's own
subject.]
