from pathlib import Path

from invoke import task

from . import ui, util


def _ensure_agents_skills(base: Path, *, label: str) -> None:
    """Ensure <base>/.agents/skills exists and <base>/.claude/skills is a symlink to it.

    .agents/skills is the emerging cross-tool convention for agent skills; Claude Code itself
    doesn't read it natively yet, only .claude/skills, so the symlink is what actually makes
    skills placed there visible to Claude Code today. Never touches an existing .claude/skills
    that isn't already that exact symlink — real content there is left alone, not overwritten.
    """
    agents_skills = base / ".agents" / "skills"
    claude_skills = base / ".claude" / "skills"

    already_linked = claude_skills.is_symlink() and claude_skills.resolve() == agents_skills.resolve()
    if util.DRY_RUN:
        print(f"[{label}] {'ok' if already_linked and agents_skills.is_dir() else 'MISSING'}")
        return

    agents_skills.mkdir(parents=True, exist_ok=True)

    if already_linked:
        print(f"[{label}] .claude/skills already linked to .agents/skills")
        return

    if claude_skills.exists() or claude_skills.is_symlink():
        ui.warn(
            f"{claude_skills} already exists and isn't a symlink to {agents_skills}.",
            "Leaving it alone — move its contents into .agents/skills yourself, then re-run, to "
            "get both a working Claude Code setup and the cross-tool convention.",
        )
        return

    claude_skills.parent.mkdir(parents=True, exist_ok=True)
    claude_skills.symlink_to(agents_skills)
    print(f"[{label}] created .agents/skills, symlinked .claude/skills to it")


_AGENTS_MD_TEMPLATE = """\
# Agent instructions for {name}

Cross-tool instructions for AI coding agents working in this repo. Universal conventions (sudo/ssh
askpass, Bash/allowlist discipline, cross-session memory policy) live in `~/AGENTS.md` — no need
to repeat them here, only what's specific to this repo.

## Build & test

<!-- e.g. `npm test`, `make build` -->

## Conventions

<!-- code style, architecture notes, anything an agent should know before making changes -->
"""


@task
def skills(c, dir=None):
    """Ensure .agents/skills exists with .claude/skills symlinked to it.

    Defaults to the home directory (the personal, cross-project skills location). Pass --dir to
    set this up for a specific project instead.
    """
    base = Path(dir).expanduser().resolve() if dir else Path.home()
    _ensure_agents_skills(base, label="ai.skills")


@task
def init(c, dir="."):
    """Scaffold a project for AI agents: minimal AGENTS.md, CLAUDE.md as a symlink to it, and
    .agents/skills/ (symlinked from .claude/skills). Never overwrites a file that already exists —
    safe to re-run.
    """
    base = Path(dir).expanduser().resolve()
    _ensure_agents_skills(base, label="ai.init")

    agents_md = base / "AGENTS.md"
    if agents_md.exists():
        print("[ai.init] AGENTS.md already exists — left alone")
    else:
        agents_md.write_text(_AGENTS_MD_TEMPLATE.format(name=base.name))
        print("[ai.init] AGENTS.md created")

    claude_md = base / "CLAUDE.md"
    claude_md_alt = base / ".claude" / "CLAUDE.md"
    # A real symlink, not a file containing the `@AGENTS.md` import directive: the import syntax
    # is Claude-Code-specific, so any other harness that also happens to read a literal CLAUDE.md
    # (for compat) would see that text verbatim instead of actual instructions. A symlink presents
    # byte-identical content to every harness, Claude Code included, with no special-case parsing
    # required anywhere. Trade-off: unlike the import form, nothing can be appended below a
    # symlink's target — a Claude-specific addendum, if one's ever truly needed, belongs in
    # AGENTS.md itself (shared) rather than CLAUDE.md, or in a separate `.claude/`-scoped file.
    if claude_md.is_symlink() and claude_md.resolve() == agents_md.resolve():
        print("[ai.init] CLAUDE.md already symlinked to AGENTS.md")
    elif claude_md.exists() or claude_md.is_symlink() or claude_md_alt.exists():
        print("[ai.init] CLAUDE.md already exists — left alone")
    else:
        claude_md.symlink_to("AGENTS.md")
        print("[ai.init] CLAUDE.md created (symlink to AGENTS.md)")
