"""Unit tests for tasks/__init__.py: the namespace builds successfully with every expected
top-level collection name, and _import_repo_tasks_modules' degraded branch (repo_tasks not
importable, e.g. bootstrap.sh's zero-install path) is exercised directly via its
simulate_missing parameter rather than faking an import failure via sys.modules patching."""

import tasks


def test_namespace_contains_every_top_level_collection():
    names = set(tasks.namespace.collections.keys())
    expected = {
        "ai",
        "allowlist",
        "apt",
        "certs",
        "clean",
        "deploy",
        "devcontainer",
        "docker",
        "fonts",
        "git",
        "gnome",
        "identity",
        "ide",
        "proxy",
        "python",
        "screenshot",
        "ssh",
        "system",
        "tools",
        "node",
        "verify",
        "wsl",
        "zsh",
    }
    assert expected <= names


def test_namespace_has_setup_as_bare_top_level_task():
    assert "setup" in tasks.namespace.task_names


def test_namespace_publishes_repo_tasks_test_namespace():
    test_collection = tasks.namespace.collections.get("test")
    assert test_collection is not None
    assert {"unit", "integration", "smoke", "regression", "all"} <= set(test_collection.task_names)


def test_import_repo_tasks_modules_returns_real_modules_when_available():
    modules = tasks._import_repo_tasks_modules()  # pyright: ignore[reportPrivateUsage]
    assert len(modules) == 6
    assert all(module is not None for module in modules)


def test_import_repo_tasks_modules_degrades_to_all_none_when_missing():
    result = tasks._import_repo_tasks_modules(simulate_missing=True)  # pyright: ignore[reportPrivateUsage]
    assert result == (None,) * 6
