---
status: in-progress
updated: 2026-09-02
---

# Do the compressed `~/AGENTS.md` rules actually fire? — the adherence watch

## Context

Split out of the retired `plans/2026-08-23-global-agents-md-leanness-pass.md` at its closure. That
pass restructured `config/global-AGENTS.md` (deployed as `~/AGENTS.md`) from 6,053 body words / 30
flat sections to ~2,500 words / 6 clusters / 30 trigger-named rules, all landed 2026-08-23 — its
intended one-cluster pilot window was skipped, so the whole file is effectively piloting at once.
The one open item was its live-adherence verification:

[UNVERIFIED: do the rules still fire from the compressed trigger + rule + one-clause-why form over
the following working sessions? Highest-value watch list: git/commit rules (granular commits without
asking how to split; neutral handling of unexplained state), Bash/allowlist (simple separate calls,
scoping flags for cross-repo, `sudo -A`), verification (real exit codes, tests over ad-hoc scripts),
and the caveman register.]

## Recommended direction

- Watch passively across normal sessions in at least two repos — routine work exercises most rules;
  no dedicated drill needed.
- On an observed miss: re-expand the affected rule's wording in the `config/agents-md/` fragment
  that owns it (strengthen language, add the concrete tell — per the "strengthen, don't lengthen"
  finding in `contributing/global-agents-md.md`'s design-rationale section), record the miss here,
  redeploy. Never revert the cluster structure for a single rule's miss.
- Close as `landed` once a handful of sessions pass with no rule regressions; a clean watch leaves
  nothing to migrate.

## Observed misses

### Session 1 — `repo-tasks`, 2026-08-24 (long implementation session)

Four misses, all mine, all in the two clusters this watch flagged as highest-value. None caused
lasting damage; each cost a detour, and three were caught only because a later step happened to
surface them.

1. **Verification — truncated my own search output and treated it as complete.** Ran a
   `rg ... | head -20` to find every reference to a directory being moved, acted on the visible
   subset, and missed a file. It failed a test one step later. Then repeated the same shape a second
   time in the same session. `### Generalizing from a sample to a set` covers sampling _files_; it
   does not name the case where the sample is the tail of your own truncated output. That is the
   concrete tell worth adding — `| head` on a search whose purpose is completeness is the
   anti-pattern, and `rg -c` or a bare count first is the cheap check.

2. **Verification — verified commits against the wrong source.** Checked out three commits in a
   worktree and ran their tests, but the venv's _editable install_ resolves the package to the main
   working tree, so every run tested current code rather than the checkout. Produced one false pass
   and one false fail before I noticed. `PYTHONPATH=<worktree>/src` fixed it. The rule's existing
   framing ("clean stdout is not proof") did fire eventually; what was missing is that a _green test
   run_ is also not proof when the import path is not what you assume.

3. **Git — `git commit` commits the index, not the files just named.** Staged a specific file list
   for one commit while `git mv` renames sat in the index from earlier, so the renames landed in the
   wrong commit and a later commit was left referencing a module it did not yet contain. Unwound
   with `reset --soft` and restaged. Nothing in the git cluster states this; it is arguably plain
   git literacy rather than a rule gap.

4. **Quality gate — committed a plan edit without re-running it.** Pushed a dprint-unformatted
   markdown file to `main`; CI would have failed. Both `plan-docs` and `session-harvest` state this
   explicitly ("Markdown is not exempt"), and it is the single most common CI-failure cause recorded
   across these repos. So: not a rule-wording gap, a rule-adherence gap — the strongest signal in
   this batch, because the rule is already as explicit as it can be.

[DECISION: two of the four got re-expanded wording, 2026-08-24. (1) extended
`### Generalizing from a sample to a set` — the same failure applied to a sample you created
yourself by truncating your own search. (2) extended
`### Verifying behavior in a repo with test
coverage` — a green suite is only evidence about the
code that was actually imported. Both are one-sentence additions to sections that already framed the
principle, per "a variant extends the existing rule's section". Evidence in
`contributing/global-agents-md.md` under matching headings.

(3) was left out as plain git literacy rather than a personal-rules concern. (4) was left out
deliberately for the opposite reason: the rule is already as explicit as it can be and was still
missed, so more wording is the wrong lever — `plans/2026-08-23-git-hooks-for-quality-gate.md` is.]

### Session 2 — cross-repo transcript audit, 2026-08-24

Not a single session's misses but a measurement over every session since the leanness pass
(2026-08-21 → 24, 3,956 Bash calls, three repos; method in the `session-bash-audit` skill). The Bash
cluster was the one that did not fire: 64–71% of Sonnet/Opus calls were chained, 29–32% piped
through `head`/`tail`, 114 `cd`s into the session's own repo, and 81 `git -C … commit/push` calls
that no ask rule matched. The cause was not the compressed wording — every session ran in auto mode,
whose system reminder instructs the opposite of "Viewing, searching, or editing files" and whose
classifier never prompted, so "Composing a Bash call"'s stated reason (prompt friction) had no
referent. Fable 5 obeyed the same wording at half the chaining rate of Opus, which separates
disposition from wording.

[DECISION: the Bash cluster was re-cut 2026-08-24 around `acceptEdits` mode and the harness-side
costs of a chain (one output and one exit code per call), with a closed list of permitted chain
shapes, the head/tail fact, and the own-repo `cd` tell; the machine default mode moved to
`acceptEdits`. Evidence under the matching headings in `contributing/global-agents-md.md`. Verify by
re-running the audit after a week of `acceptEdits` sessions — the "Open / to re-measure" list in the
skill's `references/research.md` says what to expect.]

### Session 3 — `scaffoldapy`, 2026-08-26/27 (generating a new repo from the template)

The first post-re-cut observation of the Bash cluster, and it went the other way from session 2. The
session's primary directory was `scaffoldapy`; substantially all the work was in a newly generated
sibling, `ingesta`. Session 2 measured 114 `cd`s **into** the session's own repo; this session's
failure was the inverse — omitting the `cd` when the target genuinely was a different repo. Both
misses are the same underlying thing: cwd was treated as known when it was not.

1. **Dropped the `cd` on three consecutive cross-repo staged commits.** The user challenged it
   twice, I stated both times that every subsequent git call would carry an explicit `cd`, and then
   emitted the identical command without it — three times. The user's own diagnosis was right and is
   worth recording as the mechanism: **the permitted chain shape is
   `cd <other repo> && <one
   command>`, singular, but a staged commit is two commands (`git add`,
   then `git commit`), so `cd && add && commit` matches no permitted shape at all.** With no
   compliant form available, the `cd` is what got dropped. The adjacent "Never `cd` into the
   session's own repo as a matter of course" is stated forcefully and misfires once a session has
   been working in the sibling long enough that the sibling reads as "the session's own repo".
   Resolved in-session by abandoning cwd entirely: `git -C <abs path>` on separate calls, which the
   rule already names as preferred and which has no chain problem.

2. **cwd persistence produced a false-green gate run**, and this is the expensive one.
   `inv
   quality.precommit` was invoked for `scaffoldapy` with no `cd`, but cwd had persisted from
   an earlier `cd` into `ingesta`, so it ran `ingesta`'s gate and reported everything green. The
   green said nothing about the file just written; the tell was `rootdir:` in the pytest header,
   which had to be read deliberately.
   `### Running a command against a different repo than the session's
   project` already documents
   both the persistence hazard and the `inv` exception, and names
   `cd <repo> && PATH="<repo>/.venv/bin:$PATH" inv <task>` as the working form. That form worked
   immediately once used. The miss was reaching for the bare `inv` at all.

   This one is not "cheap and recoverable": it is a verification failure that manufactures
   confirming evidence, the class `### Reading a command's result` exists to prevent. A gate that
   reports green for the wrong repo is indistinguishable from one that reports green for the right
   one unless the header is read.

[NEEDS CLARIFICATION: which lever, given both misses are adherence rather than wording — the rules
involved already say the right thing, and (2)'s correct form is spelled out verbatim in the file.
More wording is the lever the design rationale warns against here. Three candidates: name
`git -C <path>` as _the_ form for mutating git in another repo so the two-command case has a
compliant shape at all; add "the gate reported green for the wrong repo" as the concrete tell under
the `inv` exception; or treat both as evidence for `plans/2026-08-26-agents-md-leanness-pass.md`'s
open question about demoting the Bash cluster to `session-bash-audit`, which can measure the rate
rather than restate the rule.]

### Session 4 — `agent-skills`, 2026-08-30: the re-cut's after-number, and it did not move

This is the verification session 2's `[DECISION:]` asked for ("re-run the audit after a week of
`acceptEdits` sessions"). One `acceptEdits` session, Opus 5, `agent-skills` — a session whose model
had the re-cut wording loaded the entire time:

| metric                      | this session | baseline (2026-08-21→24, 3,956 calls) |
| --------------------------- | ------------ | ------------------------------------- |
| Bash calls                  | 232          | 3,956                                 |
| piped through `head`/`tail` | **67 (28%)** | **29–32%**                            |

**The rate did not move.** Six days, a re-cut rule and a mode change produced no measurable
difference. Small sample, one model, one repo — but it is the same order as the baseline rather than
a reduction, which is the outcome the DECISION was hoping to falsify.

Of the 67, **21 piped a command whose exit code was the actual answer** — `inv`, `pytest`,
`gh run watch`, `git push`, `git fetch`. The single largest shape was the quality gate itself:

```
17  inv quality.precommit … | tail -N
10  git -C … | tail -N
 8  plans.py … | tail -N
```

[PITFALL: **`inv quality.precommit | tail -4` is the shape to name, and it is not a context-saving
mistake — it is an exit-code-discarding one.** Seventeen gate runs in one session each replaced the
gate's verdict with `tail`'s, which is always 0. Every one happened to pass, so nothing surfaced it;
a failure would have printed a similar-looking tail and reported success. The same session then did
it to `gh run watch --exit-status`, whose entire purpose is turning a red run into a non-zero exit,
and reported a green CI result it had not observed.]

A **third occurrence the same day**, in the harvest session that filed
`plans/2026-08-30-git-history-rewriting-to-tidy-a-commit.md`: it piped `git fetch` through `tail`
while running the checklist that forbids it. Same shape — a stated rule held in context and not
applied.

The rule is currently split across two clusters that each hold half the answer, and neither states
the consequence for the shape that actually occurs:

- **"Viewing, searching, or editing files"** says never pipe through `head`/`tail` to save context,
  and gives the reason as _data loss_ — "pre-truncating only loses data and forces a second run".
- **"Reading a command's result"** says a pipe returns the filter's exit code, so `$?` never
  reflects an upstream failure — but frames it around `$?` and log files.

An agent piping a gate is not trying to save context and is not reading `$?`, so it matches neither
warning as written. It is truncating _display_ of a command it believes it is running normally.

[DECISION: name the shape in **"Reading a command's result"**, where the consequence lives — one
clause: piping a gate, a test run or a waiter through `head`/`tail` discards its exit code and
replaces it with the filter's, which is 0 whether or not the command failed, with
`inv quality.precommit | tail -4` as the canonical instance. End on the replacement habit rather
than the warning: run it bare, since the Bash tool already reports a non-zero exit, keeps the whole
output, and saves oversized output to a file it names. Do **not** lengthen "Viewing, searching, or
editing files" — its data-loss framing is correct for the search case (`rg … | head` on a search
meant to be complete), which is a different failure with a different fix (`rg -c` first). Two
shapes, two homes, one clause each.]

Not yet written or deployed. When it is: the fragment in `config/agents-md/` owning "Reading a
command's result", the evidence into `contributing/global-agents-md.md` under a matching heading,
then `inv deploy.all --name agents-md`.

[UNVERIFIED: one session, one model, one repo, against a baseline spanning three repos and four
days. The honest claim is "no evidence the re-cut worked", not "the re-cut failed". Re-run the real
`session-bash-audit` measurement before treating the comparison as sound — and again after the
clause above lands. The number to beat is 28%.]

[DEFERRED: the audit script does not separate the exit-code-bearing subset from ordinary display
truncation, which is the distinction this measurement turns on — the 21-of-67 split was computed ad
hoc. Teaching `session-bash-audit` to report it belongs in `agent-skills` and would make the
after-measurement answer the right question. Not blocking: the headline rate is already measurable.]

### Session 5 — `power-user-linux-setup`, 2026-08-30: the session that wrote session 4 scored worse

Measured over this session's own transcript, by the same method, immediately after it had authored
session 4's `[DECISION:]` about `head`/`tail` piping and committed it:

| metric                               | session 5 (this one) | session 4    | baseline (2026-08-21→24) |
| ------------------------------------ | -------------------- | ------------ | ------------------------ |
| Bash calls                           | 254                  | 232          | 3,956                    |
| piped through `head`/`tail`          | **86 (33%)**         | 67 (28%)     | 29–32%                   |
| ...of which carried a real exit code | 51                   | 21           | not measured             |
| chained (`&&` / `;`)                 | 103 (40%)            | not measured | 64–71%                   |
| `cd` into the session's own repo     | **0**                | not measured | 114 across three repos   |

**The rule was held in context, written about, committed, and then broken at a higher rate than the
session it was written about.** `inv quality.precommit … | tail -3` — the canonical instance the
DECISION names — was the single most repeated shape. That is not a wording gap: no wording is more
present to a session than the sentence it just authored.

[PITFALL: the piped gate runs all passed, so nothing surfaced it — exactly as in session 4. The gate
failures this session _did_ catch were all on bare, unpiped calls, which is the mechanism working.
So the sample is self-selecting in the worst way: a piped gate that fails looks identical to a piped
gate that passes, and the only reason this session never shipped a false green is that its failures
happened to land on the calls it had not piped.]

Two more misses in the same session, both of rules that are already explicit:

1. **`rg -rn <pattern> <paths>` — `-r` is `--replace`.** `~/AGENTS.md` states this verbatim,
   including "plausible-looking output that is not what the file says". The call printed a rewritten
   anchor string, which was then reasoned about as though it were the file's content. Caught only
   because the result looked odd enough to re-run with `grep`.
2. **`git stash` to check whether a commit stood alone.**
   `plans/2026-08-30-git-history-rewriting-to-tidy-a-commit.md` — **absorbed into this repo by this
   same session, hours earlier** — says `git stash` is unsafe here because parallel sessions share
   one working tree. Used twice. The first use also proved nothing: it stashed the new tests along
   with the fix, so the suite passed against neither, and the "verification" was empty. The second
   attempt used the scratchpad copy-and-revert technique `~/AGENTS.md` actually names, and worked.

[DECISION: all three are **adherence, not wording** — the shape session 3 already identified, now
with the strongest possible evidence for it: an agent authoring a rule is not thereby more likely to
follow it. More wording is the wrong lever. What this batch adds is a measurement method that costs
one script and needs no separate audit — a session can count its own transcript. That is the thing
worth generalizing: `session-bash-audit` measures across sessions after the fact, and nothing
measures a session against itself while it can still act on the answer.]

[DEFERRED: teach `session-bash-audit` to run against a single live session's own transcript and
print this table, so any session can self-measure in one call rather than reimplementing the counter
(as this one did). That skill lives in `agent-skills` and already invites newly noticed patterns;
the exit-code-bearing split it does not yet compute is
`plans/2026-08-30-head-tail-piping-survived-the-bash-recut.md`'s open item, now merged into session
4 above. Filed there rather than acted on here.]

### Session 6 — `repo-tasks`, 2026-08-30: the first sample below baseline, and two git findings

Plan triage, a currency pass over twelve plans, two new tasks, and a source-reading research pass
across five vendor repos. Filed from that repo, which cannot edit a plan here.

| metric                             | session 6    | session 5      | session 4    | baseline (2026-08-21→24) |
| ---------------------------------- | ------------ | -------------- | ------------ | ------------------------ |
| Bash calls                         | 250          | 254            | 232          | 3,956                    |
| piped through `head`/`tail`        | **51 (20%)** | 86 (33%)       | 67 (28%)     | 29–32%                   |
| chained (`&&` / `;`)               | 36 (14%)     | 103 (40%)      | not measured | 64–71%                   |
| `cd` into the session's own repo   | 0            | 0              | not measured | 114                      |
| `rg -r` (i.e. `--replace`) misuses | **2**        | first recorded | —            | —                        |

**This is the first sample below the baseline on `head`/`tail`**, and chaining is a quarter of
session 5's rate. If this plan's `[DECISION: adherence, not wording]` is right, that is what
improvement looks like — but one sample is not a trend, and the confound is obvious: this session
did an unusual amount of source reading, where `git show <tag>:<path>` and `grep -n <pat> <file>`
are naturally unpiped. A session doing more log-reading would likely score worse.

[PITFALL: counting `rg -r` naively over-reports. A regex for `\brg\s+-[a-zA-Z]*r` also matches
`grep -rn` and `grep -rln`, where `-r` is the legitimate recursive flag — that is the whole reason
the `rg` confusion exists. The raw count here was 4; the real one is 2. Any future automated counter
has to exclude `grep`, or it will inflate exactly the metric it exists to watch.]

#### The two `rg -r` occurrences

Both in one research pass, minutes apart, in a session whose context held `~/AGENTS.md`'s verbatim
statement of the trap:

```shell
rg -rn --no-heading 'credsStore|CredentialsStore|NewStore|DockerConfig' <path>   # printed `credentials.n(`
rg -rn 'DetectDefaultNativeStore' <path> --glob '*.go' -l                        # returned nothing
```

The first is the dangerous shape the rule warns about, and it behaved exactly as advertised: it
printed `credentials.n(` where the source says `credentials.NewStore(`, i.e. plausible-looking
output that is not what the file says. It was caught only because `NewStore` was the string being
searched for and its absence from the results was conspicuous. **Had the pattern been anything the
eye did not expect to see echoed back, the corrupted output would have been read as fact** — and
this was a research pass whose findings then went into three plans.

The second returned nothing and was misread as "no matches" rather than "malformed command", which
cost one wrong turn before the layout was checked directly.

Same session, same rule, twice — supporting the existing `[DECISION: adherence, not wording]` rather
than complicating it. Worth noting for the wording question anyway: the rule is stated as a fact
about `rg` (`its -r is --replace`) rather than as a habit to break
(`never write -rn; rg is already
recursive`), and both misuses were `-rn`, the bundled form, where
the `-r` is least visible.

#### Two git findings

##### 1. `git mv` stages, and the rule's examples do not name it

Session 3 of the adherence plan recorded this exact incident — renames sitting in the index from
earlier landing in the wrong commit, unwound with `reset --soft` — and concluded "nothing in the git
cluster states this; it is arguably plain git literacy rather than a rule gap."

**Something in the git cluster does state it now**, under "Committing multi-part work": _"Stage each
commit's paths immediately before that commit, never ahead of time... anything staged earlier — a
`git rm` run while tidying, a `git add` from a previous step — rides along under the next message."_
And it happened again anyway, 2026-08-30: a `git mv` renaming a plan file, run while editing rather
than while committing, rode into the next commit, which was about an unrelated new plan.

So the classification changes: no longer "arguably git literacy", now a second occurrence under an
explicit rule. The one wording observation worth making is that the rule's two examples — `git rm`
and `git add` — are both verbs that read as _staging_, whereas `git mv` reads as an _edit_. A reader
checking "did I stage anything ahead of time?" does not think of the rename.

##### 2. Nothing states what the actual protection is

The cluster says, under "Unexplained git/file state in a working tree", that `git status --short`
immediately before committing _is not_ protection, because it reports the staged set rather than
what changed while you were reading it. That is correct and it was confirmed here in the sharpest
possible way: a store commit staged by explicit path still shipped a third file that a parallel
session had staged into the shared index in the seconds between.

But the cluster stops at the warning and never names a defence. There is one, and it worked:

```shell
git commit -m "…" -- <path> <path>     # commits these paths only, whatever else is in the index
```

The pathspec form ignores the index for the named paths and leaves everything else staged, so a
parallel session's staged file cannot ride along and is not disturbed either. Used later in the same
session to split the contaminated commit cleanly.

[PITFALL: **a relative ref is not safe in a repo with parallel sessions, and this is the sharp
edge.** Undoing that contaminated commit with `git reset --soft HEAD~1` removed a _different_
commit: the other session had committed on top in the interval, so `HEAD~1` resolved to my commit
and the reset discarded theirs. Recovered from the reflog with `reset --soft <their-sha>`, nothing
lost, nothing pushed. The cluster already says a lease SHA must come from `git rev-parse` rather
than be completed by eye — this is the same principle one step earlier, and it is not stated: **read
the SHA, reset to the SHA.** `HEAD~1` silently retargets and there is no error, because both
readings are valid git.]

[DECISION: the two git findings above are wording candidates, unlike everything else in this plan.
Both are cases where the cluster frames a problem and stops short of the remedy, which is a
different failure from the adherence gap the other five sessions measure. Judge them on
`contributing/global-agents-md.md`'s admission criteria, and prefer extending "Unexplained git/file
state in a working tree" — which already sets up the parallel-session problem and ends on a warning
with nothing to do about it — over adding a heading. Report the before/after line count when
proposing, as that document requires.]

[DECISION: leave the `rg -r` wording alone unless a third session hits it. Two occurrences in one
session is one data point, not two, and the existing decision is that adherence rather than wording
is the lever.]

### Session 7 — `power-user-linux-setup`, 2026-08-30: the two metrics moved in opposite directions

Plan absorption and merging, a package added, a shared installer fixed, and an audit of `verify.all`
against every GUI-tagged package. Counted from the session's own transcript.

| metric                           | session 7    | session 6 | session 5 | baseline (2026-08-21→24) |
| -------------------------------- | ------------ | --------- | --------- | ------------------------ |
| Bash calls                       | 162          | 250       | 254       | 3,956                    |
| piped through `head`/`tail`      | 33 (20%)     | 51 (20%)  | 86 (33%)  | 29–32%                   |
| chained (`&&` / `;`)             | **65 (40%)** | 36 (14%)  | 103 (40%) | 64–71%                   |
| file reads via `cat`/`sed -n`    | 20 (12%)     | —         | —         | —                        |
| `cd` into the session's own repo | 3            | 0         | 0         | 114                      |
| `rg -r` misuses                  | 0            | 2         | —         | —                        |

**`head`/`tail` held at session 6's improved rate while chaining regressed all the way back to
session 5's.** Two consecutive samples at 20% is the first sign the piping figure is genuinely
moving rather than fluctuating; chaining doing the opposite in the same session is what makes them
separate problems. That is now the sharpest evidence for the open chaining question in
`plans/2026-08-28-auto-mode-contradicts-bash-rules.md`, and it is recorded there too.

The three `cd`s into the session's own repo are **not** the violation the baseline's 114 were: each
re-established cwd after a chain into another directory had moved it, which is exactly what the
rule's own last sentence prescribes. Worth stating because the counter cannot tell the two apart,
and a future automated version will report them as failures.

[PITFALL: the `rg -r` counter over-reports in a second way the existing note does not cover. Beyond
matching `grep -r`, a naive regex also matches the **body of a heredoc** — a `python3 - <<'PY'` or
`cat >> file <<'EOF'` whose content happens to contain the pattern is counted as a command. All
three hits this session were that; the true count was 0. Any automated counter has to match against
the command verb, not the whole call text.]

[PITFALL: this session's file-read rate is not comparable to the earlier ones, and neither is any
future sample taken under auto mode. `Grep` was **not available** — the harness withdrew it and
returned `No such tool available` — so every content search had to go through Bash regardless of
what `~/AGENTS.md` says. A counter that reads those as adherence failures is measuring the harness.
See the auto-mode plan, which now owns that finding.]

### Session 8 — `agent-skills`, 2026-08-30: the rate halved and the named instance survived

Merged in from a plan filed against this repo by that session, which could not edit this file
directly. Counted from its own transcript, 272 Bash calls.

| metric                           | session 8    | session 7 | session 6 | baseline |
| -------------------------------- | ------------ | --------- | --------- | -------- |
| piped through `head`/`tail`      | **31 (11%)** | 33 (20%)  | 51 (20%)  | 29–32%   |
| chained (`&&` / `;`)             | 58 (21%)     | 65 (40%)  | 36 (14%)  | 64–71%   |
| `cd` into the session's own repo | 0            | 3         | 0         | 114      |

11% is the lowest the watch has recorded — a third of baseline, half the previous best.

[PITFALL: **the headline rate improving is compatible with the specific rule failing exactly as
before.** Of that session's 31 piped calls, 12 were the two shapes that destroy an _exit code_
rather than merely truncate output: 10 × `inv quality.precommit 2>&1 | tail -N`, the instance this
plan has named since session 4, and 2 × `gh run watch --exit-status 2>&1 | tail -N`, the flag whose
entire purpose is converting a red run into a non-zero exit, discarded by the filter reading it. The
other 19 were `rg`/`ls` truncations — the data-loss shape. So the diffuse habit receded while the
named, argued-about instance did not move at all, and a reader tracking only the percentage would
have recorded the wording as working.]

[PITFALL: **both exit-code cases happened while that session was executing a checklist warning about
them in the sentence above the command.** `session-harvest`'s CI bullet then read "do not pipe it"
and named the lost exit code; it was piped twice anyway, hours apart. Caught only because the
session counted its own Bash calls at harvest — not by noticing.]

Its conclusion, which session 9 then tested: naming the instance is not sufficient, and a command
with **no exit code to lose** is a real mitigation rather than a warning —
`gh run view --json
status,conclusion` cannot be broken by a pipe. `session-harvest`'s CI bullet was
rewritten that way the same day.

### Session 9 — `power-user-linux-setup`, 2026-08-30: the gate is now half the problem

This session — the `~/AGENTS.md` fragment re-cut, dependency labels, `ai.check-rule-prerequisites`,
and the locale change. 270 Bash calls, counted at harvest.

| metric                             | session 9 | session 8    | session 7 | baseline |
| ---------------------------------- | --------- | ------------ | --------- | -------- |
| piped through `head`/`tail`        | 62 (22%)  | **31 (11%)** | 33 (20%)  | 29–32%   |
| — of which `inv quality.precommit` | **29**    | 10           | —         | —        |
| chained (`&&` / `;`)               | 99 (36%)  | 58 (21%)     | 65 (40%)  | 64–71%   |
| `cd` into the session's own repo   | 2         | 0            | 3         | 114      |
| `echo $?` / `EXIT=`                | **0**     | —            | —         | 10–11%   |

[PITFALL: **the named instance is not merely surviving, it is becoming the whole of the problem.**
`inv quality.precommit … | tail -N` was 32% of session 8's piped calls and is **47% of session 9's**
— 29 of 62. The share is growing while the aggregate rate oscillates, which means the aggregate is
now mostly measuring how search-heavy a session happened to be. Session 8's open question ("is 11%
real, or a composition artefact?") is answered in the direction it feared: composition dominates,
and the two metrics should be reported separately from here on.]

The `echo $?` count is the one unambiguous win: **zero occurrences in 270 calls**, against 10–11% of
Fable/Opus calls on the day a contradictory version of the rule was live. That rule was rewritten to
state the tool already reports a non-zero exit, and this session merged its three scattered copies
into one canonical home — so it is now the best-evidenced case of a rule that was fixed and stayed
fixed.

[NEEDS CLARIFICATION: the gate instance has now resisted four sessions of increasingly precise
prose, so the next move is not more wording. Session 8 named the shape of a real fix — prefer a form
with no exit code to lose. `inv quality.precommit` has no `--json`, so the candidate is running it
bare and reading the harness's own non-zero report, which is exactly what the rule already says and
is exactly what is not happening. Worth asking whether the pull is output _volume_ rather than exit
codes: the gate prints ~40 lines on success, and every one of this session's 29 pipes was `tail -3`
to `tail -6`. If so the fix is a quieter gate, not a better rule.]

### Session 10 — `power-user-linux-setup`, 2026-08-31/09-01: the announcement, then the opposite

The WSL/container first-run session (sudo pre-auth, `netdoctor`, the container harness). 404 Bash
calls over roughly ten hours, counted at harvest — the largest sample in this watch so far, and the
worst `head`/`tail` rate since session 5.

| metric                           | session 10    | session 9 | session 8 | baseline (auto mode) |
| -------------------------------- | ------------- | --------- | --------- | -------------------- |
| Bash calls                       | **404**       | 270       | ~280      | 3,956                |
| piped through `head`/`tail`      | **161 (40%)** | 62 (22%)  | 31 (11%)  | 29–32% (+9pp MISS)   |
| chained (`&&` / `;`)             | 218 (54%)     | 99 (36%)  | 58 (21%)  | 64–71% (−12pp OK)    |
| heredoc instead of Edit/Write    | **105 (26%)** | —         | —         | 16% (+10pp MISS)     |
| `sed -n` file reads              | 32 (8%)       | —         | —         | 8% (+0pp MISS)       |
| exit-masked (pipe hides `$?`)    | 81 (20%)      | —         | —         | —                    |
| `cd` into the session's own repo | 4 (1%)        | 2         | 0         | 114                  |

[PITFALL: **this session opened by announcing the rule and then broke it more than the baseline
does.** Its first substantive line was "per `~/AGENTS.md` I'll keep using Read/Edit/Write for files
(and `rg` for search) rather than the auto-mode Bash-only note" — a deliberate, correct reading of
the auto-mode contradiction (see plans/2026-08-28-auto-mode-contradicts-bash-rules.md). It then
wrote files through `python3 - <<'PY'` heredocs in 26% of its calls, 10pp _worse_ than the auto-mode
baseline it was overriding. This is the third recorded instance of announcing adherence preceding a
worse-than-baseline rate; the other two are in
`plans/2026-08-28-auto-mode-contradicts-bash-rules.md`, which now owns the question of whether the
announcement is a variable worth measuring. Whatever the announcement is doing, it is not the thing
that changes behaviour — and it makes the transcript read as compliant to anyone who does not
count.]

[PITFALL: the heredoc rate has a cause the earlier sessions did not have — this session made ~40
edits that were _mechanical rewrites across several files at once_ (renaming a helper in three
modules, inserting one line into fifteen task functions, replacing a paragraph in four docs). Edit
requires one call per site and a prior Read of each; a heredoc does the set in one call. That is a
real ergonomic pull the rule does not acknowledge, and it is the same shape as session 9's gate
finding: the aggregate rate is measuring what kind of work the session did. Worth separating
"heredoc as a file editor" from "heredoc as a multi-file refactor" before more wording is spent on
it.]

The `head`/`tail` number splits the same way session 9's did: a large share is
`inv quality.precommit … | tail -3/-4`, run ~20 times because the gate prints ~40 lines and only the
last three matter. Session 9's open question — whether the pull is output volume rather than exit
codes — now has a second session's evidence pointing the same way, and this one never once needed
the exit code it was discarding.

### Session 11 — `ingesta`, 2026-09-01: a regression, and the instrument moved the number

Merged from `plans/2026-09-01-adherence-sample-11-a-harvest-that-raised-its-own-rate.md`. Auto mode,
`claude-opus-5`, ~2h implementation then a harvest.

| metric              | session 11 | baseline (2026-08-24) |
| ------------------- | ---------- | --------------------- |
| Bash calls          | 127        | 3,956                 |
| piped `head`/`tail` | **37%**    | 29–32% (+6pp MISS)    |
| chained             | 50%        | 66% (−17pp OK)        |
| `git -C` own repo   | 3%         | 0% (+3pp MISS)        |
| met                 | 9/11       | —                     |

**A regression against a watch that had started to read like a recovery.** Sessions 6 and 8 put the
figure at or below baseline; this one is six points above it, with the rule in context and read
during the session. It also announced the auto-mode resolution and then _kept_ to it on the
read/edit side — so the announcement question came out compliant here and the piping question did
not, which separates the two for the first time.

[PITFALL: **the harvest raised the number while measuring it.** 37% at n=127 when the sweep began,
40% at n=136 by the time the report was written — `session-harvest`'s step 5 prescribes inspection
commands whose natural written form is piped, so the instrument and the rule disagree and the
published figure is inflated by an amount no reader of that report can see. A sample taken at
harvest time is therefore not comparable with one from a session that was never harvested, and this
watch mixes both.]

### Session 12 — `agent-skills`, 2026-09-01: the counterweight, and `git -C` at 22%

Merged from `plans/2026-09-01-adherence-sample-12-a-background-job-and-the-git-c-habit.md`. A
background job, ~90min authoring and shipping a skill, then a harvest. Same day as session 11.

| when                 | n   | `head`/`tail` | chained | `git -C` own repo | heredoc | met  |
| -------------------- | --- | ------------- | ------- | ----------------- | ------- | ---- |
| sweep begun          | 101 | 6%            | 10%     | **22%**           | 18%     | 8/11 |
| report being written | 132 | 6%            | —       | 17%               | 14%     | 9/11 |

**Two samples one day apart, 31 points apart on `head`/`tail`, in opposite directions** — and here
the sweep _improved_ the score where session 11's worsened it. What separates them is plausibly the
work: session 11 was implementation plus a piped-by-construction sweep; this was authoring, where
the long-output commands are a gate and a `git log`, both of which the rules say to run plain.

[PITFALL: **`git -C <own repo>` at 22% is a rule interacting with itself.** `~/AGENTS.md` warns that
cwd is unreliable after a cross-repo `cd … && …`; this session ran three such chains, saw the
harness confirm `Shell cwd was reset` each time, and then wrote every later call defensively with an
absolute `git -C` — including calls where cwd had never moved. 8% were _mutating_ git behind `-C`,
which the file says matches no allowlist rule; none prompted, so nothing contradicted the habit. The
miss is a caution outliving the situation that justified it, which is a gap in the rule's scope
rather than in the reader's attention.]

[PITFALL: **a sample can straddle a rule change and nothing in the numbers says so.** This session's
18% heredoc rate is entirely `cat > … <<'EOF'` writing commit-message files — obeying the
then-current "a message containing a backtick goes through `git commit -F <file>`" while violating
the Bash section. That rule was **inverted later the same day** (session 13 below), so this rate
measures adherence to a rule that no longer exists. Worth stamping each sample with the
`~/AGENTS.md` commit it was taken against.]

### Session 13 — `power-user-linux-setup`, 2026-09-01: the first 11/11, and the first announcement that held

This session — the WSL/container end-to-end work, the apt and zsh fixes, and the rule changes
sessions 11 and 12 refer to. Auto mode, `claude-opus-5`. Both figures recorded per session 11's open
question:

| when                 | n   | `head`/`tail` | chained | heredoc | `cd` own repo | met       |
| -------------------- | --- | ------------- | ------- | ------- | ------------- | --------- |
| sweep begun          | 266 | 7%            | 28%     | 2%      | 0%            | 10/11     |
| report being written | 302 | **6%**        | 26%     | 2%      | 0%            | **11/11** |

**The first sample to meet every expectation**, and the third consecutive one where the sweep moved
the number — improving it here and in session 12, worsening it in session 11. Three data points now
say the pre/post distinction is real and not always signed the same way, which settles session 11's
question in favour of recording both.

**It is also the first announcement that held.** Sessions 10 and 11 both opened by stating the
auto-mode resolution and then scored at or above baseline, which is what made "the announcement is
not the thing that changes behaviour" the watch's working conclusion. This session made the same
announcement and posted the best figures in the series — so the pattern is not deterministic, and
whatever the announcement correlates with, it is not reliably regression.

[PITFALL: **the aggregate hides a mid-session correction, and the correction is the more useful
fact.** The user interrupted a `git add && scan && git commit -F … && git log` chain with _"i don't
like this chaining at all, it obscures the commit message, which is what i want to read when i
approve or not approve this"_. Every commit before that point was `-F <file>` behind a chain; every
one after was inline `-m` in its own call. The 26% chain rate averages both halves, so the number
understates a real behaviour change that the transcript shows cleanly — the same "before/after
inside one session" shape session 12 identified for the heredoc rule, from the other side of the
same change.]

[DECISION: the `-F` rule that session 12 measured was reversed on that correction. "About to commit"
now reads **keep the message inline in `-m`, and write it without backticks or `$`** — because `-m`
is what puts the message in the approval prompt and a path is not — with the escape hatch kept for a
message that genuinely must carry a backtick. The companion clause landed in "Composing a Bash
call": a chain hides whatever the user needs to read inside a compound command, a reviewability cost
that rule had never stated, having argued only from exit codes and output blobs. Evidence in
`contributing/global-agents-md.md` under "Pull versus generate…" and the backtick section.]

### Session 14 — `power-user-linux-setup`, 2026-09-02: three breaches by the session editing the rules

The session that worked this plan's own cluster — round 3 of the leanness pass, the four parked
admissions, and the output-ceiling measurement. Not a rate sample; three specific breaches, each of
a rule the session had read, edited or measured within the hour. Recorded because the watch's
standing `[DECISION: adherence, not wording]` has never had a cleaner instance.

1. **`rg -rn`, the `--replace` trap.** Searching for where a task was documented. The results named
   `inv ai.n` in four files that all say `inv ai.check-rule-prerequisites`. Caught only because
   `ai.n` is not a plausible task name — the same accident that saved the first recorded occurrence,
   not a method. Third occurrence machine-wide and the third `-rn` of three; recorded in
   `plans/2026-09-02-rg-replace-flag-used-twice-in-one-session.md`, which now says the bundled form
   is the shape to measure.
2. **`git stash`, to prove a test failed without its fix.** `~/AGENTS.md` names this unsafe here
   because parallel sessions share one working tree, and names the replacement — copy to the
   scratchpad, edit down, restore. The stash was pathspec-scoped and popped immediately, so nothing
   was lost, but a parallel session's edit to that same file would have been swept in and the
   session would not have known. The pull is that `git stash push -- <path>` is one call and the
   documented technique is four.
3. **`inv quality.precommit 2>&1 | tail -6`**, roughly an hour after the same session measured the
   harness's output ceiling specifically to establish that this filter buys nothing — and wrote that
   finding into two plans. Re-run bare; the verdict held.

4. **cwd drift after a `cd … && …` chain**, hours later. A chain into the scratchpad to fetch
   several files left cwd there, and a later `plans.py commit` — issued as a bare command on the
   assumption it was running in the session repo — routed off the wrong directory. The rule states
   this hazard exactly and prescribes the remedy (treat cwd as unknown after such a chain; the next
   call takes an absolute path or re-establishes it).

[PITFALL: **the fourth adds a tell the rule does not list.** "Running a command against a different
repo" names two symptoms of a stuck cwd — `inv` reporting `Can't find any collection named 'tasks'`,
and a path that "does not exist" which plainly does. This was neither: `plans.py` answered
`verdict: needs-decision — <scratchpad> is not inside a git repository`, which reads as a
configuration question about the plans store rather than as a location error, and would have sent a
session to `plans.py config` rather than to `cd`. A tool that routes on cwd fails in the vocabulary
of whatever it routes to, so the symptom list cannot be complete — the generalisable form is that
any unexpected answer about _where something belongs_ is a cwd question first.]

[PITFALL: **the third one is the sharpest instance the watch has, because the session had just
removed the last argument in the filter's favour.** Sample 5's corpus entry had kept open the
possibility that an unknown output size justified a filter; this session probed the ceiling, found
truncation keeps the head and saves the whole output to a file, wrote "there is no legitimate
`head`/`tail` case left to carve out" as a `[DECISION:]`, committed it — and produced the shape
about forty minutes later. So the count of things that make no difference now includes: reading the
rule, authoring the rule, measuring the rule's premise, and publishing the conclusion.]

### Session 15 — `ingesta`, 2026-09-04: the rule's own justification proved itself mid-violation

Session `179f0c44-e084-4cd3-918e-77568655e419`, 189 Bash calls bounded at the harvest boundary. Two
misses, both in clusters this watch already names as highest-value, and **both caught by the user
rather than by the session.**

1. **Ad-hoc verification instead of the test suite.** After adding a new surface module to a repo
   with an 896-test suite and shared fixtures, the session verified its behaviour with two
   `uv run python -c "..."` one-liners — an exploratory print, then a debug print when the output
   looked wrong. The user interrupted the second: _"why not use pytest, fixtures, hypothesis, all
   that, instead of hand rolling bash commands?"_ The rule names the exact shape ("Run the test
   suite, not a one-off ad-hoc script (`python3 -c "..."`, a manual re-render in `/tmp`)") and was
   in context throughout — the watch's third shape, **not followed**, wording fine.
2. **`uv run pytest` where the bare command resolves.** Corrected mid-turn: _"you don't need to do
   uv run pytest, that messes with the allowlist, just to pytest"_. The repo uses direnv exactly as
   the rule assumes. Cost: a permission prompt on every run.

| pattern     | rate | note                                     |
| ----------- | ---- | ---------------------------------------- |
| chain       | 41%  |                                          |
| head/tail   | 38%  | mostly the gate through `tail -N`        |
| exit-masked | 23%  | 43 calls                                 |
| sed-n       | 4%   | 7 calls, all reading source Read handles |

[PITFALL: **the first miss's own justification demonstrated itself inside the session that broke
it.** The tests, once written, immediately surfaced three facts the ad-hoc scripts had not: that
`missed_after` is a strict threshold (at exactly four hours a dose is still `LATE`), that a horizon
bound must never hide an overdue dose, and that an intake matches a slot by `regimen_id`. Two were
wrong assumptions the session was about to build on. That is the strongest available argument that
the rule is right and the weakest possible evidence that stating it is sufficient.]

### Session 16 — `ingesta`, 2026-09-04: same repo, same day, same model, lower on everything

Session `54d36cb9-ba1c-4a48-8316-6f35ab58f452`, 08:50–14:03, 134 Bash calls bounded at the harvest
boundary. Filed alongside session 15 deliberately rather than separately, because the gap between
two sessions matched on repo, day and model is the comparison, not each rate on its own.

| pattern        | this | session 15 |
| -------------- | ---- | ---------- |
| chain          | 32%  | 41%        |
| head/tail      | 25%  | 38%        |
| exit-masked    | 17%  | 23%        |
| sed-n          | 0%   | 4%         |
| cd-own-repo    | 1%   | 1%         |
| git-C-own-repo | 0%   | 0%         |

Including the harvest's own inspections the figures are 30% / 24% / 16% — the sweep moved them
_down_, which the harvest-inflates-its-own-number story does not predict, and a second reason to
print both.

**One miss, and the user caught it.** The session needed a state the simulator would not produce and
reached past `inv` to `uv run python tasks/drive_browser.py`, because the `inv` task regenerates the
fixture first and would have wiped the hand-edit. The repo's `AGENTS.md` says `inv` is how `tasks/`
is run and there is no second mechanism — the watch's **second** shape, a rule reasoned around with
a real justification rather than forgotten. The user's question was three words: _"why uv python run
tasks instead of invoke?"_

[PITFALL: **the bypass was the visible half of an error that had already happened.** The proposed
remedies were a new `--no-export` flag or dropping the check; both were wrong, because the premise
was — the simulator _does_ produce the state, and the right move was scanning seeds for one, needing
no new mechanism. The rule violation and the bad remedies came from the same unchecked assumption,
so a rule breach is worth reading as a symptom rather than only as a lapse.]

[PITFALL: **the head/tail rule was broken inside the harvest that measures it** — the
`session-bash-audit` run was itself piped through `tail -40`, truncating its own summary line. The
cheapest possible demonstration that the rule is not lost, misworded or unavailable at the moment it
is broken.]

### Session 17 — `power-user-linux-setup`, 2026-09-04: the first corpus baseline, and an auto-mode confound

This session, `bc30285c-145c-494d-b2d1-be6b37cd37f1`, 145 Bash calls bounded before its own sweep.
Docs-gate and Node-20 work; measured because sessions 15 and 16 recommended saving a baseline and
four samples had by then reported rates against nothing.

**The baseline now exists**: `~/.local/state/session-bash-audit/2026-09-04.json`, from `--days 4` —
7,580 Bash calls, 25 main sessions, all `claude-opus-5`. Corpus rates: `chain=46%`, `head/tail=31%`,
`exit-masked=20%`, `heredoc=13%`, `sed-n=5%`, `cat-view=1%`, `git-C-own-repo=2%`. Every rate this
watch has recorded since session 4 can now be read as above or below something.

| pattern        | this session | corpus | reading                                    |
| -------------- | ------------ | ------ | ------------------------------------------ |
| chain          | 43%          | 46%    | marginally better, still the worst pattern |
| head/tail      | 25%          | 31%    | better                                     |
| exit-masked    | 22%          | 20%    | **worse**                                  |
| heredoc        | 0%           | 13%    | much better — Write/Edit throughout        |
| sed-n          | 6%           | 5%     | worse                                      |
| cat-view       | 6%           | 1%     | **six times the corpus rate**              |
| git-C-own-repo | 1%           | 2%     | one call, self-caught in the same turn     |

[PITFALL: **this session ran in auto mode, whose system note asks for `cat`/`sed -n` over `Read` and
withdraws `Grep` — so three of these columns are measuring compliance with a system instruction, not
a lapse.** `~/AGENTS.md`'s own auto-mode rule says to keep using Read/Edit/Write anyway and to say
so once; this session did say so, then produced `cat-view` at six times the corpus rate regardless.
The confound is real and the miss is real, and the numbers alone cannot tell them apart. **The
baseline is therefore mode-blind and must not be read as a like-for-like comparison** — the note
stored with it says which patterns are affected (`cat-view`, `sed-n`, `grep/find`) and which are not
(`chain`, `head/tail`, `exit-masked`). A future sample should record its permission mode.]

[PITFALL: **`exit-masked` at 22% is this watch's own shape, produced by a session that quoted the
rule to the user.** Roughly eight `inv quality.precommit 2>&1 | tail -N` calls, each followed by
telling the user the gate was green. Re-run bare at the end: 551 passed, exit 0, so every claim
holds — true by luck of the run rather than by evidence at the time, which is exactly how sessions
15 and 16 described their own. Three consecutive samples have now self-reported this identical
pattern, which makes it the most reproducible finding the watch has.]

The corpus also puts two of this plan's older claims on a footing:

- **`git -C` against the session's own repo really does spike per-session.** `~/AGENTS.md` cites
  "23% in one session"; the corpus has `agent-skills/2312636b` at **20%** and `ingesta/fc50032f` at
  **11%**, against a 2% model average. The rule's framing — a caution outliving the cross-repo step
  that justified it — matches a per-session lock-in better than a diffuse habit.
- **The `head`/`tail` cost is now counted, not argued.** 140 re-runs across the corpus followed a
  truncated first run. That is the concrete price of a filter whose only claimed benefit was saving
  context the harness was not spending.
- **Twelve denied calls in four days, and the shapes are the ones the rules name**: `git commit -F`,
  a four-step `git add && scan && git commit` chain, and gate runs piped through `tail`. The rules
  were written from these rejections, so a denial is the user re-stating a rule the session had.

[DECISION: **`bash.md`'s gate paragraph now names `2>&1 | tail -N`, 2026-09-04, deployed.** Taken at
the user's direction, and against this watch's standing `[DECISION: adherence, not wording]` — so it
was made structural rather than emphatic, which is the only form that decision leaves open. The
finding that justifies it is not "the rule needs to be louder" but that **one hazard sat across
three rules and none of them was the one a session reads while about to run a gate**: this paragraph
named only the redirect shape, the `head`/`tail` ban sits under "Viewing, searching, or editing
files" with a data-loss cost that a gate run does not feel, and the exit-code mechanism sits a
cluster away in "Reading a command's result". The change is one imperative at the right trigger plus
the measurement; the mechanism stays a pointer, per the leanness pass's shape for this paragraph.
Evidence written up in `contributing/global-agents-md.md`, "The `| tail` half of the gate clause".]

[UNVERIFIED: whether it moves the rate. Every prior wording change in this cluster was measured
after the fact against nothing; this one has `~/.local/state/session-bash-audit/2026-09-04.json` to
compare with, so the next sample should run `--compare` and report a verdict rather than another
unanchored figure. If the rate holds at ~20%, that is the fourth independent confirmation that
wording is not the lever here, and the watch should say so as a finding rather than keep testing
it.]
