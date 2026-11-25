## Agent instructions & knowledge

### Setting up a repo's agent instructions and skills

`AGENTS.md` at the repo root is the only instructions file. **No `CLAUDE.md` at all** — not a
symlink, not an `@AGENTS.md` import. Claude Code reads `AGENTS.md` itself since 2.1.277, but only
while no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` sits in the working directory or
above it, so adding one is what switches that off. A Claude-specific addendum goes in `AGENTS.md`
under a labelled heading.

**A repo's own skills are authored in `skills/<name>/`, and every install target is gitignored** —
`.agents/skills/`, `.claude/skills/` and `skills-lock.json`. Agents read the installed copies, not
`skills/`, so after cloning or editing a skill run `inv agents.install-skills` (part of
`inv dev-env.setup`), or `npx skills add ./skills --agent universal claude-code --skill '*' --yes`
where repo-tasks is absent. Never commit a symlink — a Windows checkout without Developer Mode turns
it into a text file — and never commit into an install target, which is where a developer trying
another skill with `skills add` writes.

**The home directory works differently, and assuming it matches costs an edit.** The real file is
`~/.agents/AGENTS.md`, the path four agents read natively. Every other place these rules appear is a
**copy** of it, not a symlink: `~/.claude/CLAUDE.md`, plus one path per installed agent (verified
2026-09-09, three distinct inodes here, link count 1 each). So editing whichever one a session
happens to open is not editing the original, and the next deploy overwrites it silently rather than
refusing. There is deliberately nothing at `~/AGENTS.md`, retired 2026-09-09 because no agent ever
read it. Home skills are installed by the `skills` CLI as one real copy in `~/.agents/skills/` plus
a per-skill link in `~/.claude/skills/`; that directory stays real, because Claude Code keeps its
account-synced skills in it.

### Where durable knowledge goes

Durable repo-specific knowledge → that repo's own `AGENTS.md` (or a `docs/*.md` it points to);
durable cross-repo or personal preference → `~/.agents/AGENTS.md`; anything plan-shaped → `plans/`,
per the `plan-conveyor` convention.

**Never a harness's own memory store — not for durable content, not for perishable content, not as a
staging area.** They are invisible to every other contributor, every other agent tool, every code
review, and usually to every other repo's sessions on the same machine, and they vendor-lock the
work. The sorting rule: **configuration describes the harness** (`settings.json`, hooks,
keybindings) and belongs to it; **anything describing the work is a plain file any agent can open.**
An existing memory entry is migrated to one of the three destinations above and deleted, not kept in
sync.

**Within a repo's own `AGENTS.md`, carry what an agent cannot discover by opening the file it is
about to change**, and point at the implementation site for everything else. A comment at the
implementing line is read exactly when it is relevant and cannot go stale against its own code. A
copy in the instructions file can, is paid for in every session whether or not it is needed, and
silently competes with the code it describes. Three things survive that test: the **cross-file
invariant** nobody can see from one file (two scripts pinning one tag), the **discovery step** that
says which file to open at all, and the rule that **fires while you are editing somewhere else
entirely** — a marker a task needs, applied in a module that never mentions it.

### Choosing a mechanism for agent instructions, skills, or tools

The artifact vocabulary is `AGENTS.md`, Agent Skills and MCP. Anything vendor-specific is admissible
only as **harness plumbing** — something that makes one agent work better on this machine, like a
`settings.json`, a hook or a keybinding — and never as a **carrier** for instructions or knowledge.
That is the same line the memory-store rule above draws for one case. This is the general form, and
it applies before a design exists rather than after.

The miss is silent and expensive in the same way. A design built on a vendor mechanism reads as
finished and works, right up until the harness changes or a second one is onboarded, and then the
work inside it is thrown away rather than moved. Ask which of the two a mechanism is while choosing
it.

### Installing agent instructions and skills on this machine [needs setup.toml]

`inv ai.install-skills` sets up `~`'s `.agents/skills/` and its `.claude/skills` symlink, and
installs every skill declared in `setup.toml`, never overwriting existing content. A new Python
project's own `AGENTS.md`/`CLAUDE.md`/`.agents/skills` scaffold comes from
[`scaffoldapy`](https://github.com/TheodoreAD/scaffoldapy) at generation time, not from a task run
afterwards. The convention these implement is in "Agent instructions & knowledge" below.

**Every skill on this machine is authored in `agent-skills`** — published as
`TheodoreAD/agent-skills`, checked out alongside the other personal repos — not in
`power-user-linux-setup`, which only installs them. To change one, edit it there and follow the
`skill-authoring` skill's sequence. The step that gets skipped is the push, because the installer
clones from the remote, so a committed but unpushed edit reaches nothing. Never edit the copy under
`~/.agents/skills/`: the next install overwrites it and it never leaves this machine.

### Which sessions load this file [Claude Code]

Built-in `Plan`/`Explore` subagents never load it. Claude Code deliberately skips
`CLAUDE.md`/`AGENTS.md` at every level for those agent types. Every rule in this file reaches only
the main session and custom subagents whose definitions don't override the system prompt. When a
rule matters for a `Plan`/`Explore` task, restate it in that subagent's own prompt. The Bash rules
always matter there, since subagents had the worst measured `sed -n`/`cd` rates of any session, so
paste this into every `Plan`/`Explore`/`claude-code-guide` prompt: "Use Read/Grep/Glob for files,
never `cat`/`sed -n`/`grep` via Bash. One Bash command per call, no `&&`/`;` chains, no `cd` — cwd
is already the repo. Never pipe output through `| head`/`| tail`."

**A research prompt needs one clause more**, for the same reason and with a worse measured rate:
"Clone sources into `$RESEARCH_HOME` with the `research-library` skill and grep them locally; fetch
a page only where there is no repo." Without it the subagent fetches pages, because that is what the
prompt asked for — see "About to fetch a page or file to learn how something works".

### Writing conventions into a shareable skill or template

Apply them to one real, already-working repo first, never straight from research to the shareable
artifact. A pilot surfaces what research can't: rules that are noise against a repo's deliberate
style, and config footguns that would ship to every consumer verbatim.

### Machine behavior belongs in global config, not in a repo

Git and agent-harness behavior comes from global config, so every repo works the same. Don't add
local git config (`core.autocrlf`, `url.*.insteadOf`, ...) or `.claude/settings*.json` entries that
would make sense in any repo, and never add hooks. `.claude/settings.local.json` is only for what is
specific to that repo on this machine, such as `additionalDirectories`. Propose the global change
instead: in `power-user-linux-setup` on Linux, in `win-configs` on Windows.

### Proposing an enforcement mechanism for agent behavior

Skills and instructions are the mainstay of directing agents. To correct a recurring agent behavior,
prefer teaching the agent what to run over a mechanism that fires behind its back — a git hook, a
harness hook, a CI auto-fix bot. Agents get the same standard as developers: they should know what
to run, not be silently corrected.
