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

import sys
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TypeAlias, cast

from invoke import Collection, Program, Task

from . import BORROWED_COLLECTIONS, namespace, util

_DISTRIBUTION = "power-user-linux-setup"

_REPO_ROOT = Path(__file__).parent.parent

# The checkout-side inputs the machine-administration tasks ultimately read: `setup.toml` is the
# manifest, `config/` holds the sources `deploy` writes into the home directory. Neither ships in
# the wheel, deliberately — see the module docstring.
_CHECKOUT_INPUTS = ("setup.toml", "config")

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


def _require_checkout(root: Path | None = None) -> None:
    """Fail with a sentence, rather than wherever the first task happens to read a missing file.

    The shim is installed `--editable`, so it resolves the checkout at run time instead of carrying
    a copy of it. Probed 2026-09-08: every *upgrade* path holds that anchor — `uv tool upgrade`,
    `--all`, `--reinstall`, a Python bump, and a `uv self update` across the 0.11 → 0.12 boundary,
    in both directions — which leaves a moved or gutted checkout as the only way this breaks.

    Scope, because half the failure is out of reach from here: this catches a checkout that still
    imports but no longer has its inputs. A checkout that is *gone* fails earlier and harder, in the
    console script's own `from tasks.cli import main`, with a bare `No module named 'tasks'` that no
    code of ours can intercept. `uv tool upgrade` is what names the path in that case, refusing with
    `Distribution not found at: file:///…`.
    """
    root = _REPO_ROOT if root is None else root
    missing = [name for name in _CHECKOUT_INPUTS if not (root / name).exists()]
    if not missing:
        return
    # Not `_DISTRIBUTION`: the shim answers to two names, and the one the user typed is the one
    # worth echoing back — the same reason `Program` is built without an explicit `binary`.
    command = Path(sys.argv[0]).name or _DISTRIBUTION
    raise SystemExit(
        f"{command}: the power-user-linux-setup checkout this command reads is not intact.\n"
        f"  expected at: {root}\n"
        f"  missing:     {', '.join(missing)}\n"
        "\n"
        "This tool is installed with 'uv tool install --editable', so it resolves that path on\n"
        "every run rather than carrying its own copy. If the repo moved, re-point the install:\n"
        "  uv tool install --force --editable <path to the checkout>"
    )


def main() -> None:
    _require_checkout()
    program.run()
