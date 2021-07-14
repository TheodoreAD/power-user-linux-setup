# GitHub

## gh (GitHub CLI tool)

=== "apt"

    ```shell
    sudo apt-key adv --keyserver "keyserver.ubuntu.com" --recv-key "C99B11DEB97541F0"
    sudo apt-add-repository "https://cli.github.com/packages"
    sudo apt update
    sudo apt install gh
    ```

=== "github"

    ```shell
    function install_gh() {
      VERSION=$(
        curl "https://api.github.com/repos/cli/cli/releases/latest" \
          | grep '"tag_name"' \
          | sed -E 's/.*"([^"]+)".*/\1/' \
          | cut -c2-
      )
      URL="https://github.com/cli/cli/releases/download/v${VERSION}/gh_${VERSION}_linux_amd64.tar.gz"
      curl -sSL "${URL}" | tar vxz -C "/tmp"
      SETUP_DIR="/tmp/gh_${VERSION}_linux_amd64"
      sudo cp "${SETUP_DIR}/bin/gh" "/usr/local/bin/"
      gzip -k "${SETUP_DIR}/share/man/man1/"*
      sudo cp -r "${SETUP_DIR}/share/man/man1/"*.gz "/usr/share/man/man1/"
      rm -rf "${SETUP_DIR}"
    }
    ```

=== "deb"

    !!! TODO
        Get latest version automatically.
    
    ```shell
    GH_DEB="$(mktemp)"
    GH_URL="https://github.com/cli/cli/releases/download/v0.6.4/gh_0.6.4_linux_amd64.deb"
    curl -sS -L -o "${GH_DEB}" "${GH_URL}"
    sudo dpkg -i "${GH_DEB}"
    rm "${GH_DEB}"
    ```

Config:

!!! todo:
    See why editor isn't respected. Creating an issue should open the editor. See:
    
    https://github.com/cli/cli/issues/308

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

Connect:

```shell
# select github.com, SSH, select key, perform auth, allow gh CLI to access github.com
gh auth login
```
