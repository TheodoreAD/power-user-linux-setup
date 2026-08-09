"""CLI command allowlist pipeline: extract -> classify -> review -> render -> apply.

Keeps `cli-allowlist/rules.json` (read_only/write/dangerous per subcommand, for every CLI tool
this machine actually has installed) current without hand-maintaining it, and merges the reviewed
result into `~/.claude/settings.json`. Full design rationale, every gotcha found while building
this, and why several things here are deliberate tradeoffs rather than TODOs: `docs/cli-allowlist.md`.

    inv allowlist.extract    deterministic: capture --help text per tool, version-gated cache
    inv allowlist.classify   LLM (headless `claude -p`, Haiku): read_only/write/dangerous verdict
    inv allowlist.review     human gate: shows what's new/changed, marks it reviewed
    inv allowlist.render     deterministic: reviewed rules -> Claude or Copilot rule syntax
    inv allowlist.apply      deterministic: merges reviewed Claude rules into ~/.claude/settings.json
    inv allowlist.status     quick table: installed/stale/unreviewed

`render` only prints — `apply` is the only task that writes anywhere, and it only ever touches
`~/.claude/settings.json`'s `permissions` block (see its docstring for the merge safety design).
"""
import hashlib
import json
import os
import re
import subprocess
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from invoke import task

from . import util

_ROOT = Path(__file__).parent.parent / "cli-allowlist"
_TOOLS_TOML = _ROOT / "tools.toml"
_HELP_CACHE_DIR = _ROOT / "help-cache"
_RULES_JSON = _ROOT / "rules.json"

_CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
# Machine-local mutation-tracking state, not repo content — deliberately outside cli-allowlist/
# (which is portable, shared, tracked in git) since this records what `apply` last wrote into an
# out-of-repo file on *this* machine specifically, mirroring the ~/.config/pulse/ namespace
# util.py already uses for the same kind of machine-local state (identity.toml).
_APPLIED_MANIFEST = Path.home() / ".local" / "state" / "pulse" / "claude-settings-applied.json"

_DEFAULT_MAX_SUBCOMMANDS = 40
_HELP_TIMEOUT = 10  # seconds — guards against a misbehaving or secretly-interactive tool hanging
_CLASSIFY_TIMEOUT = 120

# Extraction must give the same text on any machine, not whatever this machine's interactive
# shell happens to have configured. Without this, `git status --help` renders through `man`
# (needs the git-man package — silently absent on a minimal box) and a stray $PAGER/$BROWSER
# could theoretically block waiting for input despite stdin already being closed. None of this
# is hypothetical tightening: git's dependency on git-man was confirmed empirically here.
_DETERMINISTIC_ENV = {
    "PAGER": "cat", "MANPAGER": "cat", "GIT_PAGER": "cat", "LESS": "FRX",
    "BROWSER": "true", "NO_COLOR": "1", "CLICOLOR": "0",
}

# Subcommand-name verbs that force a "needs_review" downgrade even if the LLM said read_only.
# Deliberately checked against the subcommand *name*, not the help text, to avoid false positives
# from a read-only command's help text merely mentioning "delete" while describing something else.
_DANGEROUS_VERBS = {
    "delete", "destroy", "drop", "rm", "rmi", "remove", "purge", "uninstall", "prune",
    "truncate", "kill", "drain", "cordon", "reset", "clean", "yank", "unpublish", "force",
    "wipe", "erase", "flush", "revoke", "down", "run", "exec", "eval",
}

_SUBCOMMAND_LINE = re.compile(r"^\s{1,4}([a-z][a-z0-9_-]{1,20})(?:,\s*[a-z][a-z0-9_-]{1,20})?\s{2,}\S")
_SKIP_WORDS = {"help", "completion", "version", "options", "flags", "usage"}

_RUBRIC = """You are classifying CLI subcommands for a permission allowlist that decides which \
commands an AI coding agent may run unattended vs. which need a human to approve each time.

Categories:
- read_only: only inspects/reads/lists/describes/validates state. Cannot modify anything, local \
or remote, even indirectly.
- write: modifies state (files, cluster resources, cloud resources, packages, git history) but \
the effect is bounded, expected, and typically reversible.
- dangerous: irreversible, broad-blast-radius, bypasses a normal confirmation step, or deletes/\
destroys/force-overwrites something (force flags, deletion, destruction of infrastructure, \
publishing to a public registry, etc.)

Worked example (git, already human-reviewed): status/log/diff/show/blame -> read_only. \
commit/add/checkout -> write. clean/reset --hard -> dangerous.

Respond with a JSON object shaped {"classifications": {"<name>": {"classification": "...", \
"rationale": "<one short sentence>"}}} covering every subcommand listed below, using the exact \
names given as keys."""

