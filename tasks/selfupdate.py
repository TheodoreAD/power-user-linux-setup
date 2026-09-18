"""`inv self.update` / `spowse self.update` — update the checkout PULSE reads itself out of.

Published as the `self` collection rather than under this module's own name, the same way
`repo_tasks`' `testing` is published as `test` (see `tasks/__init__.py`). The file is not called
`self.py`: `from . import self` imports and resolves perfectly well — `self` is a convention rather
than a keyword — but it puts a name every Python reader parses as a parameter into that module's
import list, for no gain.

**Why the task exists at all.** `spowse` is installed `uv tool install --editable` against a
checkout and reads `setup.toml` and `config/` out of it on every run, so that directory is permanent
user-wide state rather than a development artifact — and until this existed, the only way to update
it was to know its path and `git pull` there by hand. `docs/updating.md` said exactly that. A
consumer who installed through `install.sh` has no reason to know where their checkout is, which is
what makes the path a poor thing to require.

**`git -C` is correct here and is not the banned shape.** `~/.agents/AGENTS.md` bans aiming a
directory-scoping option at the repo the session is already standing in. This task is the opposite
case by construction: run as `spowse self.update` the process is standing in some unrelated
directory, and the checkout is genuinely elsewhere.
"""

from pathlib import Path

from invoke import Context, task

# `setup` is imported as a *module*, deliberately, and `setup.setup(c)` is how the task is reached.
# `from .setup import setup` would bind a Task object at this module's top level, and
# `Collection.from_module` cannot tell an imported Task from a defined one — so it would publish a
# second `self.setup` alongside the real top-level `inv setup`. That trap has produced four
# undeclared tasks in this repo family already.
from . import setup, ui, util

_REPO_ROOT = Path(__file__).resolve().parent.parent

# A pulled change to either of these is not picked up by the editable install. The `.pth` in the
# tool venv makes new *code* live immediately; the venv's resolved dependency set was fixed when
# `uv tool install` ran, so a newly declared dependency is simply absent until it runs again.
_REINSTALL_TRIGGERS = ("pyproject.toml", "uv.lock")


def _git(c: Context, args: str) -> str:
    """Read a value out of the checkout. Empty string when the command failed, which every caller
    here treats as "this repository cannot answer that" rather than as an error."""
    result = c.run(f"git -C {_REPO_ROOT} {args}", hide=True, warn=True)
    return result.stdout.strip() if result and result.ok else ""


def _blocking_local_state(c: Context) -> str | None:
    """Why this checkout must not be pulled, or None if it is safe to.

    Both cases are invisible to the reader this task is for — a consumer's checkout is never dirty
    and never ahead — and both are real on a machine where PULSE is developed. Parallel agent
    sessions here share one working tree, so a pull can move a tree another session is mid-edit in;
    and a developer's own checkout may carry commits a pull would merge over.
    """
    if _git(c, "status --porcelain"):
        return "it has uncommitted changes"
    # A detached HEAD has no upstream, which is exactly what `install.sh` produces: it clones
    # `--branch stable`, so HEAD sits on a tag. Nothing can be "ahead" of an upstream that does not
    # exist, so the absence of one is an answer rather than a failure to work around.
    if not _git(c, "rev-parse --abbrev-ref --symbolic-full-name @{u}"):
        return None
    if _git(c, "rev-list --count @{u}..HEAD") not in ("", "0"):
        return "it has commits your upstream does not"
    return None


def _apply_or_explain(c: Context, setup_after: str) -> None:
    """Run `inv setup`, offer it, or say how to run it later — pulling alone changes no machine.

    Split out of `update` rather than inlined: it is the one part of this task that can change the
    machine, and it is four branches of "may I", which reads better with a name on it than as a tail.
    """
    if setup_after == "no":
        print("[self.update] pulled only (--setup-after=no). Run 'inv setup' to apply it.")
        return
    if setup_after == "yes" or util.ASSUME_YES:
        setup.setup(c)
        return
    if not util.interactive():
        print("[self.update] pulled. Run 'inv setup' to apply it to this machine.")
        return
    ui.block(
        "Next is 'inv setup', which applies what was just pulled: apt packages, your login",
        "shell, dotfiles in your home directory and GNOME settings. It asks for sudo.",
        label="apply",
    )
    if ui.ask("Run it now?", default=True):
        setup.setup(c)
    else:
        print("[self.update] stopped. Run 'inv setup' when you want to apply it.")


