"""Every path in `~` this repo has a claim on, however it got there.

`deploy.py` answers "is this path PULSE-managed?" for the one ownership model it implements —
whole-file writes it can prove it made. That is about a tenth of the real surface. The rest is
written by `util.ensure_block` marker regions, structured merges into co-owned JSON, in-place key
surgery in a file an application owns, `gsettings`/`dconf` calls with no file at a known path at
all, and installers that put a whole tree under `~`. None of those had a registry entry, so
`inv deploy.status --path` could only say "not deployed by PULSE" about most of the machine — true
of `deploy.py` and misleading about the repo. It is also narrower than `deploy.py` itself: a
destination decided at run time (the corporate systemd unit, the glob-discovered PyCharm options
directory) goes through the same writer but is deliberately not declared, so no registry-driven
command sees it.

This module is that missing registry: one entry per claim, classified on three independent axes
(`Writer`, `Authority`, `Tier`). It is deliberately **read-only and unopinionated** — it enumerates
and classifies, and never writes, prompts, or repairs.

Two rules that shape the design, both from
`plans/2026-08-29-dotfiles-repo-config-lifecycle.md`:

- **A registry entry does not imply a classifier.** Only `deploy.py` can tell CLEAN from DIRTY from
  STALE, because only it records what it wrote. A block, a merged JSON key and a dconf value each
  need their own notion of "dirty" that nobody has designed yet, so those claims report presence
  and nothing more. Reporting `—` is correct; inventing a state would be worse than silence.
- **The registry is a list, not a path-keyed mapping.** `deploy.managed_paths()` can be a dict
  because whole-file ownership is exclusive. Once blocks and key surgery are in scope, one path
  legitimately carries several claims — `~/.zshrc` holds both `ensure_block` regions and
  `zsh.configure-omz`'s in-place edits to `ZSH_THEME`/`plugins=`, from two different writers with
  two different notions of what a conflict means.

See `contributing/home-claims.md` for the rationale, and `contributing/deploy.md` for the
whole-file third this builds on.
"""

import json as jsonlib
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from invoke import Context, task

from . import certs, chrome, deploy, fonts, gnome, ide, proxy, screenshot, ssh, system, util

_HOME = Path.home()


class Writer(StrEnum):
    """How the bytes get there — and therefore what "drift" could even mean for this claim."""

    # deploy.py, from a setup.toml declaration: wrapper-script content_file, assembled
    # ~/AGENTS.md, config_files. In the registry, so `inv deploy.status` and `inv deploy.all`
    # see it and `inv verify.all` requires it to exist.
    WHOLE_FILE = "whole-file"
    # deploy.py, but with a destination decided at run time rather than declared — the systemd
    # unit only a corporate machine writes, the PyCharm options directory found by glob. Same
    # writer and the same never-clobber guarantee, so these classify exactly like the declared
    # ones; what they lack is a registry entry, which is deliberate, because every declared
    # destination is one `inv verify.all` demands after the packages phase.
    WHOLE_FILE_UNDECLARED = "whole-file-undeclared"
    # Composed by a task rather than copied from a repo source — identity.toml, written by a
    # wizard from answers. There is nothing to diff it against, so it can never be classified or
    # redeployed, and that is correct rather than a gap.
    GENERATED = "generated"
    # util.ensure_block marker regions inside a file the user owns.
    BLOCK = "block"
    # Structured merge into co-owned JSON — PULSE owns some keys, the user and other tools own the
    # rest of the document.
    MERGE = "merge"
    # In-place surgery on one key of a file some application owns, by regex rather than by parsing.
    KEY = "key"
    # No file at a knowable path: gsettings/dconf. The value is in a binary database keyed by
    # schema, and the only way to read one back is to ask the tool.
    IMPERATIVE = "imperative"
    # A symlink PULSE creates; the claim is the link and its target, not any bytes.
    SYMLINK = "symlink"
    # An installer puts a tree or a binary here. Content is upstream's, never this repo's — a
    # divergence is not drift, it is a version.
    INSTALL = "install"
    # Written by something this repo declares but does not implement — the `skills` CLI installing
    # from a remote repo.
    EXTERNAL = "external"


