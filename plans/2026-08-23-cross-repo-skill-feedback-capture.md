---
status: idea
updated: 2026-08-23
---

## Context

This repo owns the `config/agents-md/` fragments (assembled into `~/AGENTS.md`, and symlinked from
each installed agent's own instruction path) and the machinery that installs everything else agents
read. Skills used to be here too; they are authored in
[`agent-skills`](https://github.com/TheodoreAD/agent-skills) now, and PULSE only installs them. So
the capture target is no longer one repo: an `~/AGENTS.md` problem lands here, a skill problem lands
there. That is a change to §3 and §5 below, not to the premise — see "Where a capture lands, after
the skills move" at the end.

But the _need_ for a change almost never surfaces here. It surfaces mid-task in `repo-tasks`,
`scaffoldapy`, an `*-polite-mcp` repo: a skill fails to trigger on the request it exists for, a
`~/AGENTS.md` rule turns out to be wrong or missing, a correction the user just gave should have
been permanent. The evidence — the actual prompt, what the agent did, the correction verbatim, the
file that tripped it — lives in _that_ session, in _that_ repo. By the time a session in this repo
picks the topic up, that evidence is gone, and what's left is a second-hand paraphrase.

Two existing mechanisms touch this and neither closes it:

- The `session-harvest` skill's "Self-update mechanics" already says: from wherever you are, locate
  the repo that owns the skill, edit its `SKILL.md`, re-install. That's the right answer for a
  one-line additive fix and the wrong one for anything needing design, a `setup.toml` change, new
  reference files, or the quality gate — and it drags a foreign session into a second repo, which
  `~/AGENTS.md` "Testing a different repo's code in a multi-working-directory session" explicitly
  warns against. Since the move it also costs a push before the change is visible, because the
  installer clones from the remote — the `skill-authoring` skill now owns that sequence.
- The `plan-docs` skill owns plan lifecycle and already has `depends_on:` for _outbound_ cross-repo
  dependency. It has nothing for _inbound_ provenance — a plan that arrived here from elsewhere and
  whose evidence lives elsewhere.

Symptom already on record: `agent-skills`' `plans/2026-08-22-skill-trigger-quality-review.md` opens
with "Surfaced 2026-08-22 while working in `repo-tasks`" and then re-narrates the failure in prose,
because there was no mechanism to point at the real turns.

### Prior art (web pass, 2026-08-23)

Checked before designing, per `~/AGENTS.md` "Reuse maintained upstream work". Nobody has published
this loop; the pieces exist separately.

- [AgentPatterns, "Architecting a Central Repo for Shared Agent Standards"](https://agentpatterns.ai/workflows/central-repo-shared-agent-standards/)
  — the closest match to this repo's architecture, and explicitly **one-directional**: central →
  downstream via symlink/copy/package, CI checks downstream _compliance_. Fetched and read: it has
  no upstream-capture story at all. "The document's scope stops at distribution _to_ downstream
  projects, not collection _from_ them."
- [MSicc, "Skills Central"](https://msicc.net/2026-03-19-skills-central-a-pragmatic-setup-for-reusable-ai-skills/)
  — same shape, same gap; has a `skill-source.md` provenance file per installed skill (this repo's
  `.pulse-source` marker is the same idea) but documents only _pulling_ updates, never pushing
  findings back.
- Self-improving-agent / learning-loop family
  ([learning-loop-skill](https://github.com/melodykoh/learning-loop-skill), already surveyed in the
  `session-harvest` skill's `references/rationale.md`;
  [self-improving-agent](https://borghei.github.io/Claude-Skills/skills/engineering/self-improving-agent.html),
  [MindStudio writeups](https://www.mindstudio.ai/blog/how-to-build-learnings-loop-claude-code-skills))
  — contribute the _capture at the moment of friction_ idea and a `.learnings/` append target. All
  of them capture **into the current repo**, which is precisely the failure mode here: a learning
  about a user-wide skill filed in `olx-polite-mcp/.learnings/` is invisible everywhere else. Same
  siloing `~/AGENTS.md` "Cross-session memory" already rejects for Claude Code's own memory store.
- [Dachary Carey, "Agent skill mega repo woes"](https://dacharycarey.com/2026/03/13/agent-skill-mega-repo-woes/)
  — relevant as a constraint, not a solution: skill count is a context tax and overlapping
  descriptions degrade trigger selection. Argues against "add a new skill for this".
- Session transcripts as an evidence store —
  [claude-replay](https://news.ycombinator.com/item?id=47276604),
  [transcript format writeups](https://claude-dev.tools/docs/jsonl-format),
  [PromptConduit](https://promptconduit.dev/blog/claude-code-transcripts-location). Established
  practice for retro-analysis of one's own sessions; nobody uses it as a **cross-repo evidence
  pointer**, which is the one genuinely new piece below.

### Verified on this machine (2026-08-23)

- `CLAUDE_CODE_SESSION_ID` is exported into the Bash tool's environment
  (`f93cd518-6341-48c6-94aa-b8b134e47f4d` for this session), so a session can name its own
  transcript without guessing.
- Transcript path is deterministic: `~/.claude/projects/<cwd-slug>/<session-id>.jsonl`, where
  `<cwd-slug>` is the absolute cwd with `/` and `.` replaced by `-`. Confirmed by grepping this
  conversation's own text and landing on exactly that file.
- `~/.claude/settings.json` sets `"cleanupPeriodDays": 365`, so a cited transcript survives long
  enough to be worth citing (the default is 30 — this is a real dependency worth stating).
- A foreign transcript is readable and extractable from here today. This recovers real user turns
  with timestamps out of a 1.5 MB `repo-tasks` transcript:
  ```shell
  jq -r 'select(.type=="user") | (.timestamp // "") + " | " + ((.message.content // "") | if type=="array" then (map(select(.type=="text").text) | join(" ")) else . end)' <transcript>.jsonl
  ```
- `gh` is installed and issues are enabled on `TheodoreAD/power-user-linux-setup` (currently zero
  issues, open or closed).
- `pulse-proxy-start` (`[packages.pulse-proxy-start]`, `method = "wrapper-script"`) is existing
  precedent for a `pulse-*` helper deployed to `~/.local/bin` from this repo.

## Open questions

- [NEEDS CLARIFICATION: is `CLAUDE_CODE_SESSION_ID` set in every session type, or only in this
  background-job session? Needs a check from a plain interactive session and from a subagent before
  the helper can depend on it. Fallback if not: newest `*.jsonl` in the cwd-slug directory, or
  `rg -l "<a distinctive phrase from the conversation>" ~/.claude/projects/`.]
- [NEEDS CLARIFICATION: does the transcript pointer need a turn-range hint (timestamp of the failing
  exchange), or is a keyword good enough for the triage session to find the right part of a multi-MB
  transcript? Lean: record an ISO timestamp _and_ a distinctive quoted phrase — cheap, and either
  one alone can miss.]

Resolved 2026-08-23 (user): the capture prompts to commit **and** push immediately after writing the
file, cancellable — see "Commit prompt, immediately" below.

Deferred to its own plan, not an open question here: whether GitHub issues become the primary
capture channel rather than the unreachable-repo fallback. That is likely the cleaner shape long
term, but it needs a real lifecycle design connecting an issue to the `plan-docs` convention (who
opens, who triages, when an issue becomes a plan file, who closes, what keeps the two from drifting)
— out of scope here. See `plans/2026-08-23-github-issues-plan-lifecycle.md`.

## Recommended direction

**One rule, three lanes, one new artifact.** The load-bearing idea: _capture is not fixing, and the
capture carries a pointer to the real evidence rather than a paraphrase of it._

### 1. The routing rule goes in `~/AGENTS.md`, not in a skill description

The rule has to fire in a repo that has nothing to do with this one, on a session that may never
load any skill. `agent-skills`' `plans/2026-08-22-skill-trigger-quality-review.md` already
establishes that skill `description` matching is the weak link in this family — so the trigger
cannot be a skill description. A short new section in the `config/agents-md/` fragments (always
loaded, everywhere) states: skills and `~/AGENTS.md` are owned by `power-user-linux-setup`; when you
hit a problem with one from another repo, don't fix it in place — follow the capture procedure,
invoked **by name** so it never depends on description matching.

### 2. Three lanes, decided at the moment of friction

- **Fix-in-place** — a single additive edit to an existing `SKILL.md` section or one
  `global-AGENTS.md` bullet, no design decisions, no new files, no `setup.toml` change. This is what
  `session-harvest`'s "Self-update mechanics" already describes; keep it, but bound it explicitly so
  it stops being the default for things it can't carry.
- **Capture** — everything else. Write a plan file into this repo's `plans/`, stop there, tell the
  user. Do not design, do not edit any skill, do not run `inv` from the foreign session.
- **Fallback** — source repo can't reach this repo's working tree at all:
  `gh issue create -R
  TheodoreAD/power-user-linux-setup`, same body template, converted to a plan
  file at triage. Fallback-only _for now_; promoting issues to the primary channel is
  `plans/2026-08-23-github-issues-plan-lifecycle.md`.

### 3. The capture artifact: a normal plan file with provenance frontmatter

Lands as `plans/YYYY-MM-DD-topic.md` here, `status: idea`, plus new optional fields — the inbound
mirror of `depends_on`:

```yaml
---
status: idea
updated: 2026-08-23
source_repo: repo-tasks
source_session: 8f3c…-…jsonl # ~/.claude/projects/<slug>/<id>.jsonl
source_moment: 2026-08-22T16:50:15Z # plus a quoted phrase in the body
---
```

Body adds one section above the usual ones: `## Evidence` — the transcript path, the timestamp, a
verbatim quote of the user's correction, the exact repro (what was asked, what the agent did, what
it should have done). The point of the frontmatter is that a triage session in this repo can
**re-read the original turns** with the `jq` recipe above instead of trusting the summary. That is
the direct answer to "context from the other repo is key to debugging."

`plan-docs`' `SKILL.md` gains a short "Plans that arrive from another repo" section defining these
fields, and the rule that a plan carrying `source_repo` isn't done until its `## Verification` names
the original repro in that repo — the fix has to be checked against the case that produced it, after
the skill is re-installed.

### 4. Commit prompt, immediately

Decided 2026-08-23. The capture does not stop at "file written, tell the user" — writing the file
and offering to land it are one continuous step:

1. Write `plans/YYYY-MM-DD-topic.md` into this repo.
2. **Immediately** prompt to commit and push it. Not batched to the end of the session, not left for
   the next time someone opens this repo.
3. The user can decline at that exact moment (mid-task in another repo, bad timing) — declining is
   normal and leaves the file in place; it is not a failure path.

The reason the prompt has to be immediate is pollution of a working tree this session doesn't own.
An uncommitted plan file sitting in `power-user-linux-setup` is exactly the "unexplained state"
`~/AGENTS.md` "Concurrent sessions" warns about — another live session sees an untracked file it
didn't create and has to decide whether it's a leftover, a fork's stray output, or real work. The
shorter that window, the less it costs; a capture that lands within seconds of being written never
creates the ambiguity at all.

Consequences for the design:

- The commit is one file, one concern, `plans:`-scoped subject — it never waits to be bundled with
  anything, and it never picks up unrelated churn already in that tree (`git add` the one path, not
  `-A`).
- Push, not just commit — a local-only commit still isn't visible to a session on another machine,
  and the whole point is that the report leaves the repo it was found in.
- `pulse-capture` prints the exact `git -C <repo> add/commit/push` sequence so the offer is a single
  copyable action rather than three prompts, and so the foreign session never has to construct
  repo-relative paths itself.
- Nothing else is committed on the way through. Formatting churn the gate happens to surface in that
  tree is the other session's business, not the capture's (`~/AGENTS.md` "Keep incidental
  lint/formatting fixes a quality gate surfaces" applies to the session that _ran_ the gate).

### 5. `pulse-capture` — the one new artifact

A `method = "wrapper-script"` package (`config/pulse-capture.sh` → `~/.local/bin/pulse-capture`,
same shape as `pulse-proxy-start`). Runnable from any cwd, so it dodges every trap in `~/AGENTS.md`
"Testing a different repo's code in a multi-working-directory session" — no `cd`, no invoke task
discovery, no venv resolution, and it's a single stable command prefix for the allowlist.

It resolves the transcript path from `CLAUDE_CODE_SESSION_ID` + cwd slug, locates
`power-user-linux-setup`, writes the skeleton plan file with frontmatter filled in, and prints the
path plus the ready-made commit command. The agent then fills in `## Evidence` and `## Context` with
Edit. Rationale for a script rather than "the agent writes the file": slug computation, session-id
resolution and repo location are exactly the fiddly, silently-wrong-able steps an agent should not
be re-deriving in a foreign repo — and `~/AGENTS.md` "Verify what actually happened" applies.

### 6. Deliberately not doing

- **No new skill.** Trigger reliability argues for `~/AGENTS.md`; context cost and description
  overlap (mega-repo woes, above) argue against an eighth skill. The procedure extends
  `session-harvest` (which already owns "route durable knowledge to its right home" and already has
  the self-update section this bounds) and `plan-docs` (which already owns plan shape).
- **No `.learnings/` file in the consumer repo.** That's the siloing this design exists to avoid.
- **No hook, no automation.** Same call `session-harvest` already made and for the same reason.
- **No second backlog — in this plan.** GitHub issues stay a fallback for the unreachable-repo case
  here, deliberately, so this plan can land without first settling issue lifecycle. Whether they
  should become the primary channel instead is a real question with a plausible "yes", tracked
  separately in `plans/2026-08-23-github-issues-plan-lifecycle.md` — not rejected here.

### Pilot 1, by hand (2026-08-23) — sequencing step 3, run before it was planned

A `repo-tasks` session hit exactly the friction this plan describes (`~/AGENTS.md`'s `cd`/chaining
guidance turned out to be wrong) and captured it by hand as
`plans/2026-08-23-cross-directory-command-execution.md` (since landed and retired), without knowing
this plan existed. Useful as unprompted evidence rather than a rehearsal of the design.

**What matched:** lane 2 was the right call and was chosen unprompted — capture, don't fix in place,
because the leanness pass owns those paragraphs. §4's immediate-commit also happened naturally: the
file was written and committed in the same breath, no untracked-file window.

**What the pilot did not do**, i.e. what remains untested:

- No `source_repo`/`source_session`/`source_moment` frontmatter, and no `## Evidence` section. The
  capture paraphrased the incident instead of pointing at the transcript — the exact failure mode
  this plan's §3 exists to prevent, reproduced by an agent that had every reason to do better.
  Strong argument that the fields must be _prompted for by a tool_, not left to an agent's judgment.
- Committed but **not pushed**, contrary to §4's "push, not just commit."

[PITFALL: **§2's lane boundary did not survive contact.** Lane 1 (fix-in-place) is bounded to "a
single additive edit… no design decisions, no new files, no `setup.toml` change." This session did
far more from a foreign cwd — a multi-section rewrite of `skills/plan-docs/SKILL.md` plus its
`references/`, and a new `--skill` option on `ai.install-skills` with 14 tests — and it went
cleanly: 215 tests green, `basedpyright` 0 errors, committed without incident. The bound wasn't
wrong about risk so much as about _authority_: the user explicitly said "you should be able to do
your work there" each time. So the real dividing line is whether the user has authorized
foreign-repo work in this session, not how large the edit is. Worth reconciling before the lane
bound is written into `session-harvest`, or that rule will be routinely and correctly ignored.]

**Also confirmed against §5's rationale:** the traps `pulse-capture` is designed to dodge are real
but narrower than assumed. `git -C`, `dprint --config`, `ruff --config`, `basedpyright --project`
and an absolute-path `pytest` all worked fine from a foreign cwd with no `cd`; only `inv` genuinely
needed one, because task discovery walks up from cwd. That strengthens the "runnable from any cwd"
requirement for the script and weakens the general "don't touch another repo" framing it cites. See
`contributing/global-agents-md.md` ("Running a command against a different repo than the session's
project") for the full exercised list.

### Suggested sequencing

1. Resolve the `CLAUDE_CODE_SESSION_ID` question (cheap: one interactive session, one subagent).
2. `config/global-AGENTS.md` section + `plan-docs` provenance fields + `session-harvest` lane bound
   — docs only, no code. Usable immediately by hand.
3. Pilot it on the next real cross-repo friction, by hand, before writing `pulse-capture`
   (`~/AGENTS.md` "Pilot before generalizing").
4. Then `config/pulse-capture.sh` + `[packages.pulse-capture]` + a test, once the by-hand shape has
   survived a real use.

## Where a capture lands, after the skills move (2026-08-28)

Written when skills lived in this repo, so §2's "write a plan file into this repo's `plans/`" had
exactly one destination. It now has two, and the split is clean because the two halves already
answer to different repos:

| what the friction is about                                  | plan lands in          |
| ----------------------------------------------------------- | ---------------------- |
| a skill — wrong trigger, wrong content, missing case        | `agent-skills/plans/`  |
| an `~/AGENTS.md` rule, or any PULSE-deployed mechanism      | this repo's `plans/`   |
| genuinely both (a rule that should have been a skill, or …) | wherever the fix lands |

Consequences for the design below, none of which change its shape:

- **§3's provenance fields (`source_repo`/`source_session`/`source_moment`, the `## Evidence`
  section) are a `plan-docs` change, so they are authored in `agent-skills` now**, not in this
  repo's `skills/plan-docs/SKILL.md` as §3 says. Same for §2's lane bound on `session-harvest`.
- **§1's routing rule stays here** — it goes in the `config/agents-md/` fragments, which this repo
  assembles, and it now has to name _which_ repo a capture goes to rather than "this one".
- **§5's `pulse-capture` stays here too**, as a `wrapper-script` package. But it grows one argument:
  it can no longer assume the destination repo, so the target is a parameter (or inferred from what
  the friction was about) rather than hardcoded to `power-user-linux-setup`.
- The `.pulse-source` marker cited under Prior art no longer exists for these skills — the `skills`
  CLI's `skills-lock.json` records provenance instead, per package.

[NEEDS CLARIFICATION: does the fallback lane (`gh issue create`) also need a repo choice now, or do
all inbound reports go to one issue tracker and get routed at triage? One tracker is simpler for the
reporter and matches "issues are an inbox, not a backlog" from
`plans/2026-08-23-github-issues-plan-lifecycle.md`; two trackers put each report next to the code
that will fix it. Decide alongside that plan, not before it.]
