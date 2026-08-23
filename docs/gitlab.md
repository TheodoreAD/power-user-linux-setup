# GitLab

Install `glab` (GitLab CLI) — declared in `setup.toml` as `[packages.glab]`, `method = "deb-url"`
with a `version_cmd` that resolves the latest release via the GitLab API (GitLab's own releases
aren't mirrored to GitHub, so `deb-github` doesn't apply here):

```shell
inv apt.install-debs
```

## Config

```shell
glab config set -h gitlab.com git_protocol ssh
glab config set -h gitlab.com api_protocol https
glab config set pager "less --quit-if-one-screen"
glab config set editor "code --wait"
```

## Completions

```shell
glab completion -s zsh \
  | sudo -A tee "/usr/local/share/zsh/site-functions/_glab" >/dev/null
```

## Connect

Log in to gitlab.com via SSH key using web authentication:

```shell
# select Web auth, SSH as default Git protocol, follow browser prompt
glab auth login --hostname gitlab.com
```

## Add SSH key

```shell
# list existing keys first to avoid duplicates
glab ssh-key list
glab ssh-key add ~/.ssh/<your_key>.pub --title "$(uname -n)"
```
