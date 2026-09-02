import json
import os
import pwd
import shutil
import subprocess
import sys
import tempfile
import threading
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from pathlib import Path
from typing import NotRequired, Required, TypeAlias, TypedDict, cast, overload

from invoke import Context

DRY_RUN: bool = os.environ.get("PULSE_DRY_RUN", "").lower() in ("1", "true", "yes")

# The env-var form of `--yes` for the composite entry points (`inv setup`, `inv wsl.install`) that
# have no flag of their own. tasks/deploy.py's writer defaults to *not* overwriting a destination it
# can't prove it wrote, and util.confirm() returns that default when stdin isn't a terminal — so an
# unattended run (bootstrap-devcontainer.sh, a Dockerfile) that hits a pre-existing file would
# silently skip it. Set this to get the overwrite-and-say-so behavior instead.
ASSUME_YES: bool = os.environ.get("PULSE_ASSUME_YES", "").lower() in ("1", "true", "yes")

# The sudo prefix every task interpolates into its own `c.run(f"{util.SUDO} …")`. Rebound at
# runtime by ensure_sudo(), which is what makes the "no sudo call inside c.run may ever prompt"
# invariant hold — see that function for why prompting from inside invoke is unsafe at all.
#
# Empty when already root: `sudo` then isn't needed and, in a container built FROM a stock base
# image, often isn't even installed.
SUDO: str = "" if os.geteuid() == 0 else ("sudo -A" if os.environ.get("SUDO_ASKPASS") else "sudo")

_PULSE_WIDTH = 78

_PROC_VERSION = Path("/proc/version")
_CONFIG_PATH = Path(__file__).parent.parent / "setup.toml"

# Machine-local, out-of-repo state namespace shared by identity.toml and the applied-manifest
# files tasks/ai.py and tasks/allowlist.py each track their own writes to settings.json with.
# Deliberately the full repo name, not "pulse" — "~/.config/pulse" is PulseAudio's own real config
# dir, and this namespace used to collide with it silently before this rename.
PULSE_CONFIG_DIR = Path.home() / ".config" / "power-user-linux-setup"
PULSE_STATE_DIR = Path.home() / ".local" / "state" / "power-user-linux-setup"

IDENTITY_PATH = PULSE_CONFIG_DIR / "identity.toml"
OVERRIDES_PATH = PULSE_CONFIG_DIR / "overrides.toml"
CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"


# ---------------------------------------------------------------------------
# Shapes of the files this repo reads — setup.toml, identity.toml, overrides.toml, and the slice
# of ~/.claude/settings.json it writes. TypedDicts, not `dict[str, Any]`: every `cfg.get(...)`
# below resolves to a real type, so the checker sees a misspelled field or a `str` used as a
# `list` at the call site instead of erasing everything past the load. `total=False` throughout —
# setup.toml's header documents which fields each method needs, and the install tasks already
# treat every one as optional at runtime via `.get()`.
# ---------------------------------------------------------------------------

# A JSON document — recursive alias, spelled with `TypeAlias` because the 3.11 floor predates
# PEP 695's `type` statement.
Json: TypeAlias = "dict[str, Json] | list[Json] | str | int | float | bool | None"
JsonObject: TypeAlias = dict[str, Json]


class PathMapping(TypedDict):
    """A `{ src, dst }` pair — `config_files` (repo-relative src → home dst) and `symlinks`
    (installed binary → ~/.local/bin name) share the shape."""

    src: str
    dst: str


class SkillEntry(TypedDict, total=False):
    """One item of a package's `skills` list — see setup.toml's header for the two sources."""

    source: str
    path: str  # source = "local"
    repo: str  # source = "npx"
    names: list[str]
    agents: list[str]
    description: str


class StatusLine(TypedDict):
    """Claude Code's `statusLine` settings.json object, as declared by `claude_statusline`."""

    type: str
    command: str


class AgentsMdFragment(TypedDict, total=False):
    """One item of a package's `agents_md` list — a whole-`##`-section Markdown fragment of the
    assembled `~/AGENTS.md`, plus where it sits in the document.

    `order` is sparse by convention (10, 20, 30 …) so a fragment can be inserted between two
    existing ones without renumbering; it defaults to 50 so an undeclared order lands after the
    curated ones rather than silently at the top. Ties break on the declaring package's name, so
    two fragments at the same order still assemble deterministically rather than in whatever
    sequence `setup.toml`'s keys happen to iterate.
    """

    src: str
    order: int