class Authority(StrEnum):
    """Who wins a conflict. Generalizes deploy.py's MANAGED/SEEDED split, which is the `pulse`/
    `user` pair of this axis."""

    PULSE = "pulse"
    USER = "user"
    CO_OWNED = "co-owned"
    APP = "app"


class Tier(StrEnum):
    """Where this claim's content lives **today** — a statement of fact about the current machine,
    not a recommendation about where it ought to live.

    That distinction is the whole reason this axis is reported rather than assigned, and
    `config/p10k.zsh` is the case that proves it: 1103 lines of one person's prompt, the most
    personal-looking file in the repo, and its owner ruled it a deliberate public default
    (2026-08-30) — "the point of pulse is awesome smart defaults". An inventory that had guessed
    `personal` from the shape of the content would have been wrong, and confidently so.

    `PERSONAL` and `UNASSIGNED` are part of the vocabulary and carry zero claims today. That zero is
    itself the measurement: nothing in `~` is personal-but-homeless, because everything PULSE writes
    is either a public default, machine-bound, secret, or regenerable.
    """

    PUBLIC = "public"  # content comes from this public repo
    PERSONAL = "personal"  # a preference wanted on every machine — no home for this yet
    MACHINE = "machine"  # true of this box only
    SECRET = "secret"  # never in any repo without encryption
    DERIVED = "derived"  # state, caches, installed trees — regenerable, never versioned
    UNASSIGNED = "unassigned"  # exists only here, with no repo-side source and not regenerable


@dataclass(frozen=True)
class Claim:
    """One thing under `~` this repo has a claim on.

    `target` is a display string rather than a `Path` because not every claim is a file:
    a gsettings key and a dconf path are claims with no filesystem location at all. `path` carries
    the filesystem location when there is one, which is what lets presence be reported without
    every consumer re-parsing `target`.
    """

    target: str
    writer: Writer
    authority: Authority
    tier: Tier
    owner: str  # the [packages.*] section, or the `inv` task, that writes it
    source: str = ""  # repo-side origin, where there is one
    note: str = ""
    path: Path | None = None
    # The deploy.py entry, for a claim that goes through that writer — carried rather than
    # re-derived so a state comes from the same object the writer acts on.
    managed: deploy.Managed | None = None

    @property
    def classifiable(self) -> bool:
        """Whether any writer can currently tell "we wrote this" from "someone edited it".

        Only deploy.py records what it wrote, so only claims it writes can. Everything else reports
        presence, and says so, rather than guessing.
        """
        return self.managed is not None


# Paths whose content an application rewrites underneath PULSE, so `user` authority would overstate
# the user's control: the app is a second writer and wins by simply running.  Terminator is the
# standing live example in contributing/deploy.md; Chrome rewrites its own PWA launchers on every
# install/update, which `inv chrome.fix-launchers` exists to repair rather than to prevent.
_APP_OWNED = frozenset(
    {
        _HOME / ".config" / "terminator" / "config",
        _HOME / ".config" / "google-chrome" / "Local State",
    }
)

# System paths outside `~` that this repo also writes. Out of scope for an inventory whose subject
# is the home surface — a dotfiles lifecycle can never cover a root-owned file — but counted in the
# footer so nothing reads this registry as the whole of what PULSE touches.
SYSTEM_TARGETS = (
    "/etc/sysctl.conf",
    "/etc/initramfs-tools/initramfs.conf",
    "/etc/systemd/journald.conf.d/",
    "/etc/systemd/resolved.conf.d/",
    "/etc/apt/apt.conf.d/99-pulse",
    "/etc/apparmor.d/",
    "/etc/docker/daemon.json",
    "/etc/wsl.conf",
    "/usr/local/share/ca-certificates/pulse-corporate.crt",
)


