"""The two generated reference pages: docs/packages.md and docs/tasks.md.

`setup.toml` is 90KB and `inv --list` runs on a machine that already has this repo set up, so the
two things a reader most wants to know — what does it install, and what can I run — were both
invisible from the site. Each is a table generated from the thing it describes.

Generation only, never installation: nothing here reads or writes the machine. Same shape as
`inv devcontainer.render-docs` (util.ensure_block with the HTML marker style, output committed, run
deliberately rather than from the quality gate) — see ~/AGENTS.md's "Regenerating a file from a
canonical source".
"""

import re
from pathlib import Path
from typing import cast

from invoke import Context, task

from . import util

_PACKAGES_DOC = Path("docs/packages.md")
_PACKAGES_BLOCK = "package-catalog"
_TASKS_DOC = Path("docs/tasks.md")
_TASKS_BLOCK = "task-index"

# A sentence ends at .!? followed by whitespace and something that starts a new sentence. Requiring
# the capital (or a backtick/quote/paren, which is how several descriptions open a sentence) is
# what keeps `e.g. `, `vX.Y. ` and `~/.local/share/cargo ` from splitting mid-thought.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z`\"(])")


def _summary(text: str) -> str:
    """The first sentence of `text`, whitespace-collapsed.

    Both sources here are written for whoever maintains the entry — a setup.toml description or a
    task docstring — so several carry a paragraph of rationale after the opening line. A generated
    table wants the opening line: it is the part that says what the thing is, and it is the part a
    reader scanning a hundred rows can use. The rest stays where it was, for whoever changes it.
    """
    collapsed = " ".join(text.split())
    return _SENTENCE_END.split(collapsed)[0] if collapsed else ""


# How long a task summary may be before the table stops being scannable. Only 13 of 132 first
# sentences exceed it, and two of those come from `repo-tasks`.
_TASK_SUMMARY_LIMIT = 200


def _clip(summary: str) -> str:
    """A first sentence short enough for a table cell.

    Unlike a package description, a task docstring cannot always be fixed at the source: several of
    the longest arrive from `repo-tasks`, and this repo may not edit that one. So the page clips,
    preferring the sentence's own first clause — these docstrings almost all open with a summary,
    an em dash, and then the detail — and falling back to a hard cut only when there is no such
    boundary. `inv --help <task>` prints the whole docstring either way.
    """
    if len(summary) <= _TASK_SUMMARY_LIMIT:
        return summary
    clause = summary.split(" — ", maxsplit=1)[0]
    if 40 < len(clause) <= _TASK_SUMMARY_LIMIT:
        return clause
    return summary[:_TASK_SUMMARY_LIMIT].rsplit(" ", 1)[0] + "…"


def catalog_rows() -> list[tuple[str, str, str, str]]:
    """(name, summary, tags, method) per catalogued package, name-sorted.

    Two exclusions, both deliberate. A package with `enabled = false` is not installed on any
    machine, so listing it would describe something nobody gets. A package with no `method` installs
    nothing at all — `[packages.repo-tasks]` exists only to carry a `claude_permissions_allow`
    grant — and a catalog answering "what do I get" is the wrong place to explain that.

    Tags are shown rather than grouped on: a package carries several, and any grouping either
    invents a primary tag or lists the package once per tag.
    """
    packages = util.load_config().get("packages", {})
    return sorted(
        (
            name,
            _summary(cfg.get("description", "")),
            ", ".join(f"`{tag}`" for tag in cfg.get("tags", [])),
            f"`{cfg['method']}`",
        )
        for name, cfg in packages.items()
        if cfg.get("enabled", True) and "method" in cfg
    )


def task_rows() -> list[tuple[str, str]]:
    """(dotted task name, first sentence of its docstring) for every published task, sorted.

    The namespace is imported lazily: `tasks/__init__.py` imports this module to build that very
    namespace, so importing it at module scope would be a cycle. By the time a task runs, the
    package is fully imported and this is a dict lookup.

    Tasks reaching this repo from `repo-tasks` (`quality.*`, `test.*`, `docs.*`, `deps.*`, ...) are
    included, because they are part of the surface `inv --list` shows here — the page describes
    this repo's task surface, not only the tasks defined in this directory.
    """
    from tasks import namespace  # noqa: PLC0415 — lazy by necessity, see the docstring

    def docstring(name: str) -> str:
        # invoke's Task is untyped enough that `__doc__` comes back as Any; narrow it here rather
        # than letting that Any spread into the rest of the module.
        return cast(str | None, namespace[name].__doc__) or ""

    return sorted((name, _clip(_summary(docstring(name)))) for name in namespace.task_names)


def _packages_table() -> str:
    """The table, and nothing else.

    Prose deliberately stays outside the block, in the hand-written part of the page. dprint fills
    paragraphs to `dprint.json`'s markdown lineWidth, so a generated sentence has to be wrapped
    exactly as dprint would wrap it or the two rewrite each other forever — and a sentence
    containing the package count would re-wrap differently the day the count changes width. A
    table has no such problem: util.markdown_table already emits dprint's own padded form.
    """
    return util.markdown_table(
        ("Package", "What it is", "Tags", "Method"),
        [(f"`{name}`", summary, tags, method) for name, summary, tags, method in catalog_rows()],
    )


def _tasks_table() -> str:
    return util.markdown_table(
        ("Task", "What it does"),
        [(f"`inv {name}`", summary) for name, summary in task_rows()],
    )


def _render(doc: Path, block: str, content: str, label: str) -> None:
    if util.DRY_RUN:
        text = doc.read_text() if doc.exists() else ""
        _, status = util.ensure_block_text(text, block, content, style=util.MarkerStyle.HTML)
        print(f"[catalog] {label}: {util.ok_label(status == util.BlockStatus.OK)}")
        return
    status = util.ensure_block(doc, block, content, style=util.MarkerStyle.HTML)
    print(f"[catalog] {label}: {status.value}")


@task
def render_packages(c: Context):
    """Regenerate docs/packages.md's catalog table from setup.toml.

    Run it after adding, removing or re-describing a package, and commit the result. Deliberately
    not wired into `inv quality.fix`/`check`: the output is reviewed and committed like any other
    change, and a unit test fails when the committed block is stale, so nothing has to remember.
    """
    _render(_PACKAGES_DOC, _PACKAGES_BLOCK, _packages_table(), f"render-packages ({len(catalog_rows())})")


@task
def render_tasks(c: Context):
    """Regenerate docs/tasks.md's task index from the invoke namespace.

    Run it after adding, renaming or re-describing a task — including one that arrives from
    `repo-tasks`, since a dependency bump can change this repo's task surface without any commit
    here. Same reviewed-and-committed contract as `render-packages`, with its own drift test.
    """
    _render(_TASKS_DOC, _TASKS_BLOCK, _tasks_table(), f"render-tasks ({len(task_rows())})")