class PackageConfig(TypedDict, total=False):
    """A `[packages.<name>]` section. Field-by-field reference: setup.toml's header comment."""

    # common
    description: str
    method: str
    enabled: bool
    tags: list[str]
    config_files: list[PathMapping]
    verify_cmd: str
    verify: bool
    zshrc: str
    zshenv: str
    zprofile: str
    skills: list[SkillEntry]
    agents_md: list[AgentsMdFragment]
    claude_permissions_allow: list[str]
    claude_additional_directories: list[str]
    claude_default_mode: str
    claude_statusline: StatusLine
    omz_plugin: str | list[str]
    cleanup_paths: list[str]
    check_cmd: str
    check_path: str
    # apt / apt-repo
    packages: list[str]
    symlinks: list[PathMapping]
    gpg_url: str
    gpg_path: str
    sources_path: str
    sources_entry: str
    # deb-github / deb-url / binary / archive
    repo: str
    tag: str
    tag_prefix: str
    asset: str
    url: str
    version_cmd: str
    version_url: str
    download_page: str
    download_url: str
    extract_to: str
    install_dir: str
    strip_components: int
    bin_pick: str
    bin_in_root: bool
    # uv-tool
    package: str
    python: str
    extras: list[str]
    # script
    script_url: str
    shell: str
    env: dict[str, str]
    single_binary: bool
    symlink_from: str
    post_install: str
    # git-clone / wrapper-script
    dest: str
    depth: int
    content_file: str
    assembled_from: str
    symlink_dest: str | list[str]
    # gnome-extension
    uuid: str
    ego_id: int
    dconf: dict[str, str]
    # apparmor-profile
    profile: str
    content: str
    # nvm ([packages.node])
    version: str
    global_packages: list[str]
    nvm_dir: str
    # [packages.oh-my-zsh]
    theme: str
    plugins: list[str]


class FontFamily(TypedDict, total=False):
    """One `[[settings.fonts.families]]` entry."""

    zip: Required[str]
    family: str | list[str]
    check: str
    legacy: str | list[str]


class FontsSettings(TypedDict, total=False):
    """`[settings.fonts]`. `family`/`family_mono`/`size` are the one place the font is named —
    everything else that needs it derives from them, including the four repo-side config files
    `inv fonts.render-configs` rewrites. `vscode` stays a passthrough for keys that aren't the
    font itself."""

    family: str
    family_mono: str
    family_short: str
    family_mono_short: str
    size: int
    vscode: dict[str, Json]
    families: list[FontFamily]


class Settings(TypedDict, total=False):
    uv_python_default: str
    uv_python_extra: list[str]
    uv_python_set_default: bool
    install_repo_tasks: bool
    fonts: FontsSettings


class SetupConfig(TypedDict):
    """setup.toml's top level."""

    packages: dict[str, PackageConfig]
    settings: NotRequired[Settings]


class GitProfile(TypedDict):
    """A `[[git_profiles]]` entry in identity.toml — see config/identity.toml.example."""

    directory: str
    name: str
    email: str


class SshHost(TypedDict):
    """A `[[ssh_hosts]]` entry in identity.toml."""

    user: str
    alias: str
    hostname: str
    email: str


class ProxySection(TypedDict, total=False):
    """identity.toml's optional `[proxy]` table — see docs/corporate-proxy.md."""

    host: str
    port: int | str
    noproxy: str


class CertsSection(TypedDict, total=False):
    """identity.toml's optional `[certs]` table — see docs/certs.md."""

    bundle: str | list[str]


class Identity(TypedDict, total=False):
    """identity.toml's top level."""

    git_profiles: list[GitProfile]
    ssh_hosts: list[SshHost]
    proxy: ProxySection
    certs: CertsSection


class PackageOverride(TypedDict, total=False):
    enabled: bool


class Overrides(TypedDict, total=False):
    """overrides.toml's top level — see load_overrides()."""

    packages: dict[str, PackageOverride]


class ClaudePermissions(TypedDict, total=False):
    """The `permissions` block of ~/.claude/settings.json — only the keys this repo writes."""

    allow: list[str]
    ask: list[str]
    additionalDirectories: list[str]
    defaultMode: str


class ClaudeSettings(TypedDict, total=False):
    """~/.claude/settings.json — only the keys this repo reads or writes. Every other key in the
    file rides along untouched; a TypedDict doesn't forbid extra keys at runtime."""

    permissions: ClaudePermissions
    statusLine: StatusLine


def load_toml(path: Path) -> object:
    """tomllib's `dict[str, Any]` result, surfaced as `object` so the one `cast` to the file's
    TypedDict happens at the loader and nothing downstream inherits an `Any`."""
    with path.open("rb") as f:
        return cast(object, tomllib.load(f))


def load_json(path: Path) -> object:
    """Same shape as load_toml for json.loads' `Any`."""
    return cast(object, json.loads(path.read_text()))


def parse_json(text: str) -> object:
    """json.loads for text already in hand (a subprocess's stdout, a JSONC file after comment
    stripping) — same `object`-not-`Any` contract as load_json."""
    return cast(object, json.loads(text))


def missing_fields(name: str, *keys: str) -> RuntimeError:
    """The error an install task raises when a `[packages.<name>]` section lacks a field its
    method requires. The caller's own `if "x" not in cfg or ...: raise` guard is what narrows
    `PackageConfig` for the checker; this just spells the message once."""
    return RuntimeError(f"[{name}] setup.toml section is missing required field(s): {', '.join(keys)}")


