## Agent instructions & knowledge

### Setting up a repo's agent instructions and skills

`AGENTS.md` at the repo root is the real file — the cross-tool convention read by 30+ agents.
`CLAUDE.md`, if present at all, is a plain **symlink** to it, never a file containing the
`@AGENTS.md` import directive (Claude-Code-specific syntax other harnesses would read as literal
text); `~/AGENTS.md` itself follows this, with `~/.claude/CLAUDE.md` symlinking to it. Nothing can
be appended below a symlink's target, so a genuinely Claude-specific addendum goes in `AGENTS.md`
itself or a separate `.claude/`-scoped file. Skills live in `.agents/skills/`, the cross-tool
convention, with each agent's own skills directory symlinked to it for the agents that don't read it
natively.

### Where durable knowledge goes

Durable repo-specific knowledge → that repo's own `AGENTS.md` (or a `docs/*.md` it points to);
durable cross-repo or personal preference → `~/AGENTS.md`. Not a harness's own per-session or
per-project memory store: those are invisible to every other contributor, every other agent tool,
and every code review, while an `AGENTS.md` is version-controlled and visible to all three.

## Git & commits

### Committing to a repo that is or might become public

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

Measured 2026-08-28: an agent published, in a public repo, a plan tabulating six employer/client
root directory names plus one client's internal project path, and a second public repo had four work
email addresses committed inside a listing of SSH key filenames. Both were written by agents with no
rule telling them not to.

### Force-pushing, or asking what a remote actually has

`--force-with-lease` is only as good as the SHA handed to it: pass one read from `git rev-parse`,
never one completed from a short form by eye. Measured 2026-08-29 — a lease built from a
hand-extended 40-character SHA was refused as stale info, which is the mechanism working, but the
invented value was the author's, not git's.

Before assuming another session holds its own copy of the history, check: `git worktree list` and a
look for a second clone. Parallel sessions on this machine share one working tree, so the usual
"they must fetch and reset after your rewrite" does not apply — nothing of theirs to reset, and the
stale part is their context, not their repo.

A remote-tracking ref answers "what did I last fetch", not "what does the remote have". A plain
`git fetch` never prunes, so `origin/<branch>` can outlive a branch deleted upstream weeks earlier —
and `git branch -r --contains` will happily report that ghost. Ask the host
(`gh api
repos/<owner>/<repo>/branches`) or `git ls-remote`, and `git fetch --prune` before trusting
any local answer about remote state. Confirmed the same day: a branch was folded into a history
rewrite to protect against an exposure that had not existed for weeks.

### About to commit

Run the repo's quality gate first (`inv quality.precommit` where the repo-tasks tasks exist, else
the repo's own equivalent) — every commit, including a markdown-only one. "Just docs" is not exempt:
`dprint` formats markdown, and plan/skill/AGENTS.md reflows are the single most common CI failure in
these repos, all of them pushed from commits that skipped the gate. The gate is what CI runs;
skipping it schedules a red run that someone else reads.

### Committing multi-part work

Split it into small single-concern commits, even when the request was a single ask — git history is
how future agents learn why a change happened. A doc update commits separately from the code
implementing it; a bug fix found mid-implementation folds into the commit introducing the correct
behavior, never broken-then-fixed. Granularity is settled — ask only _whether_ to commit, never how
to split.

When a quality gate run for unrelated work fixes formatting in a file you didn't mean to touch, keep
the fix as its own tiny commit — reverting it just schedules the same CI failure for someone else to
rediscover. Revert an incidental change only when the repo's CI would not enforce it (a stray
content edit, not a formatting fix); that distinction is the line, not "did I mean to touch this
file."

Stage each commit's paths immediately before that commit, never ahead of time. `git commit` ships
the whole index, so anything staged earlier — a `git rm` run while tidying, a `git add` from a
previous step — rides along under the next message, and the split has to be rewritten.

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
set, not what changed while you were reading it.

The same holds one step later: before pushing, `git log origin/<branch>..HEAD` — a commit there you
didn't make belongs to another live session, which may still mean to amend or reorder it. Say so and
ask before your push publishes it.

## Bash & tool use

### Composing a Bash call

One command per call. The costs of a chain are harness-side, not just prompts: one call keeps one
whole output and one real exit code, while a chain's `$?` is its last command's and its output is
one blob; and independent calls issued as separate tool-call blocks in one response already run in
parallel, so gluing with `;`/`&&` gains nothing. `echo "=== label ==="` between steps is the tell
that a chain should have been several calls. Exactly one chain shape is fine:
`cd <other repo> && <one command>` for a cross-repo step — and that `cd` sticks: cwd persists into
the following calls on current builds, so a cross-repo chain ends the session's cwd elsewhere until
something moves it back. Never `cd` into the session's own repo as a matter of course — cwd already
is it — but after a cross-repo chain, the next call that assumes the session repo (`inv`, `pytest`,
a bare `rg`) either takes an absolute path or is itself a `cd <session repo> && …`.

