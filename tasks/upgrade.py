"""`inv upgrade` — move the agent tooling PULSE installs to what upstream publishes today.

**Why it is not part of `inv setup`.** Setup reproduces the machine `setup.toml` declares, and every
installer in it adds what is missing and leaves what is present alone. An upgrade takes whatever
upstream released since, which is a change nobody reviewed — the line `~/.agents/AGENTS.md` draws
between pulling a canonical file and generating one. So it is its own command, and `inv self.update`
offers it after offering setup, which is how a machine that only ever runs `self.update` reaches it.

**What it covers, and what it deliberately does not.** The agent tooling: the `skills` CLI and the
other `[packages.node]` globals first, so the second step runs on the current CLI, then every
installed skill. `apt.upgrade-debs` stays out by decision (2026-11-25): it needs sudo, and this
command should be safe to run from anywhere with no password. See
plans/2026-11-25-agents-md-and-agents-skills-as-the-only-source.md.

Both steps were reachable before this existed and neither was ever run: `node.update-globals` was
called by nothing, which is how the `skills` CLI sat four minor versions behind from August to
November.
"""

from invoke import Context, task

# Modules, not Task objects, for the reason selfupdate.py gives: a Task bound at module level would
# be republished by any Collection.from_module of this module. This one is added as a bare task, but
# the habit costs nothing and the trap has bitten this repo family four times.
from . import ai, node

# Order is load-bearing: the CLI is upgraded before the skills it updates.
UPGRADE_STEPS = (node.update_globals, ai.update_skills)


@task
def upgrade(c: Context):
    """Upgrade the agent tooling: the `skills` CLI and other declared npm globals, then every
    installed skill. Never part of `inv setup`; `inv self.update` offers it. No sudo."""
    for step in UPGRADE_STEPS:
        step(c)
