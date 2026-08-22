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
        "cleanup",
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


def test_import_repo_tasks_modules_returns_real_modules_when_available():
    configs, dev_env, docs, quality = tasks._import_repo_tasks_modules()  # pyright: ignore[reportPrivateUsage]
    assert configs is not None
    assert dev_env is not None
    assert docs is not None
    assert quality is not None


def test_import_repo_tasks_modules_degrades_to_all_none_when_missing():
    result = tasks._import_repo_tasks_modules(simulate_missing=True)  # pyright: ignore[reportPrivateUsage]
    assert result == (None, None, None, None)
