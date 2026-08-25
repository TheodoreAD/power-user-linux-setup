import shutil
from pathlib import Path

from invoke import Context, task

from . import deploy, ui, util


def _expand(value: str) -> str:
    return str(Path(value).expanduser()) if value.startswith("~") else value


def _check_tool(name: str, cfg: util.PackageConfig) -> bool:
    check_path = cfg.get("check_path")
    if check_path:
        return Path(check_path).expanduser().exists()
    return util.command_exists(cfg.get("check_cmd", name))


def _install_script(c: Context, name: str, cfg: util.PackageConfig) -> None:
    if util.DRY_RUN:
        print(f"[{name}] {util.ok_label(_check_tool(name, cfg))}")
        return
    if _check_tool(name, cfg):
        print(f"[{name}] already installed")
        return

    if "script_url" not in cfg:
        raise util.missing_fields(name, "script_url")
    env = {k: _expand(v) for k, v in cfg.get("env", {}).items()}
    shell = cfg.get("shell", "sh")
    print(f"[{name}] installing...")
    c.run(f"curl -fsSL {cfg['script_url']} | {shell}", env=env)

    if (
        not cfg.get("single_binary")
        and (src := cfg.get("symlink_from"))
        and util.ensure_symlink_path(src, cfg.get("check_cmd", name))
    ):
        print(f"[{name}] symlink created in ~/.local/bin")

    if post_install := cfg.get("post_install"):
        c.run(post_install, env=env)

    print(f"[{name}] installed")


def _install_binary(c: Context, name: str, cfg: util.PackageConfig) -> None:
    check_cmd = cfg.get("check_cmd", name)
    if util.DRY_RUN:
        print(f"[{name}] {util.ok_label(util.command_exists(check_cmd))}")
        return
    if util.command_exists(check_cmd):
        print(f"[{name}] already installed")
        return
    if "url" not in cfg:
        raise util.missing_fields(name, "url")
    dest = Path.home() / ".local" / "bin" / check_cmd
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"[{name}] installing...")
    c.run(f"curl -fsSL {cfg['url']} -o {dest}")
    c.run(f"chmod +x {dest}")
    print(f"[{name}] installed")


def _install_git_clone(c: Context, name: str, cfg: util.PackageConfig) -> None:
    if "dest" not in cfg or "repo" not in cfg:
        raise util.missing_fields(name, "dest", "repo")
    dest = Path(cfg["dest"]).expanduser()
    if util.DRY_RUN:
        print(f"[{name}] {util.ok_label(dest.exists())}")
        return
    if dest.exists():
        print(f"[{name}] already installed")
        return
    depth = cfg.get("depth")
    depth_flag = f"--depth={depth} " if depth else ""
    print(f"[{name}] installing...")
    c.run(f"git clone {depth_flag}{cfg['repo']} {dest}")
    print(f"[{name}] installed")


def _install_wrapper_script(c: Context, name: str, cfg: util.PackageConfig) -> None:
    # content_file, not an inline `content` string: the deployed file lives as a real file under
    # config/ in this repo (readable, diffable, editable with normal tooling) and setup.toml just
    # points at it, the same way [packages.p10k]/zsh.py's p10k_configure already reads
    # config/p10k.zsh rather than embedding it. The content write itself goes through
    # tasks/deploy.py — the one writer for every path under ~ — so an edit made at the destination
    # is shown as a diff and asked about, never silently overwritten (which this function used to
    # do, and which ate hand-edits to ~/AGENTS.md twice in one day). Only the symlink handling
    # stays here: creating/validating a symlink isn't a content write.
    if "dest" not in cfg or "content_file" not in cfg:
        raise util.missing_fields(name, "dest", "content_file")
    managed = deploy.Managed(
        path=Path(cfg["dest"]).expanduser(),
        package=name,
        source=cfg["content_file"],
        mechanism=deploy.Mechanism.WRAPPER_SCRIPT,
    )
    dest = managed.path
    link = Path(symlink_dest).expanduser() if (symlink_dest := cfg.get("symlink_dest")) else None
    link_ok = link is None or (link.is_symlink() and link.resolve() == dest.resolve())

    if util.DRY_RUN:
        ok = deploy.classify(managed) == deploy.State.CLEAN and link_ok
        print(f"[{name}] {util.ok_label(ok)}")
        return

    deploy.deploy(managed)

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


