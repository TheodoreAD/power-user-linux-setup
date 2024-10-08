# GNOME extensions

## Ubuntu 24.04

Sadly, GNOME extensions are now to be installed via browser extension.

Chrome is recommended, since Firefox is now installed via snap and has issues.

Install the browser extension:

https://chromewebstore.google.com/detail/gnome-shell-integration/gphhapmejobijbbhgpjhcjognlahblep

Install the native host connector for the browser extension:

https://gnome.pages.gitlab.gnome.org/gnome-browser-integration/pages/installation-guide.html

```shell
sudo apt update
sudo apt install -y gnome-browser-connector
```

Install:

- Dash to Panel
    - https://extensions.gnome.org/extension/1160/dash-to-panel/
    - https://github.com/home-sweet-gnome/dash-to-panel
- Extension List
    - https://extensions.gnome.org/extension/3088/extension-list/
    - https://github.com/tuberry/extension-list
- Clipboard Indicator
    - https://extensions.gnome.org/extension/779/clipboard-indicator/
    - https://github.com/Tudmotu/gnome-shell-extension-clipboard-indicator
- GTile
    - https://extensions.gnome.org/extension/28/gtile/
    - https://github.com/gTile
- Top Hat
    - https://extensions.gnome.org/extension/5219/tophat/
    - https://github.com/fflewddur/tophat
- Vitals
    - https://extensions.gnome.org/extension/1460/vitals/
    - https://github.com/corecoding/Vitals
- Lock Keys
    - https://extensions.gnome.org/extension/36/lock-keys/
    - https://github.com/kazysmaster/gnome-shell-extension-lockkeys
- Switcher
    - https://extensions.gnome.org/extension/973/switcher/
    - https://github.com/daniellandau/switcher
- Arc Menu
  - https://extensions.gnome.org/extension/3628/arcmenu/
  - https://gitlab.com/arcmenu/ArcMenu

Not tested yet:

- System Monitor Next
    - https://extensions.gnome.org/extension/3010/system-monitor-next/
    - https://github.com/mgalgs/gnome-shell-system-monitor-applet
- Freon ??? is this up-to-date ???
    - https://extensions.gnome.org/extension/841/freon/
    - https://github.com/UshakovVasilii/gnome-shell-extension-freon
- Removable Drive Menu ??? is this working ???
    - https://extensions.gnome.org/extension/7/removable-drive-menu/
- Smart Auto Move
    - https://extensions.gnome.org/extension/4736/smart-auto-move/
    - https://github.com/khimaros/smart-auto-move
- Auto Move Windows ??? is this deprecated ???
    - https://extensions.gnome.org/extension/16/auto-move-windows/
    - https://gitlab.gnome.org/GNOME/gnome-shell-extensions
- Light Dict
    - https://extensions.gnome.org/extension/2959/light-dict/
    - https://github.com/tuberry/light-dict

## Ubuntu 20.04

!!! WARNING
    Everything below is tested only for 20.04, do NOT install in 24.04.

!!! TODO
    Review entire section

https://bazel.build/install/ubuntu

