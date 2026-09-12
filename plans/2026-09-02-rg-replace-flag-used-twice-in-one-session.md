---
status: idea
updated: 2026-09-08
---

# `rg -r`: 32 defective calls a week, and never once the bare flag

Opened on two occurrences in one `ingesta` session; a third arrived from a different repo the same
day. The corpus-wide count that resolved it is in "Measured, 2026-09-05" below — the filename and
the three-occurrence framing above it are kept as written, since plan-docs promotes in place and the
original hypothesis is worth reading beside the number that confirmed it.

## Context

`~/AGENTS.md` carries the rule, under "Viewing, searching, or editing files":

> Do not carry `grep -r`'s flag across with the habit: `rg` is recursive by default and its `-r` is
> `--replace`, so `rg -r <pat> <path>` silently prints matches with the matched text **rewritten** —
> plausible-looking output that is not what the file says.

An `ingesta` session on 2026-09-02 violated it **twice**, three hours apart, with the rule in
context the whole time.

**First occurrence**, searching a vendored reference clone:

```shell
rg -rn --no-heading -i "overdue|is_late|isLate|missed|skipped" "$RESEARCH_HOME/repos/.../src"
```

`-rn` was parsed as `-r n`, so every match printed with the matched text replaced by `n` —
`takenLabel.label = _('n');`, `.status-n { color: … }`. The session noticed, said so to the user,
named the rule, and re-ran without `-r`. Exactly the intended outcome.

**Second occurrence**, three hours later, during that session's own harvest:

```shell
rg -rn --no-heading -i "ripgrep|rg -r|--replace" /home/tdumitrescu/plans 2>/dev/null | head -10
```

It returned nothing. That is consistent with "no matches" and also with a mangled search, and the
session could not tell which without re-running — which it did, correctly, getting the same empty
result.

**Third occurrence, 2026-09-02, this repo**, in a session working through the `~/AGENTS.md` plan
cluster — so a session that had the rule in context, was reading plans _about_ the rule, and had
this very file open minutes earlier:

```shell
rg -rn 'check-rule-prerequisites' --glob '!plans/**' . 2>/dev/null | head -20
```

The output came back naming `inv ai.n` in four files, where every one of them says
`inv ai.check-rule-prerequisites`. It was caught immediately, because `ai.n` is not a plausible task
name and the searched string was conspicuously absent from its own results — the same accident that
saved the first occurrence, not a method. Had the pattern been anything the eye did not expect
echoed back, the corrupted output would have been read as fact, and it was being used to decide
whether a rule's rationale had a documented home.

Two things it adds. It is the **third `-rn`** out of three, which is now the whole sample and
supports the keystroke hypothesis over the belief one. And it happened in a different repo and a
different session from the first two, so this is no longer one session's tic.

**The wording is not the problem.** The rule states the constraint, names the mechanism, and gives
the failure mode. It was read, understood, and cited out loud by the very session that then repeated
the mistake. So this is the third of the three shapes `session-harvest` distinguishes — not a rule
that is wrong, and not one that was reasoned around, but one **simply not followed**, which it calls
a measurement question rather than a rewording one.

**The second occurrence is the interesting one**, and it has a specific shape worth naming: it
happened while the session was searching for prior art _about this very trap_. Whatever mechanism
produces `-rn` is evidently not reached by having just written a paragraph about it.

**What makes it costly is that a mangled search looks like a clean one.** Both occurrences returned
plausible output — the first plausible-but-wrong, the second plausible-and-empty. Neither errors,
neither warns, and an empty result is exactly what a session reads as "nothing owns this finding",
which is the conclusion it was being used to draw.

## Measured, 2026-09-05 — it is a rate, and the keystroke hypothesis is confirmed outright

`session-bash-audit` grew the `rg-replace` counter, so the first open question below is answered by
its existence. Seven days of transcripts, 13,754 Bash calls: **39 tagged, of which 32 are real
defective invocations** — spread across **21 distinct sessions and 4 repos** (`ingesta` 14,
`repo-tasks` 7, this repo 6, `agent-skills` 5). Not one session's tic. Against ~2,590 `rg`
invocations in the same window it is **1.2%** — low-rate, persistent, and machine-wide.