def _under_home(path: Path) -> bool:
    return path == _HOME or _HOME in path.parents


def _rel(path: Path) -> str:
    """`~`-relative display form, so the listing lines up and never leaks the username."""
    return f"~/{path.relative_to(_HOME)}" if _under_home(path) and path != _HOME else str(path)


# ---------------------------------------------------------------------------
# Whole-file — deploy.py's registry, plus the writers it hasn't absorbed
# ---------------------------------------------------------------------------


def _whole_file_claims() -> Iterator[Claim]:
    """deploy.py's own registry, re-expressed on the three axes.

    Derived, never restated: `managed_paths()` is the source of truth for this third and the two
    must not be able to disagree. The `MANAGED`/`SEEDED` policy it already carries *is* the
    authority axis for these claims.
    """
    for m in deploy.managed_paths().values():
        yield Claim(
            target=_rel(m.path),
            writer=Writer.WHOLE_FILE,
            authority=(
                Authority.APP
                if m.path in _APP_OWNED
                else Authority.PULSE
                if m.policy == deploy.Policy.MANAGED
                else Authority.USER
            ),
            tier=Tier.PUBLIC,
            owner=m.package,
            source=m.source,
            note=str(m.mechanism),
            path=m.path,
            managed=m,
        )


def _symlink_claims() -> Iterator[Claim]:
    """`symlink_dest` links pointing at a deployed file — `~/.claude/CLAUDE.md` -> `~/AGENTS.md`.

    `deploy.lookup()` resolves these onto their target's entry, which is right for "what content
    should be here" and wrong for an inventory: the link is a separate thing this repo creates in
    the home directory, and nothing else enumerates it.
    """
    for name, cfg in util.packages_by_method(util.PackageMethod.WRAPPER_SCRIPT).items():
        dest = cfg.get("dest")
        if not dest:
            continue
        # Via deploy.symlink_dests rather than re-normalising here: `symlink_dest` takes a string, a
        # list, or a `{ path, always }` table, and a second copy of that parsing is a second place
        # to forget a shape. It was one before the table existed, and a dict would have reached
        # `Path()` as a mapping.
        for link in deploy.symlink_dests(cfg):
            path = link.path
            yield Claim(
                target=_rel(path),
                writer=Writer.SYMLINK,
                authority=Authority.PULSE,
                tier=Tier.PUBLIC,
                owner=name,
                source=str(Path(dest).expanduser()),
                note="symlink_dest",
                path=path,
            )


def _undeclared_whole_file_claims() -> Iterator[Claim]:
    """Whole files deployed through deploy.py whose destination isn't in setup.toml.

    Not a lesser class of claim: they carry a real `Managed`, so they get the manifest entry, the
    diff and the never-clobber rule, and they classify exactly like a declared one. What they lack
    is a registry entry, and that is deliberate — every declared destination is one
    `inv verify.all` requires to exist at the end of the packages phase, while these are written
    only when something on this machine calls for them.

    Read from the writing module's own objects (`proxy.UNIT`, `ide.managed_files()`) rather than
    restated here, so the inventory and the writer cannot disagree about the destination. That
    matters most for PyCharm, whose destination is a glob resolved against what is installed:
    with no PyCharm here there are no claims, which is the right answer rather than two rows
    reporting a file absent that was never going to exist.
    """
    for m in (proxy.UNIT, *ide.managed_files()):
        yield Claim(
            target=_rel(m.path),
            writer=Writer.WHOLE_FILE_UNDECLARED,
            authority=Authority.PULSE,
            tier=Tier.PUBLIC,
            owner=m.package,
            source=m.source,
            note="destination decided at run time, not declared in setup.toml",
            path=m.path,
            managed=m,
        )

    # identity.toml holds this machine's emails and corporate proxy host — the one claim on the
    # surface that must never reach any repo, encrypted or not. Composed by a wizard from answers
    # rather than copied from a source, so there is nothing to diff it against and it stays outside
    # deploy.py on purpose.
    yield Claim(
        target=_rel(util.IDENTITY_PATH),
        writer=Writer.GENERATED,
        authority=Authority.USER,
        tier=Tier.SECRET,
        owner="inv identity.init",
        source="config/identity.toml.example (a template, not a source to compare against)",
        path=util.IDENTITY_PATH,
    )


