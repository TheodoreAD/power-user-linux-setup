---
name: session-bash-audit
description: "Use when asked to audit, measure, or re-check how agent sessions are using the Bash tool — command chaining (&&, ;, |), cd into the session's own repo, head/tail truncation, sed -n/cat/heredoc instead of Read/Edit, git commit/push inside chains or behind git -C — or when deciding whether a permission prompt, an allowlist rule, a ~/AGENTS.md Bash rule, or the permission mode (acceptEdits vs auto) needs changing and wants evidence from real transcripts rather than a hunch. Runs a stdlib script over ~/.claude/projects/*.jsonl, prints per-model and per-session rates plus samples, and carries the dated research that explains why each pattern happens and where the fix belongs. Also the place to record a newly noticed Bash anti-pattern so the next audit measures it."
---

# Session Bash audit

Measures how Claude Code sessions on this machine actually use the Bash tool, against the rules in
`~/AGENTS.md`'s "Bash & the CLI allowlist" cluster, and turns the numbers into a decision about
_where_ a fix belongs. The first run (2026-08-24, 3,956 calls over four days) is written up in
[`references/research.md`](references/research.md) — read its "Root causes" and "Mode comparison"
sections before interpreting a new run; most of the reasoning transfers and doesn't need
re-deriving.

## Four procedures — the skill runs them, the user only reads results

Which one applies:

| Ask                                                        | Procedure                      |
| ---------------------------------------------------------- | ------------------------------ |
| "how are sessions using Bash", a new pattern to measure    | **Measure** (below)            |
| "did the change work", "re-check", a week after a change   | **Compare** against baseline   |
| "does the permission setup behave", after a mode/rule edit | **Probe** the live permissions |
| "why so many prompts", "what's still prompting"            | **Prompts** — replay the rules |

The first three use `scripts/audit.py`, the fourth `scripts/prompts.py`;
`S=~/.agents/skills/session-bash-audit` below.

**Measure**

```shell
python3 $S/scripts/audit.py --days 4 --samples 5
python3 $S/scripts/audit.py --days 7 --project repo-tasks --json "$CLAUDE_JOB_DIR/tmp/calls.json"
```

Read-only, stdlib only, ~10 s for a week of transcripts. `--samples 0` for just the tables. The
`--json` dump is the input for any ad-hoc follow-up question (`python3 -c` over it is fine here —
the data is a one-off snapshot, not repo code). Put the dump in the job/session scratch dir, not
`/tmp` directly.

**Compare** — the "did it work" check, no manual table-reading:

```shell
python3 $S/scripts/audit.py --days 7 --samples 0 --compare $S/references/baselines/2026-08-24-auto-mode.json
```

Prints each model's current rates next to the baseline as percentage-point deltas, with `OK`/`MISS`
per expectation (`EXPECTATIONS` in the script: chaining, head/tail, sed -n, cat, heredoc and
git-in-chain should be _down_; own-repo `cd` and `git -C` mutations at zero). Models with fewer than
50 calls in either run are shown as `?`, not judged. Report the verdict line and the misses to the
user; then route each miss with the table in "Decide where the fix goes". After a rule or mode
change, save a new baseline for the next comparison —
`--save-baseline $S/references/baselines/<date>-<what-changed>.json --note "<mode in force>"` — and
keep the old file; the deltas are the point.

**Probe** — live permission behaviour, which no transcript can show:

```shell
python3 $S/scripts/audit.py --probe
```

Prints six commands with the outcome each should have (prompt / no prompt) under `acceptEdits` with
this machine's rules. Run each as its **own Bash tool call** — running them from a script would
bypass the harness's permission check, which is the thing being tested — with `<scratch>` =
`$CLAUDE_JOB_DIR/tmp` or the session scratchpad. The agent cannot observe prompts: after the run,
list which steps were expected to prompt and ask the user whether that matched what they saw. A
mismatch is a real finding (a rule shadowing a mode grant, a prefix rule not matching) — record it
in `references/research.md` "Harness facts" with the date, and route the fix.

**Prompts** — which calls prompted, and why, when the user reports "too many confirmations":

```shell
python3 $S/scripts/prompts.py --days 2
python3 $S/scripts/prompts.py --since 2026-08-24T19:13:00Z --project repo-tasks
```

An approved prompt leaves no trace in a transcript, so this replays the harness's matching (split on
the separators, `ask` beats `allow`, built-in read-only set, `acceptEdits`' in-scope grant) against
the _current_ `~/.claude/settings.json` and prints the estimated prompting share per session and the
first prompting reason per call, ranked with samples. Run it before and after a rule change: the
"after" run is the check that the change actually removed the shape, not just a shape. Route each
reason with the table below — most land in `tools.toml` (`allow_overrides`/`ask_overrides`,
`global_option_prefixes`) or `setup.toml`'s `claude_permissions_allow`, not in prose. The 2026-08-25
run that introduced it is in `references/research.md` ("Prompt audit").