[DECISION: **it is `grep`'s flag string carried over whole, which is the belief hypothesis rather
than the keystroke one.** The distribution is `-rn` × 27, `-ril` × 3, `-rln` × 1, `-rl` × 1, and not
one bare `-r`. That was first read here as closing the belief hypothesis — **wrongly**, and the
correction is the useful part: a `grep` user rarely wants recursion _alone_, so a believer bundles
too, and the absence of bare `-r` is what belief predicts rather than evidence against it. The check
that settles it is what `grep` itself is typed as in the same corpus — `grep -rn` 118×/week,
`grep -rln` 12×, `grep -rlF` 11×. **Every defective `rg` bundle is a `grep` bundle in daily use on
this machine.** So the fix is a translation, and wording can carry a translation.]

[PITFALL: **bare `rg -r <pat> <path>` does not look broken — it looks like the recursive search the
user wanted, which is why the belief survives contact with the output.** `-r` takes `<pat>` as the
replacement, so `<path>` becomes the pattern and, with no path argument left, rg searches the whole
working directory. Probed 2026-09-05: `rg -r config_path sample.txt` in a directory containing
`sample.txt` returned fourteen hits **from a different file entirely**, each with the search term
written over the match. Recursive, non-empty, and containing the string searched for. Exit 0. This
row is absent from the week's corpus, so the rule now covers a form nobody has yet been caught by —
included deliberately, because it is the form whose output would be believed.]

[PITFALL: **the cost is bigger than "the matched text is rewritten", which is all the rule says.**
`-r` consumes the rest of the bundle as its replacement string, so **the flags the caller asked for
never take effect at all** — and that is invisible in the output:

| as typed | replacement | what was silently dropped | what the caller gets                              |
| -------- | ----------- | ------------------------- | ------------------------------------------------- |
| `-rn`    | `n`         | `-n`                      | matches rewritten to `n`, **and no line numbers** |
| `-rl`    | `l`         | `-l`                      | rewritten lines instead of a file list            |
| `-rln`   | `ln`        | `-l`, `-n`                | same, no line numbers either                      |
| `-ril`   | `il`        | `-i`, `-l`                | case-**sensitive** search, lines not filenames    |

Measured live on the corpus's own `-ril` call —
`rg -ril "head/tail|exit-masked|exit code|piping a gate"` over three `plans/` directories returns
**116 rewritten lines**, where the intended `rg -il` returns **13 filenames**. The session that ran
it wanted "which files mention this", got lines, and piped them through `head -20`. Nothing about
116 plausible lines says the search was mangled.

The `-rn` row is the one that matters most by volume: a search whose whole purpose is a `file:line`
citation comes back with no line numbers, so either the citation is dropped or it is invented.]

[PITFALL: **the counter over-reports by ~8%, all in one direction.** 3 of the 39 are not
invocations: two `git commit -m` messages and one `plans.py commit -m` whose text quotes `rg -rn` or
names this very plan file. The regex anchors on `\brg\b` anywhere in the command rather than at a
command-segment boundary, so a corpus that writes _about_ this trap inflates its own count of it.
Filed against the skill, which owns the script; the 32 above is the corrected figure.]

## The wording attempt, 2026-09-05

The clause in `config/agents-md/bash.md` was rewritten rather than the mechanism reached for,
because the measurement above says the habit is a translation error and the old wording never
addressed the shape that occurs.

[DECISION: **the old clause failed on three specific things, not on volume.** Its worked example was
`rg -r <pat> <path>` — the one form that does not appear in the corpus at all — so a reader
pattern-matching on the example was warned about a shape nobody types and told nothing about `-rn`.
It was a prohibition rather than a substitution, against this corpus's own finding that the
strongest form of a rule is the command replacing the habit (the `gh run watch` case in
`contributing/global-agents-md.md`). And it gave no detection signature, which is why all three
occurrences on record were caught by the accident of the searched string being conspicuously absent
from its own results.]

