# GitLab

Install `glab` (GitLab CLI):

> **Note:** `glab` is not yet in `setup.toml`. The manual install below works; to add it to PULSE
> declare it as `method = "deb-github"` with `repo = "gitlab-org/cli"`.

```shell
DEB_FILE="$(mktemp)"
VERSION=$(
    curl -s "https://gitlab.com/api/v4/projects/gitlab-org%2Fcli/releases/permalink/latest" \
      | tr '\n' ' ' \
      | sed 's/.*"tag_name":\s*"v\([^"]*\)".*/\1/'
)
FILE_URL="https://gitlab.com/gitlab-org/cli/-/releases/v${VERSION}/downloads/glab_${VERSION}_Linux_x86_64.deb"
curl -sS -L -o "${DEB_FILE}" "${FILE_URL}"
sudo -A dpkg -i "${DEB_FILE}"
rm "${DEB_FILE}"
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
