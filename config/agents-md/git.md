## Git & commits

### git fetch/push needing an SSH key [needs PULSE's zprofile]

**Run the plain `git` command — `git push`, `git fetch`, no prefix and no wrapper.** That is the
normal case and it is what to reach for every time. Keys live unlocked in the desktop keyring's
agent from login, and `~/.zprofile` points each shell at whichever agent actually holds keys, so
this normally just works with no prompt. `SSH_ASKPASS` (same Zenity helper,
`SSH_ASKPASS_REQUIRE=prefer`) pops a GUI passphrase dialog for a key that genuinely needs one; it
blocks on user input and times out if nobody is at the machine. No HTTPS/token workaround needed.

Everything below fires **only after a command has actually failed.** None of it is setup to do
first.

**When it fails with "Permission denied (publickey)", run `inv ssh.check` before anything else** —
do not reach for `ssh-add`, and never ask the user for a passphrase on the strength of that error.
This machine runs two agents (the keyring's and keychain's), and a shell pinned to the empty one
fails exactly that way while every key sits unlocked in the other. A session that read the failure
as a missing key ran `ssh-add`, and had the user type a passphrase into three dialogs for a key that
was already loaded elsewhere and needed none. A session's own shell snapshot is captured once and
survives a reboot, so an agent session is the most likely thing to be holding a stale socket.
`ssh-add -l` exits 0 with keys, 1 for a live but empty agent, 2 for no agent — those last two look
alike and mean opposite things.

**When `ssh.check` has told you to, apply its verdict as a per-call prefix, not as an `export`.**
`ssh.check` ends with `export SSH_AUTH_SOCK=/run/user/1000/keyring/ssh` for a human's interactive
shell; an agent's Bash calls each get a fresh shell, so the export evaporates and the next command
fails exactly as before — which reads as "the fix didn't work" and sends the session back toward
`ssh-add`. Prefix instead, on every ssh call **for the rest of that diagnosis**:
`SSH_AUTH_SOCK=/run/user/1000/keyring/ssh git push`. A session that pushed with the prefix then ran
a bare `git fetch` two turns later and got the same publickey error, while every key sat unlocked in
the keyring's agent. The prefix is the repair for a shell pinned to the empty agent — not the house
style for pushing, and a session that has not seen a publickey failure should never be typing it.
`gh` is not affected — it authenticates with its own token — so a green `gh` command is not evidence
that the shell's ssh agent is the right one.

### Committing to a repo that is or might become public [needs agent-skills]

**Never name an employer, client, internal project, work repo, work email address or ticket prefix
in a repo you publish** — in any file, a plan or a commit message included. A push cannot be taken
back by a later edit: the content stays in the history, and a repo's history is as readable as its
tip. Write about that work by its shape instead ("a work root with a `<project>/<repo>` hierarchy",
"a client repo under review pressure", "work root A") — for a measurement, the counts and the
structure are the evidence and the names never were.

Check it mechanically rather than by reading carefully, because the agent writing the sentence is
the one that does not know it is doing something wrong:

```shell
python3 ~/.agents/skills/plan-docs/scripts/plans.py scan --mode staged   # before the commit
python3 ~/.agents/skills/plan-docs/scripts/plans.py scan --mode history  # what is already published
```

It derives the forbidden names from this machine's own project roots, so nothing has to be listed
anywhere — a list of clients is itself the thing that must not be written down in a public repo. An
employer with no clone here has no directory to derive from and must be added to `[private] extra`
in `~/.config/plan-docs/config.toml` by hand, once.

A hit in **pushed** history is not an edit to make quietly: redacting the working tree changes
nothing about what is published. Report it, name the commits, and let the user decide — purging
means rewriting history, force-pushing, and asking the host to expire the old commits.

The same principle applies to data leaving the machine at all: **a feature that uploads, publishes
or phones home by default is a decision, not a default.** Pin the flag off deliberately and say why,
rather than accepting the behaviour because it shipped that way — report publishing, telemetry, any
"share with the vendor" toggle. Local costs nothing and cannot be taken back later, which is the
same reasoning that keeps the plans store's sensitive tier without a remote.

