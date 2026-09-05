"""Unit tests for tasks/__init__.py: the namespace builds successfully with every expected
top-level collection name, and _import_repo_tasks_modules' degraded branch (repo_tasks not
importable, e.g. bootstrap.sh's zero-install path) is exercised directly via its
simulate_missing parameter rather than faking an import failure via sys.modules patching."""

import pytest
from invoke import Collection

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


def test_report_mode_configures_the_namespace_when_the_env_var_is_set(monkeypatch: pytest.MonkeyPatch):
    """Exporting REPO_TASKS_RUN_REPORT is not sufficient on its own — repo_tasks swaps the runner on
    its own collection, which this repo does not use — so the wiring here is the whole mechanism, and
    its absence is silent: the gate just keeps printing stock invoke output."""
    monkeypatch.setenv("REPO_TASKS_RUN_REPORT", "1")
    collection = Collection()
    assert tasks._configure_report_mode(collection) is True
    assert collection.configuration()["runners"]["local"] is not None


def test_report_mode_leaves_the_namespace_alone_when_the_env_var_is_unset(monkeypatch: pytest.MonkeyPatch):
    """Stock invoke for a human at a terminal and for CI: the departure is opt-in, and off means the
    collection is not touched at all rather than configured with a passthrough."""
    monkeypatch.delenv("REPO_TASKS_RUN_REPORT", raising=False)
    collection = Collection()
    assert tasks._configure_report_mode(collection) is False
    assert "runners" not in collection.configuration()


def test_report_mode_degrades_when_repo_tasks_is_missing(monkeypatch: pytest.MonkeyPatch):
    """bootstrap.sh's zero-install path, where the variable can be set and repo_tasks is absent."""
    monkeypatch.setenv("REPO_TASKS_RUN_REPORT", "1")
    collection = Collection()
    assert tasks._configure_report_mode(collection, simulate_missing=True) is False
    assert "runners" not in collection.configuration()