# ---------------------------------------------------------------------------
# Block — util.ensure_block marker regions in files the user owns
# ---------------------------------------------------------------------------


def _block_claims() -> Iterator[Claim]:
    """One claim per (file, block) pair, not per file.

    A file's blocks are independently owned: `~/.zshenv` carries a `certs` block written from
    identity.toml, a `proxy` block written from the same, and one block per package declaring a
    `zshenv` snippet in setup.toml. Collapsing them to one row per file would hide that two of
    those have machine-local content and the rest are public — which is the distinction the tier
    axis exists to make.
    """
    for name, cfg in util.enabled_packages().items():
        for field in ("zshrc", "zshenv", "zprofile"):
            if cfg.get(field):
                path = _HOME / f".{field}"
                yield Claim(
                    target=f"{_rel(path)} [PULSE::{name}]",
                    writer=Writer.BLOCK,
                    authority=Authority.CO_OWNED,
                    tier=Tier.PUBLIC,
                    owner=name,
                    source=f"setup.toml [packages.{name}] {field}",
                    path=path,
                )

    # Blocks whose content is computed by a task rather than declared in setup.toml. The two
    # identity-derived ones are the only home content on this machine that is genuinely
    # machine-local rather than public — a corporate CA bundle path and a proxy host.
    coded: tuple[tuple[Path, str, str, str, Tier], ...] = (
        (ssh.SSH_CONFIG, "ssh", "inv ssh.configure", "identity.toml hosts", Tier.MACHINE),
        (certs.ZSHENV, "certs", "inv certs.install", "identity.toml [certs]", Tier.MACHINE),
        (proxy.ZSHENV, "proxy", "inv proxy.install", "identity.toml [proxy]", Tier.MACHINE),
        (system.CURLRC, "curlrc", "inv system.write-curlrc", "tasks/system.py", Tier.PUBLIC),
    )
    for path, block, owner, source, tier in coded:
        yield Claim(
            target=f"{_rel(path)} [PULSE::{block}]",
            writer=Writer.BLOCK,
            authority=Authority.CO_OWNED,
            tier=tier,
            owner=owner,
            source=source,
            path=path,
        )


# ---------------------------------------------------------------------------
# Merge / key — structured and unstructured surgery on files someone else owns
# ---------------------------------------------------------------------------


def _merge_claims() -> Iterator[Claim]:
    yield Claim(
        target=_rel(util.CLAUDE_SETTINGS),
        writer=Writer.MERGE,
        authority=Authority.CO_OWNED,
        tier=Tier.PUBLIC,
        owner="inv ai.install-skills, inv allowlist.apply",
        source="setup.toml claude_* fields, cli-allowlist/",
        note="6 call sites through util.write_claude_settings",
        path=util.CLAUDE_SETTINGS,
    )
    # VS Code's settings.json lives in one of two places depending on how it was installed, and
    # fonts.py picks whichever parent directory exists. Reporting the one it would pick keeps the
    # inventory honest about which file is actually claimed on this machine.
    vscode = next((p for p in fonts.VSCODE_SETTINGS_PATHS if p.parent.exists()), None)
    yield Claim(
        target=_rel(vscode) if vscode else "~/.config/Code/User/settings.json (not installed)",
        writer=Writer.MERGE,
        authority=Authority.CO_OWNED,
        tier=Tier.PUBLIC,
        owner="inv fonts.configure",
        source="setup.toml [settings.fonts] vscode",
        note="whichever of two install layouts exists",
        path=vscode,
    )


