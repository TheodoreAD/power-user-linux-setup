# Claude Code — global instructions

## sudo

Always use `sudo -A` (not plain `sudo`). The `SUDO_ASKPASS` environment variable points to
`~/.local/bin/askpass-zenity`, which opens a Zenity GUI dialog for the password. Plain `sudo` fails
because there is no TTY attached to the Bash tool.

```shell
# correct
sudo -A apt install -y something
sudo -A cp /tmp/foo /etc/bar

# wrong — hangs or fails with "sudo: a terminal is required"
sudo apt install -y something
```

## git fetch/push over SSH

`SSH_ASKPASS` (same `askpass-zenity` helper) and `SSH_ASKPASS_REQUIRE=prefer` are set, so a
`git fetch`/`git push` that needs to unlock an SSH key (no key loaded yet in the `keychain`-managed
agent this session) pops the same GUI passphrase dialog instead of failing with "Permission denied
(publickey)". `prefer` only engages the dialog when there's no usable TTY — your own interactive
terminal is unaffected and still prompts normally. Just run the `git` command as normal; no
HTTPS/token workaround needed. The dialog blocks on user input, so if nobody is at the machine to
enter the passphrase it will time out rather than hang forever.

## git push on personal repos

Direct-pushing to `main`/`master` is expected and fine on the user's own personal repos
(`power-user-linux-setup`, `repo-tasks`, `scaffoldapy`, etc.) — sole contributor and repo owner, so
a PR-based workflow doesn't make sense there. This holds even when GitHub reports bypassing a
"changes must be made through a pull request" branch-protection rule on push — that rule exists for
some other purpose (e.g. an accidental force-push guard), not to gate solo work through review.
Don't flag a bypassed-protection-rule push message as something to double check, and don't suggest
routing through a PR instead. Specific to repos where the user is sole owner — a shared/team repo
with real other contributors is a different situation this doesn't transfer to.

## Bash tool discipline: work with the CLI allowlist, not against it

Claude Code's Bash permission rules match on the literal command _prefix_ (`Bash(git status:*)`, see
`power-user-linux-setup`'s `cli-allowlist/` pipeline and `docs/cli-allowlist.md`) — anything that
changes the leading text of the command, even when harmless, produces a string that can no longer
match an already-allowlisted rule and forces an approval prompt.

**Don't `cd` out of the project.** The Bash tool's cwd is already the project root at the start of a
session and stays there as long as nothing changes it, so the default is just to run plain commands
— no path-scoping needed at all. A `cd some/dir && git status` no longer starts with `git status`,
so it can't match `Bash(git status:*)` even though the bare command is already allowlisted. The
working directory persists between Bash tool calls (only shell state resets), so a stray `cd` also
silently breaks matching for every later call in the session, not just the one it was chained onto.