[DECISION: **the replacement is one edit — delete the `r`, keep every other letter — plus a table of
the six real forms and a detection signature.** Stated as an edit it is exercised on every
`grep`→`rg` translation, which is ~150 a week, rather than firing only at the moment of the
accident; that is the structural difference from the four `head`/`tail` rewordings, each of which
restated the same prohibition at a different trigger. Whether that difference matters is exactly
what the next count tests.]

[UNVERIFIED: whether this moves the rate. Baseline is
**`~/.local/state/session-bash-audit/2026-09-05-pipefail-live-rescored.json`** — not the
`…-pipefail-live.json` first named here, which was written by a superseded `audit.py` (see
`contributing/global-agents-md.md`, "The pipe half stopped being true"). Re-count with
`audit.py --days 7 --compare` after a week, and correct for the counter's ~8% prose over-report
until that is fixed. If it has not moved, the `ask`-rule below is the fallback and the wording lever
is spent for this rule too.]

[PITFALL: **the 39/32 split above is a pre-`0165577` figure; the row now reads 46.** The tagged
count rose from 39 to 46 when the same window was re-scored under the current instrument, part
pattern change and part ~10h of real growth. The finding does not turn on the absolute number — it
turns on the bundle distribution, which no commit here touched, and on there being **no bare `-r`**
— but the next reading has to come from the same instrument as its baseline.]

## Two more, 2026-09-06 — the first session measured after the rewording, and it did not hold

A session in this repo, 174 Bash calls, produced **`-rln` once and `-rn` once**, three hours apart.
It is the first sample taken after the 2026-09-05 clause landed, so it is the first evidence about
the lever that plan chose — and it is negative. The session had the new wording in context, quoted
its "delete the `r`" framing out loud when it caught itself the first time, and typed the bundle
again anyway.

Both were caught by the same accident as all three earlier ones, not by the new detection signature:

- `rg -rln --no-messages -i 'proxy|cacert|ca-cert|certificate' <repo>` — every match came back with
  the searched terms replaced by `ln`, so the file list read `from tasks.ln import (` and
  `def test_parse_ln_authenticate…`. Conspicuous, because the corpus being searched was about
  proxies and the word had vanished from its own results.
- `rg -rn 'anchor' tasks/docs.py 2>/dev/null | head -20` — returned nothing, which is
  indistinguishable from "no such function", and the session only re-ran it because it had made the
  same mistake an hour earlier in the same session.

[UNVERIFIED: **this is one session, not the week's re-count the plan asks for** — the corrected rate
against `2026-09-05-pipefail-live-rescored.json` is still owed and is what decides the lever. What
this row establishes is narrower and still useful: the rewording does not prevent the bundle in a
session that has read it, which is the hypothesis the fallback `ask`-rule rests on. Two instances
also make the second bullet's point sharper than the plan could state before — the second occurrence
was caught **because the first had happened in the same session**, which is not a detection method
that generalises to the session that only does it once.]

[NEEDS CLARIFICATION: **which mechanism, if the wording attempt above does not move the rate.**
Three candidates, and the choice is a real trade-off rather than an obvious pick:

- **An `ask` rule on the `rg -r` prefix**, generated by `cli-allowlist/`. It has a property that
  makes it fit unusually well: `rg -r` is a literal prefix of every defective bundle (`-rn`, `-ril`,
  …) and is **not** a prefix of `rg --replace`, so the accident prompts and the deliberate long-form
  spelling stays free. It is not a mechanism firing behind the agent's back either — the agent sees
  a prompt and the user sees the command, which `~/AGENTS.md` calls friction rather than
  prohibition. Against it: that pipeline classifies tools by _capability_ (read_only / write /
  dangerous), and `rg` is read-only however it is spelled. An ask-rule for a correctness trap would
  be the first entry that classifies by hazard-of-misreading instead, which is a new meaning for the
  file.
- **A shell function wrapping `rg`.** Rejected on the standing rule unless something changes: it
  corrects or refuses what the agent typed, which is the shape "Proposing an enforcement mechanism"
  exists to refuse. Worth noting the pipefail precedent does _not_ transfer — that made the shell
  report truthfully about a command it ran unaltered; there is no equivalent here, because `rg`
  genuinely did what the flags said.
- **Nothing, and accept 1.2%.** Defensible for `-rn`, whose output is conspicuously wrong (the
  searched string absent, `n` in its place) and which has been caught by eye all three times it was
  written up. Not defensible for `-ril`, whose output is 116 plausible lines.]

