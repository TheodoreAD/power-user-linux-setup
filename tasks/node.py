from pathlib import Path

from invoke import task

from . import util


def _nvm_sh(nvm_dir: Path) -> str:
    return f'export NVM_DIR="{nvm_dir}" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"'


@task
def install(c):
    """Install nvm, Node.js, and global npm packages from config."""
    cfg = util.load_config()["packages"]["node"]
    version = cfg.get("version", "lts")
    global_packages = cfg.get("global_packages", [])
    nvm_dir = Path(cfg.get("nvm_dir", "~/.local/share/nvm")).expanduser()
    nvm_sh = _nvm_sh(nvm_dir)

    if util.DRY_RUN:
        print(f"[nvm] {'ok' if nvm_dir.exists() else 'MISSING'}")
        if nvm_dir.exists():
            for pkg in global_packages:
                result = c.run(
                    f"bash -c '{nvm_sh} && npm list -g {pkg} --depth=0'",
                    hide=True,
                    warn=True,
                )
                print(f"[{pkg}] {'ok' if result.ok else 'MISSING'}")
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
def clean_cache(c):
    """Garbage-collect npm's package cache (~/.npm), removing invalid/unneeded entries while
    verifying the rest — conservative, npm's own recommended way to reclaim cache space. Opt-in,
    not part of `inv setup`/`node.install` — see `inv cleanup.caches`. For a full wipe instead,
    see `node.clean-cache-full`.
    """
    cfg = util.load_config()["packages"]["node"]
    nvm_dir = Path(cfg.get("nvm_dir", "~/.local/share/nvm")).expanduser()
    if not nvm_dir.exists():
        print("[node.clean-cache] nvm not installed — nothing to do")
        return
    if util.DRY_RUN:
        print("[node.clean-cache] would run: npm cache verify")
        return
    c.run(f"bash -c '{_nvm_sh(nvm_dir)} && npm cache verify'")
    print("[node.clean-cache] npm cache verified, invalid/unneeded entries removed")


@task
def clean_cache_full(c):
    """Wipe npm's entire package cache (~/.npm). Safe any time — npm re-downloads as needed;
    only affects install speed, not what's installed. Opt-in, not part of `inv setup`/
    `node.install` — see `inv cleanup.all-full`.
    """
    cfg = util.load_config()["packages"]["node"]
    nvm_dir = Path(cfg.get("nvm_dir", "~/.local/share/nvm")).expanduser()
    if not nvm_dir.exists():
        print("[node.clean-cache-full] nvm not installed — nothing to do")
        return
    if util.DRY_RUN:
        print("[node.clean-cache-full] would run: npm cache clean --force")
        return
    c.run(f"bash -c '{_nvm_sh(nvm_dir)} && npm cache clean --force'")
    print("[node.clean-cache-full] npm cache cleared")
