# Python

## pip configuration

If you're using a private pypi server, assign its URL to `PIP_INTERNAL_INDEX_URL`
and uncomment the `index-url` lines.

If using and/or building wheels, uncomment the `[wheel]` section.

```shell
PIP_INTERNAL_INDEX_URL=
mkdir -p "${HOME}/.config/pip"
tee -a "${HOME}/.config/pip/pip.conf" >/dev/null <<EOF
[global]
# index-url = ${PIP_INTERNAL_INDEX_URL}
# extra-index-url = https://pypi.org/simple
no-cache-dir = true
disable-pip-version-check = true

[install]
progress-bar = off

# [wheel]
# wheel-dir = /tmp/wheelhouse
# find-links = /tmp/wheelhouse

EOF
```

## pyenv

```shell
curl -sS -L "https://pyenv.run" | bash
tee -a "${HOME}/.zshrc" >/dev/null <<EOF

# pyenv
export PATH="\${HOME}/.pyenv/bin:\$PATH"
eval "\$(pyenv init -)"
eval "\$(pyenv virtualenv-init -)"
EOF
# to enable right away
source "${HOME}/.zshrc"
```

Install Python, create and set a global virtual environment:

```shell
PYENV_VENV_VERSION="3.9.1"
echo pyenv install "${PYENV_VENV_VERSION}"
echo pyenv virtualenv "${PYENV_VENV_VERSION}" "global-${PYENV_VENV_VERSION//.}"
echo pyenv global "global-${PYENV_VENV_VERSION//.}"
```

## System Python 3 additions

### Setup tools

```shell
sudo apt install -y python3-venv python3-pip
/usr/bin/python3 -m pip install --upgrade pip setuptools wheel
```

### Task management

`invoke` is a Python-based better alternative to `make`.
`dotenv` is used together with `invoke` for `.env` file local dev workflows.

Installed globally to avoid installing for every env.

```shell
/usr/bin/python3 -m pip install --upgrade --user invoke python-dotenv
```

A hack in case the system bin location is not on the path, which is unlikely.

```shell
PYENV_VENV_VERSION="3.9.1"
INVOKE_ENABLED_ENV_NAME="my-actual-env-name-391"
sudo ln -s \
  "${HOME}/.pyenv/versions/3.9.1/envs/${INVOKE_ENABLED_ENV_NAME}/bin/invoke" \
  "/usr/bin/invoke"
```

## Poetry

```shell
URL="https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py"
curl -sS -L "${URL}" | python - --no-modify-path
ln -s "${HOME}/.poetry/bin/poetry" "${HOME}/.local/bin/poetry"

# Add plugin to Oh-My-Zsh
mkdir -p "${ZSH}/plugins/poetry"
poetry completions zsh >"${ZSH}/plugins/poetry/_poetry"
```

!!! TODO
    Make this commented out in the original zsh setup, use `sed` to uncomment here.

Enable plugin in ~/.zshrc plugins:

```shell
plugins(
    poetry
    ...
    )
```

## Nuitka

!!! TODO
    Research system python version dependency

```shell
CODENAME=$(grep UBUNTU_CODENAME /etc/os-release | cut -d '=' -f 2)
if [[ "${CODENAME}" == "" ]]; then
  CODENAME=$(lsb_release -c -s)
fi
wget -O - "http://nuitka.net/deb/archive.key.gpg" | sudo apt-key add -
echo "deb http://nuitka.net/deb/stable/${CODENAME} ${CODENAME} main" \
  | sudo tee "/etc/apt/sources.list.d/nuitka.list" >/dev/null
sudo apt update
sudo apt install nuitka
```

!!! WARNING
    only use if not using pyenv, otherwise make a dedicated pyenv virtualenv

```shell
if [[ ! -f "/usr/bin/nuitka" ]]; then
  sudo ln -s /usr/bin/nuitka3 /usr/bin/nuitka
fi
```

!!! TODO
    test

```shell
python -m nuitka --module invoke --include-package=invoke
```
