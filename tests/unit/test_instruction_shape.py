"""The lexicons are the measurement, so these tests pin the classification decisions that were
argued for rather than the arithmetic around them.

Two of them guard against a specific way this module can go wrong silently: a marker that looks
causal but is not (`rather than`), and a sentence split that fires inside a command name. Both
produce a plausible number rather than an error, which is why they are tested rather than eyeballed.
"""

from pathlib import Path

from tasks import instruction_shape as shape


def _measure(text: str):
    return shape.measure_text(text, Path("test.md"))


def _long(text: str) -> str:
    """Pad past `measure_text`'s 60-word floor without adding directives or rationale."""
    filler = " ".join(["a plain descriptive clause about the repository layout here."] * 12)
    return f"{text}\n\n{filler}"


def test_a_sentence_initial_base_verb_is_a_directive():
    assert shape.is_directive("Run the repo's quality gate first.")


def test_a_deontic_modal_anywhere_is_a_directive():
    """Position-only detection misses every prohibition written as a clause, which is most of
    them."""
    assert shape.is_directive("A chain also hides the thing being approved, so never use one.")


def test_a_plain_description_is_not_a_directive():
    assert not shape.is_directive("The deployed file is assembled from fragments.")


def test_rather_than_is_not_rationale():
    """It is the contrastive half of a directive, not a justification. Counting it overstated the
    mixed rate by a third on the first pass over this corpus."""
    assert not shape.RATIONALE.search("Translate rather than reach for the old spelling.")


def test_because_is_rationale():
    assert shape.RATIONALE.search("Plain sudo fails because the Bash tool has no TTY.")


def test_temporal_since_is_not_rationale():
    """`since <date>` is provenance, and reading it as causal would mark every dated line mixed."""
    assert not shape.RATIONALE.search("The real file moved since 2026-09-04.")
    assert shape.RATIONALE.search("Use the prefix since it repairs a shell pinned to the empty agent.")


def test_a_directive_carrying_its_own_reason_counts_as_mixed():
    measured = _measure(_long("Always use sudo -A, because the Bash tool has no TTY."))
    assert measured is not None
    assert measured.directives == 1
    assert measured.mixed == 1


def test_a_directive_without_a_reason_is_not_mixed():
    measured = _measure(_long("Always use sudo -A."))
    assert measured is not None
    assert measured.directives == 1
    assert measured.mixed == 0


def test_hedged_counts_only_directives():
    """A nuance clause in a descriptive sentence costs nothing, so it must not inflate the rate."""
    measured = _measure(_long("Never chain commands unless the step is cross-repo.\n\nIt is usually a paragraph."))
    assert measured is not None
    assert measured.hedged == 1


def test_sentences_do_not_split_inside_a_dotted_command():
    """A bare `(?<=[.!?])\\s+` split turns every `inv quality.precommit` into two sentences and
    halves the measured sentence length — in the flattering direction."""
    assert shape.split_sentences("Run inv quality.precommit before every commit.") == [
        "Run inv quality.precommit before every commit."
    ]


def test_fenced_code_is_counted_but_not_scored():
    measured = _measure(_long("Use the task.\n\n```shell\nnever do this always\n```"))
    assert measured is not None
    assert measured.structure.code_lines == 3
    assert measured.directives == 1


def test_headings_are_not_scored_as_sentences():
    """A trigger-named heading is a retrieval cue; scoring `## About to commit` as a non-directive
    would penalise the convention this repo wants."""
    blocks, structure = shape.split_blocks("## About to commit\n\nRun the gate.\n")
    assert structure.headings == 1
    assert blocks == ["Run the gate."]


def test_inline_code_becomes_a_token_rather_than_vanishing():
    """Deleting it would make command-dense rules look terser than they are."""
    assert "CODE" in shape.strip_markdown("Prefer `rg` over `grep -r`.")


def test_too_little_prose_measures_as_nothing():
    """A stub pointing at a README would otherwise land in an aggregate as an outlier built on four
    sentences."""
    assert _measure("See the README.") is None


def test_bullet_share_separates_list_files_from_prose_files():
    bullets = "\n".join(f"- keep item {i} short" for i in range(10))
    _, structure = shape.split_blocks(bullets)
    assert structure.bullet_share == 100.0

    _, prose = shape.split_blocks("A paragraph line.\nAnother paragraph line.\n")
    assert prose.bullet_share == 0.0


def test_summarise_reports_mean_and_median_separately():
    """They disagree usefully: the community mixed-rate mean is 1.0% against a 0.0% median, which
    says most files never mix and a few do it a lot."""
    texts = ["Always use sudo -A because it has no TTY.", "Always use sudo -A.", "Always use sudo -A."]
    shapes = [s for t in texts if (s := _measure(_long(t)))]
    assert len(shapes) == 3
    mean_row, median_row = shape.summarise(shapes)
    assert mean_row.endswith("MEAN of 3 files")
    assert median_row.endswith("MEDIAN")


def test_the_repo_own_agents_md_is_measurable():
    """Guards the whole pipeline against a regex change that silently matches nothing — a corpus run
    would still print rows, all of them zero."""
    measured = shape.measure_file(Path(__file__).parent.parent.parent / "AGENTS.md")
    assert measured is not None
    assert measured.directives > 0
    assert measured.words > 1000
