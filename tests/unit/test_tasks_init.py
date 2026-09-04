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


def test_namespace_publishes_repo_tasks_deps_namespace():
    """`deps.check` is in `quality.check`'s pre-chain, so the gate runs it either way — this is
    about being able to invoke it on its own when it fails."""
    deps_collection = tasks.namespace.collections.get("deps")
    assert deps_collection is not None
    assert {"check", "lock", "audit"} <= set(deps_collection.task_names)


def test_namespace_publishes_repo_tasks_ci_namespace():
    """`ci.status` is the only thing here that reads a run's *annotations*, and an annotation on a
    green run is the sole signal for a deprecation — `actions/checkout@v4` carried one for eleven
    months while CI passed. The namespace went unpublished long enough that a whole CI sweep was
    done with raw `gh api` calls instead."""
    ci_collection = tasks.namespace.collections.get("ci")
    assert ci_collection is not None
    assert {"status", "check-actions"} <= set(ci_collection.task_names)


def test_import_repo_tasks_modules_returns_real_modules_when_available():
    modules = tasks._import_repo_tasks_modules()
    assert len(modules) == 8
    assert all(module is not None for module in modules)


def test_import_repo_tasks_modules_degrades_to_all_none_when_missing():
    result = tasks._import_repo_tasks_modules(simulate_missing=True)
    assert result == (None,) * 8
