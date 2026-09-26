---
status: landed
updated: 2026-09-26
---

# Allowlist mid-pattern wildcard rules are dead

## Context

Claude Code 2.1.283 prints a startup warning for 81 rules in `~/.claude/settings.json`: each "mixes
`*` with the trailing `:*` prefix syntax, so it is matched as a literal prefix (the `*` is not
expanded) and will likely never match".

What changed upstream (Claude Code `CHANGELOG.md`, 2.1.282): "Fixed Bash permission rules with a
mid-pattern `:*` being skipped in settings files while `--allowedTools` honored them; they now work
from every source, with a startup warning on how they match". So before 2.1.282 these rules were
dropped silently, and since then they load but match only a literal `*`. **They have never matched a
real command on this machine.** Nothing broke in 2.1.283; the release made an existing gap visible.

The dead rules fall into three groups by source:

1. **Nine `ask_overrides` in `cli-allowlist/tools.toml`** (`reset * --hard`, `rm * -f`,
   `restore --staged * -W`, ...). They exist to close the flag-order hole, and with them dead
   `git reset HEAD --hard`, `git reset -q --hard` and `git rm x -f` match the `allow_overrides` rule
   for the verb and run **without a prompt**. Confirmed live below. The one group with a safety
   consequence.
2. **54 `global_option_prefixes` allow rules** (`git -C * status:*`, `git -c * log:*`, ...). Every
   cross-repo git call has prompted all along.
3. **24 hand-written allow rules in `setup.toml`** under `[packages.repo-tasks]` and
   `[packages.spowse]` (`inv *.status:*`, ...). A second source of Bash rules, in Claude syntax,
   outside the pipeline that exists to generate them.

### How Claude Code actually matches, measured

Docs (code.claude.com/docs/en/permissions, "Wildcard patterns", fetched 2026-09-26; no public repo)
plus live probes: `claude -p` in a throwaway repo with only the rules under test loaded,
`--permission-mode manual --permission-prompts none`, and the verdict read from the JSON output's
`permission_denials`; warnings read from `--debug-file`. Claude Code 2.1.283, about 50 probes and
$0.20 in total.

- `:*` is a wildcard only at the very end. Anywhere else the rule's `*` is literal and it never
  matches: `Bash(git reset * --hard:*)` let `git reset HEAD --hard` run.
- A `*` matches any text including spaces, but **not the empty string between two spaces**:
  `Bash(git reset * --hard)` does not match `git reset --hard`. Zero-or-more arguments therefore
  takes two renderings, with and without the `*`.
- A trailing `*` matches the bare command only when it is the rule's only wildcard, so
  `Bash(git reset * --hard)` + `Bash(git reset * --hard *)` is the exact pair for "the flag anywhere
  after the verb". Both were confirmed to prompt for `git reset HEAD --hard` and
  `git reset -q --hard HEAD`, with `git reset -q HEAD` still allowed.
- **An allow rule with a standalone `*` before the git subcommand warns on every startup**:
  "`Bash(git -C * add)` has a wildcard before the rest of the command, so it also matches any
  options inserted at that position and approves them without a prompt. For git, options such as -c
  and --exec-path can run arbitrary commands." Every path glob warns too: `../*`, `~/*`, `*/*`, and
  an absolute root followed by `/*`. The hazard is real: `git -C <dir> -c core.fsmonitor=true add x`
  ran under `Bash(git -C * add)`.
- `Bash(inv *.status)` and `Bash(inv *.status *)` do not warn and do match. Ask rules never warn.
- Claude's built-in read-only set covers `git status`/`git log`, but **no `git -C` form**, not even
  `git -C . status`. Registering the target as an `additionalDirectories` entry makes `ls ../other`
  run, but not `git -C ../other status` or `cd ../other && git status`.
- A rule with an exact path and a `*` only after the verb, `Bash(git -C /abs/other status *)`,
  matches and does not warn.
- **Rule count is cheap.** 9,073 and 25,601 extra allow rules cost about +1 s wall time per `-p` run
  against a one-rule baseline, and no input tokens: the rules are not part of the prompt.

What agents actually pass to `git -C`, from every transcript on this machine: absolute paths 1,713,
`~/` 320, `../` 11. By target: `~/projects` 1,077, the plans stores 769, `~/research` 181.

### How VS Code Copilot matches (`chat.tools.terminal.autoApprove`)

From `microsoft/vscode` source (a shallow clone in `$RESEARCH_HOME`,
`commandLineAutoApprover.ts`/`commandLineAutoApproveAnalyzer.ts`), 2026-09-26:

