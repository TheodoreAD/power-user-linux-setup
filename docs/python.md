# Python

All Python version management, tool installs, and virtual environments are handled by
[uv](https://github.com/astral-sh/uv). pyenv, poetry, and pipx are no longer used.

## Bootstrap

Run `bootstrap.sh` from the repo root. It installs uv, then installs and manages all
Python versions defined in `setup.toml`:

```shell
./bootstrap.sh
```

This installs:
- uv itself into `~/.local/bin/uv`
- Python versions via uv — default (`uv_python_default`) plus extras (`uv_python_extra`)
- invoke (the task runner) under the default Python version

To change which versions are installed, edit `setup.toml`:

```toml
[settings]
uv_python_default = "3.11"
uv_python_extra   = ["3.12", "3.13", "3.14"]
```

## Python version shims

After bootstrap, uv creates versioned shims in `~/.local/bin`:

```
~/.local/bin/python3.11  ->  ~/.local/share/uv/python/cpython-3.11-linux-x86_64-gnu/bin/python3.11
~/.local/bin/python3.12  ->  ...
```

These are available in any shell where `~/.local/bin` precedes `/usr/bin` on `PATH`.
The unversioned `python` and `python3` remain as the OS-level system Python — this
keeps system tools happy while all dev work uses explicit versioned commands or uv's
own resolution.

## Shell default

`UV_PYTHON` is set in `~/.zshenv` automatically by `inv zsh.configure` (or `inv setup`),
sourced from the `[packages.uv-env]` entry in `setup.toml`. Project-level `.python-version`
files override it automatically.

## System-wide tools

All tools are installed as isolated uv-managed executables and defined in `setup.toml`
under `method = "uv-tool"`. Install or upgrade all of them with:

```shell
inv python.tools
```

Current tools: `nox`, `mkdocs` (with `mkdocs-material`), `twine`, `glances`, `nuitka`, `zensical`.
(`invoke` itself is installed by `bootstrap.sh`, not this task.)

To add a new tool, add a section to `setup.toml`:

```toml
[packages.mytool]
method  = "uv-tool"
package = "mytool"
```

Then run `inv python.tools` again.

## Project virtual environments

Create a virtualenv pinned to a specific Python:

```shell
uv venv --python 3.12
```

Pin the project's default Python (writes `.python-version`, committed to the repo):

```shell
uv python pin 3.12
```

From then on, plain `uv venv` and `uv run` in that project automatically use 3.12.

Install project dependencies from a `pyproject.toml` or `requirements.txt`:

```shell
uv sync           # pyproject.toml with [project.dependencies]
uv pip install -r requirements.txt
```

## Private PyPI

If using a private package index, configure it via environment variable or `uv.toml`:

```shell
# environment variable (e.g. in .env or shell profile)
export UV_INDEX_URL="https://your-private-pypi/simple"
export UV_EXTRA_INDEX_URL="https://pypi.org/simple"
```

Or in `~/.config/uv/uv.toml` for a persistent user-level config:

```toml
[[index]]
url      = "https://your-private-pypi/simple"
default  = true

[[index]]
url      = "https://pypi.org/simple"
```

## Nuitka

Nuitka is installed as a uv tool (`inv python.tools`). It compiles Python to C and
produces standalone native executables. `patchelf` (apt) is required at compile time
and is listed in `setup.toml`.

Compile a script:

```shell
python -m nuitka --standalone --onefile my_script.py
```

Compile a package as an importable extension module:

```shell
python -m nuitka --module mypackage --include-package=mypackage
```

!!! NOTE
    Nuitka uses the Python it was invoked with. Run it via `python3.11 -m nuitka` or
    activate the project's venv first to control which interpreter is used.
