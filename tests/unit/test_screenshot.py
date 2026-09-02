"""Unit tests for tasks/screenshot.py's documentation half: accelerator formatting, the rows the
published table is built from, and a drift check on the committed block. Nothing here touches
gsettings or the live session — see tests/README.md.
"""

import pytest

from tasks import util
from tasks.screenshot import (
    _DOC_BLOCK,
    _DOC_PATH,
    _FLAMESHOT_ACTIONS,
    _MANAGED_SHELL_KEYS,
    _SHELL_KEY_DEFAULTS,
    _bindings,
    _human_binding,
    _shortcut_rows,
)


@pytest.mark.parametrize(
    ("accelerator", "expected"),
    [
        ("Print", "Print"),
        ("<Shift>Print", "Shift+Print"),
        ("<Ctrl><Shift><Alt>R", "Ctrl+Shift+Alt+R"),
    ],
)
def test_human_binding_reads_as_a_keyboard_shortcut(accelerator: str, expected: str):
    assert _human_binding(accelerator) == expected


def test_every_flameshot_binding_has_a_published_description():
    """_FLAMESHOT_ACTIONS is keyed by the same `name` gsettings stores, so renaming a binding
    without updating the description is a KeyError here rather than a wrong sentence on the site."""
    assert {b["name"] for b in _bindings()} == set(_FLAMESHOT_ACTIONS)


def test_shortcut_rows_cover_the_managed_keys_and_the_untouched_ones():
    rows = _shortcut_rows()
    shortcuts = [shortcut for shortcut, _, _ in rows]

    assert len(rows) == len(_MANAGED_SHELL_KEYS) + 2
    for key in _MANAGED_SHELL_KEYS:
        assert _human_binding(_SHELL_KEY_DEFAULTS[key][0]) in shortcuts
    # The point of publishing the untouched pair: a reader has to be able to tell "PULSE leaves
    # this alone" from "PULSE never considered it".
    assert "Alt+Print" in shortcuts
    assert "Ctrl+Shift+Alt+R" in shortcuts


def test_committed_shortcuts_table_matches_the_task():
    """Fix a failure by running `inv screenshot.render-docs` and committing the result — the one
    task in this module that touches no session state."""
    content = util.markdown_table(
        ("Shortcut", "Ubuntu default", "After `inv screenshot.enable`"),
        [(f"`{shortcut}`", default, after) for shortcut, default, after in _shortcut_rows()],
    )
    _, status = util.ensure_block_text(_DOC_PATH.read_text(), _DOC_BLOCK, content, style=util.MarkerStyle.HTML)
    assert status == util.BlockStatus.OK, "docs/shortcuts.md is stale — run `inv screenshot.render-docs`"
