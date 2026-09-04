import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import NamedTuple

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
    if "dest" not in cfg:
        raise util.missing_fields(name, "dest")
    dest = Path(cfg["dest"]).expanduser()
    # `assembled_from` composes the destination from every fragment declared under the named
    # any-section field instead of copying one `content_file` — see deploy.assemble(). Built here
    # from the cfg passed in rather than looked up in deploy's registry: this installer is called
    # with one section's config, and reaching back into the global one would make it depend on
    # state its caller never supplied.
    if field := cfg.get("assembled_from"):
        managed = deploy.assembled_entry(name, dest, field)
    elif content_file := cfg.get("content_file"):
        managed = deploy.Managed(
            path=dest,
            package=name,
            source=content_file,
            mechanism=deploy.Mechanism.WRAPPER_SCRIPT,
        )
    else:
        raise util.missing_fields(name, "content_file (or assembled_from)")
    links = symlink_dests(cfg)

    if util.DRY_RUN:
        # Links whose parent directory is absent are skipped, exactly as `_ensure_symlink` and
        # `verify._symlink_checks` skip them: a missing `~/.codex/` means that agent isn't
        # installed, which is a correct state and not a failure. Without this the dry run reported
        # `agents-md` MISSING on a machine where `deploy.status` said `ok` and the deployed file was
        # genuinely right — a false alarm on a healthy machine, which is how a report teaches people
        # to ignore it.
        ok = deploy.classify(managed) == deploy.State.CLEAN and all(
            _link_ok(link.path, dest) for link in links if link.always or link.path.parent.is_dir()
        )
        print(f"[{name}] {util.ok_label(ok)}")
        return

    deploy.deploy(managed)
    for link in links:
        _ensure_symlink(name, link, dest)


class SymlinkDest(NamedTuple):
    """One declared link, and whether a missing parent directory means "skip" or "create"."""

    path: Path
    always: bool


def symlink_dests(cfg: util.PackageConfig) -> list[SymlinkDest]:
    """`symlink_dest`, as absolute paths each carrying its parent-directory rule.

    Accepts a bare string as well as a list: one destination is still the common case (a single
    wrapper script aliased under another name), and a list is what a file several agents each read
    from their own path needs — the instructions file is linked into every installed agent's own
    instruction path. Same string-or-list shape as `omz_plugin`.

    A **string** is a vendor path and is conditional: an absent `~/.codex/` means Codex isn't
    installed, so the link is skipped rather than created (see `_ensure_symlink`). A
    **`{ path = ..., always = true }`** table opts out of that test, for a destination no vendor
    owns. Those two cases need distinguishing rather than leaving it to whether the parent happens
    to exist: `~/AGENTS.md`'s parent is the home directory, so the conditional test passes
    vacuously and would create the link for the right reason by accident, recording nothing about
    why. Verified 2026-09-04, four agents read the cross-tool `~/.agents/AGENTS.md` and none of them
    owns that directory — PULSE does.
    """
    declared = cfg.get("symlink_dest")
    if not declared:
        return []
    entries = [declared] if isinstance(declared, str) else declared
    return [_symlink_dest(e) for e in entries]


def _symlink_dest(entry: str | dict[str, str | bool]) -> SymlinkDest:
    if isinstance(entry, str):
        return SymlinkDest(Path(entry).expanduser(), always=False)
    path = entry.get("path")
    if not isinstance(path, str):
        # Covers the missing key and the wrong-typed value with one message: both mean the TOML
        # author wrote a table that declares no destination, and both would otherwise reach `Path()`
        # as a `None` or a mapping.
        raise TypeError(f"symlink_dest table needs a string `path`, got {entry!r}")
    return SymlinkDest(Path(path).expanduser(), always=bool(entry.get("always")))


def _link_ok(link: Path, dest: Path) -> bool:
    return link.is_symlink() and link.resolve() == dest.resolve()


