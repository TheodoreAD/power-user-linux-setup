"""One way to write a file into the home directory.

Every path this repo deploys under `~` goes through this module: the `wrapper-script` method's
`content_file` (`~/.agents/AGENTS.md`, `askpass-zenity`, ...) and any package's `config_files`
mappings (wezterm, terminator). Before this existed those were separate writers with different
answers to "the destination already exists" — unconditional overwrite, skip-if-exists,
diff-then-prompt — and the unconditional one silently ate hand-edits to `~/.agents/AGENTS.md` twice in one
day.

**Files only.** Skill *directories* used to be deployed here too, under `~/.agents/skills/`; that
mechanism was removed on 2026-09-07 when the `skills` CLI took over installing local skills as well
as remote ones. With it went `Mechanism.SKILL`, the `.pulse-source` marker, `dir_digest`, the
`is_dir` branch in every digest and write path, and the `copytree`/`rmtree` limb of `_write`.

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
from collections.abc import Iterator
from dataclasses import dataclass, replace
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
    # One destination composed from several repo-side fragments rather than copied from a single
    # source file — `~/.agents/AGENTS.md`, assembled from every `agents_md` fragment declared anywhere in
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

    @cached_property
    def src(self) -> Path:
        """Absolute repo-side source. Resolved against the repo root, never the cwd, so every
        caller works from any directory."""
        return _REPO_ROOT / self.source


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
    return hashlib.sha256(expected_bytes(m)).hexdigest()


def deployed_digest(m: Managed) -> str | None:
    """Digest of what's actually at the destination now, or None if nothing is."""
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
        # An assembled destination with no fragments would deploy an empty file — for ~/.agents/AGENTS.md
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


def managed_paths(base: Path | None = None) -> dict[Path, Managed]:
    """Every home-directory path this repo deploys, keyed by absolute destination.

    **No skills.** `_skill_entries` used to register every `source = "local"` skill here, because
    PULSE copied those directories itself. That copier was deleted on 2026-09-07 in favour of the
    `skills` CLI, which takes a local path directly — so keeping the registry entries would have
    been worse than useless: the registry would claim `~/.agents/skills/<name>` as a destination
    this repo deploys, `deploy.status` would report it MISSING forever, and nothing would ever
    write it. A registry entry is a promise that something writes that path.

    `base` was the skills root — the only mechanism it scoped. It is kept rather than removed
    because `lookup`, `status` and `all_` all thread it through to here, so dropping it is a
    signature change across four call sites for no behavioural gain; it becomes meaningful again
    the moment anything directory-shaped is deployed.
    """
    entries = (*_wrapper_script_entries(), *_config_file_entries())
    return {m.path: m for m in entries}


