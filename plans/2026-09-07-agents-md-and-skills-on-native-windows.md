---
status: idea
updated: 2026-11-27
---

# `AGENTS.md` and skills on native Windows

## On the Windows machine, next — do these in order

Written 2026-11-27 from the Linux machine, after it caught up with the Windows work. It lives in
this repo, which the Windows machine pulls, so a Windows session told "do the Windows checklist"
needs nothing pasted. Tick each item here as it is done, with what it printed.

1. **Pull** `power-user-linux-setup`, `win-configs` and `agent-skills`, and **clone**
   `freshful-polite-mcp`, which is not on the Windows machine at all (only `projects\personal\`
   exists there). As of 2026-11-27 the three are clean on Windows but behind GitHub
   (power-user-linux-setup at `c42d5cc`, win-configs at `d39dbf9`, agent-skills at `0e948f2`). Each
   pull brings a new `.gitattributes` (`* text=auto eol=lf`). Afterwards `git status` should be
   clean in each. If files nobody edited show as modified, check
   `git diff --ignore-cr-at-eol --stat` first: empty means line endings only, which is the
   attributes change and not anybody's work. Ask the user before touching it. Pull from the desktop:
   over SSH, `git fetch` to GitHub hangs, since the Windows key is not unlocked there.
2. ~~**Reinstall the skills**~~ **Done 2026-11-27**, by the agent-skills session over the
   herdr-remote SSH key from Linux. The seven agent-skills skills Windows already had were
   reinstalled, none added, and the installed `plans.py` SHA256 matches agent-skills `122e17a`, past
   the `3106b68` fix.
3. ~~**Check the store.**~~ **Done 2026-11-27**, the same way. `where` printed
   `device:  personal — only your own work`, and `doctor` showed the store with its `origin` remote
   0 behind and 0 ahead, fetched within the hour, `sync auto`, and no stranded sensitive-store
   plans. Still to do from a Windows win-configs session: `plans.py absorb` and `plans.py list`, for
   the store-held win-configs plans waiting there (herdr session panel, herdr mods, WSL disk and
   idle shutdown, and the SSH junction filing below).
4. **The junction check**, the one open question in
   `plans/2026-11-25-agents-md-and-agents-skills-as-the-only-source.md`. **From the desktop, not
   over SSH**: an SSH session cannot traverse a junction at all (below), so it would report a
   failure that is not the one being tested. In `freshful-polite-mcp`, run
   `npx skills add ./skills --agent universal claude-code --skill '*' --yes`, start a Claude Code
   session there, and ask it to list its skills. Both of the repo's own skills must appear. If they
   do not, Claude Code is not following the junction the `skills` CLI made.
5. **Report back.** Record steps 1 and 4 here and commit. When the junction check passes, the
   matching open item in the only-source plan above closes with it.

**Found over SSH, 2026-11-27: Windows refuses scoop's junctions in an SSH session**, with error 448,
"untrusted mount point". So `python`, `uv` and the git shim all fail there, and only the real
version directories work. It is why step 4 must run from the desktop. Filed for win-configs as
`2026-11-27-ssh-sessions-cannot-traverse-scoop-junctions.md` in the plans store.

## Context

Asked 2026-09-07: the skills now work on Windows and there is a real use case, so the instructions
half has to follow. _"there are parts of agents md that pertain to skills, and there are
dependencies everywhere, and not easy to keep track of. look at how we could achieve our overarching
goal of agents md composition on windows, or if we could have separate agents md pieces that could
be arranged into a central one with inclusions, or what a good way would be."_

The target and its constraints, from the same exchange:

- **Native Windows with a ported slice of PULSE**, not WSL. (WSL is a separate machine shape and is
  already handled; `plans/2026-08-31-wsl-and-container-first-run-experience.md` now also records
  that WSLg is not a reason to run desktop apps there.)
- **git and Git Bash are present. Python is not guaranteed** — `uv` bootstraps it. Node arrives via
  nvm, and **scoop** is the package manager, chosen because it installs without admin.
- **No admin rights, not reliably** — it is a work machine some of the time.
- _"scripts should check what they have with largely the same mechanisms we already have on linux,
  the shared tools are cross-platform."_
- _"we might want tags for anything that is cross-platform to know what also runs on windows."_
- Agents that must read the file there: **Claude Code, GitHub Copilot (VS Code), Codex CLI,
  Windsurf/Devin**.

This plan is the OS axis. The agent axis was `plans/2026-09-02-agent-harness-support-matrix.md`,
retired 2026-11-25 and superseded by
`plans/2026-11-25-agents-md-and-agents-skills-as-the-only-source.md`, which answers a different
question — which harnesses read what — and its answers are used here rather than re-derived.

**Settled 2026-11-25, from the agent axis:**

- **The tracked `CLAUDE.md` symlink is gone**, here and in every personal repo. Claude Code reads
  `AGENTS.md` itself since 2.1.277, so the breakage in "Three the survey found" item 1 no longer
  exists. The user's Windows machine hit it that morning in `agent-skills` and removed it there
  first.
- **The skills-link question below is answered.** PULSE stopped making a `~/.claude/skills`
  directory link on 2026-09-07, and the `skills` CLI writes one entry per skill itself — a junction
  on Windows. Since 1.9.0 it does so only when the targets span two directories, so PULSE installs
  with `--agent universal --agent claude-code`. Claude Code follows the junction, verified on the
  Windows machine the same day.
- **A repo's own skills get the same treatment**, designed in the next section.

### A repo's own skills, for Claude Code, without a committed symlink

**The problem.** A repo's committed `.claude/skills -> ../.agents/skills` link has the same Windows
problem `CLAUDE.md` had: Git for Windows checks it out as a text file holding the target path, so
Claude Code there sees no repo skills, silently. It affects `freshful-polite-mcp`, `ingesta` and
every repo scaffoldapy generates.

**The `skills` CLI already does the right thing for this, measured 2026-11-25** on CLI 1.9.0 in a
throwaway repo holding one skill at `.agents/skills/demo-skill/`:

- `skills add ./.agents/skills --agent universal claude-code --skill '*' --yes`, run at the repo
  root, left the source untouched and wrote
  `.claude/skills/demo-skill -> ../../.agents/skills/demo-skill`, one relative link per skill. It
  also wrote a `skills-lock.json` recording `"source": "./.agents/skills", "sourceType": "local"`
  and a content hash. `installer.ts` has an explicit `sourceIsCanonical` branch for this case — it
  skips the copy and only makes the agent link — and on Windows that link is a **junction**
  (`platform() === 'win32' ? 'junction'`), which needs no privilege.
- With `.claude/skills` deleted, as on a fresh clone,
  `skills experimental_install --agent universal claude-code` (alias `skills install`) restored the
  link from the lock alone.
- After editing the skill, the same command warned that the skill "does not match skills-lock.json;
  restoring the locked version", then rewrote the lock's hash to the edited content. The edit
  survived only because source and destination are one directory. Under `CI` it reported the skill
  as installed and changed nothing.

**The constraint that decides the design: skills are tried in a project, never globally.** Asked
2026-11-25, the user: _"i don't want to trial skills globally, since globally i expect to have
stability for important things, so i would try them out in a project first"_, and every developer
must be able to try different skills in the same repo without issue. The CLI gives no control over
where a project-scope `skills add` writes: always the skill into `.agents/skills/<name>/` and an
entry into `skills-lock.json` at the repo root (`local-lock.ts`, `LOCAL_LOCK_FILE`, no option or
variable to move or skip it). So **a committed lock makes every trial a modified tracked file**, a
diff each developer carries and must never commit, and two developers' trials would collide in it.
That rules the committed lock out.

**The design, implemented 2026-11-25** — the user's own suggestion: _"don't we author all the skills
in a skills/ directory? would't we gitignore all the installed skills?"_ — the layout `agent-skills`
already uses, applied to every repo:

1. **A repo's skills are authored in `skills/<name>/`**, the committed source. Agents do not read
   it.
2. **Every install target is gitignored:** `.agents/skills/`, `.claude/skills/`, `skills-lock.json`.
   No symlink is committed, and nothing a developer installs is tracked.
3. **Per clone, repo-tasks' `agents.install-skills`, run by `dev-env.setup`**, calls
   `skills add ./skills --agent universal claude-code --skill '*' --yes`: one copy per skill in
   `.agents/skills/` for every agent but Claude Code, one link per skill in `.claude/skills/` for
   Claude Code — a junction on Windows. Without the CLI or npx it says so and skips. Where
   repo-tasks is absent, that one command is the step.
4. **A trial is a project-scope `skills add`** and ends with `skills remove --skill <name>`; both
   touch only ignored paths. Measured in a throwaway repo: `git status` stayed clean, Claude Code
   saw the repo's skill and the trial, and `remove` took only the trial.
5. **Promoting a trial** is copying it into `skills/` and committing it — a vendored copy, which is
   a decision about owning that content.

[PITFALL: **the installed copies do not follow the source.** An edit to `skills/<name>/` reaches no
agent until the install runs again, and `skills update` skips local sources (`update.ts`,
`getProjectSkillsForUpdate`). The CLI's live-link mode exists only in `experimental_sync`, for npm
packages. Re-run `inv agents.install-skills` after an edit — the same edit → install loop
`agent-skills` has always had.]

Landed: `repo-tasks` 945d051 (`agents.install-skills`, in `dev-env.setup`, eight tests),
`scaffoldapy` 7058c65 (template), `freshful-polite-mcp` fb51553 (its two skills moved), `ingesta`
873a456 (README stub moved), `agent-skills` b954314 (the publishing note). Consumers reach
`agents.install-skills` at repo-tasks' next release; until then the README in each `skills/` gives
the npx command.

Rejected: committing the repo's skills into `.agents/skills/` with a per-skill `!` whitelist in
`.gitignore` — the previous draft of this section; it commits into an install target, and a new
skill stays silently ignored until its line is added. Rejected: a committed `skills-lock.json` with
`skills install` as the per-clone restore, which turns every project trial into a tracked-file diff
(see the constraint above). Rejected: repo-tasks creating the links itself (`os.symlink`, or
`mklink /J` on Windows), which reimplements what the CLI already does. Rejected: `core.symlinks`
with Developer Mode, which needs admin once and is unavailable on a work machine.

**Verified 2026-11-25 on the Windows machine (Claude Code 2.1.332, no Developer Mode):** Claude Code
follows a junction for a skill entry. In `nexus`,
`npx skills add ./skills -a universal claude-code -y` left a real copy in `.agents/skills/` and a
junction in `.claude/skills/`, and a headless `claude -p` listed the project skill alongside the
seven global ones, which were reinstalled the same way and are junctions too.

## What breaks, measured rather than assumed

Read off this repo 2026-09-07. Four blockers, all small, all in the slice this actually needs:

| where                 | what                                                 | why it stops Windows dead               |
| --------------------- | ---------------------------------------------------- | --------------------------------------- |
| `tasks/util.py:3`     | `import pwd`                                         | stdlib POSIX-only — `inv` cannot import |
| `tasks/util.py:34`    | `SUDO = … os.geteuid() …` at module level            | `os.geteuid` does not exist on Windows  |
| `tasks/deploy.py:185` | `assemble()` reads fragments with bare `read_text()` | locale encoding; cp1252 on Windows      |
| `tasks/verify.py:187` | `_symlink_check` requires `link.is_symlink()`        | there will not be a symlink there       |

The first two are import-time, so nothing in the repo runs at all on Windows until they are guarded
— that is the whole reason "does PULSE work on Windows" has never had an answer.

[PITFALL: **the encoding one does not raise, it corrupts.** `read_text()` with no `encoding=` uses
the locale encoding until Python 3.15 (PEP 686) and this repo pins 3.14. The expected failure is a
`UnicodeDecodeError` on a cp1252 machine — and that is not what happens for the character that
matters. `→` is U+2192; its UTF-8 bytes `E2 86 92` are **each individually defined in cp1252**, so
the read succeeds and silently yields `â†'`. The fragments are full of `—`, `…` and `→`. A deployed
instructions file that is subtly mojibaked in every session, with no error anywhere, is the worst
shape this whole plan contains. `rg -c "encoding=" tasks/` finds it in exactly one module today.]