def ok_label(ok: bool) -> str:
    """The repo-wide "ok"/"MISSING" status word used in every task's dry-run and status output."""
    return "ok" if ok else "MISSING"


def markdown_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """A GFM table, pre-padded to dprint's own column-aligned style.

    The padding is not cosmetic. Anything a render task writes into a committed `docs/*.md` is
    reformatted by `inv quality.fix`'s dprint pass, and the render task then sees its own output as
    changed and rewrites it — the two disagree forever about the "idempotent" result unless the
    generator emits what dprint would. Emitting the padded form makes the block a fixed point of
    both.

    A `|` inside a cell is escaped, since it would otherwise open a column that isn't there.
    """
    escaped = [[cell.replace("|", "\\|") for cell in row] for row in rows]
    widths = [max([len(header), *(len(row[i]) for row in escaped)]) for i, header in enumerate(headers)]

    def fmt(cells: Sequence[str]) -> str:
        return "| " + " | ".join(cell.ljust(width) for cell, width in zip(cells, widths, strict=True)) + " |"

    separator = "| " + " | ".join("-" * width for width in widths) + " |"
    return "\n".join([fmt(headers), separator, *(fmt(row) for row in escaped)])


def is_wsl() -> bool:
    """True if running under any WSL version (1 or 2) — see tasks/wsl.py for version-specific
    checks and the rest of the WSL-aware tasks."""
    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
        return True
    try:
        return "microsoft" in _PROC_VERSION.read_text().lower()
    except FileNotFoundError:
        return False


def is_docker_desktop_wsl_integration() -> bool:
    """True if the `docker` CLI is present but there's no local `dockerd` — Docker Desktop's WSL
    integration, not a native install. In that case the daemon isn't running inside this distro at
    all (it's Windows-side), so docker.py's daemon.json/systemctl calls have nothing to act on —
    manage Docker Desktop's own settings from Windows instead. Previously duplicated independently
    in tasks/docker.py and tasks/wsl.py; factored out here so the two checks can't drift.
    """
    return command_exists("docker") and not command_exists("dockerd")


def current_user() -> str:
    """Best-effort real (non-root) username: SUDO_USER when running under sudo, else $USER,
    else the actual name of the current UID. The env-var-only version of this (duplicated
    across tasks/zsh.py, tasks/docker.py, tasks/next_steps.py before being factored out here)
    raises KeyError from pwd.getpwnam("") in environments with neither var set — a plain
    `docker build` doesn't set $USER at all, only $HOME.
    """
    return os.environ.get("SUDO_USER") or os.environ.get("USER") or pwd.getpwuid(os.getuid()).pw_name


def has_systemd() -> bool:
    """True if systemd is the running init system — the same check require_systemd() uses to
    decide whether to abort. False for containers with no init system, WSL1, and WSL2 with
    systemd=true unset in /etc/wsl.conf. Used by setup() to skip the system/desktop phases
    instead of letting require_systemd() raise partway through them.
    """
    return Path("/run/systemd/system").is_dir()


def is_devcontainer() -> bool:
    """True if running inside a dev container / Codespace — used by tasks/proxy.py to skip
    systemd-`--user`-daemon assumptions and prefer the Windows/host-proxy discovery path over
    installing a second local daemon. `/.dockerenv` alone isn't enough (any Docker container has
    it, including plain CI runners) — pair it with an env var a dev-container tool actually sets.
    """
    return Path("/.dockerenv").exists() and bool(
        os.environ.get("REMOTE_CONTAINERS") or os.environ.get("CODESPACES") or os.environ.get("DEVCONTAINER")
    )


def interactive() -> bool:
    """True if stdin is a real terminal and this isn't a dry run — the gate for whether it's
    safe to prompt with input() at all, vs. a piped/scripted/CI invocation that would just hang.
    """
    return sys.stdin.isatty() and not DRY_RUN


def confirm(question: str, default: bool = True) -> bool:
    """Prompt a yes/no question on stdin. Returns `default` unmodified if stdin isn't a real
    terminal — call interactive() yourself first if the caller needs to skip prompting (and any
    surrounding explanation) entirely rather than silently falling back to the default.
    """
    if not sys.stdin.isatty():
        return default
    suffix = " [Y/n] " if default else " [y/N] "
    while True:
        answer = input(question + suffix).strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please answer y or n.")


@overload
def prompt_text(question: str, default: str) -> str: ...
@overload
def prompt_text(question: str, default: None = None) -> str | None: ...
def prompt_text(question: str, default: str | None = None) -> str | None:
    """Prompt for a line of free text on stdin. Returns `default` unmodified (may be None) if
    stdin isn't a real terminal — same non-interactive gate as confirm(); call interactive()
    yourself first if the caller needs to skip prompting entirely. Re-prompts on an empty answer
    unless a default is given, so callers never get "" back for a required field.
    """
    if not sys.stdin.isatty():
        return default
    suffix = f" [{default}] " if default else " "
    while True:
        answer = input(question + suffix).strip()
        if answer:
            return answer
        if default is not None:
            return default
        print("This can't be empty.")