def _key_claims() -> Iterator[Claim]:
    zshrc = _HOME / ".zshrc"
    yield Claim(
        target=f"{_rel(zshrc)} [ZSH_THEME, plugins=]",
        writer=Writer.KEY,
        authority=Authority.CO_OWNED,
        tier=Tier.PUBLIC,
        owner="inv zsh.configure-omz",
        source="setup.toml [packages.oh-my-zsh] theme/plugins",
        note="regex surgery, outside any PULSE:: marker",
        path=zshrc,
    )
    yield Claim(
        target=f"{_rel(screenshot.FLAMESHOT_INI)} [General]",
        writer=Writer.KEY,
        authority=Authority.APP,
        tier=Tier.PUBLIC,
        owner="inv screenshot.enable",
        source="tasks/screenshot.py",
        note="Qt ini; Flameshot rewrites the file",
        path=screenshot.FLAMESHOT_INI,
    )
    launchers = chrome.APPLICATIONS_DIR / "*.desktop"
    yield Claim(
        target=f"{_rel(launchers)} [Name, Exec, NoDisplay]",
        writer=Writer.KEY,
        authority=Authority.APP,
        tier=Tier.PUBLIC,
        owner="inv chrome.fix-launchers",
        source="tasks/chrome.py",
        note="Chrome rewrites these on PWA install/update",
    )


# ---------------------------------------------------------------------------
# Imperative — gsettings/dconf, where there is no path to look at
# ---------------------------------------------------------------------------


def _imperative_claims() -> Iterator[Claim]:
    """dconf keys declared per extension in setup.toml, plus the ones hard-coded in tasks.

    These are the claims with no filesystem location at all, so `path` stays None and presence is
    unanswerable without shelling out to `gsettings`/`dconf` — which this command deliberately does
    not do: it must stay read-only *and* runnable with no live session, including in a container.
    """
    for name, cfg in util.enabled_packages().items():
        for key in cfg.get("dconf", {}):
            yield Claim(
                target=f"dconf {key}",
                writer=Writer.IMPERATIVE,
                authority=Authority.CO_OWNED,
                tier=Tier.PUBLIC,
                owner=name,
                source=f"setup.toml [packages.{name}.dconf]",
            )

    coded = (
        ("gsettings org.gnome.shell disable-user-extensions", "inv gnome.install-extensions"),
        ("gsettings org.gnome.desktop.interface monospace-font-name", "inv fonts.configure"),
        ("gsettings org.gnome.Terminal.Legacy.Profile font/use-system-font", "inv fonts.configure"),
        ("gsettings org.gnome.settings-daemon.plugins.media-keys custom-keybindings", "inv screenshot.enable"),
        ("gsettings org.gnome.shell.keybindings screenshot*", "inv screenshot.enable"),
    )
    for target, owner in coded:
        yield Claim(
            target=target,
            writer=Writer.IMPERATIVE,
            authority=Authority.CO_OWNED,
            tier=Tier.PUBLIC,
            owner=owner,
            source="tasks/" + owner.split()[1].split(".")[0] + ".py",
        )


# ---------------------------------------------------------------------------
# Install — trees and binaries an installer puts under ~
# ---------------------------------------------------------------------------

_LOCAL_BIN = _HOME / ".local" / "bin"


def _install_targets(name: str, cfg: util.PackageConfig) -> Iterator[tuple[Path, str]]:
    """Every home path a package's installer creates, with the field that declared it.

    Derived from setup.toml rather than listed, so a package added tomorrow appears here without
    anyone remembering to. Only the destination is claimed, never its contents: what is inside an
    installed tree is upstream's, and enumerating it would be a file listing, not a registry.

    Split in two along the only line that matters for reading it back: a path some field names
    outright, and a name that resolves under `~/.local/bin`.
    """
    yield from _declared_targets(cfg)
    yield from _bin_targets(name, cfg)


