---
status: idea
updated: 2026-09-12
---

# Imperative against rationale: what the community does, and where this file sits

## Context

Opened on the hypothesis that `~/.agents/AGENTS.md` mixes directive and justification in one breath
and pays for it. The hypothesis is right about the shape and wrong about the remedy: the community
does not strip the why, it **puts the why somewhere else and keeps the directive short.**

Measured rather than surveyed. The research library already held **182 measurable agent instruction
files** (`AGENTS.md`/`CLAUDE.md`/`GEMINI.md`, incl. `openai/codex`, `git`, `telegram-desktop`,
`sst/opencode`, `raycast/extensions`), so the comparison is against real files rather than against
advice about files. Script: `instr_mix.py`, classifying each sentence independently for a directive
(sentence-initial base-form verb, or a deontic modal) and for rationale/provenance (causal markers,
dates, incident verbs). A sentence carrying both is the shape under test.

## Evidence

### The corpus measurement

| metric                                        | `~/.agents/AGENTS.md` | community mean | median | the 8 files over 2k words |
| --------------------------------------------- | --------------------: | -------------: | -----: | ------------------------: |
| body words                                    |             **8,058** |            596 |    373 |               2,086–3,285 |
| directives per 100 words                      |               **1.7** |            3.4 |    3.0 |                   2.0–4.1 |
| mean sentence words                           |              **23.0** |           11.5 |   10.7 |                  9.1–14.0 |
| directive sentences also carrying rationale   |              **5.1%** |           1.0% |   0.0% |                  0.0–2.4% |
| bullet share of content lines                 |              **1.2%** |            68% |    74% |                     0–72% |
| directives carrying a nuance/exemption clause |              **6.5%** |           3.3% |   0.0% |                   0–16.2% |

**Directive _share_ of sentences is normal** — 39.6% against a 36.5% mean. That is the finding that
reframes the hypothesis: this file is not short of imperatives, it is long in the words wrapped
around them. At 1.7 directives per 100 words against a 3.4 mean it delivers **half the instruction
per unit of always-loaded context**, and it is below the floor of every large file in the corpus.

[PITFALL: **size does not explain it, and that was the obvious way for this measurement to be
wrong.** A 373-word median invites the objection that a 8,058-word file is being compared against
sticky notes. Controlled: only 8 community files clear 2,000 words and the largest is 3,285, so
`~/.agents/AGENTS.md` is **2.5× the largest agent instruction file in the corpus.** Within that
large-file group every gap holds or widens — mean sentence length 9.1–14.0 against our 23.0,
directive density 2.0–4.1 against our 1.7. `openai/codex`'s own `AGENTS.md`, written by the people
who wrote the harness, runs 4.1 directives per 100 words in 13.6-word sentences.]

[PITFALL: **the first pass over-counted mixing by 33%, via two markers that are not rationale at
all.** `rather than` and `instead of` are contrastive halves of a directive ("translate rather than
reach for the old spelling"), not justifications, and counting them put us at 6.8% mixed. Removing
them from the lexicon and re-running **both** corpora identically gives the 5.1%-against-1.0% above.
Hand-checked against a per-sentence dump before trusting the aggregate, which is what surfaced it.]

**Where we are closest to normal is hedging** — 6.5% of directives carry a nuance or exemption
clause against a 3.3% mean, but `telegram-desktop` runs 16.2%, so we sit inside the observed range
rather than outside it. Worth saying, because the other four metrics are outliers and stacking a
fifth that isn't would be the easy overclaim.

### What the community actually prescribes

The `agents.md` spec prescribes **nothing** — "AGENTS.md is just standard Markdown. Use any headings
you like" — so every norm below is emergent, not specified. That is itself worth knowing: there is
no authority to be out of compliance with.

- **Anthropic's own `skill-creator`** says both halves, and the second cuts against a naive trim:
  "Prefer using the imperative form in instructions", and **"Try to explain to the model why things
  are important in lieu of heavy-handed musty MUSTs."** Rationale is positioned as a _substitute_
  for MUST-stacking, not as noise competing with it.
- **`obra/superpowers`' `writing-skills`** is the fullest treatment (679 lines) and answers
  structurally rather than by ratio: `## Overview` is "core principle in 1-2 sentences",
  `## Real-World Impact` is **optional and last**. Token targets: frequently-loaded skills <200
  words _total_. So the why is admitted, compressed, and **segregated** — not interleaved.
- Its **"Match the Form to the Failure"** table is the sharpest thing in the corpus, and it says the
  imperative/rationale question is the wrong axis. Classify the baseline failure first: a discipline
  failure (knows the rule, skips it under pressure) takes prohibition plus a rationalization table;
  a **wrong-shaped output takes a positive recipe and is made worse by prohibitions**; an omission
  takes a structural slot; conditional behaviour takes a conditional on an observable predicate.
  With a measurement behind it — in head-to-head wording tests the prohibition arm produced more of
  the unwanted content than the recipe arm and **trended worse than the no-guidance control.**
- Two rules from the same page bear directly on our hedging: **"No nuance clauses"** (appending one
  nuance clause to a winning recipe degraded it from consistent to noisy) and **"Exemption clauses
  don't scope"** ("this limit doesn't apply to code blocks" still suppresses code blocks).

### The research, re-read rather than re-cited

**Gloaguen et al. 2026, `arXiv 2602.11988`** (ICLR 2026 workshop; the ETH Zurich result this repo
already cites without its ID) is the one that answers the question directly, verbatim from v2:

> while instructions in the context files are well followed by coding agents, repository overviews,
> although popular and recommended by model providers, are not helpful. We conclude that while
> context files are useful for specifying non-standard coding practices, any attempts to improve
> performance should be rigorously evaluated before deployment.

Instructions are followed; overviews are not helpful; the value is in **non-standard practice** —
which is the same class this repo's own notes already flag as high-return (`sudo -A`,
`inv ssh.check`, `LC_TIME=C`). The v1 abstract still on the SRI Lab page puts it the other way up:
"unnecessary requirements from context files make tasks harder, and human-written context files
should describe only minimal requirements."

