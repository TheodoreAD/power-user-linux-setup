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
— that is the whole reason "does PULSE work on Windows" has never had an answer. The third is the
one that would have been found late and blamed on something else: every fragment is full of em
dashes and arrows, so the assembler would raise `UnicodeDecodeError` on a machine whose locale is
not UTF-8, and Python does not default to UTF-8 mode until 3.15 while this repo pins 3.14.

Two more that are conventions rather than bugs:

- `util.PULSE_CONFIG_DIR` / `PULSE_STATE_DIR` hardcode `~/.config` and `~/.local/state`. The skills
  already solved this exact problem — `skill-authoring`'s destination table maps them to `%APPDATA%`
  and `%LOCALAPPDATA%`, honouring `$XDG_*` first and branching on `os.name == "nt"` only for the
  default. **Copy that, do not invent a second answer**, because the two would disagree on the same
  machine.
- The write path is already safe: `deploy` writes with `write_bytes`, so no newline translation and
  no CRLF-versus-digest fight. Only the read side needs the encoding.

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

### 2. Linking degrades to what Windows can do without admin

Symlinks need Developer Mode or elevation, which this machine may not have. The fallbacks are not
equivalent and the choice differs by kind:

- **A directory** (`~/.claude/skills` → `~/.agents/skills`) — a junction is the admin-less option.
- **A file** (`~/.claude/CLAUDE.md` → `~/.agents/AGENTS.md`) — a hardlink is admin-less on the same
  volume, and survives this repo's writer because `deploy` writes in place with `write_bytes` rather
  than replacing the file by rename.
- **A copy**, last resort, which drifts between deploys and therefore has to be verified by content
  rather than by identity.

[UNVERIFIED: the junction and hardlink claims above are the design's load-bearing Windows facts and
the survey answering them had not landed when this section was written. Confirm before building:
whether a junction really needs no elevation, what creates one from Python (there is no stdlib API —
`_winapi.CreateJunction` is private), whether `os.link` needs any privilege, and what
`Path.symlink_to` raises without it.]

`verify.py` then cannot ask `is_symlink()`. The check becomes "this destination is equivalent to the
deployed file" — resolve for a link or junction, same file index for a hardlink, equal digest for a
copy — which is a better check than the current one on every platform, since it is the question the
current one is a proxy for.

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
mechanical once the axis exists. Then port the four blockers, which is an afternoon, and prove the
assembler on Windows with the existing fragment set before adding a single Windows-specific rule.
Take the link strategy last: it is the only part with an unverified premise, and a copy with a
content check is a correct fallback that would let the rest ship without it.