def _declared_targets(cfg: util.PackageConfig) -> Iterator[tuple[Path, str]]:
    """Destinations a setup.toml field spells out as a path."""
    # `dest` means a clone destination only for git-clone; on wrapper-script it is a deployed file,
    # which deploy.py already owns and this would double-claim.
    if (dest := cfg.get("dest")) and cfg.get("method") == util.PackageMethod.GIT_CLONE:
        yield Path(dest).expanduser(), "dest"
    if install_dir := cfg.get("install_dir"):
        yield Path(install_dir).expanduser(), "install_dir"
    if check_path := cfg.get("check_path"):
        yield Path(check_path).expanduser(), "check_path"
    if cfg.get("single_binary"):
        # A single_binary package's `env` names the install *prefix* (dprint: DPRINT_INSTALL =
        # "~/.local"), not a destination — claiming it verbatim would put the whole XDG root in the
        # registry on the strength of one binary. _bin_targets claims that binary instead.
        return
    for value in cfg.get("env", {}).values():
        if value.startswith("~"):
            yield Path(value).expanduser(), "env"


def _bin_targets(name: str, cfg: util.PackageConfig) -> Iterator[tuple[Path, str]]:
    """Names that land in `~/.local/bin` — the binary itself, or a symlink to it."""
    check = cfg.get("check_cmd", name)
    if bin_pick := cfg.get("bin_pick"):
        yield _LOCAL_BIN / bin_pick, "bin_pick"
    if cfg.get("method") in (util.PackageMethod.BINARY, util.PackageMethod.UV_TOOL):
        yield _LOCAL_BIN / check, "method"
    if cfg.get("symlink_from"):
        yield _LOCAL_BIN / check, "symlink_from"
    if cfg.get("single_binary"):
        yield _LOCAL_BIN / check, "single_binary"
    for link in cfg.get("symlinks", []):
        yield _LOCAL_BIN / link["dst"], "symlinks"


def _install_claims() -> Iterator[Claim]:
    seen: set[Path] = set()
    for name, cfg in util.enabled_packages().items():
        for path, field in _install_targets(name, cfg):
            if not _under_home(path) or path in seen:
                continue
            seen.add(path)
            yield Claim(
                target=_rel(path),
                writer=Writer.INSTALL,
                authority=Authority.PULSE,
                tier=Tier.DERIVED,
                owner=name,
                source=f"setup.toml [packages.{name}] {field}",
                path=path,
            )

    # Read directly from load_config() rather than enabled_packages(), mirroring node.install:
    # setup.toml's header states that [packages.node]'s enabled/tags are deliberately not checked,
    # so filtering here would make the registry disagree with the installer.
    node_cfg = util.load_config()["packages"].get("node", {})
    nvm_dir = Path(node_cfg.get("nvm_dir", "~/.local/share/nvm")).expanduser()
    yield Claim(
        target=_rel(nvm_dir),
        writer=Writer.INSTALL,
        authority=Authority.PULSE,
        tier=Tier.DERIVED,
        owner="node",
        source="setup.toml [packages.node] nvm_dir",
        note="plus the node versions and global npm packages inside it",
        path=nvm_dir,
    )

    coded = (
        (fonts.FONTS_DIR, "inv fonts.install", "setup.toml [settings.fonts] families"),
        (gnome.USER_EXT_DIR, "inv gnome.install-extensions", "setup.toml gnome-extension uuid/ego_id"),
        (util.PULSE_STATE_DIR, "deploy/ai/allowlist manifests", "generated per machine"),
        (util.OVERRIDES_PATH, "hand-written", "machine-local, deliberately out of git"),
    )
    for path, owner, source in coded:
        yield Claim(
            target=_rel(path),
            writer=Writer.INSTALL,
            authority=Authority.PULSE,
            # overrides.toml is the one machine-local *declaration* on the surface rather than
            # regenerable state: losing it changes which packages this machine installs.
            tier=Tier.MACHINE if path == util.OVERRIDES_PATH else Tier.DERIVED,
            owner=owner,
            source=source,
            path=path,
        )