### Force-pushing, or asking what a remote actually has

Every ref you hand git is one you read, never one you derived: `--force-with-lease` is only as good
as its SHA, so pass one from `git rev-parse` rather than a short form completed by eye. A lease
built from a hand-extended 40-character SHA was refused as stale info — the mechanism working, but
the invented value was the author's, not git's.

Before assuming another session holds its own copy of the history, check: `git worktree list` and a
look for a second clone. Parallel sessions on this machine share one working tree, so the usual
"they must fetch and reset after your rewrite" does not apply — nothing of theirs to reset, and the
stale part is their context, not their repo.

A remote-tracking ref answers "what did I last fetch", not "what does the remote have". A plain
`git fetch` never prunes, so `origin/<branch>` can outlive a branch deleted upstream weeks earlier —
and `git branch -r --contains` will happily report that ghost. Before trusting any local answer
about remote state, ask the host — `gh api repos/<owner>/<repo>/branches` or `git ls-remote` — and
`git fetch --prune`. A branch was once folded into a history rewrite to protect against an exposure
that had not existed for weeks.

### About to commit

Run the repo's quality gate first (`inv quality.precommit` where the repo-tasks tasks exist, else
the repo's own equivalent) — every commit, including a markdown-only one. "Just docs" is not exempt:
`dprint` formats markdown, and plan/skill/AGENTS.md reflows are the single most common CI failure in
these repos, all of them pushed from commits that skipped the gate. The gate is what CI runs;
skipping it schedules a red run that someone else reads.

**Write the message without backticks or `$`.** Both are live inside a double-quoted shell argument:
backticks are command substitution, so the shell _runs_ what they enclose before git sees it and
stores the output in their place. A message describing an apt fix ran `apt-get install -f -y` and
`dpkg -i && rm` on the machine and committed two empty strings where the quoted commands belonged;
only the lack of privilege made it harmless. Commit messages are prose, not Markdown — name a
command in plain words and nothing breaks. Same hazard in any other double-quoted body —
`gh pr create --body`, `gh issue comment`.

**Then keep it where the user can read it: one inline `-m`, in its own call.** The approval prompt
shows the _command_, and the message is what the user reads to decide, so anything displacing it
from the prompt defeats the rule while looking like compliance. Three shapes do, and each has been
corrected here in turn: `git commit -F <file>` hides it behind a path; a chain buries it mid-command
(see "Composing a Bash call", which owns that cost); and a series of `-m` flags runs them together
into one unbroken line, even though git joins each into its own paragraph so the finished commit and
`git log` show nothing wrong. Put the blank lines inside one quoted argument instead. Said by the
user 2026-09-02, on a five-`-m` commit: _"it's hard to read a wall of text"_. Reach for `-F` only
when the message genuinely must contain a backtick; pathspec works either way (see "Committing
multi-part work").

### Committing multi-part work

**`git log` is how a future agent learns why a change happened, and here it cannot go and look
instead**: parallel sessions share one working tree, so checking out an old commit moves a tree
somebody else is working in. `git log` and `git show` are the only reads safe by construction, which
makes the history the channel rather than the convenient record. Two things follow, and they are the
whole of this rule.

**Split it into small single-concern commits**, even when the request was a single ask. A doc update
commits separately from the code implementing it; a bug fix found mid-implementation folds into the
commit introducing the correct behavior, never broken-then-fixed. Granularity is settled — ask only
_whether_ to commit, never how to split.

**And every commit has a body.** The subject says what changed; the body says what it is for, what
it beat, and what it cost. A doc or plan commit is not exempt, and is the case where "the file
already says it" is not merely weak but backwards: `git log` does not show the file, and `plan-docs`
retires a plan by **deleting** it, so the file is deliberately temporary while its commit message is
permanent. **A trailer is not a body** — `Co-Authored-By:` alone satisfies `%b`, which is exactly
how two bare commits passed unnoticed in the session that prompted this rule.

It is a floor, not a ceremony: a formatting fix's why is one clause, and demanding a paragraph for
it teaches padding, which is worse than a bare subject because padding reads as reasoning. **Nothing
enforces it** — a `commit-msg` hook is the first thing anybody reaches for and is refused for the
same reason every other behind-the-agent's-back mechanism is (see "Proposing an enforcement
mechanism"); that call was re-measured 2026-09-02 and the CI shape it would have caught has stopped
occurring. **One exception, named so it is not discovered as an inconsistency:** a plan filed into
the plans store commits as `<repo>: <what it is>` with no body, because a filed plan _is_ its own
description and the commit is only its delivery. `gh pr create --body` and `gh issue comment` get
the full rule, not the exception.

When a quality gate run for unrelated work fixes formatting in a file you didn't mean to touch, keep
the fix as its own tiny commit — reverting it just schedules the same CI failure for someone else to
rediscover. Revert an incidental change only when the repo's CI would not enforce it (a stray
content edit, not a formatting fix); that distinction is the line, not "did I mean to touch this
file."

