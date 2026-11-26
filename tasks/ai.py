import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import cast

from invoke import Context, Exit, task

from . import instruction_shape, node, ui, util

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
# The `claude_hooks` commands this mechanism wrote, by event, so only those are ever removed.
_HOOKS_MANIFEST = util.PULSE_STATE_DIR / "claude-hooks-applied.json"
# The `claude_plugins` this mechanism installed, so only those are ever uninstalled.
_PLUGINS_MANIFEST = util.PULSE_STATE_DIR / "claude-plugins-applied.json"
# This repo's own plugin marketplace: its name is the one in .claude-plugin/marketplace.json.
_PLUGIN_MARKETPLACE = "power-user-linux-setup"
_PLUGIN_MARKETPLACE_DIR = _REPO_ROOT.resolve() / "config" / "claude-plugins"


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
    return _parse_frontmatter_description(skill_md.read_text(encoding="utf-8"))


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


_NO_NAMES: frozenset[str] = frozenset()


def _select_entry(
    entry: util.SkillEntry, selected: set[str] | None, known: frozenset[str] = _NO_NAMES
) -> util.SkillEntry | None:
    """Filter one `skills` entry against `--skill`: the entry to install, or None to skip it.

    A remote entry is narrowed to just the requested names rather than installed wholesale, so
    `--skill=a` against an entry declaring `names = ["a", "b"]` installs only `a`.

    An entry whose names aren't knowable offline (see _entry_skill_names) is handed the requested
    names no other entry declares — `known` — and nothing else, carrying its own `agents`. That is
    what lets a one-skill refresh of `[packages.agent-skills]`, which deliberately declares no
    `names`, go through the declared mechanism rather than a hand-typed `skills add`. A hand-typed
    one has no `--agent` and installs for every agent the CLI detects, writing copies setup.toml
    never declared (seen 2026-11-08: "+12 more" agents for one skill). Not knowing the names stops
    this task from *validating* them, not from passing them on: the CLI validates, and exits 1 with
    "No matching skills" when none match. A requested name that matches nothing while another in
    the same call does is skipped by the CLI without an error.
    """
    if selected is None:
        return entry
    names = _entry_skill_names(entry)
    if names is None:
        passthrough = sorted(selected - known)
        return {**entry, "names": passthrough} if passthrough else None
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

