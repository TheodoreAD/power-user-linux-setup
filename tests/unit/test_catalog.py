"""Unit tests for tasks/catalog.py: first-sentence summarising, which setup.toml entries are
catalogued, and a drift check that fails when the committed docs/packages.md block no longer
matches setup.toml. See tests/README.md.
"""

import pytest

import tasks
from tasks import util
from tasks.catalog import (
    _PACKAGES_BLOCK,
    _PACKAGES_DOC,
    _TASK_SUMMARY_LIMIT,
    _TASKS_BLOCK,
    _TASKS_DOC,
    _clip,
    _packages_table,
    _summary,
    _tasks_table,
    catalog_rows,
    task_rows,
)


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
    ago. Fix a failure by running `inv catalog.render-packages` and committing the result."""
    _, status = util.ensure_block_text(
        _PACKAGES_DOC.read_text(),
        _PACKAGES_BLOCK,
        _packages_table(),
        style=util.MarkerStyle.HTML,
    )
    assert status == util.BlockStatus.OK, "docs/packages.md is stale — run `inv catalog.render-packages`"


def test_task_rows_cover_the_whole_published_namespace():
    """Including the tasks that arrive from repo-tasks — the page describes this repo's task
    surface as `inv --list` shows it, not only what tasks/ defines."""
    names = [name for name, _ in task_rows()]
    assert names == sorted(tasks.namespace.task_names)
    assert "setup" in names  # the bare top-level task
    assert "quality.precommit" in names  # arrives from repo-tasks


def test_every_task_row_has_a_summary():
    """An undocumented task would render as an empty cell, which reads as a broken page rather
    than as a missing docstring."""
    assert all(summary for _, summary in task_rows())


def test_no_task_summary_exceeds_the_table_limit():
    assert all(len(summary) <= _TASK_SUMMARY_LIMIT + 1 for _, summary in task_rows())  # +1 for the ellipsis


@pytest.mark.parametrize(
    ("summary", "expected"),
    [
        ("Short enough already", "Short enough already"),
        # Prefers the sentence's own first clause over a hard cut.
        (
            f"Regenerate the table in docs/packages.md from setup.toml — {'detail ' * 40}",
            "Regenerate the table in docs/packages.md from setup.toml",
        ),
        # ...but not when the clause is a fragment: "Do X" tells a reader nothing on its own, so a
        # hard cut that keeps 200 characters of the real sentence is the better cell.
        (f"Do X — {'detail ' * 40}", f"Do X — {'detail ' * 40}"[:200].rsplit(" ", 1)[0] + "…"),
    ],
)
def test_clip_prefers_a_clause_boundary(summary: str, expected: str):
    assert _clip(summary) == expected


def test_committed_task_index_matches_the_namespace():
    """Fix a failure by running `inv catalog.render-tasks` and committing the result. This one can
    go stale without any commit in this repo: a `repo-tasks` bump changes the task surface here."""
    _, status = util.ensure_block_text(
        _TASKS_DOC.read_text(),
        _TASKS_BLOCK,
        _tasks_table(),
        style=util.MarkerStyle.HTML,
    )
    assert status == util.BlockStatus.OK, "docs/tasks.md is stale — run `inv catalog.render-tasks`"
