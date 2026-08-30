"""One way to write a file into the home directory.

Every path this repo deploys under `~` goes through this module: the `wrapper-script` method's
`content_file` (`~/AGENTS.md`, `askpass-zenity`, ...), any package's `config_files` mappings
(wezterm, terminator), and the skill directories under `~/.agents/skills/`. Before this existed
those were three separate writers with four different answers to "the destination already exists"
— unconditional overwrite, skip-if-exists, diff-then-prompt, and marker-checked prompt — and the
unconditional one silently ate hand-edits to `~/AGENTS.md` twice in one day.

The rule here is that PULSE never destroys content it can't prove it wrote. `classify()` answers
that from a state manifest recording the digest of what was last deployed; `deploy()` acts on the
answer, and only ever overwrites unseen when the destination still matches that digest.

See contributing/deploy.md for the full design rationale, the rejected approaches (a PostToolUse
hook, a pre-push git hook), and why `util.ensure_block`/`write_claude_settings` deliberately stay
outside this module — they write into files the *user* owns, which is a different ownership
model, not a different style.
"""

import difflib
import hashlib
import json
import shutil
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from functools import cached_property
from pathlib import Path
from typing import TypedDict, cast

from invoke import Context, Exit, task

from . import ui, util

_REPO_ROOT = Path(__file__).parent.parent

# Machine-local, out-of-repo, deliberately never setup.toml: that file is a tracked, git-shared
# *declaration*, and per-machine deploy timestamps in it would churn every machine's diff and make
# `git blame` on the declaration useless. Same state namespace as ai.py's static-permissions
# manifest and allowlist.py's applied manifest.
_MANIFEST = util.PULSE_STATE_DIR / "deployed.json"
_MANIFEST_VERSION = 1

# Written inside every skill directory this repo installs, recording the setup.toml-declared path
# that installed it. Lives here rather than in ai.py because both the skill installer and this
# module's registry need it. It answers a different question than the manifest does: the marker
# says *whose is this* and survives a wiped state dir, the manifest says *what did we write, when*.
SKILL_MARKER = ".pulse-source"


class ManifestEntry(TypedDict):
    """One destination's record in the state manifest — see record()."""

    package: str
    source: str
    mechanism: str
    digest: str
    deployed_at: str


Manifest = dict[str, ManifestEntry]


class _ManifestFile(TypedDict):
    version: int
    entries: Manifest


class Mechanism(StrEnum):
    """How a destination gets deployed — decides its content transform, ownership policy, and
    whether it's a file or a directory. Not the same axis as setup.toml's `method`: any method may
    declare `config_files`."""

    WRAPPER_SCRIPT = "wrapper-script"
    CONFIG_FILE = "config-file"
    # A whole file this repo owns outright that must NOT be executable — a systemd unit, an editor
    # options file. `wrapper-script` was the only MANAGED whole-file mechanism and it chmods 0755,
    # so a PULSE-owned non-executable file had no way to be declared at all: `~/.config/systemd/
    # user/pulse-proxy.service` was a module constant written by a task of its own instead, with no
    # manifest entry, no diff and no never-clobber guarantee. Same verbatim copy as CONFIG_FILE,
    # opposite policy.
    MANAGED_FILE = "managed-file"
    SKILL = "skill"
    # One destination composed from several repo-side fragments rather than copied from a single
    # source file — `~/AGENTS.md`, assembled from every `agents_md` fragment declared anywhere in
    # setup.toml. Everything else about it is a normal MANAGED file: same digest comparison, same
    # diff, same never-overwrite-what-we-can't-prove-we-wrote rule.
    ASSEMBLED = "assembled"


class Policy(StrEnum):
    """Who owns the deployed content after the first install."""

    # PULSE owns it. A destination that no longer matches what we wrote is carrying an edit that
    # will be lost on the next redeploy and hasn't reached the repo — a problem, reported as one.
    MANAGED = "managed"
    # PULSE seeds it once; the user owns it afterwards (setup.toml's `config_files` writes are
    # skip-if-exists by design). Divergence is the expected steady state, reported for information
    # only — never a warning, never a verify failure.
    SEEDED = "seeded"


