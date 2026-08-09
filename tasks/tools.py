import shutil
from pathlib import Path

from invoke import task

from . import ui, util


def _expand(value: str) -> str:
    return str(Path(value).expanduser()) if value.startswith("~") else value


def _check_tool(name: str, cfg: dict) -> bool:
    check_path = cfg.get("check_path")
    if check_path:
        return Path(check_path).expanduser().exists()
    return util.command_exists(cfg.get("check_cmd", name))


def _install_script(c, name: str, cfg: dict) -> None:
    if util.DRY_RUN:
        print(f"[{name}] {'ok' if _check_tool(name, cfg) else 'MISSING'}")
        return
    if _check_tool(name, cfg):
        print(f"[{name}] already installed")
        return

    env = {k: _expand(v) for k, v in cfg.get("env", {}).items()}
    shell = cfg.get("shell", "sh")
    print(f"[{name}] installing...")
    c.run(f'curl -fsSL {cfg["script_url"]} | {shell}', env=env)

    if not cfg.get("single_binary") and (src := cfg.get("symlink_from")):
        if util.ensure_symlink_path(src, cfg.get("check_cmd", name)):
            print(f"[{name}] symlink created in ~/.local/bin")

    if post_install := cfg.get("post_install"):
        c.run(post_install, env=env)

    print(f"[{name}] installed")


def _install_binary(c, name: str, cfg: dict) -> None:
    check_cmd = cfg.get("check_cmd", name)
    if util.DRY_RUN:
        print(f"[{name}] {'ok' if util.command_exists(check_cmd) else 'MISSING'}")
        return
    if util.command_exists(check_cmd):
        print(f"[{name}] already installed")
        return
    dest = Path.home() / ".local" / "bin" / check_cmd
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"[{name}] installing...")
    c.run(f'curl -fsSL {cfg["url"]} -o {dest}')
    c.run(f"chmod +x {dest}")
    print(f"[{name}] installed")


def _install_git_clone(c, name: str, cfg: dict) -> None:
    dest = Path(cfg["dest"]).expanduser()
    if util.DRY_RUN:
        print(f"[{name}] {'ok' if dest.exists() else 'MISSING'}")
        return
    if dest.exists():
        print(f"[{name}] already installed")
        return
    depth = cfg.get("depth")
    depth_flag = f"--depth={depth} " if depth else ""
    print(f"[{name}] installing...")
    c.run(f'git clone {depth_flag}{cfg["repo"]} {dest}')
    print(f"[{name}] installed")


def _install_wrapper_script(c, name: str, cfg: dict) -> None:
    dest = Path(cfg["dest"]).expanduser()
    content = cfg["content"].strip() + "\n"
    link = Path(cfg["symlink_dest"]).expanduser() if cfg.get("symlink_dest") else None
    link_ok = link is None or (link.is_symlink() and link.resolve() == dest.resolve())

    if util.DRY_RUN:
        ok = dest.exists() and dest.read_text() == content and link_ok
        print(f"[{name}] {'ok' if ok else 'MISSING'}")
        return

    if dest.exists() and dest.read_text() == content:
        print(f"[{name}] content already installed")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        dest.chmod(0o755)
        print(f"[{name}] installed")

    if link is None or link_ok:
        return
    if link.exists() or link.is_symlink():
        ui.warn(
            f"{link} already exists and isn't a symlink to {dest}.",
            "Leaving it alone — move its content into the file above yourself, then re-run.",
        )
        return
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(dest)
    print(f"[{name}] symlinked {link} -> {dest}")


def _install_archive(c, name: str, cfg: dict) -> None:
    if util.DRY_RUN:
        print(f"[{name}] {'ok' if _check_tool(name, cfg) else 'MISSING'}")
        return
    if _check_tool(name, cfg):
        print(f"[{name}] already installed")
        return

    url = cfg["download_url"]
    if "{version}" in url:
        if version_cmd := cfg.get("version_cmd"):
            version = c.run(version_cmd, hide=True).stdout.strip()
        else:
            version = c.run(f'curl -fsSL {cfg["version_url"]} | head -1', hide=True).stdout.strip()
        url = url.format(version=version)

    print(f"[{name}] installing...")
    if bin_pick := cfg.get("bin_pick"):
        dest = Path.home() / ".local" / "bin" / bin_pick
        dest.parent.mkdir(parents=True, exist_ok=True)
        if cfg.get("bin_in_root"):
            # Binary sits at archive root with no subdirectory
            c.run(f'curl -fsSL "{url}" | tar -zx -C {dest.parent} {bin_pick}')
        else:
            strip = cfg.get("strip_components", 1)
            c.run(f'curl -fsSL "{url}" | tar -zx --strip-components={strip} -C {dest.parent} --wildcards --wildcards-match-slash "*/{bin_pick}"')
        c.run(f"chmod +x {dest}")
    else:
        install_dir = Path(cfg["install_dir"]).expanduser()
        if install_dir.exists():
            shutil.rmtree(install_dir)
        extract_to = Path(cfg["extract_to"]).expanduser()
        strip = cfg.get("strip_components", 0)
        if strip:
            # Strip the versioned top-level dir and extract directly into install_dir.
            install_dir.mkdir(parents=True, exist_ok=True)
            c.run(f'curl -fsSL "{url}" | tar -zx --strip-components={strip} --directory {install_dir}')
        else:
            c.run(f'curl -fsSL "{url}" | tar -zx --directory {extract_to}')

    for lnk in cfg.get("symlinks", []):
        if util.ensure_symlink_path(
            Path(cfg["install_dir"]).expanduser() / lnk["src"], lnk["dst"]
        ):
            print(f"[{name}] symlink: ~/.local/bin/{lnk['dst']}")

    print(f"[{name}] installed")


@task
def install(c):
    """Install tools that use official installer scripts, direct binary downloads, or archives."""
    for name, cfg in util.packages_by_method("script").items():
        _install_script(c, name, cfg)
    for name, cfg in util.packages_by_method("binary").items():
        _install_binary(c, name, cfg)
    for name, cfg in util.packages_by_method("archive").items():
        _install_archive(c, name, cfg)
    for name, cfg in util.packages_by_method("git-clone").items():
        _install_git_clone(c, name, cfg)
    for name, cfg in util.packages_by_method("wrapper-script").items():
        _install_wrapper_script(c, name, cfg)