Two more that are conventions rather than bugs:

- `util.PULSE_CONFIG_DIR` / `PULSE_STATE_DIR` hardcode `~/.config` and `~/.local/state`. The skills
  already solved this exact problem — `skill-authoring`'s destination table maps them to `%APPDATA%`
  and `%LOCALAPPDATA%`, honouring `$XDG_*` first and branching on `os.name == "nt"` only for the
  default. **Copy that, do not invent a second answer**, because the two would disagree on the same
  machine.
- The write path is already safe **in `deploy`**, which uses `write_bytes` — so no newline
  translation and no CRLF-versus-digest fight there. `util.py`'s `ensure_block`, `remove_block` and
  the `~/.claude/settings.json` writer all use bare `write_text()`, which translates `\n` to
  `os.linesep` on Windows; those need `newline="\n"`.

### Three the survey found that bite before deployment even starts

1. **A Windows clone of this repo has a broken `CLAUDE.md`.** It is tracked as a symlink (`120000`
   in `git ls-files -s`), and Git for Windows sets `core.symlinks=false` by default — independently
   of Developer Mode, unless `MSYS=winsymlinks:nativestrict` is set. The checkout is then a regular
   file whose entire content is the string `AGENTS.md`, and Claude Code loads that as the project
   instructions. This is the repo's own agent config being wrong on Windows, before anything is
   deployed anywhere.
