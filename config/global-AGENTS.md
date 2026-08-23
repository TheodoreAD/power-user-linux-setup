# Claude Code — global instructions

Before changing this file: it is deployed from `config/global-AGENTS.md` in
`~/projects/github.com-personal/power-user-linux-setup` (redeploy: `inv tools.install`) — edit
there, never here, and first read that repo's `contributing/global-agents-md.md`: it holds each
rule's evidence and the admission criteria a new rule must pass.

Built-in `Plan`/`Explore` subagents never load this file — Claude Code deliberately skips
`CLAUDE.md`/`AGENTS.md` (every level) for those agent types. Every rule below reaches only the main
session and custom subagents whose definitions don't override the system prompt; when a rule here
matters for a `Plan`/`Explore` task, restate it in that subagent's own prompt.

## This machine & the harness

### sudo

Always `sudo -A`, never plain `sudo` — `SUDO_ASKPASS` points at `~/.local/bin/askpass-zenity`, a
Zenity GUI password dialog, and plain `sudo` fails because the Bash tool has no TTY.

```shell
sudo -A apt install -y something   # correct
sudo apt install -y something      # wrong — hangs or "sudo: a terminal is required"
```

### git fetch/push needing an SSH key

Run the `git` command as normal — `SSH_ASKPASS` (same Zenity helper, with
`SSH_ASKPASS_REQUIRE=prefer`) pops a GUI passphrase dialog when no key is loaded in the
`keychain`-managed agent, instead of failing with "Permission denied (publickey)". No HTTPS/token
workaround needed. The dialog blocks on user input and times out if nobody is at the machine.

### Editing `~/.claude/settings.json` (or similar) in auto mode

Use the Edit tool, not a Bash-invoked script: auto mode's background classifier reviews every Bash
call with no interactive prompt for a user approval to land on, and denies edits to
self-referential/sensitive files outright even when the user has approved them — Edit goes through a
separate permission path that isn't blocked. If Edit is also blocked, stop and ask the user rather
than hunting for another scripted workaround.

### Setting up a repo's agent instructions and skills

`AGENTS.md` at the repo root is the real file — the cross-tool convention read by 30+ agents.
`CLAUDE.md`, if present at all, is a plain **symlink** to it, never a file containing the
`@AGENTS.md` import directive (Claude-Code-specific syntax other harnesses would read as literal
text); `~/AGENTS.md` itself follows this, with `~/.claude/CLAUDE.md` symlinking to it. Nothing can
be appended below a symlink's target, so a genuinely Claude-specific addendum goes in `AGENTS.md`
itself or a separate `.claude/`-scoped file. Skills live in `.agents/skills/` with `.claude/skills`
symlinked to it; `inv ai.skills` sets this up for `~` (never overwriting existing content), and a
new Python project's own scaffold comes from
[`scaffoldapy`](https://github.com/TheodoreAD/scaffoldapy) at generation time.

### Saving to cross-session memory

Claude Code's auto-memory (`~/.claude/projects/.../memory/`) is a staging area only, never a durable
store — it's siloed per project directory, so anything left there is invisible to every other repo's
sessions. Durable repo-specific knowledge → that repo's own `AGENTS.md` (or a `docs/*.md` it points
to); durable cross-repo/personal preference → `~/AGENTS.md`. Once a piece of guidance is clear and
general enough to state as a rule, migrate it and delete the memory entry.

### Designing a uv tool-install or shared-dependency mechanism

