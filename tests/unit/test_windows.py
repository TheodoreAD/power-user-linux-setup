"""Unit tests for tasks/windows.py's PATH arithmetic and its refusals. The registry itself is not
touched here; `inv windows.configure-path` was run against the real user PATH on Windows. See
tests/README.md.
"""

import sys

import pytest
from invoke import Exit, MockContext

from tasks import util, windows
from tests.platforms import EVERYWHERE

_EXPAND = {"USERPROFILE": r"C:\Users\me"}
_SHIMS = r"%USERPROFILE%\.local\share\venv-shims"


def test_a_declared_directory_goes_first_and_everything_else_keeps_its_order():
    entries = [r"C:\a", r"C:\b"]
    assert windows.with_dirs_first(entries, [_SHIMS], _EXPAND) == [_SHIMS, r"C:\a", r"C:\b"]


def test_an_existing_entry_is_moved_not_duplicated_however_it_is_spelled():
    # Already present as an absolute path, further down: recognised as the same directory.
    entries = [r"C:\a", r"C:\Users\me\.local\share\venv-shims\\", r"C:\b"]
    assert windows.with_dirs_first(entries, [_SHIMS], _EXPAND) == [_SHIMS, r"C:\a", r"C:\b"]


def test_empty_entries_are_dropped():
    assert windows.with_dirs_first(["", r"C:\a", ""], [_SHIMS], _EXPAND) == [_SHIMS, r"C:\a"]


def test_declared_dirs_are_spelled_relative_to_the_profile(monkeypatch):
    monkeypatch.setattr(
        util,
        "load_config",
        lambda: {"packages": {"venv-shims": {"platforms": EVERYWHERE, "windows_path": ["~/.local/share/venv-shims"]}}},
    )
    monkeypatch.setattr(util, "load_overrides", dict)
    monkeypatch.setattr(util, "_excluded_tags", set)

    assert windows.declared_dirs() == [_SHIMS]


@pytest.mark.parametrize("task", [windows.check_path, windows.configure_path])
def test_every_task_refuses_off_windows(monkeypatch, task):
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(Exit, match="native Windows"):
        task(MockContext())