2. **The quality gate fails on a Windows checkout, on every markdown file.** Git for Windows'
   installer sets `core.autocrlf=true` system-wide, so tracked files check out CRLF; dprint's
   markdown plugin defaults to LF and this repo's `dprint.json` sets no `newLineKind`. There is no
   `.gitattributes` here and `.editorconfig` sets no `end_of_line`. A `.gitattributes` pinning
   markdown to LF fixes it, and is worth having regardless of Windows.
3. **A UTF-8 BOM silently destroys a `SKILL.md`.** Both `python-frontmatter` and the `skills` CLI
   anchor their frontmatter match at position 0 with no BOM strip, so the skill is skipped with a
   missing-fields warning rather than an error. Windows PowerShell 5.1 cannot write BOM-less UTF-8
   at all, so a hand-edit there is the likely source. Relevant here because skills are the half that
   already works on Windows.

Two more worth knowing but not blocking: `HOME` and `%USERPROFILE%` can be **different directories**
when Git Bash is in play — Git for Windows sets `HOME` to `%HOMEDRIVE%%HOMEPATH%` when that exists,
which on a domain-joined machine with a network home share is a different place than the profile —
and Claude Code resolves home as `HOME` → `USERPROFILE` → `HOMEDRIVE`+`HOMEPATH`, so a Git Bash
session and a PowerShell session can read two different `~/.claude`. And `shlex.join` in
`tasks/ai.py` produces POSIX quoting that `cmd.exe` does not parse the same way.