# The agents a `skills` entry installs for when it names none. Both are needed, and the first is not
# decoration: since CLI 1.9.0, `defaultInstallMode` symlinks from a canonical copy only when the
# targets span more than one skills directory, and copies straight into the one directory otherwise.
# Measured 2026-11-25 on a throwaway HOME: `--agent claude-code` alone wrote a plain copy into
# ~/.claude/skills and nothing into ~/.agents/skills, which every other agent reads. With
# `universal` beside it the CLI writes the real copy to ~/.agents/skills and one relative link per
# skill into ~/.claude/skills, and touches no other agent's directory — the agents that read
# ~/.agents/skills natively need nothing more. See
# plans/2026-11-25-agents-md-and-agents-skills-as-the-only-source.md.
_DEFAULT_AGENTS = ("universal", "claude-code")


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
    all. `names` omitted installs every skill in the source; `agents` defaults to
    `_DEFAULT_AGENTS`, whose comment says why it is two names and not one.

    This installs, and re-running it picks up a skill added upstream since; refreshing what is
    already installed is `update_skills`, which follows each skill's recorded source rather than
    re-adding it.

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
    agents = entry.get("agents", list(_DEFAULT_AGENTS))
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
    entries = [(name, entry) for name, cfg in util.enabled_packages().items() for entry in cfg.get("skills", [])]
    known = frozenset(n for _, entry in entries for n in _entry_skill_names(entry) or [])
    open_ended = [name for name, entry in entries if _entry_skill_names(entry) is None]
    # Two open-ended entries would each be handed the same undeclared names, and the CLI exits 1
    # for the one that lacks them — so the refresh would fail halfway rather than pick a source.
    if selected is not None and len(open_ended) > 1 and selected - known:
        raise ValueError(
            f"--skill {', '.join(sorted(selected - known))} is declared by no entry, and more than one "
            f"entry installs a whole repo ({', '.join(open_ended)}), so which one provides it is "
            "unknown. Declare `names` on one of them."
        )
    matched = False

    for name, entry in entries:
        chosen = _select_entry(entry, selected, known)
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
    previous: set[str] = (
        set(cast(list[str], json.loads(manifest.read_text(encoding="utf-8")))) if manifest.exists() else set()
    )
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
        manifest.write_text(json.dumps(declared[key], indent=2) + "\n", encoding="utf-8", newline="\n")
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

    Written with forward slashes (`as_posix()`), which Claude Code's settings use on every platform:
    `str()` on Windows turned `/tmp/claude-1000` into `\\tmp\\claude-1000`.
    """
    declared = sorted(
        {
            Path(d).expanduser().as_posix()
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
        set(cast(list[str], json.loads(_STATIC_DIRS_MANIFEST.read_text(encoding="utf-8"))))
        if _STATIC_DIRS_MANIFEST.exists()
        else set()
    )
    kept = [d for d in existing if d not in previous]
    merged = kept + [d for d in declared if d not in kept]

    if set(merged) == set(existing):
        print(f"[ai.install-skills] additionalDirectories: already up to date ({len(declared)} dir(s))")
        return

    settings.setdefault("permissions", {})["additionalDirectories"] = merged
    util.write_claude_settings(settings)

    _STATIC_DIRS_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    _STATIC_DIRS_MANIFEST.write_text(json.dumps(declared, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"[ai.install-skills] {util.CLAUDE_SETTINGS}: additionalDirectories updated ({len(declared)} dir(s))")


def _confirm_replace(question: str, *, yes: bool) -> bool:
    """The replace-a-different-value question every declared-setting sync asks. `-y`/`--yes` on
    `inv ai.install-skills` answers it, as apt's `-y` answers every prompt; without it a
    non-interactive run declines, which is `ui.ask`'s default here."""
    return yes or ui.ask(question, default=False)


def _package_here(name: str) -> util.PackageConfig:
    """One named package's config when it applies to this platform, else `{}`.

    The four single-value settings below look one package up by name instead of scanning
    `enabled_packages()` (see the PITFALL in `_apply_declared_skill_listing_budget`), and before this
    they skipped its `platforms` too. On Windows, `inv ai.install-skills --yes` then replaced the
    machine's own PowerShell statusLine with Linux's `bash ~/.claude/statusline-command.sh`, a
    script that does not exist there. Only the platform is checked here; whether `enabled` or a
    tag exclusion should also withdraw these settings is the separate, deferred decision.
    """
    cfg = util.load_config()["packages"].get(name)
    return cfg if cfg is not None and util.applies_here(name, cfg.get("platforms")) else {}


def _apply_declared_default_mode(*, yes: bool = False) -> None:
    """Sync `[packages.claude-code]`'s `claude_default_mode` into ~/.claude/settings.json's
    `permissions.defaultMode`. Same three-outcome shape as `_apply_declared_statusline` — one
    scalar with one desired value, so no manifest: absent -> set; matches -> no-op; set to
    something else -> ask before overwriting (declines by default, `yes` confirms).

    The mode is declared here rather than flipped per session because a session started in a mode
    other than the one the rest of this setup assumes silently gets a different permission system:
    the `cli-allowlist` rules, `defer_overrides` and `claude_auto_mode` are shaped for the declared
    one. Why it is `auto` since 2026-11-25:
    `plans/2026-11-08-auto-mode-as-default-with-slim-rules.md`.
    """
    declared = _package_here("claude-code").get("claude_default_mode")
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

    if current is not None and not _confirm_replace(
        f"~/.claude/settings.json already sets permissions.defaultMode={current!r} — replace it with {declared!r}?",
        yes=yes,
    ):
        print("[ai.install-skills] permissions.defaultMode: left existing value in place")
        return

    settings.setdefault("permissions", {})["defaultMode"] = declared
    util.write_claude_settings(settings)
    print(f"[ai.install-skills] {util.CLAUDE_SETTINGS}: permissions.defaultMode set to {declared!r}")


