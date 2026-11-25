"""Unit tests for tasks/git.py's path resolution — the part of that module that doesn't shell out to
git or touch the filesystem. See tests/README.md.
"""

from pathlib import Path

from tasks.git import PROJECTS_ROOT, include_scopes, resolve_project_dir
from tasks.util import GitProfile


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


# An absolute path on this platform: "/mnt/data/projects" on Linux, "C:\mnt\data\projects" on Windows,
# where a path without a drive is not absolute.
_ROOT = Path(Path.home().anchor)


def test_resolve_project_dir_absolute_path_used_as_is():
    absolute = _ROOT / "mnt" / "data" / "projects"
    assert resolve_project_dir(str(absolute)) == absolute


def test_resolve_project_dir_empty_string_resolves_to_projects_root():
    # Legacy form (directory = "") from before the wizard wrote "~/projects/" explicitly — kept
    # working since Path(...) / "" is a no-op join.
    assert resolve_project_dir("") == PROJECTS_ROOT


def test_include_scopes_without_extras_is_the_profile_directory_alone():
    profile: GitProfile = {"directory": "github.com-personal", "name": "J", "email": "j@example.com"}
    assert include_scopes(profile) == [PROJECTS_ROOT / "github.com-personal"]


def test_include_scopes_lists_the_profile_directory_first_then_each_extra():
    # configure() unpacks the first as the directory that owns the .gitconfig, so the order is load-bearing.
    profile: GitProfile = {
        "directory": "github.com-personal",
        "name": "J",
        "email": "j@example.com",
        "extra_directories": ["~/plans", str(_ROOT / "srv" / "notes")],
    }
    expected = [PROJECTS_ROOT / "github.com-personal", Path.home() / "plans", _ROOT / "srv" / "notes"]
    assert include_scopes(profile) == expected
