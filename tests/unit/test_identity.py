"""Unit tests for tasks/identity.py's _render/_toml_string — pure TOML string-building with no
subprocess/filesystem calls of their own (unlike init(), which prompts interactively and writes
identity.toml). See tests/README.md.
"""

import tomllib

from tasks.identity import _render, _toml_string


def test_toml_string_quotes_plain_value():
    assert _toml_string("jane") == '"jane"'


def test_toml_string_escapes_backslash_and_quote():
    assert _toml_string(r'C:\jane "the" smith') == '"C:\\\\jane \\"the\\" smith"'


def test_render_simple_profile_no_hosts_round_trips_through_toml():
    text = _render("Jane Smith", "jane@example.com", "~/projects/", hosts=[])
    parsed = tomllib.loads(text)
    assert parsed["git_profiles"] == [{"directory": "~/projects/", "name": "Jane Smith", "email": "jane@example.com"}]
    assert "ssh_hosts" not in parsed


def test_render_with_hosts_adds_one_ssh_hosts_entry_per_host():
    text = _render("Jane Smith", "jane@example.com", "~/projects/", hosts=["GitHub", "GitLab"])
    parsed = tomllib.loads(text)
    assert parsed["ssh_hosts"] == [
        {"user": "git", "alias": "github.com", "hostname": "github.com", "email": "jane@example.com"},
        {"user": "git", "alias": "gitlab.com", "hostname": "gitlab.com", "email": "jane@example.com"},
    ]


def test_render_escapes_special_characters_in_name():
    text = _render('Jane "JJ" Smith', "jane@example.com", "~/projects/", hosts=[])
    parsed = tomllib.loads(text)
    assert parsed["git_profiles"][0]["name"] == 'Jane "JJ" Smith'


def test_render_custom_absolute_directory_round_trips():
    text = _render("Jane Smith", "jane@example.com", "~/code/clientA", hosts=[])
    parsed = tomllib.loads(text)
    assert parsed["git_profiles"][0]["directory"] == "~/code/clientA"
