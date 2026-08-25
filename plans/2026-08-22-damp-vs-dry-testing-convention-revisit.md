---
status: landed
updated: 2026-08-25
---

[DECISION: landed 2026-08-25 after reading the sources directly, not the paraphrase. Answers to the
open questions, in order: (1) Khorikov's article takes no position on parametrize — it never
mentions data-driven tests; its misapplied-DRY example is shared mutable state and an arrange step
hidden in a setup method. (2) The "echoed by Brian Okken" claim did not hold: Test & Code ep. 160
(2021, transcript in `okken/testandcode_transcripts`) never cites Khorikov, calls the DAMP-for-tests
argument something he's "on the fence" about, states one readability standard for production and
test code, and names "parameterization, fixtures, and helper functions" as the right tools to clean
up duplication "only if you can still read the test quickly." His book's dedicated parametrization
chapters exist to replace near-identical repeated test functions. (3) Yes, and it's now stated in
`SKILL.md`: a new case that adds a _value_ is a parametrize row; one that changes the test's _logic_
is a new test (Simply The Test, 2019). (4) No concrete failure case was on record; the framing is
softened to "mostly confirms," with the narrow override being branch-on-parameters mega-tests and
assertion-owning `check_*` helpers. Durable content: `SKILL.md` Testing conventions bullet,
`references/rationale.md` §7 (with the citation-check note), and the `testing.py` snippet, which now
shows both sides of the line.]

## Context

`skills/python-conventions/SKILL.md`'s testing-conventions section states DAMP over DRY for test
bodies as a **model-default override** — i.e. it's flagged as deliberately fighting a model's own
instinct, not just documenting one — and its bundled snippet
(`skills/python-conventions/references/snippets/testing.py`) enforces it by writing two
near-identical `Cart` tests as two separate explicit functions rather than one
`@pytest.mark.parametrize`-driven test, with a comment underlining the choice.

Surfaced 2026-08-22 while building `plans/2026-08-22-local-index-and-registry-testing.md` in
`repo-tasks`: asked to "use fixtures and parametrize" in new integration tests, I used fixtures
freely but avoided parametrize entirely, citing this skill. In that instance there was no real input
matrix to parametrize (one scenario per test), so the instruction and the skill's guidance never
actually collided — but the user flagged, correctly, that this convention may have been adopted
without fully examining its implications, and it's a core-enough concept (touches every test file in
every repo this skill family covers) to deserve a real second look rather than staying on the
strength of whatever reasoning first justified it.

The citation backing it, `skills/python-conventions/references/rationale.md` §7: "Vladimir
Khorikov's reframing (Enterprise Craftsmanship, and echoed by Brian Okken) resolves the popular
'DAMP not DRY' framing as a false dichotomy: DRY was never about _code_ duplication, it's about not
duplicating _domain knowledge_." The actionable split it draws: setup mechanics (fixtures/helpers)
stay DRY, freely; test bodies/assertions stay explicit and duplicated per test, "even when tests
look near-identical."

**A real inconsistency already visible in the source material, not hypothetical:** the same §7,
three lines earlier, says `parametrize`: attach `ids` once values stop being self-explanatory" — a
throwaway line that only makes sense if parametrize is expected, sanctioned, everyday practice. That
sits awkwardly next to "test bodies... stay explicit and duplicated per test, even when tests look
near-identical" a few lines later, which read literally would rule parametrize out in exactly the
"near-identical tests" case it exists for. The rationale doc doesn't reconcile these two lines with
each other, and the SKILL.md-level guidance a model actually sees inherits only the second, stricter
framing — `parametrize` isn't mentioned anywhere in `SKILL.md` itself or its snippet at all.

Also worth checking: Brian Okken is the author of _Python Testing with pytest_, a book whose own
core recommendation is to reach for `parametrize` specifically to avoid near-identical repeated test
functions — the opposite instinct from what's currently written. "Echoed by Brian Okken" needs a
real citation check: does Okken's own writing actually endorse Khorikov's DAMP-over-DRY framing for
test _bodies_, or is this an extrapolation made when the skill was authored, stretching an
endorsement of something narrower (e.g. not duplicating domain _concepts_ across tests) into a
blanket anti-parametrize stance he wouldn't actually sign off on?

## Open questions

[NEEDS CLARIFICATION: does Khorikov's actual Enterprise Craftsmanship article take a position on
`pytest.mark.parametrize` specifically, or only on hand-collapsing multiple assertions into one
shared test function via conditionals/branching? These are not the same thing — parametrize keeps
each case's inputs/expected-output explicit and visible (arguably _more_ explicit than copy-pasted
near-identical function bodies, since the varying parts are isolated from the fixed scenario logic),
whereas a hand-rolled "mega-test" branching on a flag genuinely does hide the scenario. Find and
read the actual source article before deciding whether the current skill wording over-extrapolated.]

[NEEDS CLARIFICATION: what does Brian Okken's own published guidance (his book, blog, or the Test &
Code podcast) actually say about parametrize vs. duplicated test bodies? Confirm the "echoed by"
claim is accurate rather than a mismatched pairing of two authors who actually disagree on this
point.]

[NEEDS CLARIFICATION: is there a principled line between "parametrize is fine here" (e.g. a pure
input→expected-output matrix, like `test_version.py`'s `bump`/`part` cases in `repo-tasks`) and
"parametrize would hide the scenario" (e.g. tests that differ in more than their literal inputs —
different setup, different assertions, different failure semantics)? If so, the skill should state
that line explicitly rather than reading as a blanket "don't parametrize."]

[NEEDS CLARIFICATION: does the current wording's model-default-override framing ("a model left alone
would parametrize/DRY this up, don't") reflect real observed agent behavior, or was it reasoning
from first principles without a concrete failure case in hand? If there's no remembered concrete
instance of an agent producing a bad DRY'd-up test, the override framing itself may be worth
softening to "confirms" or a narrower "mostly confirms, except X."]

## Recommended direction

Re-read the actual Khorikov article and whatever Okken source is being cited (not just the
paraphrase in `rationale.md`) before touching `SKILL.md`. If the "false dichotomy" framing holds up
under a direct read, the likely fix is narrower wording in `SKILL.md` itself (not just
`rationale.md`, which a model rarely loads) distinguishing "parametrize a real input matrix — fine,
expected" from "don't collapse genuinely different scenarios into one branching mega-test — the
actual thing being warned against." If the citations turn out weaker than the current paraphrase
implies, revise the guidance itself, not just its sourcing.

## Migrated to

- **`skills/python-conventions/SKILL.md`** — the corrected testing-conventions bullet (a new case
  that adds a _value_ is a parametrize row; one that changes the test's _logic_ is a new test).
- **`skills/python-conventions/references/rationale.md` §7** — the citation check itself: what
  Khorikov's article does and doesn't say, that the Okken attribution didn't hold and what he
  actually says, and the narrowed override (branch-on-parameters mega-tests, assertion-owning
  `check_*` helpers).
- **`skills/python-conventions/references/snippets/testing.py`** — shows both sides of the line.

Not migrated: the four open questions and the "Recommended direction" — all answered by the
`[DECISION:]` at the top, whose content is what §7 now carries.