## What the research says, and it converges

Three parallel surveys, 2026-09-07. Everything below was read in a clone under `$RESEARCH_HOME`
except where a vendor has no public repo.

### Nothing composes per-OS. This is the finding the design rests on

- **No agent harness supports conditional content by OS**, at all. Every conditional mechanism that
  exists is a _file-path_ predicate — Copilot's `applyTo`, Cursor's `globs`/`alwaysApply`, Claude
  Code's `.claude/rules/` `paths:`, Windsurf's `trigger: glob`. None takes a platform.
- **No external tool does fragments × OS either.** The AI-rules generator category — `rulesync`,
  `ruler`, `ai-rulez`, `agentsmesh` — models fragments × _agent_, and the absence was confirmed in
  source rather than in prose: `process.platform` is entirely absent from `ruler`'s `src/`, appears
  in `rulesync` only in path helpers, and `runtime.GOOS` is absent from `ai-rulez`'s non-test
  `internal/`. The per-OS axis exists only in the dotfile-manager category (chezmoi's `.chezmoi.os`,
  yadm's `{% if yadm.os %}`).
- **The `AGENTS.md` spec has no include directive**, and composition is an open issue on it
  (`agentsmd/agents.md` #11), with a Gemini CLI maintainer on the thread saying a standardised
  reference feature would help them support the file. The closed v1.1 draft adds precedence and
  frontmatter — nothing about includes, nothing about platforms.

So the assembler stays, and the OS axis has to be ours. That is a conclusion, not a preference: the
one thing this problem needs is the one thing nothing off the shelf provides.

### The includes that do exist could not carry it anyway

Six harnesses have a real `@include`, and they disagree on every rule that matters for a
home-directory layout. `~` expansion: Claude Code and Amp yes, Copilot refuses it explicitly, Gemini
CLI and goose do not recognise the character — and **Gemini's failure is silent**, the line simply
stays as literal text. Absolute paths: two allow, two refuse. Sandboxing: Gemini confines an import
to the nearest `.git` root or else to the importing file's own directory, goose confines a global
file's imports to that file's parent, Copilot to the repo or the instructions directory. Depth caps
of 4, 5 and 3 respectively.

One fragment set that all of them expand identically does not exist. An include-based design would
be a different design per harness.

### Three of the current symlinks are already unnecessary

Verified in source: **Cline, goose and Kimi Code read `~/.agents/AGENTS.md` natively** — goose via
an `AgentsHome` path that resolves to `$HOME/.agents`, Cline via `resolveGlobalAgentsRulesPath()`,
Kimi after its own `~/.kimi-code/AGENTS.md`. That is the canonical path this repo already deploys
to, so for those three there is nothing to link. It also means the `~/.agents/` choice made
2026-09-04 is being independently converged on by other vendors, which is worth knowing before
anything moves.

### Claude Code's own Windows advice is "do not symlink"

From its memory docs, verbatim: _"On Windows, creating a symlink requires Administrator privileges
or Developer Mode, so use the `@AGENTS.md` import instead."_ So the vendor's recommended Windows
wiring for exactly our situation is an import file, not a link.

[PITFALL: **the import route has two open bugs and one behaviour that would bite this design
specifically.** `anthropics/claude-code#92673` — an `@import` of an absolute Windows path containing
spaces does not resolve, and fails as literal unexpanded text with no error, which on
`C:\Users\<name>\...` is a live risk. `#88405` — symlinked files under `.claude/rules/` are not
auto-loaded, contradicting the docs. And in Cowork sessions Claude Code skips a
`~/.claude/CLAUDE.md` that is itself a symlink **and** skips user-scope imports resolving outside
the working directory — so on that surface both a link and an import degrade, and only a real
assembled file survives. A plain generated file at each destination is the only wiring with no
vendor caveat attached.]

### The skills half is nearly free, and Claude Code is the whole of what is left

Read out of the shipped Claude Code binary rather than its docs: **`.agents/skills` appears zero
times in it**, against 50 occurrences of `.claude/skills`. So the cross-tool path Claude Code is
given by symlink on Linux is not something it will ever read natively, and that link is load-bearing
on every platform rather than a convenience.

Every other agent named for this machine reads `~/.agents/skills` directly, verified per vendor:
Codex (`host_roots.rs` adds `home/.agents/skills` as a user root, with a test asserting it), Copilot
(documented, verbatim: _"create a `~/.copilot/skills` or `~/.agents/skills` directory"_), Gemini CLI
(`getUserAgentSkillsDir()`), Cursor (documented). So the skills half needs nothing on Windows except
whatever makes Claude Code see them.

**And the `skills` CLI already solved that.** It is `vercel-labs/skills`, its CI matrix includes
`windows-latest`, and on Windows it creates a **junction** per skill rather than a symlink, falling
back to copying with a Windows-specific message when that fails. It links per skill —
`<base>/<skill-name>` — never the whole directory. PULSE's own `_ensure_agents_skills`, which links
the whole `~/.claude/skills` directory, is therefore the one piece with no Windows story.

[PITFALL: **the decision below is wrong on its central fact, and is reopened. Read this first.**
Written 2026-09-07 and corrected the same day when the user asked how the symlink would work on
Windows — which it does not, and the answer given for keeping it does not survive its own source.

- **`claude-code` is not a universal agent.** `src/agents.ts:152-156` gives it
  `skillsDir: '.claude/skills'`, and `isUniversalAgent` is exactly
  `agents[type].skillsDir === '.agents/skills'` (`agents.ts:879-881`). So the early return quoted
  below — which applies only to universal agents — **never applies to Claude Code**. It applies to
  `github-copilot`, whose `skillsDir` really is `.agents/skills`.
- **So the CLI already writes Claude Code's per-skill entry itself.** For a non-universal agent at
  global scope, `installer.ts:391` calls `createSymlink(canonicalDir, agentDir)` with
  `agentDir = ~/.claude/skills/<skill>`, using a **junction** on Windows and falling back to copying
  the skill directory when that fails (lines 393-405). No privilege needed on either platform.
- **Which makes PULSE's whole-directory link redundant for anything the CLI installs, and it is the
  one shape that cannot be made on Windows.** A directory symlink needs Developer Mode or
  Administrator; a junction would do, but nothing in this repo creates one and there is no public
  Python API to. "Windows keeps the same shape from a junction" was written below as though settled
  and was a proposal that had not been checked.
- **The community shape is per-skill, not per-directory.** Claude Code's own docs say a
  `<skill-name>` _entry_ may be a symlink; nothing documents `~/.claude/skills` itself being one.
  The link is our invention, and being the outlier is what made Windows hard.

What is genuinely unresolved is a version gap, not a design question. `setup.toml` records a
2026-08-27 measurement that the CLI "announces that symlink and does not create it", which is why
`_ensure_agents_skills` exists. That was measured against the installed build, still **v1.5.10**;
the source above is **v1.5.24**. The directory link also _masks_ the per-skill behaviour — with the
parent symlinked, `isAlreadyLinked`'s parent resolution (lines 214-222) makes the two paths
identical and the CLI correctly skips — so the current arrangement cannot observe what the CLI would
do without it. Updating the CLI and re-measuring with the link removed is the experiment; until then
neither the old note nor this correction is proven against what actually runs here.]

[DECISION: ~~**`~/.claude/skills` stays a symlink, and does not become a copy with the instruction
files.**~~ **Superseded by the pitfall above** — kept because its second finding is still true and
still matters. Written 2026-09-07 from the CLI's source. Two findings, both in `src/installer.ts`:

- **The CLI is written _for_ this exact arrangement.** Lines 214–222 resolve symlinks in _parent_
  directories before deciding whether a skill is already installed, with the comment naming our
  case: _"This handles cases where e.g. `~/.claude/skills` is a symlink to `~/.agents/skills`, so
  `~/.claude/skills/<skill>` and `~/.agents/skills/<skill>` are physically the same."_ The link is
  not something the tool tolerates; it is a case it was taught.
- **At global scope it writes only the canonical directory.** For a universal agent — which is all
  four of ours — lines 362–372 copy into `~/.agents/skills/<skill>` and return early, explicitly to
  avoid duplicates.

Put together: with the link, `skills add --global` reaches Claude Code immediately. As a copy, it
would reach `~/.agents/skills` and stop there until the next `inv ai.install-skills`, **and** the
CLI's duplicate detection would stop recognising the two paths as one, so it would start creating
the per-agent copy it currently skips. A copy there buys Windows uniformity and costs the Linux
workflow plus the tool's own model of the machine.

That second finding stands and is the one to keep: **while the directory link exists, it is load-
bearing**, because the CLI's parent-symlink resolution then treats `~/.claude/skills/<skill>` and
`~/.agents/skills/<skill>` as the same file and skips creating anything. Removing the link is
therefore safe only together with a CLI that does create the per-skill entry — which is what the
pitfall above says has to be measured rather than assumed.]

**Claude Code follows a junction for a skill entry — verified 2026-11-25**, see "A repo's own
skills" above. The inference recorded here (the binary classifies a junction as
`isSymbolicLink: true`, and every skill loader accepts `isDirectory() || isSymbolicLink()`) was
right.

### Nothing out there syncs both, and the drift model we just adopted is the mature one

Asked because replacing five symlinks with five copies takes on a drift problem, and it would be
foolish to own that if somebody else had solved it. Read from the clones, 2026-09-07:

**The generator category does not have this problem, because it does not reconcile — it
regenerates.** `ai-rulez` is the one with real skills machinery (`internal/config/skills.go`,
`includes/skill_resolver.go`, `crud/installed_skill.go`): skills are declared as `installed_skills`
with a git or local `source`, a `ref`, a `path` and a `local_override`, fetched and re-rendered on
every run. There is no state to drift because the output is disposable. That is a coherent design
and it is not ours: our destinations are files other tools read at their own paths, which we must
not blow away wholesale.

**`chezmoi` is the only surveyed tool that tracks drift, and its model is the one PULSE already
has.** `internal/chezmoi/entrystate.go`: an `EntryState` is `{Type, Mode, ContentsSHA256}`,
persisted, and compared on apply — `Equal` is a type check, a permission check and a SHA-256
comparison. PULSE's deploy manifest records `{package, source, mechanism, digest, deployed_at}` per
destination and `classify` compares the digest. Same shape, arrived at independently, which is the
strongest available argument for keeping the mechanism in-house rather than adopting a second
config-management system that would co-own `$HOME`.

[PITFALL: **`chezmoi` skips the permission comparison on Windows entirely** — `Equal` guards it with
`runtime.GOOS != "windows"` — because Windows synthesises `st_mode` from file attributes. That is
the same conclusion `skill-authoring` reached for `0700` checks, from a second direction, and it is
a trap waiting for any content check we extend to modes: a mirror that compares permissions would
fail on every Windows machine for a concept that does not exist there.]

So: **keep owning it.** The verdict is not "nothing exists", it is that the two categories solve
different problems and the one whose problem we actually have already agrees with us about the
mechanism.

## Design

### 1. The OS axis goes on the fragment, not into the fragment

`agents_md` entries are `{ src, order }` today. Add an optional platform predicate — the shape to
settle is below — so a fragment can say it is Linux-only, and the assembler filters before
composing. Whole fragments, never a conditional inside one, for the reason the fragment split
already gives: the assembler never merges at the rule level, and a rule may not live half in one
place and half in another.

**This makes the file smaller per machine rather than larger**, which matters more than it sounds:
the deployed file is **806 lines / 54,458 bytes** today against a review reference point of ≤200
lines, and `plans/2026-08-26-agents-md-leanness-pass.md` is open on exactly that. A Windows machine
has no use for the sudo rule, the SSH-agent rule or the direnv rule; dropping them is leanness that
costs no content.

[NEEDS CLARIFICATION: **is the predicate a new field, or does the existing `[needs …]` label already
carry it?** Every rule that is false on Windows is already labelled with what it depends on —
`[needs askpass-zenity]`, `[needs PULSE's zprofile]`, `[needs direnv]` — and
`inv ai.check-rule-prerequisites` already reads those labels and reports a rule whose package is
undeclared, disabled, or excluded by tags. The machinery to answer "does this rule's prerequisite
exist on this machine" therefore exists and stops one step short of filtering the assembly. Making
the label load-bearing is the smaller change and kills a class of drift outright — a rule can no
longer assert into a session something the machine does not have. Against: labels are per-rule and
fragments are per-file, so a fragment with one Linux-only rule in it would need either a split or a
rule-level assembler, and rule-level assembly is precisely what the fragment design rejected.]

[NEEDS CLARIFICATION: **is the axis "OS" or "what this machine has"?** The user asked for _"tags for
anything that is cross-platform to know what also runs on windows"_, which is a package-level
portability claim, and the tag system already gates packages. If portability is a package tag, then
a fragment's applicability could be derived from its `[needs <package>]` label plus that package's
tags, with no new axis at all — one mechanism instead of two. This is the same question as the one
above from the other end, and they should be answered together.]

### 2. On Windows there is no link. Deploy the file to every destination

The survey killed the tiered fallback this section first proposed, and it is worth recording why,
because the idea is the obvious one and someone will have it again.

- **A symlink needs Developer Mode or Administrator.** `Path.symlink_to` is `os.symlink`, which
  raises `OSError` WinError 1314 without the privilege; Developer Mode itself needs admin once to
  turn on and can be disabled by org policy. CPython's own test suite does not assume it works — it
  probes by attempting one and catching `OSError`.
- **A junction cannot replace a file link.** Junctions are directories only. **All five
  `symlink_dest` entries are file links**, so the admin-less mechanism does not apply to any of
  them. This is the fact that collapses the design: the tier that made the fallback look workable
  covers none of the actual destinations.
- **A hardlink works without privilege but Anthropic documents against it.** NTFS, files, same
  volume, no privilege — and then Claude Code's Cowork sessions _"skip a `~/.claude/CLAUDE.md` that
  is itself a symlink or hard link"_, with the shipped binary rejecting `nlink > 1` across several
  other paths. Choosing it means choosing a wiring the vendor has already said it ignores.

So on Windows every destination gets **a real file**, written by the same assembler. That is not a
degraded fallback, it is the only wiring with no vendor caveat attached — and it is what Claude
Code's own `/import` does, copying `~/.codex/AGENTS.md` into `~/.claude/CLAUDE.md` rather than
linking it. Anthropic's documented alternative, `@AGENTS.md`, is worse here for a reason specific to
us: see the import PITFALL above, and note it would also mean the deployed file is no longer what
the agent reads.

Copies drift, which is the real cost and the thing to design against — `deploy`'s digest comparison
already detects it, and `assemble()` is a pure function of the fragments, so N destinations cost N
`write_bytes` calls and re-deploy is idempotent. The manifest already tracks per-path digests.

**`verify.py` stops asking `is_symlink()` and asks whether the destination is equivalent** — resolve
for a link, equal digest for a copy. That is a better check than today's on every platform, because
it is the question the current one is only a proxy for.

[PITFALL: **`Path.is_symlink()` is `False` for a junction, and `shutil.rmtree` refuses one.** If a
junction is ever used for the one directory case that can take it, every is-this-a-link branch in
`deploy` reads it as a plain directory. `Path.is_junction()` exists from 3.12, `Path.readlink()`
works on a junction, and `Path.unlink()` is the correct removal — it deletes the link and leaves the
target. Reach for those rather than the `os.path` spellings the source material uses.]

[PITFALL: **pathlib cannot create a junction, and that is the one place this repo's pathlib-only
rule has no answer.** There is no public API at all: `_winapi.CreateJunction` is private,
undocumented outside the audit-events table, and every use of it in CPython is inside CPython's own
tests, which themselves skip on `OSError`. It also stores the target as an absolute path resolved
against the **process cwd**, not the link's directory. If the skills directory ever needs a
junction, that call is quarantined behind one helper with a comment saying why the rule is broken
there — rather than the rule quietly eroding across the module.]

### 3. What the Windows side actually installs

The port is not PULSE. Of 129 declared packages, 42 are `apt`, 22 are `gnome-extension`, and another
19 are `apt-repo`/`deb-url`/`deb-github` — none of which mean anything on Windows. The slice this
plan needs is two packages (`agents-md`, `agent-skills`), the `ai` and `deploy` namespaces, and
whatever `verify` needs to prove them.

`scoop` is the natural Windows analogue of the `apt` method for anything beyond that, and it fits
the existing dispatch shape — but nothing in this plan requires it yet, and adding a method with one
consumer is worse than adding it when a second package needs it.

## Open questions

[DECISION: **the Windows machine gets the fragments from a clone of this repo, and the Windows rules
fold in as fragments.** Decided by the user 2026-11-25, over a rendered `dist/AGENTS.windows.md` and
over keeping a separate Windows file. `win-configs/claude/CLAUDE.md` (PowerShell 7, the tool table,
Bash tool denied, no-memory, Documents and Artifacts) becomes a Windows-only fragment here.
`win-configs` stops deploying the instructions file once PULSE does, and keeps scoop, the terminal
and the pwsh profile. On Windows the entry point is `spowse deploy.all` +
`spowse ai.install-skills`, not `inv setup`.

Interim state, 2026-11-25: `win-configs` 0292aba copies its file to `~/.agents/AGENTS.md` and
`~/.claude/CLAUDE.md` (identical), and installs the global skills with
`-g -a universal claude-code`. So the destinations already have the shape PULSE will write.
Reconciling content is part of the fold-in. Several of the Windows file's rules (naming, Markdown
tables, commits, no personal details) are cross-platform and may duplicate or contradict fragments
here. Diff them rule by rule instead of appending the file whole.]

