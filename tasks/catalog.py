"""The published package catalog: docs/packages.md's table, generated from setup.toml.

`setup.toml` is 90KB and never rendered anywhere, so the curated tool list — the most attractive
thing this repo has — was invisible to anyone who had not opened the file. This turns it into one
table on the site.

Generation only, never installation: nothing here reads or writes the machine. Same shape as
`inv devcontainer.render-docs` (util.ensure_block with the HTML marker style, output committed,
run deliberately rather than from the quality gate) — see ~/AGENTS.md's "Regenerating a file from
a canonical source".
"""

import re
from pathlib import Path

from invoke import Context, task

from . import util

_DOC_PATH = Path("docs/packages.md")
_BLOCK = "package-catalog"

# A sentence ends at .!? followed by whitespace and something that starts a new sentence. Requiring
# the capital (or a backtick/quote/paren, which is how several descriptions open a sentence) is
# what keeps `e.g. `, `vX.Y. ` and `~/.local/share/cargo ` from splitting mid-thought.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z`\"(])")


def _summary(description: str) -> str:
    """The first sentence of a `description`, whitespace-collapsed.

    setup.toml's descriptions are written for whoever maintains the entry, so several carry a
    paragraph of rationale after the opening line. The catalog wants the opening line: it is the
    part that says what the thing is, and it is the part a reader scanning 97 rows can use. The
    rest stays in setup.toml, where the person changing the entry reads it.
    """
    collapsed = " ".join(description.split())
    return _SENTENCE_END.split(collapsed)[0] if collapsed else ""


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


def _generated_content() -> str:
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


@task
def render(c: Context):
    """Regenerate docs/packages.md's catalog table from setup.toml.

    Run it after adding, removing or re-describing a package, and commit the result. Deliberately
    not wired into `inv quality.fix`/`check`: the output is reviewed and committed like any other
    change, and a unit test fails when the committed block is stale, so nothing has to remember.
    """
    content = _generated_content()
    if util.DRY_RUN:
        text = _DOC_PATH.read_text() if _DOC_PATH.exists() else ""
        _, status = util.ensure_block_text(text, _BLOCK, content, style=util.MarkerStyle.HTML)
        print(f"[catalog] render: {util.ok_label(status == util.BlockStatus.OK)}")
        return
    status = util.ensure_block(_DOC_PATH, _BLOCK, content, style=util.MarkerStyle.HTML)
    print(f"[catalog] render: {status.value} ({len(catalog_rows())} packages)")
