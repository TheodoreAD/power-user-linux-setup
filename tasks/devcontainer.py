"""Container distribution path: bootstrap-devcontainer.sh's default tag profile, the generated
docs block, a read-only smoke check, and the host-side credential-mount helper — see
docs/dev-container.md.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from invoke import Context, task

from . import phases, ui, util
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
def print_exclude_tags(c: Context):
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
    # Pre-wrapped at dprint.json's markdown lineWidth (100), for the same reason _tag_table() is
    # pre-padded: whatever this emits, `dprint fmt` reformats, and render_docs then sees its own
    # output as changed and rewrites it — the two disagree forever about the "idempotent" result.
    # The table had that treatment from the start; this prose paragraph did not, so the block was
    # stale in git the whole time and no run could settle it (found 2026-09-01 by the drift test in
    # tests/unit/test_devcontainer.py, which failed on its first execution).
    return (
        f"{_tag_table()}\n\n"
        "Example — this is the default (equivalent to omitting `--exclude-tags`; see\n"
        "`bootstrap-devcontainer.sh`'s own default resolution via `inv devcontainer.print-exclude-tags`):\n\n"
        "```json\n"
        "{\n"
        '  "image": "mcr.microsoft.com/devcontainers/base:ubuntu-24.04",\n'
        '  "postCreateCommand": "bash bootstrap-devcontainer.sh"\n'
        "}\n"
        "```\n\n"
        f"To override: `bash bootstrap-devcontainer.sh --exclude-tags {tags_csv}`"
    )


@task
def render_docs(c: Context):
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
def check(c: Context):
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
        print(phases.probe(c, setup_tasks.PACKAGES_PHASE), end="")
        print(phases.probe(c, setup_tasks.SHELL_PHASE), end="")
    finally:
        if saved is None:
            os.environ.pop("PULSE_EXCLUDE_TAGS", None)
        else:
            os.environ["PULSE_EXCLUDE_TAGS"] = saved


# ---------------------------------------------------------------------------
# inv devcontainer.print-mounts — host-side credential/config mount helper. See docs/dev-container.md's
# "Mounting host directories" section.

_DEFAULT_CONTAINER_HOME = "/home/vscode"

_WSL_SSH_AGENT_CAVEAT = (
    "WSL2 + Docker Desktop's SSH-agent forwarding into a container has multiple open, unresolved "
    "upstream issues (microsoft/vscode-remote-release#3902, #8689, #2925). If forwarding doesn't "
    "work, the reliable fix is running `ssh-agent` natively inside WSL2 itself, not the "
    "Windows-side agent."
)
_SSH_DIR_CAVEAT = "direct mount, read-write — private key bytes become visible inside the container."
_GNUPG_CAVEAT = "GPG agent/pinentry forwarding is known-fiddly — not solved here, just offered opt-in."
_CERT_BUNDLE_CAVEAT_TEMPLATE = (
    "mounted at the identical absolute host path so identity.toml's [certs] bundle field keeps "
    "resolving correctly inside the container with no changes needed to certs.py."
)


@dataclass(frozen=True)
class MountCandidate:
    """One discoverable host directory/socket offered by `inv devcontainer.print-mounts`. `source` is
    the devcontainer.json mount "source=" value as-is (already using ${localEnv:...} where that
    makes the fragment portable across machines). `target` is an absolute container path when
    fixed (ssh-agent socket, the corporate cert bundle — same path as the host); otherwise None,
    and `target_suffix` is appended to the user-provided container home instead.
    """

    id: str
    label: str
    source: str
    target: str | None
    target_suffix: str | None
    readonly: bool
    default: bool
    remote_env: dict[str, str] | None = None
    caveat: str | None = None


def _resolve_cert_bundle_paths(identity_toml: Path | None) -> list[Path]:
    """[certs] bundle from identity_toml (a single string or a list) — same resolution shape as
    tasks/certs.py's _resolve_paths(), reimplemented here (not calling util.load_certs_override(),
    which is hardcoded to util.IDENTITY_PATH and @cache'd) so tests can point it at a fabricated
    identity.toml under a tmp_path fixture instead of the real ~/.config/power-user-linux-setup/identity.toml.
    """
    if not identity_toml or not identity_toml.exists():
        return []
    data = cast(util.Identity, util.load_toml(identity_toml))
    raw = data.get("certs", {}).get("bundle")
    if not raw:
        return []
    if isinstance(raw, str):
        return [Path(raw).expanduser()]
    return [Path(p).expanduser() for p in raw]


def _discover_candidates(
    home: Path,
    identity_toml: Path | None,
    ssh_auth_sock: str | None,
    *,
    is_wsl: bool = False,
) -> list[MountCandidate]:
    """Pure(ish) discovery: every check is a Path.exists() under `home`/`identity_toml`, no other
    I/O — lets tests fabricate a tmp_path $HOME with whichever subset of dotfiles present. Returns
    only candidates actually discoverable on this host; the interactive mounts() task prompts one
    ui.ask() per entry returned here, nothing for entries that don't apply at all.
    """
    candidates: list[MountCandidate] = []

    sock_exists = bool(ssh_auth_sock and Path(ssh_auth_sock).exists())
    if sock_exists:
        candidates.append(
            MountCandidate(
                id="ssh-agent",
                label="SSH agent forwarding ($SSH_AUTH_SOCK)",
                source="${localEnv:SSH_AUTH_SOCK}",
                target="/tmp/ssh-agent.sock",
                target_suffix=None,
                readonly=False,
                default=True,
                remote_env={"SSH_AUTH_SOCK": "/tmp/ssh-agent.sock"},
                caveat=_WSL_SSH_AGENT_CAVEAT if is_wsl else None,
            )
        )

    if (home / ".ssh").exists():
        candidates.append(
            MountCandidate(
                id="ssh-dir",
                label="~/.ssh (direct mount)",
                source="${localEnv:HOME}/.ssh",
                target=None,
                target_suffix="/.ssh",
                readonly=False,
                default=not sock_exists,
                caveat=_SSH_DIR_CAVEAT,
            )
        )

    if (home / ".config" / "power-user-linux-setup").exists():
        candidates.append(
            MountCandidate(
                id="pulse-identity",
                label="~/.config/power-user-linux-setup (identity.toml, PULSE config)",
                source="${localEnv:HOME}/.config/power-user-linux-setup",
                target=None,
                target_suffix="/.config/power-user-linux-setup",
                readonly=False,
                default=True,
            )
        )

    bundle_paths = [p for p in _resolve_cert_bundle_paths(identity_toml) if p.exists()]
    for i, bundle_path in enumerate(bundle_paths):
        suffix = "" if i == 0 else f"-{i}"
        candidates.append(
            MountCandidate(
                id=f"corporate-cert-bundle{suffix}",
                label=f"corporate CA bundle ({bundle_path})",
                source=str(bundle_path),
                target=str(bundle_path),
                target_suffix=None,
                readonly=True,
                default=True,
                caveat=_CERT_BUNDLE_CAVEAT_TEMPLATE,
            )
        )

    if (home / ".gitconfig").exists():
        candidates.append(
            MountCandidate(
                id="gitconfig",
                label="~/.gitconfig",
                source="${localEnv:HOME}/.gitconfig",
                target=None,
                target_suffix="/.gitconfig",
                readonly=True,
                default=True,
            )
        )

    if (home / ".gnupg").exists():
        candidates.append(
            MountCandidate(
                id="gnupg",
                label="~/.gnupg",
                source="${localEnv:HOME}/.gnupg",
                target=None,
                target_suffix="/.gnupg",
                readonly=False,
                default=False,
                caveat=_GNUPG_CAVEAT,
            )
        )

    for id_, dirname, target_suffix in (
        ("aws", ".aws", "/.aws"),
        ("kube", ".kube", "/.kube"),
        ("gcloud-config", "gcloud", "/.config/gcloud"),
        ("gh-config", "gh", "/.config/gh"),
    ):
        # aws/kube live directly under $HOME; gcloud/gh live under ~/.config/
        host_dir = home / dirname if id_ in ("aws", "kube") else home / ".config" / dirname
        if not host_dir.exists():
            continue
        candidates.append(
            MountCandidate(
                id=id_,
                label=f"~{target_suffix}",
                source="${localEnv:HOME}" + target_suffix,
                target=None,
                target_suffix=target_suffix,
                readonly=True,
                default=False,
            )
        )

    return candidates


def _render_mounts_json(selected: list[MountCandidate], container_home: str) -> str:
    """Render a ready-to-paste devcontainer.json fragment ({"mounts": [...], "remoteEnv": {...}})
    for the selected candidates — printed, never written; see mounts()'s docstring for why.
    """
    mounts_list: list[str] = []
    remote_env: dict[str, str] = {}
    for cand in selected:
        target = cand.target if cand.target is not None else f"{container_home}{cand.target_suffix}"
        flags = ",type=bind" + (",readonly" if cand.readonly else "")
        mounts_list.append(f"source={cand.source},target={target}{flags}")
        if cand.remote_env:
            remote_env.update(cand.remote_env)

    fragment: dict[str, object] = {"mounts": mounts_list}
    if remote_env:
        fragment["remoteEnv"] = remote_env
    return json.dumps(fragment, indent=2)


@task
def print_mounts(c: Context):
    """Host-side interactive helper: discover credential-shaped directories/sockets on this
    machine (~/.ssh or $SSH_AUTH_SOCK, ~/.config/power-user-linux-setup, the corporate CA bundle from
    identity.toml, ~/.gitconfig, ~/.gnupg, ~/.aws, ~/.kube, ~/.config/{gcloud,gh}) and print a
    ready-to-paste devcontainer.json "mounts"/"remoteEnv" fragment for whichever you select.

    Run this on the *host*, before `devcontainer up` / opening the folder in VS Code — mounts are
    fixed at container-creation time, postCreateCommand runs too late to add any. Never writes or
    edits any file (unlike render_docs) — specifically never auto-edits the shared, committed,
    CI-smoke-tested .devcontainer/devcontainer.json with one developer's personal host paths; you
    paste the printed fragment into whichever devcontainer.json you're actually using.
    """
    home = Path.home()
    candidates = _discover_candidates(home, util.IDENTITY_PATH, os.environ.get("SSH_AUTH_SOCK"), is_wsl=util.is_wsl())
    if not candidates:
        print("[devcontainer] nothing discoverable on this host to mount — nothing to do.")
        return

    ui.block(
        "Prints a devcontainer.json mounts/remoteEnv fragment for whichever of these you select "
        "below — never writes or edits any file. The current repo is already mounted automatically "
        "as the workspace folder by the devcontainer spec itself; this is only for credentials/"
        "config that live outside it.",
        label="devcontainer mounts",
    )

    selected: list[MountCandidate] = []
    for cand in candidates:
        if cand.caveat:
            ui.note(cand.caveat)
        if ui.ask(f"Mount {cand.label}?", default=cand.default):
            selected.append(cand)

    if not selected:
        print("[devcontainer] nothing selected.")
        return

    container_home = util.prompt_text("Container home directory", default=_DEFAULT_CONTAINER_HOME)
    print()
    print(_render_mounts_json(selected, container_home))
