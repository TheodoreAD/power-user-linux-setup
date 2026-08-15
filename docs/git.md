# Git

## Identity setup

Git identity is driven by `~/.config/power-user-linux-setup/identity.toml` — a personal file that is never committed to the repo.

**Quick start** — one name/email, one projects directory:

```shell
inv identity.init
```

Interactive wizard; answer a few prompts and it writes `identity.toml` for you. The projects
directory defaults to `~/projects/` itself (repos go straight in, no subdirectory) — enter an
absolute path (`~` allowed, as many nested directories as you like) if you want somewhere else,
e.g. `~/code/clientA`. Choose the "advanced" option inside it if you want multiple
directories/accounts from the start.

**Advanced / manual** — for multiple directories or accounts, copy the example and hand-edit it:

```shell
mkdir -p ~/.config/power-user-linux-setup
cp config/identity.toml.example ~/.config/power-user-linux-setup/identity.toml
# edit ~/.config/power-user-linux-setup/identity.toml
```

Either way produces the same file format — `inv identity.init`'s simple mode just writes the
minimal instance of it (one `[[git_profiles]]` entry), and you can always add more
`[[git_profiles]]`/`[[ssh_hosts]]` entries by hand later if you outgrow a single identity.

Then apply:

```shell
inv git.configure   # creates each profile's directory + per-dir .gitconfig with includeIf
inv git.settings    # applies global git settings (editor, push, pull, log, etc.)
```

`inv git.configure` disables the global `user.name`/`user.email` and wires up `includeIf.gitdir`
so git automatically picks the right identity based on which projects directory the repo lives in
(`~/projects/<directory>/` for a relative name, or the absolute path itself for a custom location).

This per-directory `.gitconfig`/`includeIf` mechanism has been running unmodified on an existing
machine for a long time, but hasn't yet been validated end-to-end on a genuinely fresh install —
worth confirming the created `.gitconfig` files and the global `includeIf` entries look right the
next time this repo is bootstrapped on a new machine.

## Multi-account platforms

For multiple accounts on the same platform (e.g. two GitHub accounts), use a distinct alias in `identity.toml`:

```toml
[[ssh_hosts]]
user = "git"
alias = "github-work"
hostname = "github.com"
email = "jane.smith@work.com"
```

Then clone via the alias instead of the real hostname:

```shell
git clone git@github-work:org/repo.git
```

SSH will route through the alias and use the correct key. See [ssh.md](ssh.md) for key setup.

## Global configuration

Applied by `inv git.settings`:

| Setting                | Value         | Purpose                                              |
| ---------------------- | ------------- | ---------------------------------------------------- |
| `core.autocrlf`        | `input`       | Normalise CRLF on commit; leave LF alone on checkout |
| `core.fileMode`        | `true`        | Track executable bit                                 |
| `core.ignorecase`      | `false`       | Case-sensitive filenames                             |
| `core.preloadindex`    | `true`        | Parallel index preload for faster diffs              |
| `core.editor`          | `code --wait` | VS Code as commit message editor                     |
| `push.default`         | `current`     | Push current branch to same-name remote branch       |
| `push.autoSetupRemote` | `true`        | Automatically set upstream on first push             |
| `pull.rebase`          | `false`       | Merge on pull (not rebase)                           |
| `rebase.autoStash`     | `true`        | Auto-stash dirty working tree before rebase          |
| `log.decorate`         | `auto`        | Show branch/tag names in `git log`                   |

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
