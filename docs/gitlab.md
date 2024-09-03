# GitLab

https://gitlab.com/gitlab-org/cli#installation

```shell
DEB_FILE="$(mktemp)"
VERSION=$(
    curl -s "https://gitlab.com/api/v4/projects/gitlab-org%2Fcli/releases/permalink/latest" \
      | tr '\n' ' ' \
      | sed 's/.*"tag_name":\s*"v\([^"]*\)".*/\1/'
)
FILE_URL="https://gitlab.com/gitlab-org/cli/-/releases/v${VERSION}/downloads/glab_${VERSION}_Linux_x86_64.deb"
curl -sS -L -o "${DEB_FILE}" "${FILE_URL}"
sudo dpkg -i "${DEB_FILE}"
rm "${DEB_FILE}"
```

Config:

```shell
# TODO: use glab config set
```

Completions:

```shell
# TODO: use glab completion
```

Log gh in to gitlab.com via ssh key using web authentication:
- run the command below
- choose Web auth
- choose SSH default Git protocol
- perform web auth following instructions in the terminal

```shell
glab auth login --hostname gitlab.com
# TODO: see if the following are useful to run before the command to avoid choosing:
#   glab config set -h gitlab.com git_protocol ssh
#   glab config set -h gitlab.com api_protocol https
# TODO: add ssh key with glab ssh-key add ~/.ssh/my_key.pub --title "my title"
```

!!! TODO
    See why there is no option to select the SSH key during setup.
