import shlex
from pathlib import Path

from invoke import Context, task

from . import util


def _nvm_sh(nvm_dir: Path) -> str:
    """Source nvm **and select its default version**.

    Sourcing alone only defines the shell function; the active node stays whatever is already on
    `PATH`. That is not neutral inside `inv`: the process inherits its PATH from the shell that
    launched it, and Claude Code replays a shell snapshot captured once per session — so a task can
    run every `npm` call against a node version installed months ago while `nvm alias default`
    points somewhere else entirely.

    Confirmed 2026-09-07, and it had already caused a silent split: `inv node.install` installed
    v24.20.0 and made it the default, then ran `npm list -g skills` under the **inherited** v24.16.0,
    found it, and printed "already installed globally". The new default was left with no global
    packages at all, so the next login shell — which does select the default — would have had no
    `skills` binary, and `inv ai.install-skills` would have reported the CLI missing on a machine
    that had just installed it.

    `|| true` because a machine with no `default` alias yet (the first install, before
    `nvm alias default` runs) must still get a usable shell rather than a failed `&&` chain.
    """
    return (
        f'export NVM_DIR="{nvm_dir}" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"'
        " && { nvm use --silent default > /dev/null 2>&1 || true; }"
    )


def _node_cfg() -> tuple[util.PackageConfig, Path, str]:
    cfg = util.load_config()["packages"]["node"]
    nvm_dir = Path(cfg.get("nvm_dir", "~/.local/share/nvm")).expanduser()
    return cfg, nvm_dir, _nvm_sh(nvm_dir)


def nvm_command(command: str) -> str | None:
    """Wrap `command` so it runs with nvm's node/npm on PATH, or None if nvm isn't installed.

    A globally-installed npm package lives under a version-specific nvm path that only exists on
    PATH after `nvm.sh` has been sourced — which a login shell does via Oh My Zsh's nvm plugin, and
    a task run from `inv` never does. So a bare `skills`/`npx` call works for a human and fails
    with exit 127 inside a `RUN` layer or an `inv setup`; see [packages.node]'s verify_cmd, which
    hits the same gap.
    """
    _cfg, nvm_dir, nvm_sh = _node_cfg()
    if not nvm_dir.exists():
        return None
    return f"bash -c {shlex.quote(f'{nvm_sh} && {command}')}"


@task
def install(c: Context):
    """Install nvm, Node.js, and global npm packages from config."""
    cfg, nvm_dir, nvm_sh = _node_cfg()
    version = cfg.get("version", "lts")
    global_packages = cfg.get("global_packages", [])

    if util.DRY_RUN:
        print(f"[nvm] {util.ok_label(nvm_dir.exists())}")
        if nvm_dir.exists():
            for pkg in global_packages:
                result = c.run(
                    f"bash -c '{nvm_sh} && npm list -g {pkg} --depth=0'",
                    hide=True,
                    warn=True,
                )
                print(f"[{pkg}] {util.ok_label(result.ok)}")
        else:
            for pkg in global_packages:
                print(f"[{pkg}] MISSING  (nvm not installed)")
        return

    if not nvm_dir.exists():
        nvm_dir.mkdir(parents=True, exist_ok=True)
        c.run(
            "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/HEAD/install.sh | bash",
            env={"NVM_DIR": str(nvm_dir), "PROFILE": "/dev/null"},
        )
    else:
        print("[nvm] already installed")

    c.run(f"bash -c '{nvm_sh} && nvm install --{version} && nvm alias default {version}/*'")

    for pkg in global_packages:
        result = c.run(f"bash -c '{nvm_sh} && npm list -g {pkg} --depth=0'", hide=True, warn=True)
        if result.ok:
            print(f"[{pkg}] already installed globally")
        else:
            c.run(f"bash -c '{nvm_sh} && npm install -g {pkg}'")
            print(f"[{pkg}] installed")


@task(name="update-globals")
def update_globals(c: Context):
    """Update every `global_packages` entry in `[packages.node]` to its latest release.

    `node.install` only ever *adds* a missing global package — by design, since an install task
    that silently upgraded tooling on every `inv setup` would be a surprise. So updating is its own
    deliberate command, the same shape as `inv deploy.all` versus `inv deploy.status`.

    Installs `<pkg>@latest` per declared package rather than running `npm update -g`, for two
    reasons found in npm's own documentation (`docs/lib/content/commands/npm-update.md`):

    - `npm update -g` acts on **every** globally installed package, including ones this repo never
      declared and does not own. Declaring what is managed and then updating exactly that is the
      same contract `deploy.py` keeps for files.
    - Its semantics have a trap: globals have no semver range, so their `wanted` is `latest`, and
      npm states plainly that "if a package has been upgraded to a version newer than `latest`, it
      will be _downgraded_". Anyone holding a prerelease deliberately would lose it silently.
    """
    _cfg, nvm_dir, nvm_sh = _node_cfg()
    cfg = _cfg
    global_packages = cfg.get("global_packages", [])

    if not nvm_dir.exists():
        print("[node.update-globals] nvm not installed — nothing to do")
        return
    if not global_packages:
        print("[node.update-globals] no global_packages declared — nothing to do")
        return

    for pkg in global_packages:
        if util.DRY_RUN:
            print(f"[{pkg}] would run: npm install -g {pkg}@latest")
            continue
        before = c.run(f"bash -c '{nvm_sh} && npm list -g {pkg} --depth=0'", hide=True, warn=True)
        c.run(f"bash -c '{nvm_sh} && npm install -g {shlex.quote(pkg)}@latest'")
        after = c.run(f"bash -c '{nvm_sh} && npm list -g {pkg} --depth=0'", hide=True, warn=True)
        # Report the version rather than "updated": on a machine already current this task should
        # look like a no-op, and a line saying "updated" when nothing moved is how a report stops
        # being read.
        print(f"[{pkg}] {'unchanged' if before.stdout == after.stdout else 'updated'}")


@task
def clean_cache(c: Context):
    """Garbage-collect npm's package cache (~/.npm), removing invalid/unneeded entries while
    verifying the rest — conservative, npm's own recommended way to reclaim cache space. Opt-in,
    not part of `inv setup`/`node.install` — see `inv clean.caches`. For a full wipe instead,
    see `node.clean-cache-full`.
    """
    _cfg, nvm_dir, nvm_sh = _node_cfg()
    if not nvm_dir.exists():
        print("[node.clean-cache] nvm not installed — nothing to do")
        return
    if util.DRY_RUN:
        print("[node.clean-cache] would run: npm cache verify")
        return
    c.run(f"bash -c '{nvm_sh} && npm cache verify'")
    print("[node.clean-cache] npm cache verified, invalid/unneeded entries removed")


@task
def clean_cache_full(c: Context):
    """Wipe npm's entire package cache (~/.npm). Safe any time — npm re-downloads as needed;
    only affects install speed, not what's installed. Opt-in, not part of `inv setup`/
    `node.install` — see `inv clean.all-full`.
    """
    _cfg, nvm_dir, nvm_sh = _node_cfg()
    if not nvm_dir.exists():
        print("[node.clean-cache-full] nvm not installed — nothing to do")
        return
    if util.DRY_RUN:
        print("[node.clean-cache-full] would run: npm cache clean --force")
        return
    c.run(f"bash -c '{nvm_sh} && npm cache clean --force'")
    print("[node.clean-cache-full] npm cache cleared")
