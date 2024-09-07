# Shortcuts

https://askubuntu.com/questions/597395/how-to-set-custom-keyboard-shortcuts-from-terminal

```shell
# this is consistent with Ubuntu's default screenshot location
flamehost_output_path=${HOME}/Pictures/Screenshots
mkdir -p ${flamehost_output_path}
# Array containing custom shortcut details: name, command, binding
shortcuts=(
  # Examples
  #"Open Terminal" "gnome-terminal" "<Control><Alt>T"
  #"Open File Manager" "nautilus" "<Control><Alt>E"
  # Add more shortcuts here
  # we don't override Ubuntu's Print, <Alt>Print, and <Shift>Print
  # especially <Alt>Print for active windows, which flameshot is missing
  "Flameshot - Capture current screen to file"
    "flameshot screen --path ${flamehost_output_path}"
    "<Control><Shift>Print"
  #"Flameshot - Capture all screens to file"
  #  "flameshot full --path ${flamehost_output_path}"
  #  "<Control><Super><Shift>Print"
  #"Flameshot - Capture region without GUI to file and clipboard"
  #  "flameshot gui --accept-on-select --clipboard --path ${flamehost_output_path}"
  #  "<Control>Print"
  "Flameshot - Capture region with GUI to file and clipboard"
    "flameshot gui --clipboard --path ${flamehost_output_path}"
    "<Control>Print"
)

# Function to create a custom keyboard shortcut
base_module="org.gnome.settings-daemon.plugins.media-keys"
module="${base_module}.custom-keybinding"
create_custom_shortcut() {
  local index="$1"
  local name="$2"
  local command="$3"
  local binding="$4"

  loc="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom${index}/"
  
  # Add the custom shortcut to the list
  existing_bindings=$(gsettings get ${base_module} custom-keybindings)
  if [[ "${existing_bindings}" == "@as []" ]]; then
    new_bindings="['${loc}']"
  else
    new_bindings="${existing_bindings::-1}, '${loc}']"
  fi
  gsettings set ${base_module} custom-keybindings "${new_bindings}"

  # Define the custom shortcut details
  gsettings set "${module}:${loc}" name "${name}"
  gsettings set "${module}:${loc}" command "${command}"
  gsettings set "${module}:${loc}" binding "${binding}"
}

# Loop through the shortcuts array
index=1
while [ $index -lt ${#shortcuts[@]} ]; do
  shortcut_name="${shortcuts[$index]}"
  shortcut_command="${shortcuts[$((index + 1))]}"
  shortcut_binding="${shortcuts[$((index + 2))]}"
  
  create_custom_shortcut \
    $((index / 3)) \
    "${shortcut_name}" \
    "${shortcut_command}" \
    "${shortcut_binding}"

  index=$((index + 3))
done
```