```shell
curl -sS -L https://bazel.build/bazel-release.pub.gpg \
  | gpg --dearmor >/usr/share/keyrings/bazel-archive-keyring.gpg
echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/bazel-archive-keyring.gpg] \
  https://storage.googleapis.com/bazel-apt stable jdk1.8" \
  | sudo tee /etc/apt/sources.list.d/bazel.list
sudo apt update
sudo apt install -y bazel

EXTENSIONS_TO_INSTALL=(
  gnome-tweaks
  gnome-shell-extensions
)

EXTENSIONS_TO_INSTALL_AND_ENABLE=(
  gnome-shell-extension-dash-to-panel
  gnome-shell-extension-disconnect-wifi
  gnome-shell-extension-weather
  gnome-shell-extension-remove-dropdown-arrows
  gnome-shell-extension-system-monitor
  gnome-shell-extension-show-ip
  # gnome-shell-extensions-gpaste
  gnome-shell-extension-arc-menu
)

EXTENSIONS_TO_ENABLE=(
  # from gnome-shell-extensions
  # Lets you reach an application using gnome 2.x style menu on the panel.
  #apps-menu \
  # Lets you manage your workspaces more easily, assigning a specific workspace to
  # each application as soon as it creates a window, in a manner configurable with a
  # GSettings key.
  auto-move-windows
  # Shows a status menu for rapid unmount and power off of external storage devices
  # (i.e. pendrives)
  drive-menu
  # Changes application icons to always launch a new instance when activated.
  #launch-new-instance \
  # An alternative algorithm for layouting the thumbnails in the windows overview, that
  # more closely reflects the actual positions and sizes.
  native-window-placement
  # Shows a status Indicator for navigating to Places.
  places-menu
  # Adds a shortcut for resizing the focus window to a size that is suitable for GNOME Software screenshots
  #screenshot-window-sizer \
  # Loads a shell theme from ~/.themes//gnome-shell.
  #user-theme \
  # Adds a bottom panel with a traditional window list.
  #window-list \
  # Allow keyboard selection of windows and workspaces in overlay mode.
  #windowsNavigator \
  # Adds a simple workspace switcher to the top bar.
  #workspace-indicator \
)

for ext in ${EXTENSIONS_TO_INSTALL[@]} ${EXTENSIONS_TO_INSTALL_AND_ENABLE[@]}; do
  sudo apt install -y --allow-downgrades "${ext}"
done

for ext in ${EXTENSIONS_TO_INSTALL_AND_ENABLE[@]} ${EXTENSIONS_TO_ENABLE[@]}; do
  gnome-extensions enable "${ext}"
done

GNOME_EXTENSIONS_DIR="${HOME}/.local/share/gnome-shell/extensions"
mkdir -p "${GNOME_EXTENSIONS_DIR}"

function get_uri_last_token_without_extension() {
  repo_url=${1}
  printf ${repo_url} | rev | cut -d '/' -f 1 | rev | cut -d '.' -f 1
}

# alternate version which doesn't end in newline
function get_uri_last_token_without_extension__alt() {
  repo_url=${1}
  last_token=${repo_url##*/}
  printf ${last_token/%.*/}
}

function install_gnome_extension_from_git_nested() {
  repo_url=${1}
  extension_key=${2}
  temp_repo_dir="$(mktemp -d)"
  git clone "${repo_url}" "${temp_repo_dir}"
  rm -v -rf "${GNOME_EXTENSIONS_DIR}/${extension_key}"
  cp -v -r "${temp_repo_dir}/${extension_key}" "${GNOME_EXTENSIONS_DIR}"
  rm -v -rf "${temp_repo_dir}"
  enable_gnome_extension ${extension_key}
}

function install_gnome_extension_from_git_root() {
  repo_url=${1}
  extension_key=${2}
  rm -v -rf "${GNOME_EXTENSIONS_DIR}/${extension_key}"
  # not clear, though unlikely, if .git being in the install dir is a problem
  git clone "${repo_url}" "${GNOME_EXTENSIONS_DIR}/${extension_key}"
  enable_gnome_extension "${extension_key}"
}

function enable_gnome_extension() {
  extension_key=${1}
  gnome-extensions enable "${extension_key}"
}

# TODO: description
install_gnome_extension_from_git_nested "https://github.com/petres/gnome-shell-extension-extensions.git" "extensions@abteil.org"
# TODO: description
install_gnome_extension_from_git_nested "https://github.com/kgshank/gse-sound-output-device-chooser.git" "sound-output-device-chooser@kgshank.net"
# TODO: description
install_gnome_extension_from_git_nested "https://github.com/kazysmaster/gnome-shell-extension-lockkeys.git" "lockkeys@vaina.lt"
# TODO: description
install_gnome_extension_from_git_root "https://github.com/Tudmotu/gnome-shell-extension-clipboard-indicator.git" "clipboard-indicator@tudmotu.com"
# TODO: description
install_gnome_extension_from_git_root "https://github.com/daniellandau/switcher.git" "switcher@landau.fi"

function install_gnome_shell_extension_freon() {
    repo_url="https://github.com/UshakovVasilii/gnome-shell-extension-freon.git"
    extension_key="freon@UshakovVasilii_Github.yahoo.com"
    temp_repo_dir="$(mktemp -d)"
    git clone "${repo_url}" "${temp_repo_dir}"
    glib-compile-schemas "${temp_repo_dir}/${extension_key}/schemas/"
    rm -v -rf "${GNOME_EXTENSIONS_DIR}/${extension_key}"
    cp -v -r "${temp_repo_dir}/${extension_key}" "${GNOME_EXTENSIONS_DIR}"
    rm -v -rf "${temp_repo_dir}"
    enable_gnome_extension "${extension_key}"
}
# TODO: description
install_gnome_shell_extension_freon

function install_gnome_shell_extension_gtile() {
    repo_url="https://github.com/gTile/gTile.git"
    extension_key="gTile@vibou"
    temp_repo_dir="$(mktemp -d)"
    git clone "${repo_url}" "${temp_repo_dir}"
    bazel run :install-extension "${temp_repo_dir}"
    rm -v -rf "${GNOME_EXTENSIONS_DIR}/${extension_key}"
    cp -v -r "${temp_repo_dir}/${extension_key}" "${GNOME_EXTENSIONS_DIR}"
    rm -v -rf "${temp_repo_dir}"
    enable_gnome_extension "${extension_key}"
}
# TODO: description
install_gnome_shell_extension_gtile
```