class MarkerStyle(StrEnum):
    """Which comment syntax _marker() emits — see ensure_block()/ensure_block_text()."""

    COMMENT = "comment"  # '# ╔══ PULSE::name ══╗' ... '# ╚══...══╝' — shell/ini/config files (default)
    HTML = "html"  # '<!-- PULSE::name -->' ... '<!-- /PULSE::name -->' — markdown/HTML targets, where a
    # '#'-prefixed line would render as a heading, not a comment


def _marker(name: str, open_: bool, style: MarkerStyle = MarkerStyle.COMMENT) -> str:
    if style == MarkerStyle.HTML:
        return f"<!-- PULSE::{name} -->" if open_ else f"<!-- /PULSE::{name} -->"
    tl, tr = ("╔", "╗") if open_ else ("╚", "╝")
    label = f" PULSE::{name} "
    fill = _PULSE_WIDTH - 2 - 2 - len(label)
    left = fill // 2
    right = fill - left
    return f"# {tl}{'═' * left}{label}{'═' * right}{tr}"


class BlockStatus(StrEnum):
    OK = "ok"
    ADDED = "added"
    UPDATED = "updated"


def ensure_block_text(
    text: str, name: str, content: str, *, style: MarkerStyle = MarkerStyle.COMMENT
) -> tuple[str, BlockStatus]:
    """Return (new_text, status) with a named PULSE block applied. Does not write."""
    start = _marker(name, open_=True, style=style)
    end = _marker(name, open_=False, style=style)
    # Markdown requires a blank line between adjacent block-level elements (here: the HTML-comment
    # marker and the content, e.g. a table) to parse/format as intended — dprint enforces this and
    # would otherwise fight ensure_block's own idempotency by re-inserting the blank lines on every
    # `inv quality.fix` pass. The comment-style marker has no such requirement (shell/config files).
    sep = "\n\n" if style == MarkerStyle.HTML else "\n"
    block = f"{start}{sep}{content.strip()}{sep}{end}"
    if start in text:
        s = text.index(start)
        e = text.index(end) + len(end)
        if text[s:e] == block:
            return text, BlockStatus.OK
        return text[:s] + block + text[e:], BlockStatus.UPDATED
    return text.rstrip("\n") + f"\n\n{block}\n", BlockStatus.ADDED


def ensure_block(path: Path, name: str, content: str, *, style: MarkerStyle = MarkerStyle.COMMENT) -> BlockStatus:
    """Idempotently write a named PULSE block to a file. Returns BlockStatus.{ADDED,UPDATED,OK}."""
    text = path.read_text() if path.exists() else ""
    new_text, status = ensure_block_text(text, name, content, style=style)
    if status != BlockStatus.OK:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_text)
    return status


def remove_block_text(text: str, name: str, *, style: MarkerStyle = MarkerStyle.COMMENT) -> tuple[str, bool]:
    """Return (new_text, removed) with a named PULSE block taken out. Does not write.

    The inverse of ensure_block_text, and needed for the same reason deploy.py tracks what it wrote:
    a block stops being wanted when its package stops applying to the machine (a `gui` package on a
    headless distro), and nothing else would ever take it out. Only the marker-delimited region goes
    — everything a human put in the file around it is left exactly as it was.
    """
    start = _marker(name, open_=True, style=style)
    end = _marker(name, open_=False, style=style)
    if start not in text or end not in text:
        return text, False
    s = text.index(start)
    e = text.index(end) + len(end)
    # Take the blank line ensure_block_text put in front of the block with it, or every removal
    # leaves a widening gap behind in a file that keeps being rewritten.
    return (text[:s].rstrip("\n") + "\n" + text[e:].lstrip("\n")).rstrip("\n") + "\n", True


def remove_block(path: Path, name: str, *, style: MarkerStyle = MarkerStyle.COMMENT) -> bool:
    """Remove a named PULSE block from a file if it is there. Returns True if the file changed."""
    if not path.exists():
        return False
    new_text, removed = remove_block_text(path.read_text(), name, style=style)
    if removed:
        path.write_text(new_text)
    return removed