def _apply_declared_auto_mode(*, yes: bool = False) -> None:
    """Sync `[packages.claude-code]`'s `claude_auto_mode` table into ~/.claude/settings.json's
    top-level `autoMode` block, which tells auto mode's classifier what is trusted and which of
    its default blocks to lift. Same three outcomes as the scalars around it, applied to the whole
    block as one value: absent -> set; equal -> no-op; different -> ask (`yes` confirms).

    Whole-block rather than merged per entry because the classifier reads the lists as prose
    rules in order, `"$defaults"` splicing the built-in ones in where it sits, so a merge would
    have to decide an order nobody declared. Only the user scope carries it: Claude Code ignores
    `autoMode` in a project's own settings files, so a checked-in repo cannot loosen it.
    """
    declared = _package_here("claude-code").get("claude_auto_mode")
    if not declared:
        return

    settings = util.load_claude_settings()
    current = settings.get("autoMode")

    if util.DRY_RUN:
        print(f"[ai.install-skills] autoMode: {util.ok_label(current == declared)}")
        return

    if current == declared:
        print("[ai.install-skills] autoMode: already up to date")
        return

    if current is not None and not _confirm_replace(
        "~/.claude/settings.json already has a different autoMode block — replace it with the declared one?",
        yes=yes,
    ):
        print("[ai.install-skills] autoMode: left existing block in place")
        return

    settings["autoMode"] = declared
    util.write_claude_settings(settings)
    print(f"[ai.install-skills] {util.CLAUDE_SETTINGS}: autoMode set")


def _apply_declared_skill_listing_budget(*, yes: bool = False) -> None:
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
    declared = _package_here("claude-code").get("claude_skill_listing_budget_fraction")
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

    if current is not None and not _confirm_replace(
        f"~/.claude/settings.json already sets skillListingBudgetFraction={current!r} — replace it with {declared!r}?",
        yes=yes,
    ):
        print("[ai.install-skills] skillListingBudgetFraction: left existing value in place")
        return

    settings["skillListingBudgetFraction"] = declared
    util.write_claude_settings(settings)
    print(f"[ai.install-skills] {util.CLAUDE_SETTINGS}: skillListingBudgetFraction set to {declared!r}")


def _apply_declared_statusline(*, yes: bool = False) -> None:
    """Point ~/.claude/settings.json's top-level `statusLine` key at the managed script, declared
    via `[packages.claude-statusline]`'s `claude_statusline` field.

    Unlike `_apply_static_claude_permissions`, no manifest/diff bookkeeping: `statusLine` is a
    single scalar value with exactly one desired state, not a list multiple packages contribute
    to over time, so there's nothing to distinguish "ours to remove" from "user's to keep." Three
    outcomes only: absent -> set it; already matches -> no-op; set to something else -> ask before
    overwriting (default: leave it alone).
    """
    declared = _package_here("claude-statusline").get("claude_statusline")
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

    if current is not None and not _confirm_replace(
        f"~/.claude/settings.json already has a custom statusLine ({current!r}) — replace it with the managed one?",
        yes=yes,
    ):
        print("[ai.install-skills] statusLine: left existing custom value in place")
        return

    settings["statusLine"] = declared
    util.write_claude_settings(settings)
    print(f"[ai.install-skills] {util.CLAUDE_SETTINGS}: statusLine updated")


def _hook_merge(
    existing: dict[str, list[util.HookGroup]], declared: dict[str, list[str]], previous: dict[str, list[str]]
) -> dict[str, list[util.HookGroup]] | None:
    """The merged `hooks` block, or None when it would not change.

    Hooks are a list several parties write to — the user by hand, `/hooks`, plugins — so the same
    rule as the permission tiers holds: only a command this mechanism wrote last time (`previous`) is
    eligible for removal, and each declared command is added once, in a group of its own with no
    matcher, when no group under that event already runs it. Pure, so it is unit-testable.
    """
    merged: dict[str, list[util.HookGroup]] = {}
    for event in sorted(set(existing) | set(declared)):
        wanted = declared.get(event, [])
        stale = set(previous.get(event, [])) - set(wanted)
        groups: list[util.HookGroup] = []
        for group in existing.get(event, []):
            kept = [h for h in group.get("hooks", []) if h.get("command") not in stale]
            if kept:
                groups.append({**group, "hooks": kept})
        present = {h.get("command") for g in groups for h in g.get("hooks", [])}
        for cmd in wanted:
            if cmd not in present:
                new_group: util.HookGroup = {"hooks": [{"type": "command", "command": cmd}]}
                groups.append(new_group)
        if groups:
            merged[event] = groups
    return None if merged == existing else merged


