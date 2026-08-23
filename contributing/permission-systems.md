<!-- Preserved 2026-08-24 from the gitignored `reference/allowlists/findings.md` research dump,
which was removed when its third-party material moved to $RESEARCH_HOME. This is the analysis of how
the permission systems themselves work — distinct from `cli-allowlist.md`, which documents the
tooling this repo built on top of that understanding. Its two siblings were not kept: `tool-rules.md`
hand-classified 16 tools and is superseded by `cli-allowlist/rules/`' 80 reviewed ones (see the note
at `cli-allowlist/tools.toml`:431 recording that it was found incomplete), and `README.md` only
described the dump's own layout. Gathered 2026-08-09; not re-verified since, so treat version-
specific claims (the enforcement bug in particular) as of that date. -->

# How the permission systems actually work

Sources: official docs (`docs/claude-code-permissions-official.md`,
`docs/claude-code-sandboxing-official.md`, fetched verbatim 2026-08-09 from
code.claude.com/docs/en/permissions and /sandboxing),
code.visualstudio.com/docs/agents/run/approvals, plus the cloned repos under `repos/`. Full
citations at the bottom.

## Claude Code

### The rule format

`Tool` or `Tool(specifier)`, in `permissions.allow` / `permissions.ask` / `permissions.deny` arrays
in a `settings.json`. For Bash: `Bash(git status)` (exact), `Bash(git log *)` / `Bash(git log:*)`
(prefix wildcard, these two forms are equivalent), `Bash(* --version)` (suffix), `Bash(git * main)`
(wildcard spans multiple args including flags — matches both `git checkout main` and
`git push origin main`).

**Evaluation order is deny → ask → allow, always, regardless of specificity.** A broad `Bash(aws *)`
deny rule beats a narrower `Bash(aws s3 ls)` allow rule. This is the opposite of what most people
assume (most-specific-wins) — worth remembering when writing deny rules meant to carve out
exceptions, because they can't.

### Why prefix-glob allowlisting is fundamentally leaky (straight from Anthropic's own docs)

Their worked example: a rule intended to restrict `curl` to GitHub,
`Bash(curl http://github.com/ *)`, is defeated by:

- flags before the URL (`curl -X GET http://github.com/...`)
- protocol swap (`https://` vs `http://`)
- a redirect through an allowed-looking short URL that 302s elsewhere
- shell variable indirection (`URL=... && curl $URL`)
- just an extra space (`curl  http://github.com`)

Their recommended fix is **not** "write a tighter glob" — it's: block `curl`/`wget` entirely via
deny rules and route fetches through the `WebFetch` tool's `domain:` allowlist instead, or use a
PreToolUse hook that actually parses the command, or add CLAUDE.md guidance (weakest, not enforced).
This is the load-bearing insight for the whole exercise: **glob prefix rules are fine for scoping to
a subcommand** (`kubectl get`, `terraform plan`), but they cannot safely constrain _arguments_
within an allowed subcommand — anything with a mutating flag needs an exact-match allow rule or a
hook, not a wildcard.

### Compound commands, wrappers, and the read-only builtin set

- Claude Code splits on `&& || ; | |& &` and newlines and requires **every** subcommand to match a
  rule independently — `Bash(safe-cmd *)` does not implicitly permit `safe-cmd && other-cmd`.
- It strips known wrappers before matching: `timeout`, `time`, `nice`, `nohup`, `stdbuf`, shell
  `command`/`builtin`, zsh `noglob` — so a rule for the inner command also covers
  `timeout 30 npm test`. **`direnv exec`, `mise exec`, `npx`, `docker exec` are deliberately not in
  this list** because they execute their argument as an arbitrary command — a rule like
  `Bash(devbox run *)` would auto-approve `devbox run rm -rf .`. Relevant here because we use
  `direnv`, `uv run`/`uvx`, and implicitly `npx` via node projects — any allow rule for these must
  name the exact inner command, never just the runner prefix.
- A **built-in, non-configurable set of read-only commands runs with zero prompt in every mode**:
  `ls, cat, echo, pwd, head, tail, grep, find, wc, which, diff, stat, du, cd`, and "read-only forms
  of git". This already covers a good chunk of what a naive allowlist would try to add — no need to
  write rules for these.
- Exec wrappers `watch`, `setsid`, `ionice`, `flock`, and `find -exec`/`-delete` **always prompt**
  and can't be prefix-allowed; only an exact full-string match works.
- `cd` is read-only _unless_ combined with `git` afterward (hook-execution risk) or an ambiguous
  output redirect.

### The enforcement bug (as of this research)