class State(StrEnum):
    """What `classify()` found at a destination."""

    ABSENT = "absent"  # nothing there yet — first install
    CLEAN = "clean"  # matches what we wrote, and the source hasn't moved on
    STALE = "stale"  # matches what we wrote, but the repo source has changed — safe redeploy
    DIRTY = "dirty"  # differs from what we wrote — edited since
    UNKNOWN = "unknown"  # exists, we have no record of writing it — never assume it's ours


class Action(StrEnum):
    """What `deploy()` did."""

    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    LEFT_ALONE = "left alone"


@dataclass(frozen=True)
class Managed:
    """One home-directory path this repo claims, and where its content comes from."""

    path: Path  # absolute destination
    package: str  # the [packages.*] section that declares it
    source: str  # repo-relative source path — the fragment directory, for an ASSEMBLED destination
    mechanism: Mechanism
    # ASSEMBLED only: the repo-relative fragment paths, already in assembly order. Empty for every
    # other mechanism, whose content comes from `source` alone.
    parts: tuple[str, ...] = ()

    @property
    def policy(self) -> Policy:
        return Policy.SEEDED if self.mechanism == Mechanism.CONFIG_FILE else Policy.MANAGED

    @property
    def is_dir(self) -> bool:
        return self.mechanism == Mechanism.SKILL

    @cached_property
    def src(self) -> Path:
        """Absolute repo-side source. Resolved against the repo root, never the cwd, so every
        caller works from any directory."""
        return _REPO_ROOT / self.source


def dir_digest(path: Path) -> str:
    """Hash of a directory's file contents, keyed by relative path — order-independent, ignores
    the marker file itself so a freshly-copied dest compares equal to its source."""
    h = hashlib.sha256()
    for f in sorted(path.rglob("*")):
        if f.is_file() and f.name != SKILL_MARKER:
            h.update(f.relative_to(path).as_posix().encode())
            h.update(f.read_bytes())
    return h.hexdigest()


def block_name(part: str) -> str:
    """The `PULSE::<name>` block a fragment is written into — its filename stem, namespaced by the
    directory it lives in so a marker is traceable back to one repo file by eye."""
    p = Path(part)
    return f"{p.parent.name}/{p.stem}"


def assemble(parts: tuple[str, ...]) -> str:
    """Compose an ASSEMBLED destination's text from its fragments, in the order given.

    Each fragment lands in its own `util.ensure_block` region so the deployed file says which repo
    file every section came from. That is *provenance only* — unlike `~/.zshrc`, where ensure_block
    writes one region into a file the user owns, the destination here is regenerated end to end and
    nothing outside a block survives. Hand-edit protection comes from the deploy manifest
    (`classify` -> DIRTY -> diff and prompt), not from the markers. HTML markers rather than
    `#`-prefixed ones because the target is Markdown, where a `#` line renders as a heading.

    Building up from an empty string rather than editing a file in place is what keeps this a pure
    function of the repo's fragments — and that purity is load-bearing: `expected_digest` compares
    it against what is actually deployed, which it could not do if the result depended on what was
    already at the destination.
    """
    text = ""
    for part in parts:
        content = (_REPO_ROOT / part).read_text().strip()
        text, _ = util.ensure_block_text(text, block_name(part), content, style=util.MarkerStyle.HTML)
    # ensure_block_text separates blocks with a blank line, which leaves two leading newlines on
    # the very first one appended to an empty string.
    return text.lstrip("\n")


def expected_bytes(m: Managed) -> bytes:
    """The exact bytes a file-kind destination should hold. `wrapper-script` deploys its
    `content_file` stripped and newline-terminated (tools.py has always done this); `assembled`
    composes its fragments the same way; `config_files` copies its source verbatim, binary
    included."""
    if m.mechanism == Mechanism.ASSEMBLED:
        return (assemble(m.parts).strip() + "\n").encode()
    if m.mechanism == Mechanism.WRAPPER_SCRIPT:
        return (m.src.read_text().strip() + "\n").encode()
    return m.src.read_bytes()


