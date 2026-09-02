import json
import re
import shlex
from pathlib import Path
from typing import cast

from invoke import Context, Exit, task

from . import deploy, node, ui, util

# Deliberately separate from tasks/allowlist.py's _APPLIED_MANIFEST — that one tracks
# CLI-classification-derived Bash rules specifically; this tracks static, hand-declared rules
# from any setup.toml package's claude_permissions_allow field. Same safe-merge pattern (only
# rule strings we previously wrote are ever removed), different manifest, so the two mechanisms
# can never step on each other's rules even though they touch the same settings.json file.
_STATIC_PERMS_MANIFEST = util.PULSE_STATE_DIR / "claude-static-permissions-applied.json"
# Same shape again for `claude_additional_directories` (permissions.additionalDirectories): its own
# manifest, so a directory the user added by hand is never removed by this mechanism.
_STATIC_DIRS_MANIFEST = util.PULSE_STATE_DIR / "claude-additional-directories-applied.json"


def _parse_frontmatter_description(text: str) -> str | None:
    """Pull the `description:` field out of a SKILL.md's YAML frontmatter without a YAML
    dependency — the frontmatter here is always a flat `key: value` block, so a line scan between
    the two `---` markers is enough. Pure string parsing (no filesystem calls of its own) so it's
    unit-testable directly — see _skill_frontmatter_description for the file-reading wrapper.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("description:"):
            return line.split("description:", 1)[1].strip().strip('"')
    return None


def _skill_frontmatter_description(skill_md: Path) -> str | None:
    if not skill_md.is_file():
        return None
    return _parse_frontmatter_description(skill_md.read_text())


def _local_skill_plan(*, present: bool, ours: bool, state: deploy.State) -> str:
    """Pure decision of what _install_local_skill should do next, given the on-disk state it
    already gathered (present/ours come from the marker file, `state` from deploy.classify — real
    filesystem checks, but the decision itself has no I/O of its own).

    One of: "foreign" (something else already lives at dest, leave it alone), "up_to_date"
    (ours, nothing to do), "install" (nothing there yet), "update" (ours, source moved on), or
    "overwrite" (ours, but edited at the destination since PULSE wrote it — the one case where
    the prompt must say what it's about to discard).
    """
    if present and not ours:
        return "foreign"
    if state == deploy.State.CLEAN:
        return "up_to_date"
    if state == deploy.State.ABSENT:
        return "install"
    return "overwrite" if state == deploy.State.DIRTY else "update"


def _selected_skill_names(skill: str | None) -> set[str] | None:
    """Parse `--skill`'s comma-separated value into a set of names, or None when the flag wasn't
    passed at all — None means "every declared skill", the default. Same comma-split shape as
    util._excluded_tags. Pure, so it's unit-testable without touching a filesystem."""
    if skill is None:
        return None
    return {s.strip() for s in skill.split(",") if s.strip()}


def _entry_skill_names(entry: util.SkillEntry) -> list[str] | None:
    """The skill names a setup.toml `skills` entry provides, or None when that can't be known
    without network access.

    A local entry's name is its directory's, matching what _install_local_skill installs it as. A
    remote entry declares `names` explicitly, but may omit it to mean "every skill in that repo" —
    only the `skills` CLI can enumerate those, so there's nothing to match against here.
    """
    if entry.get("source") == "local":
        if "path" not in entry:
            raise util.missing_fields("skills", 'path (source = "local")')
        return [Path(entry["path"]).name]
    return entry.get("names")


def _select_entry(entry: util.SkillEntry, selected: set[str] | None) -> util.SkillEntry | None:
    """Filter one `skills` entry against `--skill`: the entry to install, or None to skip it.

    A remote entry is narrowed to just the requested names rather than installed wholesale, so
    `--skill=a` against an entry declaring `names = ["a", "b"]` installs only `a`. An entry whose
    names aren't knowable (see _entry_skill_names) is skipped whenever a selection is active — it
    can't be confirmed to match, and installing it on the chance that it might would defeat the
    point of naming one skill.
    """
    if selected is None:
        return entry
    names = _entry_skill_names(entry)
    if names is None:
        return None
    matched = [n for n in names if n in selected]
    if not matched:
        return None
    return entry if entry.get("source") == "local" else {**entry, "names": matched}


def _remote_skill_label(names: list[str] | None, repo: str) -> str:
    return f"{', '.join(names) if names else 'all skills'} from {repo}"


def _remote_skill_prompt(label: str, entry_description: str | None) -> str:
    explain = f"\n{entry_description}" if entry_description else ""
    return f"Install {label}?{explain}"


def _install_local_skill(base: Path, repo_path: str, *, label: str, yes: bool) -> None:
    """Copy this repo's skills/<name>/ to <base>/.agents/skills/<name> (source = "local") — a
    real, standalone copy, not a symlink, matching how the npx-sourced installer behaves (it
    also copies, per its own install summary output). A `.pulse-source` marker records which
    setup.toml-declared path installed it, so re-runs can tell "ours, safe to refresh" apart
    from "foreign content, don't touch" the same way _ensure_agents_skills does for the
    .claude/skills symlink — without a marker, two directory copies are indistinguishable by
    content alone. Refreshed to exactly match the repo on every run once it's ours; an edit to
    the repo copy needs `inv ai.install-skills` re-run to take effect, unlike the old symlink approach.

    Asks (showing the skill's own SKILL.md description) before an actual install/update, unless
    `yes` is set — same `-y`/`--yes` convention as the `skills` CLI's own `--yes` flag used below.
    Never asks for a skill that's already up to date, so a re-run of an unchanged setup stays
    quiet either way.

    The copy itself, its post-copy verification, the marker and the deploy-manifest record all
    happen in deploy.deploy() — the one writer for every path under ~. What stays here is the
    foreign check (a marker-less directory at dest is someone else's, whatever its content) and
    this task's own install/update prompt, which deploy() then never repeats.
    """
    name = Path(repo_path).name
    managed = deploy.Managed(
        path=base / ".agents" / "skills" / name,
        package=label,
        source=repo_path,
        mechanism=deploy.Mechanism.SKILL,
    )
    src, dest = managed.src, managed.path
    present = dest.exists() or dest.is_symlink()
    marker = dest / deploy.SKILL_MARKER
    ours = marker.is_file() and marker.read_text().strip() == repo_path
    plan = _local_skill_plan(present=present, ours=ours, state=deploy.classify(managed))

    if util.DRY_RUN:
        print(f"[{label}] {name}: {util.ok_label(plan == 'up_to_date')}")
        return

    if plan == "foreign":
        ui.warn(
            f"{dest} already exists and wasn't installed by this entry ({repo_path}).",
            "Leaving it alone — remove it yourself and re-run to install the repo's copy.",
        )
        return

    if plan == "up_to_date":
        print(f"[{label}] {name} already up to date")
        return

    if not yes:
        desc = _skill_frontmatter_description(src / "SKILL.md") or "(no description found)"
        if plan == "overwrite":
            # Content that exists only at the destination is what's about to be discarded — say
            # so, and default to keeping it, the same way deploy() itself does for a DIRTY file.
            question = f"Overwrite skill '{name}'? It was edited under {dest} since PULSE deployed it.\n{desc}"
            default = False
        else:
            verb = "Update" if plan == "update" else "Install"
            question = f"{verb} skill '{name}'?\n{desc}"
            default = True
        if not ui.ask(question, default=default):
            print(f"[{label}] {name}: skipped (declined)")
            return

    # The prompt above already covered the DIRTY case, so deploy() must not ask a second time.
    deploy.deploy(managed, assume_yes=True)


# The `skills` CLI reports usage to add-skill.vercel.sh unless one of these is set, and it is on by
# default. Every event carries the CLI version, a CI flag and the name of the agent it detects
# running it; an `install` adds the source repo, the skill names, the target agents and a JSON map
# of skill name to its path within that repo. It has a gate of its own — an install is suppressed
# when the source repo is private, or when that check fails — but PULSE installs a public repo, so
# that gate never fires here and the names went out on every run.
#
# PULSE runs it unattended from `inv ai.install-skills`, so the choice is PULSE's to make rather
# than something to inherit — pinned off deliberately, per ~/AGENTS.md's rule that a feature which
# phones home by default is a decision, not a default. Both names are honoured; DO_NOT_TRACK is the
# cross-tool convention and DISABLE_TELEMETRY is the CLI's own, so setting both survives either
# being dropped upstream.
#
# This does not silence the CLI entirely, and the remainder is deliberate rather than overlooked:
# `skills add` also GETs add-skill.vercel.sh/audit with the source repo and skill names to fetch
# supply-chain risk labels, gated by neither variable nor by repo privacy. That is a security
# feature being paid for with the same disclosure, which is a different trade from usage reporting.
_SKILLS_ENV = {"DO_NOT_TRACK": "1", "DISABLE_TELEMETRY": "1"}


def _skills_command(command: str) -> str | None:
    """`command` as something actually runnable here, or None if the `skills` CLI is nowhere.

    Two ways it can be reachable and one way it can't: on PATH (a machine where a login shell has
    already sourced nvm, or a different install method), or under nvm — which is where PULSE puts
    it, and which a non-interactive `inv` process cannot see without sourcing nvm.sh. A bare call
    exited 127 and took a whole unattended container build down with it.
    """
    if util.command_exists("skills"):
        return command
    return node.nvm_command(command)


def _install_remote_skill(c: Context, entry: util.SkillEntry, *, label: str, yes: bool) -> None:
    """Install a skill from a GitHub repo via the `skills` CLI (source = "npx").

    Always global (this is unattended provisioning, not a project-local, interactive `skills
    add`) — `--yes` on the `skills` CLI invocation below skips *its own* per-file overwrite
    prompts, separate from the `yes` param here, which gates whether we ask before running it at
    all. `names` omitted installs every skill in the repo; `agents` defaults to just claude-code,
    since that's the one this repo actively manages (its .claude/skills is symlinked to
    .agents/skills, so this converges on the same shared directory local skills use, not a
    separate claude-code-only copy).

    Asks before running `skills add` unless `yes` is set — there's no cheap up-to-date check for
    a remote repo the way there is for a local copy (see _install_local_skill), so unlike that one
    this always asks, even on a re-run of an already-installed skill.
    """
    if "repo" not in entry:
        raise util.missing_fields(label, 'skills[].repo (source = "npx")')
    repo = entry["repo"]
    names = entry.get("names")
    agents = entry.get("agents", ["claude-code"])
    desc = _remote_skill_label(names, repo)

    if util.DRY_RUN:
        print(f"[{label}] {desc}: not checked in dry-run (would run `skills add`)")
        return

    if not yes and not ui.ask(_remote_skill_prompt(desc, entry.get("description"))):
        print(f"[{label}] {desc}: skipped (declined)")
        return

    cmd = ["skills", "add", repo, "--global", "--yes"]
    for a in agents:
        cmd += ["--agent", a]
    cmd += ["--skill", *(names or ["*"])]
    command = _skills_command(shlex.join(cmd))
    if command is None:
        ui.warn(
            f"[{label}] {desc}: skipped — the `skills` CLI isn't available yet. It's a global npm "
            "package (see [packages.node]), so on a first run it doesn't exist until "
            "`inv node.install` has run. Re-run `inv ai.install-skills` afterwards."
        )
        return
    c.run(command, env=_SKILLS_ENV)
    print(f"[{label}] installed {desc}")


def _install_declared_skills(c: Context, base: Path, *, yes: bool, selected: set[str] | None = None) -> None:
    """Process every `skills` list found on any setup.toml package entry, regardless of that
    entry's own `method` — same any-section pattern as zshenv/zshrc/zprofile.

    `selected` (from `--skill`) narrows this to named skills only; None processes everything.
    A selection that matches nothing raises rather than exiting quietly — a typo'd `--skill` that
    silently did no work would look exactly like a successful refresh.
    """
    known: set[str] = set()
    matched = False

    for name, cfg in util.load_config()["packages"].items():
        if not cfg.get("enabled", True):
            continue
        for entry in cfg.get("skills", []):
            known.update(_entry_skill_names(entry) or [])
            chosen = _select_entry(entry, selected)
            if chosen is None:
                continue
            matched = True
            source = chosen.get("source")
            if source == "local":
                if "path" not in chosen:
                    raise util.missing_fields(name, 'skills[].path (source = "local")')
                _install_local_skill(base, chosen["path"], label=name, yes=yes)
            elif source == "npx":
                _install_remote_skill(c, chosen, label=name, yes=yes)
            else:
                ui.warn(f"[{name}] skills entry has unknown source {source!r} — skipping")

    if selected is not None and not matched:
        raise ValueError(
            f"--skill matched no declared skill: {', '.join(sorted(selected))}. "
            f"Declared: {', '.join(sorted(known)) or '(none)'}."
        )


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

    settings = util.load_claude_settings()
    existing_allow = settings.get("permissions", {}).get("allow", [])

    if util.DRY_RUN:
        missing = [r for r in declared if r not in existing_allow]
        print(f"[ai.install-skills] static Claude permissions: {'ok' if not missing else f'MISSING {len(missing)}'}")
        return

    previous: set[str] = (
        set(cast(list[str], json.loads(_STATIC_PERMS_MANIFEST.read_text())))
        if _STATIC_PERMS_MANIFEST.exists()
        else set()
    )
    kept = [r for r in existing_allow if r not in previous]
    merged = kept + [r for r in declared if r not in kept]

    if set(merged) == set(existing_allow):
        print(f"[ai.install-skills] static Claude permissions: already up to date ({len(declared)} rule(s))")
        return

    perms = settings.setdefault("permissions", {})
    perms["allow"] = merged

    util.write_claude_settings(settings)

    _STATIC_PERMS_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    _STATIC_PERMS_MANIFEST.write_text(json.dumps(declared, indent=2) + "\n")
    print(f"[ai.install-skills] {util.CLAUDE_SETTINGS}: static permissions updated ({len(declared)} rule(s))")


def _apply_additional_directories() -> None:
    """Merge every setup.toml-declared `claude_additional_directories` entry (any package, any
    method — same any-section pattern as `claude_permissions_allow`) into ~/.claude/settings.json's
    `permissions.additionalDirectories`, `~` expanded. Same manifest-tracked safe merge as
    `_apply_static_claude_permissions`, through its own manifest (`_STATIC_DIRS_MANIFEST`).

    Why it exists: under `acceptEdits` mode, file edits and the filesystem commands it
    auto-approves are only unprompted *inside* the working directory or these directories. The
    harness's own scratch locations (`/tmp/claude-1000/<project>/<session>/scratchpad`,
    `~/.claude/jobs/<id>/tmp`) are outside every repo, so without this every scratch write prompts.
    Directories listed here grant file access only — no CLAUDE.md/skills/hooks load from them
    (documented harness behavior for the settings-file form, unlike `--add-dir`).
    """
    declared = sorted(
        {
            str(Path(d).expanduser())
            for cfg in util.load_config()["packages"].values()
            if cfg.get("enabled", True)
            for d in cfg.get("claude_additional_directories", [])
        }
    )

    settings = util.load_claude_settings()
    existing = settings.get("permissions", {}).get("additionalDirectories", [])

    if util.DRY_RUN:
        missing = [d for d in declared if d not in existing]
        print(f"[ai.install-skills] additionalDirectories: {'ok' if not missing else f'MISSING {len(missing)}'}")
        return

    previous: set[str] = (
        set(cast(list[str], json.loads(_STATIC_DIRS_MANIFEST.read_text()))) if _STATIC_DIRS_MANIFEST.exists() else set()
    )
    kept = [d for d in existing if d not in previous]
    merged = kept + [d for d in declared if d not in kept]

    if set(merged) == set(existing):
        print(f"[ai.install-skills] additionalDirectories: already up to date ({len(declared)} dir(s))")
        return

    settings.setdefault("permissions", {})["additionalDirectories"] = merged
    util.write_claude_settings(settings)

    _STATIC_DIRS_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    _STATIC_DIRS_MANIFEST.write_text(json.dumps(declared, indent=2) + "\n")
    print(f"[ai.install-skills] {util.CLAUDE_SETTINGS}: additionalDirectories updated ({len(declared)} dir(s))")


def _apply_declared_default_mode() -> None:
    """Sync `[packages.claude-code]`'s `claude_default_mode` into ~/.claude/settings.json's
    `permissions.defaultMode`. Same three-outcome shape as `_apply_declared_statusline` — one
    scalar with one desired value, so no manifest: absent -> set; matches -> no-op; set to
    something else -> ask before overwriting (declines by default).

    The mode is declared here rather than flipped per session because the rest of this machine's
    Claude Code setup — the `cli-allowlist` pipeline's prefix rules, `mode_covered`, the scratch
    `claude_additional_directories` — is designed around `acceptEdits`' rules-decide model, not
    `auto`'s classifier-decides one; a session started in the wrong mode silently gets a different
    permission system. Rationale and the audit behind the choice: the `session-bash-audit` skill's
    references/research.md.
    """
    declared = util.load_config()["packages"].get("claude-code", {}).get("claude_default_mode")
    if not declared:
        return

    settings = util.load_claude_settings()
    current = settings.get("permissions", {}).get("defaultMode")

    if util.DRY_RUN:
        print(f"[ai.install-skills] permissions.defaultMode: {util.ok_label(current == declared)}")
        return

    if current == declared:
        print("[ai.install-skills] permissions.defaultMode: already up to date")
        return

    if current is not None and not ui.ask(
        f"~/.claude/settings.json already sets permissions.defaultMode={current!r} — replace it with {declared!r}?",
        default=False,
    ):
        print("[ai.install-skills] permissions.defaultMode: left existing value in place")
        return

    settings.setdefault("permissions", {})["defaultMode"] = declared
    util.write_claude_settings(settings)
    print(f"[ai.install-skills] {util.CLAUDE_SETTINGS}: permissions.defaultMode set to {declared!r}")


def _apply_declared_statusline() -> None:
    """Point ~/.claude/settings.json's top-level `statusLine` key at the managed script, declared
    via `[packages.claude-statusline]`'s `claude_statusline` field.

    Unlike `_apply_static_claude_permissions`, no manifest/diff bookkeeping: `statusLine` is a
    single scalar value with exactly one desired state, not a list multiple packages contribute
    to over time, so there's nothing to distinguish "ours to remove" from "user's to keep." Three
    outcomes only: absent -> set it; already matches -> no-op; set to something else -> ask before
    overwriting (default: leave it alone).
    """
    declared = util.load_config()["packages"].get("claude-statusline", {}).get("claude_statusline")
    if not declared:
        return

    settings = util.load_claude_settings()
    current = settings.get("statusLine")

    if util.DRY_RUN:
        print(f"[ai.install-skills] statusLine: {util.ok_label(current == declared)}")
        return

    if current == declared:
        print("[ai.install-skills] statusLine: already up to date")
        return

    if current is not None and not ui.ask(
        f"~/.claude/settings.json already has a custom statusLine ({current!r}) — replace it with the managed one?",
        default=False,
    ):
        print("[ai.install-skills] statusLine: left existing custom value in place")
        return

    settings["statusLine"] = declared
    util.write_claude_settings(settings)
    print(f"[ai.install-skills] {util.CLAUDE_SETTINGS}: statusLine updated")


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
            "[ai.install-skills] GitHub Copilot detected — no permissions applied for it. No confirmed, "
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
        print(f"[{label}] {util.ok_label(already_linked and agents_skills.is_dir())}")
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


@task
def install_skills(c: Context, dir: str | None = None, yes: bool = False, skill: str | None = None):  # noqa: A002
    """Ensure .agents/skills exists with .claude/skills symlinked to it, then install every
    skill declared via a `skills` field anywhere in setup.toml — local repo paths symlinked in,
    remote GitHub sources fetched via the `skills` CLI (see [packages.node].global_packages).
    On the default (global) run, also merges every declared `claude_permissions_allow` rule and
    `claude_additional_directories` entry into ~/.claude/settings.json, syncs the declared
    `claude_default_mode` and `claude_statusline` values into `permissions.defaultMode` /
    `statusLine`, and checks for GitHub Copilot (see docs/claude-code.md).

    Before actually installing or updating a skill, shows its own description and asks — same
    `-y`/`--yes` convention as apt/the `skills` CLI itself (already used below for its own `skills
    add --yes`), rather than a bespoke `--confirm`-to-opt-in flag: pass -y/--yes to skip the
    prompts and install everything, e.g. for a fully unattended `inv setup`. Skills that are
    already up to date are never prompted for, so a re-run of an unchanged setup stays quiet
    either way. Like every other prompt in this repo (see ui.ask), a non-interactive run (piped,
    CI, PULSE_DRY_RUN) skips the prompt and proceeds — this never hangs a scripted run even
    without -y.

    Pass --skill=<name> (comma-separated for several) to act on just those skills instead of every
    declared one. A --skill that matches nothing raises, rather than quietly doing no work and
    looking like a successful refresh. Permissions/statusLine/Copilot are skipped for a --skill run,
    same as for --dir: they're global settings with nothing to do with which skill was named.

    Note that --skill can only narrow an entry whose skill names are knowable without the network —
    a `local` entry, or a remote one that declares `names`. `[packages.agent-skills]` deliberately
    declares no `names` (so an upstream addition needs no setup.toml edit), so it is all-or-nothing
    here and --skill skips it; refresh one of its skills with
    `skills add TheodoreAD/agent-skills --global --skill <name>` instead.

    Defaults to the home directory (the personal, cross-project skills location). Pass --dir to
    set this up for a specific project instead — permissions/statusLine/Copilot are skipped for a
    --dir run, since those are global, user-level settings, not project-scoped.
    """
    base = Path(dir).expanduser().resolve() if dir else Path.home()
    selected = _selected_skill_names(skill)
    _ensure_agents_skills(base, label="ai.install-skills")
    _install_declared_skills(c, base, yes=yes, selected=selected)
    if dir is None and selected is None:
        _apply_static_claude_permissions()
        _apply_additional_directories()
        _apply_declared_default_mode()
        _apply_declared_statusline()
        _note_copilot_permissions()


# `[Claude Code]` / `[needs <thing>]` on a `### ` heading in config/agents-md/*.md. Only the
# `needs` form is machine-checkable, and only where <thing> is a bare name: a label may also cite a
# file or a mechanism ("needs setup.toml", "needs PULSE's zprofile"), which no package corresponds
# to. See that directory's README.md for the vocabulary.
_RULE_LABEL = re.compile(r"^### (?P<rule>.+?)\s*\[(?P<label>[^\]]+)\]$", re.MULTILINE)
_CHECKABLE = re.compile(r"^[\w-]+$")
_AGENTS_MD_FRAGMENTS = Path(__file__).parent.parent / "config" / "agents-md"


def _labelled_rules() -> list[tuple[str, str, str]]:
    """(fragment, rule, label) for every labelled rule across the ~/AGENTS.md fragments."""
    return [
        (path.name, m["rule"], m["label"])
        for path in sorted(_AGENTS_MD_FRAGMENTS.glob("*.md"))
        if path.name != "README.md"
        for m in _RULE_LABEL.finditer(path.read_text())
    ]


def _stale_prerequisites(rules: list[tuple[str, str, str]], declared: set[str], enabled: set[str]) -> list[str]:
    """The complaint line for each rule whose prerequisite is gone — pure, so it is unit-testable
    without a setup.toml or a config/agents-md/ on disk.

    A label that is not `needs <bare name>` is skipped rather than reported: `[Claude Code]` names
    no package, and `needs setup.toml` / `needs PULSE's zprofile` name a file and a mechanism that
    no `[packages.*]` entry corresponds to. Those are for the reader, and treating them as failures
    would make the check cry wolf on every run.
    """
    stale: list[str] = []
    for fragment, rule, label in rules:
        dep = label.removeprefix("needs ")
        if dep == label or not _CHECKABLE.match(dep):
            continue
        if dep not in declared:
            stale.append(f"[ai] {fragment}: '{rule}' needs '{dep}', which setup.toml does not declare")
        elif dep not in enabled:
            stale.append(f"[ai] {fragment}: '{rule}' needs '{dep}', which is declared but disabled or tag-excluded")
    return stale


@task
def check_rule_prerequisites(c: Context):
    """Report ~/AGENTS.md rules whose declared prerequisite is no longer installed.

    A rule labelled `[needs direnv]` is only true while direnv is there. Disable
    `[packages.direnv]`, or exclude its tag, and the rule keeps asserting something false into
    every session on this machine — silently, because nothing reads a label. This is what reads
    them.

    Read-only, and deliberately config-level: it answers "is this still declared and enabled",
    using the same precedence `inv setup` does (setup.toml -> overrides.toml ->
    PULSE_EXCLUDE_TAGS). Whether the binary is physically present is `inv verify.all`'s job, and
    keeping that out is what lets this run without invoking anything.
    """
    stale = _stale_prerequisites(_labelled_rules(), set(util.load_config()["packages"]), set(util.enabled_packages()))
    if not stale:
        print("[ai] every [needs …] label in the ~/AGENTS.md fragments names an enabled package")
        return

    for line in stale:
        print(line)
    ui.warn(
        "A rule above asserts something this machine no longer provides. Either re-enable the "
        "package, or edit the rule in config/agents-md/ so it stops claiming a prerequisite that "
        "is gone — then redeploy with `inv deploy.all --name agents-md`."
    )
    raise Exit(code=1)