anthropics/claude-code#18846 (open, filed 2026-01-17, labels `bug`/`has repro`):
`permissions.allow`/`deny` Bash rules are reported as **not reliably enforced** in some environments
— users get prompted regardless of configured rules. Workaround in the wild is the same
PreToolUse-hook pattern described above (parse `settings.json` intent yourself, enforce it from the
hook). Two related issues referenced (#15921, #13340) suggest this isn't a one-off. **Don't assume a
settings.json allow list alone will eliminate prompts — validate against actual behavior, and have
the hook approach ready as a fallback.**

### The pattern the ecosystem has converged on

Both Anthropic's docs (`## Extend permissions with hooks`) and the independently-built
`claude-code-permissions` repo land on the same design:

```
permissions.allow: ["Bash"]        # allow everything by default
+ PreToolUse hook on Bash          # regex-match each split subcommand against a deny list
  → match found            → hookSpecificOutput.permissionDecision = "ask"
  → no match                → exit 0 (silently allowed)
```

This inverts the usual mental model — instead of enumerating hundreds of safe commands (which is
what most blog posts and the `claude-allow-list` repo do), you allow everything and enumerate the
~80-100 patterns you _don't_ trust unattended (destructive git, `rm -rf`, cloud `delete`/`destroy`,
`DROP`/`TRUNCATE`, pipe-to-shell, force-push, etc.). It's far less maintenance (new CLI tools need
no new rules; only genuinely dangerous new patterns need adding), and it's what Anthropic's own
"blocking hook takes precedence over allow rules" mechanism (`exit code 2` in the hook stops the
call before permission rules are even evaluated) is designed to support. A hook can also be a
one-liner Python/bash script rather than a 1000-line settings.json.

The `claude-allow-list` repo takes the opposite (allowlist-only, no hook) approach and gets to
~1,184 individual rules across 17 files to cover a comparable tool surface — illustrative of how
much larger the enumerate-the-safe-set approach is than enumerate-the-dangerous-set.

**Trade-off to weigh, not a clear winner either way**: allow-all+hook trusts the hook's regex
coverage completely (their own red-team notes in `repos/claude-code-permissions/analysis.md` admit
~90% catch rate against encoding/indirection attacks — variable indirection, base64+pipe, brace
expansion); a pure allowlist trusts nothing not explicitly listed but is far more prompts for
anything outside the curated set and needs upkeep as new tools get used. Anthropic's docs frame the
hook as the mechanism _for people who've already decided allow-`Bash` is their posture_, not as
strictly superior — sandboxing (below) is what they position as the actual security boundary either
way.

### Sandboxing is the orthogonal, stronger control

