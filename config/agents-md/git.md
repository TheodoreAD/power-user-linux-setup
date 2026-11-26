## Git & commits

### Committing to a repo that is or might become public [needs agent-skills]

**Never name an employer, client, internal project, work repo, work email address or ticket prefix
in a repo you publish** — in any file, a plan or a commit message included. A push cannot be taken
back by a later edit. The content stays in the history, and a repo's history is as readable as its
tip. Write about that work by its shape instead: "a work root with a `<project>/<repo>` hierarchy",
"a client repo under review pressure", "work root A". For a measurement, the counts and the
structure are the evidence and the names never were.

Check it mechanically rather than by reading carefully. The agent writing the sentence is the one
that does not know it is doing something wrong.

```shell
python3 ~/.agents/skills/plan-conveyor/scripts/plans.py scan --mode staged   # before the commit
python3 ~/.agents/skills/plan-conveyor/scripts/plans.py scan --mode history  # what is already published
```

It derives the forbidden names from this machine's own project roots, so nothing has to be listed
anywhere — a list of clients is itself the thing that must not be written down in a public repo. An
employer with no clone here has no directory to derive from. Add it to `[private] extra` in
`~/.config/plan-conveyor/config.toml` by hand, once.

A hit in **pushed** history is not an edit to make quietly. Redacting the working tree changes
nothing about what is published. Report it, name the commits, and let the user decide — purging
means rewriting history, force-pushing, and asking the host to expire the old commits.

The same principle applies to data leaving the machine at all: **a feature that uploads, publishes
or phones home by default is a decision, not a default.** Pin the flag off deliberately and say why,
rather than accepting the behaviour because it shipped that way. Report publishing, telemetry, any
"share with the vendor" toggle. Local costs nothing and cannot be taken back later, which is the
same reasoning that keeps the plans store's sensitive tier without a remote.

### Keeping personal details out of a repo

**Never write the user's name, email address, GitHub login or ID, OS username, computer name, key
names, home path or hardware into code, config or docs.** Derive them where they are needed
(`$HOME`, `$env:USERNAME`/`$USER`, `$env:COMPUTERNAME`, `gh api user`), use placeholders such as
`__HOME__` in templates and fill them in at install, and give examples made-up values (`MY-PC`,
`my-user`).

**Commits must not expose a personal email address either.** Commit with GitHub's noreply address,
`<id>+<login>@users.noreply.github.com`, derived from `gh api user`.

### Working in a repo under a client's root [needs agent-skills]

**Read, quote and file nothing from outside that root**: no other client's repo, transcript or plan,
and no private repo of the user's, its name included. Public sources and anything inside the same
root are fine. A client root is one listed as `contractor` under `[activity]` in
`~/.config/plan-conveyor/config.toml`. Each client root is insulated from every other.
plan-conveyor, session-harvest, session-bash-audit and skill-fitness enforce that for what they
write, but nothing sees what a session itself opens, and `~/.claude/projects/` holds every session's
transcript in one tree.

### Setting up a new repo

- **A `.gitattributes` that stores and checks out text as LF** (`* text=auto eol=lf`), keeps
  `.bat`/`.cmd` as CRLF and marks binaries. Shell scripts that run in WSL or on Linux must be LF.
  The template is `git/gitattributes` in the `win-configs` repo.
- **Editor folders (`.vscode/`, `.idea/`) are personal** and never committed.

### Force-pushing, or asking what a remote actually has

Every ref you hand git is one you read, never one you derived. `--force-with-lease` is only as good
as its SHA, so pass one from `git rev-parse` rather than a short form completed by eye. A lease
built from a hand-extended 40-character SHA was refused as stale info — the mechanism working, but
the invented value was the author's, not git's.

Before assuming another session holds its own copy of the history, check `git worktree list` and
look for a second clone. Parallel sessions on this machine share one working tree, so the usual
"they must fetch and reset after your rewrite" does not apply. Nothing of theirs to reset, and the
stale part is their context, not their repo.

A remote-tracking ref answers "what did I last fetch", not "what does the remote have". A plain
`git fetch` never prunes, so `origin/<branch>` can outlive a branch deleted upstream weeks earlier,
and `git branch -r --contains` will happily report that ghost. Before trusting any local answer
about remote state, ask the host — `gh api repos/<owner>/<repo>/branches` or `git ls-remote` — and
`git fetch --prune`. A branch was once folded into a history rewrite to protect against an exposure
that had not existed for weeks.

### About to change code, or re-decide something, whose reason you don't know

