import os
import re
import subprocess
from pathlib import Path

from invoke import Context, task

from . import util

_SSH_DIR = Path.home() / ".ssh"
SSH_CONFIG = _SSH_DIR / "config"

# `ssh-add -l` exit codes. 1 and 2 look alike from a failed command but mean opposite things:
# 1 is a healthy agent holding nothing, 2 is no agent reachable at all. Telling them apart is the
# whole point of ssh.check — a shell on a live-but-empty agent is the failure this module exists
# to diagnose, and it presents as "Permission denied (publickey)" rather than as a missing agent.
AGENT_HAS_KEYS = 0
AGENT_EMPTY = 1
AGENT_UNREACHABLE = 2

_AGENT_LABELS = {
    AGENT_HAS_KEYS: "holds keys",
    AGENT_EMPTY: "alive, no keys",
    AGENT_UNREACHABLE: "not reachable",
}


def agent_label(code: int) -> str:
    """Human label for an `ssh-add -l` exit code."""
    return _AGENT_LABELS.get(code, f"unknown (exit {code})")


def desktop_sockets(runtime_dir: str | None) -> list[Path]:
    """The well-known desktop agent sockets, in the order ~/.zprofile tries them.

    Kept in step with `[packages.ssh]`'s zprofile snippet in setup.toml: gnome-keyring first,
    gcr second. Both are usually the same agent reached by two paths, but only one of them
    exists on some sessions.
    """
    if not runtime_dir:
        return []
    base = Path(runtime_dir)
    return [base / "keyring" / "ssh", base / "gcr" / "ssh"]


def parse_identity_files(config_text: str) -> list[Path]:
    """Every `IdentityFile` path declared in an ssh_config, in order, deduplicated.

    This is what `ssh` itself consults, which makes it the only correct source for "which keys
    does this machine use" — a glob over ~/.ssh guesses at a naming convention instead, and gets
    it wrong on any machine whose keys `inv ssh.create-keys` did not mint (see docs/ssh.md).
    """
    found: list[Path] = []
    for line in config_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        m = re.match(r"(?i)^identityfile\s+(.+?)\s*$", stripped)
        if not m:
            continue
        raw = m.group(1).strip().strip('"')
        path = Path(raw.replace("${HOME}", "~")).expanduser()
        if path not in found:
            found.append(path)
    return found


def parse_fingerprints(ssh_add_output: str) -> set[str]:
    """The SHA256 fingerprints in `ssh-add -l` output.

    Fingerprints rather than filenames because that is all an agent knows — a loaded key has no
    path, so comparing by name would re-add a key the agent already holds under a different one.
    """
    return {m.group(1) for m in re.finditer(r"\b(SHA256:[A-Za-z0-9+/=]+)", ssh_add_output)}


HOST_STAR = """\
Host *
  IgnoreUnknown AddKeysToAgent
  AddKeysToAgent yes
  PreferredAuthentications publickey,keyboard-interactive,password,hostbased,gssapi-with-mic
  IdentitiesOnly yes
  ServerAliveInterval 300
  ServerAliveCountMax 3"""


def current_node() -> str:
    return subprocess.run(["uname", "-n"], capture_output=True, text=True, check=False).stdout.strip()


def key_path(email: str, node: str) -> Path:
    return _SSH_DIR / f"{email}__{node}_ed25519"


@task
def create_keys(c: Context):
    """Create ed25519 SSH keys for each unique email in identity.toml (skips existing)."""
    identity = util.load_identity()
    hosts = identity.get("ssh_hosts", [])
    emails = sorted({h["email"] for h in hosts})
    node = current_node()

    if util.DRY_RUN:
        for email in emails:
            key = key_path(email, node)
            status = util.ok_label(key.exists())
            print(f"[ssh] key {key.name}: {status}")
        return

    _SSH_DIR.mkdir(mode=0o700, exist_ok=True)
    for email in emails:
        key = key_path(email, node)
        if key.exists():
            print(f"[ssh] key exists: {key.name}")
            continue
        print(f"[ssh] creating key for {email}:")
        util.run_interactive(["ssh-keygen", "-t", "ed25519", "-C", f"{email}__{node}", "-f", str(key)])


