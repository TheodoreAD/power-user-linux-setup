---
name: session-harvest
description: "Use when invoked explicitly as /session-harvest, or when the user asks what's worth saving before compacting/ending a session, wants a session reviewed for durable facts, or says something like 'harvest this session', 'anything to remember here', or 'is it safe to compact'. Reviews the conversation against Claude Code's built-in auto-memory taxonomy (user/feedback/project/reference), but routes plan-specific content to plans/*.md instead (per the plan-docs skill), repo-specific durable knowledge to that repo's AGENTS.md/docs/contributing, and cross-repo/personal preference to ~/AGENTS.md, so memory doesn't end up duplicating what those already own or silently siloing a preference in one project's memory folder. Ends with a safe-to-compact report. On-demand only — never installs hooks or runs automatically."
---

# Session harvest

Reviews a conversation for what's worth persisting before it's compacted or ends, and makes sure
each candidate lands in the _right_ place — not just memory by default because memory is the easiest
tool at hand. Primary invocation is explicit (`/session-harvest`); the description above also
matches natural-language phrasing, but explicit invocation is the one to rely on — description
matching for something this consequential (it writes files) has been reported unreliable by prior
art (see `references/rationale.md`).

On-demand only. Installing hooks, wiring `settings.json`, or running on any schedule is explicitly
out of scope — that's a different, heavier tool (see `references/rationale.md` for the prior art
considered and rejected).

## Procedure

1. **Significance test first.** Re-read the conversation for candidates. For each one, before
   anything else: _if this were lost, would a future session go wrong?_ Anything that fails this is
   dropped (optionally noted in the report as "considered, not worth persisting"), not proposed.
   This is the actual noise filter — apply it upstream of routing, not after.