`/sandbox` (macOS: built-in Seatbelt, zero install; Linux/WSL2: needs two packages, `/sandbox` shows
what's missing; native Windows unsupported, use WSL2). This restricts filesystem writes and network
access for Bash **at the OS level**, independent of permission rules — it's what stops a
prompt-injected command from reaching `~/.ssh` even if some allow rule technically matches. Config
via `sandbox.filesystem.{allowRead,denyRead}` and `sandbox.network.{allowedDomains,deniedDomains}`
merges with `Read`/`Edit`/`WebFetch` permission rules into the final boundary. Worth a dedicated
follow-up since it's a bigger lift (OS packages on Linux) — noted here as the thing permission rules
alone don't give you: `rm -rf` inside a sandboxed root is still fully destructive to that root,
sandboxing constrains _where_, hooks/allowlists constrain _what_.

## GitHub Copilot (VS Code agent mode)

Two generations of settings coexist in the wild; current (VS Code ~1.10x+, per official docs at
`code.visualstudio.com/docs/agents/run/approvals`) is:

- **Permission levels** (session-scoped, not persisted by default): Default Approvals / Assisted
  (LLM risk-scores each call) / Bypass Approvals / Autopilot (bypass + autonomous iteration).
  `chat.permissions.default` sets the default level.
- **`chat.tools.terminal.autoApprove`** — object keyed by **regex** (wrapped in `/…/`) or literal
  command prefix, boolean value. Official example:
  ```json
  "chat.tools.terminal.autoApprove": {
    "/^git (status|show\\b.*)$/": true,
    "del": false,
    "/dangerous/": false
  }
  ```
  This is a fundamentally different matching engine than Claude's glob-prefix rules — full regex,
  not shell-glob. A Claude rule like `Bash(git log:*)` becomes a Copilot key like
  `"/^git log\\b.*/"`(roughly) — not a copy-paste port, every rule needs re-expressing.
- Older/parallel keys still referenced in blog posts: `github.copilot.chat.tools.terminal.allowlist`
  / `.denylist` (plain string array, prefix match) — appears to be an earlier or alternate surface;
  treat the `chat.tools.terminal.autoApprove` regex form as current per the official docs page, and
  verify which one a given VS Code/Copilot version actually reads before relying on either.
- **`chat.agent.sandbox.enabled`** (macOS/Linux/WSL2) — analogous to Claude's `/sandbox`: sandboxed
  terminal commands auto-approve without a dialog, filesystem allow/deny via
  `chat.agent.sandbox.fileSystem.<platform>.{allowRead,allowWrite,denyRead,denyWrite}`, network via
  `chat.agent.networkFilter` + `chat.agent.{allowed,denied}NetworkDomains`.
- `chat.tools.eligibleForAutoApproval` — per-tool opt-out, forces manual approval for named tools
  even under a broad auto-approve policy.
- Global YOLO: `chat.tools.global.autoApprove` (with a one-time warning dialog) or the `/yolo` /
  `/autoApprove` slash commands.

**Practical implication for "convert Claude rules to Copilot rules"**: the _tool classification_
(tool-rules.md) is reusable as-is between the two systems — "is `kubectl get` safe" doesn't change
per-agent. The _syntax_ does not port: Claude is glob-prefix, Copilot is regex. Any conversion has
to regenerate the pattern strings per target, not transliterate them.

## Comparison table

|                            | Claude Code                                                                   | Copilot (VS Code agent mode)                                                          |
| -------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Config file                | `.claude/settings.json` (+ `.local.json`, `~/.claude/settings.json`, managed) | `.vscode/settings.json` (workspace) or user `settings.json`                           |
| Pattern syntax             | glob-prefix (`Bash(cmd *)`, `:*` suffix)                                      | regex (`/^cmd\b.*/`) or literal prefix key                                            |
| Rule precedence            | deny → ask → allow, first match wins regardless of specificity                | last matching key in the object wins (standard JS object semantics)                   |
| Compound-command awareness | yes — splits on shell operators, each subcommand must match                   | not documented as thoroughly; regex applies to the whole command line unless anchored |
| Built-in always-safe set   | yes (`ls`, `cat`, read-only `git`, etc.), non-configurable                    | no equivalent documented                                                              |
| OS sandbox                 | `/sandbox` (Seatbelt / bubblewrap+landlock / WSL2)                            | `chat.agent.sandbox.enabled` (macOS/Linux/WSL2)                                       |
| Team/org policy            | managed settings, MDM, `allowManagedPermissionRulesOnly`                      | device management policies (mentioned, less documented here)                          |
| Known reliability caveat   | #18846: allow/deny not always enforced, hook workaround exists                | not investigated — worth checking before relying on autoApprove alone                 |

## Meta-finding: cloned repos' own `CLAUDE.md` auto-loads

Observed directly during this research, not from a secondary source: reading a file inside
`repos/claude-code-best-practice/` caused Claude Code to auto-inject _that repo's own_
`.claude/rules/*.md` and root `CLAUDE.md` as instructions into the session — including directives
like "create a separate commit per file" that are not anything the user asked for. Claude Code walks
up the directory tree from any file it touches looking for `CLAUDE.md`/`.claude/rules/`, so cloning
a full third-party repo into the working tree (rather than, say, a bare/sparse checkout, or a
location outside the walked tree) means its config becomes ambient instructions the moment any tool
reads inside it. None of the cloned repos here contained anything adversarial, but this is a real
prompt-injection surface worth remembering for `reference/repos/` in general: a cloned repo's
`CLAUDE.md` is untrusted content, not instructions, even though the harness will present it as the
latter.

## Sources

- https://code.claude.com/docs/en/permissions (cached: `docs/claude-code-permissions-official.md`)
- https://code.claude.com/docs/en/sandboxing (cached: `docs/claude-code-sandboxing-official.md`)
- https://code.visualstudio.com/docs/agents/run/approvals
- https://github.com/anthropics/claude-code/issues/18846
- https://github.com/anthropics/claude-code/issues/18160
- https://github.com/UgurcanAkkok/claude-allow-list (cloned: `repos/claude-allow-list/`)
- https://github.com/dylancaponi/claude-code-permissions (cloned: `repos/claude-code-permissions/`)
- https://github.com/SpillwaveSolutions/claude_permissions_skill (cloned:
  `repos/claude_permissions_skill/`)
- https://github.com/thegeosman/claude-code-settings, https://github.com/dwillitzer/claude-settings
  (cloned, near-duplicates)
- https://gist.github.com/boriskellerman/48880813830cccd0fb41de5314b3d8bf (cross-platform command
  list, not cloned)
