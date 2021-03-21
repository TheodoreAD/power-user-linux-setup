# Golang

<https://golang.org/doc/install>

<https://www.digitalocean.com/community/tutorials/how-to-install-go-on-ubuntu-18-04>

<https://github.com/golang-standards/project-layout>


!!! WARNING
    If you aren't installing for the first time, remove the go install directory first:
    
    ```shell
    rm -rf "${HOME}/.local/share/go"
    ```

```shell
GO_INSTALL_ROOT="${HOME}/.local/share"
GO_INSTALL_PATH="${GO_INSTALL_ROOT}/go"
GO_PROJECTS_ROOT="${HOME}/go"
mkdir -p "${GO_INSTALL_PATH}" "${GO_PROJECTS_ROOT}"
GOLANG_VERSION=$(curl -sS -L "https://golang.org/VERSION?m=text")
curl -sS -L "https://storage.googleapis.com/golang/${GOLANG_VERSION}.linux-amd64.tar.gz" \
  | tar -zx --directory "${GO_INSTALL_ROOT}"

# Add environment variables to shell startup for persistence
tee -a "${HOME}/.zshrc" >/dev/null <<EOF

# Golang
export GOPATH="${GO_INSTALL_PATH}"
export GOROOT="${GO_PROJECTS_ROOT}"
export PATH="\${PATH}":"\${GOROOT}/bin":"\${GOPATH}/bin"
EOF
```

To enable right away:

```shell
source "${HOME}/.zshrc"
```

To verify:

```shell
go version
```
