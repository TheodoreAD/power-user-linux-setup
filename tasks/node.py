from pathlib import Path

from invoke import task

from . import util


@task
def install(c):
    """Install nvm, Node.js, and global npm packages from config."""
    cfg = util.load_config()["packages"]["node"]
    version = cfg.get("version", "lts")
    global_packages = cfg.get("global_packages", [])
    nvm_dir = Path(cfg.get("nvm_dir", "~/.local/share/nvm")).expanduser()
    nvm_sh = f'export NVM_DIR="{nvm_dir}" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"'

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
