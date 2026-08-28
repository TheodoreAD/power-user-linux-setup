---
status: idea
updated: 2026-08-23
---

> **Pointer (2026-08-23):** this plan's intake taxonomy is the upstream half of the admission rules
> stated in `contributing/global-agents-md.md` ("Admitting a new rule", from the now-retired
> leanness pass) — the taxonomy decides _where_ a candidate belongs; those criteria gate _whether_ a
> `~/AGENTS.md`-bound candidate gets in and in what shape.

## Context

`~/AGENTS.md`'s "Cross-session memory" section (rewritten 2026-08-22, prompted directly by the user
questioning why a just-saved memory wasn't user-wide) now states the policy explicitly: Claude
Code's auto-memory is a **staging area only** — durable, repo-specific knowledge belongs in that
repo's own `AGENTS.md`; durable, cross-repo/personal preference belongs in `~/AGENTS.md` itself. A
memory entry existing at all past the point its guidance is clear and general is drift, not a
feature.

That policy was previously undocumented (memory said "cross-repo preferences are fine to keep in
memory," full stop — no staging framing, no migrate-and-delete step) and, predictably, drifted badly
before anyone caught it: a 2026-08-22 session doing unrelated `repo-tasks` work found **~30 memory
entries** accumulated across `repo-tasks`, `power-user-linux-setup`, and `freshful-polite-mcp`'s
per-project memory folders — some duplicating content already in `~/AGENTS.md` verbatim
(`feedback_sudo_askpass.md`, `feedback_reuse_maintained_upstream.md`), one already fully covered by
an existing skill (`feedback_type_everything_for_agent_precedent.md` vs. the `python-conventions`
skill's Type hygiene section), one superseded by a skill built after it was written
(`feedback_research_via_cloned_repos.md` vs. `skills/research-library`), and the rest genuine
durable rules that had simply never been promoted. That entire backlog was migrated by hand in one
session (destinations: `~/AGENTS.md` for ~20 universal ones, `power-user-linux-setup/AGENTS.md` for
4 repo-specific ones, a **new** `polite-mcp-conventions` skill for 3 that apply family-wide but have
no repo whose `AGENTS.md` every `*-polite-mcp` session would actually load, and one repo's own
`AGENTS.md` for a single repo-specific one) — see that session's actual commits for the destination
mapping, not reconstructed here.

**Second pass, same session:** the two `project`-type memories left in `power-user-linux-setup`'s
folder (`project_screenshot_shortcuts.md`, `project_polite_mcp_repo_family.md`) weren't in scope for
the `feedback`-type sweep above — they're status/narrative logs, not behavioral rules, a different
_kind_ of thing than "instructions." Prompted by a direct follow-up question ("what can we do about
the remaining memories?"), both got resolved too, surfacing two more destination kinds (see taxonomy
below): `project_screenshot_shortcuts.md` was a pure duplicate of `docs/screen_capture.md` (every
fact — the 2 real bugs found, the Wayland fix, verified-working status — already lived there in more
detail) and was deleted with zero migration needed. `project_polite_mcp_repo_family.md` was ~90% a
staler duplicate of this repo's own scaffolding plan, since retired into
`contributing/repo-family-architecture.md` and `contributing/quality-tooling.md` (confirmed by grep,
not assumed — checked specifically for the memory's "still genuinely open" items and found them
already tracked there, more currently); the memory's own "family roster" portion was explicitly
self-distrusting (its text admits being caught incomplete twice, advises always re-listing the
directory rather than trusting a cached list) so preserving a static copy would have reproduced the
same staleness risk it already warned about. One genuinely unique, still-open nugget survived
neither of those (a shopping-site-MCP registry idea, semantically about
`product-research-pipeline`'s own future design, not this repo's) — migrated to
`product-research-pipeline/ROADMAP.md` instead of being dropped, after asking the user rather than
deciding unilaterally.

## Destination taxonomy (confirmed this session, not theoretical)

Every memory resolved this session landed in one of six places — this is the concrete input for
"Recommended direction"'s memory-backlog-review mechanism below, not six independently-invented
ideas:

1. **`~/AGENTS.md`** — genuinely universal, applies regardless of which repo a session is in.
2. **That repo's own `AGENTS.md`** — repo-specific technical/behavioral content.
3. **A new skill** — content that's specific to a _family_ of repos (not universal, not one repo),
   where no existing repo's `AGENTS.md` is actually loaded by a session working in a sibling repo.
4. **An existing skill's own content** — the memory is superseded by a skill built after it was
   written, but has one salvageable methodological nugget the skill doesn't already state.
5. **Drop entirely, no migration** — exact/near-exact duplicate of content already living in (1) or
   (2), or the memory's storage-mechanics half is superseded while its content half is fully covered
   elsewhere too.
6. **A different repo's own doc/plan/roadmap** — the memory's content is genuinely about a
   _different_ project than the one the memory happened to accumulate in (captured mid-conversation
   about that other project, but never written down there).

Deciding between (5)/(6) vs. genuine content worth keeping, for a `project`-type memory
specifically, used this procedure (worth stating explicitly, since it's the part a future automated
pass would need to replicate): grep the repo's own `plans/*.md`/`docs/*.md` for the memory's key
claims and compare dates — if a more current, more detailed doc/plan already covers it, that's (5);
check whether the memory's own text hints at its own unreliability (stated omissions, "caught
incomplete" admissions) — if so, lean toward (5) over preserving a stale snapshot; then check
specifically for any small, still-open, genuinely-not-covered-elsewhere nugget before deleting —
that's what makes it (6) instead of a clean (5).

A second real finding from that same sweep, orthogonal to the memory backlog itself: `~/AGENTS.md`
is a **deployed artifact** (`[packages.agents-md]`, assembled from the `config/agents-md/` fragments
— at the time, `[packages.claude-global-md]` generating from a single `config/global-AGENTS.md`),
but had drifted from its own source — both from a fix made directly to the deployed file earlier
that same session (repeating a mistake `feedback_deployed_vs_source_config.md` had already
documented once before) and from an _older_, unrelated drift already sitting there before this
session even started (a "prefer a dedicated harness tool" paragraph, live in the deployed file,
never ported back to source). Neither drift was caught by anything automated — only by a diff run by
hand, prompted by unrelated memory-migration work, not a dedicated check.

## Open questions

[NEEDS CLARIFICATION: should the memory→`AGENTS.md` migration be a periodic _sweep_ (run
occasionally, by hand or via a slash command, across every project's memory folder) or should it
happen _continuously_, e.g. as a step `session-harvest` already performs at end-of-session?
`session-harvest` today reviews the _current_ session's conversation for what's worth saving — it
doesn't audit already-saved memory from _past_ sessions for staleness/promotion-readiness. These may
be two distinct mechanisms (one at write-time, one as a backlog sweep) rather than one covering
both.]

[NEEDS CLARIFICATION: what should an automated (or semi-automated) version of "does this memory
duplicate/get-superseded-by existing `AGENTS.md`/skill content" actually check? The three concrete
misses found by hand this session were: (a) exact/near-exact duplication of an existing `AGENTS.md`
section, (b) coverage by an existing skill written _after_ the memory, (c) genuine cross-repo
applicability that was stated in the memory's own text ("applies across repos, not just X") but
never acted on. (a) and (c) look checkable relatively mechanically (semantic-similarity search
against existing `AGENTS.md` content; grep the memory body for "across repos"/"not just X"-style
phrasing); (b) requires knowing what every skill covers, which changes over time — possibly the same
mechanism `agent-skills`' `plans/2026-08-22-skill-trigger-quality-review.md` ends up building (an
LLM-judge pass against a corpus) could serve double duty here.]

[NEEDS CLARIFICATION: should the deployed-vs-source `~/AGENTS.md` drift get a dedicated guard (e.g.
a task that diffs the repo-side source against the live `~/AGENTS.md` and fails/warns on mismatch,
possibly wired into `inv verify.all` or a pre-push hook — **largely answered since: `deploy.status`
reports the drift and `verify.all` fails on it**) rather than relying on a human/agent remembering
to check? This is a narrower, more mechanical problem than the memory-sweep question above — a
straight diff, no LLM judgment needed — and may be worth building independently of whether the
broader memory-sweep idea goes anywhere.]

[NEEDS CLARIFICATION: is a fixed cadence (weekly? monthly? "whenever `session-harvest` fires and
happens to notice drift"?) the right trigger, or should this be explicitly user-invoked only (like
`session-harvest` itself, which the skill list already documents as "on-demand only — never installs
hooks or runs automatically")? Given this user's own stated aversion to auto-triggered mutation of
tracked artifacts (see `~/AGENTS.md`'s "Commit regenerated artifacts deliberately" section — the
same principle likely applies to auto-rewriting `AGENTS.md` content from memory without review), an
explicit, human-reviewed trigger seems like the safer default to start from.]

## Recommended direction

Two genuinely separate, small mechanisms, not one big one:

1. **Deployed-vs-source drift guard for `~/AGENTS.md`** (and any other `wrapper-script`-deployed
   dotfile in `setup.toml`) — mechanical, no LLM needed, cheap to build once the open question above
   about where it hooks in is resolved.
2. **Memory-backlog review** — likely a new skill or a `session-harvest` extension, explicitly
   user-invoked (not automatic), that: lists every `~/.claude/projects/*/memory/*.md` file across
   all projects, checks each against existing `AGENTS.md`/skill/plan/doc content for the drift
   patterns found this session (exact duplication, skill-supersession, stated-but-unactioned
   cross-repo scope, a `project`-type memory superseded by a more current doc/plan in its own repo,
   content that's actually about a different project than the one it accumulated in), and proposes
   one of the six "Destination taxonomy" outcomes above for human confirmation before writing
   anything — mirroring how this session's actual migration worked, just without a human having to
   notice the backlog existed first.

Not implementing either here — this plan exists to capture the idea and the concrete precedent (this
session's manual sweep) before it's lost, per explicit instruction.
