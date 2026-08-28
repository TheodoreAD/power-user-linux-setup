---
status: idea
updated: 2026-08-28
---

## Context

`plans/*.md` (the `plan-docs` skill) is per-repo by construction: a plan lives in the repository it
describes, is formatted by that repo's quality gate, and its drafting and retirement are recorded in
that repo's git history next to the code it produced. That works well for single-repo work and badly
for the growing share of work that spans the family — `power-user-linux-setup`, `repo-tasks`,
`scaffoldapy`, the `*-polite-mcp` set. The convention already concedes this with an optional
`depends_on: [<repo-name>, ...]` frontmatter field, which names other repos a plan can't land
without but does nothing to make that plan visible from them.

The concrete failure: there is no single place that answers "what is pending across everything."
Answering it today means opening every repo's `plans/` directory by hand. A plan filed in
`power-user-linux-setup` about `repo-tasks` is invisible to a session working in `repo-tasks`, and
vice versa — the same siloing that `~/AGENTS.md` already rejects for Claude Code's per-project
auto-memory, reproduced one level up in a mechanism this repo owns.

The user's framing: something closer to `$RESEARCH_HOME` and the `research-library` skill — one
machine-wide location, plain markdown, local, no work-tracker SaaS — while acknowledging the pull in
the other direction, that the historical value of plans sitting in the repo's own git history is
strong. Explicitly stated as unresolved ("I'm divided on this"). Also raised as an option: keep a
tracker (GitHub Issues was named) as the store and continuously mirror it down to markdown.

This is the general question that `plans/2026-08-23-github-issues-plan-lifecycle.md` asks a narrow
slice of. That plan should not be settled before this one — its "issue as inbox vs. issue as
backlog" choice is downstream of where the durable store lives at all.