def sudo_write(c: Context, path: Path, text: str) -> None:
    """Write `text` to a root-owned `path` via a tempfile + `sudo install` — direct
    `path.write_text()` can't reach root-owned locations, and `sudo tee` from Python would need the
    text piped through a subprocess shell instead of written directly.

    `install -m 0644`, not `cp`: NamedTemporaryFile creates its file 0600 and `cp` carries that
    mode across, so every system file written this way came out readable by root alone. Caught in
    a WSL simulation container — `inv wsl.fix` wrote /etc/wsl.conf, and the very next line, which
    reads it back to report what changed, died with PermissionError. Every destination this is
    used for (/etc/wsl.conf, apt sources, systemd drop-ins, a CA bundle, daemon.json) is meant to
    be world-readable; none of them carries a secret.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False) as f:
        f.write(text)
        tmp = f.name
    c.run(f"{SUDO} install -m 0644 {tmp} {path} && rm {tmp}")


def sudo_read(c: Context, path: Path) -> str:
    """Read a root-owned `path` via `sudo cat`, or "" if it doesn't exist / can't be read."""
    if not path.exists():
        return ""
    result = c.run(f"{SUDO} cat {path}", hide=True, warn=True)
    return result.stdout if result.ok else ""


@cache
def load_config() -> SetupConfig:
    return cast(SetupConfig, load_toml(_CONFIG_PATH))


@cache
def load_identity() -> Identity:
    if not IDENTITY_PATH.exists():
        raise FileNotFoundError(
            f"Identity file not found: {IDENTITY_PATH}\n"
            "Run `inv identity.init` (interactive wizard) or copy config/identity.toml.example "
            f"to {IDENTITY_PATH} and fill in your details by hand."
        )
    return cast(Identity, load_toml(IDENTITY_PATH))


def load_proxy_override() -> ProxySection:
    """Optional [proxy] table from ~/.config/power-user-linux-setup/identity.toml (host/port/noproxy). Unlike
    load_identity(), tolerant of a missing file — proxy detection has to degrade gracefully on the
    common case of a personal, non-corporate machine, not require identity.toml to exist just to
    run `inv proxy.check`. Not cached like load_identity()/load_config(): this is re-read on every
    proxy.* invocation on the assumption it's edited far more often mid-troubleshooting than the
    machine's own identity ever is.
    """
    if not IDENTITY_PATH.exists():
        return {}
    return cast(Identity, load_toml(IDENTITY_PATH)).get("proxy", {})


def load_certs_override() -> CertsSection:
    """Optional [certs] table from ~/.config/power-user-linux-setup/identity.toml (corporate CA bundle path(s)).
    Same tolerant-of-missing-file, not-cached rationale as load_proxy_override() — see there.
    """
    if not IDENTITY_PATH.exists():
        return {}
    return cast(Identity, load_toml(IDENTITY_PATH)).get("certs", {})


@cache
def load_overrides() -> dict[str, bool]:
    """Machine-local `enabled` flips from ~/.config/power-user-linux-setup/overrides.toml, keyed by
    package name.

    setup.toml's `enabled` is the *default* for every machine that clones this repo; a package like
    google-chrome-x11 (an NVIDIA+Wayland workaround) has to ship off for everyone while being on
    here. This file is how one machine says otherwise, in setup.toml's own shape:

        [packages.google-chrome-x11]
        enabled = true

    Deliberately out of git, and deliberately not backed up by anything here: preserving a home
    directory is the user's own job, not this repo's. What PULSE guarantees is the stability of its
    defaults, not of any one machine's customizations on top of them.

    Only `enabled` is honoured, and only for a package setup.toml already declares — every package
    *definition* stays in git where it can be reviewed. Tolerant of a missing file, like
    load_proxy_override()/load_certs_override(), since the common case is a machine with no
    overrides at all. Cached like load_identity(): unlike the proxy/certs tables this is read on
    every enabled_packages() call, which happens many times per task run.
    """
    if not OVERRIDES_PATH.exists():
        return {}
    raw = cast(Overrides, load_toml(OVERRIDES_PATH)).get("packages", {})

    declared = load_config()["packages"]
    overrides: dict[str, bool] = {}
    for name, cfg in raw.items():
        if name not in declared:
            # A typo here would otherwise do nothing at all, silently — the whole file is
            # unvalidated by anything else, so this is the only place it can be caught.
            print(f"[overrides] no [packages.{name}] in setup.toml — ignoring (typo?)")
            continue
        enabled = cfg.get("enabled")
        if enabled is not None:
            overrides[name] = bool(enabled)
    return overrides


def load_claude_settings() -> ClaudeSettings:
    """Read CLAUDE_SETTINGS (~/.claude/settings.json), or {} if it doesn't exist yet."""
    return cast(ClaudeSettings, load_json(CLAUDE_SETTINGS)) if CLAUDE_SETTINGS.exists() else {}


def write_claude_settings(settings: ClaudeSettings) -> None:
    """Backup CLAUDE_SETTINGS (if present) then overwrite it with `settings`. Shared by
    tasks/ai.py and tasks/allowlist.py, which each merge their own slice of permissions into the
    same file and must never clobber the other's — see their callers for the merge logic."""
    if CLAUDE_SETTINGS.exists():
        CLAUDE_SETTINGS.with_suffix(".json.bak").write_text(CLAUDE_SETTINGS.read_text())
    CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    CLAUDE_SETTINGS.write_text(json.dumps(settings, indent=2) + "\n")


