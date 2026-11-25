"""WSL distros, managed from the Windows host: install one with a generic sudo user, check it, remove
it. The `wsl` collection is the other half and runs inside a distro (wsl.conf, DNS, systemd).

Moved here from win-configs' `scripts/setup-wsl.py` on 2026-11-25, which was always meant to end up
in this repo, and extended on the way for side-by-side throwaway distros: `--name` installs a second
copy of an image under its own name, `--no-set-default` leaves the current default distro alone,
and `remove` unregisters one. That is what testing PULSE in WSL needs without touching the distro
that holds real work (Docker's engine, say).

What `install` does, and why each step is the way it is:

- **`wsl --install <image> --no-launch`**, with the distro's interactive first run skipped by
  clearing its `RunOOBE` flag in the registry. Ubuntu's first run would prompt for a user, append
  `[user] default=...` to /etc/wsl.conf and register the Ubuntu font in Windows.
- **A virtual-disk cap** (`--vhd-size`, default 500GB; WSL's own default is 1TB), so a runaway
  build or log inside WSL cannot fill the Windows drive. Set on install; an existing distro of
  another size is resized, which needs `wsl --shutdown` and so stops every distro.
- **User `dev`**, in the sudo group with no usable password: a short generic name, not tied to the
  Windows account, so paths like `/home/dev` are the same on every machine and nothing personal
  lands in them.
- **Passwordless sudo** (`/etc/sudoers.d/<user>`, validated with `visudo`). Not a security boundary
  given up: anything running as the user on Windows already gets root with `wsl -u root`.
- **Default login through the registry's `DefaultUid`**, so /etc/wsl.conf stays entirely the Linux
  side's file (`inv wsl.fix` edits it).

Runs on Windows only, and stdlib only: `winreg` is imported where it is used, after the platform
check, so the module still imports on Linux, where every task refuses with a message instead.
"""

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from invoke import Context, Exit, task

from . import ui, util

DEFAULT_IMAGE = "Ubuntu-24.04"
_LXSS = r"Software\Microsoft\Windows\CurrentVersion\Lxss"
_USER_NAME = re.compile(r"[a-z_][a-z0-9_-]{0,31}")


def _require_windows() -> None:
    if sys.platform != "win32":
        raise Exit("[wsl-distro] runs on the Windows host; inside a distro, the `wsl` tasks apply")


def _wsl(*args: str, stdin: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    """`wsl.exe`, with UTF-8 output: it prints UTF-16 otherwise, which reads as NULs in between."""
    result = subprocess.run(
        ["wsl.exe", *args],
        capture_output=True,
        input=stdin,
        env={**os.environ, "WSL_UTF8": "1"},
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if check and result.returncode:
        raise Exit(f"[wsl-distro] wsl {' '.join(args)} failed ({result.returncode}):\n{result.stdout}{result.stderr}")
    return result


def _as_root(name: str, script: str, *args: str, stdin: str | None = None, check: bool = True):
    """A POSIX sh script inside the distro, as root, with `args` as $1.. — no Windows-side quoting."""
    return _wsl("-d", name, "-u", "root", "--exec", "sh", "-c", script, "sh", *args, stdin=stdin, check=check)


def registered() -> list[str]:
    return [line.strip() for line in _wsl("--list", "--quiet", check=False).stdout.splitlines() if line.strip()]


def size_bytes(text: str) -> int:
    """WSL's size strings (500GB, 1TB, 300G) in bytes. WSL counts in binary units."""
    m = re.fullmatch(r"(\d+)\s*([KMGT])B?", text.strip(), re.IGNORECASE)
    if not m:
        raise Exit(f"[wsl-distro] --vhd-size {text!r}: use a number and a unit, e.g. 500GB or 1TB")
    return int(m[1]) << (10 * ("KMGT".index(m[2].upper()) + 1))


def _gib(n: int) -> str:
    return f"{n / 1024**3:.0f}GB"


def install_command(image: str, name: str, vhd_size: str) -> list[str]:
    """The `wsl` arguments that install `image`, registered as `name` when that differs."""
    named = ["--name", name] if name != image else []
    return ["--install", image, *named, "--no-launch", "--vhd-size", vhd_size]


@dataclass
class _Registration:
    key: str
    default_uid: int | None
    run_oobe: int | None
    base_path: str | None
    is_default: bool


def _registration(name: str) -> _Registration | None:
    """The distro's entry under HKCU\\...\\Lxss, found by its DistributionName."""
    if sys.platform != "win32":
        return None
    import winreg  # noqa: PLC0415 — Windows-only module, imported after the platform check

    def value(key: winreg.HKEYType, field: str) -> object:
        try:
            return cast(object, winreg.QueryValueEx(key, field)[0])
        except FileNotFoundError:
            return None

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _LXSS) as root:
        default_guid = value(root, "DefaultDistribution")
        for i in range(winreg.QueryInfoKey(root)[0]):
            guid = winreg.EnumKey(root, i)
            with winreg.OpenKey(root, guid) as k:
                if value(k, "DistributionName") == name:
                    uid, oobe, base = value(k, "DefaultUid"), value(k, "RunOOBE"), value(k, "BasePath")
                    return _Registration(
                        key=f"{_LXSS}\\{guid}",
                        default_uid=uid if isinstance(uid, int) else None,
                        run_oobe=oobe if isinstance(oobe, int) else None,
                        base_path=base if isinstance(base, str) else None,
                        is_default=guid == default_guid,
                    )
    return None


def _set_registry(key: str, field: str, number: int) -> None:
    if sys.platform != "win32":
        return
    import winreg  # noqa: PLC0415 — Windows-only module, imported after the platform check

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, field, 0, winreg.REG_DWORD, number)


