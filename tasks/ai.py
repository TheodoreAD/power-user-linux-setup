import hashlib
import json
import shlex
import shutil
from pathlib import Path

from invoke import task

from . import ui, util

_REPO_ROOT = Path(__file__).parent.parent
_CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
# Deliberately separate from tasks/allowlist.py's _APPLIED_MANIFEST — that one tracks
# CLI-classification-derived Bash rules specifically; this tracks static, hand-declared rules
# from any setup.toml package's claude_permissions_allow field. Same safe-merge pattern (only
# rule strings we previously wrote are ever removed), different manifest, so the two mechanisms
# can never step on each other's rules even though they touch the same settings.json file.
_STATIC_PERMS_MANIFEST = Path.home() / ".local" / "state" / "pulse" / "claude-static-permissions-applied.json"
_SKILL_MARKER = ".pulse-source"


def _dir_digest(path: Path) -> str:
    """Hash of a skill directory's file contents, keyed by relative path — order-independent,
    ignores the marker file itself so a freshly-copied dest compares equal to its source."""
    h = hashlib.sha256()
    for f in sorted(path.rglob("*")):
        if f.is_file() and f.name != _SKILL_MARKER:
            h.update(f.relative_to(path).as_posix().encode())
            h.update(f.read_bytes())
    return h.hexdigest()


def _install_local_skill(base: Path, repo_path: str, *, label: str) -> None:
    """Copy this repo's skills/<name>/ to <base>/.agents/skills/<name> (source = "local") — a
    real, standalone copy, not a symlink, matching how the npx-sourced installer behaves (it
    also copies, per its own install summary output). A `.pulse-source` marker records which
    setup.toml-declared path installed it, so re-runs can tell "ours, safe to refresh" apart
    from "foreign content, don't touch" the same way _ensure_agents_skills does for the
    .claude/skills symlink — without a marker, two directory copies are indistinguishable by
    content alone. Refreshed to exactly match the repo on every run once it's ours; an edit to
    the repo copy needs `inv ai.skills` re-run to take effect, unlike the old symlink approach.
    """
    src = (_REPO_ROOT / repo_path).resolve()
    name = src.name
    dest = base / ".agents" / "skills" / name
    present = dest.exists() or dest.is_symlink()
    marker = dest / _SKILL_MARKER
    ours = marker.is_file() and marker.read_text().strip() == repo_path
    up_to_date = ours and _dir_digest(dest) == _dir_digest(src)

    if util.DRY_RUN:
        print(f"[{label}] {name}: {'ok' if up_to_date else 'MISSING'}")
        return

    if present and not ours:
        ui.warn(
            f"{dest} already exists and wasn't installed by this entry ({repo_path}).",
            "Leaving it alone — remove it yourself and re-run to install the repo's copy.",
        )
        return

    if up_to_date:
        print(f"[{label}] {name} already up to date")
        return

    if present:
        dest.unlink() if dest.is_symlink() else shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)
    marker.write_text(repo_path + "\n")
    print(f"[{label}] {name} copied from {repo_path}")


def _install_remote_skill(c, entry: dict, *, label: str) -> None:
    """Install a skill from a GitHub repo via the `skills` CLI (source = "npx").

    Always global + non-interactive (this is unattended provisioning, not a project-local,
    interactive `skills add`). `names` omitted installs every skill in the repo; `agents`
    defaults to just claude-code, since that's the one this repo actively manages (its
    .claude/skills is symlinked to .agents/skills, so this converges on the same shared
    directory local skills use, not a separate claude-code-only copy).
    """
    repo = entry["repo"]
    names = entry.get("names")
    agents = entry.get("agents", ["claude-code"])
    desc = f"{', '.join(names) if names else 'all skills'} from {repo}"

    if util.DRY_RUN:
        print(f"[{label}] {desc}: not checked in dry-run (would run `skills add`)")
        return

    cmd = ["skills", "add", repo, "--global", "--yes"]
    for a in agents:
        cmd += ["--agent", a]
    cmd += ["--skill", *(names or ["*"])]
    c.run(shlex.join(cmd))
    print(f"[{label}] installed {desc}")


