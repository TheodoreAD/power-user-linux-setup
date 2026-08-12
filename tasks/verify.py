from pathlib import Path

from invoke import task

from . import util

# Hard ceiling on any single check, via coreutils `timeout` — not a fallback/retry, just a bound
# on the one attempt. Necessary in practice, not just in theory: auditing this task against a real
# machine hung the whole session when it hit `nyancat --version` — nyancat ignores unrecognized
# flags and just runs its terminal animation forever instead of exiting. Without this, one
# badly-behaved package could hang `inv setup` (and, demonstrated live, the machine it runs on)
# indefinitely. A `verify_cmd` override doesn't need to repeat `timeout` itself; it's applied here
# uniformly to every 'cmd' check regardless of source.
_TIMEOUT_SECS = 15

# Methods that install a straightforwardly invocable command, verified by convention as
# `<check_cmd or table-key> --version` unless overridden.
_INVOKABLE = {
    util.PackageMethod.APT,
    util.PackageMethod.APT_REPO,
    util.PackageMethod.DEB_GITHUB,
    util.PackageMethod.DEB_URL,
    util.PackageMethod.UV_TOOL,
    util.PackageMethod.BINARY,
    util.PackageMethod.NVM,
}

# Methods with no invocable command by nature — verified by existence only (same file/dir the
# install-time "already installed" check already looks for), never by running anything. Found
# during the audit pass that invoking one of these to "verify" it would be actively unsafe: a
# wrapper-script's dest may be a script meant to be sourced by SUDO_ASKPASS or to launch a
# background proxy, not run standalone and re-entered as a health check.
_PATH_ONLY = {
    util.PackageMethod.GIT_CLONE: "dest",
    util.PackageMethod.WRAPPER_SCRIPT: "dest",
    util.PackageMethod.APPARMOR_PROFILE: "profile",
}


def _resolve(name: str, cfg: dict, method: util.PackageMethod) -> tuple[str, str]:
    """Return (kind, target) for one package — 'skip'/'path'/'cmd'/'error', and the reason,
    path, or shell command respectively. One deterministic outcome per package, no fallback chain.
    """
    if cfg.get("verify") is False:
        return "skip", "opted out (verify = false)"
    if verify_cmd := cfg.get("verify_cmd"):
        return "cmd", verify_cmd

    if method in _INVOKABLE:
        return "cmd", f"{cfg.get('check_cmd', name)} --version"

    if method == util.PackageMethod.ARCHIVE:
        return "cmd", f"{cfg.get('check_cmd', cfg.get('bin_pick', name))} --version"

    if method == util.PackageMethod.SCRIPT:
        if (check_path := cfg.get("check_path")) and not cfg.get("check_cmd"):
            return "path", check_path
        return "cmd", f"{cfg.get('check_cmd', name)} --version"

    if method in _PATH_ONLY:
        return "path", cfg[_PATH_ONLY[method]]

    if method == util.PackageMethod.GNOME_EXTENSION:
        # Always skipped by default, not just tag-gated: no automated path — not even inv setup —
        # ever calls inv gnome.extensions (deliberately; see tasks/gnome.py, never touch a live
        # GNOME session automatically). Tags alone don't capture that, since gnome/gui aren't
        # excluded on a default desktop install where this method's entries are otherwise fully
        # tag-eligible — checking them by default would fail inv setup for extensions it never
        # attempted to install in the first place. Still checkable per-package via an explicit
        # verify_cmd (e.g. after running inv gnome.extensions by hand): the
        # `gnome-extensions list | grep -qF <uuid>` query itself is safe and read-only, just not
        # the default here.
        return "skip", "gnome-extension — not installed by inv setup, see inv gnome.extensions"

    return "error", f"unhandled method={method.value}"


def _all_checks() -> list[tuple[str, str, str]]:
    # [packages.node] (method="nvm") is read via packages_by_method() here even though
    # node.install itself (tasks/node.py) bypasses it and ignores tags/enabled entirely — fine
    # today since that section carries neither field, but would silently diverge from what
    # node.install actually does if tags/enabled were ever added to it later.
    checks = [
        (name, *_resolve(name, cfg, method))
        for method in util.PackageMethod
        for name, cfg in util.packages_by_method(method).items()
    ]
    # method = "zsh" entries are config-only (zshrc/zshenv/zprofile snippets) and invisible to
    # packages_by_method() by design (no "zsh" PackageMethod member — see tasks/zsh.py's own
    # direct scan) — accounted for here explicitly so nothing silently has zero coverage.
    checks += [
        (name, "skip", "config-only, no command to verify")
        for name, cfg in util.load_config()["packages"].items()
        if cfg.get("method") == "zsh" and cfg.get("enabled", True)
    ]
    return checks


@task
def all(c):
    """Prove every package this run installed actually works, not just that it's present.
    Convention-based: default check is `<check_cmd or name> --version` for invocable methods,
    existence for methods with no command by nature (git-clone/wrapper-script/apparmor-profile).
    gnome-extension always skips (inv setup never installs extensions — see tasks/gnome.py).
    Override per package in setup.toml with `verify_cmd` (different invocation) or
    `verify = false` (no functional check is possible at all). No fallback chain — first failure
    aborts immediately (plain c.run(), no warn=True), the deliberate opposite of apt.py's
    warn=True-and-continue pattern: this task exists to catch exactly what that pattern lets
    through silently. Every invocation is bounded by _TIMEOUT_SECS — a hang counts as a failure,
    not an exemption.
    """
    checks = _all_checks()

    if util.DRY_RUN:
        for name, kind, target in checks:
            if kind == "skip":
                print(f"[verify] {name}: skipped")
            elif kind == "path":
                print(f"[verify] {name}: {util.ok_label(Path(target).expanduser().exists())}")
            elif kind == "cmd":
                print(f"[verify] {name}: {util.ok_label(util.command_exists(target.split()[0]))}")
            else:
                print(f"[verify] {name}: MISSING ({target})")
        return

    for name, kind, target in checks:
        if kind == "skip":
            print(f"[verify] {name}: skipped ({target})")
        elif kind == "path":
            if not Path(target).expanduser().exists():
                raise RuntimeError(f"[verify] {name}: {target} not found")
            print(f"[verify] {name}: ok")
        elif kind == "cmd":
            c.run(f"timeout {_TIMEOUT_SECS}s {target}", hide=True)
            print(f"[verify] {name}: ok")
        else:
            raise RuntimeError(f"[verify] {name}: {target}")
