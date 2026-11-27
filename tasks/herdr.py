"""Herdr desktop app: the Estro layout and the mods it is built from.

`[packages.herdr-app]` installs the app and seeds its settings; this adds what the app has no
installer for. The source is win-configs' `herdr/README.md` ("Estro layout and mods" and "On
Linux"), which was a script to paste. Its layout, icon and Better Tabs patch are copied verbatim
into `config/herdr-app/` (from win-configs 4ddc4a4, 2026-11-25), so this repo can run it unaided
and the next Linux machine gets the same thing.

The mods are third-party JavaScript running with the user's access, so they come from the two
commits that README records as security-reviewed on 2026-11-23, never from a branch. Bump a pin
only after reviewing the diff, and change the README alongside it so both machines agree.

Not part of `inv setup`: the mods folder exists only once the app has started, which a setup run
cannot do for you, and a fresh install of the mods wants a person watching the first launch.
"""

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from invoke import Context, task
from invoke.exceptions import Exit

from . import deploy

_REPO_ROOT = Path(__file__).parent.parent
APP_HOME = Path.home() / ".config" / "herdr-app"
MODS_DIR = APP_HOME / "mods"


@dataclass(frozen=True)
class _Source:
    repo: str
    commit: str
    mods: tuple[str, ...]  # each a path inside the repo whose last part is the mod's folder name


_MUNZA = _Source(
    repo="https://github.com/munza/herdr-mods",
    commit="1abf4870adb4c3f7a71739db1e0c29493f5e3f95",
    mods=(
        "better-icons/mods/better-icons",
        "better-sidebar/mods/better-sidebar",
        "better-tabs/mods/better-tabs",
        "better-files/mods/better-files",
        "better-changes/mods/better-changes",
        "better-config/mods/better-config",
    ),
)
_ISSUES = _Source(
    repo="https://github.com/jankeesvw/herdr-issues",
    commit="15ffaad00d37efe17ef952109a3198fe299ecb67",
    mods=("mods/issues",),
)
_SOURCES = (_MUNZA, _ISSUES)

# Branch PR is the one mod with a build step: its own Go program compiles a helper and installs the
# mod folder itself, refusing if one is already there. It uses no third-party Go modules.
_BRANCH_PR = "branch-pr"
_BRANCH_PR_HELPER = "branch-pr/helper"

_PATCH = "config/herdr-app/patches/better-tabs-launch-names.patch"
# Better Changes draws every changed file at once and Herdr interrupts a slow render, so a repo
# with a few hundred changes hangs the panel; 100 is the README's value.
_CHANGES_FILE_LIMIT = 100


def mod_names() -> list[str]:
    """Every mod folder this task installs, in install order."""
    return [Path(path).name for source in _SOURCES for path in source.mods] + [_BRANCH_PR]


def managed_files() -> list[deploy.Managed]:
    """The Estro layout and its Issues icon.

    CONFIG_FILE, so seeded rather than owned: a layout is something a person rearranges in the app,
    and an edit made there is theirs to keep, not drift to report. Not `config_files` on the
    package, because a declared destination is one `inv verify.all` requires after every setup,
    and this one exists only once somebody has run this task.
    """
    return [
        deploy.Managed(
            path=APP_HOME / "layouts" / name,
            package="herdr-app",
            source=f"config/herdr-app/layouts/{name}",
            mechanism=deploy.Mechanism.CONFIG_FILE,
        )
        for name in ("estro.json", "estro-issues.svg")
    ]


def _limit_changes(mod_json: Path) -> None:
    manifest = cast(dict[str, object], json.loads(mod_json.read_text(encoding="utf-8")))
    settings = cast(dict[str, object], manifest.setdefault("settings", {}))
    limits = cast(dict[str, object], settings.setdefault("limits", {}))
    limits["files"] = _CHANGES_FILE_LIMIT
    _ = mod_json.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


@task
def install_mods(c: Context):
    """Install the Estro layout and its mods into Herdr, from the reviewed upstream commits.

    Start Herdr once first, so it creates its config folder. Never replaces a mod that is already
    there: delete that mod's folder to reinstall it. Afterwards, switch to the layout with
    `herdr-app do layout.switch '{"name":"estro"}'`.
    """
    if not MODS_DIR.is_dir():
        raise Exit(f"[herdr] {MODS_DIR} does not exist — start Herdr once so it creates it, then re-run")
    fresh: list[str] = []
    with TemporaryDirectory(prefix="pulse-herdr-") as tmp:
        for source in _SOURCES:
            clone = Path(tmp) / source.repo.rsplit("/", 1)[-1]
            c.run(f"git clone --quiet {source.repo} {clone}")
            c.run(f"git -C {clone} checkout --quiet {source.commit}")
            for path in source.mods:
                dst = MODS_DIR / Path(path).name
                if dst.exists():
                    print(f"[herdr] {dst.name}: already installed, left alone")
                    continue
                shutil.copytree(clone / path, dst, symlinks=True)
                fresh.append(dst.name)
                print(f"[herdr] {dst.name}: installed")
        if (MODS_DIR / _BRANCH_PR).exists():
            print(f"[herdr] {_BRANCH_PR}: already installed, left alone")
        else:
            # GOTOOLCHAIN=local: never let `go` download a toolchain other than the installed one.
            c.run(f"go -C {Path(tmp) / 'herdr-mods' / _BRANCH_PR_HELPER} run ./install", env={"GOTOOLCHAIN": "local"})
            fresh.append(_BRANCH_PR)

    # Only on a copy made just now: the patch and the limit edit a fresh upstream folder, and a
    # folder left alone may already carry them, or a person's own change.
    if "better-tabs" in fresh:
        # GIT_CEILING_DIRECTORIES stops git finding a repository above the mods folder, where
        # `git apply` would read the patch's paths as relative to that repository's root instead.
        c.run(
            f"git -C {MODS_DIR / 'better-tabs'} apply {_REPO_ROOT / _PATCH}",
            env={"GIT_CEILING_DIRECTORIES": str(MODS_DIR)},
        )
    if "better-changes" in fresh:
        _limit_changes(MODS_DIR / "better-changes" / "mod.json")

    for managed in managed_files():
        deploy.deploy(managed)
    for name in mod_names():
        c.run(f"herdr-app check {MODS_DIR / name}")
    print("""[herdr] done — switch to it with: herdr-app do layout.switch '{"name":"estro"}'""")