def _excluded_tags() -> set[str]:
    val = os.environ.get("PULSE_EXCLUDE_TAGS", "")
    if not val:
        return set()
    return {t.strip() for t in val.split(",") if t.strip()}


class PackageMethod(StrEnum):
    """The `method` field of a `[packages.*]` section in setup.toml — see its header comment for
    what each one means."""

    APT = "apt"
    APT_REPO = "apt-repo"
    DEB_GITHUB = "deb-github"
    DEB_URL = "deb-url"
    APPARMOR_PROFILE = "apparmor-profile"
    ARCHIVE = "archive"
    UV_TOOL = "uv-tool"
    NVM = "nvm"
    SCRIPT = "script"
    BINARY = "binary"
    GIT_CLONE = "git-clone"
    WRAPPER_SCRIPT = "wrapper-script"
    GNOME_EXTENSION = "gnome-extension"


def enabled_packages() -> dict[str, PackageConfig]:
    """Every [packages.*] section that isn't disabled or excluded by PULSE_EXCLUDE_TAGS, whatever
    its method — the entry point for cross-method concerns like `config_files`, which any method
    may declare. Method-specific install tasks want packages_by_method() instead.

    Precedence is setup.toml → overrides.toml → PULSE_EXCLUDE_TAGS, environment last and absolute.
    Tags describe *capability* (no display server means a gui package genuinely cannot work), while
    an override describes *intent* — so an excluded tag wins over a machine that asked for the
    package, and the container/WSL profiles stay authoritative about what they can run.
    """
    excluded = _excluded_tags()
    overrides = load_overrides()
    return {
        name: cfg
        for name, cfg in load_config()["packages"].items()
        if overrides.get(name, cfg.get("enabled", True)) and not (excluded & set(cfg.get("tags", [])))
    }


def packages_by_method(method: PackageMethod) -> dict[str, PackageConfig]:
    return {name: cfg for name, cfg in enabled_packages().items() if cfg.get("method") == method}


def apt_packages(name: str, cfg: PackageConfig) -> list[str]:
    """Return the apt package list for a section, defaulting to [name] if not specified."""
    return cfg.get("packages", [name])


def apt_installed(pkg: str) -> bool:
    result = subprocess.run(
        ["dpkg-query", "-W", "-f=${Status}", pkg],
        capture_output=True,
        text=True,
        check=False,
    )
    return "install ok installed" in result.stdout


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


# ---------------------------------------------------------------------------
# Interactive children, and sudo
#
# One invariant holds this section together: **no command run through invoke may ever wait for
# something typed at the terminal.** Not sudo's password prompt, not an ssh key passphrase, not a
# debconf question. Two independent reasons, both reproduced in a container (see
# plans/2026-08-31-wsl-and-container-first-run-experience.md):
#
# 1. invoke echoes stdin itself. `Runner.should_echo_stdin()` is `(not using_pty) and
#    isatty(stdin)`, so for a non-pty run from a terminal invoke prints every byte it reads back
#    to stdout — while sudo reads the same terminal through /dev/tty. Two readers, one terminal:
#    whichever wins is a race, and when invoke wins, the password is printed in plain text *and*
#    sudo never sees those characters, so it re-prompts and the run looks stuck.
# 2. On Python 3.14 invoke cannot forward stdin at all. `terminals.bytes_to_read()` calls
#    `fcntl.ioctl(stdin, FIONREAD, b"  ")` with a 2-byte buffer for a 4-byte result; 3.14 turned
#    that into `SystemError: buffer overflow`, killing invoke's stdin thread on the first
#    keystroke. Every interactive `c.run` then waits forever — pty or not. Upstream:
#    pyinvoke/invoke#1070, fix unreleased as of invoke 3.0.3, which is what
#    `uv_python_default = "3.14"` gets us.
#
# So interactive children go through run_interactive() (plain subprocess, real terminal), and
# every *other* sudo call is made non-interactive by ensure_sudo() rebinding SUDO to `sudo -n`.
# ---------------------------------------------------------------------------


def run_interactive(cmd: Sequence[str], *, check: bool = True) -> int:
    """Run a command that needs the user's terminal — password/passphrase prompts, anything
    reading /dev/tty — as a plain subprocess inheriting this process's stdin/stdout/stderr.

    Never `c.run(..., pty=True)`: see this section's header. The child owns the terminal for the
    duration, exactly as if it had been typed at the shell, so echo suppression is the child's own
    business and nothing races it for the keystrokes.
    """
    argv = list(cmd)
    if DRY_RUN:
        print(f"[dry-run] would run interactively: {' '.join(argv)}")
        return 0
    return subprocess.run(argv, check=check).returncode