def expected_digest(m: Managed) -> str:
    """Digest of what a fresh deploy of `m` would put at its destination."""
    if m.is_dir:
        return dir_digest(m.src)
    return hashlib.sha256(expected_bytes(m)).hexdigest()


def deployed_digest(m: Managed) -> str | None:
    """Digest of what's actually at the destination now, or None if nothing is."""
    if m.is_dir:
        return dir_digest(m.path) if m.path.is_dir() else None
    return hashlib.sha256(m.path.read_bytes()).hexdigest() if m.path.is_file() else None


# ---------------------------------------------------------------------------
# Registry — every home path this repo claims, from setup.toml alone
# ---------------------------------------------------------------------------


def fragments(field: str) -> tuple[str, ...]:
    """Every repo-relative fragment path declared under `field` on any enabled package, in
    assembly order.

    Any-section, like `zshrc`/`zshenv`/`zprofile` and `claude_permissions_allow`: the destination
    is declared once (by the package naming the field in `assembled_from`), while the content can
    come from any number of packages, each contributing whole `##` sections. Sorted on
    `(order, package, src)` so the assembled document is byte-identical across runs regardless of
    how setup.toml's keys iterate — a document's section order is part of its meaning, unlike a
    shell rc file's.
    """
    declared: list[tuple[int, str, str]] = []
    for name, cfg in util.enabled_packages().items():
        # `field` comes from setup.toml (`assembled_from`), so it can't index the TypedDict
        # statically — widening to a plain dict is what makes the dynamic key legal.
        entries = cast(list[util.AgentsMdFragment], dict(cfg).get(field, []))
        for frag in entries:
            if "src" not in frag:
                raise util.missing_fields(name, f"{field}[].src")
            declared.append((frag.get("order", 50), name, frag["src"]))
    return tuple(src for _, _, src in sorted(declared))


def assembled_entry(name: str, dest: Path, field: str) -> Managed:
    """The registry entry for a destination composed from `field`'s fragments.

    The one place this shape is built, so `tools.py`'s installer and the registry below can never
    disagree about what a package deploys. `source` is the fragments' shared directory rather than
    any one file: it is what every human-facing message and the manifest record show, and no single
    fragment is the source.
    """
    parts = fragments(field)
    if not parts:
        # An assembled destination with no fragments would deploy an empty file — for ~/AGENTS.md
        # that is every rule on the machine, silently gone. Fail instead.
        raise util.missing_fields(name, f"at least one {field} fragment on some package")
    return Managed(
        path=dest,
        package=name,
        source=str(Path(parts[0]).parent),
        mechanism=Mechanism.ASSEMBLED,
        parts=parts,
    )


def _wrapper_script_entries() -> Iterator[Managed]:
    for name, cfg in util.packages_by_method(util.PackageMethod.WRAPPER_SCRIPT).items():
        if "dest" not in cfg:
            # A wrapper-script entry with neither a source nor a destination declares nothing to
            # deploy; an inline-`content` variant is allowed by the method but unused today. Skip
            # rather than inventing a path, so the registry never claims one it can't compare.
            continue
        dest = Path(cfg["dest"]).expanduser()
        if field := cfg.get("assembled_from"):
            yield assembled_entry(name, dest, field)
        elif content_file := cfg.get("content_file"):
            yield Managed(path=dest, package=name, source=content_file, mechanism=Mechanism.WRAPPER_SCRIPT)


def config_file_entries(name: str, cfg: util.PackageConfig) -> Iterator[Managed]:
    """One package's `config_files` declarations, as registry entries.

    Public so the install-time applier below and the registry read the identical declaration rather
    than each building its own `Managed` — the two lived in different modules and disagreed about
    which field spelled the destination once already.
    """
    for mapping in cfg.get("config_files", []):
        yield Managed(
            path=Path(mapping["dst"]).expanduser(),
            package=name,
            source=mapping["src"],
            mechanism=Mechanism.CONFIG_FILE,
        )


def _config_file_entries() -> Iterator[Managed]:
    # enabled_packages(), not packages_by_method(): `config_files` is method-agnostic, and a lookup
    # keyed on the `dest` field would miss these entirely — they use `dst`.
    for name, cfg in util.enabled_packages().items():
        yield from config_file_entries(name, cfg)


