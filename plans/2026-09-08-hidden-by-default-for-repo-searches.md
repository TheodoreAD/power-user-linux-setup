---
status: landed
updated: 2026-09-12
source_repo: github.com-personal/repo-tasks
source_session: e0a0f092-e55e-4429-95e5-1882a6b773be.jsonl
source_moment: 2026-09-08T00:00:00Z
---

# Should `fd`/`rg` search hidden paths by default, and let `.gitignore` do the excluding?

## Context

Raised by the user 2026-09-08, in their own words:

> when using for repo searches, fd and rg should probably include hidden directories, and rely on
> gitignore to avoid files that shouldn't be worked on, although i realize it might be easier said
> than done.

`~/AGENTS.md`'s "Viewing, searching, or editing files" rule currently treats hidden-path exclusion
as a **reactive** fix: it names `-H`/`-I`/`-HI` and says "a `fd` that comes back empty on a file you
are sure exists wants those flags". That only helps an agent who already suspects the answer is
wrong. The proposal is to invert it — search hidden by default, and let `.gitignore` carry the
exclusion it is already carrying.

**This is a sibling of
[`2026-08-29-fd-clause-adherence-and-search-tool-pricing.md`](2026-08-29-fd-clause-adherence-and-search-tool-pricing.md),
not a replacement for it.** That plan asks whether agents reach for `fd` at all (measured 60%); this
asks what `fd` and `rg` should do once reached for. They touch the same paragraph of the same rule,
so whoever rewords it should hold both — and that plan's `[PITFALL:]` about `fd` silently returning
zero is the specific symptom this proposal generalises.

## Evidence: the immediate trigger

Same session, measuring `actions/checkout` pins across the family.
`rg 'uses: ' <scaffoldapy>/template` returned **nothing**, while `template/.github/workflows/ci.yml`
sat right there — `.github` is a dot-directory. An empty result reads exactly like "already clean",
and that repo's template is the single highest-leverage workflow site in the family. It was caught
only because the count disagreed with a `fd` listing run moments later.