**The convention moved out of this repo while this plan was being written, and the move is now
finished.** Per `plans/2026-08-26-agent-artifact-authoring-decoupling.md`, all ten skills —
`plan-docs` among them — are authored in
[`TheodoreAD/agent-skills`](https://github.com/TheodoreAD/agent-skills). PULSE has no `skills/`
directory at all, and one `[packages.agent-skills]` entry with **no `names` filter** installs
whatever that repo publishes. The point of the move was decoupling: the skills do not depend on
PULSE, anyone can install the same set with `npx skills add TheodoreAD/agent-skills` on any agent
the `skills` CLI supports, and PULSE merely integrates them into its own holistic setup. Development
and adoption both get easier; PULSE stops being a precondition for either.

So the rules this plan proposes changing are owned by a repo that is not this one, and `depends_on`
— the field the whole discovery problem hangs on — is defined there now.

That has a sharp consequence for this plan's own shape, and a mildly absurd one: **this file is an
instance of the problem it describes.** It concerns a convention owned by `agent-skills` and
proposes tooling that would ship inside it, while being filed in `power-user-linux-setup` —
invisible from either.

[DECISION: **`agent-skills` gets its own `plans/`, like every other repo in the family.** Settled
with the user 2026-08-28. It does not have one yet. That makes seven repos carrying plans, and it
removes the awkward case of a repo owning a convention it does not itself practise.]

## What the family actually looks like, measured (2026-08-28)

Six repos under `~/projects/github.com-personal/` carry a `plans/` directory —
`power-user-linux-setup` (23), plus `repo-tasks`, `scaffoldapy`, `ingesta`, `olx-polite-mcp` and
`freshful-polite-mcp` (33 between them); `agent-skills` will be the seventh. **56 plan files, all
with `status:` frontmatter, none visible from any repo but their own.** Tallying every status line
family-wide:

| status                | count |
| --------------------- | ----- |
| `idea`                | 44    |
| `in-progress`         | 7     |
| `blocked on <reason>` | 3     |
| `landed`              | 1     |
| `abandoned`           | 1     |
| `done`                | 1     |

Two things fall out of that tally that nothing currently reports:

- **`done` is not in the vocabulary.** `plan-docs` defines `landed`, and one repo has drifted to
  `done`. A second status line is a free-form paragraph —
  `status: idea — hooks still unadopted;
  ~/AGENTS.md "About to commit" rule deployed 2026-08-25 as the next step, re-measure after it has
  run a while`
  — which is prose where an enum belongs. Neither is caught by any repo's quality gate, because each
  gate only ever sees its own repo.
- **44 open ideas is the real scale of the discovery problem.** Not "a few cross-repo plans" — a
  backlog two-thirds the size of this repo's entire plan history, spread across six working trees,
  with no way to ask which of them are `blocked on` something that has since landed elsewhere.

An aggregator would have surfaced both on its first run. That is the strongest argument in this file
for the recommended direction, and it is evidence rather than reasoning.

## Prior art survey (2026-08-28)

Others have hit this. The survey below is the useful half of a broad pass; nothing found solves the
cross-repo case well, which is itself the most important finding.

### Markdown-in-the-repo task trackers

| project                                                     | store                                                            | maturity (2026-08-28)                     | cross-repo                               |
| ----------------------------------------------------------- | ---------------------------------------------------------------- | ----------------------------------------- | ---------------------------------------- |
| [Backlog.md](https://github.com/MrLesk/Backlog.md)          | `backlog/` md files, YAML frontmatter                            | 6.5k★, MIT, TS, created 2025-06, active   | none — asked about on HN, unanswered     |
| [Markdown Projects](https://www.markdownprojects.com/)      | `.mdp/` folder-per-issue + milestones                            | MIT, published 2026-02, very new          | none stated                              |
| [git-issues](https://news.ycombinator.com/item?id=47973644) | `.issues/` YAML-frontmatter md, autocommit                       | Show HN, single Go binary                 | none                                     |
| [TrackDown](https://github.com/mgoellnitz/trackdown)        | `issues.md` on a dedicated `trackdown` branch, symlinked at root | 38★, GPL-3.0, 367 commits                 | mirrors from GitHub/GitLab/Gitea/Redmine |
| [TODO.md](https://github.com/todomd/todo.md) spec           | one `TODO.md`, GFM task lists as columns                         | 284★, 8 commits, effectively dormant      | pitched at multi-repo, no implementation |
| [tasks.md](https://github.com/tasksmd/tasks.md)             | `TASKS.md`, P0–P3 sections, per-task metadata                    | **7★**, created 2026-03, 333 commits, MIT | **yes — see below**                      |

### Non-markdown, git-native

- [git-bug](https://github.com/git-bug/git-bug) — 10k★, GPL-3.0, since 2018, still active. Stores
  bugs in git's own object database (no files in the tree at all), CLI/TUI/web, and has
  **bidirectional bridges to GitHub, GitLab and Jira**. The most mature thing in this space by a
  wide margin. Per-repo by design; a bug lives in the repo whose objects hold it.
- [beads (`bd`)](https://github.com/gastownhall/beads) — 26.7k★, MIT, Go, Steve Yegge, created
  2025-10. Explicitly "a memory upgrade for your coding agent": a dependency graph (`blocks`,
  `parent-child`, `supersedes`, `duplicates`, `related`, `replies-to`) with a `bd ready` query for
  unblocked work. Storage moved from SQLite+JSONL to **Dolt** at v1.0 in early 2026;
  `.beads/issues.jsonl` is now an export, explicitly not the source of truth. Its pitch is directly
  against this repo's convention — it exists to replace "messy markdown plans" with a queryable
  graph. Relevant precedent for the central-store question: `bd init --contributor` routes planning
  issues to a store **outside the repo** (e.g. `~/.beads-planning`), and `BEADS_DIR` overrides
  git-repo discovery entirely.

### Tracker → markdown mirroring (the "grab everything as markdown" option)

- [gh-issue-sync](https://github.com/mitsuhiko/gh-issue-sync) — 161★, Apache-2.0, created 2025-12,
  last pushed 2026-03. Mirrors GitHub issues into `.issues/{open,closed}/123-slug.md` with YAML
  frontmatter, keeps pristine copies in `.issues/.sync/originals/` and does **three-way conflict
  detection** (local vs. original vs. remote; both-changed is skipped with a warning, not merged).
  GitHub stays authoritative. `GH_ISSUE_SYNC_DIR` explicitly supports pointing at a centralized
  issue store. README states the code is entirely LLM-generated.
- [imdone-cli](https://imdone.io/markdown-github-issues-sync), `gh2md`, `github-issues-export-rs`,
  `offline-issues` — one-way export, varying liveness.
- git-bug's bridges are the mature version of this idea, minus the markdown.

### Central-store / aggregation patterns (the actual question)

- **[tasks.md](https://github.com/tasksmd/tasks.md) workspace mode** is the only surveyed project
  that solves cross-repo aggregation as designed. A "workspace" is a directory whose immediate
  children are repos each carrying a `TASKS.md`; registered workspaces live in
  `~/.config/tasks-md/workspaces.json`; `tasks next` aggregates across all of them and prints
  `<workspace>::<repo>:<task-id>`, and a task can declare `Blocked by: oncall-hub::api#fix` across
  repos. Positioning is explicitly "AGENTS.md tells agents _how_ to work, TASKS.md tells them _what_
  to work on." Verified in source rather than from the README (`packages/parser/src/workspace.ts`,
  `packages/cli/src/config/workspaces.ts`, `packages/cli/src/commands/workspaces.ts`, each with
  tests) — clone at `$RESEARCH_HOME/repos/github.com--tasksmd--tasks.md`. The feature is real; the
  project is not adopted (7 stars, five months old).
- **[The Planning Repo Pattern](https://medium.com/@jbpoley/the-planning-repo-pattern-160ee57adcaf)**
  (Jan 2026, author manages 20+ repos): one parent git repo whose `.gitignore` treats the nested
  repos as opaque. Planning documents are tracked by the parent; each project keeps full git
  independence. No submodules, no version coupling.
- **Dendron multi-vault** — a workspace of several vaults, each its own git repo, with a single
  unified lookup namespace across all of them and results labelled by vault. The closest existing
  answer to "per-repo ownership, one search surface." (Dendron itself is no longer maintained; the
  model still stands.)
- **ADR practice** — the mainstream convention is per-repo `docs/adr/`, with a central site
  generated on top once decisions cross many repos.
  [log4brains](https://github.com/thomvaill/log4brains) is the reference tool and states the split
  directly: package-specific ADRs in each package repo, global ADRs central.
- **Obsidian symlink pattern** — one vault, external repos symlinked in. Widely used, and directly
  prohibited by the `research-library` skill's "no symlinks into project repos" rule for the same
  ambient-read-path reason.
- **git submodule** for a shared `plans/` — surveyed; the recurring complaint is workflow
  complexity, plus the hard constraint that a submodule can't have two parents.

### Counter-evidence worth keeping

- GitLab's changelog crisis is the standard citation for "tracked items in the repo cause merge
  conflicts at scale," and their fix was **file-per-entry in a directory** — which is what
  `plan-docs` already does. The conflict argument does not apply to a solo owner with one file per
  plan; don't import it.
- Fossil rejects storing tickets in the source tree on two grounds: check-ins are immutable, so a
  ticket can't be added to a past one, and thousands of tickets clutter the tree. Only the second
  half transfers here, and `plan-docs`' retirement procedure is already the answer to it.
- The historical distributed-bug-tracker cohort — Bugs Everywhere, ditz, GitIssius — is dead.
  git-bug is the survivor, and it survived by _not_ putting files in the working tree.

### Second pass — read against the source, not the README (2026-08-28)

Three candidates were taken past search-summary depth. Clones under `$RESEARCH_HOME/repos/`, each
with a `SOURCE.md` recording why.

**beads has the same answer this plan reaches, and ships it.** Buried under `docs/multi-agent/`, not
in the README: every issue carries a `source_repo` field (`.`, `~/.beads-planning`, or an absolute
path to another repo), `bd create` auto-routes by role, and **hydration** aggregates issues from the
current repo plus the planning repo plus any configured additional repos into one unified `bd list`.
That is ownership-per-repo with unified discovery, implemented by the most-adopted tool in the space
— strong corroboration for the recommended direction below, arrived at independently.

Its own guidance is the honest counter-evidence, and it points the other way for this machine:

> ### You DON'T need multi-repo if:
>
> - ✅ Working solo on your own project
> - ✅ Team with shared repository and trust model
> - ✅ All issues belong in the project's git history

All three are true here. The listed reasons you _do_ need it are OSS forks, PR hygiene, and
multi-persona splits — none of which apply.

What adopting beads would actually cost, from the docs rather than the pitch: a Dolt database as the
store (`.beads/embeddeddolt/`, JSONL demoted to an export that is explicitly "not the source of
truth" and not a backup), and `docs/multi-agent/federation.md` — Dolt remotes, four data-sovereignty
tiers, a MySQL port plus a remotesapi port, and a page of lease-reclaim rules including a documented
footgun where committing `node_id` to the git-tracked `.beads/config.yaml` leaves the guard "fully
armed and fully inert." That is fleet machinery. It is also actively hostile to the surrounding
architecture: the `AGENTS.md` snippet `bd init` installs says "do not create MEMORY.md files" and
"Do not use markdown TODO lists for task tracking" — beads wants to own memory and tracking, which
this repo already assigns to `~/AGENTS.md`, `contributing/`, and `plans/`.

**Backlog.md has no cross-repo support at all** — confirmed by grep, not inference: `src/` returns
zero hits for cross-repo, multi-repo, multiple-repositories or workspaces. So the HN question that
went unanswered was answered by the code.

Two things from it are worth keeping anyway. Its `MANIFESTO.md` is close to a statement of
`plan-docs`' own philosophy from an independent direction — markdown as the durable substrate,
local-first ownership, CLI canonical, MCP explicitly demoted to "a legacy, optional adapter",
"humans and agents are both first-class users." And its store is richer than a flat directory:
`backlog/{tasks,drafts,completed,archive,decisions,docs,milestones}`, i.e. it absorbs the ADR and
docs roles that this repo splits into `contributing/` and `docs/`.

But it takes the opposite position on the one question that matters most here. Its core loop ends
with **"preserve the record: keep the completed task with its reasoning and outcome as durable
project history"** — completed work moves to `completed/`, never out. `plan-docs` retires by
_deleting_, having migrated the durable content to `contributing/`/`docs/`. Both are coherent; they
cannot both be true. Which is right is the second open question below, and Backlog.md is evidence
that the retention answer is at least defensible.

Its per-item format is also far heavier than a plan file — frontmatter carrying `dependencies`,
`references`, and a full `modified_files` list, plus `## Acceptance Criteria`,
`## Definition of
Done`, `## Implementation Plan`, `## Implementation Notes` and `## Final Summary`
delimited by `<!-- SECTION:*:BEGIN/END -->` markers so the CLI can rewrite sections without touching
prose. The marker technique is worth noting for any future generated section in a plan file.

### How skills in the wild handle script dependencies (2026-08-28)

Researched because the decision above puts a script inside a skill, and "does it need a venv?" was
raised as an open worry. **It does not, and a venv per skill is not the convention — it is the thing
the convention exists to avoid.**

[agentskills.io's "Using scripts in skills"](https://agentskills.io/skill-creation/using-scripts) is
the spec-level guidance, and it describes exactly two tiers, neither of which is a virtual
environment:

1. **One-off commands** — if an existing package already does the job, reference it straight from
   `SKILL.md` via a runner that resolves dependencies at invocation (`uvx`, `pipx run`, `npx`,
   `bunx`, `deno run`, `go run`), pinned to a version. No `scripts/` directory at all.
2. **Self-contained scripts** — bundle in `scripts/` and let the script declare its own dependencies
   **inline**. For Python that is PEP 723, a `# /// script` TOML block, run with
   `uv run scripts/foo.py`. Verbatim: "no separate manifest file or install step required." Every
   other language in the page gets the same treatment (Deno `npm:` specifiers, Bun auto-install,
   Ruby's `bundler/inline`).

Scripts are referenced by **path relative to the skill directory root**, because the agent runs
commands from there — which is what makes a bundled script work identically for anyone who installed
the skill, with no install step of the skill's own.

Where venv-per-skill _does_ appear is
[anthropics/skills discussion #117](https://github.com/anthropics/skills/discussions/117), and the
problem there is not ours: **cloud skills from different vendors sharing one sandbox**, where skill
A needs `pandas==2.1` and skill B needs `2.2`. The debated answers are venv-per-skill (pipx-style),
container-per-skill for untrusted code, and — rejected as fragile — `sys.path` namespacing. The one
point of consensus worth carrying over is that dependencies should be _declared_ even before
isolation is enforced, so conflicts are detectable rather than silent. PEP 723 is that declaration.
A single user's own skills, on their own machine, have no multi-tenant conflict to isolate.

So the ordering for anything written here:

1. **Standard library only.** Zero declaration, zero resolution, `python3 scripts/foo.py` works on
   any machine with Python. `session-bash-audit/scripts/audit.py` already proves this is enough for
   a real tool — it parses every `~/.claude/projects/*.jsonl`, tallies patterns, and samples
   transcripts on `argparse`/`json`/`re`/`dataclasses`/`pathlib` alone. A plan-frontmatter
   aggregator is a strictly smaller problem than that; YAML frontmatter this simple does not justify
   PyYAML.
2. **PEP 723 + `uv run`** if a dependency ever becomes genuinely necessary. uv is already on this
   machine (`bootstrap.sh` installs it), and this keeps the script single-file and portable.
3. **A venv, a `requirements.txt`, or a `pyproject.toml` inside a skill** — no. It would make the
   skill un-runnable until someone ran an install step the `skills` CLI does not perform, which
   defeats the decoupling the move just achieved.

One further thing from the same page worth applying whatever gets written, since it is about being
_run by an agent_ rather than about dependencies: no interactive prompts (agents run non-interactive
shells and a TTY prompt hangs forever), a real `--help` because that is how an agent learns the
interface, structured output on stdout with diagnostics on stderr, meaningful documented exit codes,
and bounded output because harnesses truncate. There is also a `compatibility` frontmatter field for
declaring runtime-level requirements.

## The tension, stated precisely

"One location" and "history next to the code" are only in conflict if the store is what moves. They
are separable:

- **Ownership** — which repo's git history records that this plan was written, revised and retired.
- **Discovery** — what answers "everything open across all repos" in one place.

Every mature project surveyed keeps ownership per-repo and solves discovery with a query or
aggregation layer (tasks.md workspaces, Dendron's cross-vault lookup, log4brains' central site,
git-bug's bridges). Nothing mature moves the store. That is the strongest signal the survey
produced, and it argues the user's stated instinct ($RESEARCH_HOME-style central store) and the
user's stated reservation (historical value) do not actually have to be traded off against each
other.

The counter-argument that has to be weighed honestly: `$RESEARCH_HOME` works precisely _because_ it
is central and outside every repo, and plans differ from research material in one way that matters —
research is read-only reference with no lifecycle, while a plan is authored, reviewed, and retired.
Whether that difference is decisive is the question below.

## Open questions

[NEEDS CLARIFICATION: is the requirement discovery or relocation? Everything else follows from this.
If the real need is "one command shows every open plan across the family," an aggregator over the
existing per-repo `plans/` directories delivers it with no migration, no lifecycle change, and no
loss of per-repo history. If the need is genuinely one editable location — plans authored and
revised in one directory regardless of which repo they concern — that is a different design and
costs the coupling of a plan's history to its code's history.]

[NEEDS CLARIFICATION: how much does per-repo plan history actually buy? Worth interrogating rather
than assuming, because `plan-docs` **deletes** plans on retirement and migrates their durable
content to `contributing/`/`docs/`. What the repo's history therefore preserves is the drafting
process plus the retirement commit — not the plan as a living document. If the durable value is
already in `contributing/`, the historical argument for per-repo storage is weaker than it feels,
and the answer may change the whole decision.]

[NEEDS CLARIFICATION: does adopting an existing tool make sense here at all, or only its model?
`~/AGENTS.md` says to check for a maintained external project before authoring from scratch. The
honest reading of the survey: the one project that solves this problem (tasks.md) is 7 stars and
five months old, and the two mature ones (git-bug, beads) both reject markdown-in-the-tree, which is
the property this repo's whole convention is built on. Adopting either means abandoning `plan-docs`.
Adopting tasks.md means depending on an unadopted npm package for something the family already has a
working convention for. Borrowing the workspace-discovery model and implementing an `inv plans.*`
aggregator is the third option and probably the right one — but it should be an explicit decision,
not a default.]

[NEEDS CLARIFICATION: where does the aggregator's config live, and how does it find the repos? The
tasks.md model is "a directory whose immediate children are repos", which maps exactly onto
`~/projects/github.com-personal/`. Alternatives: an explicit list in `setup.toml`, or a scan for
`plans/` directories under the projects root. The scan needs no registration and picks up a new repo
for free; the explicit list is reviewable and can't surprise. This repo already deploys machine-wide
config, so either is available.]

[NEEDS CLARIFICATION: does a cross-repo plan get one file or one per repo? A plan that can't land
without `repo-tasks` changing has real content for both repos. Options: single file in the repo that
owns the outcome plus `depends_on` (today's shape, already specified and unused); a stub in each
affected repo pointing at the owner; or the aggregator resolving `depends_on` into a
"blocked-by/blocking" view so no second file is ever needed. The third preserves one-file-per-topic,
which `plan-docs` insists on for good reason.]

[NEEDS CLARIFICATION: is a tracker in the loop at all? The user raised continuously mirroring a
tracker (GitHub Issues) down to markdown. gh-issue-sync and git-bug's bridges both prove it works,
but both make the remote authoritative and the markdown a mirror, which inverts what `plan-docs` is.
It also fails the offline case that `plans/2026-08-23-github-issues-plan-lifecycle.md` already
flagged. Decide whether a tracker is (a) not involved, (b) an inbox only, or (c) the store — `(b)`
is what the issues plan already leans toward and is compatible with everything above.]

[DECISION: **The aggregator ships inside the skill, as `skills/plan-docs/scripts/`, written against
the standard library only.** Settled with the user 2026-08-28: no new software is being planned
here, and any automation lives as a stdlib-only Python script in the skill that needs it. That
resolves the three-way ownership question in favour of the skill — the rule and its enforcement stay
in one repo, the script travels to anyone who installs the skill, and PULSE keeps doing only what it
now does for skills, which is install them. It also means the tool is _not_ an `inv` task, unlike
every other piece of family tooling; that is a deliberate consequence of the skills being decoupled,
not an oversight. Precedent already exists in the same repo: `session-bash-audit/scripts/audit.py`
is stdlib-only and invoked as `python3 $S/scripts/audit.py`.]

[NEEDS CLARIFICATION: **what tells the script which directories to walk?** The script is portable;
"where this user's repos live" is not. Options: a positional argument the `SKILL.md` shows being
called with a path; an env var, the way `research-library` declares `$RESEARCH_HOME`; or discovery
by scanning the parent of the current repo for siblings that have a `plans/`, which is how tasks.md
finds a workspace. The `research-library` precedent is the strongest — that skill became publishable
precisely by _declaring_ its one environment assumption instead of assuming PULSE had provided it,
and the same shape applies here. Decide before the script is written, since it determines whether
PULSE needs any config entry at all.]

[NEEDS CLARIFICATION: **should the status vocabulary be validated, and by what?** The measured tally
above found `done` where `landed` is defined, and one free-form status paragraph. A per-repo gate
cannot catch this, because drift is only visible across repos. Options: the aggregator warns (cheap,
no enforcement); each repo's `quality.check` validates its own frontmatter against the vocabulary
(catches it at commit time, but needs the vocabulary shipped somewhere every repo can read — which
is the ownership question above); or nothing, and drift is accepted as harmless. Note that whichever
is chosen has to survive the vocabulary itself being open-ended — `blocked on
<reason>` and
`superseded by <path>` are prefixes, not literals.]

[NEEDS CLARIFICATION: does a retired plan get deleted or kept? `plan-docs` deletes after migrating
durable content; Backlog.md's manifesto takes the opposite position and keeps every completed item
as "durable project history". This was not previously treated as an open question at all, and it
interacts with the history question above: if retirement stopped deleting, the argument for per-repo
storage strengthens considerably, because the repo's history would then hold the plan itself rather
than only its drafting.]

[UNVERIFIED: Markdown Projects, git-issues, TrackDown, TODO.md, gh-issue-sync, imdone and Dendron's
multi-vault behaviour were assessed at web-search/README depth only. tasks.md, beads and Backlog.md
have since been read against their actual source (clones under `$RESEARCH_HOME/repos/`). If any of
the remainder moves from "surveyed" to "candidate", it needs the same treatment first — per the
research-library skill, a README can advertise a feature that was never implemented.]

[UNVERIFIED: the Planning Repo Pattern is still known only from a search summary — medium.com
returns 403 to WebFetch on both the `medium.com/@jbpoley` and `jbpoley.medium.com` forms, and
freedium.cfd does not resolve. It is named as the fallback design below, so if the relocation branch
goes live, the article needs reading by some other route first.]

## Recommended direction

Rough, and contingent on the first open question.

**Most likely shape: keep the store where it is, add a discovery layer.** Per-repo `plans/` stays
exactly as `plan-docs` defines it — same lifecycle, same retirement procedure, same quality gate,
same coupling of drafting and retirement to the repo's own history. On top of it, an aggregator that
walks the projects root, parses the frontmatter of every `plans/*.md` it finds, and renders one
status-grouped index: what is `idea`, what is `in-progress`, what is `blocked on` what, and which
`[DEFERRED:]`/`[NEEDS CLARIFICATION:]` tags are outstanding family-wide. The `depends_on` field
finally does something — it becomes the edge in a blocked-by/blocking view instead of documentation
nobody reads. The measured tally above is what its first run should print, drift included.

It ships as `skills/plan-docs/scripts/`, stdlib-only, per the decision above — not as an
`inv plans.*` namespace in `repo-tasks`, which was the assumption before the skills were decoupled.
What remains open about it is only how it learns which directories to walk.

That gets "one location" as a _view_ rather than a _directory_, which is what every mature project
in this space converged on, and it costs nothing that currently works. The second pass strengthened
this rather than complicating it: beads' `source_repo` + hydration is the same design, shipped and
adopted at scale, and the aggregator sketched above is the small version of it — no database, no
federation, no new store, just a parse of frontmatter this repo already writes.

Two things to settle before building anything, in this order: the discovery-vs-relocation question
above, and then `plans/2026-08-23-github-issues-plan-lifecycle.md`, which becomes answerable once
the store's location is fixed.

If the answer to the first question turns out to be genuine relocation, the fallback worth designing
properly is the **Planning Repo Pattern** — a real `plans` git repo at the projects root whose
`.gitignore` treats the sibling project repos as opaque. It gives a single editable location and a
single history, keeps every project repo independent, and needs no submodules. It is the only
central-store option surveyed that doesn't require adopting a tool that rejects markdown.

Do not start moving plan files before this is settled. Half-migrated is the one state worse than
either endpoint, and the current convention is working — nothing here is urgent.

**Adopting a tool wholesale is now ruled out on evidence, not taste.** beads is the only mature
option that solves the problem, and taking it means a Dolt database, federation machinery sized for
agent fleets, and an `AGENTS.md` that tells agents to stop using markdown for tracking and memory —
replacing three conventions that work in order to fix one that is merely inconvenient. Backlog.md
has no cross-repo support in its source at all. tasks.md has the right model and seven stars. What
is left worth taking from all three is the model, not the dependency.