_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "classifications": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "classification": {"type": "string", "enum": ["read_only", "write", "dangerous"]},
                    "rationale": {"type": "string"},
                },
                "required": ["classification", "rationale"],
            },
        },
    },
    "required": ["classifications"],
})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_registry() -> dict:
    with open(_TOOLS_TOML, "rb") as f:
        return tomllib.load(f)


def _load_rules() -> dict:
    if not _RULES_JSON.exists():
        return {}
    return json.loads(_RULES_JSON.read_text())


def _save_rules(data: dict) -> None:
    _RULES_JSON.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def _load_cache(tool: str) -> dict | None:
    path = _HELP_CACHE_DIR / f"{tool}.json"
    return json.loads(path.read_text()) if path.exists() else None


def _save_cache(tool: str, data: dict) -> None:
    _HELP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (_HELP_CACHE_DIR / f"{tool}.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def _run(cmd: list[str], timeout: int = _HELP_TIMEOUT) -> str:
    """Run a command, return combined stdout+stderr, "" on timeout/missing binary. Never raises
    on nonzero exit — --help conventionally exits nonzero on plenty of tools."""
    env = {**os.environ, **_DETERMINISTIC_ENV}
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env, stdin=subprocess.DEVNULL)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""
    return (result.stdout + result.stderr).strip()


def _invocation(tool: str, args: list[str], cfg: dict) -> list[str]:
    """Build the argv for `tool args...`, honoring two per-tool escape hatches:

    - shell_prefix: some tools (nvm) only exist as a shell function sourced from a script, not
      an executable on PATH at all — invoke through `bash -c "<prefix> && <tool> <args>"` instead.
    - help_style = "prefix": most tools take `<tool> <sub> --help`, but a few (go) only give a
      one-line stub in that order and need the flag *before* the subcommand (`go help list`).
      Callers pass args already in the right order for that case; this function doesn't reorder.
    """
    prefix = cfg.get("shell_prefix")
    if not prefix:
        return [tool, *args]
    inner = " ".join([tool, *args])
    return ["bash", "-c", f"{prefix} && {inner}"]


def _tool_version(tool: str, version_flag: str, cfg: dict | None = None) -> str:
    """Return a stable per-version string for cache invalidation. Not always line 1: eza's
    --version prints its tagline first and the actual "v0.18.2 [+git]" on line 2 — a tagline
    never changes across upgrades, which would silently defeat staleness detection. Preferring
    the first line that contains a digit catches that case generally, not just for eza."""
    text = _run(_invocation(tool, version_flag.split(), cfg or {}))
    if not text:
        return ""
    for line in text.splitlines():
        if any(ch.isdigit() for ch in line):
            return line.strip()
    return text.splitlines()[0].strip()


def _discover_subcommands(help_text: str, max_n: int) -> list[str]:
    seen: list[str] = []
    for line in help_text.splitlines():
        m = _SUBCOMMAND_LINE.match(line)
        if not m:
            continue
        word = m.group(1)
        if word in _SKIP_WORDS or word in seen:
            continue
        seen.append(word)
        if len(seen) >= max_n:
            break
    return seen


def _hash_commands(commands: dict) -> str:
    return hashlib.sha256(json.dumps(commands, sort_keys=True).encode()).hexdigest()[:16]


def _looks_dangerous(subcommand: str) -> bool:
    tokens = re.split(r"[\s\-_/]+", subcommand.lower())
    return any(t in _DANGEROUS_VERBS for t in tokens)


