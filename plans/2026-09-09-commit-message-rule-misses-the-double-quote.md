---
status: idea
updated: 2026-09-09
source_repo: github.com-personal/agent-skills
source_session: 70e28d42-9a4b-4f09-8f22-19112ce49d1b.jsonl
source_moment: 2026-09-09T20:05:00Z
---

# The commit-message rule names the two characters that execute and misses the one that truncates

## Context

`~/AGENTS.md`, "About to commit", says: **write the message without backticks or `$`**, because both
are live inside a double-quoted shell argument. The reasoning is right and the two characters it
names are the two that make the shell _run_ something.

The double quote is live in that same argument for a different reason: it **ends** it. Everything
after it becomes further shell words, so the commit lands with a message truncated at that point and
the shell then fails on the remainder. The rule does not mention it, and a message quoting a phrase
is an entirely ordinary thing to write — more ordinary than one containing a backtick.

## Evidence

This session, `agent-skills`, 2026-09-09. A double-quoted `-m` argument whose message contained the
phrase `absorb's own report said "the removals" in the plural` — the inner quotation marks around a
two-word phrase being quoted from another tool's output. What happened:

- The commit **landed** as `7f30f0b`, message ending mid-sentence at `absorb's own report said the`.
- The shell then reported, after the commit:
  `(eval):15: file name too long: removals in the plural one line above the command that could not
  do it,\nand now points at the form that can.\n\n...`
- Exit code 127, so the Bash tool surfaced it — but the failure is reported **after** a successful
  commit, which is the part that makes it easy to misread as a failed commit needing a retry.
- Recovered by `git commit --amend` with the phrase unquoted, after `git rev-parse HEAD` confirmed
  HEAD had not moved. New SHA `4002efd`.

The distinctive phrase to find the moment in the transcript is "file name too long".

### A second instance, and it refutes the claim below that the commit succeeds

`power-user-linux-setup`, session `b494b3ef`, 2026-09-09T23:1x — independently, about three hours
later, and found by a harvest rather than by looking for it. Same cause, opposite outcome. The
message quoted a phrase as `a prune deciding "still ours?" from the registry alone`. What happened:

- **Nothing was committed.** Exit 1, working tree untouched, no SHA.
- The shell reported
  `(eval):1: no matches found: ours? from the registry alone would have deleted every agent's…`

The difference is entirely in what follows the closing quote. Their remainder contained a `/`, so
zsh tried it as a path and reported `file name too long` **after** git had already run. Mine
contained a `?`, so zsh tried to glob it, found no match, and **refused to run the command at all**
— `nomatch` is on by default in zsh and aborts before execution.

So the section below is right that a landed truncated commit is the nastier case, and wrong that it
is the case. **Which of the two you get depends on the punctuation in your own sentence**, which is
not something an author can reason about while writing prose. That makes the rule stronger rather
than weaker: the failure is not "the commit lands truncated", it is "the shell reinterprets the rest
of your paragraph, and what it does next depends on the characters in it".

One thing both instances share, and it is the practical tell: **the error quotes your own prose
back**, so neither reads as a quoting problem. Recovery differs — theirs needed `--amend` after
checking `HEAD`, mine needed only a reworded retry, and knowing which you are in means checking
whether a commit happened before doing anything else.

### A third instance, thirty minutes later, and this one raises no error at all

Same session `b494b3ef`, 2026-09-10T00:02. Written **while filing the two instances above**, which
is the part worth keeping: knowing the hazard exactly did not prevent it, because this variant is
not the one being watched for. The message was single-quoted to avoid the double-quote problem — and
then the pathspec form was appended from muscle memory, still carrying its own double quote:

```
git commit -m 'plans: sample 18 …
Co-Authored-By: …' -- plans/2026-09-02-….md
```

The `"` before `--` opened a quoted span rather than closing one, so `-- <path>` never became a
pathspec. It became **message text**. The commit landed, **exit 0, no error printed**, one file
changed, and `git log` showed a message ending
`…<noreply@anthropic.com>" -- plans/2026-09-02-agents-md-adherence-sample-corpus.md`.

**This is the silent one.** The first instance errored after committing; the second refused to run.
This produced no diagnostic whatsoever — the only reason it was caught is that this session had just
written two paragraphs about quoting and checked `git log -1` on principle. Amended before pushing.

So the family is three shapes now, and the ordering is the useful part: **a quote in the message can
abort, truncate, or silently append shell syntax, and the silent case is the one produced by trying
to avoid the other two.** It also widens the rule's target — the hazard is not "characters inside
the message" but "the quoting of the whole `-m` argument, including what follows it".

## Why this is worth a clause rather than being obvious

Three things make it different from the backtick case the rule already covers:

- **The commit may succeed** — see the second instance above, where it did not. A backtick
  substitutes before git sees the argument, so what lands is wrong but complete. A stray double
  quote can land a **correct prefix** of the intended message, which reads as a finished commit in
  `git log` if it happens to break at a sentence boundary; or it can abort before git runs at all.
  Two instances, one of each, and the punctuation after the closing quote is what decides.
- **The error names a fragment of your own prose**, not a shell construct, so it does not read as a
  quoting problem. `file name too long: <the rest of your paragraph>` looks like something went
  wrong with a path.
- **The prose that triggers it is the prose the body rules encourage.** The body is supposed to say
  what a rule's wording was and what it beat, and quoting the wording is the natural way to do that
  — the same instinct that produced the user's own quoted corrections throughout `~/AGENTS.md`.

[PITFALL: the natural fix — reach for `-F <file>` — is the one the same section already refuses,
because it hides the message from the approval prompt. The rule's own escape hatch is "reach for
`-F` only when the message genuinely must contain a backtick", and a quoted phrase does not
qualify.]

## Open questions

[NEEDS CLARIFICATION: is the answer a third forbidden character, or a switch to single-quoting the
`-m` argument? Single quotes make backticks, `$` **and** double quotes all inert in one move, and
this session used them for every commit after the failure with no trouble. Against: an apostrophe
then breaks the argument instead, and apostrophes in English prose are far commoner than double
quotes — so it may trade a rare failure for a frequent one. Worth counting apostrophes versus
quotation marks across the last month of commit messages before choosing.]

[NEEDS CLARIFICATION: should this be a `session-bash-audit` pattern rather than only a rule? A
`git commit -m` argument containing an unescaped quote character of the wrong kind is mechanically
detectable, and the existing plan `2026-09-04-session-rule-adherence-evidence.md` in `agent-skills`
already proposes exactly this for the `$` half — under "3. `$` in a commit message — a second
candidate, and it fails loudly", with a `${{` instance from 2026-09-04. That makes two instances of
one shape, so the two belong in one pattern rather than two.]

[NEEDS CLARIFICATION: does the same hazard reach the other double-quoted bodies the section names —
`gh pr create --body`, `gh issue comment`? Structurally yes, and the consequence there is worse than
a truncated commit: a PR body or an issue comment is published at the moment it is created, so a
truncated one is visible to whoever is reading the PR before anyone notices. Not observed, so it is
reasoning rather than evidence.]

## Recommended direction

Add the double quote to the sentence that already names backticks and `$`, and say what is different
about it — that the commit lands truncated rather than failing, which is why it needs naming at all.
One clause, in the fragment under `config/agents-md/` that owns "About to commit".

Then decide the audit-pattern question with the `$` instance rather than separately: one pattern
covering "a quoting character loose in a `-m` argument" is one row, and it is the only row in that
skill's set with a hard failure attached, so a measured rate also says how many commits were lost to
it.
