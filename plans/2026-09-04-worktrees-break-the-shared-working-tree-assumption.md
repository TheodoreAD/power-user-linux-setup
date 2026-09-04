---
status: idea
updated: 2026-09-04
---

# `~/AGENTS.md` reasons from "parallel sessions share one working tree", which worktrees make false

## Context

Filed from `agent-skills` on 2026-09-04 while auditing that corpus for git worktree directory
patterns (`plans/2026-09-04-skills-assume-one-working-tree-per-repo.md` there, which owns the
scripts half). This half is not about any skill — it is about the always-loaded instructions file
this repo generates, and it has to be decided here.

`~/AGENTS.md` states the assumption outright, in "Committing multi-part work":

> **`git log` is how a future agent learns why a change happened, and here it cannot go and look
> instead**: parallel sessions share one working tree, so checking out an old commit moves a tree
> somebody else is working in.

and again in "Unexplained git/file state in a working tree":

> Parallel sessions on this machine share one working tree, so the usual "they must fetch and reset
> after your rewrite" does not apply — nothing of theirs to reset, and the stale part is their
> context, not their repo.

Both are true of the setup as it stands, and both stop being true the moment a session runs Claude
Code's `EnterWorktree`, which creates a checkout at `<repo>/.claude/worktrees/<name>` and moves that
session into it. The tool exists, it is documented to this machine's agents, and its whole purpose
is to give one session a working tree of its own.

**Merged in 2026-09-04 from `2026-09-04-worktrees-break-the-one-working-tree-assumption.md`**, filed
a few hours later by a session that did not check the mirror first. Three things it added, and
nothing else of its own survives:

- **It is not only Claude Code, and the second one is a default nobody opts into.** VS Code's
  built-in worktree support puts a worktree in a **sibling** `<repo>.worktrees/<name>`; its own test
  plan states "the default worktree path is a directory the same level as your main repo, named
  `<repoName>.worktrees`", and the request to make that configurable (microsoft/vscode#293884, Feb
  2026) is open and unanswered. `EnterWorktree` at least takes an explicit ask; this one arrives
  from a GUI button. It also lands **outside** the repo, so the `git add -A` evidence below does not
  cover it and the "second clone" reading does.
- **Nothing on this machine has hit any of it yet.** None of the 211 project directories under
  `~/.claude/projects/` is a worktree, so no session here has ever run from one. That makes every
  rule below preventive, and is the argument for taking the larger rewrite rather than the quick
  caveat: there is no live breakage forcing a fast fix.
- **A gitignore question this repo can answer once for the machine**, below.

## Why this is worth a plan rather than an edit

**The rules reasoned from the assumption do not all fail the same way, so "add a worktree caveat" is
not the fix.** Three cases, and they point in different directions:

- **"`git log` is the channel, because you cannot check out an old commit here."** In a worktree
  this reasoning inverts: a session with its own checkout _can_ check out an old commit safely. The
  conclusion (write a real body on every commit) is worth keeping regardless, but its stated reason
  would be wrong for the session most able to act on it.
- **"Nothing of theirs to reset."** This is the dangerous one. After a history rewrite, a session
  sitting in a worktree of the same repository _does_ have something to reset, and the current text
  says explicitly that it does not. A rewrite performed on that advice leaves a real, stale checkout
  behind while the instruction says the problem cannot exist.
- **"Stage by path, never `git add -A`."** Unchanged in its conclusion and _strengthened_ in its
  reason: measured 2026-09-04 in a throwaway repo, `git add -A` in a repo containing a nested
  worktree adds it as an embedded git repository — `warning: adding embedded git repository`,
  exit 0. A blanket stage in a worktree-using repo commits a gitlink nobody meant to create.

## Open questions

[NEEDS CLARIFICATION: **is the assumption worth keeping as the default, or should it be rewritten to
be worktree-neutral?** Keeping it means adding an exception to three rules and hoping the reader
notices which one they are under. Rewriting means the rules stop leaning on "there is only one tree"
and lean on "read the state rather than assuming it" — which is already how the force-push and
undo-by-SHA rules are written, and they need no exception at all. The second is probably right and
is a larger edit.]

[NEEDS CLARIFICATION: **should `~/AGENTS.md` say anything about when to use a worktree at all?** The
harness already gates `EnterWorktree` behind an explicit request, so the file may need nothing. But
a session that is _in_ one has no rule telling it that the repo-wide statements it just read do not
describe its situation, and no cheap way to notice.]

[NEEDS CLARIFICATION: **should `.claude/worktrees/` go in this machine's global gitignore
(`~/.config/git/ignore`)?** Untracked rather than ignored, a nested worktree shows as
`?? .claude/worktrees/` in every `git status` and reads as a dirty tree to every harvest, and it is
what makes the `git add -A` gitlink below possible. `agent-skills` answered it per-repo on
2026-09-04 with one line in its own `.gitignore`; a global entry covers every repo and publishes
nothing, at the cost of hiding the directory from a repo whose author wanted it tracked — which
nobody does. VS Code's sibling layout needs no ignore at all, being outside the repo.]

[NEEDS CLARIFICATION: **does `inv` tooling here assume one tree per repo too?** Not checked from the
filing session, which had no business reading this repo. `direnv`'s `.envrc` allow-list is keyed by
path, so a new worktree is an unallowed directory until someone runs `direnv allow` in it — which
would make a venv-resolving rule ("`which <tool>` before prefixing `uv run`") behave differently
there. Worth one look before deciding the wording.]

## Recommended direction

1. **Decide the framing question above first** — every wording choice below follows from it.
2. **Fix the "nothing of theirs to reset" sentence whatever the framing**, because it is the one
   that is actively wrong rather than merely narrow, and its subject is a history rewrite.
3. **Keep the `git add -A` ban and give it the worktree reason as a second line of evidence**, since
   the measurement above strengthens a rule that already exists rather than adding one.
4. **Leave the skills alone from here** — the scripts half is `agent-skills`'s, and as of 2026-09-04
   it is **done**: `plans/2026-09-04-skills-assume-one-working-tree-per-repo.md` there is `landed`,
   with every step implemented and its three open questions settled. `plan-docs` keys a store mirror
   on the repository rather than the checkout and no longer enrols a worktree as a second repo,
   `session-harvest` and `skill-authoring` name the install consequence, and `session-bash-audit`
   carries a declared limitation. Cite that plan rather than restating it; the two should not both
   grow a copy of the same evidence table, which is exactly what the merged-away duplicate did.