Don't reach for a directory-scoping flag (`git -C path`, `npm --prefix dir`, `docker --context
ctx`,
`kubectl --kubeconfig f`) as a reflexive substitute either — for tools whose allow rules match
`<tool> <subcommand>` as a literal prefix, a flag placed _before_ the subcommand breaks the match
exactly the same way `cd &&` does (`git -C path status` no longer starts with `git status`). Only
reach for one of these when you genuinely need to target a directory other than your current one
(rare — you're normally already at the project root), and even then expect that call not to match an
existing allow rule; the flag isn't a trick to dodge the approval prompt, just a way to avoid
leaving a stray `cd` behind that corrupts every later call. Flat, subcommand-less tools
(`rg`/`fd`/`ls`/...) are unaffected either way — their allow rules match the whole tool
(`Bash(rg:*)`), so a trailing path argument doesn't change the matched prefix.

If a command truly has to run from a different directory and has no scoping flag at all, run the
`cd` as its own Bash call — never chained with `&&` — then the target command as a separate call,
then `cd` back to the project root. Each individual call stays a plain, matchable command (the two
`cd` calls themselves just won't be allowlisted, same one-off cost as above).

**Prefer several simple commands over one complex one.** Don't fuse independent steps into a single
Bash call with `&&`, `;`, `|`, a leading env-var assignment (`VAR=x cmd`), or a
`bash -c "..."`/`sh -c "..."` wrapper just to save a round trip — each produces a novel command
string that can't match an existing allow-rule prefix, so it prompts every time even when every
individual piece is already allowlisted on its own. Issue separate Bash tool calls instead;
independent ones can run in parallel in the same turn anyway. A multi-step pipeline you find
yourself reaching for often is a signal it may be worth its own explicit allowlist entry
(`inv allowlist.review`) rather than eating the prompt indefinitely.

**"Run in parallel" means separate tool-call blocks, not a chained command string.** The harness's
own guidance to maximize parallel tool calls is about issuing multiple independent Bash (or other
tool) invocations in the same response — it is not license to glue them into one command with `;` or
`&&`. Conflating the two is the most common way this rule actually gets broken in practice: two
throwaway read-only lookups (e.g. `rg foo; fd bar`) feel like a single "quick check" and get typed
as one command out of habit, even though each half is independently allowlisted and would incur zero
extra cost as two separate calls. If a second command occurs to you while typing the first, that's
the signal to stop and issue it as its own call, not to append it.

**Prefer a dedicated harness tool over its Bash equivalent whenever it fits, if doing so doesn't
cost significantly more tokens.** Read beats `cat`/`sed -n`/`head`/`tail` for viewing a file or a
line range; Grep/Glob beat `grep`/`find` for searching; Edit/Write beat `sed -i`/heredocs for
changing a file. This isn't only about the allowlist-prefix problem above — a dedicated tool has its
own permission gate entirely separate from the Bash allowlist, so it causes zero prompt friction for
the exact same read/search/edit intent that a shell command would need an allowlist entry for. Reach
for Bash for the read/search/edit trio only when the dedicated tool genuinely can't express what's
needed (e.g. one step of a larger shell pipeline that has to run as a single command for other
reasons, or an operation with no tool equivalent) — not out of habit.

**Built-in `Plan`/`Explore` subagents don't see this file at all.** Claude Code's built-in `Plan`
and `Explore` agent types deliberately skip loading `CLAUDE.md`/`AGENTS.md` (any level — user or
project), to keep research fast and cheap. A rule added here — including every rule in this file —
is invisible to a subagent of either type; it only reaches the main session and any custom subagent
whose own definition doesn't override the system prompt. If a just-established or task-critical
convention actually matters for what you're asking a `Plan`/`Explore` subagent to do (e.g. "use
Read, not `sed -n`, when viewing files"), state it explicitly in that subagent's own prompt — don't
assume it inherits this file.

## Testing a different repo's code in a multi-working-directory session

When a session has more than one working directory (the "additional working directories" the system
prompt lists) and you need to actually run/test code that lives in a _different_ one than the
session's primary project, a plain `cd other-repo && pytest`/`cd other-repo && inv <task>` (as its
own Bash call, per the allowlist guidance above) does **not** put that repo's own `.venv` on `PATH`.
direnv's shell hook fires on an interactive shell's prompt/precmd, not inside a non-interactive
`bash -c` invocation — so PATH stays whatever it already was at session start (the _primary_
project's direnv-activated `.venv/bin`), and a bare `pytest`/`inv` after the `cd` silently resolves
to the primary project's interpreter and dependencies, not the target repo's. Concretely, this means
testing against a stale/wrong package copy (an old pinned git commit, a different version) without
any error — it just runs, and looks like it passed.

The fix: invoke the target repo's own venv binary by absolute path —
`/path/to/other-repo/.venv/bin/pytest`, `/path/to/other-repo/.venv/bin/inv <task>` — rather than
relying on bare-command PATH resolution after a `cd`. Confirmed directly (2026-08-22/23): running
plain `inv`/`pytest` after `cd`-ing into a secondary repo silently exercised the primary repo's
pinned dependency copy of a package under active development in the secondary repo, until switching
to the absolute-path form surfaced the real, current code.

## Preferred search tools

When shelling out via Bash — not the dedicated Grep/Glob tools, which are already preferred by
default and unaffected by this — use `rg` instead of `grep -r`/`grep -R` and `fd` instead of `find`.
Both are installed globally via power-user-linux-setup, both are faster, and both respect
`.gitignore` by default (fewer accidental matches inside `node_modules/`, `.venv/`, build output,
etc.). Plain `grep`/`find` are still fine for a simple non-recursive lookup, inside a pipeline that
specifically needs `find`'s `-exec`/`-delete`, or anything meant to stay portable to a machine
without rg/fd — default to rg/fd otherwise.

## Project conventions

If a repo has (or should have) instructions for AI coding agents, prefer `AGENTS.md` at the repo
root over `CLAUDE.md` — it's the cross-tool convention read by 30+ agents (Claude Code, Cursor,
Copilot, Aider, ...), not just this one. `CLAUDE.md`, if it exists at all, should be a plain
**symlink** to `AGENTS.md` — not a file containing the `@AGENTS.md` import directive. The import
syntax is Claude-Code-specific, so any other harness that also happens to read a literal `CLAUDE.md`
(for compat) would see that text verbatim instead of real instructions; a symlink presents
byte-identical content to every harness with no special-case parsing anywhere. Trade-off worth
knowing: unlike the import form, nothing can be appended below a symlink's target — a genuinely
Claude-specific addendum belongs in `AGENTS.md` itself (shared) or a separate `.claude/`-scoped
file, never a duplicate copy of `AGENTS.md`'s content. This file follows its own rule: `~/AGENTS.md`
is the real content, `~/.claude/CLAUDE.md` symlinks to it, same as this repo's own root.

Skills go in `.agents/skills/` — the emerging cross-tool convention — with `.claude/skills`
symlinked to it so Claude Code actually discovers them (`.agents/skills/` alone isn't read natively
yet). `inv ai.skills` sets this up for `~` and installs every skill declared in `setup.toml` — never
overwrites a file or symlink that's already there. A new Python project's own `AGENTS.md` +
`CLAUDE.md` symlink + `.agents/skills`/`.claude/skills` scaffold comes from
[`scaffoldapy`](https://github.com/TheodoreAD/scaffoldapy) at generation time instead, not from this
machine.

## Cross-session memory

Don't use Claude Code's auto-memory system (`~/.claude/projects/.../memory/`) as a durable store at
all — it's scoped per project directory (a separate `memory/` folder per repo, confirmed 2026-08-22:
`repo-tasks`, `power-user-linux-setup`, `scaffoldapy`, the `*-polite-mcp` repos each have their own,
none shared), so anything saved there is invisible to every other repo's sessions regardless of
whether the content itself is repo-specific or a general cross-repo preference. Treat it as a
**staging area only**, never the final resting place:

- Durable, repo-specific knowledge → that repo's own `AGENTS.md` (or a `docs/*.md` file it points
  to).
- Durable, cross-repo/personal preference (collaboration style, tool defaults, workflow rules that
  apply no matter which repo a session is in) → **this file**, `~/AGENTS.md` — not memory. Same
  underlying reason `AGENTS.md` beats memory for a single repo (reviewable, one source of truth
  instead of N per-project copies) applies just as much across repos as within one.

A memory entry is fine to exist _temporarily_ — mid-session capture of something just learned or
corrected — but once a piece of guidance is clear and general enough to state as a rule, migrate it
into the relevant `AGENTS.md` and delete the memory entry rather than letting it sit there
indefinitely as a second, competing, per-repo-siloed copy of the same instruction.

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

## Commit regenerated artifacts deliberately, don't auto-wire regeneration

When a mechanism regenerates a file from some canonical/shared source (a shared config package, a
template, a pulled dependency), default to **committing the regenerated output** and running
regeneration as its own **deliberate, standalone command** — not gitignoring the output "because
it's reproducible," and not auto-wiring regeneration into commands that run constantly (`pre=` of a
routine `fix`/`check`/`precommit`). Reasons: some CI setups need the file present without an extra
generation step running first; `git blame`/`git log` on the file is how you answer "what config was
actually in effect for this change," impossible if it was never checked in; and silently rewriting a
tracked file as a side effect of routine work (possibly pulling in an upstream bump nobody decided
to take yet) is exactly the kind of surprise this should avoid. Reproducible is not the same
requirement as disposable — regeneration should be intentional, reviewed (diffed), tested, and
committed like any other code change.

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

## Verify what actually happened, not what output looks like

A command's stdout looking clean is not proof it exited zero — always check the real exit code
directly (`command; echo $?`, or redirect to a file first if a pipe is needed for readability, then
check `$?` in a separate unpiped step). `tail`/`grep` in a pipeline return _their own_ exit code,
not the upstream command's, so `$?` right after a piped command never reflects the real failure.
Confirmed concretely: `basedpyright` hard-errors (exit 3) on a config error while still printing a
clean `"0 errors, N warnings, 0 notes"` summary line — a real regression across three repos went
unnoticed for a stretch of a session because every check was read via `... | tail -N`. Assume any
CLI's "clean summary text" and "process exit code" can disagree until verified otherwise.

Once a repo has real test coverage (or a trivial addition would cover it), verify behavior by
running the test suite, not a one-off ad-hoc script (`python3 -c "..."`, a manual re-render in
`/tmp`, etc.) — even for a quick "let me just check this" moment. Check whether an existing test (or
a trivial addition to one) already covers what's being checked before reaching for a throwaway
script. Genuinely exploratory prototyping that has no natural home in the test suite yet (confirming
a brand-new, unproven mechanism works at all) is legitimate throwaway exploration, done deliberately
outside the real repo — but "slow" or "needs the network" is _not_ a valid reason to fall back to a
script for something that already has, or trivially could have, real test coverage; write it as a
real, clearly-labeled test instead (marked/skipped from the fast default suite if genuinely slow,
per that repo's own convention for that).

## This machine's locale silently breaks `date`/`awk` formatting in shell scripts

This machine's `LC_TIME` and `LC_NUMERIC` default to `ro_RO.UTF-8` (while `LANG`/`LC_MESSAGES` stay
`en_US.UTF-8` — a mixed locale, not a uniformly non-English one). Any bash script that formats a
date or a decimal number without forcing the C locale can silently emit Romanian-locale output
instead of the expected English/period-decimal form — with no error, so it passes a casual glance
and only shows up on close inspection of the actual bytes.

**Confirmed concretely** 2026-08-23, twice in one script (`~/.claude/statusline-command.sh`):
`date -d ... '+%a'` returned `"Ma"` (Marți, Tuesday) instead of `"Tue"`, and
`awk '{printf "%.2f",
c}'` rendered `1,23` instead of `1.23`. Both were caught only by piping real
output through `xxd`/ `cat -A` and reading the literal bytes — a rendered terminal glyph or a quick
glance at "does this look like a number" would not have caught either.

**How to apply:** in any bash script (on this machine specifically) that calls `date` with a
locale-sensitive format specifier (`%a`, `%A`, `%b`, `%B`, ...) or `awk`/`printf` with a decimal
format (`%f`, `%.Nf`), force the C locale explicitly — `LC_TIME=C date ...` or
`LC_NUMERIC=C awk
...` — rather than relying on the ambient locale. Don't assume "the terminal looks
fine" is proof of correct output — same underlying lesson as "Verify what actually happened, not
what output looks like" above, applied to locale instead of exit codes.

## Concurrent sessions: check before assuming ownership of unexpected state

This user frequently runs multiple Claude Code sessions in parallel across the same small set of
personal repos (Remote Control, cloud sessions, forks not run with `isolation: "worktree"` sharing a
working tree, etc.). Git/file state that looks unexplained — an untracked file, a diff that doesn't
match anything this session did, a commit you don't recognize — is not necessarily this session's
own leftover work, and not necessarily a background fork/subagent gone out of scope either (a real
possibility, just not the default assumption). It can belong to a different, actively-running
session on the same repo.

**How to apply:**

- When unexplained state turns up, don't assume ownership or a specific culpable cause. Ask
  neutrally ("I see a commit I didn't make — was that you or another session, or should I
  investigate further?") rather than asserting a cause before confirming it.
- If the user identifies something as belonging to a separate session, treat that as fully hands-off
  from then on — don't re-verify it, re-read it, or reference its content further, unless later told
  otherwise.
- Before committing your own changes to a repo that showed any sign of concurrent activity, use
  `git fetch`/`git log origin/<branch>` to check whether the remote has moved since you last looked
  — cheap, and resolves "is this a live conflict or just an earlier commit I hadn't seen yet"
  definitively instead of guessing.
- Still worth surfacing unexpected state before building on top of it — that instinct is right, only
  the assumed cause needs to stay neutral.

## Granular commits, split by logical concern

Split multi-part work into multiple small, single-concern commits rather than one commit per
task/request, even when the user's own instruction was a single ask — this is a standing cross-repo
practice ("as we usually do"), not a one-off. Git history is a resource future agents (not just
humans) rely on to understand _why_ a change happened; a single monolithic commit mixing e.g. a bug
fix, a new feature module, and a doc update makes that history much less useful to bisect or read
later. When staging/committing multi-part work, split by logical unit even if it means several
`git add`/`git commit` cycles: a research/design doc update as its own commit separate from the code
implementing it; a bug fix discovered mid-implementation folded into the commit that introduces the
correct behavior (not committed broken-then-fixed); an unrelated incidental fix (see next section)
as its own tiny commit rather than bundled into unrelated work.

## Keep incidental lint/formatting fixes a quality gate surfaces

When running a repo's own precommit/format/lint gate as part of unrelated work surfaces a formatting
fix to a file you didn't intend to touch, keep the fix (as its own small commit, per above) rather
than reverting it with `git checkout -- <file>` to keep the diff minimal. If the repo's CI enforces
the same formatting check, reverting the fix just guarantees a future CI failure someone else has to
re-discover and fix again later — actively worse than leaving the tiny diff in. Only revert an
incidental change if it's _not_ something the repo's own CI would enforce (a stray content edit, not
a formatting fix) — that distinction is the actual line, not "did I mean to touch this file."

## Check for direnv before reflexively prefixing `uv run`

Before running `uv run <cmd>`, check whether direnv has already put `.venv/bin` on `PATH` (e.g.
`which <tool>` resolving into `.venv/bin/`) instead of reflexively prefixing with `uv run`. Many of
this user's repos use a `.envrc` with `PATH_add .venv/bin`, activated by `direnv allow` or a
`dev-env.setup`-style bootstrap task — once active, the bare command already resolves into the venv
and `uv run` is redundant. Check `which <tool>` or the repo's `.envrc`/`AGENTS.md` before defaulting
to a wrapper prefix. If a repo's `AGENTS.md` Build & test section is empty or stale, that's itself
worth fixing (fill it in / correct it), not just working around silently — these repos' own docs
already have the answer more often than not, if kept current.

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
