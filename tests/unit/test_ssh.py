"""Unit tests for tasks/ssh.py's pure helpers — the parsing and labelling that decides which agent
a shell is on and which keys it should hold — and for `[packages.ssh]`'s zshenv snippet, run in a
real `zsh -f` against throwaway agents under a temporary runtime directory. The task's own probing
shells out to ssh-add and is not covered here. See tests/README.md.
"""

import os
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from tasks import util
from tasks.ssh import (
    AGENT_EMPTY,
    AGENT_HAS_KEYS,
    AGENT_UNREACHABLE,
    agent_label,
    desktop_sockets,
    parse_fingerprints,
    parse_identity_files,
)

# Real `ssh-add -l` output, three RSA keys in one desktop agent.
_SSH_ADD_L = """\
4096 SHA256:BRJ2dA+DbUy1eoXhSCqydpk9Hsbcpwdv+FdQ/GTe+Tk user@example.com__HOST (RSA)
4096 SHA256:iGwecXMzW6x6YPaBVJC5k7rYDFD+budqPgxKk4hi5Wo other@example.com__HOST (RSA)
4096 SHA256:+O1R/rGaJeh5CTLXwdM6weaRjeZhrYR2HYG5PpToh30 third@example.com__HOST (RSA)
"""


def test_agent_label_distinguishes_empty_from_unreachable():
    # The whole point of the diagnostic: 1 and 2 both look like "the command failed", and mean
    # opposite things — a healthy agent holding nothing vs. no agent at all.
    assert agent_label(AGENT_HAS_KEYS) != agent_label(AGENT_EMPTY)
    assert agent_label(AGENT_EMPTY) != agent_label(AGENT_UNREACHABLE)


def test_agent_label_unknown_code_is_still_readable():
    assert "5" in agent_label(5)


def test_desktop_sockets_order():
    socks = desktop_sockets("/run/user/1000")
    assert socks == [Path("/run/user/1000/keyring/ssh"), Path("/run/user/1000/gcr/ssh")]


@pytest.mark.parametrize("field", ["zprofile", "zshenv"])
def test_desktop_sockets_match_the_setup_toml_snippets(field):
    # Three copies of one list: this helper for `inv ssh.check`, the login shell's picker and the
    # agent shell's. Nothing but this test notices when one of them gains a socket the others lack.
    snippet = util.load_config()["packages"]["ssh"][field]
    positions = [snippet.find(f'"{sock}"') for sock in desktop_sockets("${XDG_RUNTIME_DIR}")]
    assert -1 not in positions, f"[packages.ssh] {field} is missing a desktop socket"
    assert positions == sorted(positions), f"[packages.ssh] {field} tries the sockets in another order"


_AGENT_TOOLS = ("zsh", "ssh-agent", "ssh-add", "ssh-keygen")
needs_agent_tools = pytest.mark.skipif(
    not all(shutil.which(tool) for tool in _AGENT_TOOLS), reason=f"needs {', '.join(_AGENT_TOOLS)}"
)


@pytest.fixture
def runtime_dir() -> Iterator[Path]:
    # Not tmp_path: a unix socket path is capped at 108 bytes, and
    # /tmp/pytest-of-<user>/pytest-<n>/<test name>/keyring/ssh overruns it for the longer names.
    with tempfile.TemporaryDirectory(prefix="ssh-") as tmp:
        yield Path(tmp)


def _clean_env(**extra: str) -> dict[str, str]:
    # Only PATH from the real environment: this machine exports SSH_ASKPASS with
    # SSH_ASKPASS_REQUIRE=prefer, and a real CLAUDECODE would leak into the cases that unset it.
    return {"PATH": os.environ["PATH"], **extra}


@pytest.fixture
def start_agent(runtime_dir: Path) -> Iterator[Callable[..., Path]]:
    procs: list[subprocess.Popen[bytes]] = []

    def start(sock: Path, *, with_key: bool) -> Path:
        sock.parent.mkdir(parents=True, exist_ok=True)
        procs.append(subprocess.Popen(["ssh-agent", "-D", "-a", str(sock)], stdout=subprocess.DEVNULL))
        deadline = time.monotonic() + 5
        while not sock.is_socket():
            assert time.monotonic() < deadline, f"ssh-agent never created {sock}"
            time.sleep(0.01)
        if with_key:
            key = runtime_dir / f"key{len(procs)}"
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "", "-f", str(key)], check=True)
            subprocess.run(["ssh-add", "-q", str(key)], env=_clean_env(SSH_AUTH_SOCK=str(sock)), check=True)
        return sock

    yield start
    for proc in procs:
        proc.terminate()
        proc.wait()


def _run_zshenv(runtime_dir: Path, inherited: Path, *, claudecode: bool = True) -> subprocess.CompletedProcess[str]:
    """Run the snippet the way an agent's Bash call reads ~/.zshenv, and report the socket it left."""
    env = _clean_env(XDG_RUNTIME_DIR=str(runtime_dir), SSH_AUTH_SOCK=str(inherited))
    if claudecode:
        env["CLAUDECODE"] = "1"
    snippet = util.load_config()["packages"]["ssh"].get("zshenv")
    assert snippet, "[packages.ssh] declares no zshenv snippet"
    # The snippet's own status is checked before print runs, since ~/.zshenv's last status is the
    # one every shell starts with.
    script = f'{snippet}\n_status=$?\nprint -r -- "$_status $SSH_AUTH_SOCK"'
    return subprocess.run(["zsh", "-fc", script], env=env, capture_output=True, text=True, check=True)


