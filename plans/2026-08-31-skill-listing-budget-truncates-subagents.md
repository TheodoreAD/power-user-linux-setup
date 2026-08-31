---
status: in-progress
updated: 2026-08-31
source_repo: github.com-personal/agent-skills
source_session: 7e9e213d-6989-4534-a4c2-cf22bbab93ea.jsonl
source_moment: 2026-08-31T17:59:03Z
---

# The skill listing overflows its budget on 200k-window models, and nothing in real use is one

Filed from a session in `agent-skills`, which measured the mechanism while building the
`skill-fitness` skill. The mechanism, the arithmetic and the sources are in that repo's
`plans/2026-08-30-skill-fitness-analyzer.md`, section "The listing budget, measured rather than
paraphrased"; only what this repo has to decide is repeated here.

## Evidence

Backfilled 2026-09-01, because the first version of this plan paraphrased its own incident — the
failure `plans/2026-08-23-cross-repo-skill-feedback-capture.md` exists to prevent, reproduced by the
session that was reading it.

- **Transcript**:
  `~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-agent-skills/7e9e213d-6989-4534-a4c2-cf22bbab93ea.jsonl`
- **The moment**: `2026-08-31T17:59:03Z`, the probe run whose debug log carried
  `Skill listing over budget: 25 skills, 15486 chars > 8000 budget`. Search the transcript for that
  phrase; a second useful anchor is `--model claude-haiku-4-5-20251001 --debug-file`.
- **The repro**, runnable in any repo on this machine:

  ```shell
  claude -p 'reply with the single word ok' --model claude-haiku-4-5-20251001 \
    --debug-file /tmp/probe.log
  rg 'over budget' /tmp/probe.log
  ```

  Present behaviour: the warning fires. Wanted behaviour after the change below: no match.
- **The observed consequence**, from a real listing recorded in that same store: of 13 user skills,
  only `research-library`, `session-harvest` and `skill-authoring` kept their descriptions; the
  other ten were sent as a bare `- name`.
- **Not a user correction.** Nobody reported this; it was found by reading the CLI binary while
  building `skill-fitness`. Recorded so a triage session does not go looking for a complaint.

## The finding

Claude Code sends the model a listing of every skill's name and description. That listing has a
**character** budget of `context_window_tokens × 4 × skillListingBudgetFraction` (default 0.01), so
**8,000 characters on a 200k-window model**. When it overflows, user and project skills are demoted
to name-only — the description is dropped whole, not shortened — in ascending order of decayed
usage. Most of the harness's own entries are exempt — charged first, never demoted — though not all
of them, and which qualify is not derivable from a skill's origin: `security-review` was demoted in
a real listing while `code-review`, `run` and `init` kept their descriptions.

Measured on this machine, 2026-08-31, CLI 2.1.251:

| quantity                                       | chars      |
| ---------------------------------------------- | ---------- |
| whole listing, interactive (30 entries)        | **18,109** |
| whole listing, headless probe (25 entries)     | 15,486     |
| of which the 13 user skills                    | 9,550      |
| of which exempt, charged first, never demoted  | ~5,900     |
| budget on a 200k-window model                  | **8,000**  |
| budget on the models this user actually drives | ≥ 18,109   |

**On a 200k-window model, ten of the thirteen user skills are listed as a bare name.** Observed, not
simulated — a `--model claude-haiku-4-5-20251001` run on 2026-08-31 kept descriptions for only
`research-library`, `session-harvest` and `skill-authoring`. A skill listed as `- plan-docs` with no
description cannot be matched against a request, which is also what keeps it at the bottom of the
usage ranking that decided to demote it.

## Which sessions this actually hits, measured rather than assumed

Every model this user drives fits the listing. Probed one at a time against the real listing:
`claude-haiku-4-5-20251001` overflows (8,000 budget, so a 200k window); `claude-opus-5`,
`claude-sonnet-5` and `claude-fable-5` all produce no overflow warning, which puts each of their
windows above 387,150 tokens.

Across 443 transcripts, by the model holding the most assistant turns, cross-tabulated against what
kind of session it is:

| session kind       | model       | sessions | assistant messages |
| ------------------ | ----------- | -------- | ------------------ |
| real project       | `sonnet-5`  | 80       | 28,600             |
| real project       | `opus-5`    | 63       | 25,022             |
| real project       | `fable-5`   | 20       | 4,541              |
| **subagent**       | `sonnet-5`  | **71**   | 2,342              |
| **subagent**       | `haiku-4-5` | **13**   | 196                |
| headless, temp dir | `haiku-4-5` | 168      | 743                |
| headless, temp dir | `opus-5`    | 26       | 37                 |

**Subagents run on `sonnet-5`, which fits.** The `haiku-4-5` population is almost entirely headless
runs in temporary directories — this repo's own allowlist pipeline, and `agent-skills`' trigger
probes — averaging four assistant messages each.

And from the listings the harness actually sent, recorded verbatim in the transcript store:
**truncation has occurred in real work exactly twice**, both `agent-*` sessions on 2026-08-22 under
CLI 2.1.237. Nine further truncated listings are recorded and every one is a probe or a pipeline run
in a scratch directory — six from this repo's allowlist runs, three from the session that wrote this
plan.

[PITFALL: **an earlier version of this plan claimed the overflow hits "the whole subagent tier, 181
of 443 transcripts", and that was a sampling error.** The 181 was sessions whose dominant model is
`haiku-4-5`; its largest few were inspected, they were `agent-*` subagents doing real work, and the
set was described from them. The set is not like its largest members — 168 of the 181 are headless
probe traffic. The corrected reading is above, and it downgrades this plan from a live defect to a
latent one. Worth keeping as the worked example: the sample was self-selected by size, so the
outliers were the whole finding.]

