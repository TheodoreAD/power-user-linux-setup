from invoke import task

from . import util


@task
def tools(c):
    """Install global Python CLI tools via uv tool install."""
    if not util.command_exists("uv"):
        raise RuntimeError("uv not found — run ./bootstrap.sh first")

    default_python = util.load_config().get("settings", {}).get("uv_python_default", "")

    for name, cfg in util.packages_by_method("uv-tool").items():
        package = cfg["package"]
        if util.DRY_RUN:
            ok = util.command_exists(cfg.get("check_cmd", name))
            print(f"[{name}] {'ok' if ok else 'MISSING'}  ({package})")
            continue
        python = cfg.get("python", default_python)
        extras = cfg.get("extras", [])
        flags = f" --python {python}" if python else ""
        flags += "".join(f" --with {e}" for e in extras)
        print(f"[{name}] installing: {package}{' + ' + ', '.join(extras) if extras else ''}")
        c.run(f"uv tool install --upgrade{flags} {package}")
        print(f"[{name}] ok")
