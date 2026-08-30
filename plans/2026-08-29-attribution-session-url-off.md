---
status: idea
updated: 2026-08-30
repo: git@github.com:TheodoreAD/power-user-linux-setup.git
---

# Stop the `Claude-Session:` trailer, and deal with the ones already published

## Context

Raised from a session in `agent-skills` on 2026-08-29, not from work on this repo. Filed in the
store rather than committed into `power-user-linux-setup/plans/` deliberately: writing into another
repo's working tree is the cross-repo-commit problem this whole filing convention is trying to stop.

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

## The setting was applied, and it did not work (2026-08-29)

The hand-edit went in the same day — the user asked for it to take effect immediately rather than
waiting for this plan. The test the plan named was "the first commit of the **next** session". That
test ran on 2026-08-29 ~21:30 in a `repo-tasks` session, and **it failed**:

- `~/.claude/settings.json` carries `"attribution": {"sessionUrl": false}` as a top-level key (line
  848 at the time of the check). The file parses, and `json.load` returns exactly that value — so
  the key is present and spelled as the research said.
- `claude --version` reports **2.1.251**, well past the 2.1.183 that introduced the setting.
- No project-level override: `repo-tasks/.claude/settings.json` sets only `env` and a `PreToolUse`
  hook, nothing about attribution.
- The session's own instructions nonetheless still said to end every commit message with
  `Claude-Session: https://claude.ai/code/session_<id>`. The user caught it on the first commit of
  the session, which is why the check happened at all.

So the setting is correctly placed, at a version that supports it, and the trailer is still emitted.
That is consistent with the first pitfall above: the flag was written for the documented path (web
and Remote Control), and plausibly never reaches the local terminal one.

The workaround in force is manual: the trailer is omitted by hand from each commit message. It works
— commits `c1861d8` (repo-tasks) and `e2c342f` (the plans store) carry `Co-Authored-By` and no
session URL — but it depends on the agent remembering, against an explicit instruction telling it to
do the opposite, on every commit for the life of the session.

## Open questions

[NEEDS CLARIFICATION: whether the emitting path is the settings file at all. Everything measured
above is consistent with the trailer being baked into the session prompt from something other than
`~/.claude/settings.json` — a managed/enterprise settings layer, a per-session default, or a code
path that predates the flag. Worth checking `claude config` output and the enterprise managed
settings location before spending another session on a settings key.]

[NEEDS CLARIFICATION: whether `attribution.commit = ""` actually suppresses it where `sessionUrl`
did not. It is the named fallback, but a strictly bigger hammer — it hides attribution entirely,
`Co-Authored-By` included, which is not what was asked for. And it is unverifiable in the session
that sets it, for exactly the reason `sessionUrl` was: the instructions are fixed at session start.
Same test, one session later.]

[NEEDS CLARIFICATION: whether upstream anthropics/claude-code#41873 is actually closed at 2.1.251,
or closed against the web path only. Flagged as the thing to check rather than assume; nobody has
checked it since.]

[NEEDS CLARIFICATION: whether any of these sessions was ever set to Public visibility. Nothing on
this machine can answer it; it is a look at the account's session list. It decides whether the
session-deletion step is tidying or remediation.]

## Recommended direction

Three separable pieces, and the first one is now a diagnosis rather than a settings edit.

1. **Stop it recurring.** Do not add another settings key on the strength of a guess — one has
   already been tried and its result went unrecorded until it had to be re-derived. In order:
   1. Determine where the instruction comes from before changing anything — managed settings,
      `claude config` as it actually resolves, and the upstream issue state at 2.1.251. One of those
      three likely explains it, and two of them mean no amount of editing `~/.claude/settings.json`
      will help.
   2. Only if that is inconclusive, try `attribution.commit = ""` and read the **next** session's
      first commit. Record the result either way.
   3. Keep the manual omission as the standing behaviour until one of the above works, and say so in
      `~/AGENTS.md` rather than leaving it as a per-session correction the user has to make again.
      That is this repo's part of the job: the rule belongs in the fragment that generates it, not
      in a session's memory of being told once.
   4. Whatever value ends up working, fold it into the config this repo's pipeline generates
      `~/.claude/settings.json` from, so the next deploy does not silently drop it — and check
      whether that pipeline preserves unknown top-level keys, because if it rewrites wholesale the
      current hand-edit is already living on borrowed time.
2. **Kill the referents.** Delete the sessions on claude.ai so the published URLs become dead
   pointers. Needs no history rewrite, which is the explicit constraint. Re-measure the table above
   first — every commit written since it was taken has added to the count.
3. **Accept the residue.** Deleting sessions does not remove the id strings from public commit
   messages, so the metadata stays: how many sessions, when, which commits share one. That is
   correlation data about working patterns, not content. It is the part that would need a history
   rewrite, and a rewrite is explicitly ruled out — so this is a decision to accept it, and should
   be recorded as one rather than left looking like an oversight.

[DEFERRED: the same trailer is in `ingesta`'s 27 commits, which is private, so the exposure is
different and the urgency lower. Worth the same treatment eventually for consistency.]
