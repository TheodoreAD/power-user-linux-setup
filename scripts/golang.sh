GOLANG_VERSION="1.16.2"
# Check if golang is installed
current_golang_version_error=$(go version > /dev/null 2>&1)
if [ ! -z "${current_golang_version_error}" ]; then
    GO_INSTALL_PATH="${HOME}/go"
    GO_INSTALL_ROOT="${HOME}/Golang"
    mkdir -p "${GO_INSTALL_PATH}" "${GO_INSTALL_ROOT}"
    curl -sS -L https://storage.googleapis.com/golang/go${GOLANG_VERSION}.linux-amd64.tar.gz \
        | tar --directory "${GO_INSTALL_ROOT}" -zx

    # Add environment variables to shell startup for persistence
    tee -a "${HOME}/.zshrc" > /dev/null \
<<EOF

# Golang
export GOPATH="${GO_INSTALL_PATH}"
export GOROOT="${GO_INSTALL_ROOT}/go"
export PATH="\${PATH}":"\${GOROOT}/bin":"\${GOPATH}/bin"
EOF

    # to enable right away
    source "${HOME}/.zshrc"
fi
