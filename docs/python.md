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

`pyenv` handles Python version and virtual environment management.

<https://github.com/pyenv/pyenv-installer?tab=readme-ov-file#installation--update--uninstallation>

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

Install Python via pyenv in user home, create and set a global virtual environment to avoid polluting the system Python:

!!! TODO
    Read version from prompt.

```shell
PYENV_VENV_VERSION="3.11.9"
pyenv install "${PYENV_VENV_VERSION}"
pyenv virtualenv "${PYENV_VENV_VERSION}" "global-${PYENV_VENV_VERSION//.}"
pyenv global "global-${PYENV_VENV_VERSION//.}"
```

## pipx

`pipx` enables running Python tools from isolated environments.

<https://github.com/pypa/pipx?tab=readme-ov-file#install-pipx>

!!! WARNING
    This assumes you have the global pyenv virtualenv indicated above active.

```shell
"$(pyenv which python)" -m pip install --upgrade pipx
ln -s "$(pyenv which pipx)" "${HOME}/.local/bin/pipx"
tee -a "${HOME}/.zshrc" >/dev/null <<EOF

# pipx
eval "\$(register-python-argcomplete pipx)"
EOF
```

## Poetry

`poetry` handles package dependency management.

<https://python-poetry.org/docs/#installing-with-pipx>
<https://python-poetry.org/docs/#zsh>

```shell
pipx install poetry
# Add plugin to Oh-My-Zsh
# The poetry docs mention using $ZSH_CUSTOM instead of $ZSH, however the $ZSH-based path contains poetry.plugin.zsh
poetry completions zsh >"${ZSH}/plugins/poetry/_poetry"
# configure poetry to not create virtual envs, we handle those with pyenv
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

<https://twine.readthedocs.io/en/stable/#installation>

```shell
pipx install twine
```

!!! TODO
    See how to use keyring to publish to PyPI.

### Nox

!!! WARNING
    Optional.

!!! TODO
    See if we want this in the project env, the same as pytest.

`Nox` automates testing in multiple Python environments.

<https://github.com/theacodes/nox>

```shell
pipx install nox
```

### mkdocs including material theme

!!! WARNING
    Optional.

!!! TODO
    See if we want this in the project env.

`mkdocs` generates and serves documentation sites based on markdown files.

```shell
pipx install mkdocs-material --include-deps
```

### yamllint

```shell
pipx install yamllint
```

## Nuitka

!!! WARNING
    Optional.

!!! WARNING
    Experimental.

!!! TODO
    Research system python version dependency.

```shell
CODENAME=$(grep UBUNTU_CODENAME /etc/os-release | cut -d '=' -f 2)
if [[ "${CODENAME}" == "" ]]; then
  CODENAME=$(lsb_release -c -s)
fi
curl -sS -L -f "http://nuitka.net/deb/archive.key.gpg" | sudo apt-key add -
sudo add-apt-repository -y "deb http://nuitka.net/deb/stable/${CODENAME} ${CODENAME} main"
sudo apt update
sudo apt install -y nuitka
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