## Recommended direction

The measurement asked for is done, and it named a translation habit rather than a stray keystroke —
so the wording lever was not spent after all, and the rewritten clause is the cheap, reversible test
of it. Re-count in a week against the baseline named above. If the rate holds, the `ask`-rule is the
fallback: it is the only one of the three mechanisms that needs no standing rule bent to allow it,
and its cost is one prompt on a shape occurring about four times a week.

## A sixth, 2026-09-07 — the first one nobody caught in the session that made it

One `-rn`, in this repo, in a 201-call session. What makes it worth a section rather than a tally
mark is that it is the case the row above **predicted and could not yet show**: a session that typed
the bundle exactly once, and therefore had no earlier instance of its own to be alerted by.

```shell
rg -rn --no-heading "import-environment" /etc/xdg/autostart/ /etc/X11/Xsession.d/ /usr/share/gdm/
```

It returned nothing. The session read that as "no autostart entry imports the environment", moved
on, and reached its conclusion by a different route entirely. Nothing surfaced the typo for the rest
of the session; the harvest's own `audit.py` run found it, roughly forty calls later.

**The detection signature cannot fire on a zero-match search, and that is a gap in the signature
rather than in the reader.** Every earlier occurrence was caught because output came back with the
searched term replaced — the file list reading `from tasks.ln import`, or a pattern conspicuously
absent from a corpus that is about it. A search with no matches produces no output at all, so there
is nothing for the eye to find wrong: the mangled call and the correct one are byte-identical in
their result. The plan's own second bullet at 2026-09-06 said the same thing about a `-rn` that
"returned nothing, which is indistinguishable from 'no such function'" — but there the session
re-ran it because it had made the mistake an hour earlier. Take that crutch away and the occurrence
simply stands.

Re-run correctly afterwards, the search still exits 1 with no matches, so **the conclusion the
session drew was right** — `-r` rewrites output and does not affect matching, so a zero-match search
is the one case where the bundle is harmless to the answer while being invisible to the reader. That
is not reassurance: it means the harmless case is also the undetectable one, and the session cannot
tell which case it is in without re-running.

[UNVERIFIED: whether that generalises — a zero-match `-r` bundle is harmless, and a matching one is
both harmful and self-announcing. If it holds, the detection signature only ever fires on the
occurrences that were going to be caught anyway, and the residue is exactly the invisible half. That
would move the argument for the `ask`-rule above from "the wording does not prevent it" to "no
reader-side signal can", which is a stronger case than the plan currently makes and rests on one
observation. **Sharpened 2026-09-08 by the seventh occurrence below**, which had matches, announced
itself within one call, and was re-run correctly — a second observation on the matching side, and
still one on the zero-match side.]

## A seventh, 2026-09-07 — and the post-rewording tally is four, not three

One `rg -rn --stats -l`, in this repo, in a 270-call session — a different session from the sixth,
which ran the same day in the same repo. Recorded as sample 16 of
`plans/2026-09-02-agents-md-adherence-sample-corpus.md`, where it is the single miss on the best
adherence row that corpus holds: every other counter came in at or near zero and this one did not.

`-r` ate the `n`, so the requested flags never applied. **It was caught within one call, and by the
signature rather than by luck** — the output shape was wrong for what had been asked, which is the
documented tell working as designed rather than the searched string happening to be conspicuous in
its own absence. The search was re-run correctly and the conversation said so.

**The count is four, not three.** The filed plan that brought this row in called it the third
occurrence against a session holding the rewritten clause, counting the two in the 2026-09-06 row
and missing the sixth above — which landed the same day, in the same repo, from another session.
Written out, the four post-rewording occurrences and what caught each:

