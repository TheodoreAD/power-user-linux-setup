# Apt packages

# Basic pack

Install these as the very first step, many of them are dependencies.

!!! WARNING
    After the apt commands you might get a list of packages that are considered
    to no longer be required, followed by the following advice:

    ```
    Use 'sudo apt autoremove' to remove them.
    ```

    Do NOT run this unless you know EXACTLY what the involved packages do.

```shell
PACKAGES=()
# build
PACKAGES+=(make build-essential gettext)
# source control
PACKAGES+=(git)
# man pages
PACKAGES+=(manpages-dev man-db manpages-posix-dev)
# editor
PACKAGES+=(vim)
# network
PACKAGES+=(wget curl libpcap-dev libnet1-dev rpcbind openssh-client openssh-server nmap)
# iproute2 is installed by default, but the docs aren't
PACKAGES+=(iproute2-doc)
# includes older utilities, iproute2 is the newer alternative:
#     arp, hostname, ifconfig, netstat, rarp, route,
#     plipconfig, slattach, mii-tool, iptunnel, ipmaddr
PACKAGES+=(net-tools traceroute iftop hping3 vnstat iptraf dstat)
# TODO: find resolvconf replacement
# network fs mounting
PACKAGES+=(cifs-utils)
# docker requirements
PACKAGES+=(apt-transport-https ca-certificates software-properties-common)
# pyenv requirements
# https://github.com/pyenv/pyenv/wiki#suggested-build-environment
PACKAGES+=(
  libssl-dev zlib1g-dev \
  libbz2-dev libreadline-dev libsqlite3-dev  \
  libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev \
  llvm
)
# TODO: find what requires this
PACKAGES+=(python3-openssl)
# TODO: find what requires these, likely python related
PACKAGES+=(libgdbm-dev libnss3-dev)
# python dev
PACKAGES+=(python3-pip python3-venv)
# security
PACKAGES+=(keychain gnupg)
# hardware diagnostics
PACKAGES+=(lm-sensors gir1.2-gtop-2.0 gir1.2-nm-1.0 gir1.2-clutter-1.0)
# system monitor
PACKAGES+=(htop ncdu)
# terminal
PACKAGES+=(terminator tmux xclip)
# file management and search
PACKAGES+=(tree fd-find ripgrep)
# converters
PACKAGES+=(html2text bat jq)
# linting
PACKAGES+=(shellcheck)
# environment variable management
PACKAGES+=(direnv)
# windows compatiblity
PACKAGES+=(dos2unix)
# system configuration (ui)
PACKAGES+=(font-manager)
# idle state management
PACKAGES+=(xidle)
# screenshot and annotation
PACKAGES+=(flameshot)
# typo helper
# TODO: see why thefuck isn't working
# clipboard
PACKAGES+=(gpaste-2)

sudo apt update
sudo apt full-upgrade -y
sudo apt install -y ${PACKAGES[@]}

# TODO: see if this is still an issue
# to solve apt clash due to rust packaging error
# sudo apt install -o Dpkg::Options::="--force-overwrite" bat ripgrep

# symlinks for programs with already claimed binary names
mkdir -p "${HOME}/.local/bin"
ln -s "$(which batcat)" "${HOME}/.local/bin/bat"
ln -s "$(which fdfind)" "${HOME}/.local/bin/fd"
```

!!! TODO
    Configure flameshot and other installed software above.