[PITFALL: **the counter-evidence, and it is real.** Across 84 `agent-*` transcripts there are
**zero** `Skill` tool calls, so no subagent has ever been observed picking a skill, truncated
listing or not. That has at least three possible causes and this data cannot separate them: some
subagent types are defined without the `Skill` tool at all (`claude-code-guide` has only Bash, Read,
WebFetch, WebSearch), the built-in `Plan`/`Explore` agents deliberately skip `AGENTS.md` and may be
scoped away from skills too, and the truncation itself removes the descriptions selection needs.
This is exactly the zero-is-not-a-verdict shape the `skill-fitness` skill warns about.]

## What the settings file actually is, which changes where the fix goes

`~/.claude/settings.json` is **merged, not generated wholesale.** `inv ai.install-skills` syncs
individual keys declared in `setup.toml`'s `[packages.claude-code]` — `claude_default_mode`,
`claude_additional_directories`, `statusLine`, and the allowlist's `permissions.allow` — and leaves
everything else in the file alone. So a hand-added top-level key survives a deploy today; what it
does not do is reach the next machine, or explain itself to the next reader.

## Recommended direction

**This is insurance against a latent failure, not a repair.** Nothing in real use is truncated
today. What makes it worth doing anyway is that the cost is close to zero and the failure is silent:
a demoted skill produces no error, just a description the model never sees, and the corpus is one
model change or a few skills away from it. What makes it _not_ urgent is that the same measurement
now exists — `fitness.py budget` reports every truncation the harness has actually performed, so a
recurrence is detectable rather than invisible, whether or not this lands.

[DECISION: **declare `skillListingBudgetFraction = 0.03` in `setup.toml` and sync it, the same way
`claude_default_mode` is synced.** 0.03 gives 24,000 characters on a 200k model, clearing the
observed interactive listing of 18,109 with room to grow by a third. 0.02 (16,000) does not even
clear today's interactive listing, and would have looked sufficient against the headless probe's
15,486 — which is why the probe's number is documented as a floor.]

The cost is bounded and lands only where the overflow does. On a model whose listing already fits —
which is every model in real use — raising the cap changes nothing at all: the budget is a ceiling,
not an allocation. On a 200k-window session the listing grows from 8,000 to about 18,000 characters,
roughly **2,500 extra tokens per turn**, against sessions that currently average four.

Rejected, with reasons:

- **`disableBundledSkills`** (or `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS`) frees the whole 5,912 exempt
  characters, which alone would fix the overflow. It also removes every bundled skill, and the
  harness's own usage map shows `update-config`, `claude-api` and `claude-in-chrome` in real use.
  Trading working features for budget when the budget is a settable number is backwards.
- **`skillOverrides` per skill** — `name-only`, `user-invocable-only` (typable as `/name`, hidden
  from the model) or `off` — is the surgical lever and does work on bundled skills, whose exemption
  covers demotion by the budget but not an explicit override. It buys the same headroom at the cost
  of a curated list that has to be revisited every time the CLI ships or drops a bundled skill, and
  it silently removes capability from the main session to help the subagent tier. Worth keeping in
  mind for a specific skill the user never wants offered; not the answer to a budget question.
- **Trimming descriptions to fit** stays ruled out for the reason it always was: it deletes trigger
  vocabulary to satisfy a length check, which is the opposite of the goal.

## The work

1. Add the declaration to `[packages.claude-code]` in `setup.toml`, with a comment carrying the
   arithmetic and the 200k number, in the style of `claude_default_mode`'s.
2. Sync it in `tasks/ai.py` alongside `_apply_claude_default_mode` / the `statusLine` sync — a
   scalar top-level key, so the `statusLine` shape (ask before replacing a different explicit value)
   fits it better than the manifest/diff bookkeeping the permission rules need.
3. A unit test in `tests/unit/test_ai.py` beside the existing settings-sync cases.
4. `docs/claude-code.md` gets the mechanism in a paragraph — the budget is model-dependent, and that
   is the part nobody guesses.

## Verification

Not "the key is in the file". Re-run the probe that found it:

```shell
claude -p 'reply with the single word ok' --model claude-haiku-4-5-20251001 \
  --debug-file /tmp/probe.log
rg 'over budget' /tmp/probe.log     # before: 25 skills, 15486 chars > 8000 budget
                                    # after:  no match
```

The warning only exists on overflow and only reaches the debug file — a plain `--debug` prints
nothing — so its absence is the pass condition. Second check, free and retrospective:
`fitness.py budget` in `agent-skills` reads back every listing the harness has actually sent and
reports which entries were demoted, so a regression shows up without anyone probing for it.

[PITFALL: the probe runs headless, and a headless run lists fewer skills than an interactive one: 42
bundled skills were loaded and 25 entries listed, because several bundled skills are conditional on
a capability or a flag that a `-p` run does not have. So 15,486 is a floor for what an interactive
session sends, and the fraction should be chosen with that in mind — another reason 0.02 is too
tight.]

## Open questions

[NEEDS CLARIFICATION: is the subagent tier meant to see skills at all? Two of this machine's own
rules point the other way — `~/AGENTS.md` records that built-in `Plan`/`Explore` agents never load
`AGENTS.md`, and asks for the Bash rules to be pasted into their prompts instead. If skills are
deliberately not part of the subagent contract, the right fix is not budget at all; it is to stop
paying 8,000 characters per subagent turn for a listing nobody uses, which argues the opposite
direction and is worth an hour of measurement before the fraction is raised.]

[NEEDS CLARIFICATION: does the fraction interact with `/context`'s accounting or with autocompact
thresholds in any way worth knowing? The listing is an attachment, not a tool definition, and it is
re-sent per turn; 1,900 extra tokens per turn is small, but it was not measured against a long
session's compaction cadence.]
