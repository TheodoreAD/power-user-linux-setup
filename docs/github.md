# GitHub CLI (gh)

Installed via apt-repo by `inv apt.install-repos` (or `inv setup`). Zsh completions are included in
the apt package and loaded automatically by `compinit`.

## Post-install (interactive — run manually)

```shell
# Select: github.com → SSH → pick key → browser auth → allow CLI access
gh auth login
```

## Config

```shell
gh config set pager "less --quit-if-one-screen"
gh config set editor "code --wait"
```
