# SSH

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
inv ssh.add        # add all keys for this machine to ssh-agent
```

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

## Keychain (persistent agent across logins)

`keychain` wraps `ssh-agent` so keys survive across terminal sessions and survive logout/login.

```shell
sudo -A apt install -y keychain
```

Add to `~/.zprofile` (runs once at login, not on every shell):

```shell
eval $(keychain --nogui --quick --quiet --lockwait 0 --agents ssh --eval --confhost)
[ -z "${HOSTNAME}" ] && HOSTNAME=$(uname -n)
[ -f "${HOME}/.keychain/${HOSTNAME}-sh" ] && source "${HOME}/.keychain/${HOSTNAME}-sh"
```

**Verified on 24.04 + Wayland (2026-08-08):** the `keychain`-managed `ssh-agent` persists correctly
across the Wayland session — the agent socket survives from login through the full session, and
`AddKeysToAgent yes` (in the `Host *` block above) adds each key to it on first use. An empty
`ssh-add -l` right after login is expected (keys load lazily on first connection, not eagerly at
login), not a sign of breakage.

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