For the weather extension, see <https://home.openweathermap.org/api_keys>.

!!! WARNING
    This causes some scaled windows to display as if unscaled.

To use extensions right away, press ++alt+f2++ , ++r++ , ++enter++ .

!!! WARNING
    Supposedly this is the command line equivalent, avoid since it can crash the system:

    ```shell
    gnome-shell --replace
    ```

To verify state of all extensions:

```shell
gnome-extensions list | xargs -I{} gnome-extensions info {}
```

## Superseded

Extensions that are no longer used in favor of a better alternative.
Left as a backup and for reference.


```shell
# TODO: description
#curl -sS -L -O https://extensions.gnome.org/extension-data/world_clock_liteailin.nemui.v9.shell-extension.zip

install_gnome_extension_from_git_root "https://github.com/jwendell/gnome-shell-extension-timezone.git" "timezone@jwendell"
# set the path to people.json in the extension settings
TIMEZONE_EXTENSION_DIR="${HOME}/.config/gnome-shell-extension-timezone"
mkdir -p "$TIMEZONE_EXTENSION_DIR"
# include "avatar": "<url>/avatar.jpg" in the list of attributes below
# or "gravatar" with email registered at gravatar.com or libravatar.org
tee -a "$TIMEZONE_EXTENSION_DIR/people.json" > /dev/null <<EOF
[
  {
    "name": "Jim",
    "city": "NYC",
    "tz": "America/New_York"
  },
  {
    "name": "Hans",
    "city": "Berlin",
    "tz": "Europe/Berlin"
  },
  {
    "name": "Chris",
    "city": "San Jose",
    "tz": "America/Los_Angeles"
  },
  {
    "name": "Singh",
    "city": "Bangalore",
    "tz": "Asia/Kolkata"
  }
]
EOF
```

Disabled in favor of `gnome-shell-extension-system-monitor`:

```shell
REPO_URL="https://github.com/hedayaty/NetSpeed.git"
REPO_NAME=$(get_uri_last_token_without_extension ${REPO_URL})
git clone "${REPO_URL}" "/tmp/${REPO_NAME}"
cd "/tmp/${REPO_NAME}" && make && make enable
rm -rf "/tmp/${REPO_NAME}"
```

## Not yet evaluated

!!! TODO
    Evaluate and decide to keep or discard.

```shell
gnome-shell-extension-autohidetopbar
gnome-shell-extension-bluetooth-quick-connect
gnome-shell-extension-dashtodock
gnome-shell-extension-easyscreencast
gnome-shell-extension-gsconnect-browsers
gnome-shell-extension-gsconnect
gnome-shell-extension-hard-disk-led
gnome-shell-extension-hide-activities
gnome-shell-extension-hide-veth
gnome-shell-extension-impatience
gnome-shell-extension-kimpanel
gnome-shell-extension-log-out-button
gnome-shell-extension-move-clock
gnome-shell-extension-multi-monitors
gnome-shell-extension-no-annoyance
gnome-shell-extension-onboard
gnome-shell-extension-pixelsaver
gnome-shell-extension-redshift
gnome-shell-extension-shortcuts
gnome-shell-extension-suspend-button
gnome-shell-extension-tilix-dropdown
gnome-shell-extension-tilix-shortcut
gnome-shell-extension-top-icons-plus
gnome-shell-extension-trash
gnome-shell-extension-workspaces-to-dock

gnome-shell-extension-appindicator
gnome-shell-extension-caffeine
gnome-shell-extension-desktop-icons
gnome-shell-extension-draw-on-your-screen
gnome-shell-extension-gamemode
gnome-shell-extension-hijra
gnome-shell-extension-prefs
gnome-shell-extension-ubuntu-dock
gnome-shell-extension-xrdesktop
```


To get all the extensions in apt:

```shell
apt search gnome-shell-extension --names-only | grep 'gnome.*\w/\w' | cut -d'/' -f1
```


!!! TODO:
    Enable NetSpeed.
