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

## Reuse maintained upstream work

Before authoring new content, config, or reference data from scratch — a `.gitignore`, a rule set, a
template, any reusable artifact a design needs — actively check whether an actively-maintained
external/community project already provides it. Don't treat "the first thing I checked didn't have
it" as proof nothing exists; search properly before concluding that.

Validated concretely, not just asserted: designing `.gitignore` ownership for a shared dev-tooling
package (`power-user-linux-setup`'s `repo-tasks`/`scaffoldapy`), checked for prior art before
drafting a Python `.gitignore` in-house — found that PyCharm's own bundled `.ignore` plugin
(`JetBrains/idea-gitignore`) doesn't maintain its own list either: it generates from
`github/gitignore`, GitHub's officially-maintained template repo. A mainstream, widely-used tool had
already made the identical "don't roll your own" call.

Distinct from, and broader than, "prefer a tool's own built-in feature over a hand-rolled workaround
for that same tool" (see "Tool-native over hand-rolled" below) — this is about reusing an external
maintained artifact/dataset instead of authoring new content, not just choosing between two ways of
using one tool.

Same bar applies when designing a new skill or convention, not just content/data: run a real
`WebSearch`/GitHub research pass for prior art before finalizing the design — don't stop at an
internal signal (a `skills find`/repo grep) even when it looks conclusive. Caught live designing
`session-harvest`: an initial internal search surfaced one loosely-related hit and looked like
enough to conclude "nothing fits, build from scratch" — a real web search turned up a much closer
match (`melodykoh/learning-loop-skill`) that meaningfully changed the design. Treat a single narrow
tool's "nothing relevant" as a weak signal, not a conclusion, whenever the task is "build/design X"
and X is a plausible thing others have already built.

## Tool-native over hand-rolled

When two implementation options achieve the same practical outcome — one hand-rolled, one using a
tool's own built-in feature — prefer the tool-native option, even if it carries a documented
trade-off the hand-rolled option would avoid, unless the trade-off is _verified_ risky (grep/test
for concrete breakage), not just theoretically possible. Example: choosing
`uv python install --default` (creates an unversioned `python3` shim that shadows apt's own
`/usr/bin/python3` on `PATH`) over a hand-rolled `python`-only symlink that would have preserved a
"system `python3` never shadowed" invariant byte-for-byte — picked the tool-managed option after
confirming the shadowing risk was theoretical (grepped every `#!/usr/bin/env python3` script on the
system, none needed distro-specific bindings), citing "rule of least surprise" and "a non-managed
symlink is worse than a uv-managed one" (the tool's own shim is understood by
`uv python uninstall`/`--reinstall`/upgrades; a raw `ln -sf` is one more thing to hand-maintain).

## Best tool per concern, not fewer technologies for their own sake

When picking libraries/tools for different concerns in a project (caching, analytics, time-series,
...), default to the best-fit tool for each concern rather than consolidating onto fewer
technologies for its own sake. YAGNI still applies to speculative dependencies for needs that don't
exist yet — this is about not being needlessly consolidation-driven once a real need is already
established.

**Exception:** when the explicit goal is reducing how many options an _agent_ has to choose between
when pattern-matching off existing code — not reducing dependency count or technology diversity —
that goal wins instead. A data-modeling decision table trimmed from six routine choices
(Pydantic/dataclass/attrs/NamedTuple/TypedDict/msgspec) to two (Pydantic for boundaries, frozen
dataclass for everything else) is the concrete instance: "best tool per concern" argues for more
specialized tools, "fewer options for an agent to mimic incorrectly" argues for fewer routine
defaults — these can point opposite ways, and the second wins when the stated audience is
agent-authored code specifically.

## Deep research for real tool/library choices

For a genuine tool/library-selection decision with real trade-offs (not a simple factual lookup), go
deeper than a single-pass web-search summary before presenting a recommendation. Either do a deeper
pass up front (actual CLI walkthroughs, real config file examples, not just doc summaries) or
explicitly flag that the research is search-summary depth and offer to go deeper before the choice
is treated as final. Observed as a real pattern, not a one-off: pushed for more depth twice in one
planning session on a monorepo-versioning tool choice, both times because a search-summary-level
survey wasn't considered sufficient to close out the decision.

## Research before asking, when the answer is factual rather than a real preference

Before reaching for `AskUserQuestion` on something that sounds like a judgment call, check whether
it actually has a discoverable factual answer first — a web search away, not a preference only the
user can supply. `AskUserQuestion` is for decisions genuinely the user's to make (a real preference,
a trade-off with no objectively-better side); a question like "where does model X sit in
capability/cost relative to the others" or "what's a realistic value for Y" is a lookup, not a
preference, even when it's tempting to hand it to the user as a quick multiple-choice.

**Confirmed directly** 2026-08-23: asked the user to pick a color tier for a newly-released Claude
model ("Fable") in a statusline script, framing it as a stylistic choice. The user's reply — "look
it up online, come on" — was a real correction: Fable's actual capability tier (above Opus, per
Anthropic's own docs) was one search away, not something only the user could supply. Re-ran the
research, found the answer, applied it without another round-trip.

## Pilot before generalizing