Run a gate or test plain — `inv quality.precommit`, `pytest` — not `> log 2>&1; echo $?` with a Read
of the log afterwards. The Bash tool already reports a non-zero exit code on its own, keeps the
whole output, and when output is oversized saves the full text to a file and tells you where. The
redirect form turns one call into two (plus a prompt when the target is a `$VAR` path) and buys
nothing. Redirect only when the log is genuinely needed later, then Grep/Read it as a second call.

### Viewing, searching, or editing files

Prefer the dedicated harness tool over its Bash equivalent: Read over `cat`/`sed -n`/`head`/`tail`,
Grep/Glob over `grep`/`find`, Edit/Write over `sed -i`/heredocs — dedicated tools have their own
permission gate and keep the whole result. Never pipe tool output through `| head`/`| tail` to save
context: the harness already truncates large output and saves the full text to a file, so
pre-truncating only loses data and forces a second run; if size is the worry, count first (`rg -c`,
`wc -l`). That includes a log you did redirect to: Grep/Read _on the log_ as a second call — never
`; rg … log | head` tacked onto the same one. And never append `; echo "EXIT=$?"` to a command — the
tool already reports a non-zero exit, and a bare `$?` after `;` is the previous command's anyway
only because nothing else ran, so it adds a chain for information you already have. When shelling
out to search anyway, use `rg` over `grep -r` and `fd` over `find` (faster, `.gitignore`-aware);
plain `grep`/`find` stay fine for non-recursive lookups, `find -exec`/`-delete`, or portability. Do
not carry `grep -r`'s flag across with the habit: `rg` is recursive by default and its `-r` is
`--replace`, so `rg -r <pat> <path>` silently prints matches with the matched text _rewritten_ —
plausible-looking output that is not what the file says.

### Running a command against a different repo than the session's project

Avoid needing to: keep a session focused on one project — substantial work in another repo belongs
in its own session. For the unavoidable quick cross-repo command:

- Whether cwd persists between Bash calls is not reliable either way: some calls end with the
  harness resetting it to the primary directory ("Shell cwd was reset"), others leave it where a
  `cd` put it — both observed in one session. Assume neither — scope by flag or by a single
  `cd … && …` chain, and after that chain treat cwd as unknown until a call re-establishes it. The
  tell that it stuck: `inv` answering `Can't find any collection named 'tasks'`, or `rg`/`pytest`
  reporting a path that "does not exist" which plainly does.
- Prefer the tool's own directory-scoping option (`git -C <path>`, `ruff --config <path>`,
  `basedpyright --project <path>`, the target repo's own `.venv/bin/pytest` by absolute path —
  site-packages resolve from the interpreter, not cwd). Read-only `git -C` verbs are allowlisted; a
  mutating one (`git -C x commit`/`push`) matches no rule and prompts — that prompt is the
  checkpoint, not friction to route around.
- `inv` is the exception: invoke finds `tasks.py` by walking up from cwd, so no flag redirects it,
  and its tasks shell out to bare tool names (`pytest`, `ruff`, `basedpyright`) that resolve from
  PATH rather than from the `inv` that launched them — an absolute `<repo>/.venv/bin/inv` fixes
  neither. `cd <repo> && PATH="<repo>/.venv/bin:$PATH" inv <task>`, chained in one call, is the
  working form: the `cd` supplies task discovery, the PATH prefix supplies that repo's `inv` and
  every tool underneath it. Expect a prompt — a leading env assignment matches no rule's prefix. A
  repo with no `inv` in its own venv still falls back to `~/.local/bin`, where which of two uv tools
  owns the name varies.