[DECISION: **Copilot and Windsurf are dropped for now**, by the user on 2026-11-25. Nothing is
written for either on Windows: `also_deploy_to` declares Copilot's path `["linux"]` (`01728fb`),
where it was already written before this plan, and nothing here has ever written for Windsurf. The
two facts that made them open questions still hold if either comes back: Copilot's include refuses
`~/` and absolute paths, so a copy into its own directory is the only wiring, and Windsurf's global
rules file has a 6,000-character limit, which the assembled file exceeds about eight times over on
either platform.]

## Recommended direction

Answer the two paired questions in §1 first — they are one question — because everything else is
mechanical once the axis exists.

The link strategy no longer needs deciding: **there are no links on Windows**, junctions cover none
of the file destinations and the one privilege-free file mechanism is one Anthropic documents
against. That is settled, which moves the work to the order below.

1. **The three pre-deployment breakages**, because they are wrong on Windows today and none of them
   waits on the axis: `.gitattributes`, the tracked `CLAUDE.md` symlink, and `encoding="utf-8"` on
   every text read. The encoding one first — it corrupts silently, and every later verification on
   Windows would be measuring a mojibaked file.
2. **The four import- and write-time blockers**, which is an afternoon.
3. **Prove the assembler on Windows with the existing fragment set**, before adding one
   Windows-specific rule. A deployed file that is byte-identical to the Linux one is the checkpoint
   that says the port works; content differences are the next problem, not this one.
