## Agent instructions & knowledge

### Setting up a repo's agent instructions and skills

`AGENTS.md` at the repo root is the real file — the cross-tool convention read by 30+ agents.
`CLAUDE.md`, if present at all, is a plain **symlink** to it, never a file containing the
`@AGENTS.md` import directive (Claude-Code-specific syntax other harnesses would read as literal
text); `~/AGENTS.md` itself follows this, with `~/.claude/CLAUDE.md` symlinking to it. Nothing can
be appended below a symlink's target, so a genuinely Claude-specific addendum goes in `AGENTS.md`
itself or a separate `.claude/`-scoped file. Skills live in `.agents/skills/`, the cross-tool
convention, with each agent's own skills directory symlinked to it for the agents that don't read it
natively.

### Where durable knowledge goes

Durable repo-specific knowledge → that repo's own `AGENTS.md` (or a `docs/*.md` it points to);
durable cross-repo or personal preference → `~/AGENTS.md`; anything plan-shaped → `plans/`, per the
`plan-docs` convention.

**Never a harness's own memory store — not for durable content, not for perishable content, not as a
staging area.** They are invisible to every other contributor, every other agent tool, every code
review, and usually to every other repo's sessions on the same machine, and they vendor-lock the
work. The sorting rule: **configuration describes the harness** (`settings.json`, hooks,
keybindings) and belongs to it; **anything describing the work is a plain file any agent can open.**
An existing memory entry is migrated to one of the three destinations above and deleted, not kept in
sync.

### Installing agent instructions and skills on this machine

`inv ai.install-skills` sets up `~`'s `.agents/skills/` and its `.claude/skills` symlink, and
installs every skill declared in `setup.toml` (never overwriting existing content). A new Python
project's own `AGENTS.md`/`CLAUDE.md`/`.agents/skills` scaffold comes from
[`scaffoldapy`](https://github.com/TheodoreAD/scaffoldapy) at generation time, not from a task run
afterwards. The convention these implement is in "Agent instructions & knowledge" below.

**Every skill on this machine is authored in `agent-skills`** — published as
`TheodoreAD/agent-skills`, checked out alongside the other personal repos — not in
`power-user-linux-setup`, which only installs them. To change one, edit it there and follow the
`skill-authoring` skill's sequence; the step that gets skipped is the push, because the installer
clones from the remote, so a committed but unpushed edit reaches nothing. Never edit the copy under
`~/.agents/skills/` — the next install overwrites it and it never leaves this machine.

### Which sessions load this file

Built-in `Plan`/`Explore` subagents never load it — Claude Code deliberately skips
`CLAUDE.md`/`AGENTS.md` (every level) for those agent types. Every rule in this file reaches only
the main session and custom subagents whose definitions don't override the system prompt; when a
rule matters for a `Plan`/`Explore` task, restate it in that subagent's own prompt. The Bash rules
always matter there (measured: subagents had the worst `sed -n`/`cd` rates of any session), so paste
this into every `Plan`/`Explore`/`claude-code-guide` prompt: "Use Read/Grep/Glob for files, never
`cat`/`sed -n`/`grep` via Bash. One Bash command per call, no `&&`/`;` chains, no `cd` — cwd is
already the repo. Never pipe output through `| head`/`| tail`."

### Writing conventions into a shareable skill or template

Apply them to one real, already-working repo first — never straight from research to the shareable
artifact. A pilot surfaces what research can't: rules that are noise against a repo's deliberate
style, and config footguns that would ship to every consumer verbatim.

### Proposing an enforcement mechanism for agent behavior

Skills and instructions are the mainstay of directing agents — to correct a recurring agent
behavior, prefer teaching the agent what to run over a mechanism that fires behind its back (a git
hook, a harness hook, a CI auto-fix bot). Agents get the same standard as developers: they should
know what to run, not be silently corrected.