Two traps: `uv tool install --with-executables-from <dep> <pkg>` only adds _extra_ console scripts
from `<dep>` — a package with zero `[project.scripts]` of its own still fails to install as a tool.
And `dependency-groups` (PEP 735) are per-project, never inherited through a regular dependency — a
shared package that wants consumers to pick up its tool list needs an explicit mechanism (a task
editing the consumer's own `pyproject.toml`, or an optional-dependencies extra).

## Git & commits

### Pushing to a personal repo's default branch

Direct pushes to `main`/`master` are the norm on the user's own personal repos
(`power-user-linux-setup`, `repo-tasks`, `scaffoldapy`, ...) — sole contributor and owner, so PR
review gates nothing. A "bypassing branch protection" message on push is expected there (the rule is
a force-push guard, not a review gate) — don't flag it and don't suggest a PR. None of this
transfers to a shared/team repo with real other contributors.

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

### Regenerating a file from a canonical source

Commit the regenerated output, and run regeneration as its own deliberate standalone command — never
gitignored as "reproducible," never auto-wired into routine `fix`/`check`/`precommit` runs.
`git blame`/`git log` on the output is how "what was actually in effect" gets answered, and routine
work silently pulling in an upstream bump nobody chose to take is exactly the surprise to avoid.
Regeneration is reviewed, tested, and committed like any other change.

### Unexplained git/file state in a working tree

This user runs parallel sessions on the same repos, so an unrecognized commit, diff, or untracked
file may belong to another live session — don't assume it's yours, a subagent's, or any specific
cause; surface it and ask neutrally before building on it. Once the user assigns it to another
session, it's fully hands-off — don't re-read or reference it further. Before committing to a repo
that showed concurrent activity, `git fetch` and check `git log origin/<branch>` to see whether the
remote moved.

## Bash & the CLI allowlist

Bash permission rules match on the literal command prefix (`Bash(git status:*)` — generated by
`power-user-linux-setup`'s `cli-allowlist/` pipeline), evaluated per subcommand: a chained command
is split on `&&`/`;`/`|`/newlines and each piece must match a rule on its own. An approval prompt is
a friction cost, never a prohibition — when a rule in this section conflicts with completing real
work, pay the prompt and do the work; only correctness and safety reasons block.

### Composing a Bash call

Prefer several simple calls over one fused command: independent commands issued as separate
tool-call blocks in one response run in parallel anyway — "run in parallel" never means gluing them
with `;`/`&&`. A `bash -c`/`sh -c` wrapper always prompts (the outer `bash` is itself gated), and a
leading env-var assignment (`VAR=x cmd`) produces a string no rule's prefix matches — avoid both
unless the step genuinely needs them. A pipeline you reach for often is a candidate for its own
allowlist entry (`inv allowlist.review`), not a prompt to keep paying.

### Viewing, searching, or editing files

Prefer the dedicated harness tool over its Bash equivalent: Read over `cat`/`sed -n`/`head`/`tail`,
Grep/Glob over `grep`/`find`, Edit/Write over `sed -i`/heredocs — dedicated tools have their own
permission gate, so the same intent causes zero prompt friction. When shelling out to search anyway,
use `rg` over `grep -r` and `fd` over `find` (faster, `.gitignore`-aware); plain `grep`/`find` stay
fine for non-recursive lookups, `find -exec`/`-delete`, or portability.

### Running a command against a different repo than the session's project

Avoid needing to: keep a session focused on one project — substantial work in another repo belongs
in its own session. For the unavoidable quick cross-repo command:

- cwd does not persist between Bash calls — the harness resets it to the session's primary directory
  after every call, so a standalone `cd` accomplishes nothing.
- Prefer the tool's own directory-scoping option (`git -C <path>`, `ruff --config <path>`,
  `basedpyright --project <path>`, the target repo's own `.venv/bin/pytest` by absolute path —
  site-packages resolve from the interpreter, not cwd) and expect a one-off prompt.
- `inv` is the exception: invoke finds `tasks.py` by walking up from cwd, so no flag redirects it —
  `cd <repo> && <repo>/.venv/bin/inv <task>`, chained in one call, is the only working form. The
  `cd` supplies task discovery; the absolute venv path supplies the right dependencies and dodges
  the ambiguity of bare `inv` (which of two uv tools owns it varies).
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
hand-rolled equivalent even when the built-in carries a documented trade-off — unless that
trade-off is _verified_ risky (grep/test for concrete breakage), not just theoretically possible.

### Choosing a tool or library

For a real selection decision with trade-offs, go deeper than a single-pass web-search summary
(actual CLI walkthroughs, real config examples) — or explicitly flag the research as search-summary
depth and offer to go deeper before the choice is treated as final.

Across a project's concerns, default to the best-fit tool per concern rather than consolidating
onto fewer technologies for its own sake (YAGNI still applies to speculative needs). Exception:
when the explicit goal is fewer options for an _agent_ pattern-matching off existing code, fewer
routine defaults wins over specialization.

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

### Adding a CLI flag

Match the surrounding ecosystem's shape (check the wrapped CLI's own flags too) rather than
inventing a bespoke one. For confirmation prompts that means apt/dnf's: prompt on by default,
`-y`/`--yes` to skip — never an opt-in `--confirm`; `rm -i`'s inverted shape is only for the
genuinely destructive-by-default. And don't add a bypass flag that overrides a marker/manifest the
tool uses to decide what it owns — that gives ownership two meanings, one with the flag and one
without; no hacks that complicate the mental model unless the alternative is utterly impractical.

