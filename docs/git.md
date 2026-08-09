# Git

## Identity setup

Git identity is driven by `~/.config/pulse/identity.toml` — a personal file that is never committed to the repo.

Copy the example and fill in your details:

```shell
mkdir -p ~/.config/pulse
cp config/identity.toml.example ~/.config/pulse/identity.toml
# edit ~/.config/pulse/identity.toml
```

Then apply:

```shell
inv git.configure   # creates ~/projects/<directory>/ + per-dir .gitconfig with includeIf
inv git.settings    # applies global git settings (editor, push, pull, log, etc.)
```

`inv git.configure` disables the global `user.name`/`user.email` and wires up `includeIf.gitdir`
so git automatically picks the right identity based on which `~/projects/<directory>/` the repo lives in.

This per-directory `.gitconfig`/`includeIf` mechanism has been running unmodified on an existing
machine for a long time, but hasn't yet been validated end-to-end on a genuinely fresh install —
worth confirming the created `~/projects/<directory>/.gitconfig` files and the global `includeIf`
entries look right the next time this repo is bootstrapped on a new machine.

## Multi-account platforms

For multiple accounts on the same platform (e.g. two GitHub accounts), use a distinct alias in `identity.toml`:

```toml
[[ssh_hosts]]
user     = "git"
alias    = "github-work"
hostname = "github.com"
email    = "jane.smith@work.com"
```

Then clone via the alias instead of the real hostname:

```shell
git clone git@github-work:org/repo.git
```

SSH will route through the alias and use the correct key. See [ssh.md](ssh.md) for key setup.

## Global configuration

Applied by `inv git.settings`:

| Setting | Value | Purpose |
|---|---|---|
| `core.autocrlf` | `input` | Normalise CRLF on commit; leave LF alone on checkout |
| `core.fileMode` | `true` | Track executable bit |
| `core.ignorecase` | `false` | Case-sensitive filenames |
| `core.preloadindex` | `true` | Parallel index preload for faster diffs |
| `core.editor` | `code --wait` | VS Code as commit message editor |
| `push.default` | `current` | Push current branch to same-name remote branch |
| `push.autoSetupRemote` | `true` | Automatically set upstream on first push |
| `pull.rebase` | `false` | Merge on pull (not rebase) |
| `rebase.autoStash` | `true` | Auto-stash dirty working tree before rebase |
| `log.decorate` | `auto` | Show branch/tag names in `git log` |

## PyCharm diff and merge tools

Run once after installing PyCharm via Toolbox:

```shell
PYCHARM_PATH="${HOME}/.local/share/JetBrains/Toolbox/apps/pycharm/bin/pycharm"
git config --global diff.tool pycharm-professional
git config --global difftool.prompt false
git config --global difftool.pycharm-professional.cmd \
  \""${PYCHARM_PATH}"\"' diff "$LOCAL" "$REMOTE"'
git config --global merge.tool pycharm-professional
git config --global mergetool.prompt false
git config --global mergetool.pycharm-professional.cmd \
  \""${PYCHARM_PATH}"\"' merge "$LOCAL" "$REMOTE" "$BASE" "$MERGED"'
git config --global mergetool.pycharm-professional.keepBackup false
```

!!! WARNING
    The Toolbox path changes on IDE version upgrades — re-run when upgrading PyCharm.
