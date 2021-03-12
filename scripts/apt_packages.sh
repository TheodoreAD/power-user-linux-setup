# to generate uniform locale settings:
# export LANGUAGE=en_US.UTF-8
# export LANG=en_US.UTF-8
# export LC_ALL=en_US.UTF-8
# locale-gen en_US.UTF-8
# to configure dpkg:
# dpkg-reconfigure locales

# TODO: make this stick after reboot
sudo tee "/etc/default/locale" >/dev/null <<EOF
LANG=en_US.UTF-8
LANGUAGE=en_US.UTF-8
LC_CTYPE="en_US.UTF-8"
LC_NUMERIC="en_US.UTF-8"
LC_TIME="en_US.UTF-8"
LC_COLLATE="en_US.UTF-8"
LC_MONETARY="en_US.UTF-8"
LC_MESSAGES="en_US.UTF-8"
LC_PAPER="en_US.UTF-8"
LC_NAME="en_US.UTF-8"
LC_ADDRESS="en_US.UTF-8"
LC_TELEPHONE="en_US.UTF-8"
LC_MEASUREMENT="en_US.UTF-8"
LC_IDENTIFICATION="en_US.UTF-8"
LC_ALL=en_US.UTF-8
EOF

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
  # ???
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
  # xautolock \
  xidle \
  # very old version, even in 20.04, better to install from release
  # gh
  # typo helper - already installed?
  thefuck \
)

sudo apt install -y --allow-downgrades ${PACKAGES}

# TODO: alias 'jq' to 'jq -S' for sorting

# bat alternative to cat
mkdir -p ~/.local/bin
ln -s /usr/bin/batcat ~/.local/bin/bat

# TODO: investigate https://github.com/Tarrasch/zsh-autoenv

# hyperfine benchmark tool
curl -sSL "https://api.github.com/repos/sharkdp/hyperfine/releases/latest" \
  | grep 'browser_download_url.*hyperfine_.*amd64\.deb' \
  | sed -E 's/.*"([^"]+)"\s*$/\1/' \
  | xargs curl -sS -L -o /tmp/hyperfine.deb
sudo dpkg -i /tmp/hyperfine.deb
rm /tmp/hyperfine.deb

# gh (GitHub CLI tool)
function install_gh() {
  VERSION=$(
    curl "https://api.github.com/repos/cli/cli/releases/latest" \
      | grep '"tag_name"' \
      | sed -E 's/.*"([^"]+)".*/\1/' \
      | cut -c2-
  )
  curl -sSL "https://github.com/cli/cli/releases/download/v${VERSION}/gh_${VERSION}_linux_amd64.tar.gz" \
    | tar vxz -C /tmp
  SETUP_DIR="/tmp/gh_${VERSION}_linux_amd64"
  sudo cp ${SETUP_DIR}/bin/gh /usr/local/bin/
  gzip -k ${SETUP_DIR}/share/man/man1/*
  sudo cp -r ${SETUP_DIR}/share/man/man1/*.gz /usr/share/man/man1/
  rm -rf ${SETUP_DIR}
}

# Sidekick browser
TEMP_DEB="$(mktemp)" \
  && wget -O "${TEMP_DEB}" "https://api.meetsidekick.com/downloads/df/linux/deb" \
  && sudo dpkg -i "${TEMP_DEB}"
rm -f "${TEMP_DEB}"

# Google Cloud SDK and CLI
sudo apt update
sudo apt install google-cloud-sdk
sudo apt --only-upgrade install \
  google-cloud-sdk-kpt \
  google-cloud-sdk-datastore-emulator \
  google-cloud-sdk-kubectl-oidc \
  google-cloud-sdk-cbt \
  kubectl \
  google-cloud-sdk \
  google-cloud-sdk-app-engine-python \
  google-cloud-sdk-spanner-emulator \
  google-cloud-sdk-app-engine-java \
  google-cloud-sdk-firestore-emulator \
  google-cloud-sdk-skaffold \
  google-cloud-sdk-cloud-build-local \
  google-cloud-sdk-pubsub-emulator \
  google-cloud-sdk-anthos-auth \
  google-cloud-sdk-minikube \
  google-cloud-sdk-local-extract \
  google-cloud-sdk-app-engine-grpc \
  google-cloud-sdk-config-connector \
  google-cloud-sdk-bigtable-emulator \
  google-cloud-sdk-datalab \
  google-cloud-sdk-app-engine-go \
  google-cloud-sdk-app-engine-python-extras

# https://superuser.com/questions/358749/how-to-disable-ctrlshiftu-in-ubuntu-linux
#
# Problem
# The problem is that with the "Ibus" input method, "Ctrl-shift-u"
#  is by default configured to the "Unicode Code Point" shortcut.
#   You can try this: Type ctrl-shift-u, then an (underlined) u appears.
#   If you then type a unicode code point number in hex
#   (e.g. 21, the ASCII/unicode CP for !) and press enter,
#   it is replaced with the corresponding character.
#
# This shortcut can be changed or disabled using the ibus-setup utility:
#
# Run ibus-setup from the terminal (or open IBus Preferences).
# Go to "Emoji".
# Next to "Unicode code point:", click on the three dots (i.e. ...).
# In the dialog, click "Delete", then "OK".
# Close the IBus Preferences window.
