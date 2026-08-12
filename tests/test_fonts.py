"""Unit tests for tasks/fonts.py's _load_jsonc — the only part of that module that doesn't
shell out to gsettings/fc-list or touch the filesystem/network. Also covers _load_vscode_settings,
which now delegates to it. See tests/README.md.
"""

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