Session `e0a0f092-e55e-4429-95e5-1882a6b773be.jsonl` under
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-repo-tasks/`. The distinctive
phrase to search that transcript for is "rg skips dot-directories by default".

## Measured 2026-09-08, in `repo-tasks`

The whole question turns on what `--hidden` actually costs, so it was measured rather than reasoned
about. File counts, same tree, same moment:

| invocation                       | files     | `.git/`      | gitignored (`.venv/`) |
| -------------------------------- | --------- | ------------ | --------------------- |
| `rg --files`                     | 130       | excluded     | excluded              |
| `rg --files --hidden`            | **3319**  | **INCLUDED** | excluded              |
| `rg --files --hidden -g '!.git'` | 144       | excluded     | excluded              |
| `fd -t f .`                      | 130       | excluded     | excluded              |
| `fd -t f -H .`                   | **144**   | excluded     | excluded              |
| `fd -t f -HI .`                  | **17081** | included     | **INCLUDED**          |

**The user's intuition holds, and the cost is 14 files.** Everything `--hidden` adds to a
correctly-spelled search is something you would want searched:

```
.claude/settings.json  .dockerignore  .editorconfig  .envrc  .gitignore  .python-version
.github/workflows/{ci,docker-release,publish,release,security,security-reusable}.yml
```

`.gitignore` does the rest of the work exactly as proposed — `.venv/` stays excluded under
`--hidden`, because it is ignored rather than merely hidden.

### The trap is narrower than it looks: skipped on **descent**, searched when **named**

Measured after the table above, and it changes what the rule should say. Both tools skip a hidden
path only while walking into it from a non-hidden ancestor. Name it — or name a file inside it — and
no flag is needed:

| command                                                    | result                                      |
| ---------------------------------------------------------- | ------------------------------------------- |
| `rg -c 'uses: ' <template>` (descends)                     | **nothing**                                 |
| `rg -c 'uses: ' <template>/.github` (names the hidden dir) | 3 files, 6 matches                          |
| `rg -c 'uses: ' <template>/.github/workflows/ci.yml`       | 2 matches                                   |
| `fd --type f . <template>` (descends)                      | 37 files, the 3 under `.github` **missing** |
| `fd --type f . <template>/.github` (names it)              | 3 files                                     |

So the failure needs **both** conditions: a hidden component, _and_ an ancestor being walked. That
is exactly the shape of the trigger above — `rg 'uses: ' <template>` — and it is why the miss is
silent: the command is well-formed, the path exists, and the tool is behaving as documented.

[PITFALL: **this makes the anti-pattern close to unmeasurable from a transcript**, which matters
because the sibling plan's step 1 established the precedent of adding a `session-bash-audit` row
before rewording anything. A row cannot be written here: `rg foo src/` and
`rg foo <dir-with-hidden-children>/` are the same string, and whether the answer was under a
dot-directory depends on a tree the transcript does not contain. Confirmed 2026-09-08 that
`session-bash-audit` has no such row and that the existing rows (`find-not-fd`, `rg-replace`, …) all
key on command _text_, which is sufficient for them and is not sufficient here. **The
audit-row-first sequencing does not transfer to this rule** — which is an argument for changing the
wording on its own evidence, not an argument for doing nothing.]

### The catch, and it is a real one: the two tools are not symmetric

**`fd -H` is already safe. `rg --hidden` is not.** `fd`'s own `--help` states it has "the default
rule that excludes `.git/`", and `fd -t f -H .` returns zero paths under `.git/`. `rg` has no such
rule, so `--hidden` walks `.git/objects` and the file count goes 130 → 3319 — a **25× blow-up**,
essentially all loose objects, which are binary and will mostly be skipped for matching but are all
walked and stat'd.

So the honest form of the proposal is not one rule but two:

- `fd -H` — safe as written, nothing further needed.
- `rg --hidden --glob '!.git'` — the `.git` exclusion is **not** optional, and `.gitignore` will
  never supply it, because git does not ignore its own directory. It is not part of the worktree at
  all.

[PITFALL: **`-I`/`--no-ignore` is the dangerous flag, not `-H`, and the current rule pairs them.**
`~/AGENTS.md` recommends `-HI` "for a target that is both", which is right for a targeted lookup of
a known-ignored file and is badly wrong as a default: `fd -t f -HI .` returns **17081** files here
against 144 for `-H`, because it disables `.gitignore` — the very mechanism this proposal wants to
rely on. Any reword must keep `-H` and `-I` clearly apart; today they appear as a pair.]

## Answered (2026-09-12)

**Rule, not configuration — and the two questions collapse into one answer.** `RIPGREP_CONFIG_PATH`
is parked rather than refused. It fails the least-surprise rule this corpus already states: a config
file changes `rg` for the human, for every script on the machine and for every agent, invisibly, so
`rg foo` behaves differently here than in its own documentation with nothing at the call site saying
so — the same objection this corpus makes to harness hooks firing behind the agent's back. That `fd`
has no config lever at all, so no uniform mechanism was ever available, only confirms the choice; it
was not what decided it. Reconsider if the reword is measured and does not hold.

**`--glob '!.git'` unanchored is correct, re-measured on two repos 2026-09-12.** All six `.github/`
files survive it and nothing under `.git/` leaks, because the glob matches the path component rather
than a prefix. `'!.git/'` gives an identical count, so the trailing slash is optional rather than
load-bearing — worth knowing only so nobody adds it thinking it is a fix.

**The `Grep`/`Glob` half is handed to
[`2026-09-05-grep-glob-preference-is-inoperative.md`](2026-09-05-grep-glob-preference-is-inoperative.md)**,
which owns the mode question that blocks it. It was unmeasurable for the third time from this
session, for the same reason as the first two: auto mode withdraws both tools. That plan's own 96%
figure also resizes the question — the harness tools are absent from almost every call that would
exercise them — so the reword ships scoped to the Bash spellings and says so in as many words.

## Recommended direction

Rough, and the measurement above is the part worth keeping whichever way the questions go.

Start with the **rule**, not the configuration, for the reason the sibling plan already established:
reword first and alone, so the next reading attributes to one cause. The reword is small and mostly
already half-present — `-H` is named, it just needs promoting from "what to try when a search comes
back suspiciously empty" to "what a repo search is", with `rg`'s `.git` caveat stated because it is
the one thing that makes the naive version bad.

Three things to carry into that wording, all measured above rather than assumed: **`-H` and `-I` are
not a pair** and pairing them is what makes the safe flag look expensive; **`fd` needs no `.git`
exclusion while `rg` does**, so a single sentence covering both tools will be wrong about one of
them; and **the miss happens on descent, not on naming**, which is the cheapest thing to teach
because it gives the reader a second remedy that costs no flag at all — if you know the path holds a
dot-directory, name it.

That third point is what makes the reword small. The rule does not have to say "always pass
`--hidden`"; it has to say **a search that walks a tree cannot see into `.github`, `.claude` or any
other dot-directory unless you say so** — and then give the two ways out. Stated that way it is a
fact about the tools rather than a house style, which is the shape that has held at 94.5% for the
`rg`-over-`grep` clause next to it.

Hold the `RIPGREP_CONFIG_PATH` option until the reword has been measured. It is the stronger lever
and the harder one to undo, it changes behaviour for the human as well as the agent, and the sibling
plan's whole sequencing argument is that a wording change and a mechanism change made together
cannot be told apart afterwards.

The `rg -rln` instance this plan was carrying — unrelated to hidden paths, kept here only so it
would not be lost — has been moved to
[`2026-09-02-rg-replace-flag-used-twice-in-one-session.md`](2026-09-02-rg-replace-flag-used-twice-in-one-session.md)
as its tenth occurrence, which is the clause that owns it.

## Migrated to

- `config/agents-md/bash.md`, the `fd` clause — `-H` promoted from a reactive fix to the default
  posture, `-H` and `-I` separated with their measured costs, `rg`'s non-optional `.git` exclusion
  stated because a single sentence covering both tools would be wrong about one, and the
  descent-versus-named remedy taught first because it costs no flag. Deployed with
  `inv deploy.all --name agents-md`.
- [`contributing/global-agents-md.md`](../contributing/global-agents-md.md), "Viewing, searching, or
  editing files" → "Hidden paths" — the user's own words, the two-repo measurement table, the
  `-I`-is-the-dangerous-one pitfall, the parked `RIPGREP_CONFIG_PATH` decision with its reasoning,
  and the unmeasurability pitfall that rules out the audit-row-first sequencing.
- [`2026-09-05-grep-glob-preference-is-inoperative.md`](2026-09-05-grep-glob-preference-is-inoperative.md)
  — the harness `Grep`/`Glob` question, which that plan's mode blocker owns and whose 96% figure
  resizes.
- [`2026-09-02-rg-replace-flag-used-twice-in-one-session.md`](2026-09-02-rg-replace-flag-used-twice-in-one-session.md)
  — the `rg -rln` instance this plan was only holding, as its tenth occurrence.

Deliberately not migrated:

- **The sibling relationship with the `fd`-clause-adherence plan.** That plan is still open and will
  be read on its own; restating the pairing in a page it does not own would be a second authority on
  one question.
- **The `.github` trigger incident in full.** One sentence naming the shape — an empty result reads
  like "already clean" — is what a reader needs; the repo it happened in is incidental.
