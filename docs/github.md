# GitHub

<https://github.com/cli/cli/blob/trunk/docs/install_linux.md>

!!! WARNING
    Do NOT use `snap`: <https://github.com/cli/cli/blob/trunk/docs/install_linux.md#snap-do-not-use>

## gh (GitHub CLI tool)

!!! INFO
    Use the apt version unless you prefer updating manually.

=== "apt"

    ```shell
    # add the official GPG key to the keyring and ensure it has the right permissions
    KEY_FILE=/etc/apt/keyrings/githubcli-archive-keyring.gpg
    sudo curl -sS -L https://cli.github.com/packages/githubcli-archive-keyring.gpg -o ${KEY_FILE}
    sudo chmod a+r ${KEY_FILE}
    # add the repository to Apt sources
    ARCH=$(dpkg --print-architecture)
    REPO_URL=https://cli.github.com/packages
    LIST_NAME=github-cli
    echo "deb [arch=${ARCH} signed-by=${KEY_FILE}] ${REPO_URL} stable main" \
      | sudo tee /etc/apt/sources.list.d/${LIST_NAME}.list > /dev/null
    sudo apt update
    sudo apt install -y gh
    ```

=== "deb"

    ```shell
    GH_DEB="$(mktemp)"
    VERSION=$(
      curl "https://api.github.com/repos/cli/cli/releases/latest" \
        | grep '"tag_name"' \
        | sed -E 's/.*"([^"]+)".*/\1/' \
        | cut -c2-
    )
    GH_URL="https://github.com/cli/cli/releases/download/v${VERSION}/gh_${VERSION}_linux_amd64.deb"
    curl -sS -L -o "${GH_DEB}" "${GH_URL}"
    sudo dpkg -i "${GH_DEB}"
    rm "${GH_DEB}"
    ```

=== "github"

    ```shell
    VERSION=$(
      curl "https://api.github.com/repos/cli/cli/releases/latest" \
        | grep '"tag_name"' \
        | sed -E 's/.*"([^"]+)".*/\1/' \
        | cut -c2-
    )
    URL="https://github.com/cli/cli/releases/download/v${VERSION}/gh_${VERSION}_linux_amd64.tar.gz"
    curl -sSL "${URL}" | tar -v -xz --directory "/tmp"
    SETUP_DIR="/tmp/gh_${VERSION}_linux_amd64"
    sudo cp "${SETUP_DIR}/bin/gh" "/usr/local/bin/"
    gzip -k "${SETUP_DIR}/share/man/man1/"*
    sudo cp -r "${SETUP_DIR}/share/man/man1/"*.gz "/usr/share/man/man1/"
    rm -rf "${SETUP_DIR}"
    ```

Config:

```shell
gh config set pager "less --quit-if-one-screen"
gh config set editor "code --wait"
```

Completions:

```shell
# requires .zshrc to contain: autoload -U compinit && compinit
gh completion -s zsh \
  | sudo tee "/usr/local/share/zsh/site-functions/_gh" >/dev/null
```

Log gh in to github.com via ssh key using web authentication:
- run the command below
- select the appropriate key
- copy the key name from the selected SSH file
- paste the key name when asked about the SSH key name in GitHub
- perform web auth following instructions in the terminal

```shell
gh auth login --hostname github.com --git-protocol ssh --web
```
