# SSH

SSH keys, the agent, and the askpass helper — how this machine authenticates with no terminal
attached.

## Identity setup

SSH keys and config are driven by `~/.config/power-user-linux-setup/identity.toml` — a personal file
that is never committed to the repo.

**Quick start** — one email, one key per host you pick (GitHub/GitLab):

```shell
inv identity.init
```

Interactive wizard; walks through name/email and which hosts to key for, and writes `identity.toml`
for you. Pick "advanced" inside it if you need multiple accounts/hosts/aliases from the start (see
[git.md](git.md) for what that looks like).

**Advanced / manual** — for multiple accounts, aliases, or non-git server hosts, copy the example
and hand-edit it:

```shell
mkdir -p ~/.config/power-user-linux-setup
cp config/identity.toml.example ~/.config/power-user-linux-setup/identity.toml
# edit ~/.config/power-user-linux-setup/identity.toml
```

Both paths produce the same `identity.toml` schema, so you can always add more `[[ssh_hosts]]`
entries by hand later — nothing about the simple path locks you out of the advanced features.

Then run the tasks in order:

```shell
inv ssh.create-keys       # create one ed25519 key per unique email (prompts for passphrase per key)
inv ssh.configure  # write ~/.ssh/config (idempotent)
inv ssh.forward    # ssh-copy-id to non-git server hosts (skips GitHub/GitLab)
inv ssh.add        # add this machine's keys to the agent, skipping any it already holds
inv ssh.check      # read-only: which agent this shell uses, and whether it holds those keys
```

`ssh.add` reads the `IdentityFile` entries out of `~/.ssh/config` rather than globbing `~/.ssh` for
a naming convention, so it works on a machine whose keys `ssh.create-keys` did not mint. It skips
keys the agent already holds — comparing fingerprints, since a loaded key has no path — so
re-running it costs no passphrase prompts. It is deliberately not part of any composite task:
`ssh-add` prompts per key and retries three times per key, which is a lot of dialogs to fire at
someone unattended.

**Migrating a machine with an existing hand-written `~/.ssh/config`** (not managed by PULSE, no
sentinel markers): `inv ssh.configure` only _appends_ a new PULSE block via `ensure_block` — it
won't touch or remove existing hand-written blocks. That's safe in general, but if a new `ssh_hosts`
alias collides with an existing hand-written `Host` entry (e.g. both define `github.com`), the old
block wins, since SSH config resolution is first-match-wins per keyword. Check the `ssh_hosts` alias
list against the existing config's `Host` entries for collisions before running this on a machine
with years of accumulated manual SSH config.

## What gets created

**Keys** — one per unique email across your `ssh_hosts` entries, named:

```
~/.ssh/<email>__<hostname>_ed25519
~/.ssh/<email>__<hostname>_ed25519.pub
```

**Config** — `~/.ssh/config` gets a PULSE-managed block with one `Host` entry per `ssh_hosts` entry,
plus a `Host *` default section:

```
Host github.com
  HostName github.com
  IdentityFile ~/.ssh/jane.smith@gmail.com__mymachine_ed25519
  User git

Host github-work
  HostName github.com
  IdentityFile ~/.ssh/jane.smith@work.com__mymachine_ed25519
  User git

Host *
  IgnoreUnknown AddKeysToAgent
  AddKeysToAgent yes
  PreferredAuthentications publickey,keyboard-interactive,password,hostbased,gssapi-with-mic
  IdentitiesOnly yes
  ServerAliveInterval 300
  ServerAliveCountMax 3
```

## Add keys to GitHub / GitLab

After creating keys, upload each public key to the relevant platform:

```shell
# GitHub
gh ssh-key add ~/.ssh/<email>__<hostname>_ed25519.pub --title "$(uname -n)"

# GitLab
glab ssh-key add ~/.ssh/<email>__<hostname>_ed25519.pub --title "$(uname -n)"
```

## Which agent a shell talks to

A desktop session normally runs **two** SSH agents, and picking the wrong one is the failure mode
this section exists to prevent:

| agent                   | socket                         | keys                                    |
| ----------------------- | ------------------------------ | --------------------------------------- |
| `gcr-ssh-agent` (GNOME) | `$XDG_RUNTIME_DIR/keyring/ssh` | unlocked at login, no passphrase prompt |
| `ssh-agent` (keychain)  | `/tmp/ssh-*/agent.<pid>`       | empty until something loads them        |

GNOME publishes its socket through the systemd user environment, so every shell inherits a working
agent for free. `keychain` is still installed — it is what provides an agent on a TTY login or any
session without gnome-keyring — but running it unconditionally **replaces** GNOME's agent with its
own empty one.

`[packages.ssh]`'s `zprofile` snippet (written to `~/.zprofile` by `inv zsh.configure`) picks
whichever agent actually holds keys, and only starts keychain when neither desktop socket does. It
supersedes the hand-written keychain block this page used to recommend; if you still have one,
delete it — two of them means the last one wins, which is how a shell ends up on the empty agent.

**Why it matters (2026-08-28):** after a reboot, a shell pinned to keychain's empty agent failed
`git push` with `Permission denied (publickey)` while all three keys sat unlocked in GNOME's. The
symptom chain — publickey denied, so "no key loaded", so `ssh-add`, so a passphrase prompt — points
at the passphrase, and the passphrase is never involved. Cached `~/.keychain/<host>-sh` files make
it worse: they outlive a reboot, and sourcing one pins the shell to a socket that may be dead or
belong to a fresh, empty agent. Nothing sources them any more.

Diagnose it with:

```shell
inv ssh.check
```

Read-only — it never starts an agent, loads a key, or prompts. It reports which socket this shell is
on, what each desktop socket holds, which declared keys are loaded, and ends with a verdict:

```console
$ inv ssh.check
[ssh] this shell: /tmp/ssh-HXUkhy0Reloe/agent.2497 — alive, no keys
[ssh] /run/user/1000/keyring/ssh: holds keys
[ssh] declared keys (/home/you/.ssh/config): 5
[ssh]   NOT LOADED  you@example.com__HOST_rsa
[ssh] verdict: this shell's agent has no keys but /run/user/1000/keyring/ssh does. A new login
      shell picks the right one; to fix this shell only, export SSH_AUTH_SOCK=/run/user/1000/keyring/ssh
```

By hand it is one `ssh-add -l` per candidate socket — exit 0 with keys, 1 for a live but empty
agent, 2 when it cannot connect. Those two failing codes look alike and mean opposite things, which
is most of why this is worth a task.

**Verified on 24.04 + Wayland (2026-08-08):** the `keychain`-managed `ssh-agent` persists across the
Wayland session — the socket survives from login through the full session, and `AddKeysToAgent yes`
(in the `Host *` block above) adds each key to it on first use. An empty `ssh-add -l` right after
login is expected on that path (keys load lazily on first connection, not eagerly at login) and is
not itself a sign of breakage — but on a desktop session you should be on GNOME's agent, where the
keys are already there.

## Troubleshooting

Fix key permissions if needed:

```shell
chmod 600 ~/.ssh/<keyfile>
chmod 644 ~/.ssh/<keyfile>.pub
```

Change the comment on an existing key:

```shell
ssh-keygen -f ~/.ssh/<keyfile> -o -c -C "new comment"
```

## See also

- [Git](git.md) — the identity these keys belong to
- [GitHub](github.md) — adding a key and testing it
- [Corporate proxy](corporate-proxy.md) — reaching a host through one
