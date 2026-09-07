"""Unit tests for tasks/cli.py: the standalone shim publishes machine-administration tasks and
nothing from repo_tasks or from this repo's own authoring pipeline.

The point of most of these is drift rather than correctness-today. Both namespaces are derived from
one source, so the failure mode to guard is a *new* task arriving on the wrong side of the line
silently — which is why the subset relationship and the marker-count are asserted rather than only
the current membership."""

from invoke import Collection, task

import tasks
from tasks import cli, util


def _flat(collection: Collection) -> set[str]:
    """Every `collection.task` identifier, one level deep — which is as deep as this repo nests."""
    names = set(cli._tasks_of(collection))
    for outer, inner in cli._collections_of(collection).items():
        names |= {f"{outer}.{name}" for name in cli._tasks_of(inner)}
    return names


def test_production_namespace_is_a_subset_of_the_full_one():
    """The shim may only ever take away. Anything it publishes that `inv` does not is a task nobody
    can run in the checkout, which is the one direction no derivation should be able to produce."""
    assert _flat(cli.production_namespace()) <= _flat(tasks.namespace)


def test_no_borrowed_collection_reaches_the_shim():
    """These would also vanish by accident — a tool venv resolves only `dependencies`, and
    repo-tasks is a dev-group entry — but the accident is invisible and reversible by an
    `--with repo-tasks` nobody would think twice about. The exclusion is declared, so it is tested."""
    published = set(cli.production_namespace().collections)
    assert tasks.BORROWED_COLLECTIONS
    assert published.isdisjoint(tasks.BORROWED_COLLECTIONS)


def test_development_tasks_are_absent():
    published = _flat(cli.production_namespace())
    for name in (
        "catalog.render-packages",
        "catalog.render-tasks",
        "devcontainer.render-docs",
        "allowlist.extract",
        "allowlist.classify",
        "allowlist.review",
        "allowlist.render",
        "allowlist.reconfirm",
        "allowlist.check-man-deps",
    ):
        assert name not in published, name


def test_a_wholly_development_collection_disappears_rather_than_publishing_empty():
    """`catalog` is both its tasks, so dropping empty collections is what removes it — no list here
    names it, and none should."""
    assert "catalog" in tasks.namespace.collections
    assert "catalog" not in cli.production_namespace().collections


def test_machine_administration_tasks_are_present():
    published = _flat(cli.production_namespace())
    for name in (
        "setup",
        "deploy.all",
        "deploy.status",
        "ai.install-skills",
        "verify.all",
        "home.list-claims",
        "net.check",
    ):
        assert name in published, name


def test_the_allowlist_collection_keeps_only_its_machine_facing_tasks():
    """`apply` writes ~/.claude/settings.json, and `status`/`check-coverage` answer "what would
    apply do" without needing the repo. The other six write into cli-allowlist/ in the checkout."""
    published = cli._collections_of(cli.production_namespace())["allowlist"]
    assert set(cli._tasks_of(published)) == {"apply", "status", "check-coverage"}


def test_dev_only_marks_the_function_and_survives_the_task_wrapper():
    """`@task` wraps the function, and functools.update_wrapper copies its __dict__ across — so the
    marker has to be readable off the Task, which is what the namespace builder sees."""

    @task
    @util.dev_only
    def marked(c):  # pragma: no cover - never executed, only inspected
        pass

    @task
    def unmarked(c):  # pragma: no cover - never executed, only inspected
        pass

    assert util.is_dev_only(marked)
    assert not util.is_dev_only(unmarked)


def test_version_falls_back_when_the_distribution_is_not_installed():
    """The shim is importable from a source tree that was never `pip install`ed — the test suite is
    exactly that case — and a PackageNotFoundError there would take down `--version`."""
    assert cli._version()


def test_program_is_built_with_a_bundled_namespace():
    """This is what makes the shim independent of cwd: invoke skips disk discovery entirely when it
    already has a namespace, so there is no `tasks/` directory to find and no `-r` to pass."""
    assert cli.program.namespace is not None