4. **Then the axis**, then the Windows-only rules it enables.

**Steps 1–3 are done, 2026-11-25, on the Windows machine:**

- `a504832`: `inv` imports on Windows (`pwd` imported locally, `util.is_root()` replaces the
  `os.geteuid()` checks, `getpass.getuser()` for the user name).
- `529bdb3`: every text read and write in `tasks/` and `tests/` passes `encoding="utf-8"`, and every
  `write_text()` passes `newline="\n"`. That's 299 calls, not the "about 20" this plan counted.
- `76798db`: three paths that came out wrong on Windows: `additionalDirectories` in Claude settings,
  `home.list-claims` labels, and `session_bus_address()`.
- `87b2836`: the unit suite runs on Windows: 898 passed, 41 skipped by `tests/platforms.py` marks
  with stated reasons. `inv quality.precommit` passes there too, so Windows is now a machine the
  repo can be developed on, not only deployed to.
- `c709b6a`: `.gitattributes`.
- Not needed: the `verify.py` symlink check had already become a content comparison, and
  `PULSE_CONFIG_DIR`/`PULSE_STATE_DIR` already agree with the skills, which moved to
  `~/.config`/`~/.local/state` on every OS on 2026-11-08 (the `%APPDATA%` advice in "What breaks" is
  out of date).