# ---------------------------------------------------------------------------
# External — written by something this repo declares but does not implement
# ---------------------------------------------------------------------------


def _external_claims() -> Iterator[Claim]:
    """Skills installed by the `skills` CLI, and the directory they land in.

    `deploy._skill_entries` only registers `source = "local"` skills, and this repo deliberately
    declares none — every skill is authored in `agent-skills` and fetched from its remote. So the
    whole of `~/.agents/skills/` is claimed by setup.toml and invisible to the deploy registry.

    A remote entry without a `names` field cannot be expanded without the network, so the claim is
    the directory rather than one row per skill: an inventory that needs a network call to be
    complete is not one you can trust offline.
    """
    for name, cfg in util.load_config()["packages"].items():
        if not cfg.get("enabled", True):
            continue
        for entry in cfg.get("skills", []):
            if entry.get("source") != "npx":
                continue
            names = entry.get("names")
            path = _HOME / ".agents" / "skills"
            yield Claim(
                target=f"{_rel(path)}/  ({', '.join(names)})" if names else f"{_rel(path)}/",
                writer=Writer.EXTERNAL,
                authority=Authority.PULSE,
                tier=Tier.PUBLIC,
                owner=name,
                source=f"skills CLI <- {entry.get('repo', '?')}",
                note="skill names not knowable offline" if not names else "",
                path=path,
            )

    claude_skills = _HOME / ".claude" / "skills"
    yield Claim(
        target=_rel(claude_skills),
        writer=Writer.SYMLINK,
        authority=Authority.PULSE,
        tier=Tier.PUBLIC,
        owner="inv ai.install-skills",
        source=str(_HOME / ".agents" / "skills"),
        note="never replaces existing non-symlink content",
        path=claude_skills,
    )


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------


def claims() -> list[Claim]:
    """Every claim this repo has on the home directory, in writer order.

    Pure: reads `setup.toml` and the filesystem, never writes and never shells out. It must stay
    runnable with no GNOME session and no network, which is why a dconf claim reports no value and
    a remote skill entry reports no skill names.
    """
    return [
        *_whole_file_claims(),
        *_undeclared_whole_file_claims(),
        *_symlink_claims(),
        *_block_claims(),
        *_merge_claims(),
        *_key_claims(),
        *_imperative_claims(),
        *_install_claims(),
        *_external_claims(),
    ]


def state_of(claim: Claim, manifest: deploy.Manifest) -> str:
    """One word for what is at this claim's target now.

    A real `deploy.State` where a writer can prove what it wrote; otherwise presence, which is all
    that is knowable — and `—` where even presence isn't, because the claim has no path.

    `manifest` is threaded through so a whole listing reads the state file once rather than once
    per claim.
    """
    if claim.managed is not None:
        return str(deploy.classify(claim.managed, manifest))
    if claim.path is None:
        return "—"
    return "present" if claim.path.exists() else "absent"


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


def _rows(selected: list[Claim]) -> list[tuple[str, str, str, str, str, str]]:
    manifest = deploy.load_manifest()
    return [(str(c.writer), str(c.authority), str(c.tier), state_of(c, manifest), c.target, c.owner) for c in selected]


