"""Container distribution path: bootstrap-devcontainer.sh's default tag profile, the generated
docs block, and a read-only smoke check — see docs/dev-container.md.
"""

import os
from pathlib import Path

from invoke import task

from . import phases, util
from . import setup as setup_tasks

_DOC_PATH = Path(__file__).parent.parent / "docs" / "dev-container.md"

# Single source of truth for the recommended container tag exclusion — consumed by
# bootstrap-devcontainer.sh (via print_exclude_tags below, since bash can't import this), by
# render_docs()'s generated table, and by check()'s dry run.
CONTAINER_EXCLUDE_TAGS = ["gui", "workstation", "corporate", "ide", "gnome"]

_TAG_DESCRIPTIONS = [
    ("gui", "Wayland/X11 apps, desktop tools, browsers"),
    ("workstation", "Hardware sensors (`lm-sensors`), local terminal multiplexer (`tmux`), **Docker**"),
    ("corporate", "Webex, Citrix, and other work-specific tools"),
    ("ide", "Full IDEs and their support profiles (`vscode`, `jetbrains-toolbox`)"),
    ("gnome", "GNOME Shell extensions and GNOME-only `xdg-desktop-portal` backends"),
]


@task
def print_exclude_tags(c):
    """Print CONTAINER_EXCLUDE_TAGS, comma-separated, no surrounding text.

    Machine-readable — bootstrap-devcontainer.sh calls this (after it's bootstrapped `inv` onto
    PATH) to resolve its `--exclude-tags` default, instead of hardcoding a second copy of the
    list in bash. Not meant for interactive use; see `inv devcontainer.check`/`render-docs` for
    human-facing output.
    """
    print(",".join(CONTAINER_EXCLUDE_TAGS))


def _tag_table() -> str:
    # Pre-padded to dprint's own GFM table style (column-aligned, `-`-padded separator row) so the
    # generated block is already a fixed point of `inv quality.fix`'s dprint pass — otherwise
    # dprint would re-pad it on every quality.fix run, which render-docs would then see as changed
    # and "fix" back to unpadded, forever disagreeing with dprint about the "idempotent" output.
    headers = ("Tag", "Excludes")
    rows = [(f"`{tag}`", desc) for tag, desc in _TAG_DESCRIPTIONS]
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(len(headers))]

    def fmt_row(cells: tuple[str, ...]) -> str:
        return "| " + " | ".join(cell.ljust(width) for cell, width in zip(cells, widths, strict=True)) + " |"

    sep_row = "| " + " | ".join("-" * width for width in widths) + " |"
    return "\n".join([fmt_row(headers), sep_row, *(fmt_row(row) for row in rows)])


def _generated_content() -> str:
    tags_csv = ",".join(CONTAINER_EXCLUDE_TAGS)
    return (
        f"{_tag_table()}\n\n"
        "Example — this is the default (equivalent to omitting `--exclude-tags`; see "
        "`bootstrap-devcontainer.sh`'s own default resolution via "
        "`inv devcontainer.print-exclude-tags`):\n\n"
        "```json\n"
        "{\n"
        '  "image": "mcr.microsoft.com/devcontainers/base:ubuntu-24.04",\n'
        '  "postCreateCommand": "bash bootstrap-devcontainer.sh"\n'
        "}\n"
        "```\n\n"
        f"To override: `bash bootstrap-devcontainer.sh --exclude-tags {tags_csv}`"
    )


@task
def render_docs(c):
    """Regenerate the tag-table + example block in docs/dev-container.md from
    CONTAINER_EXCLUDE_TAGS/_TAG_DESCRIPTIONS (HTML-comment-marked — see util.MarkerStyle.HTML,
    since a '#'-prefixed marker would render as a Markdown heading). Run after changing either so
    the doc can't silently drift.
    """
    content = _generated_content()
    if util.DRY_RUN:
        text = _DOC_PATH.read_text() if _DOC_PATH.exists() else ""
        _, status = util.ensure_block_text(text, "devcontainer-tags", content, style=util.MarkerStyle.HTML)
        print(f"[devcontainer] render-docs: {util.ok_label(status == util.BlockStatus.OK)}")
        return
    status = util.ensure_block(_DOC_PATH, "devcontainer-tags", content, style=util.MarkerStyle.HTML)
    print(f"[devcontainer] render-docs: {status.value}")


@task
def check(c):
    """Read-only dry run for the container distribution path: reports what `inv setup`'s
    packages+shell phases would do under the recommended container tag profile, without running
    anything for real — same shape as `inv wsl.check`. Both bootstrap-devcontainer.sh and
    docker/Dockerfile ultimately call `inv setup`, so this dry-runs the exact same phase lists
    (tasks/setup.py's PACKAGES_PHASE/SHELL_PHASE).
    """
    print(
        "[devcontainer] systemd: "
        + (
            "present (unexpected in a real container — inv setup would still run the "
            "system/desktop phases; that's fine on a systemd-enabled container, just not "
            "the common case)"
            if util.has_systemd()
            else "absent ✓ — inv setup self-skips the system/desktop phases (util.has_systemd())"
        )
    )
    print(f"[devcontainer] apt/dpkg: {util.ok_label(util.command_exists('apt') and util.command_exists('dpkg'))}")

    env_override = os.environ.get("PULSE_EXCLUDE_TAGS")
    tags = env_override or ",".join(CONTAINER_EXCLUDE_TAGS)
    print(
        f"[devcontainer] PULSE_EXCLUDE_TAGS={tags}"
        + ("" if env_override else "  (container default from CONTAINER_EXCLUDE_TAGS — not overridden)")
    )

    saved = os.environ.get("PULSE_EXCLUDE_TAGS")
    os.environ["PULSE_EXCLUDE_TAGS"] = tags
    try:
        print(phases._probe(c, setup_tasks.PACKAGES_PHASE), end="")
        print(phases._probe(c, setup_tasks.SHELL_PHASE), end="")
    finally:
        if saved is None:
            os.environ.pop("PULSE_EXCLUDE_TAGS", None)
        else:
            os.environ["PULSE_EXCLUDE_TAGS"] = saved