### Naming around a collision

Use the full, unambiguous canonical name (e.g. "power-user-linux-setup"), not a new compound short
alias (e.g. "pulse-setup") — an alias that half-repeats the disambiguating word reads as awkward,
not clean. Offer a short form only if asked, or where the full name is genuinely unwieldy (an env
var prefix).

## Verification

### Reading a command's result

Clean-looking stdout is not proof of success — check the real exit code (`command; echo $?`, or
redirect to a file and check `$?` in a separate unpiped step). A piped `tail`/`grep` returns _its
own_ exit code, so `$?` after a pipeline never reflects the upstream failure. Assume a CLI's clean
summary text and its exit code can disagree until verified otherwise.

### Generalizing from a sample to a set

A clean-looking sample is not evidence about its siblings, and "they're all the same kind of file"
is not evidence either. `--stat`'s per-file line counts are the cheap tell: when they disagree,
read the outliers, not the representative-looking one.

### Verifying behavior in a repo with test coverage

Run the test suite, not a one-off ad-hoc script (`python3 -c "..."`, a manual re-render in `/tmp`)
— check whether an existing test, or a trivial addition to one, already covers it. "Slow" or "needs
the network" is not a reason to fall back to a throwaway script: write a real, clearly-labeled test
instead (marked/skipped from the fast default suite per that repo's convention). Genuinely
exploratory prototyping with no natural home in the suite yet stays legitimate, done deliberately
outside the real repo.

### Formatting a date or decimal in a shell script

This machine's `LC_TIME`/`LC_NUMERIC` default to `ro_RO.UTF-8` (mixed locale — `LANG`/`LC_MESSAGES`
stay `en_US.UTF-8`), so `date` with a locale-sensitive specifier (`%a`, `%b`, ...) or
`awk`/`printf` with a decimal format silently emits Romanian-locale output. Force the C locale —
`LC_TIME=C date ...`, `LC_NUMERIC=C awk ...`. "The terminal looks fine" is not proof — verify the
actual bytes.

## Collaboration & output

### A narrow check grows into design work

When a "just check/confirm X" request starts revealing design decisions with real trade-offs,
proactively suggest or move into Plan Mode rather than continuing to edit inline — scope grows one
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

### Caveman-style terse output

Respond terse — technical substance stays, fluff dies. Drop articles, filler (just/really/
basically/actually/simply), pleasantries, hedging. Fragments OK. Short synonyms over long phrases.
No tool-call narration, no preamble before or between calls. No decorative tables/emoji. Code
blocks and error messages stay exact, verbatim — never compressed. Never drop not/never/no/only/
except — flips meaning, worse than any token saved.

Drop this style entirely for security warnings, irreversible-action confirmations, or anywhere
compression would create real ambiguity — write normal prose there, then resume after.

Applies to conversational replies only, not anything that persists outside the chat (code,
comments, commit messages, docs). "stop caveman" / "normal mode" turns it off for the rest of the
session.