| when       | bundle | caught by                                                    |
| ---------- | ------ | ------------------------------------------------------------ |
| 2026-09-06 | `-rln` | output shape — the searched word absent from its own results |
| 2026-09-06 | `-rn`  | the session's own earlier instance, an hour before           |
| 2026-09-07 | `-rn`  | **nobody** — zero matches, found by the harvest's audit      |
| 2026-09-07 | `-rn`  | the detection signature, within one call                     |

So the rewriting has been in force for four occurrences across three sessions, and the rate it was
meant to move has not been re-counted yet — that measurement is still owed and is still what decides
the lever. What the four do settle is the shape of the residue: **three of four were caught, and the
one that was not is the one with no output to look at.** That is the same split the `UNVERIFIED`
above predicted, now on four observations rather than one, and it says the fallback `ask`-rule would
be buying exactly one case in four — the invisible one, which is also the one that has so far cost
nothing.

## Eighth and ninth, 2026-09-08 — typed by the session merging this plan, twice

The session that absorbed the filed rows above and wrote the table on this page produced
`rg -rn --stats -c` about twenty minutes after committing it, and `rg -rn --stats -l` roughly ten
minutes after that. Both were self-caught immediately, announced in the conversation, and re-run
without `-r`; both re-runs returned the same result, so neither conclusion was affected.

That is the corpus's authoring-and-breaking shape at its shortest interval on record — minutes
rather than the same day — and this plan is where the interval is smallest, since the trap and the
text about the trap are the same subject. It is worth writing down here rather than only in the
corpus, because it costs the plan one of its own claims.

[PITFALL: **"the session's own earlier instance" is a detection aid, not a deterrent, and these two
separate the roles.** The 2026-09-06 row's second occurrence was caught _because_ the first had
happened an hour earlier, and this plan has since leaned on that as the thing that saves a repeating
session. Here the first occurrence was caught, named out loud, and corrected — and the second
followed anyway, ten minutes later, from a session that had just written the correction. So a prior
instance in the same session raises the chance of noticing the next one and does nothing at all to
prevent it. Every mechanism this plan has considered on the reader's side is a detection mechanism;
nine occurrences in, **not one prevention has been observed from any wording, any authorship, or any
amount of immediately prior awareness.** That is the strongest argument the `ask`-rule has yet had,
and it arrived from the plan's own author.]

[DECISION: **they are in the corpus, as sample 17.** The condition this asked for was met a few
hours later: that session was harvested at a recorded boundary (`2026-09-08T12:05:54+03:00`) with
the instrument named (`9ae8772`) and `pipefail` confirmed, so the row carries all three things the
corpus requires and `rg-replace-bundle = 2` sits in it as a scored MISS. The denominator turns out
to matter here: **2 in 212 calls**, against roughly 2,590 `rg` invocations a week machine-wide at
1.2%, so this session ran the trap at close to the machine's own rate rather than unusually hot —
which is the context an occurrence count alone cannot give, and the reason to prefer the row over
the tally.]

## A tenth, 2026-09-08 — carried here from the hidden-paths plan on its retirement

`rg -rln --hidden '<pattern>' <path>`, typed while searching for the hidden-paths plan itself. `-r`
ate `ln` as the replacement string, so the matched text was rewritten to `ln` and the file list that
`-l` was asked for never appeared.

It was filed as a `[DEFERRED:]` inside the now-retired
`plans/2026-09-08-hidden-by-default-for-repo-searches.md`, whose author noted it belonged to this
clause rather than to that plan and kept it only so it would not be lost. Moved here on that plan's
retirement, which is the mechanism working as intended: a deferred item blocks deletion until it has
a home that stays.

**It changes nothing about the tally's shape and confirms the detection signature.** The
`~/.agents/AGENTS.md` table predicts this exact row (`rg -rln` → `-r` eats `ln` → rewritten lines
and no line numbers), and the session caught it by the documented tell — its own flag letters
appearing where the matched text should be. So the wording continues to describe the failure
accurately and continues not to prevent it, which is the finding this plan has been accumulating.
