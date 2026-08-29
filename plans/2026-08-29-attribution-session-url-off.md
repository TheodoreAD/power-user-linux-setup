---
status: idea
updated: 2026-08-29
repo: git@github.com:TheodoreAD/power-user-linux-setup.git
---

## Context

Raised from a session in `agent-skills` on 2026-08-29, not from work on this repo. Filed here in the
store rather than committed into `power-user-linux-setup/plans/` deliberately: writing into another
repo's working tree is the cross-repo-commit problem this whole filing convention is trying to stop.
Pick it up whenever a session is next working in that repo.

Claude Code appends a `Claude-Session: https://claude.ai/code/session_<id>` trailer to commits.
Measured 2026-08-29 across this machine's personal repos:

| repo                     | commits carrying the trailer | visibility |
| ------------------------ | ---------------------------: | ---------- |
| `agent-skills`           |                           40 | public     |
| `repo-tasks`             |                           19 | public     |
| `power-user-linux-setup` |                           15 | public     |
| `scaffoldapy`            |                            1 | public     |
| `ingesta`                |                           27 | private    |

75 in public history. Four distinct session ids in `agent-skills` alone.

## What the research says (2026-08-29)

- **The setting is `attribution.sessionUrl = false`**, added in Claude Code v2.1.183, alongside
  `attribution.commit` / `attribution.pr` (free-text attribution, empty string hides it) and the
  older `includeCoAuthoredBy`. Normal settings precedence: `~/.claude/settings.json` for the user,
  `.claude/settings.json` per project, enterprise managed on top.
- **Access is normally owner-only** — a stranger with the URL cannot open the transcript. But
  session visibility is a per-session setting, and on Max/Pro the options are Private or **Public**,
  where public means any logged-in claude.ai user. So the guarantee is a default, not a property.
- **Deleting a session is the remediation that needs no history rewrite.** Anthropic's stated
  retention: a deleted conversation goes from history immediately and from back-end storage within
  30 days. The URL string stays in the commit message; what it points at stops existing.

[PITFALL: the documented scope of the trailer is narrower than the observed behaviour. Both public
write-ups state the link is added only for **web and Remote Control** sessions and that local CLI
sessions never add it — yet these commits were authored from local terminal sessions on this
machine. So do not assume `attribution.sessionUrl = false` covers every path that emits it. Set it,
then verify against a real commit before believing it.]

[PITFALL: there is a known upstream issue that the attribution setting did not control the session
URL (anthropics/claude-code#41873), which is what `sessionUrl` was added to fix, plus an open
request that the trailer be opt-in rather than default-on (#66504) and a docs gap (#69614). Check
the issue state at the version in use rather than assuming the flag works.]

## Recommended direction

Three separable pieces:

1. **Stop it recurring.** `attribution.sessionUrl = false`. This repo generates
   `~/.claude/settings.json`, so the value belongs in whatever config that pipeline reads, not in a
   hand-edit that the next deploy overwrites. That is the whole of this repo's part of the job.

   [DECISION: **the hand-edit is already applied, 2026-08-29** — the user asked for it to take
   effect immediately rather than waiting for this plan. `~/.claude/settings.json` now carries
   `"attribution": { "sessionUrl": false }` as a top-level key, and the file still parses. So this
   repo's remaining job is **durability, not discovery**: fold the same value into the generating
   config so the next `inv deploy` does not silently drop it. Check whether the pipeline preserves
   unknown top-level keys — if it does, the hand-edit survives and this is belt-and-braces; if it
   rewrites wholesale, the hand-edit is already living on borrowed time.]

   [UNVERIFIED: whether the setting actually suppresses the trailer. It could not be tested in the
   session that applied it — that session's own instructions were fixed when it started, so it kept
   emitting the trailer regardless of the file underneath. The first commit of the **next** session
   is the test. If it still carries `Claude-Session:`, the relevant upstream issue is
   anthropics/claude-code#41873 and the fallback is `attribution.commit`, whose empty string hides
   attribution entirely.]
2. **Kill the referents.** Delete the sessions on claude.ai so the 75 published URLs become dead
   pointers. Needs no history rewrite, which is the explicit constraint. Worth checking each
   session's visibility first — a session that was ever set Public is a different exposure from one
   that was always Private.
3. **Accept the residue.** Deleting sessions does not remove the id strings from public commit
   messages, so the metadata stays: how many sessions, when, which commits share one. That is
   correlation data about working patterns, not content. It is the part that would need a history
   rewrite, and a rewrite is explicitly ruled out — so this is a decision to accept it, and should
   be recorded as one rather than left looking like an oversight.

[NEEDS CLARIFICATION: whether any of these sessions was ever set to Public visibility. Nothing on
this machine can answer it; it is a look at the account's session list. It decides whether step 2 is
tidying or remediation.]

[DEFERRED: the same trailer is in `ingesta`'s 27 commits, which is private, so the exposure is
different and the urgency lower. Worth the same treatment eventually for consistency.]