Stage each commit's paths immediately before that commit, never ahead of time. `git commit` ships
the whole index, so anything staged earlier — a `git rm` run while tidying, a `git mv` run while
editing, a `git add` from a previous step — rides along under the next message, and the split has to
be rewritten. `git mv` is the one that gets missed: `rm` and `add` read as staging, a rename reads
as an edit. What removes the risk entirely is committing by pathspec —
`git commit -m "…" -- <path> <path>` takes the named paths whatever else sits in the index.

When two concerns land in the _same file_, staging by path can't separate them and `git add -p`/`-i`
is unavailable here — but that is not a reason to give up and ship one fat commit. Copy the finished
file to the scratchpad, edit it back down to just the first concern, verify that state passes the
gate (it has to: each commit should stand on its own), commit, then restore the copy and commit the
rest. Cheap, and the intermediate gate run is what catches a split that doesn't actually decompose.

### Regenerating a file from a canonical source

Commit the regenerated output, and run regeneration as its own deliberate standalone command — never
gitignored as "reproducible," never auto-wired into routine `fix`/`check`/`precommit` runs.
`git blame`/`git log` on the output is how "what was actually in effect" gets answered, and routine
work silently pulling in an upstream bump nobody chose to take is exactly the surprise to avoid.
Regeneration is reviewed, tested, and committed like any other change.

When the canonical file names paths, ordering is part of that review: adopt the structure it assumes
_before_ pulling it, then run the repo's own gate. A pull is not inert — a canonical `pytest.ini`
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
file may belong to another live session — don't assume it's yours, a subagent's, or any specific
cause; surface it and ask neutrally before building on it. Once the user assigns it to another
session, it's fully hands-off — don't re-read or reference it further. Before committing to a repo
that showed concurrent activity, `git fetch` and check `git log origin/<branch>` to see whether the
remote moved.

Stage by path there, never `git add -A`/`git add .` — a parallel session's edit can land between
your last `git status` and your commit, and a blanket stage silently ships it under your commit
message. `git status --short` immediately before committing is not protection: it reports the staged
set, not what changed while you were reading it. Commit by pathspec (see "Committing multi-part
work") — a parallel session's staged file can then neither ride along nor be disturbed.

**Undo by SHA, never by a relative ref.** `git reset --soft HEAD~1` silently retargets when another
session commits in the interval — `HEAD~1` then resolves to _your_ commit and the reset discards
_theirs_, with no error, because both readings are valid git. Read the SHA (`git rev-parse`, or the
reflog) and reset to it — the same rule as the force-push lease, one step earlier.

The same holds one step later: before pushing, `git log origin/<branch>..HEAD` — a commit there you
didn't make belongs to another live session, which may still mean to amend or reorder it. Say so and
ask before your push publishes it.

### Pushing to a personal repo's default branch

Direct pushes to `main`/`master` are the norm on the user's own personal repos
(`power-user-linux-setup`, `repo-tasks`, `scaffoldapy`, ...) — sole contributor and owner, so PR
review gates nothing. A "bypassing branch protection" message on push is expected there (the rule is
a force-push guard, not a review gate) — don't flag it and don't suggest a PR. None of this
transfers to a shared/team repo with real other contributors.