@task
def extract(c, tool=None, force=False):
    """Capture --help text per registered tool (tools.toml). Skips any tool whose --version
    output hasn't changed since the last successful extract, unless --force."""
    registry = _load_registry()
    names = [tool] if tool else sorted(registry)

    for name in names:
        cfg = registry.get(name)
        if cfg is None:
            print(f"[allowlist] {name}: not in tools.toml — skipping")
            continue
        # shell_prefix tools (nvm) are shell functions, not binaries — `which` can't see them,
        # so existence is judged by whether the extraction call actually produces output instead.
        if not cfg.get("shell_prefix") and not util.command_exists(name):
            print(f"[allowlist] {name}: not installed — skipping")
            continue

        if cfg.get("skip_interactive"):
            _save_cache(name, {"interactive": True, "version": None, "extracted_at": _now(), "commands": {}})
            print(f"[allowlist] {name}: interactive-only, no help captured")
            continue

        version_flag = cfg.get("version_flag", "--version")
        version = _tool_version(name, version_flag, cfg)

        cached = _load_cache(name) or {}
        if not force and version and cached.get("version") == version:
            print(f"[allowlist] {name}: unchanged ({version}) — skipped")
            continue

        help_flag = cfg.get("help_flag", "--help")
        help_style = cfg.get("help_style", "suffix")  # "prefix": <tool> <flag> <sub> (go); default: <tool> <sub> <flag>

        def _sub_args(sub: str | None) -> list[str]:
            if sub is None:
                return help_flag.split()
            return [*help_flag.split(), sub] if help_style == "prefix" else [sub, *help_flag.split()]

        top_help = _run(_invocation(name, _sub_args(None), cfg))
        commands: dict[str, str] = {}

        if not top_help and not cfg.get("shell_prefix"):
            print(f"[allowlist] {name}: no output from --help — skipping (installed but unresponsive?)")
            continue

        if cfg.get("no_subcommands"):
            commands["*"] = top_help
        else:
            commands["_top"] = top_help
            subs = cfg.get("subcommands")
            if subs is None:
                subs = _discover_subcommands(top_help, cfg.get("max_subcommands", _DEFAULT_MAX_SUBCOMMANDS))
            for sub in subs:
                commands[sub] = _run(_invocation(name, _sub_args(sub), cfg))

        if cfg.get("shell_prefix") and not any(commands.values()):
            print(f"[allowlist] {name}: no output at all — likely not installed on this machine, skipping")
            continue

        _save_cache(name, {
            "interactive": False,
            "version": version,
            "extracted_at": _now(),
            "commands": commands,
        })
        classifiable = len(commands) - (1 if "_top" in commands else 0)
        print(f"[allowlist] {name}: extracted ({version or 'unknown version'}, {classifiable} subcommand(s))")


_FLAT_KEY = "_default_"


def _build_prompt(tool: str, commands: dict) -> str:
    if list(commands) == ["*"]:
        # No subcommand tree — first attempt asked the model to classify a heading literally
        # named "*", which it read as "list whatever looks like a distinct action" and classified
        # individual flags (--help, --mode, --run) instead of the tool as one unit. Ask
        # explicitly for a single verdict under a fixed, unambiguous key instead.
        return (
            f"{_RUBRIC}\n\nTool: {tool}\n\n"
            f"This tool has no subcommands — it's invoked as a single flat command "
            f"(`{tool} [options] ...`), not `{tool} <subcommand> ...`. Its --help text is below. "
            f"Ignore informational flags like --help/--version — judge the tool's own primary "
            f"purpose when run normally. Respond with exactly one entry in \"classifications\", "
            f"keyed literally \"{_FLAT_KEY}\", covering the tool as a whole.\n\n"
            f"--help output:\n{commands['*'][:1500]}\n"
        )

    parts = [_RUBRIC, "", f"Tool: {tool}", ""]
    top = commands.get("_top", "")
    if top:
        parts.append(f"Top-level --help (context only — this is not itself something to classify):\n{top[:1000]}\n")
    for sub_name, text in commands.items():
        if sub_name == "_top":
            continue
        parts.append(f"### {sub_name}\n{text[:800]}\n")
    return "\n".join(parts)