@task
def configure(c: Context):
    """Write ~/.ssh/config from identity.toml (idempotent PULSE block)."""
    identity = util.load_identity()
    hosts = identity.get("ssh_hosts", [])
    node = current_node()

    if util.DRY_RUN:
        for h in hosts:
            key = key_path(h["email"], node)
            print(f"[ssh] Host {h['alias']} → {h['hostname']} key={key.name}")
        return

    _SSH_DIR.mkdir(mode=0o700, exist_ok=True)

    blocks: list[str] = []
    for h in hosts:
        key = key_path(h["email"], node)
        blocks.append(f"Host {h['alias']}\n  HostName {h['hostname']}\n  IdentityFile {key}\n  User {h['user']}")
    blocks.append(HOST_STAR)

    status = util.ensure_block(SSH_CONFIG, "ssh", "\n\n".join(blocks))
    SSH_CONFIG.chmod(0o600)
    print(f"[ssh] config: {status.value}")


@task
def forward(c: Context):
    """Copy public keys to remote (non-git) server hosts from identity.toml."""
    identity = util.load_identity()
    server_hosts = [h for h in identity.get("ssh_hosts", []) if h["user"] != "git"]
    node = current_node()

    if not server_hosts:
        print("[ssh] no server hosts to forward keys to")
        return

    for h in server_hosts:
        pub = Path(str(key_path(h["email"], node)) + ".pub")
        if not pub.exists():
            print(f"[ssh] missing public key for {h['email']} — run inv ssh.create-keys first")
            continue
        util.run_interactive(["ssh-copy-id", "-f", "-i", str(pub), f"{h['user']}@{h['alias']}"], check=False)


def _probe_agent(sock: str | None) -> int:
    """`ssh-add -l` against one socket, returning its exit code. `None` uses the ambient one."""
    env = dict(os.environ)
    if sock is not None:
        env["SSH_AUTH_SOCK"] = sock
    return subprocess.run(["ssh-add", "-l"], capture_output=True, text=True, check=False, env=env).returncode


def _agent_identities(sock: str | None) -> str:
    env = dict(os.environ)
    if sock is not None:
        env["SSH_AUTH_SOCK"] = sock
    return subprocess.run(["ssh-add", "-l"], capture_output=True, text=True, check=False, env=env).stdout


def _declared_keys() -> list[Path]:
    """Private keys this machine actually uses, from ~/.ssh/config, newest source of truth first."""
    if not SSH_CONFIG.exists():
        return []
    return parse_identity_files(SSH_CONFIG.read_text())


def _pub_fingerprint(key: Path) -> str | None:
    """Fingerprint from the key's .pub sibling — never the private key, which can prompt."""
    pub = Path(f"{key}.pub")
    if not pub.exists():
        return None
    out = subprocess.run(["ssh-keygen", "-lf", str(pub)], capture_output=True, text=True, check=False)
    fingerprints = parse_fingerprints(out.stdout)
    return next(iter(fingerprints), None)


