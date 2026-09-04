from pathlib import Path

from invoke import Context, task

from . import deploy, tools, util

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


def _path_only(name: str, cfg: util.PackageConfig, method: util.PackageMethod) -> tuple[str, str] | None:
    """Methods with no invocable command by nature — verified by existence only (same file/dir
    the install-time "already installed" check already looks for), never by running anything.
    Found during the audit pass that invoking one of these to "verify" it would be actively
    unsafe: a wrapper-script's dest may be a script meant to be sourced by SUDO_ASKPASS or to
    launch a background proxy, not run standalone and re-entered as a health check. None for
    any other method."""
    if method == util.PackageMethod.GIT_CLONE:
        if "dest" not in cfg:
            raise util.missing_fields(name, "dest")
        return "path", cfg["dest"]
    if method == util.PackageMethod.APPARMOR_PROFILE:
        if "profile" not in cfg:
            raise util.missing_fields(name, "profile")
        return "path", cfg["profile"]
    return None


def _resolve_wrapper_script(name: str, cfg: util.PackageConfig) -> tuple[str, str]:
    """Existence alone doesn't catch a deploy that landed stale/partial/hand-edited content —
    confirmed as a real gap, not theoretical: this session needed a manual diff twice to confirm
    ~/AGENTS.md actually matched its repo-side source after a redeploy, exactly what this check
    exists to make unnecessary. A "deploy" check asks tasks/deploy.py's classifier — the same
    answer `inv deploy.status` gives — rather than re-implementing the content comparison here.
    Every wrapper-script package currently declares content_file or assembled_from (no
    inline-`content` variant is actually in use), but fall back to existence-only for a
    hypothetical future one that doesn't, rather than erroring."""
    if "dest" not in cfg:
        raise util.missing_fields(name, "dest")
    if cfg.get("content_file") or cfg.get("assembled_from"):
        return "deploy", cfg["dest"]
    return "path", cfg["dest"]


def _deploy_check(m: deploy.Managed, state: deploy.State) -> tuple[bool, str]:
    """(passed, message) for one deployed path, from the shared classification.

    MANAGED content (wrapper-script, skills) must be exactly what a fresh deploy would write —
    anything else is a stale, partial, or hand-edited destination, and fails. SEEDED content
    (config_files) is the user's after first install, so only its absence fails; a customized or
    out-of-date copy is reported and passes, since flagging it would fail `inv setup` on every
    config the user has ever touched.
    """
    if state == deploy.State.CLEAN:
        return True, "ok"
    if state == deploy.State.ABSENT:
        return False, f"{m.path} not found — not deployed"
    if m.policy == deploy.Policy.SEEDED:
        return True, f"ok (your copy differs from {m.source} — yours to own)"
    return False, f"{m.path} {deploy.SUMMARY[state]} — see `inv deploy.status --name {m.package}`"


def _resolve(name: str, cfg: util.PackageConfig, method: util.PackageMethod) -> tuple[str, str]:
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

    if method == util.PackageMethod.WRAPPER_SCRIPT:
        return _resolve_wrapper_script(name, cfg)

    if path_only := _path_only(name, cfg, method):
        return path_only

    if method == util.PackageMethod.GNOME_EXTENSION:
        # Always skipped by default, not just tag-gated: no automated path — not even inv setup —
        # ever calls inv gnome.install-extensions (deliberately; see tasks/gnome.py, never touch a live
        # GNOME session automatically). Tags alone don't capture that, since gnome/gui aren't
        # excluded on a default desktop install where this method's entries are otherwise fully
        # tag-eligible — checking them by default would fail inv setup for extensions it never
        # attempted to install in the first place. Still checkable per-package via an explicit
        # verify_cmd (e.g. after running inv gnome.install-extensions by hand): the
        # `gnome-extensions list | grep -qF <uuid>` query itself is safe and read-only, just not
        # the default here.
        return "skip", "gnome-extension — not installed by inv setup, see inv gnome.install-extensions"

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
    # packages_by_method() by design (no "zsh" PackageMethod member) — accounted for here
    # explicitly so nothing silently has zero coverage. Tag-blind, unlike zsh.configure itself,
    # which stopped being so; harmless because every row this produces is a "skip" with nothing to
    # verify, so the only effect is that an excluded package is still named as skipped.
    checks += [
        (name, "skip", "config-only, no command to verify")
        for name, cfg in util.load_config()["packages"].items()
        if cfg.get("method") == "zsh" and cfg.get("enabled", True)
    ]
    # Deployed paths that aren't a package's primary artifact: any method's `config_files`
    # mappings and every `skills` entry. The registry is the one place that knows them all;
    # wrapper-script destinations are already covered above (via _resolve, so verify_cmd /
    # verify = false still apply to them) and are excluded here so nothing is checked twice.
    checks += [
        (m.package, "deploy", str(m.path))
        for m in deploy.managed_paths().values()
        if m.mechanism not in (deploy.Mechanism.WRAPPER_SCRIPT, deploy.Mechanism.ASSEMBLED)
    ]
    checks += _symlink_checks()
    return checks