- Never a bare `pytest`/`inv` against another repo: PATH stays the primary project's
  direnv-activated `.venv/bin` (direnv hooks don't fire in non-interactive shells), so the command
  silently runs the wrong repo's interpreter, dependencies, or tasks — and looks like it passed.

### Invoking a venv tool in the session's own project

Check `which <tool>` before prefixing `uv run` or spelling out `.venv/bin/<tool>`: most of this
user's repos put `.venv/bin` on `PATH` via direnv (`.envrc`), so the bare command already resolves
into the venv and a wrapper or absolute path only adds prompt friction. If a repo's `AGENTS.md`
Build & test section is empty or stale, fix it rather than silently working around it.

## Research & design

### About to author content, config, or a workaround from scratch

Check whether an actively-maintained external project already provides it — a `.gitignore`, a rule
set, a template, any reusable artifact — and search properly before concluding it doesn't: "the
first thing I checked didn't have it" and a single internal tool's "nothing relevant" are weak
signals, not conclusions. The same bar applies to designing a new skill or convention (a real
web/GitHub prior-art pass before finalizing). Within one tool, prefer its built-in feature over a
hand-rolled equivalent even when the built-in carries a documented trade-off — unless that trade-off
is _verified_ risky (grep/test for concrete breakage), not just theoretically possible.

### Choosing a tool or library

For a real selection decision with trade-offs, go deeper than a single-pass web-search summary
(actual CLI walkthroughs, real config examples) — or explicitly flag the research as search-summary
depth and offer to go deeper before the choice is treated as final.

Across a project's concerns, default to the best-fit tool per concern rather than consolidating onto
fewer technologies for its own sake (YAGNI still applies to speculative needs). Exception: when the
explicit goal is fewer options for an _agent_ pattern-matching off existing code, fewer routine
defaults wins over specialization.

### About to ask the user something factual

Check whether it has a discoverable answer first — `AskUserQuestion` is for decisions genuinely the
user's to make (a real preference, a trade-off with no objectively better side), not for lookups a
web search resolves, however tempting the quick multiple-choice framing.

### Writing conventions into a shareable skill or template

Apply them to one real, already-working repo first — never straight from research to the shareable
artifact. A pilot surfaces what research can't: rules that are noise against a repo's deliberate
style, and config footguns that would ship to every consumer verbatim.

### Designing a generator or multi-mode tool

Default to independent, combinable axes/flags, each gating a small module, over one top-level enum
branching into near-duplicate trees — ask whether the "modes" are really orthogonal concerns
conflated into one axis. Design the user-facing interaction as a first-class concern: minimal
necessary prompts, skip what doesn't apply, concrete examples in helper text, and first-run output
that doesn't read as a diff against unchosen branches.

### Designing a uv tool-install or shared-dependency mechanism

Two traps: `uv tool install --with-executables-from <dep> <pkg>` only adds _extra_ console scripts
from `<dep>` — a package with zero `[project.scripts]` of its own still fails to install as a tool.
And `dependency-groups` (PEP 735) are per-project, never inherited through a regular dependency — a
shared package that wants consumers to pick up its tool list needs an explicit mechanism (a task
editing the consumer's own `pyproject.toml`, or an optional-dependencies extra).

### Adding a CLI flag

Match the surrounding ecosystem's shape (check the wrapped CLI's own flags too) rather than
inventing a bespoke one. For confirmation prompts that means apt/dnf's: prompt on by default,
`-y`/`--yes` to skip — never an opt-in `--confirm`; `rm -i`'s inverted shape is only for the
genuinely destructive-by-default. And don't add a bypass flag that overrides a marker/manifest the
tool uses to decide what it owns — that gives ownership two meanings, one with the flag and one
without; no hacks that complicate the mental model unless the alternative is utterly impractical.

### Proposing an enforcement mechanism for agent behavior

Skills and instructions are the mainstay of directing agents — to correct a recurring agent
behavior, prefer teaching the agent what to run over a mechanism that fires behind its back (a git
hook, a harness hook, a CI auto-fix bot). Agents get the same standard as developers: they should
know what to run, not be silently corrected.

### Naming around a collision

Use the full, unambiguous canonical name (e.g. "power-user-linux-setup"), not a new compound short
alias (e.g. "pulse-setup") — an alias that half-repeats the disambiguating word reads as awkward,
not clean. Offer a short form only if asked, or where the full name is genuinely unwieldy (an env
var prefix).

## Verification

### Reading a command's result

Clean-looking stdout is not proof of success — the exit code is. The Bash tool reports it whenever
it is non-zero, so a plain unpiped command already gives you the real answer; `echo $?` and
redirect-to-a-log add nothing. What loses it is a pipe: `tail`/`grep` return _their own_ exit code,
so `$?` after a pipeline never reflects the upstream failure, and the tool's exit report is the
filter's too. Assume a CLI's clean summary text and its exit code can disagree until verified
otherwise.

Backgrounding from the shell can leave you reading state from a command that **never ran**. Measured
2026-08-26: `nohup script.sh & disown` and `setsid script.sh &` both returned non-zero while the
script's first statement, a file write, never happened — yet a plain `cmd &` plus `sleep` in the
same call did run. Intermittent is the danger: the next call inspects processes or files as though
the work happened, so the failure yields false evidence rather than an error, and a background write
or delete that silently didn't happen looks exactly like one that did. Use the Bash tool's own
`run_in_background` (it survives across turns and re-invokes you on exit); if something must be
backgrounded anyway, have it write a marker the next call checks before trusting any result.

A wait is only as sound as the value its condition tests, and a filter that can return _nothing_
never satisfies one. Measured 2026-08-28: `gh run list --commit <7-char-sha>` prints `[]` and exits
0 — `--commit` matches only the full 40-char SHA — so `.[0].status` is `null` forever and
`until [ "$(…)" = "completed" ]` can never become true. Four such loops from one session were still
polling 36 hours later, every 15–20s, while the session had already told the user it would report
when CI landed: the loop cannot fail, so it reports nothing, and "still running" and "will never
finish" look identical. Before wrapping anything in a loop, run the inner command once and look at
what it actually returns; bound the wait by an iteration count or deadline, and say so when it
expires. Best is not to hand-roll the loop at all — reach for the purpose-built waiter first:
`gh run watch <run-id> --exit-status` blocks until a run finishes and turns failure into a non-zero
exit (verified 2026-08-28: on an already-finished run it returns at once with the conclusion), and
the run-id comes from `gh run list --branch <branch>`, the filter that actually matches.

### Generalizing from a sample to a set

A clean-looking sample is not evidence about its siblings, and "they're all the same kind of file"
is not evidence either. `--stat`'s per-file line counts are the cheap tell: when they disagree, read
the outliers, not the representative-looking one. This includes samples you created yourself: piping
a search through `| head` when the point of the search was completeness turns the set into a sample
without saying so. Count first (`rg -c`, `| wc -l`) or don't truncate.

### Verifying behavior in a repo with test coverage

Run the test suite, not a one-off ad-hoc script (`python3 -c "..."`, a manual re-render in `/tmp`) —
check whether an existing test, or a trivial addition to one, already covers it. "Slow" or "needs
the network" is not a reason to fall back to a throwaway script: write a real, clearly-labeled test
instead (marked/skipped from the fast default suite per that repo's convention). Genuinely
exploratory prototyping with no natural home in the suite yet stays legitimate, done deliberately
outside the real repo. A green run is only evidence about the code that was actually imported — with
an editable install the package resolves to the working tree, not to whatever you checked out, so
confirm the import path (`python -c "import pkg; print(pkg.__file__)"`) before trusting a per-commit
or per-worktree result.

`tmp_path` sandboxes the working tree, not the user: a test that runs `direnv allow`, `uv tool`,
`inv configure`, or any code path through `Path.home()` writes into the real `$HOME` (direnv's allow
database, `~/.cache/claude-code`, ...) and leaves one stale entry per run. Give such tests a
fake-`HOME` fixture — patch `os.environ` _and_ any library holding its own environment snapshot
(copier runs `_tasks` from plumbum's `local.env`, copied at import; `monkeypatch.setenv` never
reaches it) — and pin `UV_CACHE_DIR` back to the real cache so the run stays warm.

## Collaboration & output

### A narrow check grows into design work

When a "just check/confirm X" request starts revealing design decisions with real trade-offs,
proactively suggest or move into plan mode rather than continuing to edit inline — scope grows one
incremental step at a time and is easy to miss; don't wait for the user to notice. "Implement and
document ..." is clear approval to exit plan mode and execute for real, state-changing commands
included — the caution is editing ahead of an agreed plan, not avoiding real changes once one is
approved.

### Invited to push back

"Push back if you think it doesn't make sense" is a genuine standing invitation, not a rhetorical
courtesy — actually check the proposal for gaps and trade-offs before responding, and say
specifically what doesn't hold up. Agreement is not the safe default while the invitation stands.

### Something the user wrote looks like a typo or mental slip

Flag it and confirm rather than quietly treating it as deliberate or parking it as an open question
for later. Repetition across messages is not proof of intent — it's exactly what a tired slip looks
like too. The tell: a repeated name/term/detail that doesn't match established context (earlier
usage, the actual repo/file on disk, domain convention). Running with a slip costs a real detour
once design work builds on the wrong name.

### Ending a turn with a next step

The user works only through prompts — they never type shell commands themselves — so never close
with "run `git push`" or "you can run X": it hands them a step they can't take. When the work is
done and what happens next is their call (push now, pick the next plan, stop), put the concrete
options in an `AskUserQuestion` and act on the answer. Push/commit still need their say-so; asking
via the tool is how they give it.

### Caveman-style terse output

Respond terse — technical substance stays, fluff dies. Drop articles, filler (just/really/
basically/actually/simply), pleasantries, hedging. Fragments OK. Short synonyms over long phrases.
No tool-call narration, no preamble before or between calls. No decorative tables/emoji. Code blocks
and error messages stay exact, verbatim — never compressed. Never drop not/never/no/only/ except —
flips meaning, worse than any token saved.

Drop this style entirely for security warnings, irreversible-action confirmations, or anywhere
compression would create real ambiguity — write normal prose there, then resume after.

Applies to conversational replies only, not anything that persists outside the chat (code, comments,
commit messages, docs). "stop caveman" / "normal mode" turns it off for the rest of the session.