def _skill_entries(base: Path) -> Iterator[Managed]:
    # Mirrors ai.py:_install_declared_skills' own scan deliberately: it reads load_config()
    # directly and honours `enabled` but not tags, so going through enabled_packages() here would
    # make the registry disagree with the installer about which skills exist on a tag-excluded run.
    for name, cfg in util.load_config()["packages"].items():
        if not cfg.get("enabled", True):
            continue
        for entry in cfg.get("skills", []):
            if entry.get("source") != "local":
                continue  # npx-sourced skills are installed by the `skills` CLI, not by this repo
            if "path" not in entry:
                raise util.missing_fields(name, "skills[].path")
            source = entry["path"]
            yield Managed(
                path=base / ".agents" / "skills" / Path(source).name,
                package=name,
                source=source,
                mechanism=Mechanism.SKILL,
            )


def managed_paths(base: Path | None = None) -> dict[Path, Managed]:
    """Every home-directory path this repo deploys, keyed by absolute destination.

    `base` is the skills root (defaults to the home directory) — `inv ai.install-skills --dir` installs
    project-local skills elsewhere, and passing that directory here scopes the registry to match.
    """
    home = base or Path.home()
    entries = (*_wrapper_script_entries(), *_config_file_entries(), *_skill_entries(home))
    return {m.path: m for m in entries}


def lookup(path: Path | str, base: Path | None = None) -> Managed | None:
    """The registry entry for `path`, or None if this repo doesn't deploy it.

    Tries the path as given, then its resolved form — that second attempt is what makes
    `~/.claude/CLAUDE.md` (a `symlink_dest` pointing at `~/AGENTS.md`) match the entry for its
    target, without the symlink itself becoming a deploy destination in its own right.
    """
    registry = managed_paths(base)
    candidate = Path(path).expanduser()
    if hit := registry.get(candidate):
        return hit
    return registry.get(candidate.resolve()) if candidate.exists() else None


# ---------------------------------------------------------------------------
# State manifest
# ---------------------------------------------------------------------------


def load_manifest() -> Manifest:
    """The per-destination record of what PULSE last wrote, or {} if there is none yet."""
    if not _MANIFEST.exists():
        return {}
    data = cast(_ManifestFile, cast(object, json.loads(_MANIFEST.read_text())))
    if data.get("version") != _MANIFEST_VERSION:
        # A future version's format isn't readable here, and guessing would risk treating a
        # destination as ours on bad evidence. An empty manifest degrades to UNKNOWN/CLEAN by
        # content comparison, which is safe — it prompts rather than overwrites.
        return {}
    return data.get("entries", {})