def _symlink_checks() -> list[tuple[str, str, str]]:
    """One check per `symlink_dest` whose agent is actually installed here.

    A deploy check proves the instructions file holds the right bytes; it says nothing about whether
    each agent can *see* it, and a missing or misdirected link is silent — the agent simply runs
    without the rules. Links whose parent directory doesn't exist are skipped for the same reason
    the installer skips creating them: that agent isn't installed, so its missing link is correct.

    An `always` destination is never skipped, matching `tools._ensure_symlink`: the installer
    creates that parent rather than reading its absence as a verdict, so a missing link there is a
    real failure and not a machine without that agent.
    """
    return [
        (name, "symlink", str(link.path))
        for name, cfg in util.enabled_packages().items()
        for link in tools.symlink_dests(cfg)
        if link.always or link.path.parent.is_dir()
    ]


def _symlink_check(target: str) -> tuple[bool, str]:
    """(passed, message) for one declared symlink.

    Correctness is "resolves to a path this repo deploys", not merely "is a symlink": a link
    pointing at a stale or hand-made copy of the file would satisfy the weaker test while leaving
    that agent reading something PULSE doesn't manage. deploy.lookup already resolves a symlink to
    its target's registry entry, which is exactly the question being asked.
    """
    link = Path(target).expanduser()
    if not link.is_symlink():
        kind = "a regular file" if link.exists() else "missing"
        return False, f"{target} is {kind}, not a symlink — that agent isn't reading the deployed file"
    m = deploy.lookup(link)
    if m is None or m.path != link.resolve():
        return False, f"{target} points at {link.resolve()}, which this repo doesn't deploy"
    return True, f"{target} -> {m.path}"


def _classify_deploy(target: str) -> tuple[deploy.Managed, deploy.State]:
    m = deploy.lookup(target)
    if m is None:
        raise RuntimeError(f"[verify] {target} is a deploy check target but isn't in the deploy registry")
    return m, deploy.classify(m)


@task
def all(c: Context):  # noqa: A001, C901
    """Prove every package this run installed actually works, not just that it's present.
    Convention-based: default check is `<check_cmd or name> --version` for invocable methods,
    existence for methods with no command by nature (git-clone/apparmor-profile), and the deploy
    classifier's verdict (tasks/deploy.py, the same one `inv deploy.status` reports) for every
    path this repo deploys under ~ — wrapper-script `content_file`s, `config_files`, skills —
    since existence alone doesn't catch a deploy that landed stale/partial/hand-edited content,
    only that something is there. A customized `config_files` copy passes (it's yours after the
    first install); anything else that differs fails. gnome-extension always skips (inv setup
    never installs extensions — see tasks/gnome.py). Override per package in setup.toml with
    `verify_cmd` (different invocation) or `verify = false` (no functional check is possible at
    all). A GUI application whose only interface is a window needs one of those — audited
    2026-08-30, the whole class is `freelens` and `telegram-desktop`, and what each can honestly
    promise depends on how it is packaged (see contributing/verify.md, "Auditing the rest of the
    class"). No fallback chain — first failure
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
            elif kind == "deploy":
                print(f"[verify] {name}: {util.ok_label(_deploy_check(*_classify_deploy(target))[0])}")
            elif kind == "symlink":
                print(f"[verify] {name}: {util.ok_label(_symlink_check(target)[0])}")
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
        elif kind == "deploy":
            passed, message = _deploy_check(*_classify_deploy(target))
            if not passed:
                raise RuntimeError(f"[verify] {name}: {message} — redeploy needed (`inv deploy.all`)")
            print(f"[verify] {name}: {message}")
        elif kind == "symlink":
            passed, message = _symlink_check(target)
            if not passed:
                raise RuntimeError(f"[verify] {name}: {message} — re-run `inv tools.install`")
            print(f"[verify] {name}: {message}")
        elif kind == "cmd":
            c.run(f"timeout {_TIMEOUT_SECS}s {target}", hide=True)
            print(f"[verify] {name}: ok")
        else:
            raise RuntimeError(f"[verify] {name}: {target}")
