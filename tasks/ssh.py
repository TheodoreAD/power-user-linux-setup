import subprocess
from pathlib import Path

from invoke import task

from . import util

_SSH_DIR = Path.home() / ".ssh"
_SSH_CONFIG = _SSH_DIR / "config"

_HOST_STAR = """\
Host *
  IgnoreUnknown AddKeysToAgent
  AddKeysToAgent yes
  PreferredAuthentications publickey,keyboard-interactive,password,hostbased,gssapi-with-mic
  IdentitiesOnly yes
  ServerAliveInterval 300
  ServerAliveCountMax 3"""


def _node() -> str:
    return subprocess.run(["uname", "-n"], capture_output=True, text=True).stdout.strip()


def _key_path(email: str, node: str) -> Path:
    return _SSH_DIR / f"{email}__{node}_ed25519"


@task
def keys(c):
    """Create ed25519 SSH keys for each unique email in identity.toml (skips existing)."""
    identity = util.load_identity()
    hosts = identity.get("ssh_hosts", [])
    emails = sorted({h["email"] for h in hosts})
    node = _node()

    if util.DRY_RUN:
        for email in emails:
            key = _key_path(email, node)
            status = "ok" if key.exists() else "MISSING"
            print(f"[ssh] key {key.name}: {status}")
        return

    _SSH_DIR.mkdir(mode=0o700, exist_ok=True)
    for email in emails:
        key = _key_path(email, node)
        if key.exists():
            print(f"[ssh] key exists: {key.name}")
            continue
        print(f"[ssh] creating key for {email}:")
        c.run(f'ssh-keygen -t ed25519 -C "{email}__{node}" -f "{key}"', pty=True)


@task
def configure(c):
    """Write ~/.ssh/config from identity.toml (idempotent PULSE block)."""
    identity = util.load_identity()
    hosts = identity.get("ssh_hosts", [])
    node = _node()

    if util.DRY_RUN:
        for h in hosts:
            key = _key_path(h["email"], node)
            print(f"[ssh] Host {h['alias']} → {h['hostname']} key={key.name}")
        return

    _SSH_DIR.mkdir(mode=0o700, exist_ok=True)

    blocks = []
    for h in hosts:
        key = _key_path(h["email"], node)
        blocks.append(f"Host {h['alias']}\n  HostName {h['hostname']}\n  IdentityFile {key}\n  User {h['user']}")
    blocks.append(_HOST_STAR)

    status = util.ensure_block(_SSH_CONFIG, "ssh", "\n\n".join(blocks))
    _SSH_CONFIG.chmod(0o600)
    print(f"[ssh] config: {status}")


@task
def forward(c):
    """Copy public keys to remote (non-git) server hosts from identity.toml."""
    identity = util.load_identity()
    server_hosts = [h for h in identity.get("ssh_hosts", []) if h["user"] != "git"]
    node = _node()

    if not server_hosts:
        print("[ssh] no server hosts to forward keys to")
        return

    for h in server_hosts:
        pub = Path(str(_key_path(h["email"], node)) + ".pub")
        if not pub.exists():
            print(f"[ssh] missing public key for {h['email']} — run inv ssh.keys first")
            continue
        c.run(f'ssh-copy-id -f -i "{pub}" "{h["user"]}@{h["alias"]}"', pty=True)


@task
def add(c):
    """Add all SSH keys for this node to ssh-agent."""
    node = _node()
    pattern = str(_SSH_DIR / f"*{node}_ed25519")
    c.run(f"ssh-add {pattern}", warn=True)
