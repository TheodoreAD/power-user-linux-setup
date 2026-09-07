---
status: idea
updated: 2026-09-07
---

# `AGENTS.md` and skills on native Windows

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

This plan is the OS axis. The agent axis is `plans/2026-09-02-agent-harness-support-matrix.md`,
which is in progress and answers a different question — which harnesses read what — and its answers
are used here rather than re-derived.

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
the whole `~/.claude/skills` directory, is therefore the one piece with no Windows story, and the
question is whether it should keep that shape there or defer to the CLI's per-skill junctions.

[UNVERIFIED: **whether Claude Code follows a junction for a skill entry.** Its docs say a
`<skill-name>` entry "can be a symlink to a directory elsewhere on disk", and its binary classifies
a Windows junction as `isSymbolicLink: true` in its own directory-listing wrapper while every
user/project skill loader accepts `isDirectory() || isSymbolicLink()` — so it almost certainly
works. That is source inference about a closed binary, not documentation and not a Windows test. It
is also the single fact the skills half rests on, so it is the first thing to check on a real
Windows machine.]

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

[NEEDS CLARIFICATION: **where does the Windows machine get the fragments — a clone of this repo, or
a rendered artifact?** A clone means the whole repo lands on a work machine and the port has to be
real. A rendered artifact (assemble on Linux, commit `dist/AGENTS.windows.md`, fetch it there) needs
almost no port at all, and this repo already has a convention for it — "Regenerating a file from a
canonical source" says commit the regenerated output and run regeneration as a deliberate standalone
command. The user asked for a port, so this is a question about how much of one, not whether.]

[NEEDS CLARIFICATION: **does Copilot get written to on Windows?** It is one of the four named
agents, and PULSE deliberately writes nothing for Copilot today because no confirmed path-scoped
setting was found. Its include also refuses `~/` and absolute paths and must stay within the
instructions directory, so a copy is the only wiring available — which is a decision about writing
into a vendor's directory, not a mechanism question.]

[NEEDS CLARIFICATION: **Windsurf's global rules file has a 6,000 character limit** and the assembled
file is 54,458 bytes — nine times over. So Windsurf cannot take this file whole on any platform, and
"which rules does a Windsurf machine get" is a content question that the OS axis does not answer.
Filed here because Windsurf was named as a target; it may deserve its own plan.]

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

The one thing to check on a real Windows machine before trusting any of it is whether Claude Code
follows a junction for a skill entry, since the whole skills half rests on it and the evidence is
inference from a closed binary.
