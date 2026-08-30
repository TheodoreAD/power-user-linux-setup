"""Unit tests for the parts of tasks/fonts.py that don't shell out to gsettings/fc-list or touch
the network: _load_jsonc (and _load_vscode_settings, which delegates to it), the values derived
from [settings.fonts], and the renderer that writes the font into the repo-side configs.

The last of those includes the check that matters most — that the four committed config files
already say what [settings.fonts] declares, so a font change that skips `inv fonts.render-configs`
fails here rather than leaving one application on the old font. See tests/README.md.
"""

import pytest

from tasks import fonts, util
from tasks.fonts import _load_jsonc, _load_vscode_settings


def test_load_jsonc_plain_json():
    assert _load_jsonc('{"a": 1, "b": 2}') == {"a": 1, "b": 2}


def test_load_jsonc_strips_line_comment():
    text = '{\n  // a leading comment\n  "a": 1\n}'
    assert _load_jsonc(text) == {"a": 1}


def test_load_jsonc_strips_trailing_same_line_comment():
    text = '{\n  "a": 1 // trailing comment\n}'
    assert _load_jsonc(text) == {"a": 1}


def test_load_jsonc_ignores_double_slash_inside_string_value():
    assert _load_jsonc('{"url": "https://example.com"}') == {"url": "https://example.com"}


def test_load_jsonc_strips_trailing_comma_before_brace():
    assert _load_jsonc('{"a": 1, "b": 2,}') == {"a": 1, "b": 2}


def test_load_jsonc_strips_trailing_comma_before_bracket():
    assert _load_jsonc('{"a": [1, 2,]}') == {"a": [1, 2]}


def test_load_vscode_settings_missing_file_returns_empty(tmp_path):
    assert _load_vscode_settings(tmp_path / "does-not-exist.json") == {}


def test_load_vscode_settings_empty_file_returns_empty(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("")
    assert _load_vscode_settings(path) == {}


def test_load_vscode_settings_parses_jsonc_with_trailing_comment(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{\n  "editor.fontFamily": "JetBrains Mono" // set by pulse\n}')
    assert _load_vscode_settings(path) == {"editor.fontFamily": "JetBrains Mono"}


# ---------------------------------------------------------------------------
# One place names the font
# ---------------------------------------------------------------------------


def _stub_fonts(monkeypatch, cfg: util.FontsSettings) -> None:
    monkeypatch.setattr(fonts, "_cfg", lambda: cfg)


def test_monospace_is_the_mono_variant_with_the_size_appended(monkeypatch):
    _stub_fonts(monkeypatch, {"family": "Fam", "family_mono": "Fam Mono", "size": 14})

    assert fonts.monospace_font() == "Fam Mono 14"


def test_vscode_font_keys_are_derived_from_the_two_families(monkeypatch):
    _stub_fonts(monkeypatch, {"family": "Fam", "family_mono": "Fam Mono", "size": 14})

    assert fonts.vscode_settings() == {
        "editor.fontFamily": "'Fam', monospace",
        "editor.fontSize": 14,
        "terminal.integrated.fontFamily": "Fam Mono",
        "terminal.integrated.fontSize": 14,
    }


def test_vscode_passthrough_keys_survive_alongside_the_derived_ones(monkeypatch):
    _stub_fonts(
        monkeypatch,
        {"family": "Fam", "family_mono": "Fam Mono", "vscode": {"editor.fontLigatures": True}},
    )

    assert fonts.vscode_settings()["editor.fontLigatures"] is True
    assert fonts.vscode_settings()["editor.fontSize"] == 12  # the default size, still derived


def test_a_missing_family_raises_rather_than_configuring_an_empty_font(monkeypatch):
    """An empty family renders as the system fallback, which looks exactly like the Nerd Font
    failing to install — a loud failure is the only way to tell those apart."""
    _stub_fonts(monkeypatch, {"size": 12})

    with pytest.raises(RuntimeError, match="family"):
        fonts.monospace_font()


# ---------------------------------------------------------------------------
# Rendering it into the repo-side configs
# ---------------------------------------------------------------------------


def test_render_rewrites_every_rule_it_is_given(monkeypatch):
    _stub_fonts(monkeypatch, {"family": "Fam", "family_mono": "Fam Mono", "size": 14})
    rules = (
        (r'^(config\.font\s*=\s*wezterm\.font\s*")[^"]*(")', r"\g<1>{mono}\g<2>"),
        (r"^(config\.font_size\s*=\s*).*$", r"\g<1>{size}.0"),
    )

    out = fonts.render_text('config.font = wezterm.font "Old"\nconfig.font_size = 9.0\n', rules)

    assert out == 'config.font = wezterm.font "Fam Mono"\nconfig.font_size = 14.0\n'


def test_a_rule_matching_nothing_raises(monkeypatch):
    """A silently-skipped substitution leaves the old font in a file this claims to have updated —
    which is how an upstream option rename would slip through unnoticed."""
    _stub_fonts(monkeypatch, {"family": "Fam", "family_mono": "Fam Mono"})

    with pytest.raises(RuntimeError, match="matched nothing"):
        fonts.render_text("nothing here\n", ((r"^font = .*$", r"font = {mono}"),))


def test_the_committed_configs_match_what_settings_fonts_declares():
    """The whole point of the mechanism: `[settings.fonts]` is the one place the font is named, so
    every repo-side file that names it must already agree. A change to that block without a
    `inv fonts.render-configs` run fails here."""
    stale = [path.name for path, text in fonts.rendered().items() if path.read_text() != text]

    assert not stale, f"run `inv fonts.render-configs` — these no longer match: {stale}"