@task
def update(c: Context, setup_after: str = "ask"):
    """Pull the power-user-linux-setup checkout this command reads, and report what moved.

    `spowse` resolves that checkout on every run rather than carrying a copy, so this is how a
    machine picks up a new package or a changed dotfile without anyone having to remember where the
    directory is. It only ever fast-forwards, and it refuses outright on a checkout that has
    uncommitted changes or commits its upstream does not — neither is something to resolve on
    somebody's behalf.

    Pulling changes nothing about the machine by itself. Applying what was pulled is `inv setup`,
    which installs apt packages, changes the login shell and writes GNOME settings — so it is asked
    about rather than assumed, the same way `install.sh` asks before the same command.

    Args:
        setup_after: "ask" (default) — offer to run `inv setup` once the pull brought something
          new, declining by default anywhere that cannot prompt (piped, scripted, CI, dry run).
          "yes" runs it without asking; "no" pulls and stops.
    """
    if setup_after not in ("ask", "yes", "no"):
        raise SystemExit(f"[self.update] --setup-after must be ask, yes or no (got {setup_after!r})")

    if not (_REPO_ROOT / ".git").is_dir():
        raise SystemExit(
            f"[self.update] {_REPO_ROOT} is not a git checkout, so there is nothing to pull.\n"
            "  PULSE updates by pulling the repository it was installed from. If this is an\n"
            "  unpacked archive rather than a clone, re-install it with install.sh."
        )

    blocked = _blocking_local_state(c)
    if blocked:
        ui.warn(
            f"Not pulling {_REPO_ROOT}: {blocked}.",
            "This is your checkout to resolve — commit, stash or push, then run this again.",
        )
        return

    before = _git(c, "rev-parse HEAD")

    if util.DRY_RUN:
        print(f"[self.update] would fast-forward {_REPO_ROOT} (currently {before[:12]})")
        return

    # --ff-only rather than a plain pull: the checks above guarantee there is nothing local to
    # merge, so anything git cannot fast-forward means the *remote* moved somewhere this history
    # does not lead — `stable` pointed backwards, or rewritten. That is a decision, not a conflict
    # to resolve automatically, so it stops and names the recovery.
    if not c.run(f"git -C {_REPO_ROOT} pull --ff-only", warn=True).ok:
        raise SystemExit(
            f"[self.update] {_REPO_ROOT} could not be fast-forwarded — see the error above.\n"
            "  The published ref has moved somewhere this checkout's history does not lead.\n"
            "  Nothing has been changed. To take the published state as it now stands:\n"
            f"    git -C {_REPO_ROOT} fetch origin --tags --force\n"
            f"    git -C {_REPO_ROOT} status    # then check out the ref it reports following"
        )

    after = _git(c, "rev-parse HEAD")
    if after == before:
        print(f"[self.update] already up to date ({before[:12]})")
        return

    changed = [line for line in _git(c, f"diff --name-only {before} {after}").splitlines() if line]
    print(f"[self.update] {before[:12]} -> {after[:12]}, {len(changed)} file(s) changed")

    if any(path in _REINSTALL_TRIGGERS for path in changed):
        ui.note(
            "This pull changed " + " or ".join(_REINSTALL_TRIGGERS) + ".",
            "New code is live already — the editable install resolves it on every run — but a newly",
            "declared dependency is not, because the tool's own environment was resolved when it was",
            "installed. Run 'inv python.install-tools' to rebuild it.",
        )

    _apply_or_explain(c, setup_after)
