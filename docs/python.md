# Python

## Setup tools

!!! WARNING
    Use this only if you intend to use the system wide python,
    which is NOT recommended.

```shell
/usr/bin/python3 -m pip install --upgrade "pip~=20.3" setuptools wheel
```

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

`pyenv` handles Python version and virtual environment management.

<https://github.com/pyenv/pyenv>

```shell
curl -sS -L "https://pyenv.run" | bash
ln -s "${HOME}/.pyenv/bin/pyenv" "${HOME}/.local/bin/pyenv"
tee -a "${HOME}/.zshrc" >/dev/null <<EOF

# pyenv
eval "\$(pyenv init -)"
eval "\$(pyenv virtualenv-init -)"
EOF
# to enable right away
source "${HOME}/.zshrc"
```

To update `pyenv`, run:

```shell
pyenv update
```

Install Python, create and set a global virtual environment:

```shell
# TODO: read from prompt
PYENV_VENV_VERSION="3.10.5"
echo pyenv install "${PYENV_VENV_VERSION}"
echo pyenv virtualenv "${PYENV_VENV_VERSION}" "global-${PYENV_VENV_VERSION//.}"
echo pyenv global "global-${PYENV_VENV_VERSION//.}"
```

## Poetry

`poetry` handles package dependency management.

<https://github.com/python-poetry/poetry>

```shell
POETRY_VERSION="1.1.13"
curl -sS -L "https://install.python-poetry.org" | "/usr/bin/python3" - --version ${POETRY_VERSION} --force

# Add plugin to Oh-My-Zsh
# The poetry docs mention using ZSH_CUSTOM instead of ZSH, however the ZSH path contains poetry.plugin.zsh
mkdir -p "${ZSH}/plugins/poetry"
poetry completions zsh >"${ZSH}/plugins/poetry/_poetry"

poetry config virtualenvs.create false
poetry config virtualenvs.in-project true 
```

!!! TODO
    Make this commented out in the original zsh setup, use `sed` to uncomment here.

Enable plugin in ~/.zshrc plugins if not already previously performed:

```shell
plugins(
    poetry
    ...
    )
```

## pipx

`pipx` enables running Python tools from isolated environments.

<https://github.com/pipxproject/pipx>

```shell
/usr/bin/python3 -m pip install --upgrade --user pipx
tee -a "${HOME}/.zshrc" >/dev/null <<EOF

# pipx
eval "\$(register-python-argcomplete pipx)"
EOF
```

## System-wide tools

### invoke and dotenv

`invoke` is a Python-based alternative to `make` focused on task management.
`dotenv` is used together with `invoke` for `.env` file local dev workflows.

<https://github.com/pyinvoke/invoke>
<https://github.com/theskumar/python-dotenv>

We install `dotenv` side-by-side so that the `invoke`-run `tasks.py`
can import `dotenv` and read `.env` files.

```shell
pipx install invoke
pipx inject invoke --include-apps "python-dotenv[cli]"
```

### twine

Twine is a utility for publishing Python packages on PyPI.



### Nox

`Nox` automates testing in multiple Python environments.

<https://github.com/theacodes/nox>

```shell
pipx install nox
```

### mkdocs including material theme

`mkdocs` generates and serves documentation sites based on markdown files.

```shell
pipx install mkdocs-material --include-deps
pipx inject mkdocs-material mkdocs-mermaid2-plugin
```

### yamllint

```shell
pipx install yamllint
```

## Nuitka

!!! WARNING
    Experimental

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
