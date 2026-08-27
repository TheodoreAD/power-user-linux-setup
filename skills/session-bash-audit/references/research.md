# Session Bash audit — research and evidence

Dated findings behind `SKILL.md`. Append; don't rewrite history — the value is in the deltas.

## Contents

- [Baseline 2026-08-24](#baseline-2026-08-24)
- [Root causes (2026-08-24)](#root-causes-2026-08-24)
- [The `git -C` ask-rule bypass](#the-git--c-ask-rule-bypass)
- [Mode comparison: acceptEdits vs auto](#mode-comparison-acceptedits-vs-auto)
- [Harness facts (checked 2026-08-24)](#harness-facts-checked-2026-08-24)
- [Decisions taken 2026-08-24](#decisions-taken-2026-08-24)
- [Rejected: a PreToolUse nudge hook](#rejected-a-pretooluse-nudge-hook)
- [Prompt audit 2026-08-25: the first day of acceptEdits](#prompt-audit-2026-08-25-the-first-day-of-acceptedits)
- [`pgrep -f` matches the harness's own wrapper (2026-08-25)](#pgrep--f-matches-the-harnesss-own-wrapper-2026-08-25)
- [Shell backgrounding can be killed before the command runs (2026-08-26)](#shell-backgrounding-can-be-killed-before-the-command-runs-2026-08-26)
- [`rg -r` is `--replace`, not `--recursive` (2026-08-27)](#rg--r-is---replace-not---recursive-2026-08-27)
- [Open / to re-measure](#open--to-re-measure)

## Baseline 2026-08-24

Window: transcripts modified 2026-08-21 → 2026-08-24, three repos (`power-user-linux-setup`,
`repo-tasks`, `scaffoldapy`), 3,956 Bash calls (98 from subagents). Every session in the window ran
in **auto mode** (the machine default at the time). Rates are share of that model's calls.

| model (main sessions) |    n | any chain | 5+ chain | `\| head/tail` | exit-masked | `sed -n` | git commit/push in chain | `cd` (any) |
| --------------------- | ---: | --------: | -------: | -------------: | ----------: | -------: | -----------------------: | ---------: |
| Sonnet 5              | 1828 |       64% |      13% |            29% |         23% |       3% |                       7% |        16% |
| Opus 5                | 1676 |       71% |      24% |            32% |         11% |       8% |                       8% |        10% |
| Fable 5               |  354 |       35% |       3% |            19% |         12% |       2% |                       2% |         2% |
| Sonnet 5 (subagent)   |   75 |       52% |      20% |            29% |          0% |      32% |                       0% |        76% |
| Haiku 4.5 (subagent)  |   23 |       39% |       0% |            26% |          4% |       0% |                       0% |        43% |

Other counts in the window:

- `2>&1 | tail/head/grep` (exit code masked): 662, of which 364 wrapped a quality/test gate
  (`inv quality.*`, `pytest`, `basedpyright`). `~/AGENTS.md` already had the rule; the habit and the
  rule never connected.
- `rg/grep … | head` on a search meant to be complete: 201.
- Standalone file views via `cat`/`sed -n`/`head` that `Read` would have done: 156.
- Same command re-issued after a `| head/tail`-truncated first run: 51 — the direct waste.
- `echo "=== label ==="`-batched multi-step calls: 375.
- `cd` into the session's own repo (cwd already there): 114. `cd` into another personal repo: 372.
- `git -C <path> commit|push|add`: 81, zero errors, zero prompts (see below).
- Denials: 29 of 3,956 — a handful of classifier blocks (`settings.json` edits via `python3 -c`, a
  `cp` into `~/.config`), the rest human declines. Chaining itself never drew a denial.
- Subagent spawns: 17 (`Plan`, `Explore`, `claude-code-guide`, `fork`, `statusline-setup`). Only
  `fork` inherits context; the others never load `AGENTS.md`, and only 5 of the 17 prompts mentioned
  it. Subagent `sed -n` (32%) and `cd` (76%) rates were the worst anywhere.

Re-measure with `scripts/audit.py --days N`; the script's own tags are a superset of this table
(`heredoc`, `python-c`, `label-echo`, `env-prefix` were added after the first pass).

## Root causes (2026-08-24)

Ranked by how much of the behaviour each explains. The first two are structural; wording changes in
`~/AGENTS.md` cannot fix them, which is why the prior "strengthen the rule" iterations hadn't.

1. **Auto mode injects the opposite instruction.** Verbatim, in the system prompt of every auto-mode
   session:

   > While auto mode is active: Do your work through the Bash tool wherever it can accomplish the
   > job: read files with cat, head, or sed -n, search with grep and find, and make file changes
   > with sed, heredocs, or short scripts, rather than using the dedicated Read, Edit, or Write
   > tools. Fall back to a dedicated tool only when Bash genuinely cannot do the job.

   It names the same four anti-patterns `~/AGENTS.md` names and reverses each. A live harness
   directive in system-prompt position beats standing instruction-file prose. It also drags every
   read and edit into Bash, where chaining then happens. Presumably it exists because the auto-mode
   classifier reads shell commands (it never sees tool results) and wants intent in shell form.

2. **No felt friction, so the rule's stated reason evaporated.** `~/AGENTS.md` justified "several
   simple calls" purely as allowlist prompt friction. In auto mode nothing prompted (29 denials in
   3,956 calls), and `cat`, `sed -n`, `grep`, `rg`, `fd` were all in `allow`. "Friction cost, never
   a prohibition" + no observed cost → chain freely. The costs that actually matter (lost output,
   masked exit codes, ask-rule bypass, lost parallelism) weren't the rule's rationale, so the model
   never weighed them.

3. **Chaining is the model's native efficiency instinct.** One round-trip for N facts, labelled with
   `echo ===`; and a chain _sequences_ dependent steps (`run > log; echo $?; tail log`). The harness
   says independent calls in one response run in parallel, but nobody told the model the
   harness-side downsides of a chain. Rates differ sharply by model under identical rules (Opus 24%
   five-part chains, Fable 3%) — disposition, not wording.

4. **`head`/`tail` is context anxiety.** Models truncate to protect context. The harness already
   truncates large output and persists the full text to a file ("Output too large … saved to …");
   nobody told the model, so it pre-truncates, loses data, and re-runs (51×). Combined with
   `2>&1 | tail` on gates it also masks exit codes; that rule existed but was stated separately from
   the head/tail habit.

5. **`cd` into the own repo** was cargo-culted from the documented cross-repo form
   (`cd <repo> && PATH=… inv`). 114 own-repo `cd`s did nothing. Cross-repo `cd`s are also
   prompt-inducing by harness design (`cd` + `git` in one command always prompts), which is part of
   why `git -C` became popular.

6. **Knowing the rule is not the same as loading it — and neither changes the reflex without a
   substitute.** The session that rewrote the Bash cluster audited itself an hour later: 124 calls,
   65% chained, 36% `head`/`tail`, worse than the Fable baseline it had cited. Instruction files
   load at session start, so the rewrite never reached the session that wrote it (and auto mode's
   reminder was still live there). But with the rule fresh in working memory the habit held anyway,
   because nearly every violation was one shape the rule offered no substitute for:
   `gate > log
   2>&1; echo $?; sed … log | rg … | head` — the permitted capture form with a filter
   bolted on to keep a long log out of context — plus a reflexive `; echo "EXIT=$?"` the Bash tool
   makes redundant. Both got a named substitute in the rule (Grep/Read on the log as a second call)
   and their own audit patterns (`redirect-then-filter`, `echo-exit`, both expected at zero).

## The `git -C` ask-rule bypass

The user's report was "ask rules like `git commit`/`git push` seem ignored inside long chains."
Chains were not the mechanism: Claude Code splits on `&&`, `||`, `;`, `|`, `|&`, `&`, newline and
matches each subcommand independently (docs, and a live test recorded in
`plans/2026-08-22-compound-command-permission-audit.md`). The mechanism is **prefix matching plus a
global option**: `Bash(git push:*)` does not match `git -C /path push`, so the call matched no rule,
fell through to the auto-mode classifier, and the classifier's documented default allows pushes to a
working repo's remotes. 81 such calls in the window, all executed, none prompted. Same hole for
`git -c k=v push`, `git --git-dir=… push`. `~/AGENTS.md` itself recommended `git -C <path>` for
cross-repo work — the bypass was the documented preferred form.

Under `acceptEdits` the hole closes by itself: an unmatched non-read-only Bash command prompts. The
read-only forms (`git -C x status`) would prompt too; `tools.toml`'s `global_option_prefixes`
renders `Bash(git -C * status:*)`-style allow rules for those (with a known multi-argument wildcard
hole, accepted deliberately — see `contributing/cli-allowlist.md`).

## Mode comparison: acceptEdits vs auto

Against this machine's allowlist philosophy (classify every installed CLI from real `--help` output;
`ask` on the ~60 genuinely mutating verbs stays a human checkpoint; prompts are review signal for
`inv allowlist.review`):

|                                          | `acceptEdits` + allowlist                            | `auto`                                                                |
| ---------------------------------------- | ---------------------------------------------------- | --------------------------------------------------------------------- |
| Who decides an unmatched Bash call       | you (prompt) — and the prompt feeds the review loop  | a Sonnet classifier, from the transcript; no signal back to the rules |
| Allowlisted read-only / quality commands | no prompt                                            | no prompt                                                             |
| `git commit`/`push` checkpoint           | ask rule, deterministic; unmatched shapes prompt too | ask rule only if the prefix matches; `git -C` slips to the classifier |
| In-scope edits, `mkdir`/`cp`/`rm`/`sed`  | auto-approved by path scope, prompt outside          | classifier                                                            |
| Model behaviour                          | Read/Edit/Grep per `~/AGENTS.md`                     | harness reminder pushes everything into Bash                          |
| Failure mode                             | an occasional prompt                                 | silent allow, or a hard classifier deny with no prompt to override it |
| Determinism                              | same command → same outcome                          | depends on transcript state, compaction, stated "boundaries"          |
| Subagents                                | same rules, prompts surface                          | classifier at spawn, per action, and on return                        |

The two are different theories of trust. The allowlist work is exactly `acceptEdits`' model; auto
mode's premise is "don't classify, judge", and it actively degrades the behaviours (dedicated tools,
simple commands) that make prefix rules work. They can't be reconciled by rules or prose, so the
machine default moved to `acceptEdits` (dogfooding from 2026-08-24). Auto mode remains a per-session
opt-in for exploratory work where classifier judgment is acceptable; nothing in the repo fights it
when it is on.

## Harness facts (checked 2026-08-24)

Sources: `https://code.claude.com/docs/en/permission-modes.md`,
`https://code.claude.com/docs/en/permissions.md`, fetched 2026-08-24. Re-check before relying on any
of these across a Claude Code upgrade.

- **Rule precedence**: deny > ask > allow, no specificity tiebreak. "A matching ask rule prompts
  even when a more specific allow rule also matches the same call." Ask/deny also apply on top of
  the built-in read-only set ("to require a prompt for one of these commands, add an ask or deny
  rule") — hence `mode_covered`: an ask rule for `mkdir` would beat `acceptEdits`' in-scope grant.
- **Compound commands**: split on `&&`, `||`, `;`, `|`, `|&`, `&`, newline; every subcommand must
  match a rule on its own. Newline is a separator, so `\` continuations change nothing.
- **Wildcards**: `*` anywhere in a Bash rule, and a single `*` spans any number of arguments
  (`Bash(git * main)` matches `git push origin main`). `Bash(ls *)` enforces a word boundary;
  `Bash(ls*)` doesn't. `:*` is only recognized at the end.
- **Wrappers stripped before matching**: `timeout`, `time`, `nice`, `nohup`, `stdbuf`, `command`,
  `builtin`, `noglob`, bare `xargs`; a leading assignment of _known-safe_ env vars only. A deny/ask
  rule matches past any leading assignment; an allow rule doesn't. Not stripped: `direnv exec`,
  `npx`, `docker exec`, `watch`, `setsid`, `find -exec/-delete`.
- **Built-in read-only set** (every mode, not configurable):
  `ls cat echo pwd head tail grep find
  wc which diff stat du cd` and read-only `git`. A `cd`
  inside the working directory or an additional directory is read-only, but **`cd` + `git` in one
  command always prompts** (hooks in the target repo), and `cd` + an output redirect prompts unless
  the target is `/dev/null`.
- **Redirects** are checked as file writes against Edit rules, protected paths, and working
  directories; a `~`-prefixed or glob target needs approval.
- **`acceptEdits`**: auto-approves Edit/Write in scope plus `mkdir touch rm rmdir mv cp sed` on
  in-scope paths (also behind safe env prefixes and `timeout`/`nice`/`nohup`); everything else
  outside the read-only set prompts. `additionalDirectories` in a settings file grants file access
  only — no `CLAUDE.md`, skills, or hooks load from them (unlike `--add-dir`).
- **`auto`**: allow/ask/deny resolve first (an ask rule that names a command still forces a prompt);
  everything unmatched goes to the classifier (Sonnet 5 by default; Opus for Fable sessions). The
  classifier sees user messages, `CLAUDE.md`, and tool _calls_ — never tool results. Denials in most
  sessions are the fixed text `Blocked by classifier`; 3 consecutive or 20 total blocks pause auto
  mode. On entering auto mode, broad allow rules that grant arbitrary execution (`Bash`, `Bash(*)`,
  `Agent`, `Monitor`) are dropped for the session. Pushes to the working repo's remotes and PR
  creation run without a prompt by default. Subagents: task description evaluated at spawn, each
  action classified, full history reviewed on return; a subagent's own `permissionMode` is ignored.
- **Auto mode's Bash-preference reminder** is not documented on either page, and no setting to
  suppress it was found. Treat it as a property of the mode.
- **Probed live 2026-08-25** (user watching, four single-call probes, run twice): under
  `acceptEdits`, an allow rule does **not** exempt a read outside the working directory,
  `additionalDirectories`, or a `Read(...)` rule — `rg -c x ~/.claude/settings.json` prompted with
  `Bash(rg:*)` in `allow`. The same check honours `Read(...)` rules for Bash read-only commands:
  `ls ~/projects/…/repo-tasks/plans` did not prompt once `Read(//home/…/projects/**)` was in place.
  `rg … | sort | uniq -c` did not prompt (so `sort`/`uniq` count as read-only filters even though
  the documented list doesn't name them), and an unquoted glob (`rg … tasks/*.py`) did not prompt
  for `rg`. Consequence: the harness's own overflow files
  (`~/.claude/projects/<slug>/<session>/
  tool-results/*.txt`, "Output too large … saved to") are
  outside every grant, so reading one back with `rg`/`cat` prompts — `Read` on them does too.
  `scripts/prompts.py` models the path check since the same day (`read-outscope`).
- **Plan mode with auto available**: shell commands during planning go to the classifier too
  (`useAutoModeDuringPlan`, default on).

## Decisions taken 2026-08-24

- Machine default permission mode → `acceptEdits`, declared as `claude_default_mode` on
  `[packages.claude-code]` in `setup.toml`, synced by `inv ai.install-skills`.
- `/tmp/claude-1000` and `~/.claude/jobs` → `permissions.additionalDirectories`
  (`claude_additional_directories`, same package), so harness scratch writes don't prompt.
- `cp mv rm rmdir mkdir touch` keep their `write` classification but stop rendering as `ask`
  (`mode_covered = true` in `cli-allowlist/tools.toml`); the hand-maintained `Bash(sed -i*)` /
  `Bash(sed --in-place*)` ask rules were removed for the same reason.
- `git` gets `global_option_prefixes = ["-C *", "-c *"]` → allow rules for read-only verbs behind a
  global option; the mutating forms rely on "unmatched prompts" in `acceptEdits`.
- `~/AGENTS.md`'s Bash cluster rewritten around the real costs (one call = one whole output and one
  exit code; per-subcommand prefix matching; parallelism already free), with the closed list of
  permitted chain shapes and the head/tail and own-repo-`cd` tells. Evidence in
  `contributing/global-agents-md.md`.
- No nudge hook (below). No rules written against auto mode's reminder — the mode is the lever.

## Rejected: a PreToolUse nudge hook

A now-retired plan (`plans/2026-08-22-sed-read-nudge-hook.md` in `power-user-linux-setup`, abandoned
2026-08-24) proposed a non-blocking `PreToolUse`/`Bash` hook that injects "use Read instead" when it
sees `sed -n`. Dropped 2026-08-24: under auto mode it would fire on ~30% of calls against a standing
system-prompt instruction and lose on ordering; under `acceptEdits` the cause it targeted is gone;
and it contradicts the standing rule that agents get the same treatment as developers — taught what
to run, not corrected behind their back. The `Plan`/`Explore` blind spot it also cited is handled by
pasting the Bash-discipline paragraph into those subagents' prompts instead.

## Prompt audit 2026-08-25: the first day of acceptEdits

The user's report after one day on `acceptEdits` across the three repos: "a whole lot of manual
confirmations we should've taken care of with all that AGENTS.md work." Transcripts can't show an
approved prompt, so `scripts/prompts.py` was written to replay the harness's matching over every
call since the switch (2026-08-24 22:13 local) against the live `settings.json`. 373 main-session
calls, six sessions, all Fable:

- **40% of calls would have prompted.** Per session 8–75%; the two worst were sessions working
  across repos.
- **67% of those prompts were the git commit flow**: `git add` 35, `git commit` 26,
  `git -C ../other add|commit|fetch` 18, `git push` 10, `git rm`/`restore --staged`/`reset -q` 10.
  The rest: `inv deploy.all` 9 (its own `--yes` confirm plus a Bash prompt), the documented
  cross-repo `cd X && PATH=… inv …` form 12, read-only `inv --list`/`deploy.status`/`configs.diff`
  8, a handful of `python3 script.py`, `gh api`, `curl`, `bash script.sh`.
- Cause: two correct things interacting. `~/AGENTS.md` (rewritten 2026-08-24) mandates many small
  single-concern commits, staged right before each and `git fetch`ed before every push; the
  allowlist's honest `write` verdict for `add` rendered as `ask`, and
  `fetch`/`rm`/`restore`/`switch`/ `mv` weren't registered in `tools.toml` at all. Two to four
  prompts per commit, times the commit count the instructions drove up. Not a wording problem — no
  sentence in `~/AGENTS.md` could have moved it.
- Behaviour side (`--compare` against the auto-mode baseline): 11/30 expectations met. Opus/Sonnet
  unchanged, but every one of their sessions in the window predates the rewrite — nothing to
  conclude yet. Fable: chaining −6pp, head/tail −9pp, `echo EXIT=$?` +10pp (a habit that costs
  nothing under `acceptEdits` except a line). Chaining now has a direct price: one unmatched piece
  prompts the whole call.

Decisions (user, 2026-08-25): `commit` and `stash` stay `ask` — commit is the checkpoint, stash
hides work; everything that only touches the index and cannot lose code goes `allow`; every flag
shape that can lose code gets its own `ask`. Landed in `power-user-linux-setup`:

- `tools.toml` `[git]`: `allow_overrides = ["add", "rm", "reset", "restore --staged", "fetch"]`,
  `ask_overrides` for `reset --hard/--merge/--keep`, `restore --staged --worktree/-W`,
  `rm -f/--force/-rf/-fr` — each as `verb --flag` and `verb * --flag`, since the mid-pattern `*`
  spans any number of arguments and closes the flag-order hole. New render knob in
  `tasks/allowlist.py` (`contributing/cli-allowlist.md` "allow_overrides / ask_overrides");
  `fetch rm restore switch mv` registered; `inv allowlist.review --tool=<x>` added so one tool can
  be approved from a non-TTY without marking `sed`/`inv` reviewed.
- `setup.toml` `[packages.repo-tasks]` `claude_permissions_allow`: `inv --list`, `inv -l`,
  `inv deploy.status`, `inv allowlist.status`, `inv configs.diff`.
- Re-run against the new rules (507 calls by then): 40% → 30%, and 58 of the remaining 152 are
  `commit`/`push` — the two the user kept. What's left is disposition and one-offs: the cross-repo
  form (`cd` + env prefix, 13), `inv deploy.all`/`configs.*`/`allowlist.*` (mutating, correct to
  prompt), `python3 <script>`, `bash <script>`, `shfmt`/`basedpyright`/`bump-my-version --version`
  (tools not registered in `tools.toml` — candidates for `inv allowlist.extract` if they keep
  appearing outside `inv quality.*`).

Harness fact learned the hard way: `inv allowlist.review` from an agent's Bash tool can't answer its
confirm (`util.confirm` returns the default off a non-TTY), and `--apply-all` marks every pending
tool — which would have re-reviewed `sed` and `inv`, the exact near-miss
`contributing/cli-allowlist.md` records. Hence `--tool`.

## `pgrep -f` matches the harness's own wrapper (2026-08-25)

Noticed live, not by audit: `pgrep -af 'google-chrome.*--app-id'` returned exactly one "hit" — the
Bash tool's own invocation. Claude Code runs each call as
`zsh -c "source <snapshot> … && eval '<command>'"`, so the literal pattern text sits on a live
process's command line for as long as the call runs, and `-f` matches against full command lines.
The result reads as a genuine running process and drags the whole `DIRENV_DIFF`/`PATH` env blob into
context with it. `ps -C chrome -o args=` answered correctly (nothing running).

Added as the `pgrep-f` pattern. First measurement, `--days 7`: **24 calls out of 6652** (0.36%), all
true positives, no over-matching — one from the live session above, the rest from the 2026-08-24
ozone A/B (`pgrep -f 'user-data-dir=./ozone-test'`, `pkill -f` on the same string).

Two things make the rate understate the risk:

- `$(pgrep -f … | head -1)` usually escapes by luck, not design. `pgrep` prints ascending PIDs and
  the wrapper is the newest process, so it lands last and `head -1` takes the real one. Change it to
  `tail -1`, or have the real process start after the call, and the variable silently holds the
  wrapper's PID.
- `pkill -f <pattern>` can target the wrapper itself, i.e. the Bash call issuing it. The ozone A/B
  ran exactly this shape; it worked, but the failure mode is the call dying mid-command rather than
  anything reporting an error.

Fix is per-call, not a rule: match the executable (`pgrep -x chrome`, `ps -C chrome -o args=`)
rather than the command line. Routed here rather than into `~/AGENTS.md` (2026-08-25, user's call) —
the trigger is sharp and the miss is recoverable in one call, and that file is already at 33 rules /
390 lines against its own ≤15 / ≤200 reference points.

## Shell backgrounding can be killed before the command runs (2026-08-26)

Noticed live, not by audit, during the same Chrome ozone work. Three shapes were tried to launch a
throwaway Chrome instance and inspect it in a later call:

- `nohup $SP/oz-test.sh >/dev/null 2>&1 & disown` — tool reported exit 144; the script's **first**
  statement, an `env | grep > env-seen.txt`, never produced the file.
- `setsid $SP/oz-test.sh >/dev/null 2>&1 < /dev/null &` — same, no file.
- `OZONE_PLATFORM=x11 <chrome> --user-data-dir=… &` followed by `sleep 8` in the same call — this
  one **did** run.

So it is intermittent, and that is what makes it dangerous rather than merely unreliable. The
session read `/proc/<pid>/environ` and a process tree afterwards and drew a conclusion — that Chrome
ignores `OZONE_PLATFORM` — from a script that had never executed. The conclusion happened to be
right (confirmed independently by `strings` on the binary), but it was not evidence at the time. The
tell was cheap and nearly missed: the marker file the script writes before doing anything else was
absent.

Mechanism not diagnosed; 144 is `128+16`, and no signal was captured. Recorded as an observation,
not an explanation — someone re-deriving this should not assume the exit code means what it looks
like it means.

Added as the `shell-background` pattern (`nohup`, `setsid`, `disown`, or a trailing bare `&`). First
measurement, `--days 4`: **7 calls**, all from the session above. The rate is not the argument here
— the cost per occurrence is, since the failure produces _false evidence_ rather than an error, and
a background write or delete that silently did not happen is indistinguishable from one that did.

Fix: the Bash tool's own `run_in_background`, which survives across turns and re-invokes on exit.
When something must be backgrounded anyway, have it leave a marker the next call checks. Unlike
`pgrep -f` above, this one **was** also routed to `~/AGENTS.md` (2026-08-26, user's call: "we don't
like things that can fool us when writing or deleting files") — it extends the existing "Reading a
command's result" rule rather than adding a 34th, since it is the same
surface-signal-isn't-the-real-signal shape that rule already covers.

## `rg -r` is `--replace`, not `--recursive` (2026-08-27)

Added the `rg-replace` pattern row. ripgrep is recursive by default and its `-r` takes a replacement
string, so `rg -rn pat path` prints every match **with the matched text rewritten**. The output
looks like an ordinary search result and is not what the file says — which is the whole cost: it
fails silently and plausibly, unlike a flag error that errors.

`~/AGENTS.md` has warned about exactly this since before the measurement ("don't carry `grep -r`'s
flag across with the habit"), so this row measures adherence to an existing rule rather than
proposing a new one. That turns out to be the interesting part.

**First run, 3 days, 3875 Bash calls: 7 flagged.** Read individually rather than counted, per the
row's own "why":

- **3 genuine slips** — `rg -rn <pat> <dir>` meaning recursion, across three different projects and
  two different sessions. So it is not one session's tic.
- **2 deliberate and correct** — `rg -o '<pat with capture>' -r '$1' file`, the idiomatic
  capture-group extraction. Not defects, and the row must not be read as if they were.
- **2 false positives** — the literal text `-r` sitting inside a _quoted argument_ (a session
  grepping for this very trap, and a script body containing the regex). Unavoidable without
  quote-aware parsing, and shared with several other rows in the table.

[PITFALL: The row also has a known **false negative**. The pre-flag span excludes `|` so the scan
does not run past a pipe into an unrelated command, which means a quoted alternation stops it dead:
`rg -n -i 'rxnorm|ingredient' <path> -r ''` is a real slip that this row does not catch. Widening
the span to admit `|` would catch it and would newly false-positive on the common `rg … | xargs -r`,
so the exclusion stays. The measured 7 is therefore a floor, not a count.]

What this says about the rule rather than the tool: an always-loaded `~/AGENTS.md` rule naming this
exact flag did not prevent three slips in three days, two of them in a session whose author had read
the rule that morning. Worth carrying into the next mode comparison — it is one data point against
"write the rule and the behaviour follows", and for detection over instruction where the failure is
silent.

## Open / to re-measure

Both checks are procedures in `SKILL.md`, not chores for a human:

- **Compare** (a week of `acceptEdits` sessions):
  `audit.py --days 7 --compare
  references/baselines/2026-08-24-auto-mode.json`. The script's
  `EXPECTATIONS` encode what should move: `sed-n`/`cat-view`/`heredoc` down (no reminder), chaining
  down somewhat (rationale rewritten) but not to zero (disposition), `cd-own-repo` and
  `git-C-mutating` at zero. If chaining doesn't move, the next lever is model choice for long
  implementation sessions, not more wording. The stored baseline is the auto-mode window (2026-08-21
  → 24, saved from a `--days 4` run on 2026-08-24; that day's Fable calls are included, so its Fable
  row is a little noisier than the table above).
- **Probe** (`audit.py --probe`): six live commands with expected prompt/no-prompt outcomes — an
  in-scope `mkdir` (proves the fs `ask` rules are gone and the mode grant holds),
  `git -C <other>
  status` (the `global_option_prefixes` allow rule), a bare `git init` and a
  `git -C … push` to a throwaway bare repo (must prompt), and cleanup. Answers, once a human has
  watched a run: whether an explicit `ask` rule beats the in-scope grant (documented for the
  read-only set, extrapolated for the fs set), and whether `git -C x status` was already built-in
  read-only (in which case the allow rule is redundant, harmless). Record the observed outcomes here
  with the date.
- Prompt rate under `acceptEdits`: approved prompts leave no trace in transcripts, so the denial
  list understates friction — `scripts/prompts.py` (the **Prompts** procedure) estimates it by
  replaying the rules instead. Two of its approximations are worth a probe: whether a redirect to a
  `"$CLAUDE_JOB_DIR/tmp/x.log"` target (variable, not literal) prompts — the script assumes it does,
  and it is the exact form `~/AGENTS.md` recommends for capturing a gate's exit code — and whether
  `git -C <other> fetch` now matches `Bash(git -C * fetch:*)` without a prompt.