Reading the **Measure** output, in order:

1. **per model** — the baseline. Compare against the table in `references/research.md` ("Baseline
   2026-08-24"). Chaining and head/tail rates are the headline; `cd-own-repo`,
   `git-mutating-in-chain`, and `git-C-mutating` should be near zero after the 2026-08-24 changes.
2. **per session** — outliers, not averages. One session at 90% chaining with the same rules as a
   session at 15% is disposition or a task shape, not a wording problem; read a few of its samples
   before touching any rule.
3. **pattern totals** — each row carries its cost ("why"). A pattern with a high count whose cost is
   "prompt friction" only matters in a mode that prompts; check the mode in force during the window
   (`permissions.defaultMode` in `~/.claude/settings.json`, and whether sessions overrode it).
4. **re-runs after truncation** — the direct cost of `| head`/`| tail`: the same command issued
   again with a bigger limit. Each one is a wasted call plus whatever was decided on the truncated
   view in between.
5. **denied** — classifier denials (`Blocked by classifier`) mean auto mode was active for that
   session; "user doesn't want to proceed" is a human decline. Both are worth a look for what shape
   of command drew them.

## Decide where the fix goes

The audit exists to prevent the reflex of "add a sentence to `~/AGENTS.md`". Route by mechanism:

| Finding                                                                                            | Fix lives in                                                                                                                                                                       |
| -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A rule's stated _reason_ no longer holds (e.g. "prompt friction" under a mode that doesn't prompt) | Rewrite the reason in the owning `config/agents-md/` fragment, evidence in `contributing/global-agents-md.md`. Wording alone won't move a rate when the rationale is what's wrong. |
| A command shape prompts but is read-only and common                                                | `inv allowlist.review`/`tools.toml` (`global_option_prefixes` for `git -C`-style shapes) — see `contributing/cli-allowlist.md`                                                     |
| A verb is honestly `write` but can't lose code, and the instructions make it frequent              | `allow_overrides` on the tool in `tools.toml`, with `ask_overrides` for its code-losing flag shapes (`git add`/`reset --hard`, 2026-08-25)                                         |
| A read-only `inv` task prompts                                                                     | `claude_permissions_allow` on `[packages.repo-tasks]` in `setup.toml` — `inv` is deliberately unreviewed, so only listed tasks are allowed                                         |
| A command shape is gated by the mode more precisely than a prefix rule                             | `mode_covered` in `cli-allowlist/tools.toml`, never a hand edit of `settings.json`                                                                                                 |
| Writes to a harness scratch dir prompt                                                             | `claude_additional_directories` on `[packages.claude-code]` in `setup.toml`                                                                                                        |
| The harness itself instructs the opposite (auto mode's "prefer Bash" reminder)                     | The mode, not the wording: `claude_default_mode` in `setup.toml`. Don't write rules that fight a live system reminder                                                              |
| Only `Plan`/`Explore`/`claude-code-guide` subagents misbehave                                      | Their spawn prompt — they never load `AGENTS.md`. `~/AGENTS.md`'s subagent note has the paragraph to paste                                                                         |
| One model's disposition (rates differ by model under identical rules)                              | Nothing to write; note it in `references/research.md` and pick the model for the task                                                                                              |

Prefer teaching over enforcement: no PreToolUse nudge hooks (`~/AGENTS.md` "Proposing an enforcement
mechanism for agent behavior"; the rejected hook design is in `references/research.md`).

## Record what you learned

- A new pattern worth measuring → add a `PATTERNS` row in `scripts/audit.py` with an honest "why",
  run once, and add a dated paragraph to `references/research.md` with the count and what it means.
  Rows with no stated cost teach nothing; leave them out.
- A new baseline after a rule/mode change → append a dated row to the baseline table in
  `references/research.md`; don't overwrite the old one — the point is the delta.
- Harness facts (what auto mode does, what a mode auto-approves, rule precedence) → the "Harness
  facts" section of `references/research.md`, with the docs URL and date checked. Those change
  between Claude Code versions; a dated entry is the difference between evidence and folklore.
- A one-off finding that is really a repo bug or a design decision → that repo's `plans/` (see the
  `plan-docs` skill), linked from here.

This skill ships from `power-user-linux-setup`'s `skills/session-bash-audit/`; edit there and
`inv ai.install-skills --skill=session-bash-audit -y` to refresh the installed copy.
