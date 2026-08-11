import pwd
import re
import shutil
from pathlib import Path

from invoke import task

from . import util

_REPO_ROOT = Path(__file__).parent.parent


def _current_shell() -> str:
    return pwd.getpwnam(util.current_user()).pw_shell


def _shell_is_zsh(shell_path: str) -> bool:
    # Name-based, not exact-path: machines can have more than one zsh on disk (e.g. an apt one
    # at /usr/bin/zsh and another earlier on PATH) — what matters is that the registered login
    # shell is *a* zsh, not that it's byte-for-byte the one `shutil.which` happens to find.
    return Path(shell_path).name == "zsh"


@task
def omz_configure(c):
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
        print(f"[oh-my-zsh] plugins block: {'ok' if plugins_present else 'MISSING'}")
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
def configure(c):
    """Add or update zsh configuration blocks declared in setup.toml."""
    if util.DRY_RUN:
        for name, cfg in util.load_config()["packages"].items():
            if not cfg.get("enabled", True):
                continue
            for target in ("zshrc", "zshenv", "zprofile"):
                if content := cfg.get(target):
                    path = Path.home() / f".{target}"
                    text = path.read_text() if path.exists() else ""
                    _, status = util.ensure_block_text(text, name, content)
                    print(f"[{name}] .{target}: {'ok' if status == 'ok' else 'MISSING'}")
        return
    for name, cfg in util.load_config()["packages"].items():
        if not cfg.get("enabled", True):
            continue
        for target in ("zshrc", "zshenv", "zprofile"):
            if content := cfg.get(target):
                path = Path.home() / f".{target}"
                path.parent.mkdir(parents=True, exist_ok=True)
                result = util.ensure_block(path, name, content)
                if result != "ok":
                    print(f"[{name}] .{target}: {result}")


@task
def set_default_shell(c):
    """Set zsh as the login shell (usermod -s, not chsh — chsh's PAM password prompt doesn't
    work in a non-interactive/piped session the way sudo -A does). Only takes effect in a new
    login shell/terminal, not the one this runs in.
    """
    zsh_path = shutil.which("zsh")
    if not zsh_path:
        print("[zsh] zsh not found on PATH — install it first (apt.base)")
        return
    if util.DRY_RUN:
        print(f"[zsh] default shell: {'ok' if _shell_is_zsh(_current_shell()) else 'MISSING'}")
        return
    if _shell_is_zsh(_current_shell()):
        print(f"[zsh] default shell already zsh ({_current_shell()}) — nothing to do")
        return
    c.run(f"{util.SUDO} usermod -s {zsh_path} {util.current_user()}")
    print(f"[zsh] default shell set to {zsh_path} — close this terminal and open a new one for it to take effect")


@task
def history_fix(c):
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
def p10k_configure(c):
    """Copy repo baseline config/p10k.zsh to ~/.p10k.zsh if not already present."""
    dest = Path.home() / ".p10k.zsh"
    if util.DRY_RUN:
        print(f"[p10k] ~/.p10k.zsh: {'ok' if dest.exists() else 'MISSING'}")
        return
    if dest.exists():
        print("[p10k] ~/.p10k.zsh already exists — skipping")
        return
    src = _REPO_ROOT / "config" / "p10k.zsh"
    if not src.exists():
        print("[p10k] config/p10k.zsh not found in repo — skipping")
        return
    dest.write_bytes(src.read_bytes())
    print("[p10k] ~/.p10k.zsh installed from repo baseline")