- Step 3 checkpoint: `deploy.status` runs on Windows, and `deploy.expected_bytes()` for
  `~/.agents/AGENTS.md` renders 62,608 bytes, 971 lines, no CR, with `→`/`—` intact and no mojibake.
  It's the same pure function over the same UTF-8 bytes as on Linux; no Linux machine was at hand to
  compare digests directly.

**Step 4 is done too, 2026-11-25.** Both §1 questions were answered by the user: the axis is an
explicit, required `platforms` field on every package and every fragment, not tags and not a
derivation from `[needs …]` labels (`b2956cb`). Fragments that mixed platforms were split into
`<parent>.<platform>.md` supplements that land under the parent's heading (`41c2190`). The Windows
machine's global rules were merged rule by rule (`60ea993`), after the user decided the four real
conflicts: auto-push own repos on both platforms; writes to another repo allowed only with explicit
approval (`4c68269`); caveman replaced by a plain no-fluff reply rule (`c5a970f`); supplements
rather than per-OS clusters. Rendered: Linux 1,043 lines, Windows 838.

**Deployed on the Windows machine, 2026-11-25, at the user's go-ahead.** `~/.agents/AGENTS.md` and
`~/.claude/CLAUDE.md` are identical, and a fresh headless session loads the Windows rules. The
deploy refused at first to overwrite the `win-configs`-written `~/.claude/CLAUDE.md`, as designed;
that file was moved aside and the deploy re-run. `win-configs` `d92600f` deleted its
`claude/CLAUDE.md`, and its install snippet now runs this repo's `deploy.all` instead.

**What is left:**

- Copilot and Windsurf: dropped for now, see the decision under "Open questions".
- ~~`.claude/settings.json` from repo-tasks' `agents.wire-claude-hook`~~ — done 2026-11-26.
  repo-tasks v0.8.0 removed the task, `[packages.claude-direnv-hook]` replaced it at user level, and
  every repo that tracked the file deleted it: this one, repo-tasks and agent-skills on the Windows
  machine; hekate in its PR 31; scaffoldapy, ingesta, invoke-stubs and olx-polite-mcp in the v0.8.0
  sweep. The home path stays in those repos' published history; purging it would be a history
  rewrite, left undone.