Read its history first. `git log` is safe in a working tree another session holds; a checkout is
not.

```shell
git log -n 5 --format='%h %s%n%b' -- <path>
git log --format='%h %s%n%(trailers:key=Rejected,valueonly)' --grep='^Rejected:' -- <path>
```

A `Rejected:` line naming what you were about to propose means it was tried. Read that commit's body
before proposing it again, and if you still think it is right, say what has changed since. A
`Not-verified:` line on the code you are touching is a risk you now inherit.

### About to commit

Run the repo's quality gate first: `inv quality.precommit` where the repo-tasks tasks exist, else
the repo's own equivalent. Every commit, including a markdown-only one. "Just docs" is not exempt.
`dprint` formats markdown, and plan/skill/AGENTS.md reflows are the single most common CI failure in
these repos, all of them pushed from commits that skipped the gate. The gate is what CI runs, so
skipping it schedules a red run that someone else reads.

### Committing multi-part work

Parallel sessions share one working tree, so checking out an old commit moves a tree somebody else
is working in. `git log` and `git show` are the only reads safe by construction, which makes the
history the channel rather than the convenient record. Two things follow.

**Commit as you go.** In a multi-step task, commit each step as soon as it is finished and passes
the gate, without waiting to be asked, and never end a task with finished work left uncommitted.

**Split it into small single-concern commits**, even when the request was a single ask. A doc update
commits separately from the code implementing it. A bug fix found mid-implementation folds into the
commit introducing the correct behavior, never broken-then-fixed. Granularity is settled — ask only
_whether_ to commit, never how to split.

**And every commit has a body**, in this order. First what changed, named the way a reader would
search for it: the setting, flag, function, field or file, and what it now does. Then what the
change is for, what it beat and what it cost. The bar is that `git log` alone explains the change
and the diff only confirms it. **Cite only files tracked in this repo, by their path in it** — a
plan under its `plans/`, a doc, a module — never a nickname like "the leanness plan", since a
retired plan is deleted and only its path finds it again. Never a path elsewhere on the machine: the
plans store, a research clone, a scratchpad, a transcript. A store-held plan is kept out of the repo
on purpose, and a commit naming it publishes what the routing hides. When the commit records an
investigation whose evidence is local, say what the evidence is and that it is local. A doc or plan
commit is not exempt, and is the case where "the file already says it" is backwards: `git log` does
not show the file, and `plan-conveyor` retires a plan by **deleting** it, so the file is temporary
while its message is permanent. **A trailer is not a body** — `Co-Authored-By:` alone satisfies
`%b`. It is a floor rather than a ceremony: a formatting fix's why is one clause, and padding reads
as reasoning, which is worse than a bare subject. **One exception**, named so it is not discovered
as an inconsistency: a plan filed into the plans store commits as `<repo>: <what it is>` with no
body, because a filed plan _is_ its own description. `gh pr create --body` and `gh issue comment`
get the full rule, not the exception.

**Then the trailers, which make the history searchable by the next agent.** Each is written only
when its condition holds, one per line, in the final block together with `Co-Authored-By:` and no
blank line inside it — git reads only that last unbroken block as trailers:

- `Plan: plans/<file>.md` — the commit carries out a plan tracked in this repo. Never a store-held
  plan.
- `Rejected: <approach> (<reason>)` — an alternative was weighed and dropped. One line each.
- `Verified: <command or probe>` — what was run that proves the change.
- `Not-verified: <what> (<why>)` — a part that was not proven. The risk the next session inherits.

The body still explains; a trailer is the line a query finds.

**Stage each commit's paths immediately before that commit**, never ahead of time. `git commit`
ships the whole index, so anything staged earlier rides along under the next message — a `git rm`
run while tidying, a `git mv` run while editing, a `git add` from a previous step. `git mv` is the
one that gets missed, because `rm` and `add` read as staging while a rename reads as an edit.
Committing by pathspec removes the risk entirely: `git commit -m "…" -- <path> <path>` takes the
named paths whatever else sits in the index.

**When two concerns land in the _same file_**, staging by path cannot separate them and
`git add -p`/`-i` is unavailable here. That is not a reason to ship one fat commit. Copy the
finished file to the scratchpad, edit it back down to just the first concern, verify that state
passes the gate, commit, then restore the copy and commit the rest. The intermediate gate run is
what catches a split that does not actually decompose.

When a gate run for unrelated work fixes formatting in a file you did not mean to touch, keep the
fix as its own tiny commit. Reverting it just schedules the same CI failure for someone else to
rediscover. Revert an incidental change only where the repo's CI would not enforce it: a stray
content edit, not a formatting fix.

