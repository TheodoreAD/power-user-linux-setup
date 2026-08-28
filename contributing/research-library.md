# Research library machinery (`$RESEARCH_HOME`)

What this repo deploys so a research library can exist on this machine, and why each piece is shaped
the way it is. **The library's own conventions — layout, naming, provenance, when to prefer a local
clone over a web fetch — are the `research-library` skill**, published in
[`agent-skills`](https://github.com/TheodoreAD/agent-skills) and installed here via
`[packages.agent-skills]`. Its `references/rationale.md` carries the design reasoning that travels
with the convention: why the library sits outside every repo, the naming rule, the docs-site
mirroring research, and why RAG was rejected. This page is only the local mechanism, which does not
travel and is not the skill's business.

The split was made 2026-08-28, when the skill moved out. Before that both halves lived here, which
made the machinery read as part of the convention — it isn't; anyone can keep a research library
with a shell export and a loop.

## What `[packages.research-library]` deploys

| Piece                      | Field                           | Why                                                                                                              |
| -------------------------- | ------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `RESEARCH_HOME=~/research` | `zshenv`                        | Every project references `$RESEARCH_HOME/...` instead of a hardcoded path, so the location is one edit to change |
| `research-update`          | `wrapper-script`/`content_file` | Refreshes every clone under `repos/` — see `config/research-update.sh`                                           |
| `Read(//…/research/**)`    | `claude_permissions_allow`      | Curated, read-only reference material; see below                                                                 |

**Location: plain `~/research/`, not `~/.local/share/research/`.** The XDG-paths convention this
repo otherwise enforces ("user tool installs go to `~/.local/share/<tool>`") is about _tool_
installs cluttering `$HOME`. This is human-facing content opened directly — PDFs, epubs, source you
read — so it behaves more like `~/Documents` than a program's data directory.

**`research-update` does a shallow fetch and hard reset**, not a merge: these are disposable
reference clones, not working copies with local commits to preserve. The skill documents the
pinned-tag trap that makes a clone silently report "up to date" forever; the fix belongs in the
clone's fetch refspec, not in this script.

**Deliberately no symlink from inside any repo into `~/research`.** That would reintroduce ambient
exposure to repo-scoped agents, which is the entire reason the library lives outside every repo.
Access is an explicit act: a project's `AGENTS.md` names the exact path relevant to a given task.

## Why the read grant is a single `Read(...)` rule

The `claude_permissions_allow` entry grants read access across the whole library without a per-call
prompt. This is curated, read-only reference material, not arbitrary internet content, so treating
it like project files rather than gating every lookup is the point of building it at all.

One `Read` rule covers every file-reading tool (Read, Glob, Grep); `Glob(...)`/`Grep(...)` rule
types aren't matched by Claude Code's file permission checks at all — its launch-time linter flags
them. Applied declaratively by `inv ai.install-skills` (`tasks/ai.py`) through its own manifest,
deliberately separate from `tasks/allowlist.py`'s CLI-classification pipeline, which this isn't part
of. See `docs/claude-code.md`.

The rule's path is absolute and names this user's home, which is one of the two reasons the skill
could not simply be published as-is: the convention is portable, this grant is not.