def lookup(path: Path | str, base: Path | None = None) -> Managed | None:
    """The registry entry for `path`, or None if this repo doesn't deploy it.

    Tries the path as given, then its resolved form. The second attempt used to be what made
    `~/.claude/CLAUDE.md` match the entry for its target back when it was a symlink; since
    2026-09-07 those destinations are copies and resolve to themselves, so the fallback now serves
    a machine still carrying the old links — `_replaceable` asks this question about one — plus any
    destination reached through a symlinked parent directory.
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
    try:
        before = m.path.read_bytes().decode().splitlines(keepends=True)
        after = expected_bytes(m).decode().splitlines(keepends=True)
    except UnicodeDecodeError:
        return "  (binary file — diff not shown)\n"
    lines = difflib.unified_diff(before, after, fromfile=str(m.path), tofile=m.source)
    return "".join(f"  {line}" if line.endswith("\n") else f"  {line}\n" for line in lines)


def _write(m: Managed) -> str:
    """Put the source content at the destination and return the digest actually landed.

    Re-reads rather than trusting the write: a full disk or a permission race should fail loudly
    here, before the manifest records it as ours, not silently surface later as a stale-looking
    file someone has to go diff by hand.
    """
    m.path.parent.mkdir(parents=True, exist_ok=True)
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
    entries = _scoped(name)
    actions = [deploy(m, assume_yes=yes, manifest=manifest) for m in entries]
    counts = {a: actions.count(a) for a in Action if actions.count(a)}
    summary = ", ".join(f"{n} {a}" for a, n in counts.items())
    print(f"[deploy] {len(actions)} path(s): {summary}")
    _deploy_mirrors(entries)


# ---------------------------------------------------------------------------
# Mirrored destinations
#
# An `also_deploy_to` is a home-directory path this repo creates and owns, which is this module's
# subject — it lived in tools.py only because the wrapper-script installer was its one caller.
# That made `inv deploy.all` unable to create one, while docs/ai.md told people it could, and
# the only command that did was `inv tools.install`, which re-runs every installer for every
# package. Moved here 2026-09-04 so the documented repair path is the real one.
#
# **These are copies, not symlinks, and were symlinks until 2026-09-07.** The field is named for
# the intent rather than the mechanism precisely because the mechanism turned out to be the part
# that changed. Three reasons, in the order they were found:
#
#   - Claude Code skips a `~/.claude/CLAUDE.md` that is itself a symlink or hard link in Cowork
#     sessions, and its shipped binary refuses `nlink > 1` in several other paths. The link was
#     already being ignored on one surface we care about, on Linux.
#   - On Windows a symlink needs Developer Mode or Administrator, a junction cannot stand in for a
#     *file* link (junctions are directories only, and every destination here is a file), and the
#     one privilege-free file mechanism is the hard link the vendor documents against. There is no
#     link to make.
#   - Anthropic's own documented Windows answer is an import or a copy, and its `/import` flow
#     copies `~/.codex/AGENTS.md` into `~/.claude/CLAUDE.md` rather than linking it.
#
# The cost is drift, which is a real cost and is what `classify`/`expected_digest` already exist to
# catch: a mirror is CLEAN only while it holds the deployed bytes, so `deploy.status` reports a
# stale one and `verify` fails it. What is bought is that every destination is a plain file that
# every agent, every platform and every git checkout treats identically.
# ---------------------------------------------------------------------------


def mirror_dests(cfg: util.PackageConfig) -> list[Path]:
    """`also_deploy_to`, as absolute paths.

    Accepts a bare string as well as a list: one destination is still the common case (a single
    wrapper script aliased under another name), and a list is what a file several agents each read
    from their own path needs — the instructions file is written into every installed agent's own
    instruction path. Same string-or-list shape as `omz_plugin`.

    Every destination is a vendor path and is therefore conditional: an absent `~/.codex/` means
    Codex isn't installed, so the mirror is skipped rather than created (see `ensure_mirror`). There
    used to be a `{ path = ..., always = true }` table form that opted out of that test, for the one
    destination no vendor owned — `~/AGENTS.md`, retired 2026-09-09. It never changed an outcome:
    that path's parent is the home directory, so the conditional test it opted out of would have
    passed anyway, which setup.toml's own comment conceded in the word "vacuously". The field
    reference in setup.toml never documented the table form, so this is the code returning to the
    schema rather than the schema losing anything.
    """
    declared = cfg.get("also_deploy_to")
    if not declared:
        return []
    entries = [declared] if isinstance(declared, str) else declared
    for entry in entries:
        # Kept from the table form's validation rather than dropped with it: a TOML author who
        # writes anything but a string here would otherwise reach `Path()` with a mapping and get a
        # message about `os.PathLike`, which says nothing about the field they got wrong.
        # The annotation says `list[str]`; TOML at runtime says whatever the author typed, and this
        # field carried a table form until 2026-09-09 that some setup.toml out there may still have.
        if not isinstance(entry, str):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError(f"also_deploy_to takes a path string or a list of them, got {entry!r}")
    return [Path(entry).expanduser() for entry in entries]


def mirror_ok(mirror: Path, dest: Path) -> bool:
    """Whether `mirror` already holds exactly what `dest` holds.

    A symlink is deliberately *not* ok, even one resolving to `dest`: that is the pre-2026-09-07
    wiring, and returning True for it would leave every existing machine on the old mechanism
    forever. `_replaceable` recognises it and `ensure_mirror` replaces it.
    """
    if mirror.is_symlink() or not mirror.is_file() or not dest.is_file():
        return False
    return mirror.read_bytes() == dest.read_bytes()


def _replaceable(managed: Managed, mirror: Path) -> bool:
    """Is what sits at `mirror` something this repo can prove it put there, unmodified?

    Two shapes, and both arise the moment a package's `dest` changes — which is not hypothetical:
    `agents-md` moved from `~/AGENTS.md` to `~/.agents/AGENTS.md` on 2026-09-04, and without this
    every existing machine would have ended up with two real files and every link still aimed at the
    old one. A stale link is not a hand-edit and must not be treated as one.

    - **a symlink into a path this repo has deployed** — a link PULSE made, now aimed at a previous
      destination, or one made under the pre-2026-09-07 wiring when these were links rather than
      copies. The manifest is the proof: a hand-made link to some file of the user's own is not in
      it. This branch is what migrates an existing machine, and it stays for as long as a machine
      might still carry one.
    - **a regular file this repo wrote and nobody has touched since** — `classify` against the same
      source says CLEAN or STALE. DIRTY or UNKNOWN keeps the existing refusal, because those are
      exactly the hand-edit this repo promises never to silently discard.
    """
    if mirror.is_symlink():
        target = mirror.resolve()
        return str(target) in load_manifest() or lookup(target) is not None
    return classify(replace(managed, path=mirror)) in (State.CLEAN, State.STALE)


def ensure_mirror(name: str, mirror: Path, dest: Path, managed: Managed) -> None:
    """Write `dest`'s bytes to the declared path, unless something else already lives there.

    **Never creates the parent directory of a vendor path.** A missing `~/.codex/` means Codex isn't
    installed, and creating it to hold an instruction file would leave a directory that makes an
    absent agent look present — the same detection rule the `skills` CLI uses when it picks which
    agents to install to. Says so rather than skipping silently, since "my rules didn't reach agent
    X" is otherwise a very quiet failure; installing that agent and re-running picks the file up.

    Copies the deployed file's bytes rather than re-deriving them from the source, so a mirror can
    never disagree with the destination it mirrors even if assembly is non-deterministic for some
    future package. `write_bytes` for the same reason `_write` uses it: no newline translation.
    """
    if mirror_ok(mirror, dest):
        return
    if mirror.exists() or mirror.is_symlink():
        if not _replaceable(managed, mirror):
            ui.warn(
                f"{mirror} already exists and isn't a copy of {dest}.",
                "Leaving it alone — move its content into the file above yourself, then re-run.",
            )
            return
        was = "symlink to" if mirror.is_symlink() else "copy of"
        mirror.unlink()
        print(f"[{name}] {mirror}: replaced a stale {was} this file")
    if not mirror.parent.is_dir():
        print(f"[{name}] {mirror}: skipped — {mirror.parent} doesn't exist (that agent isn't installed here)")
        return
    data = dest.read_bytes()
    mirror.write_bytes(data)
    # Record it, or the next deploy cannot tell this copy from a file somebody else put there.
    # A symlink was self-identifying — it either pointed at a deployed path or it didn't — and a
    # copy is not: `_replaceable` falls through to `classify`, which without a manifest entry
    # returns UNKNOWN for anything whose content has moved on, and `ensure_mirror` then refuses to
    # touch its own previous output. Caught by
    # `test_a_dest_change_rewrites_a_mirror_that_held_the_old_dests_content`, which failed exactly
    # that way: the mirror kept the old dest's content and the run reported "Leaving it alone".
    record(replace(managed, path=mirror), hashlib.sha256(data).hexdigest())
    print(f"[{name}] wrote {mirror} (copy of {dest})")


def _deploy_mirrors(entries: list[Managed]) -> None:
    """Write each deployed package's `also_deploy_to` copies, after its content is in place.

    This is why `mirror_dests`/`ensure_mirror` live in this module. Until 2026-09-04 they were
    reachable only from `tools._install_wrapper_script`, so `inv deploy.all` — the command
    `docs/ai.md` tells you to run to wire a newly-installed agent in — wrote content and nothing
    else, and the only thing that did write them re-ran every installer for every package.

    Ordered after the content deploy for the same reason the installer does it that way: a mirror
    should never be copied from a path that has not been written yet.

    Under `PULSE_DRY_RUN` this reports instead of writing. Reporting rather than staying silent is
    the point: the first version returned early, so a machine that would gain three mirrors printed
    `1 path(s): 1 created` and nothing else — a dry run that understates what the real run does is
    worse than no dry run, because it is the output someone checks *before* deciding to trust it.
    """
    packages = util.enabled_packages()
    seen: set[str] = set()
    for m in entries:
        if m.package in seen or m.mechanism not in (Mechanism.WRAPPER_SCRIPT, Mechanism.ASSEMBLED):
            continue
        seen.add(m.package)
        for mirror in mirror_dests(packages.get(m.package, {})):
            if util.DRY_RUN:
                print(f"[{m.package}] {_mirror_plan(mirror=mirror, dest=m.path, managed=m)}")
            else:
                ensure_mirror(m.package, mirror, m.path, m)


def _mirror_plan(*, mirror: Path, dest: Path, managed: Managed) -> str:
    """One line saying what `ensure_mirror` would do, without doing it.

    Mirrors that function's branches in the same order rather than summarising, so a dry run
    distinguishes the outcomes that actually differ: already correct, would be created, would be
    skipped because that agent isn't installed, would replace something this repo can prove it
    wrote, and would refuse to touch something it can't.
    """
    if mirror_ok(mirror, dest):
        return f"{mirror}: ok"
    if mirror.exists() or mirror.is_symlink():
        if not _replaceable(managed, mirror):
            return f"{mirror}: would leave alone — not a copy of {dest}"
        was = "symlink to" if mirror.is_symlink() else "copy of"
        return f"{mirror}: would replace a stale {was} this file"
    if not mirror.parent.is_dir():
        return f"{mirror}: would skip — {mirror.parent} doesn't exist (that agent isn't installed here)"
    return f"{mirror}: would write a copy of {dest}"


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