Before writing a set of tool choices, configs, or conventions into a shareable skill/template meant
to be copied across multiple repos, apply them directly to one real, already-working repo first —
don't go from research straight to the shareable artifact. Piloting researched typing/lint/format
tool choices on one real repo before writing them into a skill surfaced real mistakes pure research
couldn't have caught: a lint rule that was pure noise against that repo's actual deliberate style, a
rule that doesn't fit the repo's shape at all, and two config-file footguns that would have silently
misconfigured every repo that copied the config verbatim. A skill built straight from research, no
pilot step, would have shipped all of these to every consumer.

## Composable design, UX designed first

When building something that will need to support several distinct "kinds" of thing — now or
foreseeably (a scaffolding template, a CLI with growing subcommands, a config generator) — default
to independent, combinable axes/questions/flags, each gating a small module, rather than one
top-level enum/choice that branches into separate near-duplicate trees. Before designing a
generator/template/ multi-mode tool, ask whether the "modes" are really orthogonal concerns being
conflated into one axis; if so, split them so a new kind is a new small module, not a new branch
duplicating everything else.

Design the user-facing interaction as a first-class concern alongside this, not an afterthought:
both the interaction flow itself (minimal necessary prompts, skip whatever doesn't apply, real
concrete examples in helper text rather than an abstract label) and the first-run experience of the
output (nothing that reads as a diff against unchosen branches).

## Naming collisions: prefer the canonical name over a new short alias

When a short/abbreviated name collides with something else, don't invent a new compound short alias
to disambiguate (e.g. "pulse-setup" for a `~/.config/pulse` clash with PulseAudio). Use the full,
unambiguous canonical name instead (e.g. "power-user-linux-setup") — a short alias that half-repeats
the disambiguating word reads as awkward rather than clean. Offer the short form only if asked, or
if the full name is genuinely too unwieldy for the context (e.g. an env var prefix).

## CLI flag conventions: match the ecosystem, don't invent a bespoke shape

When a CLI task needs a flag that controls whether it prompts before doing something impactful,
default to the apt/dnf/`skills`-CLI convention: prompt is on by default, `-y`/`--yes` skips it and
proceeds. Don't invent a bespoke opt-in flag (e.g. `--confirm`) that defaults to _not_ prompting and
requires a flag to turn prompting _on_ — the less common, more surprising shape. Before adding a
flag like this, check whether the surrounding ecosystem (or a wrapped CLI's own flags in the same
file) has a standard for it. `rm`'s `-i` (opt-in prompting, off by default) is the well-known
exception to the apt/dnf shape — don't reach for that pattern unless the task is genuinely
destructive-by-default the way `rm` isn't.

## Move to a written plan once scope grows past a narrow check

When a "just check/confirm X" request starts revealing design decisions with real trade-offs (not
just a one-line fix), proactively suggest or move into Plan Mode rather than continuing to edit
files inline — don't wait for the user to notice scope creep and stop you. Growing scope organically
during investigation is easy to miss as a transition point: each individual step feels incremental,
but the sum can be a multi-file change with real trade-offs the user hasn't seen yet. This user does
treat "implement and document..." as clear approval to exit plan mode and execute for real,
including state-changing commands — the caution is about not editing ahead of an agreed plan, not
about avoiding real system changes once a plan is approved.

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

## Genuine pushback is a standing invitation, not a courtesy

When this user proposes a non-trivial design/refactor and says "push back if you think it doesn't
make sense" (or similar), treat it as a genuine standing invitation, not a rhetorical courtesy —
actually evaluate the proposal and voice disagreement if warranted, rather than defaulting to
agreement. Spend a beat actually checking for gaps/tradeoffs before responding, and say so
explicitly — with the specific reason — if something doesn't hold up. Don't treat agreement as the
safe default when this invitation is on the table.

## Flag apparent typos and mental slips, don't quietly treat them as deliberate

When something the user writes looks like it could be a typo or an unintentional mental slip — not a
deliberate ambiguity — flag it directly and ask/confirm rather than quietly accepting it as
intentional or cataloging it as an open question to decide later. Repetition across multiple
messages is not proof of intent — repetition is exactly what a tired mental slip looks like too.
Concrete instance: a name used consistently across two messages while designing a naming convention,
read as a deliberate choice and written into a plan doc as a genuine undecided design fork — it was
actually a slip, and the user had to correct it explicitly: "remember to push back on typos and
apparent mental slips. people, unlike machines, get tired and their brains connect the wrong things
despite good intentions." When a name/term/detail is repeated but doesn't match established context
(used differently earlier in the conversation, doesn't match the actual repo/package/file on disk,
isn't standard for the domain), ask a quick clarifying question rather than running with it —
silently running with a slip costs a real detour once design work gets built around the wrong name.

## Caveman-style terse output

Respond terse — technical substance stays, fluff dies. Drop articles, filler (just/really/
basically/actually/simply), pleasantries, hedging. Fragments OK. Short synonyms over long phrases.
No tool-call narration, no preamble before or between calls. No decorative tables/emoji. Code blocks
and error messages stay exact, verbatim — never compressed. Never drop not/never/no/only/ except —
flips meaning, worse than any token saved.

Drop this style entirely for security warnings, irreversible-action confirmations, or anywhere
compression would create real ambiguity — write normal prose there, then resume after.

Applies to conversational replies only, not anything that persists outside the chat (code, comments,
commit messages, docs). "stop caveman" / "normal mode" turns it off for the rest of the session.