def _ensure_symlink(name: str, dest_entry: SymlinkDest, dest: Path) -> None:
    """Point the declared link at `dest`, unless something else already lives there.

    **Never creates the parent directory of a vendor path.** A missing `~/.codex/` means Codex isn't
    installed, and creating it to hold an instruction file would leave a directory that makes an
    absent agent look present — the same detection rule the `skills` CLI uses when it picks which
    agents to install to. Says so rather than skipping silently, since "my rules didn't reach agent
    X" is otherwise a very quiet failure; installing that agent and re-running picks the link up.

    An `always` destination is the exception and does create its parent, because that test asks a
    question about a *vendor's* directory and there is no vendor to ask about — nobody owns
    `~/.agents/`, PULSE creates it, so "is it there?" would only ever be answering about this repo's
    own earlier run.
    """
    link = dest_entry.path
    if _link_ok(link, dest):
        return
    if link.exists() or link.is_symlink():
        ui.warn(
            f"{link} already exists and isn't a symlink to {dest}.",
            "Leaving it alone — move its content into the file above yourself, then re-run.",
        )
        return
    if not link.parent.is_dir():
        if not dest_entry.always:
            print(f"[{name}] {link}: skipped — {link.parent} doesn't exist (that agent isn't installed here)")
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
    # Downloaded to a file rather than piped into tar, because tar can only auto-detect an
    # archive's compression when it can seek: `curl | tar -x` fails outright on anything but the
    # gzip its old hardcoded -z assumed ("Archive is compressed. Use -J option"), while `tar -xf`
    # on the same bytes handles gzip, xz and bzip2 alike. Sniffing the URL suffix instead would
    # not work either — an upstream "latest" endpoint (telegram.org/dl/desktop/linux) carries no
    # extension at all and only reveals the format via redirect.
    with TemporaryDirectory(prefix="pulse-archive-") as tmp:
        tarball = Path(tmp) / "archive"
        c.run(f'curl -fsSL "{url}" -o {tarball}')
        if bin_pick := cfg.get("bin_pick"):
            dest = Path.home() / ".local" / "bin" / bin_pick
            dest.parent.mkdir(parents=True, exist_ok=True)
            if cfg.get("bin_in_root"):
                # Binary sits at archive root with no subdirectory
                c.run(f"tar -x -f {tarball} -C {dest.parent} {bin_pick}")
            else:
                strip = cfg.get("strip_components", 1)
                c.run(
                    f"tar -x -f {tarball} --strip-components={strip} -C {dest.parent} "
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
                c.run(f"tar -x -f {tarball} --strip-components={strip} --directory {install_dir}")
            else:
                c.run(f"tar -x -f {tarball} --directory {extract_to}")

    if symlinks := cfg.get("symlinks"):
        if "install_dir" not in cfg:
            raise util.missing_fields(name, "install_dir (symlinks are relative to it)")
        for lnk in symlinks:
            if util.ensure_symlink_path(Path(cfg["install_dir"]).expanduser() / lnk["src"], lnk["dst"]):
                print(f"[{name}] symlink: ~/.local/bin/{lnk['dst']}")

    print(f"[{name}] installed")


_INSTALLERS = (
    (util.PackageMethod.SCRIPT, _install_script),
    (util.PackageMethod.BINARY, _install_binary),
    (util.PackageMethod.ARCHIVE, _install_archive),
    (util.PackageMethod.GIT_CLONE, _install_git_clone),
    (util.PackageMethod.WRAPPER_SCRIPT, _install_wrapper_script),
)


@task
def install(c: Context):
    """Install tools that use official installer scripts, direct binary downloads, or archives.

    Each package's `config_files` are seeded right after it installs, the same as the apt and deb
    methods already did. Without this a declared config on an `archive` or `git-clone` package
    (`~/.config/wezterm/wezterm.lua`, `~/.p10k.zsh`) was never written during `inv setup` at all —
    it waited for a separate `inv deploy.all` that a fresh machine has no reason to run, while
    `inv verify.all`, at the end of this very phase, requires every declared destination to exist.
    """
    for method, installer in _INSTALLERS:
        for name, cfg in util.packages_by_method(method).items():
            installer(c, name, cfg)
            deploy.apply_config_files(name, cfg)


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
