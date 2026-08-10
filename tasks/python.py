import re
from pathlib import Path

from invoke import task

from . import util

_SETUP_TOML = Path(__file__).parent.parent / "setup.toml"
_DEFAULT_RE = re.compile(r'(?m)^(\s*uv_python_default\s*=\s*)"[^"]*"')
_EXTRA_RE   = re.compile(r'(?m)^(\s*uv_python_extra\s*=\s*)\[[^\]]*\]')
_UV_ENV_RE  = re.compile(r'(UV_PYTHON=")[^"]*(")')


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


@task(help={"version": "Python version to make the new default, e.g. 3.14"})
def set_default(c, version):
    """Change settings.uv_python_default in setup.toml and re-point the live python/python3
    shims at it (uv python install <version> --default, unless uv_python_set_default is false).

    Swaps the old default into uv_python_extra (so it stays installed) and keeps
    [packages.uv-env]'s UV_PYTHON zshenv value in sync — both previously had to be edited by
    hand alongside uv_python_default. Run `inv zsh.configure` afterward and open a new terminal
    to pick up the new UV_PYTHON shell default.
    """
    if not re.fullmatch(r"\d+\.\d+", version):
        raise ValueError(f"version must look like '3.14', got {version!r}")
    if not util.command_exists("uv"):
        raise RuntimeError("uv not found — run ./bootstrap.sh first")

    settings = util.load_config().get("settings", {})
    old_default = settings.get("uv_python_default")
    if version == old_default:
        print(f"[python] uv_python_default already {version} — nothing to do")
        return

    extras = [v for v in settings.get("uv_python_extra", []) if v != version]
    if old_default and old_default not in extras:
        extras.append(old_default)
    extras_literal = "[" + ", ".join(f'"{v}"' for v in extras) + "]"

    if util.DRY_RUN:
        print(f"[python] would set uv_python_default: {old_default} -> {version}")
        print(f"[python] would set uv_python_extra: {extras_literal}")
        return

    text = _SETUP_TOML.read_text()
    if not _DEFAULT_RE.search(text):
        raise RuntimeError("uv_python_default not found in setup.toml")
    text = _DEFAULT_RE.sub(rf'\1"{version}"', text, count=1)
    text = _EXTRA_RE.sub(rf'\g<1>{extras_literal}', text, count=1)
    text = _UV_ENV_RE.sub(rf'\g<1>{version}\g<2>', text, count=1)
    _SETUP_TOML.write_text(text)
    print(f"[python] setup.toml: uv_python_default = \"{version}\", uv_python_extra = {extras_literal}")

    c.run(f"uv python install {version}")
    if settings.get("uv_python_set_default", True):
        c.run(f"uv python install {version} --default")
        print(f"[python] python / python3 now point at {version}")
    else:
        print("[python] uv_python_set_default is false — python/python3 left system-owned")
    print("[python] next: inv zsh.configure, then open a new terminal to pick up UV_PYTHON")
