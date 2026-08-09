# CLI permission allowlist

Claude Code (and similar agent harnesses) prompt for approval on most Bash commands. Most of what
gets run in a typical session is safe — inspecting, listing, describing — and approving the same
`kubectl get`/`git log`/`docker ps` shape of command over and over is pure friction. The fix isn't
a hand-written list of "safe commands" (stale the moment a tool updates, and nobody keeps it in
sync) — it's a small pipeline that regenerates the list from what's actually installed, classifies
it with an LLM instead of guessing, and keeps a human in the loop before anything gets trusted.

That pipeline lives in `cli-allowlist/` (tracked in git — this is original derived project config,
not vendor material) and `tasks/allowlist.py` (`inv allowlist.*`). This page is the durable
explanation of *why* it's built the way it is; the code docstrings cover the *how*.

## Architecture: extract → classify → review → apply

```
inv allowlist.extract   deterministic, no LLM      captures --help text, version-gated
inv allowlist.classify  LLM (headless claude -p)    read_only / write / dangerous per subcommand
inv allowlist.review    human gate                  you look at what changed, mark it reviewed
inv allowlist.apply     deterministic, no LLM       merges reviewed rules into ~/.claude/settings.json
```

Each stage is independently re-runnable and cheap to re-run when nothing changed — that's the
point. `extract` is skipped per-tool when `--version` output hasn't changed; `classify` is skipped
per-tool when the extracted help text hasn't changed (content-hash-gated); `apply` is a no-op when
the computed rule set already matches what's live. A routine re-run after `apt upgrade` costs
close to nothing and makes zero LLM calls unless a tool's actual command surface changed.

### `tools.toml` — the registry

`cli-allowlist/tools.toml` lists every tool `extract` probes, one `[tool]` section per binary.
Most CLIs are `<tool> <subcommand> --help` cobra/click/argparse programs and need no special
handling, but the registry has escape hatches for the ones that aren't, discovered by testing, not
guessed:

- **`help_flag`** — override the default `--help`. `git` uses `-h` instead: see below.
- **`help_style = "prefix"`** — some tools put the flag *before* the subcommand
  (`go help list`, not `go list --help` — the latter is just a one-line stub pointing at the
  former). Only `go` needs this so far.
- **`no_subcommands`** — flat tools (coreutils, `jq`, `curl`, `rsync`, `bash`, `zsh`...) where the
  risk lives in flags, not a subcommand tree. Classified as one unit.
- **`skip_interactive`** — TUI-only tools (`k9s`, `vim`) with no non-interactive surface to
  classify at all.
- **`shell_prefix`** — for tools that aren't binaries. `nvm` only exists as a shell function after
  sourcing `nvm.sh`; `which nvm` fails and a direct exec fails. Extraction instead runs
  `bash -c "<shell_prefix> && nvm <args>"`.
- **`version_flag`** — several tools don't use `--version`: `kubectl` needs `version --client`,
  `helm` needs `version --short`, `go` needs `version`, `tmux` needs `-V`, `ssh`/`unzip` need
  `-V`/`-v`. Guessed wrong for all of these on the first pass; caught by actually running each one
  and reading the output, not by assuming GNU-style conventions apply everywhere.

Coverage isn't limited to what `setup.toml` installs — it also includes the base system
(coreutils, util-linux, diffutils, procps, tar/gzip/bzip2/xz), audited via `dpkg -L coreutils` etc.
rather than from memory, since an agent reaches for `cat`/`cp`/`rm`/`dd` just as often as anything
PULSE explicitly installs.

### Deterministic extraction has more sharp edges than it looks like

Two real, empirically-confirmed problems, not hypothetical ones:

1. **A tool's `--help` can depend on a separately-installed package.** `git status --help`
   renders through the system `man` command, which needs the `git-man` package. It happened to be
   installed on the machine this was built on, which made the bug invisible until tested with a
   stripped environment. Fixed by using `git -h` instead — a self-contained synopsis with no
   package dependency. `cli-allowlist/check_man_deps.py` runs every registered tool's help
   invocation under `strace -f -e trace=execve` and checks for a child `exec` of `/usr/bin/man` —
   the only reliable way to tell "renders like a man page" (`gcloud`, which mimics man's
   NAME/SYNOPSIS/DESCRIPTION layout with its own self-contained renderer, no `man` involved) apart
   from "actually shells out to man" (`git`, the one real case found so far). Re-run it
   (`python3 cli-allowlist/check_man_deps.py`) after registering a new tool.