### Regenerating a file from a canonical source

Commit the regenerated output, and run regeneration as its own deliberate standalone command. Never
gitignored as "reproducible," never auto-wired into routine `fix`/`check`/`precommit` runs.
`git blame`/`git log` on the output is how "what was actually in effect" gets answered, and routine
work silently pulling in an upstream bump nobody chose to take is exactly the surprise to avoid.
Regeneration is reviewed, tested, and committed like any other change.

When the canonical file names paths, ordering is part of that review: adopt the structure it assumes
_before_ pulling it, then run the repo's own gate. A pull is not inert. A canonical `pytest.ini`
whose `testpaths` named a `tests/unit/` the repo hadn't created yet sent pytest's fallback search
into a second `tests/` tree and broke collection outright, exit 2 rather than the documented
warning.

**Two operations share these words and take opposite answers.** Everything above is about _pulling_
a file from a source outside the repo, where the surprise is an upstream bump nobody chose.
**Generating** a file from the repo's own code — a docs table rendered from a constant in `tasks/`,
a schema emitted from a model — has no upstream and no bump: generator and output land in the same
commit. That one belongs **in the quality gate, early**, ahead of the linters and formatters so they
format what was just written, and the result is committed by whoever ran it. Neither is ever
gitignored.

**No CI job may commit a generated file back to a branch.** Not `main`/`master`, not a release,
support, develop or feature branch — a throwaway branch is the only acceptable target. Auto-commit
turns a reviewed change into an unreviewed one and rewrites the branch under whoever is working on
it. If CI should care, it runs the generator and **fails on a diff** rather than committing one.
Deleted from `power-user-linux-setup`'s `devcontainer.yml` 2026-09-01, where a
`git-auto-commit-action` step pushed a regenerated docs block straight to `master`.

### Unexplained git/file state in a working tree

This user runs parallel sessions on the same repos, so an unrecognized commit, diff, or untracked
file may belong to another live session. Don't assume it's yours, a subagent's, or any specific
cause. Surface it and ask neutrally before building on it. Once the user assigns it to another
session, it's fully hands-off — don't re-read or reference it further. Before committing to a repo
that showed concurrent activity, `git fetch` and check `git log origin/<branch>` to see whether the
remote moved.

Stage by path there, never `git add -A`/`git add .`. A parallel session's edit can land between your
last `git status` and your commit, and a blanket stage silently ships it under your commit message.
`git status --short` immediately before committing is not protection: it reports the staged set, not
what changed while you were reading it. Commit by pathspec (see "Committing multi-part work") — a
parallel session's staged file can then neither ride along nor be disturbed.

**Undo by SHA, never by a relative ref.** `git reset --soft HEAD~1` silently retargets when another
session commits in the interval. `HEAD~1` then resolves to _your_ commit and the reset discards
_theirs_, with no error, because both readings are valid git. Read the SHA (`git rev-parse`, or the
reflog) and reset to it — the same rule as the force-push lease, one step earlier.

The same holds one step later: before pushing, `git log origin/<branch>..HEAD`. A commit there you
didn't make belongs to another live session, which may still mean to amend or reorder it. Say so and
ask before your push publishes it.

**And the inverse, which is the one nothing signals: a local commit is not a private holding
state.** Your commit sits on a shared branch in a shared clone, so any other session's `git push`
carries it to the remote regardless of whether you were holding it for approval. An ahead-count
falling to zero reads as "someone pushed, fine" rather than as work published without the decision
that was being waited on. Verify with `git branch -r --contains <sha>` after a fetch, never from the
count. "I will commit but not push, and ask first" is a stated intention, not a mechanism. Work that
genuinely must be withheld has to stay off the shared branch, and otherwise the user should be told
before the commit that the commit itself is the publishing decision. This is where the
confidentiality rule above is sharpest, since all of it turns on a push being irreversible.

### Pushing to a personal repo's default branch

Direct pushes to `main`/`master` are the norm on the user's own personal repos
(`power-user-linux-setup`, `repo-tasks`, `scaffoldapy`, ...) — sole contributor and owner, so PR
review gates nothing. A "bypassing branch protection" message on push is expected there, since the
rule is a force-push guard rather than a review gate. Don't flag it and don't suggest a PR. None of
this transfers to a shared/team repo with real other contributors. Work on the default branch unless
the user asks for another one, and `git fetch` before pushing to make sure it is not behind its
remote.