def _install_archive(c: Context, name: str, cfg: util.PackageConfig) -> None:  # noqa: C901
    if util.DRY_RUN:
        print(f"[{name}] {util.ok_label(_check_tool(name, cfg))}")
        return
    if _check_tool(name, cfg):
        print(f"[{name}] already installed")
        return

    if "download_url" not in cfg:
        raise util.missing_fields(name, "download_url")
    url = cfg["download_url"]
    if "{version}" in url:
        if version_cmd := cfg.get("version_cmd"):
            version = c.run(version_cmd, hide=True).stdout.strip()
        elif version_url := cfg.get("version_url"):
            version = c.run(f"curl -fsSL {version_url} | head -1", hide=True).stdout.strip()
        else:
            raise util.missing_fields(name, "version_cmd or version_url (download_url has {version})")
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
            c.run(
                f'curl -fsSL "{url}" | tar -zx --strip-components={strip} -C {dest.parent} '
                f'--wildcards --wildcards-match-slash "*/{bin_pick}"'
            )
        c.run(f"chmod +x {dest}")
    else:
        if "install_dir" not in cfg or "extract_to" not in cfg:
            raise util.missing_fields(name, "install_dir", "extract_to")
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

    if symlinks := cfg.get("symlinks"):
        if "install_dir" not in cfg:
            raise util.missing_fields(name, "install_dir (symlinks are relative to it)")
        for lnk in symlinks:
            if util.ensure_symlink_path(Path(cfg["install_dir"]).expanduser() / lnk["src"], lnk["dst"]):
                print(f"[{name}] symlink: ~/.local/bin/{lnk['dst']}")

    print(f"[{name}] installed")


@task
def install(c: Context):
    """Install tools that use official installer scripts, direct binary downloads, or archives."""
    for name, cfg in util.packages_by_method(util.PackageMethod.SCRIPT).items():
        _install_script(c, name, cfg)
    for name, cfg in util.packages_by_method(util.PackageMethod.BINARY).items():
        _install_binary(c, name, cfg)
    for name, cfg in util.packages_by_method(util.PackageMethod.ARCHIVE).items():
        _install_archive(c, name, cfg)
    for name, cfg in util.packages_by_method(util.PackageMethod.GIT_CLONE).items():
        _install_git_clone(c, name, cfg)
    for name, cfg in util.packages_by_method(util.PackageMethod.WRAPPER_SCRIPT).items():
        _install_wrapper_script(c, name, cfg)


# Matches [packages.rust]'s CARGO_HOME in setup.toml. Only the registry (downloaded crate
# sources/index) is reclaimable cache — the sibling `bin/` under the same CARGO_HOME holds the
# actual cargo/rustc/clippy/rustfmt binaries and must not be touched.
_CARGO_REGISTRY = Path.home() / ".local/share/cargo/registry"
# Compressed .crate downloads — cheap to refetch, no local rebuild cost. The rest of registry/
# (extracted `src/`, the git/sparse `index/`) is slower to reconstruct, so it's left alone by the
# conservative variant.
_CARGO_REGISTRY_CACHE = _CARGO_REGISTRY / "cache"


def _du(c: Context, path: Path) -> str:
    result = c.run(f"du -sh {path}", hide=True, warn=True)
    return result.stdout.split()[0] if result.ok and result.stdout.split() else "0"


@task
def clean_cache(c: Context):
    """Remove cargo's compressed crate-download cache (~/.local/share/cargo/registry/cache), if
    rust is installed — conservative, leaves the extracted sources and index alone (slower to
    rebuild than a plain re-download). Opt-in, not part of `inv setup`/`tools.install` — see
    `inv clean.caches`. For a full wipe of the whole registry instead, see
    `tools.clean-cache-full`.
    """
    if not _CARGO_REGISTRY_CACHE.exists():
        print("[tools.clean-cache] cargo download cache not found — nothing to do")
        return
    if util.DRY_RUN:
        print(f"[tools.clean-cache] cargo download cache: {_du(c, _CARGO_REGISTRY_CACHE)}")
        return
    shutil.rmtree(_CARGO_REGISTRY_CACHE)
    print(f"[tools.clean-cache] removed {_CARGO_REGISTRY_CACHE}")


@task
def clean_cache_full(c: Context):
    """Remove cargo's entire registry cache (~/.local/share/cargo/registry) — compressed
    downloads, extracted sources, and index — if rust is installed. Safe any time — cargo
    re-fetches and re-syncs as needed; doesn't touch the installed rustc/cargo/clippy/rustfmt
    toolchain itself. Opt-in, not part of `inv setup`/`tools.install` — see
    `inv clean.all-full`.
    """
    if not _CARGO_REGISTRY.exists():
        print("[tools.clean-cache-full] cargo registry cache not found — nothing to do")
        return
    if util.DRY_RUN:
        print(f"[tools.clean-cache-full] cargo registry cache: {_du(c, _CARGO_REGISTRY)}")
        return
    shutil.rmtree(_CARGO_REGISTRY)
    print(f"[tools.clean-cache-full] removed {_CARGO_REGISTRY}")