# Everything an apt/dpkg call needs so it can't stop and wait for a human. Both halves are load-
# bearing and neither implies the other:
#
#   DEBIAN_FRONTEND=noninteractive  a package with a debconf question (tzdata's "Geographic area",
#                                   wireshark-common's dumpcap question, keyboard-configuration)
#                                   takes the default instead of drawing a dialog nobody can
#                                   answer. `-y` does not cover this — it answers apt's own
#                                   "do you want to continue", not debconf's.
#   --force-confold/--force-confdef  a conffile this machine has edited keeps the local version
#                                   rather than asking which to install. dpkg's prompt is the
#                                   other half of the same hang.
#
# Passed via `env` rather than as a `VAR=value sudo …` prefix (sudo's env_reset drops that) or a
# `sudo VAR=value …` prefix (allowed only where sudoers grants setenv).
_NONINTERACTIVE_ENV = "env DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical"
_KEEP_LOCAL_CONFFILES = "-o Dpkg::Options::=--force-confold -o Dpkg::Options::=--force-confdef"


def apt_command(args: str) -> str:
    """A complete `apt-get` command line that can never stop for a question.

    `apt-get`, not `apt`: apt's own CLI warns that it has no stable interface for scripts, and
    every subcommand this repo uses (install/update/purge/autoremove/clean/autoclean) exists in
    both.
    """
    return f"{SUDO} {_NONINTERACTIVE_ENV} apt-get {_KEEP_LOCAL_CONFFILES} {args}".strip()


def dpkg_command(args: str) -> str:
    """Same, for a direct `dpkg` call (installing a downloaded .deb)."""
    return f"{SUDO} {_NONINTERACTIVE_ENV} dpkg --force-confold --force-confdef {args}".strip()


@dataclass(frozen=True)
class SudoState:
    """What `sudo` will do here if we ask it to, decided before anything is installed rather than
    discovered halfway through an apt run."""

    root: bool
    passwordless: bool
    cached: bool
    askpass: str | None
    tty: bool

    @property
    def ready(self) -> bool:
        """True if a `sudo -n` call will succeed right now with nothing typed."""
        return self.root or self.passwordless or self.cached

    @property
    def can_authenticate(self) -> bool:
        """True if there's some way to *get* to that state — a GUI askpass or a real terminal."""
        return self.ready or self.askpass is not None or self.tty


