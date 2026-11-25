---
status: idea
updated: 2026-11-25
---

# Commit trailers as agent memory

## Context

Asked 2026-11-25, while commit and push were being made unprompted
(`plans/2026-11-08-auto-mode-as-default-with-slim-rules.md`): _"try to look online what commit rules
are out there, if any, that make life easier for agents, and come up with something that helps our
agentic flow as well, not just conventions for humans"_.

**What this machine already does well, measured the same day.** Over the 90 days to 2026-11-25, 31
of 2,782 commits across ten personal repos had no body, and a 15-commit sample read for content
carried the reasoning in every case: what it is for, what it beat, what it cost. The gaps were the
noun (what changed, by name) and plans cited by nickname, both fixed in `config/agents-md/git.md`
the same day. Evidence: `contributing/global-agents-md.md`, "What changed comes first".

**What it does badly for agents is retrieval, not content.** The reasoning is prose, so an agent can
only find it by reading. "Was a sandbox already rejected for this?", "which commits carried out this
plan?", "what did this commit actually verify?" each need a read through dozens of bodies. Prose
says it; nothing makes it findable by a query.

### What exists, researched 2026-11-25

Primary material read: the `srdjan/structured-git-commits` skills (cloned into the research
library), the Lore paper (arXiv 2603.15566), the kernel's coding-assistants policy. Search-summary
depth for the rest.

- **Lore** (arXiv 2603.15566, March 2026) puts decision context in git trailers: `Constraint:`,
  `Rejected:`, `Confidence:`, `Scope-risk:`, `Reversibility:`, `Directive:`, `Tested:`,
  `Not-tested:`, `Related:`. Agents query them before changing a file. **No empirical results**: the
  paper proposes a six-month study and reports none.
- **structured-git-commits** (`srdjan`): Conventional Commits headers plus required `Intent:` (a
  controlled taxonomy) and `Scope:` trailers, optional `Decided-Against:`, `Session:`, `Refs:`,
  `Context:` (JSON), `Breaking:`. It calls `Decided-Against:` "the highest-value trailer for agent
  memory". It ships a validator, a trailer index, and a `UserPromptSubmit` hook that injects recent
  rejections into every prompt.
- **Attribution trailers**: the kernel requires `Assisted-by: AGENT:MODEL` and forbids agents adding
  `Signed-off-by`; GitHub's Copilot agent adds `Agent-Logs-Url:`; `Co-Authored-By:` is the common de
  facto form. These serve audit by humans, not retrieval by agents.
- **Line-level provenance**: Agent Trace (a JSON spec from Cursor and Cognition) and `git-ai` store
  which lines a conversation produced in git notes under `refs/notes/…`. Heavy tooling, and notes do
  not travel on a plain push.

[DECISION: **adopt a small closed trailer vocabulary, each key earning its place by one query an
agent actually runs.** Trailers are the right carrier: plain `git log` reads them
(`--format='%(trailers:key=Rejected,valueonly)'`, `--grep='^Rejected:.*sandbox'`), they travel with
every push, and `git interpret-trailers --parse` confirms they parse beside `Co-Authored-By:`
(checked 2026-11-25 on a draft message). It beat git notes, which need extra refspecs to push and
fetch, and beat a separate decision log, which is a second store that drifts from the commits.]

### The proposed vocabulary

The body stays prose, in the order `git.md` now prescribes: what changed by name, then what it is
for, what it beat, what it cost. Trailers are the **index** into that prose, not a replacement.

| trailer                           | when                                                 | the query it answers                                                               |
| --------------------------------- | ---------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `Plan: plans/<file>.md`           | the commit carries out a plan tracked in this repo   | every commit of one plan, even after the plan is deleted                           |
| `Rejected: <approach> (<reason>)` | an alternative was weighed and dropped, one per line | "was X already tried here?" before an agent re-proposes it                         |
| `Verified: <command or probe>`    | something was run that proves the change             | what a green claim rested on, without re-running it                                |
| `Not-verified: <what> (<why>)`    | a part could not be or was not proven                | the open risk a later session inherits, the commit-level twin of `[UNVERIFIED: …]` |
| `Co-Authored-By: …`               | unchanged                                            | attribution                                                                        |

[DECISION: **`Plan:` is the one that fixes something already broken.** `plan-conveyor` deletes a
plan on retirement, and a nickname in a commit body leaves nothing to search for. `Plan:` names the
file, so `git log --grep='^Plan: plans/<file>'` lists a plan's whole implementation and
`plans.py archive --file <file>` brings the plan back. The 15-commit sample had four nickname
references ("the leanness plan", "the shipping plan", "stage 1", "the pilot's criterion").]

[DECISION: **every trailer value names something in the repo or nothing local at all — user rule,
2026-11-25.** _"only files in the repo should be referenced, nothing on the same machine, unless
it's about an investigation etc"_. So `Plan:` is written only for a plan tracked in the repo's own
`plans/`. A repo routed to the plans store gets no `Plan:` trailer, because naming a store plan in
its history publishes what the routing keeps out. The same line now stands in
`config/agents-md/git.md` for commit bodies.]