[PITFALL: **the two published abstracts differ and a single fetch would have reported either as
_the_ abstract.** The SRI Lab page carries v1's wording, arXiv carries v2's, and the "repository
overviews are not helpful" sentence exists only in v2. A first fetch produced a summary containing
that sentence, a second produced a verbatim abstract without it — which reads as one fetch having
hallucinated, and neither had. Resolved by asking for the abstract verbatim, by version, from both
hosts.]

[DECISION: **`arXiv 2601.03269` is misattributed in `contributing/global-agents-md.md` and the
citation has to go.** The file says "Instructions compete for attention with inline narrative (arXiv
2601.03269) — relocating provenance here buys adherence independent of the token saving. **This file
exists because of that finding.**" The paper is "The Instruction Gap: LLMs get lost in Following
Instruction", on instruction compliance across 13 LLMs in enterprise RAG. Its actual sentence is
that instructions "often compete for attention with **lengthy knowledge snippets**" — retrieved
documents, not authored prose. The paraphrase swapped the referent and an architecture was built on
the result. Confirmed twice, against `/abs/` and `/html/v1`, both returning the same title and an
explicit no to the narrative question.]

The conclusion may survive its citation — `2602.11988` supports a version of it — but the support
has to be swapped, not quietly kept. Same class as this corpus's own recorded PITFALL about a
byte-exact, confidently wrong Codex finding: precision downstream of an unchecked premise reads as
rigour.

[UNVERIFIED: `arXiv 2510.14842` is "Boosting Instruction Following at Scale"; its "up to 7 points
for two instructions and up to 4 points for ten" is **the gain from their Instruction Boosting
method**, which this repo cites as the size of the near-duplicate conflict effect (~4–7pp). The
direction is defensible — they do attribute degradation to "tension and conflict as the number of
instructions is increased" — but the number is doing work it was not measured for. Needs the paper
read rather than its abstract.]

### The conflict this turns up, which is not ours to settle quietly

`superpowers` names our house style an anti-pattern outright:

> ❌ Narrative Example — "In session 2025-10-03, we found empty projectDir caused..." **Why bad:**
> Too specific, not reusable

`tests/unit/test_agents_md.py`'s docstring protects exactly that shape, naming the SSH rule's
three-passphrase-dialogs passage as narrative that **earns its place** "because it names the wrong
move the reader is about to make and nobody takes a reference hop before making it". Both positions
are argued; neither is measured. And the ETH result does not adjudicate it — an incident narrative
is neither an instruction nor a repository overview, so it is the third thing, unmeasured by the one
study that measured the other two.

## Open questions

[NEEDS CLARIFICATION: does the narrative that "earns its place" actually earn it? It is the one
claim in this corpus with a house exemption, a test protecting it, and no measurement either way.
`session-bash-audit` can measure the miss rate of a rule whose narrative is compressed to its
mechanism against one that keeps it — the SSH rule is a bad candidate (its failure is rare), the
`| head` and `echo $?` shapes are good ones (known rates, high volume).]

[NEEDS CLARIFICATION: is the 1.2% bullet share a defect or a deliberate register? Every large
community file except one runs 28–72% bullets. Prose was chosen here for rules whose conditions do
not decompose into a list, and no measurement says bullets beat prose for those. But 1.2% is not a
choice made per rule, it is a house voice applied to all of them.]

## Recommended direction

Nothing here proposes trimming for its own sake, which this corpus has already tried three times and
measured as spent (`plans/2026-08-26-agents-md-leanness-pass.md`).

1. **Fix the citation first**, because it is a factual error rather than a judgement call: swap
   `2601.03269` for `2602.11988` under "Evidence out of the deployed file", quote the
   instructions-followed/overviews-unhelpful sentence, add the ID to the existing Gloaguen bullet,
   and downgrade the SCALEDIF number to what it actually measured.
2. **Adopt "match the form to the failure" as an intake question**, not as a trim. It is a criterion
   the gate does not currently have: the criteria ask whether a rule states a trigger, duplicates,
   and files its evidence — never what _kind_ of failure it is answering, which is what decides
   between a prohibition, a recipe and a conditional. This is the highest-value finding here and it
   costs no words in the deployed file.
3. **Take the sentence length before the word count.** 23.0 against a 9.1–14.0 large-file range is
   the metric most clearly out of band, and it is the one that can move without deleting a claim — a
   directive and its justification in one 40-word sentence become a 12-word directive and a 12-word
   reason, same content, both readable alone.
4. **Leave hedging alone for now.** We are inside the observed range, and `superpowers`'
   nuance-clause finding is about a clause appended to a recipe under test, not about an exemption
   that records a real boundary. Revisit if 2 lands, since "express a real exception as its own
   conditional on an observable predicate" is the same move.
5. Re-measure with `instr_mix.py` after any of the above, so this comparison stays like-for-like.
   The script belongs in the repo if it is going to be re-run — it is currently a scratchpad file.