@task
def check(c: Context):
    """Diagnose which ssh-agent this shell talks to and whether it holds the declared keys.

    Read-only — never starts an agent, never loads a key, never prompts. This is the command to
    run when git says `Permission denied (publickey)`: a desktop session has more than one agent,
    and a shell pinned to the empty one fails exactly that way while the keys sit unlocked in the
    other. See docs/ssh.md "Which agent a shell talks to".
    """
    ambient = os.environ.get("SSH_AUTH_SOCK")
    ambient_code = _probe_agent(None)
    print(f"[ssh] this shell: {ambient or '(SSH_AUTH_SOCK unset)'} — {agent_label(ambient_code)}")

    better: Path | None = None
    for sock in desktop_sockets(os.environ.get("XDG_RUNTIME_DIR")):
        if not sock.is_socket():
            print(f"[ssh] {sock}: absent")
            continue
        code = _probe_agent(str(sock))
        print(f"[ssh] {sock}: {agent_label(code)}")
        if code == AGENT_HAS_KEYS and str(sock) != ambient:
            better = better or sock

    keys = _declared_keys()
    if not keys:
        print(f"[ssh] no IdentityFile entries in {SSH_CONFIG} — run inv ssh.configure")
    else:
        loaded = parse_fingerprints(_agent_identities(ambient))
        print(f"[ssh] declared keys ({SSH_CONFIG}): {len(keys)}")
        for key in keys:
            if not key.exists():
                print(f"[ssh]   MISSING     {key.name}")
                continue
            fp = _pub_fingerprint(key)
            if fp is None:
                print(f"[ssh]   no .pub     {key.name}")
            else:
                print(f"[ssh]   {'loaded     ' if fp in loaded else 'NOT LOADED '} {key.name}")

    if ambient_code == AGENT_HAS_KEYS:
        print("[ssh] verdict: this shell's agent holds keys — nothing to do")
    elif better is not None:
        print(
            f"[ssh] verdict: this shell's agent has no keys but {better} does. A new login shell "
            "picks the right one (see [packages.ssh]'s zprofile snippet); to fix this shell only, "
            f"export SSH_AUTH_SOCK={better}"
        )
    else:
        print("[ssh] verdict: no agent here holds keys — inv ssh.add loads them")


@task
def add(c: Context):
    """Add this machine's SSH keys to the agent, skipping any it already holds."""
    keys = _declared_keys()
    source = str(SSH_CONFIG)
    if not keys:
        # No config to read: fall back to a glob, and cover both algorithms rather than assuming
        # ssh.create-keys minted these. A machine adopting PULSE onto an existing home directory
        # usually has neither this repo's naming nor its key type.
        node = current_node()
        keys = sorted(p for pat in (f"*{node}_ed25519", f"*{node}_rsa") for p in _SSH_DIR.glob(pat))
        source = f"{_SSH_DIR}/*{node}_{{ed25519,rsa}}"

    if not keys:
        print(
            f"[ssh] no keys found via {source}. `inv ssh.configure` writes the IdentityFile "
            "entries this reads; `inv ssh.create-keys` mints ed25519 keys. A machine whose keys "
            "predate this repo may simply need them named in ~/.ssh/config."
        )
        return

    if _probe_agent(None) == AGENT_UNREACHABLE:
        print("[ssh] no agent reachable — open a new login shell first, or start one with `keychain`")
        return

    loaded = parse_fingerprints(_agent_identities(None))
    present = [k for k in keys if k.exists()]
    # A key with no .pub sibling cannot be fingerprinted without its passphrase, so whether the
    # agent already holds it is undecidable — it stays pending and costs one prompt per run.
    # Naming it beats leaving the user wondering why one key keeps asking.
    unknown = [k for k in present if _pub_fingerprint(k) is None]
    pending = [k for k in present if _pub_fingerprint(k) not in loaded]
    skipped = len(present) - len(pending)
    if skipped:
        print(f"[ssh] already loaded: {skipped} key(s)")
    for key in unknown:
        print(f"[ssh] {key.name}: no .pub sibling — cannot tell if it is loaded, will try")
    if not pending:
        print("[ssh] every declared key is already in the agent — nothing to do")
        return

    if util.DRY_RUN:
        for key in pending:
            print(f"[ssh] would add {key.name}")
        return

    # One passphrase prompt per key, and ssh-add retries three times per key before giving up —
    # so this is deliberately not run by any composite task. See docs/ssh.md.
    for key in pending:
        util.run_interactive(["ssh-add", str(key)], check=False)