def _disk_size(name: str) -> int | None:
    """The virtual size of the distro's root disk, in bytes: what the disk may grow to."""
    out = _as_root(name, 'blockdev --getsize64 "$(findmnt -no SOURCE /)"', check=False).stdout.strip()
    return int(out) if out.isdigit() else None


def _host_room_warning(reg: _Registration, cap: int) -> str | None:
    """The cap only protects Windows if the drive holding the VHDX can actually give it that much."""
    vhdx = Path(os.path.expandvars(reg.base_path or "")) / "ext4.vhdx"
    if not vhdx.is_file():
        return None
    room = shutil.disk_usage(vhdx.anchor).free + vhdx.stat().st_size
    if cap <= room:
        return None
    return (
        f"the cap ({_gib(cap)}) is more than {vhdx.anchor} can give the disk ({_gib(room)}: free space plus "
        f"the VHDX's current {_gib(vhdx.stat().st_size)}), so a full WSL disk would still fill {vhdx.anchor}"
    )


def _check_user(user: str) -> None:
    if not _USER_NAME.fullmatch(user):
        raise Exit("[wsl-distro] --user must be a lowercase Linux name (a-z, 0-9, _ or -, starting with a letter)")


@task(
    help={
        "name": f"Name to register the distro under (default: {DEFAULT_IMAGE})",
        "image": f"Distribution to install, as `wsl --list --online` names it (default: {DEFAULT_IMAGE})",
        "user": "The generic sudo user to create and log in as (default: dev)",
        "vhd-size": "Cap on the distro's virtual disk, e.g. 500GB (default; WSL's own is 1TB)",
        "set-default": "Make it the default distro (default: yes; --no-set-default for a side-by-side one)",
    }
)
def install(
    c: Context,
    name: str = DEFAULT_IMAGE,
    image: str = DEFAULT_IMAGE,
    user: str = "dev",
    vhd_size: str = "500GB",
    set_default: bool = True,
):
    """Install a WSL distro with a passwordless-sudo user as its default login, or repair one.

    Safe to run again: each step checks first and skips what is done. Ends with `check`.
    """
    _require_windows()
    _check_user(user)
    cap = size_bytes(vhd_size)
    if name not in registered():
        print(f"[wsl-distro] installing {image} as {name} (the download can take a few minutes)")
        _wsl(*install_command(image, name, vhd_size))
        if name not in registered():
            raise Exit(f"[wsl-distro] {name} isn't registered after install; run `wsl -d {name}` once, then again")
    else:
        print(f"[wsl-distro] {name} already installed")

    current = _disk_size(name)
    if current is not None and current != cap:
        print(f"[wsl-distro] resizing the virtual disk {_gib(current)} -> {vhd_size} (shuts down all of WSL)")
        _wsl("--shutdown")
        _wsl("--manage", name, "--resize", vhd_size)

    reg = _registration(name)
    if reg is None:
        raise Exit(f"[wsl-distro] {name} is registered but has no entry under HKCU\\{_LXSS}")
    if set_default and not reg.is_default:
        print(f"[wsl-distro] making {name} the default distro")
        _wsl("--set-default", name)

    if _as_root(name, 'id -u "$1" >/dev/null 2>&1', user, check=False).returncode:
        print(f"[wsl-distro] creating user {user}")
        _as_root(name, 'useradd --create-home --shell /bin/bash --groups sudo "$1"', user)
    else:
        _as_root(name, 'usermod --append --groups sudo "$1"', user)

    _as_root(
        name,
        'f=/etc/sudoers.d/"$1"; cat > "$f.tmp" && visudo -cqf "$f.tmp" && chmod 0440 "$f.tmp" && mv "$f.tmp" "$f"',
        user,
        stdin=f"{user} ALL=(ALL) NOPASSWD:ALL\n",
    )

    uid = int(_as_root(name, 'id -u "$1"', user).stdout.strip())
    changed = False
    if reg.default_uid != uid:
        print(f"[wsl-distro] default login -> {user} (uid {uid})")
        _set_registry(reg.key, "DefaultUid", uid)
        changed = True
    # WSL clears RunOOBE itself after the first interactive launch; clearing it here makes that
    # launch a plain login instead of Ubuntu's user-creation prompt.
    if reg.run_oobe:
        print("[wsl-distro] skipping the distro's first-run setup (RunOOBE -> 0)")
        _set_registry(reg.key, "RunOOBE", 0)
        changed = True
    if changed:
        _wsl("--terminate", name)

    _report(name, user, vhd_size, expect_default=set_default)


