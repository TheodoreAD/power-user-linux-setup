"""Unit tests for tasks/ssh.py's pure helpers — the parsing and labelling that decides which agent
a shell is on and which keys it should hold. The probing itself shells out to ssh-add and is not
covered here. See tests/README.md.
"""

from pathlib import Path

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


def test_desktop_sockets_order_matches_the_zprofile_snippet():
    socks = desktop_sockets("/run/user/1000")
    assert socks == [Path("/run/user/1000/keyring/ssh"), Path("/run/user/1000/gcr/ssh")]


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
