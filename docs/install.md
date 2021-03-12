# Installation steps for Ubuntu 19.10 eoan ermine

```shell script
# disabled -u for unset variables due to weird behavior 
set -ex -o pipefail
```

## Apt Packages - tools and prerequisites

[Script to set up apt packages](../scripts/apt_packages.sh)

## Gnome extensions

[Script to set up gnome extensions](../scripts/gnome_extensions.sh)

## Golang

[Script to set up Golang](../scripts/golang.sh)

## Python tools

[Script to set up Python tools](../scripts/python.sh)

## Fonts

[Script to set up fonts](../scripts/fonts.sh)

## Zsh + Oh My Zsh + PowerLevel10k

[Script to set up Z shell](../scripts/zsh.sh)

### NyanCat for terminal

```shell script
NYANCAT_INSTALL_DIR="${HOME}/.nyancat"
git clone https://github.com/klange/nyancat.git "${NYANCAT_INSTALL_DIR}" && \
    make -C "${NYANCAT_INSTALL_DIR}" && \
    ln -s -f "${NYANCAT_INSTALL_DIR}/src/nyancat" "${USER_BIN_DIR}/nyancat"
```

## SSH

[Script to set up SSH](../scripts/ssh.sh)

## Git

[Script to set up SSH](../scripts/git.sh)

## Browsing

### Google Chrome

```shell script
cd /tmp
CHROME_DEB=google-chrome-stable_current_amd64.deb
curl -sS -Lo "/tmp/${CHROME_DEB}" "https://dl.google.com/linux/direct/${CHROME_DEB}"
sudo dpkg -i "/tmp/${CHROME_DEB}"
```

## Communication

### Franz

```shell script
FRANZ_DEB="franz_5.4.1_amd64.deb"
curl -sS -Lo "/tmp/$FRANZ_DEB" "https://github.com/meetfranz/franz/releases/download/v5.4.1/${FRANZ_DEB}"
sudo dpkg -i "/tmp/${FRANZ_DEB}"
```

### Slack

```shell script
# disabled in favor of franz
# sudo snap install --classic slack
```

## Software Development

### Visual Studio Code

```shell script
sudo snap install --classic code
```

### Pycharm Professional

```shell script
sudo snap install --classic pycharm-professional
```

### Notepad++

```shell script
# not working properly
# sudo snap install notepad-plus-plus
```

#### Alternative - Notepadqq

```shell script
# TODO: install, test, document
# sudo snap install notepadqq
```

## Spotify

```shell script
sudo snap install spotify
```

## File management

### Double Commander

```shell script
sudo apt install -y doublecmd-gtk
```

## Email

### Evolution

```shell script
# TODO: install, test, document
# ??? VERY OLD ???
# !!! repo doesn't work, needs to be specified with older ubuntu release name !!!
# sudo add-apt-repository ppa:fta/gnome3
# sudo apt update
# sudo apt install -y evolution
```

### Thunderbird

```shell script
# TODO: configure, document
```

## Autostart

```shell script
USER_AUTOSTART_DIR="${HOME}/.config/autostart"
APT_AUTOSTART_APPS=( \
    doublecmd \
    terminator \
    google-chrome \
)
for app in "${APT_AUTOSTART_APPS[@]}"; do
    cp -v /usr/share/applications/${app}.desktop ${USER_AUTOSTART_DIR}
done
SNAP_AUTOSTART_APPS=( \
    pycharm-professional_pycharm-professional \
    spotify_spotify \
)
for app in "${SNAP_AUTOSTART_APPS[@]}"; do
    cp -v /var/lib/snapd/desktop/applications/${app}.desktop ${USER_AUTOSTART_DIR}
done

# sample .desktop file creation

# tee -a ${HOME}/.config/autostart/cisco_anyconnect.desktop > /dev/null <<EOF
# [Desktop Entry]
# Type=Application
# Name=Cisco Anyconnect Secure Mobility Client
# Comment=Connect to a private network using the Cisco Anyconnect Secure Mobility Client
# Exec=/opt/cisco/anyconnect/bin/vpnui
# Icon=cisco-anyconnect
# Terminal=false
# Encoding=UTF-8
# StartupNotify=true
# EOF
````

## Fix CRLF

```shell script
# find . -type f | xargs file -k -- | grep CRLF | wc -l
# find . -type f | xargs dos2unix
# chmod go-w -R *
# sudo find . -type f | xargs chmod a-x
```