_WHO = 'echo "$(id -un) $(id -Gn | tr " " ",")"; sudo -n true && echo sudo-ok'


def _login_problems(name: str, user: str) -> tuple[str, bool, list[str]]:
    """(default login, passwordless sudo works, problems) — read by logging in as the default user."""
    who = _wsl("-d", name, "--exec", "sh", "-c", _WHO, check=False).stdout.split()
    login = who[0] if who else "?"
    sudo_ok = "sudo-ok" in who
    problems: list[str] = []
    if login != user:
        problems.append(f"default login is {login}, not {user}")
    if "sudo" not in (who[1].split(",") if len(who) > 1 else []):
        problems.append(f"{user} isn't in the sudo group")
    if not sudo_ok:
        problems.append("passwordless sudo doesn't work")
    return login, sudo_ok, problems


def _problems(name: str, user: str, vhd_size: str, *, expect_default: bool) -> tuple[list[str], list[str]]:
    """(problems, notes) for one distro. Notes are facts worth printing that are not failures."""
    if name not in registered():
        return [f"{name} isn't installed"], []
    reg = _registration(name)
    if reg is None:
        return [f"{name} has no registry entry"], []
    problems: list[str] = []
    if expect_default and not reg.is_default:
        problems.append(f"{name} isn't the default distro")
    if reg.run_oobe:
        problems.append("the distro's first-run setup is still pending (RunOOBE=1)")
    login, sudo_ok, login_problems = _login_problems(name, user)
    problems += login_problems
    size = _disk_size(name)
    if size is None:
        problems.append("couldn't read the virtual disk size")
    elif size > size_bytes(vhd_size):
        problems.append(f"the virtual disk can grow to {_gib(size)}, more than the {vhd_size} cap")
    notes = [f"{name}: default={reg.is_default}, login={login}, sudo-ok={sudo_ok}, disk cap={_gib(size or 0)}"]
    if warning := _host_room_warning(reg, size or size_bytes(vhd_size)):
        notes.append(f"WARNING: {warning}")
    return problems, notes


def _report(name: str, user: str, vhd_size: str, *, expect_default: bool) -> None:
    problems, notes = _problems(name, user, vhd_size, expect_default=expect_default)
    for note in notes:
        print(f"[wsl-distro] {note}")
    if problems:
        raise Exit("\n".join(f"[wsl-distro] PROBLEM: {p}" for p in problems))


@task(
    help={
        "name": f"Registered distro name (default: {DEFAULT_IMAGE})",
        "user": "The user it should log in as (default: dev)",
        "vhd-size": "The disk cap it should have (default: 500GB)",
        "expect-default": "Report it as a problem when this isn't the default distro (default: yes)",
    }
)
def check(
    c: Context, name: str = DEFAULT_IMAGE, user: str = "dev", vhd_size: str = "500GB", expect_default: bool = True
):
    """Verify a distro without changing anything: login user, passwordless sudo, first-run, disk cap."""
    _require_windows()
    _check_user(user)
    _report(name, user, vhd_size, expect_default=expect_default)


@task(
    help={
        "name": "Registered distro name to remove (required)",
        "yes": "Don't ask for confirmation",
        "force": "Allow removing the default distro",
    }
)
def remove(c: Context, name: str, yes: bool = False, force: bool = False):
    """Unregister a distro, deleting everything inside it. Asks first; refuses the default distro."""
    _require_windows()
    if name not in registered():
        print(f"[wsl-distro] {name} isn't installed, nothing to remove")
        return
    reg = _registration(name)
    if reg is not None and reg.is_default and not force:
        raise Exit(f"[wsl-distro] {name} is the default distro; pass --force to remove it anyway")
    if not yes:
        ui.warn(f"`wsl --unregister {name}` deletes its virtual disk and every file inside it.")
        if not util.confirm(f"Remove {name}?", default=False):
            print("[wsl-distro] left in place")
            return
    _wsl("--unregister", name)
    print(f"[wsl-distro] removed {name}")