def _install_declared_skills(c, base: Path) -> None:
    """Process every `skills` list found on any setup.toml package entry, regardless of that
    entry's own `method` — same any-section pattern as zshenv/zshrc/zprofile.
    """
    for name, cfg in util.load_config()["packages"].items():
        if not cfg.get("enabled", True):
            continue
        for entry in cfg.get("skills", []):
            source = entry.get("source")
            if source == "local":
                _install_local_skill(base, entry["path"], label=name)
            elif source == "npx":
                _install_remote_skill(c, entry, label=name)
            else:
                ui.warn(f"[{name}] skills entry has unknown source {source!r} — skipping")


def _apply_static_claude_permissions() -> None:
    """Merge every setup.toml-declared `claude_permissions_allow` rule (checked on any package
    entry, any method — same any-section pattern as `skills`/`zshenv`) into
    ~/.claude/settings.json's permissions.allow.

    Same safe-merge shape as tasks/allowlist.py's `apply` — every other key in the file untouched,
    a backup written before any real change, and only rule strings *this* mechanism wrote last
    time are eligible for removal (tracked in `_STATIC_PERMS_MANIFEST`, not allowlist.py's own
    manifest) — but deliberately not that module's code path: these are static, hand-declared
    rules, not CLI-classification output, and keeping the two mechanisms' manifests separate means
    neither can ever remove a rule the other one owns.
    """
    declared = sorted(
        {
            rule
            for cfg in util.load_config()["packages"].values()
            if cfg.get("enabled", True)
            for rule in cfg.get("claude_permissions_allow", [])
        }
    )

    settings = json.loads(_CLAUDE_SETTINGS.read_text()) if _CLAUDE_SETTINGS.exists() else {}
    existing_allow = settings.get("permissions", {}).get("allow", [])

    if util.DRY_RUN:
        missing = [r for r in declared if r not in existing_allow]
        print(f"[ai.skills] static Claude permissions: {'ok' if not missing else f'MISSING {len(missing)}'}")
        return

    previous = set(json.loads(_STATIC_PERMS_MANIFEST.read_text())) if _STATIC_PERMS_MANIFEST.exists() else set()
    kept = [r for r in existing_allow if r not in previous]
    merged = kept + [r for r in declared if r not in kept]

    if set(merged) == set(existing_allow):
        print(f"[ai.skills] static Claude permissions: already up to date ({len(declared)} rule(s))")
        return

    perms = settings.setdefault("permissions", {})
    perms["allow"] = merged

    if _CLAUDE_SETTINGS.exists():
        _CLAUDE_SETTINGS.with_suffix(".json.bak").write_text(_CLAUDE_SETTINGS.read_text())
    _CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    _CLAUDE_SETTINGS.write_text(json.dumps(settings, indent=2) + "\n")

    _STATIC_PERMS_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    _STATIC_PERMS_MANIFEST.write_text(json.dumps(declared, indent=2) + "\n")
    print(f"[ai.skills] {_CLAUDE_SETTINGS}: static permissions updated ({len(declared)} rule(s))")


def _copilot_present() -> bool:
    ext_dir = Path.home() / ".vscode" / "extensions"
    return ext_dir.is_dir() and any(ext_dir.glob("github.copilot-*"))


def _note_copilot_permissions() -> None:
    """Check for GitHub Copilot and say plainly why nothing gets written for it, rather than
    guessing at a settings.json key and shipping a rule that might be wrong or a no-op.

    Researched, not assumed: VS Code Copilot Chat has `chat.tools.terminal.autoApprove` (terminal
    commands — already handled by tasks/allowlist.py's `inv allowlist.render --target=copilot`)
    and `chat.tools.urls.autoApprove` (URL fetches), but no confirmed, documented equivalent for
    path-scoped *file-read* auto-approval the way Claude's `Read(pattern)` rules work — only a
    global `github.copilot.chat.agent.autoApproveFileChanges` boolean, which isn't the same thing
    (it's for edits, not reads, and it's all-or-nothing rather than scoped to one directory).
    Revisit if a scoped-read key is ever confirmed.
    """
    if _copilot_present():
        print(
            "[ai.skills] GitHub Copilot detected — no permissions applied for it. No confirmed, "
            "path-scoped file-read auto-approve setting exists for Copilot Chat (see "
            "docs/claude-code.md); not guessing at one."
        )


