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
argcomplete_dir="$(pyenv root)/versions/$(pyenv whence register-python-argcomplete | head -n1)/bin/"
eval "$(${argcomplete_dir}/register-python-argcomplete pipx)"
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

!!! TODO
    Solve this deprecation issue:

    ```shell
    Warning: poetry-plugin-export will not be installed by default in a future version of Poetry.
    In order to avoid a breaking change and make your automation forward-compatible, please install poetry-plugin-export explicitly. See https://python-poetry.org/docs/plugins/#using-plugins for details on how to install a plugin.
    To disable this warning run 'poetry config warnings.export false'.
    ```

## System-wide tools

### invoke and dotenv

`invoke` is a Python-based alternative to `make` focused on task management.
`dotenv` is used together with `invoke` for `.env` file local dev workflows.

<https://github.com/pyinvoke/invoke>
<https://github.com/theskumar/python-dotenv>

We install `dotenv` side-by-side so that the `invoke`-run `tasks.py`
can import `dotenv` and read `.env` files.

!!! TODO
    solve issues forcing versions lower than 2 to avoid compatibilty issues

```shell
pipx install invoke==1.7.3
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
    Intall via pyenv and pipx.

!!! TODO
    test

```shell
python -m nuitka --module invoke --include-package=invoke
```