def _print_table(rows: list[tuple[str, str, str, str, str, str]]) -> None:
    headers = ("writer", "authority", "tier", "state", "target", "owner")
    widths = [max(len(r[i]) for r in (*rows, headers)) for i in range(len(headers))]
    print("  ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True)).rstrip())
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print("  ".join(cell.ljust(w) for cell, w in zip(row, widths, strict=True)).rstrip())


def _print_summary(selected: list[Claim], everything: list[Claim]) -> None:
    """Counts for what was selected, but the headline number always for the whole surface.

    A coverage percentage computed over a filtered view answers a question nobody asked — filter to
    `install` and "0% of the non-derived surface" is arithmetically true and says nothing about the
    machine. The denominator that matters is fixed.
    """
    by_writer = Counter(str(c.writer) for c in selected)
    by_tier = Counter(str(c.tier) for c in selected)
    # Installed trees and generated state can never be the subject of a config lifecycle: their
    # content is upstream's or regenerable, so counting them would flatter any coverage number.
    lifecycle = [c for c in everything if c.tier != Tier.DERIVED]
    # `generated` is not reachable and never will be: identity.toml has no repo-side source to sync
    # against, and its content is the one thing on the surface that must reach no repo at all.
    whole_file = [c for c in lifecycle if c.writer in (Writer.WHOLE_FILE, Writer.WHOLE_FILE_UNDECLARED)]
    declared = [c for c in whole_file if c.writer == Writer.WHOLE_FILE]

    print(f"\n[home] {len(selected)} claim(s)" + (f" of {len(everything)}" if len(selected) != len(everything) else ""))
    for writer, count in by_writer.most_common():
        print(f"[home]   {writer:<18} {count:>3}")
    print("[home] by tier (where the content lives today, not where it should):")
    for tier, count in by_tier.most_common():
        print(f"[home]   {tier:<18} {count:>3}")

    if lifecycle:
        print(
            f"\n[home] a whole-file-only lifecycle would reach {len(whole_file)}/{len(lifecycle)} "
            f"({len(whole_file) * 100 // len(lifecycle)}%) of the non-derived surface. All of them go "
            f"through deploy.py and can be classified; {len(declared)} are declared in setup.toml, so "
            "the rest are invisible to `inv deploy.status`."
        )
    print(f"[home] {len(SYSTEM_TARGETS)} further target(s) outside ~ are written by this repo and out of scope here.")
    print("[home] skill-written config (~/.config/plan-docs, ~/.config/tasks-md) is deliberately not claimed:")
    print("[home]   this repo declares the skill, not the skill's config — see contributing/home-claims.md.")


@task(
    name="list-claims",
    help={
        "writer": "Only show claims written this way, e.g. block, merge, imperative, install.",
        "tier": "Only show claims whose content lives in this tier today, e.g. machine, derived.",
        "json": "Emit the registry as JSON instead of a table.",
    },
)
def list_claims(c: Context, writer: str | None = None, tier: str | None = None, json: bool = False):
    """List every path in ~ this repo has a claim on, classified by writer, authority and tier.

    Strictly read-only, and deliberately wider than `inv deploy.status`: that command reports the
    whole-file third it can also repair, while this one reports the whole surface — marker blocks,
    merged JSON, key surgery, gsettings/dconf, installed trees and skills — so that "is this path
    PULSE-managed?" has one answer instead of a true-but-misleading no.

    The `state` column is a real `deploy` state only for claims the deploy manifest covers.
    Everything else reports presence, because no other writer records what it wrote — a block, a
    merged key and a dconf value each need their own notion of "dirty" that does not exist yet.
    A claim with no filesystem location at all reports `—`.
    """
    everything = claims()
    selected = everything
    if writer:
        selected = [x for x in selected if x.writer == writer]
    if tier:
        selected = [x for x in selected if x.tier == tier]

    if json:
        print(
            jsonlib.dumps(
                [
                    {
                        "target": x.target,
                        "writer": str(x.writer),
                        "authority": str(x.authority),
                        "tier": str(x.tier),
                        "owner": x.owner,
                        "source": x.source,
                        "note": x.note,
                        "path": str(x.path) if x.path else None,
                        "classifiable": x.classifiable,
                    }
                    for x in selected
                ],
                indent=2,
            )
        )
        return

    if not selected:
        print("[home] no claims match that filter")
        return

    _print_table(_rows(selected))
    _print_summary(selected, everything)