- A key is `/regex/flags` or a plain string; a plain string is `^<escaped>\b`, so `*` in it is
  literal. Regex keys are **not** anchored implicitly.
- `true` approves, `false` requires approval, `null` unsets a default. **Deny is checked before
  allow**, so any matching `false` beats any `true`. That is the same no-specificity precedence the
  parent-skip in `_compute_claude_rules` is built on, and `_render_copilot` does not apply the skip
  today.
- The line is parsed with tree-sitter and every sub-command must be approved on its own; a leading
  `VAR=value` is always denied.
- VS Code's own defaults already approve read-only git with `(\s+(-C\s+\S+|--no-pager))*` after
  `git`. Regex can say "exactly one argument", which Claude's syntax cannot.

## Design

The user's constraints (2026-09-26): the rules must work; **no startup warnings**, because a
permanent warning hides the next new one; generating many more rules is fine unless measured
otherwise, and was measured fine; **one source of rules with an output per harness**, which is the
reason the rules are generated in Python at all.

### 1. A harness-neutral rule model, `tasks/permission_rules.py`

A new pure module, the functional core. `allowlist.py` keeps the I/O: loading `rules/*.json` and
`tools.toml`, writing settings.

- **Source grammar**, used by `tools.toml` overrides and by nothing harness-specific. A pattern is
  space-separated tokens after the tool name:
  - a plain word is literal;
  - `...` is zero or more whole arguments;
  - a word containing `*` is **one** argument matching that glob (`*.status`, `--collection*`).
- **`Rule`**: frozen dataclass of tool, decision (`allow`/`ask`), tokens, plus two render hints:
  `repo_dir_options` (options such as git's `-C` that take a repository directory and may precede
  the verb) and `mode_covered` (dropped for Claude, whose `acceptEdits` gates it; kept for Copilot).
- **Claude renderer**: each `...` expands to "absent" and "`*`"; a trailing `...` to "absent" and
  "`*`". It never emits `:*`. A single-argument glob renders as its text, which in Claude's syntax
  can span arguments. That is a widening, so every tool with a glob in an allow rule must declare
  ask guards for its code-loading options (see §4). A repo-directory option renders nothing (see
  §3).
- **Copilot renderer**: regex keys anchored `^…$`. `...` becomes `(?:\s+\S+)*`, a glob becomes `\S*`
  pieces, a repo-directory option becomes `(?:\s+-C\s+\S+)*` after the tool name. `allow` → `true`,
  `ask` → `false`. Still print-only.
- **Invariants, enforced by unit tests over the real `tools.toml` and `rules/`**: no Claude rule
  contains `:*`; no Claude allow rule has a standalone `*` token anywhere but last.

### 2. Building the rules, `allowlist.py`