def _result(proc: subprocess.CompletedProcess[str]) -> tuple[int, Path]:
    status, sock = proc.stdout.strip().split(" ", 1)
    return int(status), Path(sock)


@needs_agent_tools
def test_zshenv_repicks_a_dead_inherited_socket(runtime_dir, start_agent):
    # The 2026-09-28 case: a WezTerm agent link that died with its GUI at logout.
    keyring = start_agent(runtime_dir / "keyring" / "ssh", with_key=True)
    assert _result(_run_zshenv(runtime_dir, runtime_dir / "wezterm" / "agent.1")) == (0, keyring)


@needs_agent_tools
def test_zshenv_skips_a_desktop_agent_holding_no_keys(runtime_dir, start_agent):
    start_agent(runtime_dir / "keyring" / "ssh", with_key=False)
    gcr = start_agent(runtime_dir / "gcr" / "ssh", with_key=True)
    assert _result(_run_zshenv(runtime_dir, runtime_dir / "dead")) == (0, gcr)


@needs_agent_tools
def test_zshenv_leaves_a_working_inherited_agent_alone(runtime_dir, start_agent):
    # Even with a desktop agent available: the loop runs only after the inherited one fails.
    start_agent(runtime_dir / "keyring" / "ssh", with_key=True)
    inherited = start_agent(runtime_dir / "forwarded" / "agent", with_key=True)
    assert _result(_run_zshenv(runtime_dir, inherited)) == (0, inherited)


@needs_agent_tools
def test_zshenv_is_inert_outside_an_agent_shell(runtime_dir, start_agent):
    start_agent(runtime_dir / "keyring" / "ssh", with_key=True)
    dead = runtime_dir / "dead"
    assert _result(_run_zshenv(runtime_dir, dead, claudecode=False)) == (0, dead)


@needs_agent_tools
def test_zshenv_keeps_the_inherited_socket_when_no_agent_holds_keys(runtime_dir):
    # No keychain fallback from a per-call file: nothing is started, and the status stays zero.
    dead = runtime_dir / "dead"
    assert _result(_run_zshenv(runtime_dir, dead)) == (0, dead)


def test_desktop_sockets_without_runtime_dir():
    # A session with no XDG_RUNTIME_DIR (a bare TTY, a container) has no desktop agent to find.
    assert desktop_sockets(None) == []
    assert desktop_sockets("") == []


def test_parse_identity_files_reads_the_paths_ssh_uses():
    config = """\
Host github.com
  HostName github.com
  IdentityFile /home/u/.ssh/user@example.com__HOST_rsa
  User git

Host *
  AddKeysToAgent yes
"""
    assert parse_identity_files(config) == [Path("/home/u/.ssh/user@example.com__HOST_rsa")]


def test_parse_identity_files_is_case_insensitive_and_dedupes():
    # ssh_config keywords are case-insensitive, and the same key is routinely shared by several
    # Host blocks — the agent only needs it once.
    config = """\
Host a
  identityfile ~/.ssh/k
Host b
  IdentityFile ~/.ssh/k
Host c
  IDENTITYFILE ~/.ssh/other
"""
    assert parse_identity_files(config) == [Path.home() / ".ssh/k", Path.home() / ".ssh/other"]


def test_parse_identity_files_expands_home_and_strips_quotes():
    config = 'Host x\n  IdentityFile "~/.ssh/quoted"\n'
    assert parse_identity_files(config) == [Path.home() / ".ssh/quoted"]


def test_parse_identity_files_ignores_comments():
    config = "Host x\n  # IdentityFile ~/.ssh/disabled\n  IdentityFile ~/.ssh/live\n"
    assert parse_identity_files(config) == [Path.home() / ".ssh/live"]


def test_parse_identity_files_none_declared():
    assert parse_identity_files("Host x\n  User git\n") == []


def test_parse_fingerprints_extracts_all_three():
    fps = parse_fingerprints(_SSH_ADD_L)
    assert len(fps) == 3
    assert "SHA256:iGwecXMzW6x6YPaBVJC5k7rYDFD+budqPgxKk4hi5Wo" in fps


def test_parse_fingerprints_on_empty_agent_output():
    # What a live-but-empty agent prints. Must be an empty set, not a parse error — this is the
    # state the whole diagnostic exists to report.
    assert parse_fingerprints("The agent has no identities.\n") == set()


def test_parse_fingerprints_matches_ssh_keygen_output():
    # ssh-keygen -lf prints the same fingerprint format, which is what lets ssh.add compare a key
    # file against what the agent already holds.
    out = "4096 SHA256:BRJ2dA+DbUy1eoXhSCqydpk9Hsbcpwdv+FdQ/GTe+Tk user@example.com (RSA)\n"
    assert parse_fingerprints(out) == {"SHA256:BRJ2dA+DbUy1eoXhSCqydpk9Hsbcpwdv+FdQ/GTe+Tk"}