def _classify_via_claude(prompt: str, model: str) -> dict | None:
    with tempfile.TemporaryDirectory(prefix="pulse-allowlist-") as scratch:
        try:
            result = subprocess.run(
                [
                    "claude", "-p", "--strict-mcp-config",
                    "--disallowedTools", "Edit,Write,NotebookEdit,Bash,Agent",
                    "--model", model,
                    "--output-format", "json",
                    "--json-schema", _SCHEMA,
                    "--max-budget-usd", "0.10",
                    prompt,
                ],
                capture_output=True, text=True, timeout=_CLASSIFY_TIMEOUT, cwd=scratch,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            return None
    if result.returncode != 0:
        return None
    try:
        envelope = json.loads(result.stdout)
        return envelope["structured_output"]["classifications"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


@task
def classify(c, tool=None, force=False, model="haiku"):
    """Classify each tool's extracted subcommands as read_only/write/dangerous via a headless
    `claude -p` call, isolated in a scratch cwd outside the repo with file/exec tools disallowed.
    Skips any tool whose extracted help hasn't changed since the last classification (or is a
    community-seeded entry not yet backed by a local extraction) — this is what keeps repeat runs
    close to free. See the plan doc for why --bare isn't used here (breaks OAuth login)."""
    if not util.command_exists("claude"):
        print("[allowlist] claude CLI not found — nothing to classify")
        return

    registry = _load_registry()
    rules = _load_rules()
    names = [tool] if tool else sorted(registry)

    for name in names:
        cached = _load_cache(name)
        if cached is None:
            print(f"[allowlist] {name}: no extracted help — run `inv allowlist.extract --tool={name}` first")
            continue

        if cached.get("interactive"):
            rules[name] = {
                "version": None, "help_hash": None, "extracted_at": cached.get("extracted_at"),
                "classified_at": _now(), "source": "manual", "reviewed": True, "reviewed_at": _now(),
                "note": "interactive-only TUI, no non-interactive command surface to classify",
                "subcommands": {},
            }
            print(f"[allowlist] {name}: interactive-only — marked reviewed, nothing to classify")
            continue

        commands = cached.get("commands", {})
        help_hash = _hash_commands(commands)
        existing = rules.get(name)

        if existing and not force and existing.get("help_hash") == help_hash:
            print(f"[allowlist] {name}: unchanged since last classification — skipped")
            continue

        if existing and existing.get("source") == "community" and not existing.get("help_hash") and not force:
            existing["help_hash"] = help_hash
            existing["version"] = cached.get("version")
            existing["extracted_at"] = cached.get("extracted_at")
            rules[name] = existing
            print(f"[allowlist] {name}: community-seeded, backfilled help_hash — no LLM call")
            continue

        verdict = _classify_via_claude(_build_prompt(name, commands), model=model)
        if verdict is None:
            print(f"[allowlist] {name}: classification call failed — left as-is")
            continue

        if list(commands) == ["*"]:
            # Flat (no_subcommands) tool: map the model's single _FLAT_KEY answer back to "*".
            # If it ignored the instruction and broke the tool into multiple entries anyway
            # (observed once, on a flags-heavy --help text), fall back to the most cautious of
            # whatever it returned rather than an arbitrary one — consistent with the verb
            # backstop's "when in doubt, don't assume safe" stance.
            if _FLAT_KEY in verdict:
                verdict = {"*": verdict[_FLAT_KEY]}
            elif verdict:
                order = {"read_only": 0, "write": 1, "dangerous": 2}
                worst = max(verdict.values(), key=lambda v: order.get(v.get("classification"), 1))
                verdict = {"*": {
                    "classification": worst.get("classification", "write"),
                    "rationale": f"inferred conservatively — model split this flat tool into "
                                  f"multiple parts instead of one verdict ({worst.get('rationale', '')})",
                }}

        subcommands = {}
        for sub_name in commands:
            if sub_name == "_top":
                continue
            result = verdict.get(sub_name)
            if result is None:
                continue
            classification = result.get("classification", "write")
            if classification == "read_only" and _looks_dangerous(sub_name):
                classification = "needs_review"
            subcommands[sub_name] = {
                "classification": classification,
                "rationale": result.get("rationale", ""),
            }

        rules[name] = {
            "version": cached.get("version"),
            "help_hash": help_hash,
            "extracted_at": cached.get("extracted_at"),
            "classified_at": _now(),
            "source": "llm",
            "model": model,
            "reviewed": False,
            "reviewed_at": None,
            "subcommands": subcommands,
        }
        print(f"[allowlist] {name}: classified {len(subcommands)} subcommand(s) via {model}")

    _save_rules(rules)


@task
def review(c, apply_all=False):
    """Show tools with unreviewed classifications (new or changed since the last reviewed
    snapshot) and, on confirmation, mark them reviewed. Nothing in `render` trusts an unreviewed
    entry, so this is the human gate before anything downstream sees a tool's rules."""
    rules = _load_rules()
    pending = {name: entry for name, entry in rules.items() if not entry.get("reviewed")}

    if not pending:
        print("[allowlist] nothing pending review")
        return

    for name, entry in sorted(pending.items()):
        needs_review = [s for s, v in entry.get("subcommands", {}).items() if v["classification"] == "needs_review"]
        dangerous = [s for s, v in entry.get("subcommands", {}).items() if v["classification"] == "dangerous"]
        print(f"\n[allowlist] {name} (source: {entry.get('source')}, {len(entry.get('subcommands', {}))} subcommand(s))")
        if entry.get("note"):
            print(f"  note: {entry['note']}")
        if dangerous:
            print(f"  dangerous: {', '.join(sorted(dangerous))}")
        if needs_review:
            print(f"  needs_review (LLM said read_only, downgraded by the verb backstop): {', '.join(sorted(needs_review))}")
        for sub, v in sorted(entry.get("subcommands", {}).items()):
            print(f"    {sub}: {v['classification']} — {v['rationale']}")

        approve = apply_all or util.confirm(f"Mark {name} reviewed?", default=False)
        if approve:
            entry["reviewed"] = True
            entry["reviewed_at"] = _now()
            print(f"  -> {name} marked reviewed")
        else:
            print(f"  -> {name} left unreviewed")

    _save_rules(rules)


def _compute_claude_rules(rules: dict) -> tuple[list[str], list[str]]:
    """Reviewed rules.json -> (allow patterns, ask patterns). Shared by `render` (prints it) and
    `apply` (merges it into ~/.claude/settings.json) so the two can never drift apart."""
    allow, ask = [], []
    for name, entry in sorted(rules.items()):
        if not entry.get("reviewed"):
            continue
        for sub, v in sorted(entry.get("subcommands", {}).items()):
            pattern = f"Bash({name}:*)" if sub == "*" else f"Bash({name} {sub}:*)"
            if v["classification"] == "read_only":
                allow.append(pattern)
            elif v["classification"] in ("write", "dangerous"):
                ask.append(pattern)
    return allow, ask


def _render_claude(rules: dict) -> str:
    allow, ask = _compute_claude_rules(rules)
    return json.dumps({"permissions": {"allow": allow, "ask": ask}}, indent=2)


def _render_copilot(rules: dict) -> str:
    auto_approve = {}
    for name, entry in sorted(rules.items()):
        if not entry.get("reviewed"):
            continue
        for sub, v in sorted(entry.get("subcommands", {}).items()):
            key = f"/^{re.escape(name)}\\b.*/" if sub == "*" else f"/^{re.escape(name)} {re.escape(sub)}\\b.*/"
            auto_approve[key] = v["classification"] == "read_only"
    return json.dumps({"chat.tools.terminal.autoApprove": auto_approve}, indent=2)


@task
def render(c, target="claude", out=None):
    """Print the reviewed subset of rules.json as Claude Bash(...) allow/ask rules or Copilot
    chat.tools.terminal.autoApprove regex rules. Output-only — never writes to any settings file
    (local or user-wide); that's a deliberate next step, not part of this task. `write` and
    `dangerous` entries always render as still-prompting (Claude `ask` / Copilot `false`), never
    as a hard deny — the point is a visible, still-approvable prompt, not a block."""
    rules = _load_rules()
    unreviewed = [name for name, entry in rules.items() if not entry.get("reviewed")]
    if unreviewed:
        print(f"[allowlist] note: {len(unreviewed)} tool(s) not yet reviewed, excluded from output: {', '.join(sorted(unreviewed))}")

    if target == "claude":
        text = _render_claude(rules)
    elif target == "copilot":
        text = _render_copilot(rules)
    else:
        print(f"[allowlist] unknown target {target!r} — use 'claude' or 'copilot'")
        return

    if out:
        Path(out).write_text(text + "\n")
        print(f"[allowlist] wrote {out}")
    else:
        print(text)


@task
def apply(c):
    """Merge the reviewed Bash allow/ask rules into ~/.claude/settings.json's `permissions`
    block — the only thing this task ever touches there.

    Every other key in that file (theme, effortLevel, cleanupPeriodDays, any permission rule you
    added by hand, etc.) is left completely untouched, including on repeated runs. This works by
    tracking exactly which rule strings *we* wrote last time in a local manifest
    (~/.local/state/pulse/claude-settings-applied.json, not repo content — see its definition
    above): on each run, only rules present in that manifest are eligible to be removed, and only
    the freshly computed set is added back. A rule that was never in our manifest — something you
    added yourself — is never touched, and a rule we used to generate but no longer do (say a
    tool's classification changed) is cleanly removed rather than left orphaned. This is what
    "the bash allow rules could be overwritten every time" means in practice: our portion is fully
    regenerated each run, nothing else is.
    """
    rules = _load_rules()
    unreviewed = [name for name, entry in rules.items() if not entry.get("reviewed")]
    if unreviewed:
        print(f"[allowlist] note: {len(unreviewed)} tool(s) not yet reviewed, excluded: {', '.join(sorted(unreviewed))}")

    allow, ask = _compute_claude_rules(rules)
    new_set = set(allow) | set(ask)
    previous = set(json.loads(_APPLIED_MANIFEST.read_text())) if _APPLIED_MANIFEST.exists() else set()

    settings = json.loads(_CLAUDE_SETTINGS.read_text()) if _CLAUDE_SETTINGS.exists() else {}
    perms = settings.setdefault("permissions", {})
    existing_allow = perms.get("allow", [])
    existing_ask = perms.get("ask", [])

    kept_allow = [r for r in existing_allow if r not in previous]
    kept_ask = [r for r in existing_ask if r not in previous]
    merged_allow = kept_allow + [r for r in allow if r not in kept_allow]
    merged_ask = kept_ask + [r for r in ask if r not in kept_ask]

    # Per-bucket diff, not just the flattened union — a rule moving from allow to ask (a tool's
    # classification changed) is a real, meaningful change even though the union of both arrays
    # contains that rule string either way. Reporting only the union would silently print "+0 -0"
    # for exactly the kind of change this task most needs to surface honestly.
    added_allow = set(merged_allow) - set(existing_allow)
    removed_allow = set(existing_allow) & previous - set(merged_allow)
    added_ask = set(merged_ask) - set(existing_ask)
    removed_ask = set(existing_ask) & previous - set(merged_ask)
    added = added_allow | added_ask
    removed = removed_allow | removed_ask
    unchanged = new_set & previous - added - removed

    if set(merged_allow) == set(existing_allow) and set(merged_ask) == set(existing_ask):
        print(f"[allowlist] {_CLAUDE_SETTINGS}: already up to date ({len(unchanged)} rule(s))")
        return

    print(f"[allowlist] {_CLAUDE_SETTINGS}: +{len(added)} -{len(removed)} rule(s) ({len(unchanged)} unchanged)")
    if util.DRY_RUN:
        for r in sorted(added_allow):
            print(f"  + {r} (allow)")
        for r in sorted(added_ask):
            print(f"  + {r} (ask)")
        for r in sorted(removed_allow):
            print(f"  - {r} (allow)")
        for r in sorted(removed_ask):
            print(f"  - {r} (ask)")
        return

    perms["allow"] = merged_allow
    perms["ask"] = merged_ask

    if _CLAUDE_SETTINGS.exists():
        _CLAUDE_SETTINGS.with_suffix(".json.bak").write_text(_CLAUDE_SETTINGS.read_text())
    _CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    _CLAUDE_SETTINGS.write_text(json.dumps(settings, indent=2) + "\n")

    _APPLIED_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    _APPLIED_MANIFEST.write_text(json.dumps(sorted(new_set), indent=2) + "\n")
    print(f"[allowlist] wrote {_CLAUDE_SETTINGS} (backup at {_CLAUDE_SETTINGS}.bak)")


@task
def status(c):
    """Quick table: which registered tools are installed, stale (version changed since last
    classify), or still unreviewed."""
    registry = _load_registry()
    rules = _load_rules()

    for name in sorted(registry):
        cfg = registry[name]
        if not cfg.get("shell_prefix") and not util.command_exists(name):
            print(f"[allowlist] {name}: not installed")
            continue

        entry = rules.get(name)
        if entry is None:
            print(f"[allowlist] {name}: not yet extracted/classified")
            continue

        if cfg.get("skip_interactive"):
            print(f"[allowlist] {name}: interactive-only, reviewed={entry.get('reviewed')}")
            continue

        version_flag = cfg.get("version_flag", "--version")
        current_version = _tool_version(name, version_flag, cfg)
        stale = bool(current_version) and current_version != entry.get("version")
        flags = []
        if stale:
            flags.append("STALE")
        if not entry.get("reviewed"):
            flags.append("unreviewed")
        needs_review = sum(1 for v in entry.get("subcommands", {}).values() if v["classification"] == "needs_review")
        if needs_review:
            flags.append(f"{needs_review} needs_review")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        print(f"[allowlist] {name}: {entry.get('version') or '?'} ({entry.get('source')}, {len(entry.get('subcommands', {}))} subcommand(s)){flag_str}")