def _write_manifest(entries: Manifest) -> None:
    _MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    payload: _ManifestFile = {"version": _MANIFEST_VERSION, "entries": entries}
    _MANIFEST.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def record(m: Managed, digest: str) -> None:
    """Record that PULSE just wrote `digest` to `m`'s destination. No-op under PULSE_DRY_RUN."""
    if util.DRY_RUN:
        return
    entries = load_manifest()
    entries[str(m.path)] = {
        "package": m.package,
        "source": m.source,
        "mechanism": str(m.mechanism),
        "digest": digest,
        # Never consulted by classify() — a timestamp can't answer "has this been edited since",
        # only the digest can. It's here for the human-facing message and for debugging.
        "deployed_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    _write_manifest(entries)


def forget(path: Path) -> None:
    """Drop a destination's record — for a package that no longer declares it."""
    if util.DRY_RUN:
        return
    entries = load_manifest()
    if entries.pop(str(path), None) is not None:
        _write_manifest(entries)


# ---------------------------------------------------------------------------
# Classify
# ---------------------------------------------------------------------------


def classify(m: Managed, manifest: Manifest | None = None) -> State:
    """What state `m`'s destination is in. Pure: reads the filesystem, never writes.

    Pass `manifest` to classify a whole registry without re-reading the file per entry.

    A destination with no manifest entry that nonetheless matches its source byte-for-byte is
    CLEAN, not UNKNOWN. That is what makes this mechanism a no-op when it first lands on a machine
    whose files were all deployed before the manifest existed — without it, every managed path on
    every existing machine would classify UNKNOWN and prompt.
    """
    deployed = deployed_digest(m)
    if deployed is None:
        return State.ABSENT

    expected = expected_digest(m)
    entries = load_manifest() if manifest is None else manifest
    entry = entries.get(str(m.path))

    if entry is None:
        return State.CLEAN if deployed == expected else State.UNKNOWN
    if deployed != entry.get("digest"):
        return State.DIRTY
    return State.CLEAN if deployed == expected else State.STALE


def scan(base: Path | None = None) -> list[tuple[Managed, State]]:
    """Classify the whole registry in one pass, in registry order."""
    manifest = load_manifest()
    return [(m, classify(m, manifest)) for m in managed_paths(base).values()]


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def diff(m: Managed) -> str:
    """Indented unified diff of what's deployed against what a fresh deploy would write."""
    if m.is_dir:
        return f"  (directory — {m.path} differs from {m.source})\n"
    try:
        before = m.path.read_bytes().decode().splitlines(keepends=True)
        after = expected_bytes(m).decode().splitlines(keepends=True)
    except UnicodeDecodeError:
        return "  (binary file — diff not shown)\n"
    lines = difflib.unified_diff(before, after, fromfile=str(m.path), tofile=m.source)
    return "".join(f"  {line}" if line.endswith("\n") else f"  {line}\n" for line in lines)


def _write(m: Managed) -> str:
    """Put the source content at the destination and return the digest actually landed.

    Re-reads rather than trusting the write: a full disk, a permission race, or a partial copytree
    should fail loudly here, before the manifest records it as ours, not silently surface later as
    a stale-looking file someone has to go diff by hand.
    """
    m.path.parent.mkdir(parents=True, exist_ok=True)
    if m.is_dir:
        if m.path.is_symlink():
            m.path.unlink()
        elif m.path.exists():
            shutil.rmtree(m.path)
        shutil.copytree(m.src, m.path)
        (m.path / SKILL_MARKER).write_text(m.source + "\n")
    else:
        m.path.write_bytes(expected_bytes(m))
        if m.mechanism == Mechanism.WRAPPER_SCRIPT:
            m.path.chmod(0o755)

    landed = deployed_digest(m)
    if landed is None or landed != expected_digest(m):
        raise RuntimeError(f"[deploy] wrote {m.path} but its content doesn't match {m.source}")
    return landed


def deploy(m: Managed, *, assume_yes: bool = False, manifest: Manifest | None = None) -> Action:
    """Deploy `m`, never destroying content PULSE can't prove it wrote.

    ABSENT creates and STALE overwrites, both silently — neither can lose anything, since a STALE
    destination still holds exactly what we last put there. DIRTY and UNKNOWN are the cases that
    matter: for a MANAGED path they print the diff and ask (defaulting to *not* overwriting, so a
    piped or CI run without `assume_yes` leaves the file alone rather than clobbering it); for a
    SEEDED path they leave it alone and say so, because a user-customized config is the expected
    state there, not a problem.

    `assume_yes` is the `--yes` flag; `PULSE_ASSUME_YES=1` (util.ASSUME_YES) is the same thing for
    the install tasks, which reach this writer from `inv setup` with no flag of their own.
    """
    assume_yes = assume_yes or util.ASSUME_YES
    state = classify(m, manifest)

    if state == State.CLEAN:
        print(f"[deploy] {m.package}: {m.path} already matches {m.source}")
        return Action.UNCHANGED

    if state in (State.ABSENT, State.STALE):
        verb = "create" if state == State.ABSENT else "update"
        if util.DRY_RUN:
            print(f"[deploy] {m.package}: would {verb} {m.path}")
            return Action.CREATED if state == State.ABSENT else Action.UPDATED
        record(m, _write(m))
        print(f"[deploy] {m.package}: {verb}d {m.path}")
        return Action.CREATED if state == State.ABSENT else Action.UPDATED

    # `and not assume_yes` is load-bearing: without it this returns before the overwrite path below
    # and `--yes` silently does nothing on a SEEDED destination — while this very message, and
    # all_()'s docstring, both promise it overwrites. Found by running the command the message
    # tells you to run (2026-08-30, redeploying wezterm.lua after a font rename).
    if m.policy == Policy.SEEDED and not assume_yes:
        print(
            f"[deploy] {m.package}: {m.path} differs from {m.source} — yours to own, leaving it "
            f"alone (`inv deploy.all --name {m.package} --yes` would overwrite it)"
        )
        return Action.LEFT_ALONE

    edited = "edited since PULSE deployed it" if state == State.DIRTY else "not deployed by PULSE"
    print(f"\n[deploy] {m.package}: {m.path} was {edited} — its repo-side source is {m.source}\n")
    print(diff(m))
    if util.DRY_RUN:
        print(f"[deploy] {m.package}: would overwrite {m.path}")
        return Action.UPDATED
    if not assume_yes and not util.confirm(f"Overwrite {m.path}?", default=False):
        print(f"[deploy] {m.package}: left alone — port the edit into {m.source} to keep it")
        return Action.LEFT_ALONE
    record(m, _write(m))
    print(f"[deploy] {m.package}: overwrote {m.path}")
    return Action.UPDATED


def apply_config_files(name: str, cfg: util.PackageConfig) -> None:
    """Seed one package's `config_files` at install time, through the writer above.

    Called from every install task, so a declared config lands in the packages phase with its
    package — which `inv verify.all`, running at the end of that phase, then requires to exist. It
    lives here rather than in whichever install module happened to need it first (it was apt.py's
    private helper, so only apt- and deb-method packages ever got their config seeded during
    `inv setup`; an `archive` or `git-clone` package's declared config waited for a separate
    `inv deploy.all` that a fresh machine never runs).
    """
    for managed in config_file_entries(name, cfg):
        deploy(managed)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

SUMMARY = {
    State.ABSENT: "not deployed yet",
    State.CLEAN: "ok",
    State.STALE: "source has changed since it was deployed",
    State.DIRTY: "edited since PULSE deployed it",
    # Deliberately non-committal: with no manifest entry there is no way to tell an edit under ~
    # apart from a repo-side change that simply hasn't been deployed yet, and claiming either would
    # be wrong half the time. Says what is actually known, and what to do about it.
    State.UNKNOWN: "differs from its source — either edited here, or the source moved on",
}


def _needs_attention(m: Managed, state: State) -> bool:
    """Whether a state is a problem worth surfacing, as opposed to normal. Only MANAGED paths
    qualify: a SEEDED destination that differs is the user's own customization, which is what
    that mechanism is for — flagging it would cry wolf on every config the user has ever touched.
    """
    return m.policy == Policy.MANAGED and state in (State.DIRTY, State.UNKNOWN)


def _scoped(name: str | None, base: Path | None = None) -> list[Managed]:
    entries = [m for m in managed_paths(base).values() if name is None or m.package == name]
    if name is not None and not entries:
        raise Exit(f"[deploy] no enabled [packages.{name}] section deploys anything into your home directory")
    return entries


@task(
    help={
        "name": "Only report paths declared by this [packages.*] section, e.g. agents-md.",
        "path": "Report on one path instead of the whole registry — including whether PULSE deploys it at all.",
    }
)
def status(c: Context, name: str | None = None, path: str | None = None):
    """Report every path this repo deploys under ~, and whether it still matches its repo source.

    Strictly read-only: never writes, never prompts, never fixes. `inv deploy.all` is the repair
    path. A path that differs from what PULSE last wrote there is shown with its full diff, since
    that content only exists at the destination — it has not reached the repo, and the next
    redeploy is what would discard it.

    Pass --path to ask about one specific file, whether or not this repo deploys it: the answer for
    an unmanaged path ("not deployed by PULSE") is as useful as the answer for a managed one, and
    is the thing to check before assuming an edit under ~ will survive.
    """
    if path is not None:
        _status_one(Path(path).expanduser())
        return

    entries = _scoped(name)
    manifest = load_manifest()
    attention: list[Managed] = []

    for m in entries:
        state = classify(m, manifest)
        print(f"[deploy] {m.package}: {m.path} — {SUMMARY[state]}")
        if _needs_attention(m, state):
            attention.append(m)
            print(diff(m))

    if attention:
        edited = [m for m in attention if classify(m, manifest) == State.DIRTY]
        ui.warn(
            f"{len(attention)} deployed file(s) no longer match their repo source.",
            "Read each diff above before redeploying: content that exists only at the destination "
            "is discarded by the next deploy, and only the diff tells you whether there is any.",
            *(f"  {m.path}  ->  {m.source}" for m in attention),
            (
                "Port anything worth keeping into the repo-side source, then `inv deploy.all`."
                if edited
                else "If the diffs are all repo-side changes, `inv deploy.all` deploys them."
            ),
        )


@task(
    name="all",
    help={
        "name": "Only deploy paths declared by this [packages.*] section, e.g. agents-md.",
        "yes": "Overwrite a destination that was edited here without asking (the diff is still shown).",
    },
)
def all_(c: Context, name: str | None = None, yes: bool = False):
    """Deploy every path this repo declares under ~ — or one package's with --name — never
    destroying content PULSE can't prove it wrote.

    This is the repair path `inv deploy.status` points at, and the one command to reach for after
    editing any repo-side source (a `config/agents-md/` fragment, a `config_files` `src`, a skill under
    `skills/`): the install tasks only ever create a destination that doesn't exist yet, so a
    changed source never reaches an already-deployed file on its own. Per path: absent → created;
    unchanged since PULSE last wrote it → updated silently; edited at the destination → the full
    diff is printed first, then a prompt that defaults to *no* (so a piped/CI run without --yes
    leaves it alone); a `config_files` destination you customized is yours and is left alone
    unless --yes. `PULSE_DRY_RUN=1` reports without writing.
    """
    manifest = load_manifest()
    actions = [deploy(m, assume_yes=yes, manifest=manifest) for m in _scoped(name)]
    counts = {a: actions.count(a) for a in Action if actions.count(a)}
    summary = ", ".join(f"{n} {a}" for a, n in counts.items())
    print(f"[deploy] {len(actions)} path(s): {summary}")


def _has_pulse_block(target: Path) -> bool:
    """Whether a file the registry doesn't own nonetheless carries a PULSE-written block.

    util.ensure_block writes marker-delimited regions into files the *user* owns (~/.zshrc,
    ~/.zshenv, ~/.ssh/config, /etc/sysctl.conf, ...). Those aren't deploy destinations and this
    module never writes them — but reporting one as "not deployed by PULSE, an edit to it lives
    only on this machine" would be actively wrong, since re-running the task that wrote the block
    rewrites that region. Both marker styles embed the same "PULSE::" tag, so one scan covers both.
    """
    try:
        return "PULSE::" in target.read_text()
    except (OSError, UnicodeDecodeError):
        return False


def _status_one(target: Path) -> None:
    m = lookup(target)
    if m is None and _has_pulse_block(target):
        print(f"[deploy] {target}: not a deploy destination, but contains a PULSE-managed block")
        ui.note(
            f"{target} is yours — PULSE only owns the marked `PULSE::<name>` region(s) inside it, "
            "written by util.ensure_block (inv zsh.configure, ssh.configure, certs.*, proxy.*, "
            "system.*). Re-running the task that wrote a block rewrites that region and leaves the "
            "rest of the file untouched.",
            "Content outside those markers is never deployed, tracked, or restored by this repo.",
        )
        return
    if m is None:
        print(f"[deploy] {target}: not deployed by PULSE")
        ui.note(
            f"{target} isn't declared in setup.toml, so nothing here deploys, tracks, or restores "
            "it — an edit to it lives only on this machine.",
            "To bring it under PULSE, add a [packages.*] entry declaring it: `content_file` (with "
            'method = "wrapper-script") for a file this repo should own outright, or a '
            "`config_files` mapping for one PULSE seeds once and you own afterwards.",
        )
        return

    state = classify(m)
    print(f"[deploy] {m.package}: {m.path} — {SUMMARY[state]} (source: {m.source}, {m.policy})")
    if state in (State.DIRTY, State.UNKNOWN, State.STALE):
        print(diff(m))