def _sudo_ok(*args: str) -> bool:
    return (
        subprocess.run(
            ["sudo", *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def _usable_askpass() -> str | None:
    """SUDO_ASKPASS, but only when it can actually produce a password here. The helper this repo
    deploys is a Zenity dialog (config/askpass-zenity.sh); with no display it can only fail, and
    sudo's own failure for that is the unhelpful "no password was provided". A helper that reads
    the terminal instead is fine either way, so a display is required only for the GUI one.
    """
    askpass = os.environ.get("SUDO_ASKPASS")
    if not askpass or not os.access(askpass, os.X_OK):
        return None
    if "zenity" in Path(askpass).name and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return None
    return askpass


def sudo_state() -> SudoState:
    if os.geteuid() == 0:
        return SudoState(root=True, passwordless=True, cached=True, askpass=None, tty=sys.stdin.isatty())
    if not command_exists("sudo"):
        return SudoState(root=False, passwordless=False, cached=False, askpass=None, tty=sys.stdin.isatty())
    # `sudo -n true` succeeds for a NOPASSWD rule *and* for a live credential cache; `sudo -n -k
    # true` ignores the cache, so the pair separates the two without ever prompting. -k here only
    # tells this one call to ignore the timestamp — unlike a bare `sudo -k`, it doesn't clear it.
    passwordless = _sudo_ok("-n", "-k", "true")
    cached = passwordless or _sudo_ok("-n", "true")
    return SudoState(
        root=False,
        passwordless=passwordless,
        cached=cached,
        askpass=_usable_askpass(),
        tty=sys.stdin.isatty(),
    )


_sudo_ready = False
_sudo_keepalive: "threading.Thread | None" = None
_sudo_keepalive_stop = threading.Event()

# How often the keepalive re-stamps sudo's credential cache. sudo's own default timeout is 15
# minutes and a full `inv setup` on a slow connection runs far longer than that, so without this
# the cache lapses mid-run and the next `sudo -n` call fails for no reason the user can see.
_SUDO_KEEPALIVE_SECONDS = 60


def _sudo_keepalive_loop() -> None:
    while not _sudo_keepalive_stop.wait(_SUDO_KEEPALIVE_SECONDS):
        _sudo_ok("-n", "-v")


def ensure_sudo(reason: str = "the rest of this run") -> bool:
    """Authenticate sudo once, up front, then guarantee no later sudo call can prompt.

    Returns True when sudo is usable. Idempotent — later calls are a no-op, so every task that
    needs root can call it without coordinating with the others.

    Three things happen here, in order:

    1. The password (if one is needed at all) is collected **outside invoke** — a GUI askpass if
       one can work here, otherwise `sudo -v` as a plain subprocess owning the real terminal.
    2. `SUDO` is rebound to `sudo -n`, so every `c.run(f"{util.SUDO} …")` in the repo becomes
       non-interactive. A lapsed cache then fails loudly and immediately instead of printing an
       invisible prompt into a `hide=True` stream and hanging.
    3. A daemon thread re-stamps the credential cache every minute, so it can't lapse during a
       long install in the first place.
    """
    # SUDO is deliberately rebindable despite its name: it is the one piece of process-wide state
    # every task interpolates, and the whole point of this function is to change what it means for
    # the rest of the run. Renaming it to lowercase would touch 46 call sites for a naming rule.
    global _sudo_ready, SUDO, _sudo_keepalive  # noqa: PLW0603 — process-wide state by design
    if _sudo_ready or DRY_RUN:
        return True

    state = sudo_state()
    if state.root:
        SUDO = ""  # pyright: ignore[reportConstantRedefinition]
        _sudo_ready = True
        return True
    if not command_exists("sudo"):
        raise RuntimeError(
            "sudo is not installed and this isn't running as root — install sudo (or run as "
            "root) before setting up this machine."
        )

    if not state.ready:
        if state.askpass:
            print(f"[sudo] authenticating via {state.askpass} — a password dialog should appear")
            run_interactive(["sudo", "-A", "-v"])
        elif state.tty:
            print(
                f"[sudo] this machine needs a sudo password for {reason}. Asking once now, so "
                "nothing later stops to ask again — nothing you type is echoed."
            )
            run_interactive(["sudo", "-v"])
        else:
            raise RuntimeError(
                "sudo needs a password here, but there's no terminal to ask on and no usable "
                "SUDO_ASKPASS helper.\n"
                "Pick one:\n"
                "  • run `sudo -v` yourself first, then re-run this within the credential "
                "cache's lifetime;\n"
                "  • give this user a NOPASSWD rule (`/etc/sudoers.d/`), which is what dev "
                "container base images do;\n"
                "  • or run this as root.\n"
                "Refusing to continue: every install step below needs root, and each would stop "
                "at its own invisible password prompt."
            )

    SUDO = "sudo -n"  # pyright: ignore[reportConstantRedefinition]
    _sudo_ready = True
    if _sudo_keepalive is None and not state.passwordless:
        _sudo_keepalive = threading.Thread(target=_sudo_keepalive_loop, daemon=True, name="pulse-sudo-keepalive")
        _sudo_keepalive.start()
    return True


def require_systemd() -> None:
    """Abort immediately if systemd isn't the running init system.

    Any task that shells out to systemctl/localectl needs this — fails the same way whether the
    cause is WSL1 (no real kernel, systemd never runs at all), WSL2 with `systemd=true` unset in
    /etc/wsl.conf, or a minimal/container environment with no init system. This repo only
    supports WSL2 with systemd enabled; WSL1 is not a supported target.
    """
    if not has_systemd():
        raise RuntimeError(
            "systemd is not running (no /run/systemd/system) — this task shells out to "
            "systemctl/localectl and needs it.\n"
            "On WSL2, add to /etc/wsl.conf:\n"
            "  [boot]\n"
            "  systemd=true\n"
            "then run `wsl.exe --shutdown` from Windows and reopen the terminal. WSL1 cannot run "
            "systemd at all and isn't a supported target.\n"
            "Run `inv wsl.check` for a full diagnostic."
        )


def require_apt() -> None:
    """Abort immediately if apt/dpkg aren't available — this repo only targets Debian/Ubuntu."""
    missing = [name for name in ("apt", "dpkg") if not command_exists(name)]
    if missing:
        raise RuntimeError(
            f"{' and '.join(missing)} not found — this repo only supports Debian/Ubuntu (apt, "
            "apt-repo, deb-github, deb-url methods all shell out to apt/dpkg).\n"
            "On WSL this usually means a non-Ubuntu distro (Alpine, Fedora Remix, etc.) — install "
            "Ubuntu-24.04 from the Microsoft Store instead: wsl.exe --install Ubuntu-24.04\n"
            "Run `inv wsl.check` for a full diagnostic."
        )


def file_contains(path: str | Path, text: str) -> bool:
    try:
        return text in Path(path).expanduser().read_text()
    except FileNotFoundError:
        return False


def ensure_symlink(src_cmd: str, link_name: str) -> bool:
    """Create ~/.local/bin/<link_name> -> which(<src_cmd>) if not already present."""
    src = shutil.which(src_cmd)
    if not src:
        return False
    return ensure_symlink_path(src, link_name)


def ensure_symlink_path(src_path: str | Path, link_name: str) -> bool:
    """Create ~/.local/bin/<link_name> -> <src_path> if not already present."""
    src = Path(src_path).expanduser()
    if not src.exists():
        return False
    link = Path.home() / ".local" / "bin" / link_name
    link.parent.mkdir(parents=True, exist_ok=True)
    if not link.exists():
        link.symlink_to(src)
        return True
    return False