2. **Routing filters**, for what survives the significance test:
   - **Plan-specific content → `plans/*.md`, never memory.** If the session touched or produced work
     that the `plan-docs` skill would track — a design, an idea, in-progress implementation — it
     does not get a memory entry. Check whether the relevant `plans/YYYY-MM-DD-*.md` already
     captures it; if the repo uses `plan-docs` and it doesn't, say so and offer to create/update the
     plan file instead of saving to memory. Memory has no retirement mechanism, so a plan snapshot
     parked there would just rot silently — `plans/` already owns that lifecycle. **If a plan file
     already exists but its `status` is now stale** (e.g. `planned`/`in-progress` when the session
     just finished landing and verifying the work), invoke the `plan-docs` skill directly to apply
     its own status-bump/retirement procedure — don't improvise an `AskUserQuestion` about whether
     to retire it. Confirmed as friction 2026-08-23: asked the user a retirement judgment call that
     `plan-docs`'s own "Retiring a plan" section already answers (default: preserve unless the
     rationale is already covered elsewhere in the repo); the user's correction was "why isn't the
     plan docs skill kicking in?"
   - **Repo-specific durable knowledge → `AGENTS.md`/`docs/`/`contributing/`, never memory.** Use
     this split, not a flat "put it in AGENTS.md":
     - `AGENTS.md` (or equivalent instructions file) — only operating instructions an agent needs on
       _every_ task in that repo (commands, conventions, gotchas that change behavior). Keep it
       minimal: it's loaded into every session unconditionally, so this is the actual
       bloat-avoidance lever, not a place to write everything learned.
     - `docs/*.md` — usage-facing reference material, linked from `AGENTS.md`, read on demand.
     - `contributing/*.md` (or a skill's own `references/*.md`, if the knowledge is about a skill
       itself rather than the repo) — design rationale, prior art, implementation gotchas, also on
       demand.
   - **Cross-repo/personal preference (not tied to one project) → `~/AGENTS.md`, never memory
     either.** Same logic as the repo-specific split above, one level up — version-controlled via
     its real source (a fragment under `power-user-linux-setup/config/agents-md/` — that directory's
     `README.md` says which one owns what; never edit the deployed `~/AGENTS.md` directly, it's
     silently overwritten by the next `inv tools.install`). **Read the canonical source before
     drafting an addition — the deployed copy loaded into a session's context can be structurally
     stale against it.** Confirmed 2026-08-24: a session held a ~20 flat-section `~/AGENTS.md` while
     the source had been restructured to 7 clustered ones, so an addition drafted against the
     section names in context would have targeted headings that no longer existed.
     `grep -n '^## ' <source>` first. Loaded into every session regardless of repo, so it's the
     actual bloat-avoidance-and-reviewability lever for content that isn't tied to one project, the
     same way a repo's own `AGENTS.md` is for that repo. Confirmed as a real gap 2026-08-22: a
     session found ~30 `feedback`-type memories accumulated across multiple projects' memory folders
     — each project's memory is invisible to every other project's sessions, so a genuinely
     cross-repo preference saved there never actually reaches a session in a different repo. Most
     had simply never been promoted because nothing routed them anywhere else. **A candidate that's
     a _variant_ of a rule already in `~/AGENTS.md` extends that rule's existing section — it
     doesn't get a new one.** "Already covered → skip" (below) is for an exact duplicate; this is
     the near-miss case, where the principle is written down but this particular shape of it isn't.
     Default to appending a short paragraph to the section that already frames it, because that file
     is loaded into every session in every repo, so a new heading costs context everywhere and a
     reader who sees three instances under one principle generalizes better than one holding three
     unrelated rules. Reach for a new section only when the trigger and the detection signal are
     both genuinely different from anything already there. Resolved 2026-08-23: "don't characterize
     a multi-file diff from one sampled file" was folded into "Verify what actually happened, not
     what output looks like" — which already covered clean-stdout-vs-exit-code and
     test-suite-vs-throwaway-script, both the same "the convenient surface signal isn't the real
     signal" shape.
   - **A skill that already owns the topic beats a new always-loaded rule.** `~/AGENTS.md` is not
     the default home for every cross-repo finding: `contributing/global-agents-md.md`'s "Admitting
     a new rule" is the gate, and its tier test is the deciding question — a rule whose miss is
     _silent and expensive_ belongs in the always-loaded file, while one with a sharp trigger whose
     miss is _cheap and recoverable_ belongs in a skill. Check the file's current size against its
     own reference points (`grep -c '^### '`, `wc -l`; ≤15 rules / ≤200 lines) before proposing, and
     say the numbers out loud when asking — admission is a real cost once it is over them, and the
     user should decide with that in view. Resolved 2026-08-25: `pgrep -f` matching the harness's
     own `zsh -c … eval` wrapper (a false positive that reads as a real process) went to
     `session-bash-audit` — which already invites newly noticed Bash anti-patterns and can _measure_
     the rate — rather than becoming a 34th rule in a file already at 33 rules / 390 lines. A
     finding that a topic-owning skill can act on is usually better there than restated globally.
   - **Destination mid-restructure → the plan reshaping it, not the file.** When a candidate's
     correct home is currently the subject of an open `plans/*.md` that is reshaping it — especially
     one that defines its own criteria for what may be added — record the candidate _in that plan_,
     as a `[NEEDS CLARIFICATION: ...]` item stating its trigger, rather than appending to the file.
     Appending bypasses the criteria that plan exists to enforce, risks the addition being
     restructured away unread, and conflicts with whatever session is doing the restructuring.
     Applies to any destination with an open plan owning its shape, not just `~/AGENTS.md`. Resolved
     2026-08-23: two cross-repo rules routed to `~/AGENTS.md` while the (since retired) leanness
     pass was actively cutting it from 30 sections and adding admission rules of its own — now
     permanent in `contributing/global-agents-md.md` ("Admitting a new rule"); both candidates were
     parked in that plan instead of appended, and were decided at its close.
   - **Already covered → skip.** If an existing memory file or doc already says this, don't write a
     duplicate — check first.
   - **Meta-conventions about how to build things in this ecosystem (e.g. "skills should do X by
     default") → the relevant existing skill's own docs, not a feedback memory** — even though on
     the surface "how to approach work" sounds like the `feedback` bucket. Resolved via
     `AskUserQuestion` during this skill's own design: a preference about how _new skills_ should be
     authored belongs in `mcp-skill-shipping` (durable, version-controlled, visible to every
     contributor/tool), not this harness's private memory store. Use that as the default for similar
     cases rather than re-asking each time.

3. **Survivors** get saved following the harness's own existing memory-save procedure exactly as
   specified in its system prompt (frontmatter format, `MEMORY.md` index entry, `[[links]]`) — not
   reimplemented here. **Expect this to be rare.** Confirmed directly by the user 2026-08-23: memory
   is not a durable store at all anymore — a prior session's restructuring moved everything durable
   that used to live there into `AGENTS.md`/`~/AGENTS.md`, and step 2's filters exist precisely so
   that keeps being true going forward. What's actually left to save here should be genuinely
   temporary — expires on its own, isn't meant to persist indefinitely (a deadline, a "don't touch X
   until Y happens" note) — not a preference, convention, or fact that would still be true in a
   month. If a candidate feels durable but doesn't cleanly fit any filter in step 2, that's a signal
   to add a new routing filter there (step 6's self-update), not to default to memory.

4. **Loose-ends pass**, separate from the memory scan: is there in-progress state in _this_
   conversation that isn't memory-worthy (failed step 1) and isn't covered by a plan file either,
   that compaction would still lose track of? Surface it explicitly — recommend a `plans/*.md` entry
   if it's real design/idea work worth resuming, or say plainly that it's fine to let go if it's
   genuinely ephemeral task state.

5. **Harvest report**, zoned and capped:
   - Judgment calls that genuinely need the user's input, first, capped to a handful so review stays
     fast even after a long session.
   - Routine, unambiguous routings underneath as one-liners (saved to memory / routed to plan /
     routed to docs / dropped as insignificant) — informational, not asking for confirmation.
   - Ends with a one-line verdict: "safe to compact" or "not yet — needs a decision on X."

6. **On friction, ask — then self-update the skill, not just this session.** Two triggers:
   - A candidate doesn't clearly fit any routing filter in step 2 (e.g. arguably both plan-specific
     _and_ a durable cross-repo preference), or the significance test itself is a genuine toss-up.
   - The user corrects a routing decision this skill just made.

   In either case, use `AskUserQuestion` to resolve it for _this_ item — never silently pick a side
   on a real ambiguity. Then fold the resolution back into this skill's source (see below) so the
   same friction doesn't recur next time. Resolving it for one session only defeats the point of a
   shared convention skill.

Everything this harvest writes into a repo — a `plans/*.md` entry, an `AGENTS.md` addition, a
`docs/`/`contributing/` page, a skill's own source — goes through that repo's quality gate
(`inv quality.precommit`, or the repo's equivalent) before committing, same as code. Markdown is not
exempt: dprint reformats prose line-wrapping, and doc-only commits that skipped the gate were the
one recurring CI-failure cause across these repos (confirmed 2026-08-23).

## Self-update mechanics

Resolving friction (step 6) means editing the skill's _source_, not whatever copy is in front of the
current session:

- The running copy — `~/.agents/skills/session-harvest/` (or a project-local
  `.agents/skills/session-harvest/`) — is a plain file copy dropped there by
  `inv ai.install-skills`. Its `.pulse-source` marker means hand-editing it is silently clobbered on
  the next `inv ai.install-skills` run and never reaches any other project anyway. Never edit it
  directly.
- Find the canonical source: the repo whose `setup.toml` declares `[packages.session-harvest]` —
  `power-user-linux-setup`, normally at `~/projects/github.com-personal/power-user-linux-setup` on
  this machine. If that's not obviously reachable from the current session (invoked from an
  unrelated project), locate it (e.g. `fd -td power-user-linux-setup ~/projects -d 4`) or ask the
  user for its path — don't guess or silently skip the update.
- Edit `skills/session-harvest/SKILL.md` there: a small, additive change — a new bullet under the
  relevant routing filter, or a note under "On friction, ask" if the friction was about the
  escalation process itself. Not a rewrite. Rationale for _why_ a resolution was made a particular
  way goes in `references/rationale.md` instead, matching the split already used for the rest of
  this skill.
- Re-run `inv ai.install-skills` from that repo so the update actually reaches every project. Then
  tell the user what changed and that it's a durable convention update worth a commit — don't commit
  it unasked, same standing rule as everything else in that repo.

## Full rationale

[`references/rationale.md`](references/rationale.md) has the prior-art survey (why this isn't a
`PreCompact` hook, what was borrowed from `learning-loop-skill` and what was deliberately left out,
why plan-specific content is excluded from memory even though it's tempting mid-session) and the
reasoning behind the self-update mechanism.
