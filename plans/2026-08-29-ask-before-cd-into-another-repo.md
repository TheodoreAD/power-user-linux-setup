---
status: idea
updated: 2026-08-29
repo: git@github.com:TheodoreAD/power-user-linux-setup.git
---

## Context

Raised by the user 2026-08-29 from a session in `agent-skills`, while reviewing the cross-repo guard
built into `plan-docs`: _"we should have a rule to always ask before cd in other repos anyway."_
Filed here rather than committed into this repo, for the reason the rule itself is about.

`~/AGENTS.md` already covers the mechanics of running a command against another repo — prefer the
tool's own `-C`/`--config` scoping, use `cd <repo> && <one command>` only when unavoidable, and
treat cwd as unknown afterwards. What it does not say is that **`cd`-ing into another repo is a
decision to put to the user first**, not a technique to reach for silently.

## Why it matters more than it looks

Two things make a stray `cd` expensive on this machine specifically:

1. **Parallel sessions share one working tree.** A session that wanders into another repo and writes
   there is putting a file under a session already working in it.
2. **cwd persistence is unreliable in both directions.** Measured 2026-08-29 inside one session: a
   `cd` into the scratchpad persisted and broke a later `pytest` that assumed the repo, while a `cd`
   into a sibling repo minutes later was followed by `Shell cwd was reset`. Both behaviours, one
   session, same harness version.

[PITFALL: the second point is what makes the first hard to defend against with tooling. `plan-docs`'
cross-repo guard compares the write target against cwd — so when cwd itself has drifted, both sides
of the comparison drift together and the guard cannot fire at all. A tool cannot reliably detect
"this session is somewhere it should not be" when the only signal available is the thing that moved.
That is precisely why the rule has to be behavioural: ask first, so the drift never happens.]

## Recommended direction

Add to the `Bash & tool use` section of the agents-md fragments, near the existing cross-repo
guidance:

- **Never `cd` into another repo without asking the user first.** It is a decision, not a technique:
  the target may have a live session in it, and cwd may not come back. Prefer the tool's own
  directory scoping every time it exists.
- **After any command that changed directory, treat cwd as unknown** until a call re-establishes it
  — already stated, but worth pairing with the above so the two read as one rule.
- Where the work is genuinely in another repo, it belongs in **its own session**, which is already
  the stated preference; this rule is what makes that preference enforceable rather than advisory.

[NEEDS CLARIFICATION: whether "ask first" should also cover `cd` into non-repo directories — the
scratchpad, `/tmp`, a build output tree. The measured breakage above was a scratchpad `cd`, so the
cost is real there too, but requiring a question before every scratchpad write would be heavy. A
narrower version — ask before `cd` into another _repo_, and treat every other `cd` as
persistence-unsafe — is probably the right split, but it is a judgement about friction the user
should make.]

[DEFERRED: `plan-docs` states a local version of this rule in its own `SKILL.md`, since it is what
its cross-repo guard leans on. If this lands in `~/AGENTS.md`, check the two do not contradict each
other — the skill's copy is deliberately narrower, covering only plan writes.]
