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
yet). `inv ai.skills` sets this up for `~`; `inv ai.init [--dir PATH]` scaffolds a full project
(`AGENTS.md` + the `CLAUDE.md` symlink + the skills symlink) — both from the power-user-linux-setup
repo. Neither ever overwrites a file or symlink that's already there.

## Cross-session memory

Don't use Claude Code's auto-memory system (`~/.claude/projects/.../memory/`) for durable,
repo-specific knowledge — put it in that repo's `AGENTS.md` (or a `docs/*.md` file it points to)
instead. Reasons: `AGENTS.md` is version-controlled, visible to every contributor and every agent
tool (not just Claude), and reviewable in diffs — auto-memory is none of those. Personal, cross-repo
preferences (not tied to one project) are still fine to keep in memory.

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
