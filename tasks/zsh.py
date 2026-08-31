import pwd
import re
import shutil
from pathlib import Path

from invoke import Context, task

from . import deploy, util


def _snippets(cfg: util.PackageConfig) -> list[tuple[str, str]]:
    """The (dotfile name, snippet) pairs a package declares — one per zshrc/zshenv/zprofile field
    it actually sets. Spelled out per field rather than `cfg.get(target)` in a loop over the
    names: a TypedDict lookup only keeps its field type for a literal key."""
    declared = (("zshrc", cfg.get("zshrc")), ("zshenv", cfg.get("zshenv")), ("zprofile", cfg.get("zprofile")))
    return [(target, content) for target, content in declared if content]


def _current_shell() -> str:
    return pwd.getpwnam(util.current_user()).pw_shell


def _shell_is_zsh(shell_path: str) -> bool:
    # Name-based, not exact-path: machines can have more than one zsh on disk (e.g. an apt one
    # at /usr/bin/zsh and another earlier on PATH) — what matters is that the registered login
    # shell is *a* zsh, not that it's byte-for-byte the one `shutil.which` happens to find.
    return Path(shell_path).name == "zsh"


@task
def configure_omz(c: Context):  # noqa: C901
    """Update Oh My Zsh theme and plugins list in ~/.zshrc in-place."""
    all_cfg = util.load_config()["packages"]
    cfg = all_cfg.get("oh-my-zsh", {})
    zshrc = Path.home() / ".zshrc"
    if not zshrc.exists():
        print("[oh-my-zsh] ~/.zshrc not found — skipping")
        return

    text = zshrc.read_text()
    theme = cfg.get("theme", "powerlevel10k/powerlevel10k")

    if util.DRY_RUN:
        m = re.search(r"^ZSH_THEME=(.*)$", text, flags=re.MULTILINE)
        current_theme = m.group(1).strip('"') if m else None
        theme_ok = current_theme == theme
        plugins_present = bool(re.search(r"^plugins=\(", text, flags=re.MULTILINE))
        print(f"[oh-my-zsh] theme: {'ok' if theme_ok else f'MISSING  (current: {current_theme!r})'}")
        print(f"[oh-my-zsh] plugins block: {util.ok_label(plugins_present)}")
        return

    changed = False
    new_text = re.sub(r"^ZSH_THEME=.*$", f'ZSH_THEME="{theme}"', text, flags=re.MULTILINE)
    if new_text != text:
        text = new_text
        changed = True
        print(f"[oh-my-zsh] theme → {theme}")

    base = cfg.get("plugins", [])
    if base:
        tail = "zsh-syntax-highlighting"
        ordered = [p for p in base if p != tail]
        for pkg_cfg in all_cfg.values():
            if not pkg_cfg.get("enabled", True):
                continue
            extra = pkg_cfg.get("omz_plugin", [])
            if isinstance(extra, str):
                extra = [extra]
            for p in extra:
                if p not in ordered and p != tail:
                    ordered.append(p)
        if tail in base:
            ordered.append(tail)

        plugins_body = "\n".join(f"    {p}" for p in ordered)
        new_plugins = f"plugins=(\n{plugins_body}\n)"
        new_text = re.sub(r"^plugins=\(.*?\)", new_plugins, text, flags=re.DOTALL | re.MULTILINE)
        if new_text != text:
            text = new_text
            changed = True
            print("[oh-my-zsh] plugins updated")

    if changed:
        zshrc.write_text(text)
    else:
        print("[oh-my-zsh] already configured — nothing to do")


@task
def configure(c: Context):
    """Add or update zsh configuration blocks declared in setup.toml."""
    if util.DRY_RUN:
        for name, cfg in util.load_config()["packages"].items():
            if not cfg.get("enabled", True):
                continue
            for target, content in _snippets(cfg):
                path = Path.home() / f".{target}"
                text = path.read_text() if path.exists() else ""
                _, status = util.ensure_block_text(text, name, content)
                print(f"[{name}] .{target}: {util.ok_label(status == util.BlockStatus.OK)}")
        return
    for name, cfg in util.load_config()["packages"].items():
        if not cfg.get("enabled", True):
            continue
        for target, content in _snippets(cfg):
            path = Path.home() / f".{target}"
            path.parent.mkdir(parents=True, exist_ok=True)
            result = util.ensure_block(path, name, content)
            if result != util.BlockStatus.OK:
                print(f"[{name}] .{target}: {result.value}")


@task
def set_default_shell(c: Context):
    """Set zsh as the login shell (usermod -s, not chsh — chsh's PAM password prompt doesn't
    work in a non-interactive/piped session the way sudo -A does). Only takes effect in a new
    login shell/terminal, not the one this runs in.
    """
    util.ensure_sudo()  # standalone-safe: no sudo call inside c.run may prompt
    zsh_path = shutil.which("zsh")
    if not zsh_path:
        print("[zsh] zsh not found on PATH — install it first (apt.install-base)")
        return
    if util.DRY_RUN:
        print(f"[zsh] default shell: {util.ok_label(_shell_is_zsh(_current_shell()))}")
        return
    if _shell_is_zsh(_current_shell()):
        print(f"[zsh] default shell already zsh ({_current_shell()}) — nothing to do")
        return
    c.run(f"{util.SUDO} usermod -s {zsh_path} {util.current_user()}")
    print(f"[zsh] default shell set to {zsh_path} — close this terminal and open a new one for it to take effect")


@task
def fix_history(c: Context):
    """Recover a corrupt ~/.zsh_history using strings(1) to strip non-printable bytes."""
    hist = Path.home() / ".zsh_history"
    bad = Path.home() / ".zsh_history_bad"
    if not hist.exists():
        print("[zsh-history] ~/.zsh_history not found — nothing to fix")
        return
    if util.DRY_RUN:
        print(f"[zsh-history] would recover {hist} via strings → {bad} → {hist}")
        return
    hist.rename(bad)
    c.run(f"strings {bad} > {hist}")
    c.run(f"fc -R {hist}", warn=True)
    bad.unlink()
    print("[zsh-history] recovered — corrupt backup removed")


@task
def configure_p10k(c: Context):
    """Seed ~/.p10k.zsh from the repo baseline, through tasks/deploy.py's writer.

    The prompt config is yours once it exists — p10k's own `p10k configure` wizard rewrites it — so
    it is declared as `config_files` on [packages.powerlevel10k] and carries the SEEDED policy: an
    absent destination is created, a customized one is left alone and said so. This used to be a
    bare `write_bytes` with a skip-if-exists guard, which meant the file had no manifest entry, no
    diff, and no redeploy path at all when the repo baseline changed. `inv deploy.all --name
    powerlevel10k --yes` is now the deliberate overwrite.
    """
    cfg = util.load_config()["packages"]["powerlevel10k"]
    deploy.apply_config_files("powerlevel10k", cfg)