def _apply_declared_hooks() -> None:
    """Merge every enabled package's `claude_hooks` (event -> command) into ~/.claude/settings.json's
    `hooks`, tracked by `_HOOKS_MANIFEST` so a hook that stops being declared is taken back out.

    Global harness plumbing, which is the one place a hook is allowed (see "Machine behavior belongs
    in global config" in config/agents-md/agent-knowledge.md): no hook is ever written into a repo.
    The first user is `[packages.claude-direnv-hook]`, the per-directory venv activation that the
    `~/.zshenv` direnv line could not provide; docs/claude-code.md has the measurements.
    """
    declared: dict[str, list[str]] = {}
    for cfg in util.enabled_packages().values():
        for event, command in cfg.get("claude_hooks", {}).items():
            declared.setdefault(event, []).append(command)

    settings = util.load_claude_settings()
    existing = settings.get("hooks", {})
    previous: dict[str, list[str]] = (
        cast(dict[str, list[str]], json.loads(_HOOKS_MANIFEST.read_text(encoding="utf-8")))
        if _HOOKS_MANIFEST.exists()
        else {}
    )

    if util.DRY_RUN:
        present = {h.get("command") for groups in existing.values() for g in groups for h in g.get("hooks", [])}
        missing = [c for cmds in declared.values() for c in cmds if c not in present]
        print(f"[ai.install-skills] hooks: {'ok' if not missing else f'MISSING {len(missing)}'}")
        return

    merged = _hook_merge(existing, declared, previous)
    if merged is None:
        print(f"[ai.install-skills] hooks: already up to date ({sum(map(len, declared.values()))} declared)")
        return
    if merged:
        settings["hooks"] = merged
    else:
        settings.pop("hooks", None)
    util.write_claude_settings(settings)
    _HOOKS_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    _HOOKS_MANIFEST.write_text(json.dumps(declared, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"[ai.install-skills] {util.CLAUDE_SETTINGS}: hooks updated ({', '.join(sorted(declared)) or 'none'})")


def _plugin_commands(
    enabled: dict[str, bool],
    marketplaces: dict[str, dict[str, dict[str, str]]],
    declared: list[str],
    previous: list[str],
) -> list[list[str]]:
    """The `claude` arguments that bring the installed plugins in line with `declared`, in order.

    The CLI stays the writer — it owns `enabledPlugins`, `extraKnownMarketplaces` and its own
    install records — and this only decides which calls to make, so it is pure and unit-testable.
    A plugin present in `enabledPlugins` at all counts as installed, so one the user disabled stays
    disabled. A marketplace registered from another checkout (a moved clone) is re-registered, and
    every declared plugin reinstalled from it. Only a plugin this mechanism installed (`previous`)
    is ever uninstalled.
    """
    cmds: list[list[str]] = []
    known = marketplaces.get(_PLUGIN_MARKETPLACE, {}).get("source", {}).get("path")
    moved = bool(declared) and known != str(_PLUGIN_MARKETPLACE_DIR)
    if moved:
        if known is not None:
            cmds.append(["plugin", "marketplace", "remove", _PLUGIN_MARKETPLACE])
        cmds.append(["plugin", "marketplace", "add", str(_PLUGIN_MARKETPLACE_DIR)])
    for name in declared:
        plugin_id = f"{name}@{_PLUGIN_MARKETPLACE}"
        if moved or plugin_id not in enabled:
            cmds.append(["plugin", "install", plugin_id])
    for name in sorted(set(previous) - set(declared)):
        plugin_id = f"{name}@{_PLUGIN_MARKETPLACE}"
        if plugin_id in enabled:
            cmds.append(["plugin", "uninstall", plugin_id])
    return cmds


def _apply_declared_plugins() -> None:
    """Install every enabled package's `claude_plugins` from this repo's marketplace,
    config/claude-plugins/, at user scope, and uninstall the ones that stopped being declared.

    Harness plumbing, not a carrier: a plugin here may only make Claude Code work better on this
    machine (a language server), never hold instructions or skills, which go through AGENTS.md and
    the `skills` CLI. The marketplace is a local directory, so Claude Code loads each plugin in place
    from this checkout and a pull is live at the next session. The first user is
    `[packages.basedpyright-lsp]`; docs/claude-code.md has what it does and how it was verified.
    """
    declared = sorted({p for cfg in util.enabled_packages().values() for p in cfg.get("claude_plugins", [])})
    previous: list[str] = (
        cast(list[str], json.loads(_PLUGINS_MANIFEST.read_text(encoding="utf-8"))) if _PLUGINS_MANIFEST.exists() else []
    )
    if not declared and not previous:
        return
    settings = util.load_claude_settings()
    cmds = _plugin_commands(
        settings.get("enabledPlugins", {}), settings.get("extraKnownMarketplaces", {}), declared, previous
    )

    if util.DRY_RUN:
        print(f"[ai.install-skills] plugins: {'ok' if not cmds else f'{len(cmds)} change(s) pending'}")
        return
    if not cmds:
        print(f"[ai.install-skills] plugins: already up to date ({', '.join(declared) or 'none'})")
    elif (claude := shutil.which("claude")) is None:
        print("[ai.install-skills] plugins: skipped, `claude` is not on PATH")
        return
    else:
        for args in cmds:
            print(f"[ai.install-skills] claude {' '.join(args)}")
            _ = subprocess.run([claude, *args], check=True)
    # Written even when nothing ran, so a plugin installed before this manifest existed is still
    # recorded as this mechanism's to take back.
    _PLUGINS_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    _PLUGINS_MANIFEST.write_text(json.dumps(declared, indent=2) + "\n", encoding="utf-8", newline="\n")


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

    `~/.claude/skills` must also stay a real directory for a reason of Claude Code's own: it keeps
    skills synced from a claude.ai account in `~/.claude/skills/synced/` and moves removed ones to
    `~/.claude/skills/.trash/`. Linked to `~/.agents/skills`, both would land in the directory every
    other agent reads.
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
    """Ensure .agents/skills exists, then install every skill declared via a `skills` field
    anywhere in setup.toml through the `skills` CLI (see [packages.node].global_packages), which
    also makes each skill's own .claude/skills link — see _ensure_agents_skills for why this task
    no longer links the whole directory.
    On the default (global) run, also merges every declared `claude_permissions_allow` rule and
    `claude_additional_directories` entry into ~/.claude/settings.json, syncs the declared
    `claude_default_mode`, `claude_auto_mode`, `claude_skill_listing_budget_fraction` and
    `claude_statusline` values into `permissions.defaultMode` / `autoMode` /
    `skillListingBudgetFraction` / `statusLine`, merges every declared `claude_hooks` command into
    `hooks`, installs every declared `claude_plugins` entry from config/claude-plugins/, and checks
    for GitHub Copilot (see docs/claude-code.md).

    Before actually installing or updating a skill, shows its own description and asks — same
    `-y`/`--yes` convention as apt/the `skills` CLI itself (already used below for its own `skills
    add --yes`), rather than a bespoke `--confirm`-to-opt-in flag: pass -y/--yes to skip the
    prompts and install everything, e.g. for a fully unattended `inv setup`. It answers the
    replace-a-different-setting questions above too, as apt's `-y` answers every prompt. Skills that are
    already up to date are never prompted for, so a re-run of an unchanged setup stays quiet
    either way. Like every other prompt in this repo (see ui.ask), a non-interactive run (piped,
    CI, PULSE_DRY_RUN) skips the prompt and proceeds — this never hangs a scripted run even
    without -y.

    Pass --skill=<name> (comma-separated for several) to act on just those skills instead of every
    declared one. A --skill that matches nothing raises, rather than quietly doing no work and
    looking like a successful refresh (here, or as the CLI's own exit 1). Permissions/statusLine/
    Copilot are skipped for a --skill run, same as for --dir: they're global settings with nothing
    to do with which skill was named.

    A name no entry declares is handed to the one entry that installs a whole repo —
    `[packages.agent-skills]`, which deliberately declares no `names` — with that entry's own
    `agents`, and the `skills` CLI validates it: `inv ai.install-skills --skill=<name>` is the
    one-skill refresh for those skills too. See _select_entry for why that beats a hand-typed
    `skills add`.

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
        _apply_declared_default_mode(yes=yes)
        _apply_declared_auto_mode(yes=yes)
        _apply_declared_skill_listing_budget(yes=yes)
        _apply_declared_statusline(yes=yes)
        _apply_declared_hooks()
        _apply_declared_plugins()
        _note_copilot_permissions()


@task(name="update-skills")
def update_skills(c: Context):
    """Update every globally installed skill to its source's latest, through `skills update`.

    The counterpart to `install_skills`, the same way `node.update-globals` is to `node.install`:
    installing reproduces what `setup.toml` declares, updating takes whatever upstream published
    today, and the second is a choice rather than a side effect of the first. `inv upgrade` runs it.

    The CLI reads `~/.agents/.skill-lock.json`, compares each skill against its source's current
    tree and reinstalls only what moved, keeping each skill's agent links. So this needs no list of
    its own: whatever `install_skills` installed, from any entry, is what gets updated. `--yes` only
    skips the CLI's project-or-global scope question, which `--global` already answers.
    """
    if util.DRY_RUN:
        print("[ai.update-skills] would run: skills update --global --yes")
        return
    command = _skills_command("skills update --global --yes")
    if command is None:
        ui.warn(
            "[ai.update-skills] skipped — the `skills` CLI isn't available. It's a global npm "
            "package (see [packages.node]); run `inv node.install` first."
        )
        return
    c.run(command, env=_SKILLS_ENV)


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
        for m in _RULE_LABEL.finditer(path.read_text(encoding="utf-8"))
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


@task
@util.dev_only
def measure_instruction_shape(c: Context, path: str | None = None, corpus: str | None = None):
    """Report how much of an instruction file instructs, rather than how long it is.

    Word count says a file is big; it does not say whether the words are carrying directives. This
    reports directives per 100 words, mean sentence length, the share of directives that also carry
    their own justification, and the share carrying a nuance clause — the four things
    `plans/2026-09-12-imperative-vs-rationale-in-instruction-files.md` measured this file to be an
    outlier on, against 182 community files.

    Defaults to the deployed `~/.agents/AGENTS.md` plus this repo's own `AGENTS.md`. Pass `--corpus`
    a directory of checkouts (the research library, say) to print mean and median rows to compare
    against — the comparison is the point, since none of these numbers has a meaningful absolute
    target.

    Read-only. `--path` takes one file, for checking a fragment mid-edit.
    """
    if path:
        targets = [Path(path).expanduser()]
    else:
        targets = [Path("~/.agents/AGENTS.md").expanduser(), _REPO_ROOT / "AGENTS.md"]

    shapes = [shape for target in targets if target.is_file() and (shape := instruction_shape.measure_file(target))]
    missing = [t for t in targets if not t.is_file()]
    if not shapes:
        ui.warn(f"[ai] nothing measurable in: {', '.join(str(t) for t in targets)}")
        raise Exit(code=1)

    print(instruction_shape.HEADER)
    print("-" * len(instruction_shape.HEADER))
    for shape in shapes:
        print(instruction_shape.format_row(shape))

    if corpus:
        root = Path(corpus).expanduser()
        if not root.is_dir():
            ui.warn(f"[ai] --corpus is not a directory: {root}")
            raise Exit(code=1)
        compared = instruction_shape.measure_tree(root)
        if not compared:
            ui.warn(f"[ai] no measurable instruction files under {root}")
        else:
            print("-" * len(instruction_shape.HEADER))
            for line in instruction_shape.summarise(compared):
                print(line)

    for target in missing:
        print(f"[ai] skipped, not a file: {target}")