`_compute_claude_rules`/`_tool_claude_rules` become one builder, `_build_rules(rules, registry)`,
returning `Rule`s. It keeps every existing knob (reviewed-only, parent-with-children skip,
`cloud_cli` cap, `mode_covered`, `allow_overrides` replacing the node's rule) and changes three
things:

- **`ask_overrides` in the new grammar**: `reset ... --hard` replaces the `reset --hard` +
  `reset * --hard` pair. It renders four Claude rules, which cover the flag first, last and in the
  middle.
- **An allow override now suppresses the ask of the node it extends.** `restore --staged` is allowed
  but the `restore` node renders `Bash(git restore:*)` as ask, and ask beats allow, so
  `git restore --staged x` has prompted all along. Confirmed live: denied with both rules loaded,
  ran with the allow alone. The test
  `test_compute_claude_rules_ask_overrides_render_verbatim_alongside_allow_override` asserts exactly
  that shadowing pair. The node's ask is dropped whenever an allow override starts with its path.
  Its destructive shapes stay covered by explicit `ask_overrides`
  (`restore --staged ... --worktree`, `-W`).
- **Repo-directory variants apply to every allow rule and every `ask_override` of the tool**, so a
  carve-out holds under `git -C <repo>` exactly as it does without it. Node ask rules get no
  variants: an unmatched `git -C <repo> push` prompts anyway.

### 3. `git -C`: nothing for Claude; the Bash sandbox carries it

[DECISION: **Claude's renderer emits nothing for `repo_dir_options`**, settled with the user
2026-09-26 after three designs lost. The `-C *`/`-c *` prefixes never matched. A glob in any form
warns at every startup and lets `-c core.fsmonitor=<program>` through. One rule per repository was
built (commits f92d099, 11a9149) and worked warning-free, but rendered 2.7 MB across 279
repositories, and Claude Code rejects a settings file over 2 MiB whole; narrowed to the used verbs
it was still 626 KB and stale for every new clone. The Bash sandbox runs
`git -C <repo> status`/`log` with no rule at all and still prompts for `-c` and for the carve-outs
(probed, recorded in `plans/2026-09-05-web-tool-permissions-and-what-auto-actually-buys.md`), so it
is the right layer. Until it is enabled, cross-repo git prompts, as it always has. Copilot keeps
`-C` as one regex.]

[PITFALL: **Claude Code rejects a settings file over 2 MiB outright** (`claude` exits 1, "Settings
file exceeds the 2MiB limit"), losing every setting, not just the rules. Found by `check-claude`
before anything was applied. `util.write_claude_settings` now refuses past 1 MiB.]

### 4. One source: the `inv`/`spowse` rules move into `tools.toml`

The 34 hand-written `Bash(...)` rules leave `setup.toml`, which keeps only its non-command
Claude-specific plumbing (`Read(...)`, `Bash(dangerouslyDisableSandbox:true)`).

- **A new registry field, `overrides_only = true`**: the tool's rules come from its overrides alone,
  outside the review gate, because the `tools.toml` entry is itself the hand-reviewed artifact. Its
  classification, if any, is not rendered. `extract`/`classify` skip it. `inv` needs this, since a
  reviewed `inv` would render its own `write` verdict as `Bash(inv:*)` ask and shadow every
  override.
- **`aliases = ["spouse"]`** on `[spowse]`, rendering the same rules under each name.
- **Guards for the glob widening.** `Bash(inv *.status)` also matches `inv -c evil x.status`, and
  invoke's `-c/--collection`, `-r/--search-root` and `-f/--config` all load and execute Python. Each
  gets an ask override in both short and long form: `... -c* ...`, `... --collection* ...`, and so
  on.

### 5. `inv allowlist.check-claude`, a live check against the installed harness

This answers "I will miss new warnings when the software changes". It is a dev-only task, not a
test: the suite is hermetic and unit-only by design (`tests/README.md`), and this spends real API
money. It renders the current rule set into a temporary settings file and runs a fixed table of
`claude -p` probes (Haiku, `--safe-mode`, `--permission-prompts none`) in throwaway repos. It fails
on any permission-rule warning in the debug log and on any probe whose run/deny outcome differs from
the table. A `check-*` name falls under the read-only-by-convention allow rule: it inspects and
never mutates, at about $0.05 a run.

### 6. Documentation

The `tools.toml` header, the `_compute_claude_rules` docstring, `contributing/cli-allowlist.md` (the
`global_option_prefixes` and `allow_overrides` sections, "Known gaps"), `docs/cli-allowlist.md`, and
the `setup.toml` comments that describe the moved rules. The measured matching semantics above
become a "how each harness matches" section in `contributing/cli-allowlist.md`, because it is the
reason the renderers differ.

## Files touched

- `tasks/permission_rules.py` (new), `tasks/allowlist.py`, `cli-allowlist/tools.toml`, `setup.toml`
- `tests/unit/test_permission_rules.py` (new), `tests/unit/test_allowlist.py`,
  `tests/unit/test_cli.py` (the new dev-only task)
- `contributing/cli-allowlist.md`, `docs/cli-allowlist.md`

## Verification

- `inv quality.precommit`, including the invariant tests over the real registry.
- `inv allowlist.render` before and after: diff the non-`-C` rules by hand.
- `PULSE_DRY_RUN=1 inv allowlist.apply`, then `inv allowlist.apply` and `inv ai.install-skills`
  (which removes the rules that moved out of `setup.toml`).
- `inv allowlist.check-claude` green on Claude Code 2.1.283, and a fresh session showing no
  permission-rule warnings at startup.

## Migrated to

- `contributing/cli-allowlist.md`: "How each harness matches" (the measured Claude Code and VS Code
  Copilot semantics above), the `repo_dir_options` section (the `-C` decision, the three designs
  that lost, the sandbox probe, the 2 MiB cap), and the `allow_overrides` section (the dead
  carve-outs, the `restore --staged` shadowing, residual flag clusters).
- `docs/cli-allowlist.md`: the one-source model and when to run `inv allowlist.check-claude`.
- `cli-allowlist/tools.toml` header and `tasks/permission_rules.py` docstrings: the grammar and each
  knob, at the implementing lines.
- `plans/2026-09-05-web-tool-permissions-and-what-auto-actually-buys.md`: the sandbox probe table
  and the phantom-file pitfall, which are open work there.

Not migrated: the per-commit build log and the size estimates for the withdrawn per-repository
design, which git history keeps (commits f92d099, 11a9149, c724175).
