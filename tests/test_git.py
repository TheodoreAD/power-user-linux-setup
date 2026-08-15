"""Unit tests for tasks/git.py's resolve_project_dir — the only part of that module that doesn't
shell out to git or touch the filesystem. See tests/README.md.
"""

from pathlib import Path

from tasks.git import PROJECTS_ROOT, resolve_project_dir


def test_resolve_project_dir_relative_name_joins_under_projects_root():
    assert resolve_project_dir("github.com-personal") == PROJECTS_ROOT / "github.com-personal"


def test_resolve_project_dir_relative_name_with_nested_segments():
    assert resolve_project_dir("work/clientA") == PROJECTS_ROOT / "work/clientA"


def test_resolve_project_dir_wizard_default_resolves_to_projects_root_itself():
    # "~/projects/" is what tasks/identity.py's wizard writes when the user accepts the default —
    # it must resolve to PROJECTS_ROOT itself, not a subdirectory under it.
    assert resolve_project_dir("~/projects/") == PROJECTS_ROOT


def test_resolve_project_dir_tilde_path_expanded_and_used_as_is():
    assert resolve_project_dir("~/code/clientA") == Path.home() / "code" / "clientA"


def test_resolve_project_dir_absolute_path_used_as_is():
    assert resolve_project_dir("/mnt/data/projects") == Path("/mnt/data/projects")


def test_resolve_project_dir_empty_string_resolves_to_projects_root():
    # Legacy form (directory = "") from before the wizard wrote "~/projects/" explicitly — kept
    # working since Path(...) / "" is a no-op join.
    assert resolve_project_dir("") == PROJECTS_ROOT
