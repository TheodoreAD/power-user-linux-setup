import json
import re
import shlex
from pathlib import Path
from typing import cast

from invoke import Context, Exit, task

from . import node, ui, util

# Its own constant rather than reaching into deploy's, matching fonts.py/python.py/system.py. Only
# `source = "local"` needs it, to turn a repo-relative `path` into the absolute one the `skills` CLI
# requires before it will treat a source as a directory at all — see _skill_source.
_REPO_ROOT = Path(__file__).parent.parent

# Deliberately separate from tasks/allowlist.py's _APPLIED_MANIFEST — that one tracks
# CLI-classification-derived Bash rules specifically; this tracks static, hand-declared rules
# from any setup.toml package's claude_permissions_allow field. Same safe-merge pattern (only
# rule strings we previously wrote are ever removed), different manifest, so the two mechanisms
# can never step on each other's rules even though they touch the same settings.json file.
_STATIC_PERMS_MANIFEST = util.PULSE_STATE_DIR / "claude-static-permissions-applied.json"
# deny and ask get their own manifests rather than sharing the allow one, for the reason the allow
# manifest exists at all: a manifest is the record of "rules this mechanism wrote", and one file
# covering three tiers could not say which tier a removed rule came from. The allow manifest keeps
# its original filename so an existing machine's record stays valid across this change.
_STATIC_PERMS_DENY_MANIFEST = util.PULSE_STATE_DIR / "claude-static-permissions-deny-applied.json"
_STATIC_PERMS_ASK_MANIFEST = util.PULSE_STATE_DIR / "claude-static-permissions-ask-applied.json"
# (permissions key in settings.json, setup.toml field, manifest). Order matters only for output.
_STATIC_PERM_TIERS = (
    ("allow", "claude_permissions_allow", _STATIC_PERMS_MANIFEST),
    ("deny", "claude_permissions_deny", _STATIC_PERMS_DENY_MANIFEST),
    ("ask", "claude_permissions_ask", _STATIC_PERMS_ASK_MANIFEST),
)
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


# The `skills` CLI reports usage to add-skill.vercel.sh unless one of these is set, and it is on by
# default. Every event carries the CLI version, a CI flag and the name of the agent it detects
# running it; an `install` adds the source repo, the skill names, the target agents and a JSON map
# of skill name to its path within that repo. It has a gate of its own — an install is suppressed
# when the source repo is private, or when that check fails — but PULSE installs a public repo, so
# that gate never fires here and the names went out on every run.
#
# PULSE runs it unattended from `inv ai.install-skills`, so the choice is PULSE's to make rather
# than something to inherit — pinned off deliberately, per ~/.agents/AGENTS.md's rule that a feature which
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


def _skill_source(entry: util.SkillEntry, *, label: str) -> str:
    """The source argument to hand `skills add` — a repo shorthand, or an absolute local path.

    **The path must be absolute, and that is not a style choice.** The CLI decides local-versus-
    remote by shape: `isLocalPath` in its `source-parser.ts` accepts only an absolute path, `./`,
    `../`, `.` or `..`, and everything else falls through to GitHub-shorthand parsing. A
    repo-relative `skills/my-skill` is therefore read as the GitHub repo `skills/my-skill` — a real
    repo namespace — and the CLI would go to the network for somebody else's code under a name that
    looked local in `setup.toml`.
    """
    if entry.get("source") == "local":
        if "path" not in entry:
            raise util.missing_fields(label, 'skills[].path (source = "local")')
        return str((_REPO_ROOT / entry["path"]).resolve())
    if "repo" not in entry:
        raise util.missing_fields(label, 'skills[].repo (source = "npx")')
    return entry["repo"]


