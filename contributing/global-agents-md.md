# `~/AGENTS.md` — rationale and evidence

Companion to the [`config/agents-md/`](../config/agents-md/README.md) fragments, which are assembled
into `~/AGENTS.md` (and its `~/.claude/CLAUDE.md` symlink) on this machine — `[packages.agents-md]`
in `setup.toml`, redeployed by `inv deploy.all --name agents-md` or `inv tools.install`. The
deployed file is never edited directly, and neither is any one fragment without checking that
directory's `README.md` for which one owns the rule.

That file is loaded whole into every session in every repo, so each rule there holds only what earns
always-loaded space: trigger + rule + one clause of why. Everything else about a rule — dated
confirmations, reproductions, rejected alternatives, the story of how it was learned — lives here,
under a heading matching the rule's own, so rule and evidence stay findable from each other by name.
This file is deliberately exactly one reference hop from `~/AGENTS.md`; don't chain it onward to a
third file (per Anthropic's skill-authoring guidance, files reached through nested references get
partially read).

Design and research behind the split: the "Why the deployed file is shaped this way" section below
(extracted from the now-retired `plans/2026-08-23-global-agents-md-leanness-pass.md`).

## Admitting a new rule

A new rule enters `~/AGENTS.md` — i.e. one of the `config/agents-md/` fragments — only if it:

1. **States its trigger** — the situation that fires it, named in its heading. A heading is a
   retrieval cue, not navigation; "Project conventions" is a topic, "sudo" is a trigger.
2. **Doesn't duplicate an existing rule** — a variant extends the existing rule's section rather
   than adding a new one. Overlapping near-duplicate rules are a measured driver of degraded
   adherence, not just clutter.
3. **Puts its evidence here, not inline** — dated confirmations and reproductions go in this file
   under a matching heading.

There is no word budget or mechanical gate; the external reference points for review are ≤200 lines
and ≤15 rules. Tier placement: a rule whose miss is silent and expensive stays in `~/AGENTS.md`
regardless of size pressure; a rule with a sharp, statable trigger whose miss is cheap and
recoverable may live in a skill instead — but moving an existing rule out of the always-loaded set
needs the same per-rule user approval as deleting it. Nothing in the file is deleted without asking.

The intake side of this — deciding whether a candidate is durable at all and which home (repo
`AGENTS.md`, skill, plan, this file) it belongs to — is
`plans/2026-08-22-memory-to-agents-md-migration-sweep.md`'s taxonomy; these criteria are the
admission gate for the candidates that taxonomy routes here.

## Why the deployed file is shaped this way

Researched 2026-08-23 for the leanness pass that restructured the file from 30 flat sections / 6,053
body words to 6 trigger-clustered sections of trigger-named rules. The findings that drove each
structural choice:

