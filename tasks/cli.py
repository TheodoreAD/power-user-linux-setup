"""The standalone shim's entry point: PULSE's machine-administration tasks, and nothing else.

`inv` inside the checkout keeps showing everything — this repo's own tasks plus the eight
collections borrowed from repo_tasks. The shim installed by `[project.scripts]` shows the subset
that administers a *machine*, so `quality`, `test` and the rest of the dev loop are absent, and so
are this repo's own authoring tasks (`catalog.render-*`, `allowlist.extract`, …).

**Both namespaces come from `tasks.namespace`**, subtracting rather than re-listing. A parallel list
of what to publish drifts the moment a task is added, and it drifts silently in the worse direction:
a new repo-authoring task would ship to every machine, or a new administration task would be missing
from the tool with nothing to say why. What is subtracted is recorded where it is created — the
borrowed collections by `tasks.BORROWED_COLLECTIONS` as they are added, and the development tasks by
`@util.dev_only` on the task itself.

`Program(namespace=…)` also means the shim never looks for a `tasks/` directory at all: invoke skips
disk discovery entirely when it is handed a namespace, so the command works from any directory
without `-r` and without caring what the cwd contains. The repo it reads its own inputs from is the
one this module was imported out of — which is why the tool must be installed `--editable`, so that
anchor stays on the checkout instead of a copy inside the tool's own venv.
"""

from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from typing import TypeAlias, cast

from invoke import Collection, Program, Task

from . import BORROWED_COLLECTIONS, namespace, util

_DISTRIBUTION = "power-user-linux-setup"

# `Collection.tasks` and `.collections` are `Lexicon`s — dict subclasses invoke leaves unannotated,
# so every value read out of one arrives as Unknown and `failOnWarnings` stops the gate. The two
# readers below are the only places this module touches them.
AnyTask: TypeAlias = Task[Callable[..., object]]


def _tasks_of(collection: Collection) -> dict[str, AnyTask]:
    return cast("dict[str, AnyTask]", collection.tasks)


def _collections_of(collection: Collection) -> dict[str, Collection]:
    return cast("dict[str, Collection]", collection.collections)


def _version() -> str:
    """The installed distribution's version, or a marker when running from a source tree that was
    never installed (the test suite, and `python -c 'import tasks.cli'`)."""
    try:
        return version(_DISTRIBUTION)
    except PackageNotFoundError:
        return "0.0.0+source"


def production_namespace(source: Collection | None = None) -> Collection:
    """`source` minus the borrowed collections and minus every `@util.dev_only` task.

    A collection left with no tasks is dropped rather than published empty, which is what makes a
    wholly-development collection like `catalog` disappear without being named here.
    """
    source = namespace if source is None else source
    production = Collection()
    for name, task in _tasks_of(source).items():
        if not util.is_dev_only(task):
            production.add_task(task, name=name)
    for name, collection in _collections_of(source).items():
        if name in BORROWED_COLLECTIONS:
            continue
        kept = Collection()
        for task_name, task in _tasks_of(collection).items():
            if not util.is_dev_only(task):
                kept.add_task(task, name=task_name)
        if _tasks_of(kept):
            production.add_collection(kept, name=name)
    return production


# `binary` is deliberately not passed: invoke falls back to the name the shim was actually invoked
# as, so help output and completion follow `[project.scripts]` rather than repeating it here.
program = Program(namespace=production_namespace(), version=_version())


def main() -> None:
    program.run()