def _install_skill(c: Context, entry: util.SkillEntry, *, label: str, yes: bool) -> None:
    """Install a skill through the `skills` CLI, from a GitHub repo or a local directory.

    Always global (this is unattended provisioning, not a project-local, interactive `skills
    add`) — `--yes` on the `skills` CLI invocation below skips *its own* per-file overwrite
    prompts, separate from the `yes` param here, which gates whether we ask before running it at
    all. `names` omitted installs every skill in the source; `agents` defaults to just claude-code.

    **`source = "local"` used to be PULSE copying the directory itself**, with a `.pulse-source`
    marker, an up-to-date check and a deploy-registry entry. That was removed 2026-09-07: the CLI
    takes a local path directly (`add.ts`, "Use local path directly, no cloning needed"), so the
    copier was a second implementation of something the tool already did — and a worse one, because
    it wrote only `.agents/skills/<name>` and relied on a `~/.claude/skills` directory symlink that
    no longer exists. Routing both sources through the CLI means a local skill gets the same
    per-skill entry in every selected agent's directory as a remote one, on every platform.

    Asks before running `skills add` unless `yes` is set. There is no cheap up-to-date check here,
    so this asks even on a re-run of an already-installed skill.
    """
    source = _skill_source(entry, label=label)
    names = entry.get("names")
    agents = entry.get("agents", ["claude-code"])
    desc = _remote_skill_label(names, source)

    if util.DRY_RUN:
        print(f"[{label}] {desc}: not checked in dry-run (would run `skills add`)")
        return

    # A local skill can describe itself, and the copier this replaced showed that description in
    # its prompt — keeping it means routing through the CLI costs the reader nothing. A remote one
    # cannot be read without fetching it first, so there `description` in setup.toml is all there is.
    explain = entry.get("description")
    if explain is None and entry.get("source") == "local":
        explain = _skill_frontmatter_description(Path(source) / "SKILL.md")

    if not yes and not ui.ask(_remote_skill_prompt(desc, explain)):
        print(f"[{label}] {desc}: skipped (declined)")
        return

    cmd = ["skills", "add", source, "--global", "--yes"]
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

    enabled_packages(), not a hand-rolled `enabled` check: that check honoured setup.toml and
    nothing else, so a package switched off in this machine's own overrides.toml still had its
    skills installed — and a tagged one would be installed on a profile that excludes it. Same
    blindness as zsh.configure's, which was found by its symptom on a real machine rather than by
    reading the code. Already-installed skills are left alone; this stops them being re-installed,
    and removing a skill directory is not something to do behind the user's back.
    """
    known: set[str] = set()
    matched = False

    for name, cfg in util.enabled_packages().items():
        for entry in cfg.get("skills", []):
            known.update(_entry_skill_names(entry) or [])
            chosen = _select_entry(entry, selected)
            if chosen is None:
                continue
            matched = True
            source = chosen.get("source")
            if source in ("local", "npx"):
                _install_skill(c, chosen, label=name, yes=yes)
            else:
                ui.warn(f"[{name}] skills entry has unknown source {source!r} — skipping")

    if selected is not None and not matched:
        raise ValueError(
            f"--skill matched no declared skill: {', '.join(sorted(selected))}. "
            f"Declared: {', '.join(sorted(known)) or '(none)'}."
        )


def _perm_lists(perms: util.ClaudePermissions) -> dict[str, list[str]]:
    """The permissions block viewed as plain lists keyed by tier name.

    `ClaudePermissions` is a TypedDict, so a tier name held in a variable cannot index it — and the
    three tiers here are driven by a table, not written out one by one. This is the single place
    that gap is bridged, via the `object` hop basedpyright asks for. The returned dict is the same
    object, so writing through it updates the settings being saved.
    """
    return cast(dict[str, list[str]], cast(object, perms))


def _static_perm_merge(existing: list[str], declared: list[str], manifest: Path) -> list[str] | None:
    """The merged rule list for one permissions tier, or None when it would not change.

    Only rule strings this mechanism wrote last time (per `manifest`) are eligible for removal, so
    a rule added by hand — or by tasks/allowlist.py, which keeps its own separate manifest — is
    never dropped. Pure apart from reading the manifest, so the merge itself is unit-testable.
    """
    previous: set[str] = set(cast(list[str], json.loads(manifest.read_text()))) if manifest.exists() else set()
    kept = [r for r in existing if r not in previous]
    merged = kept + [r for r in declared if r not in kept]
    return None if set(merged) == set(existing) else merged


def _apply_static_claude_permissions() -> None:
    """Merge every setup.toml-declared `claude_permissions_allow` / `claude_permissions_deny` /
    `claude_permissions_ask` rule (checked on any package entry, any method — same any-section
    pattern as `skills`/`zshenv`) into the matching list in ~/.claude/settings.json's
    `permissions`.

    Same safe-merge shape as tasks/allowlist.py's `apply` — every other key in the file untouched,
    a backup written before any real change, and only rule strings *this* mechanism wrote last
    time are eligible for removal — but deliberately not that module's code path: these are
    static, hand-declared rules, not CLI-classification output, and keeping the two mechanisms'
    manifests separate means neither can ever remove a rule the other one owns.

    **`deny` and `ask` are what let a permission decision survive `auto` mode.** In `auto` a
    classifier decides, so an `allow` rule is mostly moot there — but Claude Code evaluates rules
    deny-then-ask-then-allow and applies both to every subcommand, "including a command nested
    inside a subshell, a command substitution, or a control-flow body ... even in auto mode"
    (docs/en/permissions). So a declared deny is the one permission control this machine's usual
    mode cannot loosen, which is why it is worth declaring here rather than left to a session.

    All three tiers are written in one pass so a run produces a single settings write and a single
    backup, rather than three.
    """
    # enabled_packages(): a package this machine turned off in overrides.toml, or one its profile
    # excludes by tag, should not be granting permissions here. The manifest makes that complete
    # rather than half-done — a rule that stops being declared is removed on the next run, because
    # only rules this mechanism wrote last time are eligible for removal.
    cfgs = list(util.enabled_packages().values())
    # The setup.toml field name is a variable here, not a literal, so the package TypedDict's `.get`
    # degrades to Any — hence the explicit cast rather than the literal-key form the single-tier
    # version used. Same reason for reading the settings lists below.
    declared: dict[str, list[str]] = {}
    for key, field, _ in _STATIC_PERM_TIERS:
        rules: set[str] = set()
        for cfg in cfgs:
            rules.update(cast(list[str], cfg.get(field, [])))
        declared[key] = sorted(rules)

    settings = util.load_claude_settings()
    perms_now = _perm_lists(settings.get("permissions", {}))

    if util.DRY_RUN:
        for key, _, _ in _STATIC_PERM_TIERS:
            missing = [r for r in declared[key] if r not in perms_now.get(key, [])]
            state = "ok" if not missing else f"MISSING {len(missing)}"
            print(f"[ai.install-skills] static Claude permissions ({key}): {state}")
        return

    changed = {
        key: merged
        for key, _, manifest in _STATIC_PERM_TIERS
        if (merged := _static_perm_merge(perms_now.get(key, []), declared[key], manifest)) is not None
    }

    if not changed:
        total = sum(len(v) for v in declared.values())
        print(f"[ai.install-skills] static Claude permissions: already up to date ({total} rule(s))")
        return

    _perm_lists(settings.setdefault("permissions", {})).update(changed)
    util.write_claude_settings(settings)

    for key, _, manifest in _STATIC_PERM_TIERS:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(declared[key], indent=2) + "\n")
    summary = ", ".join(f"{key} {len(declared[key])}" for key, _, _ in _STATIC_PERM_TIERS if key in changed)
    print(f"[ai.install-skills] {util.CLAUDE_SETTINGS}: static permissions updated ({summary})")


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
            for cfg in util.enabled_packages().values()
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


def _apply_declared_skill_listing_budget() -> None:
    """Sync `[packages.claude-code]`'s `claude_skill_listing_budget_fraction` into
    ~/.claude/settings.json's top-level `skillListingBudgetFraction`. Same three-outcome scalar
    shape as the two functions either side of this one — absent -> set; matches -> no-op; set to
    something else -> ask before overwriting.

    What the number does: the skill listing Claude Code sends the model is capped at
    `context_window_tokens * 4 * fraction` **characters**, and on overflow user and project skills
    are demoted to name-only in ascending order of decayed usage — the description dropped whole
    rather than shortened, so the skill can no longer be matched against a request. The default 0.01
    is 8,000 characters on a 200k-window model against a real listing here of 18,109. setup.toml
    carries the arithmetic and the reason 0.02 is too tight.

    A ceiling, not an allocation: on a session whose listing already fits — every model in real use
    — raising it changes nothing that is sent.

    [PITFALL: this reads `load_config()` rather than `enabled_packages()`, matching
    `_apply_declared_default_mode` and `_apply_declared_statusline` immediately around it. All three
    look up one named package rather than scanning, so they are not the blind-scan shape the
    2026-09-06 audit moved off that call — but they do share the question of whether disabling
    `[packages.claude-code]` should withdraw the harness settings it declared. That is one decision
    for all three and a behaviour change, so it is not made here by adding a fourth shape.]
    """
    declared = util.load_config()["packages"].get("claude-code", {}).get("claude_skill_listing_budget_fraction")
    if declared is None:
        return

    settings = util.load_claude_settings()
    current = settings.get("skillListingBudgetFraction")

    if util.DRY_RUN:
        print(f"[ai.install-skills] skillListingBudgetFraction: {util.ok_label(current == declared)}")
        return

    if current == declared:
        print("[ai.install-skills] skillListingBudgetFraction: already up to date")
        return

    if current is not None and not ui.ask(
        f"~/.claude/settings.json already sets skillListingBudgetFraction={current!r} — replace it with {declared!r}?",
        default=False,
    ):
        print("[ai.install-skills] skillListingBudgetFraction: left existing value in place")
        return

    settings["skillListingBudgetFraction"] = declared
    util.write_claude_settings(settings)
    print(f"[ai.install-skills] {util.CLAUDE_SETTINGS}: skillListingBudgetFraction set to {declared!r}")


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
    """Ensure <base>/.agents/skills exists. Deliberately does **not** link .claude/skills to it.

    Until 2026-09-07 this made `.claude/skills` a symlink to `.agents/skills`, because Claude Code
    does not read the cross-tool path natively (verified: zero occurrences of `.agents/skills` in
    its shipped binary, against 50 of `.claude/skills`) and a 2026-08-27 measurement said the
    `skills` CLI announced a symlink it did not create.

    That measurement is stale, and the whole-directory link was the wrong shape anyway:

    - **The CLI does create it, per skill.** `claude-code` is not one of its *universal* agents —
      its `skillsDir` is `.claude/skills`, and `isUniversalAgent` tests for `.agents/skills` — so
      the early return that skips per-agent links never applied to it. Re-measured on this machine
      with CLI v1.5.24 and the directory link removed: 14 skills, 14 symlinks created at
      `~/.claude/skills/<name>` pointing to `../../.agents/skills/<name>`.
    - **The old link hid that.** The CLI resolves parent symlinks before deciding whether a skill
      is already installed, so with `.claude/skills` linked, `<link>/<name>` and
      `.agents/skills/<name>` are the same file and it correctly skipped. The arrangement could not
      observe what the CLI would do without it.
    - **A directory symlink is the one shape Windows cannot make** without Developer Mode or
      admin, and no vendor documents it: Claude Code's docs say a `<skill-name>` *entry* may be a
      symlink, never the directory. The CLI's per-skill path uses a junction on Windows, which
      needs no privilege, and falls back to copying.

    So the directory is created and the linking is left to the tool that owns it.
    """
    agents_skills = base / ".agents" / "skills"
    if util.DRY_RUN:
        print(f"[{label}] {util.ok_label(agents_skills.is_dir())}")
        return
    existed = agents_skills.is_dir()
    agents_skills.mkdir(parents=True, exist_ok=True)
    if not existed:
        print(f"[{label}] created {agents_skills}")


@task
def install_skills(c: Context, dir: str | None = None, yes: bool = False, skill: str | None = None):  # noqa: A002
    """Ensure .agents/skills exists with .claude/skills symlinked to it, then install every
    skill declared via a `skills` field anywhere in setup.toml — local repo paths symlinked in,
    remote GitHub sources fetched via the `skills` CLI (see [packages.node].global_packages).
    On the default (global) run, also merges every declared `claude_permissions_allow` rule and
    `claude_additional_directories` entry into ~/.claude/settings.json, syncs the declared
    `claude_default_mode`, `claude_skill_listing_budget_fraction` and `claude_statusline` values
    into `permissions.defaultMode` / `skillListingBudgetFraction` / `statusLine`, and checks for
    GitHub Copilot (see docs/claude-code.md).

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
        _apply_declared_skill_listing_budget()
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
    """(fragment, rule, label) for every labelled rule across the ~/.agents/AGENTS.md fragments."""
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
    """Report ~/.agents/AGENTS.md rules whose declared prerequisite is no longer installed.

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
        print("[ai] every [needs …] label in the ~/.agents/AGENTS.md fragments names an enabled package")
        return

    for line in stale:
        print(line)
    ui.warn(
        "A rule above asserts something this machine no longer provides. Either re-enable the "
        "package, or edit the rule in config/agents-md/ so it stops claiming a prerequisite that "
        "is gone — then redeploy with `inv deploy.all --name agents-md`."
    )
    raise Exit(code=1)