[DECISION: **`Rejected:` duplicates part of the body on purpose.** The body explains why the
alternative lost; the trailer is the signpost a query finds. That is the one duplication worth its
cost, because "re-proposing a rejected approach" is the failure both Lore and structured-git-commits
were built against, and this corpus records it too:
`plans/2026-08-28-auto-mode-contradicts-bash-rules.md` documents sessions re-deriving settled
decisions.]

[DECISION: **`Verified:` and `Not-verified:` make the verification rules checkable after the fact.**
`~/.agents/AGENTS.md` asks for a gate before every commit and for reporting what was not verified;
today that lives in chat and is lost. A `Not-verified:` line is the inheritance a later session
needs, and its absence on a commit claiming a fix is visible in review.]

### Deliberately not adopted

- **Conventional Commits types** (`feat:`, `fix:`). These repos already prefix subjects with an area
  (`deploy:`, `plans:`, `identity:`), which is the query agents actually run
  (`git log --grep='^deploy:'`). Switching would split 2,782 commits of history into two styles for
  a type label `git log -- <path>` mostly makes redundant.
- **A controlled `Intent:` taxonomy.** Its value depends on a validator keeping the vocabulary
  closed, and a validator is enforcement behind the agent's back, which "Proposing an enforcement
  mechanism" refuses. Free-text intent is already the body's first paragraph.
- **`Confidence:`, `Scope-risk:`, `Reversibility:`.** Self-assessed and unverifiable. Lore itself
  names "rubber-stamped atoms" as the residual risk. `Not-verified:` carries the only part of this
  that a later reader can act on.
- **`Directive:` (instructions to future modifiers).** That belongs in a comment at the line it
  governs, where `~/.agents/AGENTS.md`'s "Where durable knowledge goes" puts it: read exactly when
  relevant, and it cannot go stale against its own code.
- **Git notes, Agent Trace, `git-ai`.** Line-level provenance answers "which conversation wrote this
  line", which nothing here asks. Revisit if it ever is.
- **`Session:` (the agent transcript behind a commit).** It points at a file on this machine, which
  the rule above excludes, and the transcript is deleted after 30 days by default, so the trailer
  would outlive what it names. Copilot's `Agent-Logs-Url:` works because its logs are hosted; ours
  are not.
- **A prompt hook injecting recent rejections** (structured-git-commits' `UserPromptSubmit`). It
  fires behind the agent's back, and the read side below is a rule the agent runs instead.

### The read side

Trailers only help if agents query them. One rule, triggered by the moment it is needed: **about to
change code, or re-decide something, whose reason you don't know: read its history first.**

```shell
git log -n 5 --format='%h %s%n%b' -- <path>
git log --format='%h %s%n  %(trailers:key=Rejected,valueonly)' --grep='^Rejected:' -- <path>
```

Read with `git log`, which is safe in a working tree another session holds, unlike a checkout.

## Open questions

[NEEDS CLARIFICATION: **which trailers, and required or optional?** Proposed: all optional and
written when the condition in the table holds, so a formatting fix carries none. Making any one
required turns it into ceremony, which the existing "a floor, not a ceremony" guard warns against.]

[NEEDS CLARIFICATION: **`agent-skills` already writes `Claude-Session: <url>`** on some commits — a
claude.ai URL, so hosted rather than local, but private to the account and still a vendor-specific
link in a public history. Whether that stays is a question for that repo, filed there if the user
wants it changed.]

[NEEDS CLARIFICATION: **how does `plans.py commit` carry trailers?** It derives subjects and takes
`--body`. A `Plan:` trailer on plan commits is the most mechanical case and the script could add it
itself. That is a change to `plan-conveyor` in `agent-skills`, filed there with `new --for`, not
made from here.]

[NEEDS CLARIFICATION: **does the vocabulary go to the whole repo family?** `scaffoldapy` stamps an
`AGENTS.md` into generated repos. A trailer vocabulary that only these repos write is still useful
here; across the family it becomes queryable everywhere. Same question the "Every commit has a body"
evidence left open for `scaffoldapy`.]

## Recommended direction

Pick the vocabulary, then land it as two rules in `config/agents-md/git.md`: the trailer table as a
positive recipe under "Committing multi-part work" (criterion 4: an omission takes a structural
slot), and the read-side rule under its own trigger heading. Evidence into
`contributing/global-agents-md.md`. Pilot on this repo for a week, then measure with the same 90-day
script: how many commits carry each trailer, and whether any session ran a trailer query before
re-deciding something. Only then file the `plan-conveyor` and `scaffoldapy` changes.

## Sources

- https://github.com/srdjan/structured-git-commits
- https://arxiv.org/abs/2603.15566
- https://docs.kernel.org/process/coding-assistants.html
- https://github.com/git-ai-project/git-ai
- https://www.ronaldtebrake.nl/blog/git-blame-intent-aware-agents/
- https://dev.to/hubtheocoelho/introducing-qac-a-commit-message-specification-for-ai-agents-4opd
