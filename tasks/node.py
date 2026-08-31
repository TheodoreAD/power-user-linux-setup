import shlex
from pathlib import Path

from invoke import Context, task

from . import util


def _nvm_sh(nvm_dir: Path) -> str:
    return f'export NVM_DIR="{nvm_dir}" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"'


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