- **Size.** [Anthropic's CLAUDE.md guidance](https://claude.com/blog/using-claude-md-files) says
  concise and human-readable; secondary write-ups of Anthropic engineers' practice put the working
  limit near **200 lines / 15 rules**
  ([XDA](https://www.xda-developers.com/your-claude-md-is-probably-wrong-how-anthropics-engineers-structure/),
  [betterclaw](https://www.betterclaw.io/blog/agents-md-best-practices)). The load-bearing finding:
  **bloated instruction files cause models to ignore instructions wholesale**, not selectively
  filter the irrelevant ones ([morphllm](https://www.morphllm.com/agents-md-guide)); and
  [Anthropic's context-engineering post](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  — recall degrades as context grows, so aim for the minimal set that fully outlines expected
  behavior ("minimal does not necessarily mean short"). Those numbers are review reference points,
  not a gate — the discipline lives upstream, in the admission criteria above.
- **Clustering.** Clear markdown section boundaries measurably improve adherence and prevent
  "instruction bleed" between rules sharing vocabulary. Position is **not** a lever: the
  instruction-following literature found no consistent relationship between position and follow rate
  ([arXiv 2511.13900](https://arxiv.org/pdf/2511.13900),
  [arXiv 2510.10276](https://arxiv.org/html/2510.10276v1)) — don't reorder for primacy/recency.
- **Merging near-duplicates.** Conflict between overlapping instructions is a primary driver of
  degradation as instruction count grows ([arXiv 2510.14842](https://arxiv.org/abs/2510.14842),
  SCALEDIF) — real but modest (~4–7pp), so dedup/merge is the change most likely to improve
  adherence, worth doing without overselling.
- **Evidence out of the deployed file.** Instructions compete for attention with inline narrative
  ([arXiv 2601.03269](https://arxiv.org/html/2601.03269v1)) — relocating provenance here buys
  adherence independent of the token saving. This file exists because of that finding.
- **What transfers from
  [skill authoring](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices):**
  progressive disclosure (the deployed file is the overview, this file the on-demand detail);
  references one level deep (why this file must not chain onward — nested references get partially
  read); a TOC for reference files over 100 lines; consistent terminology; no time-sensitive info
  inline; concrete examples over abstract prose; degrees of freedom matched to fragility (`sudo -A`
  is low-freedom/exact, design rules are high-freedom/heuristic); and when a rule is observed being
  missed, **strengthen its language rather than lengthen its explanation**.
- **Three tiers.** Tier 1, `~/AGENTS.md`: rules that can fire on any turn or whose miss is silent
  and expensive — paid every session. Tier 2, a skill: sharp statable trigger, cheap recoverable
  miss — kept small because skill descriptions under-trigger (`agent-skills`'
  `plans/2026-08-22-skill-trigger-quality-review.md`). Tier 3, this file: free until read.

## Re-measuring the deployed file

The two commands behind every measurement in the leanness pass, so a later review compares like with
like. Landed shape 2026-08-23: ~2,500 body words, 6 clusters, 30 rules, 294 lines, provenance share
0%. Re-cut 2026-08-26 into three fragments and eight clusters; measure the **assembled** result, not
one fragment, since that is what a session actually loads. Measured straight after that re-cut:
4,326 body words, 8 clusters, 37 rules, 446 lines — **well past the ≤200-line / ≤15-rule reference
points, and grown by ~1,800 words since the leanness pass** without a review in between. The split
did not cause that (it moved rules, it did not add any); it made it visible. Tracked as
`plans/2026-08-26-agents-md-leanness-pass.md`, with the per-cluster breakdown.

```shell
# per-section word count, largest first
python3 -c "
import re
from tasks import deploy
m = deploy.lookup('~/AGENTS.md')
secs = re.split(r'^## ', deploy.expected_bytes(m).decode(), flags=re.M)[1:]
rows = [(len(s.split(chr(10), 1)[1].split()), s.split(chr(10), 1)[0]) for s in secs]
for w, h in sorted(rows, reverse=True): print(f'{w:5d}  {h[:70]}')
print(f'--- {sum(w for w, _ in rows)} words in {len(rows)} sections')
"

# share of words in provenance-bearing sentences (sentence-granularity: treat as a floor)
python3 -c "
import re
from tasks import deploy
m = deploy.lookup('~/AGENTS.md')
body = re.sub(r'\`\`\`.*?\`\`\`', '', deploy.expected_bytes(m).decode(), flags=re.S)
sents = re.split(r'(?<=[.!?])\s+', body.replace(chr(10), ' '))
prov = re.compile(r'2026-\d\d-\d\d|Confirmed|Reaffirmed|Validated|Observed as a real|Caught live|Concrete instance|Example:')
tw = sum(len(s.split()) for s in sents)
pw = sum(len(s.split()) for s in sents if prov.search(s))
print(f'{pw} of {tw} words ({pw*100//tw}%) in provenance sentences')
"
```

## Contents

- [Bash & the CLI allowlist (cluster intro)](#bash--the-cli-allowlist-cluster-intro)
- [What this setup provisions (cluster intro, retired 2026-08-30)](#what-this-setup-provisions-cluster-intro-retired-2026-08-30)
- [Composing a Bash call](#composing-a-bash-call)
- [Viewing, searching, or editing files](#viewing-searching-or-editing-files)
- [Running a command against a different repo than the session's project](#running-a-command-against-a-different-repo-than-the-sessions-project)
- [Editing `~/.claude/settings.json` (or similar) in auto mode](#editing-claudesettingsjson-or-similar-in-auto-mode)
- [git fetch/push needing an SSH key](#git-fetchpush-needing-an-ssh-key)
- [A narrow check grows into design work](#a-narrow-check-grows-into-design-work)
- [Designing a uv tool-install or shared-dependency mechanism](#designing-a-uv-tool-install-or-shared-dependency-mechanism)
- [Installing a tool on this machine](#installing-a-tool-on-this-machine)
- [About to author content, config, or a workaround from scratch](#about-to-author-content-config-or-a-workaround-from-scratch)
- [Choosing a tool or library](#choosing-a-tool-or-library)
- [About to ask the user something factual](#about-to-ask-the-user-something-factual)
- [Writing conventions into a shareable skill or template](#writing-conventions-into-a-shareable-skill-or-template)
- [Adding a CLI flag](#adding-a-cli-flag)
- [Proposing an enforcement mechanism for agent behavior](#proposing-an-enforcement-mechanism-for-agent-behavior)
- [Naming around a collision](#naming-around-a-collision)
- [Reading a command's result](#reading-a-commands-result)
- [Generalizing from a sample to a set](#generalizing-from-a-sample-to-a-set)
- [Force-pushing, or asking what a remote actually has](#force-pushing-or-asking-what-a-remote-actually-has)
- [Fragments are subjects, dependency is a label](#fragments-are-subjects-dependency-is-a-label)
- [Committing to a repo that is or might become public](#committing-to-a-repo-that-is-or-might-become-public)
- [The permission model in force](#the-permission-model-in-force)
- [Where durable knowledge goes](#where-durable-knowledge-goes)
- [Choosing a mechanism for agent instructions, skills, or tools](#choosing-a-mechanism-for-agent-instructions-skills-or-tools)
- [Unexplained git/file state in a working tree](#unexplained-gitfile-state-in-a-working-tree)
- [Regenerating a file from a canonical source](#regenerating-a-file-from-a-canonical-source)
- [Verifying behavior in a repo with test coverage](#verifying-behavior-in-a-repo-with-test-coverage)
- [Formatting a date or decimal in a shell script](#formatting-a-date-or-decimal-in-a-shell-script)
- [About to commit](#about-to-commit)
- [Committing multi-part work](#committing-multi-part-work)
- [Invoking a venv tool in the session's own project](#invoking-a-venv-tool-in-the-sessions-own-project)
- [Something the user wrote looks like a typo or mental slip](#something-the-user-wrote-looks-like-a-typo-or-mental-slip)
- [Ending a turn with a next step](#ending-a-turn-with-a-next-step)

## Editing `~/.claude/settings.json` (or similar) in auto mode

Confirmed directly 2026-08-23: a `python3 -c "..."` one-liner making a temporary, explicitly
user-approved edit to `~/.claude/settings.json` was denied outright by auto mode's background
classifier both before and after the user said "I will approve it" — auto mode has no per-call
interactive step for that approval to land on. The Edit tool, which goes through a separate
permission path, was not blocked for the identical change.

## Committing to a repo that is or might become public

Measured 2026-08-28, and the reason the rule exists at all: an agent published, in a public repo, a
plan tabulating six employer/client root directory names plus one client's internal project path,
and a second public repo had four work email addresses committed inside a listing of SSH key
filenames. Both were written by agents with no rule telling them not to. Moved here from the
deployed file 2026-08-30 — it had been the largest block of inline provenance left in any rule, and
criterion 3 puts a dated confirmation in this file. The rule keeps the instruction and the
mechanical check; what it no longer carries is the incident.

### Data flowing outward to a vendor

Added 2026-08-30, from the user 2026-08-29: _"as a general rule, we dislike data flowing out to
vendors."_ Stated while reviewing `claude plugin eval`'s HTML report, which publishes to claude.ai
by default and needs `--no-publish` to opt out. It extends the public-repo section rather than
opening a rule of its own, because it is the same principle that section already frames — what
leaves this machine, and what cannot be taken back — applied to a vendor feature instead of to repo
content. Its miss is silent the same way: a default-on upload succeeds quietly and is never
discovered by observing normal behaviour.

## git fetch/push needing an SSH key

Both incidents the rule narrates, with their dates, moved here 2026-08-30 — the narratives stay in
the rule, because each names the wrong move the reader is about to make and a session reaching for
`ssh-add` does not take a reference hop first.

Confirmed 2026-08-28: a session read a `Permission denied (publickey)` failure as a missing key, ran
`ssh-add`, and had the user type a passphrase into three dialogs for a key that was already loaded
in the other agent and needed none. Confirmed 2026-08-29: a session applied `ssh.check`'s verdict,
then ran a bare `git fetch` two turns later and got the identical publickey error while every key
sat unlocked in the keyring's agent — the failure the export-vs-prefix distinction exists to
prevent, and the reason that distinction stayed emphatic in the rewrite below. `gh` was verified
unaffected in the same session; it authenticates with its own token.

Rewritten 2026-08-30 to bound the prefix. The section had opened with "Run the `git` command as
normal" and then, two paragraphs down, an emphatic unconditional-sounding imperative: "Prefix
instead, on every call that talks to the remote over ssh." The conditional that governs it — that
`ssh.check` has diagnosed a shell pinned to the empty agent — was stated once, in a heading
sentence, and the emphatic paragraph below outweighed it. Sessions read the prefix as the house
style for pushing and applied it without ever having seen a `Permission denied (publickey)`.

The fix keeps the emphasis where it was earned. The export-vs-prefix distinction stays emphatic,
because the failure it prevents is expensive — a session that exported instead of prefixing saw the
next command fail identically, read it as "the fix didn't work", and went back toward `ssh-add`.
What changed is scope: the default is stated first and more emphatically ("run the plain `git`
command — no prefix and no wrapper"), an explicit line says everything below fires only after a
command has actually failed, and the prefix paragraph now says it applies for the rest of that
diagnosis rather than to every ssh call forever.

**The authoring hazard this is an instance of**, worth checking for whenever this file is open: a
conditional stated once in a heading sentence, followed by an emphatic imperative that reads as
standing advice when quoted or skimmed alone. Rules in this file are retrieved by scanning, so the
most emphatic sentence in a section is the one that fires — if that sentence is the exceptional
branch, the exception becomes the default.

## The permission model in force

### Auto mode withdraws Grep

Measured 2026-08-30. Auto mode's system note asks the session to work through Bash rather than the
dedicated tools, which inverts "Viewing, searching, or editing files". Four sessions had been
measured for their Bash rates without settling which instruction wins. A fifth found the reason the
question could not be answered as one question: `Grep` is **not available** under the note —

```
Error: No such tool available: Grep. Grep is not available in this session —
search file contents with `grep` via the Bash tool instead.
```

— while `Read`, `Edit` and `Write` stayed and were used 17, 35 and 2 times against 164 Bash calls in
the same session. So the search half is not a conflict at all: the rule has no referent, every
`grep`/`rg` call is forced, and counting those as adherence failures measures the harness rather
than the agent. The read/edit half is a real choice and is where a rule can direct behaviour. The
note's own wording hides the distinction by saying to fall back to a dedicated tool "only when Bash
genuinely cannot do the job", which reads as a preference among available tools rather than as one
of them being gone. Full sample history is in
`plans/2026-08-28-auto-mode-contradicts-bash-rules.md`.

## A narrow check grows into design work

Corrected 2026-08-30 — the rule's mechanism contradicted the user. It said to "suggest or move into
plan mode"; the user, 2026-08-29: _"you can write a plan in md, i don't like plan mode because it
creates files in other places than the ones we typically use."_ The intent is right and kept: scope
growing unnoticed is a real failure and the rule should keep warning about it. Only the response
changed, to writing a `plans/*.md` file via the `plan-docs` convention, which puts the design in the
repo it belongs to and under version control. The trailing sentence about "exiting plan mode" was
reworded to match, since there is no longer a mode to exit; the approval signal it describes
("Implement and document …") is unchanged and still correct.

## Where durable knowledge goes

Retitled 2026-08-30 from "Saving to cross-session memory". The rule it documents had itself been
renamed and moved out of the "Claude Code specifics" cluster (see the 2026-08-29 entry below), and
this heading was left behind naming the old trigger — so the rule and its evidence, which this file
keeps findable from each other by name, no longer matched. Nothing else changed.

Confirmed 2026-08-22: auto-memory is a separate `memory/` folder per project directory —
`repo-tasks`, `power-user-linux-setup`, `scaffoldapy`, and the `*-polite-mcp` repos each had their
own, none shared — so even a general cross-repo preference saved there is invisible everywhere else.
The same session found ~30 accumulated entries, several duplicating `~/AGENTS.md` or existing skills
verbatim; the full migration story is `plans/2026-08-22-memory-to-agents-md-migration-sweep.md`. The
underlying reason `AGENTS.md` beats memory (reviewable, one source of truth instead of N per-project
copies) applies across repos exactly as it does within one.

Ruled absolute 2026-08-29, by the user: no memories, for any harness, for any project, for any
reason — project data and user-wide practices must not be vendor-locked. The rule was rewritten
2026-08-30 to say that flatly, and moved out of the "Claude Code specifics" cluster into "Where
durable knowledge goes", because sitting under a vendor heading made it read as a note about one
product's feature rather than a general routing rule. The carve-out stated in the same breath is
harness **configuration** (`settings.json`, hooks, keybindings), which describes the tool rather
than the work. Stating the mechanism instead of the prohibition is what previously let a session
reason its way to an exception, so the wording leads with the ban and names the three destinations
that replace it.

## Choosing a mechanism for agent instructions, skills, or tools

Admitted 2026-09-02, from the leanness pass's parked list, where it had waited since 2026-08-26 for
that pass to close. It is the **general form of the rule above**, which is why it took a heading
rather than extending it: "never a harness's own memory store" is one instance of a constraint that
has to fire before a design exists, and a rule filed under where knowledge goes cannot reach a
session choosing a mechanism to build on.

The vocabulary — `AGENTS.md`, Agent Skills, MCP — is not a preference among equals. Each is a
cross-tool convention with more than one implementation, so work expressed in it survives a change
of harness; a vendor mechanism does not, and the design built on it is thrown away rather than
moved. The admissible use is **plumbing**: a `settings.json`, a hook, a keybinding, anything that
makes one agent work better on this machine without carrying instructions or knowledge. Plumbing
versus carrier is the same distinction the memory rule draws as configuration versus work, one level
up.

Tier 1 on the admission criteria: it can fire on any turn in any repo, and the miss is silent and
expensive — the design reads as finished and works, right up until a second harness is onboarded. No
topic-owning skill covers it, so there was nowhere else for it to go. The constraint was first
stated by the user during the artifact-authoring work, after a design had nearly been built the
other way; that near-miss is the evidence, and there is deliberately no measured rate behind this
one.

## Fragments are subjects, dependency is a label

Landed 2026-08-30. `config/agents-md/` went from three fragments split by dependency to seven split
by subject — `preamble.md`, `agent-knowledge.md`, `git.md`, `bash.md`, `research.md`,
`verification.md`, `collaboration.md` — each owning the single `##` cluster named after it. What a
rule _assumes_ moved onto its heading as a label: `[Claude Code]` on nine rules, `[needs <thing>]`
on six, nothing on the rest.

**Why a dependency partition was rejected.** All 38 rules were classified by what they depend on,
and about ten turned out to be a portable principle wearing a local instantiation — "About to
commit" is universal and names `inv quality.precommit`; "Committing to a repo that is or might
become public" is universal and names `plans.py scan`. A rule may not live half in one fragment and
half in another, so any dependency partition forces each of those to a side, and filing a universal
rule under PULSE because it names an `inv` task misdescribes when it fires. A label is the only form
a rule can carry without moving.

**The whole-`##`-section constraint stopped binding rather than being dropped.** With fragment and
cluster both keyed to subject, each fragment contributes exactly one cluster, so the rule is
satisfied by construction. It never needed relaxing; it needed the two axes to stop disagreeing.

**The vocabulary is closed at two shapes**, enforced by `tests/unit/test_agents_md.py`. An open one
is how a label set stops meaning anything: nothing tells a reader whether `[Claude]` and
`[Claude Code]` are the same claim, and no grep can either. A coarse `[PULSE]` was rejected for the
same reason a checkable claim is worth more — `[needs direnv]` can be verified against
`[packages.direnv]`, and a future "someone disabled direnv" warning has something to read. That test
earned itself immediately: `[needs plan-docs]` was written first, looked like a package name, and is
a skill arriving through `[packages.agent-skills]`; a label whose form implies a check it does not
pass is worse than no label.

**Which rules got a `[Claude Code]` label was a judgement, and the sweep that looks like it would
answer it is wrong.** Seven of `portable.md`'s 29 rules named Claude Code tools, in three different
ways, and the difference decides how the rule should read once labelled:

- **Incidental** — the name swaps out for free ("a `Read` of the log", "copy to the scratchpad").
- **Mechanism-named** — the action is portable and the tool is not; both `AskUserQuestion` rules.
- **Harness-factual** — genericising makes the claim false or vague: "the Bash tool reports it
  whenever it is non-zero", the whole of "Viewing, searching, or editing files", "don't reach for
  plan mode".

Three apparent hits were ordinary English and must not be "fixed" — "Write about that work by its
shape", "Read the SHA", "Read-only `git -C` verbs". A mechanical pass over capitalised tool names
flags all three, which is the standing argument against doing any of this as a sweep.

**The prerequisite warning reads the labels, and that is why it was cheap.** `[needs <thing>]` gave
`inv ai.check-rule-prerequisites` something to parse; before the labels there was nothing to read,
which is why the check was deferred rather than designed up front. Two choices in it are worth
keeping:

- **Config-level, not presence-level.** It answers "is this package still declared and enabled",
  using the same precedence `inv setup` does (`setup.toml` → `overrides.toml` →
  `PULSE_EXCLUDE_TAGS`). Whether the binary is on disk is `inv verify.all`'s job. Keeping that out
  is what lets the task invoke nothing — which matters, because the allowlist auto-approves
  `<ns>.check-*` on the naming convention alone, so a `check` task that ran commands would run them
  unprompted. The bar is "declared **and enabled**": 29 packages carry `enabled = false`, so
  declaration alone was barely a check.
- **The deterministic half is a unit test; the rest stays on demand.** "Does `setup.toml` declare
  this, not disabled" depends only on committed content, so CI catches it on the breaking commit.
  `verify.all` was rejected as the home: it aborts on first failure, and a container or WSL profile
  excluding the `dev` tag makes `[needs direnv]` legitimately false, so gating there would break
  `inv setup` on a correctly configured machine.

**Verifying a re-cut that is supposed to change no content needs its own method.** All 38 rule
bodies were snapshotted before the move and diffed against the assembled output afterwards: same 38
headings, zero bodies differing. The first run of that diff reported **all 38 changed**, and the
diff was what was wrong — the deployed format leaves a leading newline the fragments do not.
"Everything changed" is nearly always a measurement bug rather than 38 real ones, and reading a
single diff concretely settled it in one command.

**The old fragments stayed tracked after being deleted from disk, and the gate caught it rather than
the tests.** `repo-tasks`' `link_check` walks `git ls-files "*.md"`, so it tried to read a fragment
that no longer existed and raised `FileNotFoundError`. Staging the deletions fixed it. Generalises
past this repo: a "which files exist" check sourced from the index disagrees with the working tree
for exactly as long as a deletion sits unstaged.

Worked out in a plan retired 2026-09-02; `plans.py archive --search "the axis they leak across"`
reads it back.

## What this setup provisions (cluster intro, retired 2026-08-30)

Renamed 2026-08-30 from "This machine & this setup". The old name and its intro ("rules that are
true because of how this particular machine and this user's repos are set up") described the cluster
as personal to one box, and that is not what is in it: measured against `setup.toml`, five of its
seven rules depend on something PULSE installs — `[packages.askpass-zenity]` supplies both the
helper and the `SUDO_ASKPASS` export, PULSE writes the `~/.zprofile` ssh-agent picker, `setup.toml`
_is_ the tool-installation rule, `[packages.direnv]` and its zsh hook are why the bare venv command
resolves, and `inv ai.install-skills` installs the skills. Only the locale rule (a desktop regional
setting PULSE does not create, though PULSE's own `config/statusline-command.sh` works around it
throughout) and the personal-repo push rule are outside that.

The distinction is not cosmetic. Stated by the user 2026-08-30: _"harness settings are not just for
this machine, they are for pulse as a holistic approach to development"_, and _"i'm not planning to
have anything machine-specific for myself in terms of agents.md — everything i change in my
workflows fundamental enough to require an agents.md or skill rule will be integrated in pulse to
happen by default as a prerequisite."_ So "this machine" was never a category the file should have
had, and calling the cluster that invited rules to be filed by where they were noticed rather than
by what they depend on. The admission test is now the dependency: does this hold because PULSE put
something there?

Superseded the same day, and worth keeping only as the step that made the next one visible. Stating
the admission test as a dependency question exposed that the fragments were the dependency axis
while the clusters were the subject axis, and that a fragment contributing whole `##` sections
stopped the two from varying independently. The resolution was to key both to subject: the cluster
no longer exists, its rules were redistributed by what they are about, and what a rule depends on
became a label on its heading — see "Fragments are subjects, dependency is a label" below.

## Bash & the CLI allowlist (cluster intro)

Rewritten 2026-08-24 around `acceptEdits` mode, after a four-day transcript audit (3,956 Bash calls;
method and numbers in the `session-bash-audit` skill's `references/research.md`). The previous intro
described prefix matching correctly but never said which permission mode the machine runs, and the
mode turned out to be the variable that mattered: every session in the audit window ran in `auto`
mode, where a classifier decides unmatched calls and the harness injects a system reminder telling
the agent to prefer `cat`/`sed -n`/heredocs over Read/Edit — the inverse of the rule below it. No
wording in this file can out-rank a live system-prompt directive, so the fix was the mode
(`claude_default_mode` in `setup.toml`), and the intro now states the mode so the rules read as a
description of the system in force rather than as preferences. The "global option before the verb"
clause records the one real ask-rule bypass found: `Bash(git push:*)` does not match
`git -C /path push` (81 such calls in the window, all run unprompted under auto mode's classifier).

## Composing a Bash call

Rewritten 2026-08-24 from "prefer several simple calls" to "one command per call" with a closed list
of two permitted chain shapes, after the audit measured 64–71% of Sonnet/Opus calls chained (13–24%
five or more parts) with the previous wording in force. The earlier rationale was prompt friction
only; under a mode that never prompted, the model read "friction cost, never a prohibition" as "no
cost" and chained freely. The new text names the costs that hold in every mode — one output and one
exit code per call, parallelism already free, `echo "=== ==="` as the tell — because a rule whose
reason has evaporated is a rule that gets ignored, however strongly worded. The own-repo `cd`
clause: 114 `cd <session's own repo> && …` calls in the window, cargo-culted from the documented
cross-repo form.

The rule's earlier form claimed a chained command can never match an allow rule
("`cd some/dir &&
git status` no longer starts with `git status`, so it can't match
`Bash(git status:*)`") and banned `&&` outright. Corrected 2026-08-23 on two independent sources: a
live test (`cd /tmp && git
status` and `cd /tmp && cat /etc/hostname`, neither prompted) and
`code.claude.com/docs/en/permissions.md`'s "Compound commands" section, read in full twice in
separate sessions — Claude Code splits on `&&`, `||`, `;`, `|`, `|&`, `&`, and newlines, and
evaluates each subcommand against the rules independently (newline being a recognized separator also
means `\` line continuations have zero effect on matching). The `bash -c` claim survives because the
outer `bash` is itself classified dangerous (`cli-allowlist/rules/bash.json`) and renders as `ask`.

Held conservative rather than loosened further:
`plans/2026-08-22-compound-command-permission-audit.md` still carries an unexplained report of a
write-classified command executing without a prompt inside a compound command — until that
incident's mechanism is understood, the guidance stays "prefer simple separate calls" even though
the documented per-subcommand model would permit more chaining.

The "friction cost, never a prohibition" clause exists because the old ban was obeyed literally: an
agent in a `repo-tasks` session concluded legitimate cross-repo work was impossible (the fix needed
one chained command, chaining was "banned") and reported it as a limitation instead of paying one
approval prompt — abandoning real work to dodge friction, strictly worse than any number of prompts
(`plans/2026-08-23-cross-directory-command-execution.md`, retired).

The redirect shape (`<cmd> > <file> 2>&1; echo $?`) was dropped from the permitted list on
2026-08-25. It had been admitted the day before as the safe substitute for `2>&1 | tail`, and the
user then reported "a LOT of invoke tool output redirects, exit codes, redirected output reading
later instead of default agent tools" across three repos. The rule was self-contradictory: this
section sanctioned the form, "Viewing, searching, or editing files" said not to append
`; echo "EXIT=$?"`, and "Reading a command's result" recommended `command; echo $?` — so models
followed the sanctioned form for every gate (the audit's `echo-exit` pattern rose from 0 to 10–11%
of Fable/Opus calls in the day it was in force). Verified live 2026-08-25 before rewriting: a plain
`inv quality.precommit` run reports nothing on exit 0 and an explicit `Exit code N` otherwise, and a
1 MB output was saved to a file by the harness with the path in the result — every property the
redirect form was reaching for, in one call instead of two and with no `$VAR`-target prompt. The
second driver was the 1 MB itself: 4,145 basedpyright warnings on a green run, which any model will
try to keep out of context. That was a gate-output problem rather than a wording fix, and it was
fixed at the source — this repo is at zero warnings with `failOnWarnings: true`, so the gate's
output fits one tool result again. See `repo-tasks`' `contributing/type-checking.md` for how.

Merged 2026-08-30, in the leanness pass's first round
(`plans/2026-08-26-agents-md-leanness-pass.md`). Two changes, both removing a claim's _second_
statement rather than the claim:

- **The redirect paragraph lost its own explanation of what the Bash tool already reports**, keeping
  the imperative and pointing at "Reading a command's result", which states it in full. The same
  claim had been written out in three rules across two clusters — this section, "Viewing, searching,
  or editing files", and "Reading a command's result" — which is the configuration recorded below as
  having previously made models follow the wrong one.
- **The cwd sentence was a contradiction, not a duplication, and was resolved against this file.**
  It asserted that "`cd` sticks: cwd persists into the following calls on current builds"; the
  measurement under "Running a command against a different repo" below records both behaviours in
  one session on one build, and that rule says to assume neither. The confident half was the stale
  one and now reads "treat cwd as unknown". The practical consequence it existed to state — the next
  call assuming the session repo must re-establish it — is unchanged.

### The `git -C <own repo>` clause

Admitted 2026-09-02 from the leanness pass's parked list, as a clause rather than a rule: it is the
existing `cd` ban failing in a way the ban itself causes, so it belongs where the ban is stated and
the rule count is unchanged.

**The rule was creating the behaviour it forbids.** Measured 2026-08-29 by `session-bash-audit` over
two days and 2,077 calls, after the user corrected a session mid-task ("you don't need cd, you're in
this repo"): `cd` into the session's own repo occurred **14** times — agents comply — while
`git -C <own repo>` occurred **89**, up to 18% of one session's calls. The same rule that bans the
`cd` recommends `git -C <path>` as the directory-scoping option for a cross-repo step, so agents
reach for that flag against their own repo six times as often as they ever ran the banned form.

Two later samples say the rate is a **per-session disposition rather than a machine-wide trend**:
23% of one `agent-skills` session's calls (`cd-own-repo` 0% in the same session, so the habit the
rule was written against was fully avoided and its replacement scored worse), against 0% in another
session in the same repo, the same shape of work, the same day's rules. That does not weaken the
clause — one session in five reaching 23% is worth a sentence — but it does mean no wording change
should be judged by the aggregate.

The mechanism named in the rule comes from the second of those sessions: it ran three cross-repo
chains, saw the harness confirm `Shell cwd was reset` each time, and then wrote every later call
defensively with an absolute `git -C`, including calls where cwd had never moved. So the clause ends
on scope rather than on prohibition — a caution outliving the situation that justified it.

## Viewing, searching, or editing files

The `; echo "EXIT=$?"` clause was cut to one sentence 2026-08-30, same round and same reason as
above: the tool-reports-the-exit-code explanation now lives once, in "Reading a command's result".
The prohibition itself is untouched. Worth watching rather than assuming settled — that shape was
measured at 10–11% of Fable/Opus calls in the day a contradictory version was in force, so it is a
rule with a known miss rate, and the finding below says to strengthen language rather than lengthen
explanation when one is missed. What was removed here is neither: it is the third copy of an
explanation, which is the driver the SCALEDIF result names.

The `| head`/`| tail` clause, added 2026-08-24: 1,128 of 3,956 audited calls (29–32% for
Sonnet/Opus) piped tool output through `head`/`tail`; 662 of those were `2>&1 | tail/head/grep`,
which also masks the upstream exit code (364 of them wrapped a quality or test gate); 201 truncated
a search whose purpose was completeness; and 51 times the same command was re-issued with a larger
limit after the truncated view proved insufficient. The habit is context anxiety — the harness
already truncates large output and persists the full text to a file, which the model isn't told. The
clause states that fact rather than just forbidding the pipe, because the previous "Reading a
command's result" rule (exit codes) and "Generalizing from a sample to a set" rule (search
truncation) both existed and neither connected to the reflex.

The redirect-then-filter clause, added the same day from the session that wrote the rule above:
audited an hour later, it had 124 Bash calls at 65% chained and 36% `head`/`tail` — worse than the
Fable baseline it was citing. Two causes. The rewritten file never reached that session (instruction
files load at session start; the auto-mode reminder was still live), which is the documented
mechanism and needs no fix. And with the rule fresh in working memory the habit held anyway, because
nearly every violation was one shape the rule gave no substitute for:
`gate > log 2>&1; echo $?; sed … log | rg … | head` — the permitted capture form with a filter
tacked on to keep a 5,000-line log out of context. The clause names the substitute (Grep/Read on the
log, as a second call) and the reflexive `; echo "EXIT=$?"` that the tool makes redundant. The
`session-bash-audit` script measures the shape as `redirect-then-filter`.

The `rg -r` clause, added 2026-08-26 from a live occurrence. Retiring a plan file meant grepping
every repo for inbound references; the call was written `rg -rn <pattern> <dir>`, reaching for
`grep -r`'s recursive flag. `rg` is recursive by default and `-r` is `--replace`, so every hit
printed with the matched text substituted — real paths came back as `plans/2026-08-25-n.md`. This is
the failure mode the sibling "Reading a command's result" rule is about, one level worse: exit code
0, seventeen hits, output that reads like a normal grep result. It was caught only because the
mangled filename looked wrong; the same slip during a reference sweep that returned _zero_ hits
would have read as "nothing to fix" and left dangling references behind. Placed as a clause on the
existing `rg`-over-`grep -r` sentence rather than a new rule, because that sentence is what invites
the flag to be carried across — criterion 2, a variant extends its rule. Considered and rejected: a
`session-bash-audit` PATTERNS row instead. That skill can measure the rate, but the fix here is one
clause at the exact point of confusion, and a single occurrence is not yet evidence of a rate worth
a row ("rows with no stated cost teach nothing"). Worth adding there if it recurs.

## Running a command against a different repo than the session's project

The hard no-writing clause was added 2026-08-30, on the user's instruction: "we don't act on other
repos any more, unless we have some very complex work that needs back and forth ... if something
needs adjusing in another repo, make a plan." The rule had previously only discouraged _substantial_
work elsewhere, which left every small, obviously-correct edit looking like an exception — and the
session it was given in had just made exactly one: a `session-harvest` session, following that
skill's own "Self-update mechanics" section, edited `agent-skills`, ran its gate and committed
there, all as instructed. The skill was written before `plan-docs` grew `new --for <repo>`, when a
cross-repo commit really was the only way to deliver a fix instead of deferring it; the mechanism
now exists, so the reasoning that justified the commit no longer holds. That correction is itself
owed to `agent-skills` and was filed there rather than made — see
`plans.py archive --search "self-update crosses repos"` if it has since been absorbed and retired.

The clause is stated as absolute rather than proportionate because the failure is silent: a commit
in another repo's tree reads as routine in that repo's own `git log`, so the session that owns the
repo has no signal distinguishing it from its own work, and the natural next action is to push it.
Size is not what makes a cross-repo write dangerous, and "it was only two lines" is exactly the
framing under which one gets made.

The `git -C` clause was re-cut 2026-08-24: read-only `-C` verbs are now rendered as allow rules by
`cli-allowlist`'s `global_option_prefixes`, and the mutating ones are meant to prompt — the earlier
"expect a one-off prompt" framing read as friction to minimize, and under auto mode the prompt never
came at all (see the cluster intro above).

Confirmed directly 2026-08-22/23: running plain `inv`/`pytest` after `cd`-ing into a secondary repo
silently exercised the primary repo's pinned dependency copy of a package under active development
in the secondary repo — direnv's shell hook fires on an interactive shell's prompt/precmd, not
inside a non-interactive `bash -c` invocation, so PATH stayed the primary project's direnv-activated
`.venv/bin`.

Confirmed again 2026-08-23, one layer deeper: even invoking `/path/to/other-repo/.venv/bin/inv` by
absolute path, without changing cwd, still silently ran the **primary** repo's own tasks — invoke
discovers `tasks.py`/`tasks/` by walking up from the current working directory, independent of which
venv's `inv` binary executes. The `pytest` fix (absolute-path binary is enough, because
site-packages resolution depends on the interpreter, not cwd) and the `inv` fix (an actual `cd` is
required) are not the same fix.

The rule's earlier form prescribed the opposite of what now stands: it discouraged directory-scoping
flags and prescribed "run `cd` as its own call, then the command, then `cd` back" — which cannot
work, because the harness resets cwd to the session's primary directory after every Bash call.
Observed twice 2026-08-23: a standalone `cd` into another directory returned "Shell cwd was reset",
and a chained `cd <repo> && .venv/bin/inv …` printed the same reset line after the command ran (i.e.
the chain worked precisely because the `cd` and the command shared one call). Whether the reset is
universal or specific to this harness version/configuration is unpinned; the current guidance holds
either way, which is why it no longer depends on cwd persistence.

Pinned the other way 2026-08-25 (Claude Code, Fable 5 session in `repo-tasks`): after one
`cd <scratch dir> && uvx dunamai …` call, the next three bare calls ran in the scratch dir — `uvx`
answered with the scratch repo's version, then `inv quality.precommit` failed with
`Can't find any collection named 'tasks'` and `rg plans/…` with "No such file or directory" — until
a `cd <session repo> && inv quality.precommit` moved it back. No "Shell cwd was reset" line appeared
on any of those calls — yet a later `cd power-user-linux-setup && PATH=… inv quality.precommit` in
the _same session_ ended with "Shell cwd was reset to …/repo-tasks". The Bash tool's own description
on that build reads "Working directory persists between calls." So both behaviors are real, not even
consistently per build, and the rule now says so instead of asserting either: the durable guidance
(scope by flag, or one `cd && …` chain) is unchanged, and the addition is "after such a chain, cwd
is unknown until re-established" plus the two error messages that reveal a stuck cwd — the failure
looked like a genuinely missing file for one call.

Scoping flags were validated live the same day, all against this repo from a `repo-tasks` session
with no `cd`: `git -C <path> status`/`log`/`add`/`commit` (full commit workflow),
`dprint fmt --config <path>`, `ruff check --config <path>`, `ruff format --config <path>`,
`basedpyright --project <path>` (exit 0), and `<venv>/bin/pytest <abs path>` over a 215-test suite.

Corrected 2026-08-24, a third layer: `cd <repo> && <repo>/.venv/bin/inv <task>` — the form this rule
previously called "the only working form" — still ran the wrong tools. Invoke's tasks are thin
wrappers around `c.run("pytest …")`, `c.run("ruff check .")`, `c.run("basedpyright")`; `c.run`
inherits the caller's environment, so every bare tool name resolved through the **primary** repo's
direnv-activated `.venv/bin`. The result was a phantom test failure that cost real time before the
mismatch was spotted: the target repo's task list running the session repo's `pytest`, its
dependencies, and its plugins. Prefixing PATH is the fix that reaches the subprocesses; pointing at
the `inv` binary never could, because the binary's location says nothing about what its children
resolve. Note this is the case the "Composing a Bash call" rule means by "unless the step genuinely
needs them" — the leading env assignment is load-bearing here, and the approval prompt is the price.

Not every repo has `inv` in its own venv (`scaffoldapy` did not, 2026-08-24), which is why the
`~/.local/bin` fallback clause survives the rewrite rather than being replaced by the PATH prefix.

The "bare `inv` may be either uv tool" clause: `repo-tasks` and standalone `invoke` both provide
`inv`/`invoke` console scripts, and whichever was `--force`-installed last owns the `~/.local/bin`
symlinks (`plans/2026-08-23-invoke-repo-tasks-tool-conflict.md`). The two `inv` failure modes
compose: cwd decides which `tasks.py` is found; the binary decides whether that `tasks.py` can
import `repo_tasks`. Both misses are silent, and `<repo>/.venv/bin/inv` addresses the second for
free.

## About to author content, config, or a workaround from scratch

Reuse-upstream, validated concretely: designing `.gitignore` ownership for a shared dev-tooling
package (`power-user-linux-setup`'s `repo-tasks`/`scaffoldapy`), a prior-art check before drafting a
Python `.gitignore` in-house found that PyCharm's own bundled `.ignore` plugin
(`JetBrains/idea-gitignore`) doesn't maintain its own list either — it generates from
`github/gitignore`, GitHub's officially-maintained template repo. A mainstream, widely-used tool had
already made the identical "don't roll your own" call.

Caught live designing `session-harvest`: an initial internal search (`skills find`/repo grep)
surfaced one loosely-related hit and looked conclusive enough to justify building from scratch — a
real web search then turned up a much closer match (`melodykoh/learning-loop-skill`) that
meaningfully changed the design. A single narrow tool's "nothing relevant" is a weak signal, not a
conclusion.

Tool-native over hand-rolled, the defining instance: choosing `uv python install --default` (which
creates an unversioned `python3` shim shadowing apt's `/usr/bin/python3` on `PATH`) over a
hand-rolled `python`-only symlink that would have preserved a "system `python3` never shadowed"
invariant byte-for-byte. The tool-managed option won after the shadowing risk was verified
theoretical — every `#!/usr/bin/env python3` script on the system was grepped, none needed
distro-specific bindings — citing rule of least surprise, and that the tool's own shim is understood
by `uv python uninstall`/`--reinstall`/upgrades while a raw `ln -sf` is one more thing to
hand-maintain.

## Choosing a tool or library

Research depth, observed as a real pattern rather than a one-off: the user pushed for more depth
twice in one planning session on a monorepo-versioning tool choice, both times because a
search-summary-level survey wasn't considered sufficient to close out the decision.

The agent-audience exception's concrete instance: a data-modeling decision table trimmed from six
routine choices (Pydantic/dataclass/attrs/NamedTuple/TypedDict/msgspec) to two (Pydantic for
boundaries, frozen dataclass for everything else). "Best tool per concern" argued for more
specialized tools; "fewer options for an agent to mimic incorrectly" argued for fewer routine
defaults — the second won because the stated audience was agent-authored code specifically.

## About to ask the user something factual

Confirmed directly 2026-08-23: asked the user to pick a color tier for a newly-released Claude model
("Fable") in a statusline script, framing it as a stylistic choice. The user's reply — "look it up
online, come on" — was a real correction: Fable's actual capability tier (above Opus, per
Anthropic's own docs) was one search away, not something only the user could supply. Re-ran the
research, found the answer, applied it without another round-trip.

## Writing conventions into a shareable skill or template

Piloting researched typing/lint/format tool choices on one real repo before writing them into a
skill surfaced real mistakes pure research couldn't have caught: a lint rule that was pure noise
against that repo's actual deliberate style, a rule that didn't fit the repo's shape at all, and two
config-file footguns that would have silently misconfigured every repo copying the config verbatim.
A skill built straight from research, with no pilot step, would have shipped all of these to every
consumer.

## Adding a CLI flag

The bypass-flag clause's originating incident (2026-08-23): a `--force` on `inv ai.install-skills`
that would have overwritten foreign content was rejected because the `.pulse-source` marker _is_ the
ownership model — a flag overriding it would make ownership mean one thing with the flag and another
without. Stated by the user as "we shouldn't have hacks that make the mental model difficult, unless
something is utterly impractical." Folded into this rule (which previously covered only flag
_shape_) during the leanness pass, as the second §11 candidate admission.

## Proposing an enforcement mechanism for agent behavior

Originating decision (2026-08-23): researched git-hook enforcement of the quality gate was rejected
in favor of skill-level guidance — the user: "i've always been against companies imposing git
precommit hooks for devs. i see no reason to treat a dev differently from an agent." Recorded in
`plans/2026-08-23-git-hooks-for-quality-gate.md`'s decision context; routed here by
`session-harvest` the same day as the leanness pass's third candidate admission, because the
principle is broader than that one plan and outlives its retirement.

**Measured 2026-09-02, and the principle held.** The rejection came with a revisit trigger: if the
docs-commit CI shape recurred at a real rate once the `~/AGENTS.md` "About to commit" rule had been
live a while, the hook design would be reopened. The rule deployed 2026-08-25; the sweep eight days
later across all three repos, reading every failed log rather than counting runs, found **zero
dprint reflow failures** — against 11 in the single day before the skill-level fix and 4 in the ~30
hours after it. So teaching the rule is not merely the preferred lever here, it is the one observed
to work, and that is now the strongest support this principle has.

Two things the sweep would have concluded wrongly if read carelessly, both worth carrying:

- **Count instances, not runs.** Six `repo-tasks` failures looked like a worse post-rule rate than
  the pre-rule one. They were one instance retried across a single evening — one plan file, one
  cross-repo relative link — and the naive count would have reopened a closed question on an
  artifact of retry behaviour.
- **A failure in the same family is not the same shape.** That instance was a docs commit pushed
  ungated, so it belongs to the broader problem, but it failed on `docs.link-check` rather than on a
  formatter, and the researched hook's fast subset runs no link check. The one post-rule instance is
  therefore not evidence for the mechanism that was rejected — a distinction only visible by reading
  the log.

## Naming around a collision

The originating incident: "pulse-setup" was proposed to disambiguate a `~/.config/pulse` clash with
PulseAudio; the full canonical name "power-user-linux-setup" was the right answer — a short alias
that half-repeats the disambiguating word reads as awkward rather than clean.

## Reading a command's result

Measured 2026-08-26, the backgrounding half: `nohup script.sh & disown` and `setsid script.sh &`
both returned non-zero while the script's first statement, a file write, never happened — yet a
plain `cmd &` plus `sleep` in the same call did run. Date moved here 2026-08-30; the rule keeps the
two forms and the reason intermittence is what makes it dangerous.

`basedpyright` hard-errors (exit 3) on a config error while still printing a clean
`"0 errors, N warnings, 0 notes"` summary line — a real regression across three repos went unnoticed
for a stretch of a session because every check was read via `... | tail -N`, and `tail`/`grep` in a
pipeline return their own exit code, not the upstream command's.

Rewritten 2026-08-25 to drop its own `command; echo $?` / redirect-and-check advice: the Bash tool
reports a non-zero exit itself, so the advice produced a chain on every gate run for information
already in the tool result (see "Composing a Bash call" above for the measurement). The rule's point
— a pipe masks the exit code — survives; the prescribed remedy is now "don't pipe", not "add
`echo $?`".

Extended 2026-08-28 (`repo-tasks`) with the non-terminating-wait half, from a live incident rather
than a hypothetical. A session ended four turns by backgrounding
`until [ "$(gh run list --repo … --commit <sha> --limit 1 --json status --jq '.[0].status')" = "completed" ]; do sleep 20; done`
to wait on CI. `gh run list --commit` matches only the full 40-char SHA and returns `[]` — exit 0,
no diagnostic — for the 7-char abbreviation every one of them passed, so `.[0].status` was `null` on
every iteration. Reproduced both directions on gh 2.97.0 while writing this: the abbreviation
returns `[]`, the full SHA returns the run (`--branch main` also returns it, which is what made the
empty result obviously wrong rather than plausibly "no run yet").

Found 2026-08-28 by a `/session-harvest` process sweep: all four still alive, ~36 hours in, each
with a `sleep` child seconds old, having issued on the order of 26,000 API calls between them. Two
things make this worth a rule rather than a footnote about one CLI flag:

- **The failure is unfalsifiable from inside.** A loop testing a condition that cannot be true has
  no error path; it produces silence, and silence is what "still waiting" looks like. Contrast the
  backgrounding failure above, which at least yields _wrong_ state to read.
- **It made the session lie.** The turn closed with "CI is running; I'll report when it lands." That
  was already false when written — nothing would ever land. The user's actual answer (CI green on
  `863ede6`) was available immediately from `--branch`, and went unreported for a day and a half.

The rule as written asks for two cheap things — bound the wait, and run the inner command once
before wrapping it — because either alone would have caught this. Deliberately not a rule about
`gh`: the shape is any poll whose predicate reads a filtered/parsed value that can come back empty.

It names `gh run watch --exit-status` because the strongest form of a rule is the command that
replaces the bad habit, not a warning about it (per the skill-authoring finding above: strengthen
language rather than lengthen explanation). Verified 2026-08-28 against a finished run — returns
immediately with `Run CI (33169261418) has already completed with 'success'` — so it degrades
correctly in the case a hand-rolled `until` handles worst, the work already being done. Its help
text was already sitting in this repo's own `cli-allowlist/help-cache/gh.json`,
`gh run watch && notify-send` example included: the tool that would have prevented the incident was
cached on disk the whole time and never consulted, which is why "About to author content, config, or
a workaround from scratch" applies to a poll loop too.

Swept the three repos for the pattern in committed code at the same time: none. `repo_tasks/ci.py`
uses `gh run list --branch`, the correct filter, and no `until`/`while true` loop exists anywhere
outside these two documentation quotes. The bug lived only in ad-hoc session shells — which is
exactly why it belongs in an always-loaded instruction rather than a lint or a test.

Extended 2026-08-30 with the absence-probe case, the same "convenient surface signal is not the
signal" shape the section already carries. A `repo-tasks` session asked whether an ini key belonging
to an uninstalled pytest plugin was harmless, and probed with
`uv run --no-project --with pytest==9.1.1 pytest` from a shell with the repo's venv active. It
reported `plugins: anyio-4.14.2, socket-0.8.1, cov-7.1.0` and passed — the hoped-for answer, and
wrong: `--with` builds an ephemeral overlay **on top of** the active environment, so `sys.prefix`
was the repo's own `.venv` and the probe measured a machine that had the package all along. The
isolating form (`env -u VIRTUAL_ENV -u PYTHONPATH uv run --no-project --python 3.11 --with …`) gave
the opposite conclusion immediately — a hard error, exit 4. Two properties make it silent rather
than merely wrong: the contaminated run passes, and AnyIO ships a `pytest11` entry point, so mere
presence on the path registers it with nothing in the project naming it. The wrong answer had
already been written into a plan before the user questioned the stated cause.

## Generalizing from a sample to a set

Confirmed live 2026-08-23 — nine modified `cli-allowlist` files were reported as "timestamp-only
churn" after reading one of them (`vim.json`) in full; five carried real upstream version bumps
(`dprint` 0.54.0 → 0.56.1, `twine` 6.2.0 → 7.0.0, and three more), and `--stat` had already shown 27
changed lines against `vim.json`'s 6. Harmless that time only because the conclusion was "leave it
alone" — the identical reasoning behind a discard would have thrown away real data.

Extended 2026-08-24 (`repo-tasks`): the same failure with a self-inflicted sample. A
`rg ... | head -20` run to find every reference to a directory being moved was treated as the
complete list; a file it cut off kept a stale path and failed a test one step later. Repeated in the
same session — the truncation, not the reading, was the constant.

Merged 2026-08-30, first round of the leanness pass. The clause had restated the mechanical rule and
named the same substitute command (`rg -c`, `wc -l`) as "Viewing, searching, or editing files",
which owns it. What is distinctive here is the _inference_ — that your own truncated output is a
sample and stops being evidence about the set — and that is what the clause now says, pointing at
the other rule for the mechanics. The two halves had been drifting toward being one rule written
twice, in two clusters, which is the case criterion 2 exists to catch.

### The constructed-probe clause

Admitted 2026-09-02 from the leanness pass's parked list, as a paragraph on this rule rather than a
heading. The rule already covered a sample you created yourself by truncating your own output; the
new half is that a **probe input** is the same thing, and that a green result is the failure mode
rather than an error.

The instance, measured 2026-08-29 in `ingesta`: a `Decimal` round-trip through SQLAlchemy's SQLite
dialect passed on ten significant digits and silently lost the value on nineteen
(`1234567890123456789.000000001` came back `…768.0000000000`, no warning). The first probe used ten
digits, so it read as "`Numeric` is fine" — a conclusion one step from being written into a shared
skill doc where nobody re-derives it.

What makes it worth stating rather than obvious: the probe's author chooses the input, and the
convenient input is short. Every other sampling failure in these rules is about a sample you were
handed; this is the one where the sample is constructed by the person asking the question, which is
also what makes a pass feel like an answer. No topic-owning skill covers how to choose a probe
input.

## Verifying behavior in a repo with test coverage

Confirmed 2026-08-24 (`repo-tasks`): three commits were checked out in a worktree and their tests
run, to verify each stood alone. Every run tested the _working tree_ instead — the venv's editable
install resolves the package there, not to the checkout — producing one false pass and one false
fail before the contradiction was noticed. `PYTHONPATH=<worktree>/src` fixed it. A passing suite had
felt like proof; it was proof about the wrong code.

The fake-`HOME` clause, added 2026-08-24, on two independent instances found in one session.
`scaffoldapy`'s e2e tier renders a repo into `tmp_path` and runs the generated `inv configure` for
real; every run had left a `~/.local/share/direnv/allow/*` entry and a `~/.cache/claude-code/*` file
pointing at a since-deleted `pytest-of-*` directory — 292 of each on the machine, never noticed
because nothing failed. `repo-tasks`' `tests/unit/test_agents.py` — a _unit_ test, "nothing outside
tmp_path" by that tier's own contract — had left ~366 more, because `agents.py` derives its cache
dir from `Path.home()`. The first fix attempt patched `os.environ` only and both leaks survived:
copier executes `_tasks` with `subprocess.run(..., env=dict(local.env))`, plumbum's import-time copy
of the environment. Extends this section rather than opening a new one (criterion 2): the trigger is
still "verifying via the test suite", and what is being sharpened is what the suite's sandbox does
and does not cover.

## Formatting a date or decimal in a shell script

Confirmed concretely 2026-08-23, twice in one script (`~/.claude/statusline-command.sh`):
`date -d ... '+%a'` returned `"Ma"` (Marți, Tuesday) instead of `"Tue"`, and
`awk '{printf "%.2f", c}'` rendered `1,23` instead of `1.23` — `LC_TIME`/`LC_NUMERIC` default to
`ro_RO.UTF-8` while `LANG`/`LC_MESSAGES` stay `en_US.UTF-8`. Both were caught only by piping real
output through `xxd`/`cat -A` and reading the literal bytes; a rendered terminal glyph or a quick
"does this look like a number" glance would have caught neither.

Rewritten 2026-08-30 to lead with the imperative and drop the machine fact, because the machine fact
stopped being true: `inv system.set-locale` now pins `LC_TIME=en_DK.UTF-8` and `LC_NUMERIC=C.UTF-8`
(`plans/2026-08-30-english-iso-locale-defaults.md`), so a rule opening "this machine's `LC_TIME`
defaults to `ro_RO`" asserted something false into every session. The instruction was always the
portable half — forcing the C locale for output a script parses is correct wherever it runs, and
merely unnecessary on a single-locale machine — so what changed is which half leads. The two
concrete tells stay in the rule (`Mi` for `Wed`, `1,23` for `1.23`) because they are what makes the
hazard recognisable; the incident that produced them stays here.

It also means the rule needs no dependency label, which is what closed the last open question about
it: it depends on nothing PULSE installs, and it is not a rule about this machine. It is ordinary
defensive scripting that this machine happened to teach.

## Force-pushing, or asking what a remote actually has

Measured 2026-08-29: a lease built from a 40-character SHA that had been hand-extended from a short
form was refused as stale info. That is `--force-with-lease` working exactly as designed — the point
is that the value handed to it was the author's invention rather than anything git had produced, so
the refusal was luck about which invented SHA it was. Date moved here 2026-08-30; the rule keeps the
account, which is what makes "never one you derived" concrete.

The stale-remote-ref half is from the same day: a branch was folded into a history rewrite to
protect against an exposure that had not existed for weeks, because `origin/<branch>` had outlived a
branch deleted upstream and a plain `git fetch` never prunes. The rule said "confirmed the same
day", which dangled the moment the date above moved out of it — a relative date is only as good as
the absolute one next to it, and stripping provenance is exactly when that link breaks.

Reworded 2026-08-30, round 2 of the leanness pass, to lead with the principle instead of with the
flag. It had opened on `--force-with-lease` specifically, and "Unexplained git/file state in a
working tree" then had to reach across and say "same principle as a force-push lease SHA" to borrow
it — so the general rule existed only as one rule's incidental property plus another rule's
cross-reference, and neither heading is one a session looks under for "how do I name a commit". It
now opens "every ref you hand git is one you read, never one you derived", with the lease as its
first instance. No evidence changed; the 2026-08-29 measurement it rests on is unaffected.

## Unexplained git/file state in a working tree

The `git add -A` clause, added 2026-08-24 after doing exactly what it forbids. Working in
`power-user-linux-setup` while a parallel session edited `config/global-AGENTS.md` (this file's
source before the 2026-08-26 split into `config/agents-md/`) and `contributing/global-agents-md.md`
in the same tree, a `git add -A && git status --short && git
commit` chain swept both files into a
commit whose message was about invoke task naming and said nothing about them. The tree had been
clean at session start and the edits landed mid-session.

Two things this teaches beyond "be careful". First, the existing rule above covers _noticing_
unexplained state; it said nothing about how to stage, so the safe-reading habit and the unsafe
staging habit coexisted without friction. Second, the `git status --short` in that same chain looked
like a check but wasn't one — it ran after `git add -A`, so it faithfully reported a staged set that
already included the other session's work. A verification step positioned after the action it's
meant to guard is worse than none, because it produces output that reads like confirmation.

The recovery was cheap only because nothing had been pushed: `git reset --soft HEAD~1`, restore the
index, and commit the two groups separately. Had the commit been pushed first, splitting it would
have meant a force-push against a branch another session may have been building on.

The push clause, added the same day from the push-side version of that near miss: a `repo-tasks`
session pushed `main` after its own commits, and the push also carried `d18f3b0` — a parallel
session's "record where the naming audit's content went", committed but deliberately not yet pushed,
the first half of a two-commit plan retirement. The rule above had covered fetching before a commit
and staging by path; `git push` publishes every unpushed commit on the branch regardless of author,
so the same "is this mine?" question applies to `git log origin/<branch>..HEAD` right before it.
Harmless that time; a force-push to undo it would not have been.

Extended 2026-08-30 with the remedy the section had been missing and one near-loss. It already said
`git status --short` before committing is not protection; it never named what is. Committing by
pathspec (`git commit -m "…" -- <path>`) takes the named paths whatever else sits in the shared
index, so a parallel session's staged file can neither ride along nor be disturbed — established
after a store commit staged by explicit path still shipped a third file another session had staged
in the seconds between.

The sharper half is the undo. `git reset --soft HEAD~1`, used to unwind that contaminated commit,
removed a **different** commit: the other session had committed on top in the interval, so `HEAD~1`
resolved to this session's commit and the reset discarded theirs. Recovered from the reflog, nothing
lost, nothing pushed. There is no error because both readings are valid git, which is the same
silent-by-construction shape as the rest of this cluster — and the file already required a
force-push lease SHA to come from `git rev-parse` rather than the eye, so this is that principle one
step earlier and it was simply unstated.

Merged 2026-08-30, round 2 of the leanness pass. Two claims this section shared with its siblings,
both moved to a single home:

- **The pathspec remedy moved to "Committing multi-part work"**, and this section points at it. The
  two rules had split one subject down the middle — that section named the failure (`git commit`
  ships the index, so anything staged earlier rides along) without naming the remedy, while this one
  named the remedy but framed it purely as parallel-session defence. Committing by pathspec answers
  both, and a session reading only the commit-splitting rule had been learning "stage late" while
  never meeting the stronger protection. What stays here is what is genuinely specific: that the
  interloper is another live session, and that `git status --short` run before the commit is not a
  check.
- **The `git rev-parse` half of "undo by SHA" is now inherited rather than restated.** This section
  had ended on "same principle as a force-push lease SHA", which left the principle owned by a
  `--force-with-lease` fact that this rule had to claim kinship with. "Force-pushing" now opens by
  stating it as a principle — every ref you hand git is one you read, never one you derived — and
  this section cites it.

Considered and rejected in the same round: merging the "parallel sessions share one working tree"
fact, which this section and "Force-pushing" each state in about eight words as the premise for
different consequences. Replacing one with a pointer would cost a reader the premise at the point
they need it, to save less than a line. Checked at the same time and confirmed **not** a third site:
"Running a command against a different repo than the session's project" — its "a commit in someone
else's tree is silent by construction" is about repo ownership, not about the shared tree.

### The local-commit-is-not-private clause

Admitted 2026-09-02 from the leanness pass's parked list, as a paragraph on this rule. The section's
last paragraph already covered the outward direction — a commit in your ahead-count may be another
session's, so ask before your push publishes it. This is the inverse, and nothing stated it.

Confirmed 2026-08-29 in `agent-skills`: a session committed two skill edits and deliberately did not
push, because another session's commits sat under them and publishing was the user's call. Minutes
later the ahead-count was zero — the other session had pushed the branch and carried both commits
with it. Nothing signalled it, and an ahead-count falling to zero reads as "someone pushed, fine"
rather than as work published without the decision that was being waited on. Verified after a fresh
fetch with `git branch -r --contains <sha>`, not inferred from the count.

Two things earn it the space. It is **silent by construction** — there is no error, no prompt, and
the observable (a falling ahead-count) has an innocent reading that is usually correct. And it is
where the confidentiality rule is sharpest, since all of that rule's force comes from a push being
irreversible: a session that has decided something must not be published yet has, on this machine,
already published it if it committed to the shared branch.

The consequence the clause states is the useful half: "I will commit but not push, and ask first" is
a stated intention, not a mechanism. Work that must genuinely be withheld has to stay off the shared
branch, and if it cannot, the user is told before the commit that the commit is itself the
publishing decision.

## Regenerating a file from a canonical source

The ordering clause was added 2026-08-24, from `scaffoldapy` adopting `repo-tasks`' two-tier test
layout. `inv configs.pull` was run first, on the assumption that a config regeneration is inert and
the repo's structure could follow. It is not inert: the pulled `pytest.ini` names
`testpaths = tests/unit`, that directory did not exist yet, and pytest's documented fallback
("Searching recursively from the current directory instead") walked into `template/` — a second
`tests/` tree that repo maintains as copier template content. `template/tests/conftest.py` was then
imported as `conftest`, shadowing the real `tests/conftest.py`, and collection failed with
`ImportError: cannot import name 'BASE_ANSWERS' from 'conftest'`. Exit 2, not a warning.

Two things generalize past that repo. The fallback is documented as benign and usually is, so its
failure mode is invisible until a repo has something else for it to find — which is a property of
the consuming repo, not of the config being pulled, and therefore not something the canonical source
can guard. And the fix was purely ordering: adopting `tests/unit/` first, then pulling, then gating,
made the same pull clean. That is why the rule is stated as sequence rather than as a warning about
`testpaths` specifically.

The clause deliberately extends the existing section rather than opening one of its own, per
"Admitting a new rule" criterion 2 — the trigger (regenerating from a canonical source) is
identical, and only the "tested" half of the existing sentence is being sharpened.

### Pull versus generate, and the CI auto-commit prohibition

Added 2026-09-01, from the user's own statement of the rule while reviewing this repo's
`devcontainer.yml`: _"docs generation/regeneration must be a task, ideally invoke if possible, that
may produce changes only on the dev machine, before ci. this task must be run as part of the
precommit chain, ideally early to allow linters and formatters to do their work... we do NOT want
anything to autocommit on our feature, release, support, develop, main/master or any other
non-throwaway, non-source-code branch."_

**It reads as a reversal of the section it sits in and is not one.** The existing rule says
regeneration is "never auto-wired into routine `fix`/`check`/`precommit` runs"; this one says
generation belongs in precommit. They are compatible because the words cover two different
operations, which the section had not distinguished:

|                | pull                                          | generate                            |
| -------------- | --------------------------------------------- | ----------------------------------- |
| source         | outside the repo (`repo-tasks`' `pytest.ini`) | this repo's own code                |
| what can shift | an upstream bump nobody chose                 | nothing — same commit as its input  |
| so             | deliberate, standalone, reviewed              | early in the gate, output committed |

The existing rule's own evidence above is entirely a pull (`inv configs.pull` into `scaffoldapy`),
and its stated rationale — "routine work silently pulling in an upstream bump" — has no referent
when the generator's input is a constant three files away. Distinguishing them is what makes both
admissible; leaving the section undistinguished would have left two rules giving opposite advice
under one trigger, which the admission criteria call out as a measured driver of degraded adherence.

The CI half came from finding the concrete case. `devcontainer.yml` had a `docs` job running
`inv devcontainer.render-docs` followed by `stefanzweifel/git-auto-commit-action@v7` with
`file_pattern: docs/dev-container.md`; `actions/checkout@v4` with no `ref:` plus the job's own
`if: github.ref == 'refs/heads/master'` meant it committed and pushed to `master`. It had never run
— the workflow is `workflow_dispatch`-only and `gh run list --workflow devcontainer.yml` returned
`[]` — so this was caught before it ever fired. Deleted rather than converted, with the shared
"generate early in precommit" mechanism filed for `repo-tasks`, which owns `quality.precommit`.

Worth noting for anyone re-reading that workflow: the auto-commit targeted `master` precisely
because the file is **source**, not build output. The repo's other publish path
(`publish_on_push.yml`) builds the docs site and pushes it to the `gh-pages` branch, which is the
correct shape and is untouched by this rule.

## About to commit

Admitted 2026-08-25, from `plans/2026-08-23-git-hooks-for-quality-gate.md`'s measurement. A
2026-08-23 CI-failure sweep across `power-user-linux-setup`/`repo-tasks`/`scaffoldapy` found every
recurring failure was one shape: markdown-only commits (`plans/*.md`, skill files, the then-single
`config/global-AGENTS.md`) pushed without the gate, failing `dprint check` (exit 20) on line-wrap
reflows `dprint fmt` would have fixed — 11 red runs in one day. The first fix was skill-level:
`plan-docs` and `session-harvest` gained "run the gate before committing" (`c84cbe4`, 17:46Z that
day). Re-measured 2026-08-25 over every failed run since: 4 of 5 were the same shape again, all
`plans/*.md`, all in `plans:` commits — the skill instruction only reaches a session that loaded the
skill for that commit, and a status bump made as a side task of other work never does. That reach
limit is why the rule is here (tier 1 — fires on any turn, miss is silent until CI) and not only in
the skills.

The rule was chosen over a git hook deliberately: the user's standing position (recorded in that
plan) is that agents should know what to run rather than be corrected behind their back, same as
developers — see "Proposing an enforcement mechanism for agent behavior".

**Re-measured 2026-09-02 and the rule worked:** eight days of CI across the three repos, every
failed log read, zero occurrences of the shape. The hook design stays parked as research rather than
as a queued next step. The full sweep and the two ways of miscounting it are recorded under
"Proposing an enforcement mechanism for agent behavior".

### The backtick clause

Admitted 2026-09-01, from one confirmed occurrence in this repo. A commit describing the `apt.py`
tolerance fix was written as an inline `git commit -m "…"` whose body quoted two commands in
backticks. Inside a double-quoted shell argument those are command substitution, so **the shell ran
them**: the terminal returned `E: Could not open lock file /var/lib/dpkg/lock-frontend` and
`dpkg: error: requested operation requires superuser privilege`, and the stored message carried two
empty strings where the quoted commands belonged. Nothing was installed or removed — the sandbox has
no passwordless root, which is the only reason this is a note rather than an incident. Fixed with
`git commit --amend -F <file>`.

One occurrence, which is normally below the bar. It is admitted anyway on the strength of three
things the frequency does not capture:

- **The trigger is structural, not rare.** These repos' commit messages routinely quote command
  names, task names and flags in backticks — the house style makes the hazard likely, and every
  message written in this session after the first one would have hit it.
- **The failure is silent in the direction that matters.** The substitution succeeded as far as the
  shell was concerned; git committed cleanly, and the damage was visible only by reading the stored
  message back with `git log --format=%B`. A message that quoted a _destructive_ command would have
  run it with the session's own privileges and still committed.
- **No existing rule reaches it.** "Composing a Bash call" governs how many commands go in a call,
  not how their arguments quote; nothing in either cluster mentions shell quoting at all.

Placed in "About to commit" rather than the Bash cluster, per criterion 2: the trigger is the moment
of committing, which is where the section already fires, and the `gh --body` case is named in one
clause rather than given a heading of its own. Deployed file: 598 → 607 lines, 38 rules unchanged.
Both numbers were already past the ≤200-line/≤15-rule reference points before this clause, so it
adds nine lines to a pre-existing question rather than raising a new one.

**Reversed the same day, on the user's correction.** The clause originally mandated
`git commit -F <file>` for any message containing a backtick. That fixed the quoting hazard and
introduced a worse one: `-m` is what puts the message into the approval prompt, and a path does not.
The user's words, on a session that had also chained the commit behind `git add` and a scan: _"i
don't like this chaining at all, it obscures the commit message, which is what i want to read when i
approve or not approve this... if there's a problem with quoting and backticks, prefer to simply not
use backticks and replace with something else that doesn't break bash/zsh."_

That is the better answer and the clause now says it: keep the message inline, and write it without
backticks or `$`, because a commit message is prose rather than Markdown and naming a command in
plain words costs nothing. `-F` survives only as the escape hatch for a message that genuinely must
carry a backtick.

The correction generalises past commits, so half of it went to the Bash cluster instead: a chain
hides whatever the user needs to read inside a compound command. That is a reviewability cost the
"Composing a Bash call" rule had never stated — it argued from exit codes, output blobs and parallel
tool-call blocks, all of which are about the agent's own accuracy rather than the human's ability to
approve. Worth noting that the rule was already in the file and already being followed for most of
that session; what failed was applying it to the one call shape where it mattered most.

### The one-`-m` clause

Admitted 2026-09-02, and it is the third correction to this same rule — which is the interesting
part of it. The rule had said "keep the message inline in `-m`", reasoning entirely from what the
approval prompt shows the user. A session in this repo read that as licensing a **chain** of `-m`
flags and shipped two commits written as four and six of them. Each `-m` becomes its own paragraph,
so the finished commits are correct and `git log` shows nothing wrong; what breaks is the thing the
rule exists to protect, because the prompt displays the _command_ and six quoted arguments run
together into one unbroken line. The user's words: _"make sure the commit message command is not a
series of -m, but the usual full text I can easily review before approving the commit, it's hard to
read a wall of text."_

Admitted on one occurrence, like the backtick clause and for the same structural reason rather than
a frequency one: the wording actively invited it. A rule whose stated remedy is `-m` and whose
stated enemy is `-F` and chaining gives a reader no reason to suspect that the number of `-m` flags
is also load-bearing. The fix is one `-m` carrying real newlines, which renders in the prompt
exactly as it will render in the log.

Worth recording that the failure was invisible from inside the rule. The session had the rule in
context, followed its letter, and produced the outcome it forbids — which is the same shape as the
adherence corpus's "authoring a rule is not evidence of following it", one step earlier:
**satisfying a rule's stated test is not evidence of meeting its purpose.** That is an argument for
stating the purpose, which this section already did, and for naming the shapes that defeat it, which
it now does three times over.

## Committing multi-part work

Reaffirmed 2026-08-23 in `scaffoldapy` ("we should use granular commits, that should be a general
rule") after a "want this split into three commits?" question — the second time the rule needed
restating, which is the signal it was being treated as a per-task preference rather than a standing
one. The conflation to avoid: needing permission to commit at all (the harness's own default) is
separate from how to split once committing is authorized.

The stage-right-before-committing clause was added 2026-08-25 from a `repo-tasks` session: two plan
files were `git rm`'d while the tree was being tidied, then the code change was staged by path and
committed — and the plan deletions landed in that commit, because `git rm` had already put them in
the index. Nothing was pushed, so it cost a `git reset --soft origin/main` and three re-staged
commits; the same slip after a push would have been a rewrite of public history or a permanently
mis-attributed deletion.

The same-file clause was added 2026-08-26 from a `repo-tasks` session that implemented two separable
features — a gate-step binary preflight and dev-group drift reporting — both of which landed in
`configs.py` and `test_configs.py`. Staging by path could not separate them, and the rule above
mandates the split while the environment's own note ("interactive flags are not supported") removes
`git add -p`/`-i`, the standard answer. The gap was doing real damage in the moment: the session
weighed abandoning the split and shipping one combined commit, on the grounds that reconstructing an
intermediate file state by hand was too much churn. The clause names the mechanism that makes it
cheap — copy the finished file aside, edit back to the first concern, gate, commit, restore — and
the reason the intermediate gate run is not optional: it ran green at 289 tests before the second
commit took it to 294, which is what proved the first commit stood on its own rather than merely
compiling. A rule that mandates an outcome the environment makes awkward, and is silent on how, is
the shape most likely to be abandoned under time pressure; this is the second clause on this rule
added for that same reason.

Extended 2026-08-30 to name `git mv`. The rule's examples were `git rm` and `git add`; a rename run
while editing rode into the next commit, which was about an unrelated plan — a second occurrence
under an explicit rule, having previously been classified as "arguably plain git literacy". The
wording observation that survives: `rm` and `add` both read as _staging_ verbs, whereas `git mv`
reads as an _edit_, so a reader checking "did I stage anything ahead of time?" does not think of it.

Gained the pathspec remedy 2026-08-30, round 2 of the leanness pass — see "Unexplained git/file
state in a working tree" for why it moved here. The section had described the index-ships-everything
failure in full and then offered only "stage late" against it, which is a discipline rather than a
mechanism; `git commit -m "…" -- <path>` is the mechanism, and it had been sitting in a sibling rule
under a heading a session splitting commits has no reason to consult.

### Every commit has a body

Admitted 2026-09-02, from the now-retired `plans/2026-09-01-every-commit-carries-a-why.md`, after
the user named it directly: commits must say what and why, and for that they must always have a
description, so agents can walk through history and understand the past without checkouts.

**The gap was structural rather than newly discovered.** This section already opened on the premise
— git history is how future agents learn why a change happened — and then constrained only
_granularity_. The body of the message is the other half of that same claim and was stated nowhere,
so a session could split its commits impeccably and still leave a log explaining nothing. That is
why it extends this rule rather than getting a heading: a reader who meets granularity and body
under one principle generalises better than one holding two adjacent rules, and `git.md` stays at 8
rules.

Two arguments carry it, and only one of them travels:

- **Who reads it changed.** A commit body used to be a courtesy to a colleague who mostly remembered
  the change anyway. An agent arriving at a commit has no memory of it at all, so the log is not a
  supplement to its recollection but the whole of its access. True of any agent in any repo.
- **On this machine it cannot go and look instead.** Parallel sessions share one working tree, so
  checking out an old commit to understand it moves a tree somebody else is working in — which the
  same file forbids elsewhere. `git log` and `git show` are the only reads safe by construction,
  which makes the body the only channel rather than the convenient one. **Machine-specific**, and
  the reason the `scaffoldapy` question below is a real question rather than a formality.

The measured shape: the session that prompted it made 17 commits, 15 with real bodies and **2 with
only the `Co-Authored-By:` trailer** — both doc commits landing right after the code commit they
belonged to. The rationalisation is worth recording because it is specific and seductive: the
reasoning had just been written into the plan file in that very commit, so restating it felt like
duplication. It is not. `git log` does not show the file, and for a plan commit the body outlives
what it describes — `plan-docs` retires a plan by deleting it, so the file is deliberately temporary
while the message is permanent. That makes a bare-bodied plan commit the one case where "the file
says it" is backwards rather than merely weak.

**A second occurrence was filed independently the same day**, by a session in `agent-skills` with no
part in the first: five commits, four carrying multi-paragraph bodies and one — a six-line
`README.md` edit — carrying a subject line alone. The user rejected that tool call with _"commits
need a description"_, and the re-do was approved with a four-line body and nothing else changed, so
the absent body is the whole of what was refused.

Its tell is a different mechanism from the first occurrence's, and the more general of the two:
**the agent scaled the message to the size of the diff.** The four commits that got bodies were the
substantial ones — no rule was reasoned around, and the plan-file rationalisation above played no
part. That is the judgement this rule has to overrule rather than accommodate, because a small diff
is precisely where the reasoning is least recoverable afterwards: the diff itself explains even
less. It is also why the first guard below is worded as a floor rather than as an exemption — the
right answer to a six-line edit is a one-clause why, never no why.

Three guards, each covering a real failure direction:

- **A floor, not a ceremony.** A formatting fix's why is one clause. Demanding a paragraph teaches
  padding, which is worse than a bare subject because padding reads as reasoning.
- **A trailer is not a body.** `Co-Authored-By:` alone satisfies `%b`, so any check written against
  this rule — an audit, a `git log --format` sweep — has to strip trailers first. That is exactly
  how the two commits above passed unnoticed in the session that made them.
- **The plans store is the named exception.** A filed plan commits as `<repo>: <what it is>` with no
  body, because the filed plan is its own description and the commit is only its delivery. Named in
  the rule rather than left to be discovered as an inconsistency. `gh pr create --body` and
  `gh issue comment` get the full rule.

**Nothing enforces it**, per "Proposing an enforcement mechanism for agent behavior" — a
`commit-msg` hook is the first thing anybody reaches for and is refused on the standing principle.
What is new is that the principle now has a measurement under it; see that section.

The one question this repo did not settle is whether `scaffoldapy` should stamp the rule into the
`AGENTS.md` it generates. Filed there rather than decided here, because the premise transfers and
the shared-working-tree argument does not, so a verbatim copy would ship reasoning that is false in
a generated repo.

## Invoking a venv tool in the session's own project

Moved twice on 2026-08-30, and it is now labelled `[needs direnv]` in `bash.md` — first out of
`portable.md` into the then-existing `this-setup.md`, then back into "Bash & tool use" when the
fragments were re-cut by subject. The reason for the first move stands and became the label: the
rule is not a portable convention that happens to mention this setup — its content is entirely "most
of this user's repos put `.venv/bin` on `PATH` via direnv", which is false on a machine without
direnv and meaningless on one without these repos. Doing it first, as a move with no rewording, was
deliberate: it tested whether a fragment boundary was worth enforcing before any rule's wording —
tuned for adherence, some of it after being measured as missed — was touched for it. What it
actually demonstrated was the opposite of a green light. A wholly-misplaced rule is the easy case,
the move cost nothing, and the round-trip it took two hours later is the evidence that filing rules
by dependency was the wrong scheme rather than one this rule happened to violate.

Confirmed live 2026-08-23 in `repo-tasks`: used `.venv/bin/python -m pytest tests/integration/` out
of habit while direnv was already active and plain `pytest tests/integration/` would have resolved
to the identical binary; corrected mid-session. The absolute path added nothing except a novel
command string that breaks Bash-allowlist prefix matching.

## Designing a uv tool-install or shared-dependency mechanism

Both traps confirmed live 2026-08-23 while building `repo-tasks`' shared-tool-list mechanism. The
`--with-executables-from` failure presents as "No executables are provided by package `X`; removing
tool" — and must be verified against the real target package, not a sandboxed fixture: a fixture
package having its own console script (even accidentally) hides it. The dependency-groups trap's
consequence spelled out: bumping the shared package's own dev/quality group changes nothing for any
project that merely depends on it, because PEP 735 groups aren't pulled in transitively the way
`[project.dependencies]`/extras are.

## Installing a tool on this machine

Measured 2026-08-26, both directions in one session, and moved here 2026-08-30: a search summary
claimed `hadolint-py` downloads its binary at install time — it ships real 12 MB platform-tagged
wheels, and was nearly rejected on that false reading — while `lychee-bin` turned out to be a 78 MB
wheel with exactly one release ever, which reversed a decision already made to adopt it. The rule
keeps both examples because they are what "judge from the PyPI file list, never from a search
summary" means concretely, in the two directions it can fail; the date is what moved.

Confirmed 2026-08-24: an agent reached for `gh extension install nektos/gh-act` and
`curl … download-actionlint.bash | bash` to get `act` and `actionlint` onto the machine, with no
`setup.toml` entry — the user stopped both before they ran. Both tools had maintained PyPI wrappers
(`act-bin` 0.2.89, tracking upstream act's 0.2.x monthly releases; `actionlint-py` 1.7.12.24,
tracking actionlint 1.7.12) that fit the existing `uv-tool` method with zero new mechanism, exactly
as `shellcheck-py`/`shfmt-py` already did. The user's framing: "we don't install anything without
also making a note to do it through pulse later. we can't afford to do things manually and forget
about them later", and PyPI-first because each extra install method is permanent setup complexity.
The rule was written and both wrappers landed in `setup.toml` in the same pass, so the "note to do
it later" never had to exist. `[packages.dprint]` still uses `method = "script"` although
`dprint-py` exists and `repo-tasks` already depends on it — a candidate for the same treatment, left
alone because its plugin list is handled by the script installer.

## Something the user wrote looks like a typo or mental slip

Concrete instance: a name used consistently across two messages while designing a naming convention
was read as deliberate and written into a plan doc as a genuine undecided design fork — it was
actually a slip, and the user had to correct it explicitly: "remember to push back on typos and
apparent mental slips. people, unlike machines, get tired and their brains connect the wrong things
despite good intentions." Repetition across messages is not proof of intent — repetition is exactly
what a tired mental slip looks like too.

## Ending a turn with a next step

Stated directly 2026-08-25 in `repo-tasks`, after a recap closed with "Push when ready —
`git push`": "don't tell me to run commands, i only work via prompts, ideally ask me with
askuserquestions what i choose to do next." The instruction was first saved as a project-scoped
memory entry, which the `session-harvest` pass then promoted here — memory is siloed per project
directory, so a preference about how every session should end would never have reached the next
repo. Admitted as its own rule rather than a variant of "About to ask the user something factual":
that rule is about _not_ asking when the answer is discoverable; this one is about asking, via the
tool, when the answer is genuinely the user's.
