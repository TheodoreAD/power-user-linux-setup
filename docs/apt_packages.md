# Apt packages

# Basic pack

Install these as the very first step, many of them are dependencies.

```shell
PACKAGES=(
  # build
  make build-essential gettext
  # source control
  git
  # man pages
  manpages-dev man-db manpages-posix-dev
  # network
  wget curl libpcap-dev libnet1-dev rpcbind openssh-client openssh-server nmap
  # includes older utilities, iproute2 is the newer alternative:
  #     arp, hostname, ifconfig, netstat, rarp, route,
  #     plipconfig, slattach, mii-tool, iptunnel, ipmaddr
  net-tools
  traceroute iftop hping3 vnstat iptraf dstat
  # docker requirements
  apt-transport-https ca-certificates software-properties-common
  # pyenv requirements
  # https://github.com/pyenv/pyenv/wiki/Common-build-problems
  libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev llvm
  libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev
  python-openssl
  # TODO: find what requires these
  libgdbm-dev libnss3-dev
  # python utilities
  python3-distutils
  # security
  keychain
  # system monitor
  htop gir1.2-gtop-2.0 gir1.2-nm-1.0 gir1.2-clutter-1.0
  # terminal
  terminator tmux tree xclip
  # converters
  html2text bat jq
  # linting
  yamllint
  # environment variable management
  direnv
  # windows compatiblity
  dos2unix
  # ui
  gnome-clocks
  # system configuration (ui)
  font-manager
  # idle state management
  # WARNING: superseded by xidle
  # xautolock
  xidle
  # WARNING: very old version, even in 20.04, better to install from release
  # gh
  # typo helper
  thefuck
)

sudo apt update
sudo apt install -y --allow-downgrades ${PACKAGES[@]}

# bat, alternative to cat
mkdir -p "${HOME}/.local/bin"
ln -s "/usr/bin/batcat" "${HOME}/.local/bin/bat"
```

!!! TODO
    See how `${PACKAGES[@]}` and `${PACKAGES}` compare wrt defining the variable.

!!! TODO
    Investigate <https://github.com/Tarrasch/zsh-autoenv>.


## Google Cloud SDK and CLI

!!! TODO
    Add post-install auth instructions.

```shell
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
  | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl "https://packages.cloud.google.com/apt/doc/apt-key.gpg" \
  | sudo apt-key --keyring "/usr/share/keyrings/cloud.google.gpg" add -
sudo apt update
sudo apt install -y google-cloud-sdk
GOOGLE_INSTALL_PACKAGES=(
  google-cloud-sdk-app-engine-python
  google-cloud-sdk-app-engine-python-extras
  google-cloud-sdk-bigtable-emulator
  google-cloud-sdk-cbt
  google-cloud-sdk-cloud-build-local
  google-cloud-sdk-config-connector
  google-cloud-sdk-datalab
  google-cloud-sdk-datastore-emulator
  google-cloud-sdk-firestore-emulator
  google-cloud-sdk-kind
  google-cloud-sdk-kpt
  google-cloud-sdk-kubectl-oidc
  google-cloud-sdk-local-extract
  google-cloud-sdk-minikube
  google-cloud-sdk-pubsub-emulator
  google-cloud-sdk-skaffold
  kubectl
)
sudo apt install -y ${GOOGLE_INSTALL_PACKAGES[@]}
```

Although not essential (see below), `docker-credential-gcr` is missing from apt packages.

<https://github.com/GoogleCloudPlatform/docker-credential-gcr>

> Note: `docker-credential-gcr` is primarily intended for users
> wishing to authenticate with GCR in the absence of `gcloud`,
> though they are not mutually exclusive. For normal development setups,
> users are encouraged to use `gcloud auth configure-docker`, instead.

To later update all the packages:

```shell
GOOGLE_UPDATE_PACKAGES=(
  google-cloud-sdk
  google-cloud-sdk-anthos-auth
  google-cloud-sdk-app-engine-go
  google-cloud-sdk-app-engine-grpc
  google-cloud-sdk-app-engine-java
  google-cloud-sdk-app-engine-python
  google-cloud-sdk-app-engine-python-extras
  google-cloud-sdk-bigtable-emulator
  google-cloud-sdk-cbt
  google-cloud-sdk-cloud-build-local
  google-cloud-sdk-config-connector
  google-cloud-sdk-datalab
  google-cloud-sdk-datastore-emulator
  google-cloud-sdk-firestore-emulator
  google-cloud-sdk-kind
  google-cloud-sdk-kpt
  google-cloud-sdk-kubectl-oidc
  google-cloud-sdk-local-extract
  google-cloud-sdk-minikube
  google-cloud-sdk-pubsub-emulator
  google-cloud-sdk-skaffold
  google-cloud-sdk-spanner-emulator
  kubectl
)
sudo apt install -y --only-upgrade ${GOOGLE_UPDATE_PACKAGES[@]}
```