2. **Extraction must be portable, not just correct on the machine that wrote it.** `PAGER`,
   `MANPAGER`, `GIT_PAGER`, and `BROWSER` are neutralized (`cat`/`true`) for every extraction call
   — the actual defense here isn't "nothing tries to page or open a browser," it's that the
   captured text can't depend on this machine's interactive shell configuration.

### Classification via headless Claude

`classify` shells out to the `claude` CLI already installed on this machine (`-p`/`--print`,
`--model haiku`, `--output-format json`, `--json-schema` for enforced structure) rather than
standing up separate Anthropic API billing. This was the answer to "how do you automate the LLM
judgment call without new infrastructure": reuse what's already paid for and authenticated.

Things that weren't obvious until tested:

- **`--bare` cannot be used.** It restricts auth to `ANTHROPIC_API_KEY`/`apiKeyHelper` only — "OAuth
  and keychain are never read" per its own `--help` text — and this account is logged in via
  OAuth, so `--bare` calls fail outright with "Not logged in". Isolation from this repo's own
  `.claude/` instead rests on running with `cwd` pointed at a scratch directory outside the repo
  entirely, plus `--disallowedTools` covering every file/exec/subagent-spawning tool as a backstop.
- **`--json-schema` output lands in `structured_output` at the top level of the response envelope**,
  not nested inside `result` as text (that field is just the model's natural-language summary).
- **`claude -p` waits ~3s for stdin and prints a warning that breaks JSON parsing** unless stdin is
  explicitly closed (`stdin=subprocess.DEVNULL`).
- **A single flat "classify this whole tool as one thing" prompt is genuinely ambiguous.** The
  first attempt used a heading literally named `*` for `no_subcommands` tools; the model read that
  as "find distinct things to classify" and broke `nuitka --help` into per-flag verdicts
  (`--mode`, `--run`, ...) instead of one verdict for the tool. Fixed by asking explicitly for a
  single entry under a fixed key (`_default_`), with a conservative fallback (take the most
  cautious of whatever came back) if a future tool's help text confuses it the same way again.
- **Cost is dominated by fixed per-call overhead, not prompt size.** A single trivial 2-item
  classification call cost ~$0.026 and ~12s at Haiku — a real tool with 15-25 subcommands costs
  roughly the same ballpark. Classifying the ~70 tools not already covered by a community-sourced
  seed (see below) cost under $2 total, one time; steady-state re-runs are close to free because of
  the content-hash gate.
- **A deterministic safety backstop runs after every LLM call, at no extra cost**: any subcommand
  the model marks `read_only` gets re-checked against a small set of dangerous-sounding verb tokens
  in the subcommand *name itself* (`delete`, `destroy`, `rm`, `force`, `run`, `exec`, ...) — a
  match downgrades it to `needs_review` regardless of what the model said. `run`/`exec` were added
  to this list after the model classified `nvm run`/`nvm exec` as `read_only`, which is wrong —
  they execute arbitrary commands. (This does cause one known, accepted false positive: `gh run`
  — the noun, GitHub Actions run history, not a verb — also gets flagged. Harmless: it just means
  that one entry falls back to a normal prompt instead of being pre-approved, same as any other
  `needs_review` entry.)

Six tools (`git`\*, `gh`, `kubectl`, `helm`, `docker`, `terraform`, `gcloud`) were seeded from a
cloned community allowlist repo rather than classified fresh — `source: "community"` in
`rules.json` — on the theory that a well-covered, actively-maintained community list is a fine
starting point for stable, widely-used tools. (\* `git` was later reclassified via LLM anyway,
after switching its `help_flag` to `-h` changed the extracted text enough to invalidate the seed's
hash — an expected one-time cost of that fix, not a bug.)

### Review — the human gate

`inv allowlist.review` shows what's new or changed since the last reviewed snapshot and, on
confirmation, marks a tool `reviewed: true`. **Nothing downstream trusts an unreviewed entry** —
`render` and `apply` silently exclude any tool that hasn't been through this. This is a
per-*tool* gate, not per-subcommand: there's no mechanism (yet) to individually override a single
subcommand's classification without re-running the LLM step, which is why `needs_review` entries
stay excluded even after their tool is marked reviewed.

### `render` / `apply` — where the classified data goes

`render --target=claude|copilot` is pure, deterministic, output-only: turns the reviewed subset of
`rules.json` into Claude `Bash(...)` glob-prefix rules or Copilot `chat.tools.terminal.autoApprove`
regex rules. It never writes anywhere by itself.

`apply` (Claude only, so far) is what actually makes the rules take effect: it merges the
`allow`/`ask` output into **`~/.claude/settings.json`**, the global per-user config that applies to
every project on this machine. Two things make this safe to run repeatedly without either
clobbering your own settings or leaving stale rules behind:

1. **Only the `permissions` block is ever touched.** Every other key — `theme`, `effortLevel`,
   `cleanupPeriodDays`, anything else you or a future you adds — is read, kept, and written back
   unchanged.
2. **A local manifest tracks exactly which rule strings this pipeline wrote last time**
   (`~/.local/state/pulse/claude-settings-applied.json` — deliberately *not* repo content, unlike
   everything under `cli-allowlist/`, since it's machine-local mutation-tracking state for an
   out-of-repo file, the same category as `~/.config/pulse/identity.toml`). On each run, only rule
   strings present in that manifest are eligible for removal; anything else already in your
   `permissions.allow`/`ask` — a rule you added by hand — is never touched, and a rule this
   pipeline generated before but no longer does (a tool's classification changed) gets cleanly
   removed instead of left orphaned. A `.json.bak` is written alongside the settings file before
   every real change.

Verified directly, not just by reading the code: idempotent re-run is a true no-op; a manually
added rule survives repeated `apply` runs untouched; a tool's classification changing tiers (tested
by flipping one back and forth) correctly moves its rule between `allow` and `ask` with an accurate
diff report. (The first version of the diff report was itself wrong — it compared the flattened
union of both arrays, so a rule moving from `allow` to `ask` printed as `+0 -0`. Caught by testing
the actual move, not by reading the diff logic and assuming it was right.)

Both tiers always still let you approve interactively — `write` and `dangerous` classifications
render as `ask` rules, never `deny`. This was a deliberate call, not an oversight: a PreToolUse
hook that intercepts and blocks specific patterns (the approach a couple of community repos take,
and what Anthropic's own docs suggest as the workaround for prefix-glob allowlisting's known
fragility) was considered and rejected — it changes the agent's control flow more invasively than
a declarative `ask` rule, for a benefit (catching a dangerous command *before* Claude even proposes
it, vs. after) that didn't seem worth the added complexity of a custom interception script. What
matters is that dangerous-tier commands still surface a real, interactively-approvable prompt
instead of running silently — plain `ask` rules already get that.

### End-to-end confirmed live

This isn't just tested in isolation — after `apply`, the actual rules were exercised in a live
Claude Code session: `allow`-tier commands (`git status`, `cat`, `jq --version`) ran without any
visible prompt; `ask`-tier commands (`rm --help`, `git add --help`, `npm install --help` — chosen
so they're harmless to execute either way) triggered real permission prompts. Confirmed by the
user watching the session, since a silent auto-approval and an instantly-approved prompt look
identical from the agent's own side.

## Retention policy note

While reviewing the global `~/.claude/settings.json` for this work, `cleanupPeriodDays` (governs
how long session transcripts, `tasks/`, `shell-snapshots/`, and `backups/` under `~/.claude/` are
kept before cleanup) was checked and deliberately left at **365** — the default is 30; other users
in the wild range from 60 to effectively-unlimited (99999). Not a disk problem at the time this was
reviewed (~52M total under `~/.claude/`, oldest transcript only a couple of days old on a
freshly-set-up install) — this was a preference call, not a fix.

## Operating it

```shell
# after installing a new tool, or periodically (e.g. after apt upgrade):
inv allowlist.extract
inv allowlist.classify
inv allowlist.review      # look at what's new/changed, approve it
inv allowlist.apply       # merge into ~/.claude/settings.json

inv allowlist.status                        # what's tracked, stale, or still unreviewed
inv allowlist.render --target=copilot       # Copilot's format instead — still print-only, no apply yet
python3 cli-allowlist/check_man_deps.py     # re-check for new man-page dependencies
```

## Known gaps / deliberately not built

- **`apply` only targets Claude's `settings.json`.** Copilot's `chat.tools.terminal.autoApprove`
  still needs manual copy-paste from `render --target=copilot`.
- **No sandboxing integration** (`/sandbox`, OS-level filesystem/network isolation) — a stronger,
  orthogonal control considered out of scope for this pass.
- **No PreToolUse hook** — see the `render`/`apply` section above for why this was a deliberate
  rejection, not a TODO.
- **No subcommand-level review override** — `needs_review` entries (currently just `nvm run` /
  `nvm exec`) stay excluded from both `allow` and `ask` until the underlying classification changes
  and gets re-run through the LLM step; there's no way to manually promote one without that.