def _ensure_agents_skills(base: Path, *, label: str) -> None:
    """Ensure <base>/.agents/skills exists and <base>/.claude/skills is a symlink to it.

    .agents/skills is the emerging cross-tool convention for agent skills; Claude Code itself
    doesn't read it natively yet, only .claude/skills, so the symlink is what actually makes
    skills placed there visible to Claude Code today. Never touches an existing .claude/skills
    that isn't already that exact symlink — real content there is left alone, not overwritten.
    """
    agents_skills = base / ".agents" / "skills"
    claude_skills = base / ".claude" / "skills"

    already_linked = claude_skills.is_symlink() and claude_skills.resolve() == agents_skills.resolve()
    if util.DRY_RUN:
        print(f"[{label}] {'ok' if already_linked and agents_skills.is_dir() else 'MISSING'}")
        return

    agents_skills.mkdir(parents=True, exist_ok=True)

    if already_linked:
        print(f"[{label}] .claude/skills already linked to .agents/skills")
        return

    if claude_skills.exists() or claude_skills.is_symlink():
        ui.warn(
            f"{claude_skills} already exists and isn't a symlink to {agents_skills}.",
            "Leaving it alone — move its contents into .agents/skills yourself, then re-run, to "
            "get both a working Claude Code setup and the cross-tool convention.",
        )
        return

    claude_skills.parent.mkdir(parents=True, exist_ok=True)
    claude_skills.symlink_to(agents_skills)
    print(f"[{label}] created .agents/skills, symlinked .claude/skills to it")


_AGENTS_MD_TEMPLATE = """\
# Agent instructions for {name}

Cross-tool instructions for AI coding agents working in this repo. Universal conventions (sudo/ssh
askpass, Bash/allowlist discipline, cross-session memory policy) live in `~/AGENTS.md` — no need
to repeat them here, only what's specific to this repo.

## Build & test

<!-- e.g. `npm test`, `make build` -->

## Conventions

<!-- code style, architecture notes, anything an agent should know before making changes -->
"""


@task
def skills(c, dir=None):
    """Ensure .agents/skills exists with .claude/skills symlinked to it, then install every
    skill declared via a `skills` field anywhere in setup.toml — local repo paths symlinked in,
    remote GitHub sources fetched via the `skills` CLI (see [packages.node].global_packages).
    On the default (global) run, also merges every declared `claude_permissions_allow` rule into
    ~/.claude/settings.json and checks for GitHub Copilot (see docs/claude-code.md).

    Defaults to the home directory (the personal, cross-project skills location). Pass --dir to
    set this up for a specific project instead — permissions/Copilot are skipped for a --dir run,
    since those are global, user-level settings, not project-scoped.
    """
    base = Path(dir).expanduser().resolve() if dir else Path.home()
    _ensure_agents_skills(base, label="ai.skills")
    _install_declared_skills(c, base)
    if dir is None:
        _apply_static_claude_permissions()
        _note_copilot_permissions()


@task
def init(c, dir="."):
    """Scaffold a project for AI agents: minimal AGENTS.md, CLAUDE.md as a symlink to it, and
    .agents/skills/ (symlinked from .claude/skills). Never overwrites a file that already exists —
    safe to re-run.
    """
    base = Path(dir).expanduser().resolve()
    _ensure_agents_skills(base, label="ai.init")

    agents_md = base / "AGENTS.md"
    if agents_md.exists():
        print("[ai.init] AGENTS.md already exists — left alone")
    else:
        agents_md.write_text(_AGENTS_MD_TEMPLATE.format(name=base.name))
        print("[ai.init] AGENTS.md created")

    claude_md = base / "CLAUDE.md"
    claude_md_alt = base / ".claude" / "CLAUDE.md"
    # A real symlink, not a file containing the `@AGENTS.md` import directive: the import syntax
    # is Claude-Code-specific, so any other harness that also happens to read a literal CLAUDE.md
    # (for compat) would see that text verbatim instead of actual instructions. A symlink presents
    # byte-identical content to every harness, Claude Code included, with no special-case parsing
    # required anywhere. Trade-off: unlike the import form, nothing can be appended below a
    # symlink's target — a Claude-specific addendum, if one's ever truly needed, belongs in
    # AGENTS.md itself (shared) rather than CLAUDE.md, or in a separate `.claude/`-scoped file.
    if claude_md.is_symlink() and claude_md.resolve() == agents_md.resolve():
        print("[ai.init] CLAUDE.md already symlinked to AGENTS.md")
    elif claude_md.exists() or claude_md.is_symlink() or claude_md_alt.exists():
        print("[ai.init] CLAUDE.md already exists — left alone")
    else:
        claude_md.symlink_to("AGENTS.md")
        print("[ai.init] CLAUDE.md created (symlink to AGENTS.md)")
