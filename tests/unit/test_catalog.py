"""Unit tests for tasks/catalog.py: first-sentence summarising, which setup.toml entries are
catalogued, and a drift check that fails when the committed docs/packages.md block no longer
matches setup.toml. See tests/README.md.
"""

import pytest

from tasks import util
from tasks.catalog import _BLOCK, _DOC_PATH, _generated_content, _summary, catalog_rows


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("One sentence only", "One sentence only"),
        ("First one. Second one.", "First one."),
        ("Collapses\n  wrapped   text", "Collapses wrapped text"),
        ("", ""),
        # The reason the split needs a capital after the period, not just whitespace: these are
        # ordinary in this file's descriptions and none of them ends a sentence.
        (
            "Installs to ~/.local/share/cargo instead of the ~/.cargo dotdir",
            "Installs to ~/.local/share/cargo instead of the ~/.cargo dotdir",
        ),
        ("Needs Ubuntu 24.04 or newer", "Needs Ubuntu 24.04 or newer"),
        ("Handles e.g. a proxy that answers 407", "Handles e.g. a proxy that answers 407"),
        # A sentence may open with a backtick or a paren, which the split has to accept as a start.
        ("What it is. `inv thing.do` runs it.", "What it is."),
    ],
)
def test_summary_takes_the_first_sentence(description: str, expected: str):
    assert _summary(description) == expected


def test_catalogued_packages_are_installable_and_enabled():
    """The two exclusions are the whole editorial policy of the page, so they are asserted against
    the real setup.toml rather than a fixture — a new disabled or method-less entry silently
    appearing in the published catalog is exactly the regression worth catching."""
    packages = util.load_config().get("packages", {})
    catalogued = {name for name, _, _, _ in catalog_rows()}

    assert catalogued, "the catalog is empty — setup.toml stopped parsing?"
    assert all("method" in packages[name] for name in catalogued)
    assert all(packages[name].get("enabled", True) for name in catalogued)

    excluded = set(packages) - catalogued
    assert excluded, "no entry is excluded any more — check the exclusions still apply"
    assert all(not packages[name].get("enabled", True) or "method" not in packages[name] for name in excluded)


def test_catalog_rows_are_name_sorted():
    names = [name for name, _, _, _ in catalog_rows()]
    assert names == sorted(names)


def test_committed_catalog_matches_setup_toml():
    """docs/packages.md is generated and committed, so the gate has to be what notices a stale
    one — the alternative is a docs page that quietly describes a setup.toml from three commits
    ago. Fix a failure by running `inv catalog.render` and committing the result."""
    _, status = util.ensure_block_text(
        _DOC_PATH.read_text(),
        _BLOCK,
        _generated_content(),
        style=util.MarkerStyle.HTML,
    )
    assert status == util.BlockStatus.OK, "docs/packages.md is stale — run `inv catalog.render`"
