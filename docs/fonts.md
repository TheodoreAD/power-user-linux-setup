# Fonts

Install nerd fonts, patched with the many glyphs required for a beautiful terminal.

!!! HINT "Troubleshooting"

    When you put the fonts in that specified directory, Ubuntu will automatically start caching.
    After 5-6 seconds, the fonts should appear in listing.
    Close any open application before you want to change the font for it.
    
    Font files should have the permission of `644`, and the containing folder should have `755`.
    If the fonts are missing from listing, check the permissions of those files and folders.

```shell
FONTS_DIR="${HOME}/.local/share/fonts"
mkdir -p "${FONTS_DIR}"

function copy_fonts() {
  font_extension="${1}"
  # exclude Mono and Windows fonts from Nerd Fonts packages
  echo -n "$(
    find ${font_temp_dir} -maxdepth 1 -type f \
      -name "${font_extension}" \
      -not -iname "*windows*" \
      -not -iname "*complete mono.${font_extension}" \
      -exec cp -v "{}" "${FONTS_DIR}" \;
  )"
}

function get_uri_last_token_without_extension() {
  repo_url=${1}
  printf ${repo_url} | rev | cut -d '/' -f 1 | rev | cut -d '.' -f 1
}

function install_font_from_zip_url() {
  font_url="${1}"
  font_archive_name="$(get_uri_last_token_without_extension ${font_url})"
  font_temp_dir="/tmp/${font_archive_name}"
  font_temp_zip_path="${font_temp_dir}/${font_archive_name}.zip"
  mkdir -p "${font_temp_dir}"
  curl -sS -L -o "${font_temp_zip_path}" "${font_url}"
  # -j prevents director creation, i.e. all files end up in unzip root
  unzip -j -o "${font_temp_zip_path}" -d "${font_temp_dir}"
  # install .otf fonts, if found, else .ttf
  otf_output=$(copy_fonts "*.otf")
  if [ ! -z "${otf_output}" ]; then
    echo ${otf_output}
  else
    echo "No .otf files found, trying .ttf."
    ttf_output=$(copy_fonts "*.ttf")
    if [ ! -z "${ttf_output}" ]; then
      echo ${ttf_output}
    else
      echo "No .otf or .ttf files found, nothing copied."
    fi
  fi
  rm -v -rf "${font_temp_dir}"
}

# Nerd Fonts, see https://github.com/ryanoasis/nerd-fonts/releases/latest
NERD_FONT_URLS=(
  "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/SourceCodePro.zip"
  "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.zip"
  "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/Meslo.zip"
  "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/RobotoMono"
  "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/FiraCode"
  "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/FiraMono"
  "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/Ubuntu"
  "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/UbuntuMono"
)
for url in "${NERD_FONT_URLS[@]}"; do
  install_font_from_zip_url ${url}
done

fc-cache -v -f
```
