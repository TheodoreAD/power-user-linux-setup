"""Unit tests for tasks/util.py's pure helpers — ok_label, ensure_block_text/BlockStatus, and
packages_by_method's enabled/tag-filtering logic (given an in-memory config, no file I/O). See
tests/README.md.
"""

from tasks import util


def test_ok_label():
    assert util.ok_label(True) == "ok"
    assert util.ok_label(False) == "MISSING"


def test_block_status_formats_as_plain_value_not_enum_repr():
    # (str, Enum) members format as "ClassName.MEMBER" in an f-string unless __str__ is
    # overridden — every call site here prints the status word directly, so this must hold.
    assert f"{util.BlockStatus.ADDED}" == "added"
    assert str(util.BlockStatus.UPDATED) == "updated"


def test_ensure_block_text_adds_new_block():
    text, status = util.ensure_block_text("existing content\n", "myblock", "new stuff")
    assert status == util.BlockStatus.ADDED
    assert "new stuff" in text
    assert text.startswith("existing content\n")


def test_ensure_block_text_is_idempotent_when_unchanged():
    first, _ = util.ensure_block_text("", "myblock", "content")
    second, status = util.ensure_block_text(first, "myblock", "content")
    assert status == util.BlockStatus.OK
    assert second == first


def test_ensure_block_text_updates_changed_block():
    first, _ = util.ensure_block_text("", "myblock", "old content")
    updated, status = util.ensure_block_text(first, "myblock", "new content")
    assert status == util.BlockStatus.UPDATED
    assert "old content" not in updated
    assert "new content" in updated


def test_ensure_block_text_html_style_uses_html_comment_markers():
    text, status = util.ensure_block_text("", "myblock", "content", style=util.MarkerStyle.HTML)
    assert status == util.BlockStatus.ADDED
    assert "<!-- PULSE::myblock -->" in text
    assert "<!-- /PULSE::myblock -->" in text
    assert "#" not in text


def test_ensure_block_text_html_style_blank_lines_around_content():
    # Markdown needs a blank line between adjacent block-level elements (marker <-> content) to
    # match dprint's own formatting — otherwise `inv quality.fix` would perpetually "fix" what
    # render-docs just wrote, and the two would never agree on a stable, idempotent output.
    text, _ = util.ensure_block_text("", "myblock", "content", style=util.MarkerStyle.HTML)
    assert "<!-- PULSE::myblock -->\n\ncontent\n\n<!-- /PULSE::myblock -->" in text


def test_ensure_block_text_html_style_is_idempotent_when_unchanged():
    first, _ = util.ensure_block_text("", "myblock", "content", style=util.MarkerStyle.HTML)
    second, status = util.ensure_block_text(first, "myblock", "content", style=util.MarkerStyle.HTML)
    assert status == util.BlockStatus.OK
    assert second == first


def test_packages_by_method_filters_by_method_and_enabled(monkeypatch):
    monkeypatch.setattr(
        util,
        "load_config",
        lambda: {
            "packages": {
                "ripgrep": {"method": "apt"},
                "fzf": {"method": "apt", "enabled": False},
                "docker": {"method": "apt-repo"},
            }
        },
    )
    monkeypatch.setattr(util, "_excluded_tags", set)

    result = util.packages_by_method(util.PackageMethod.APT)

    assert set(result) == {"ripgrep"}


def test_packages_by_method_filters_by_excluded_tags(monkeypatch):
    monkeypatch.setattr(
        util,
        "load_config",
        lambda: {
            "packages": {
                "ripgrep": {"method": "apt", "tags": ["cli"]},
                "steam": {"method": "apt", "tags": ["gui"]},
            }
        },
    )
    monkeypatch.setattr(util, "_excluded_tags", lambda: {"gui"})

    result = util.packages_by_method(util.PackageMethod.APT)

    assert set(result) == {"ripgrep"}
