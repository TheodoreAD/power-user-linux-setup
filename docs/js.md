# Node.js

Node.js through nvm: where it installs, and why a non-interactive shell cannot see it.

<https://github.com/nvm-sh/nvm>

Installed via `inv node.install` (nvm method — installs nvm to `~/.local/share/nvm`, then installs
Node LTS and global packages declared in `setup.toml`).

Shell integration is split across two files written by `inv zsh.configure`:

- `~/.zshenv` — `export NVM_DIR` (sourced first, before oh-my-zsh, so the `nvm` plugin sees the
  custom path)
- `~/.zshrc` — `export NVM_DIR` as a fallback for shells that skip `.zshenv`

The oh-my-zsh `nvm` plugin (declared in `setup.toml` as `omz_plugin = "nvm"`) sources `nvm.sh` and
handles zsh completion via `bashcompinit`. The `nvm install` script is run with `PROFILE=/dev/null`
so it never writes to shell config files directly — PULSE owns those.

## Version management

nvm manages Node versions. Common commands:

```shell
nvm install --lts          # install latest LTS
nvm install 22             # install a specific major version
nvm use 22                 # switch version in current shell
nvm alias default lts/*    # set default for new shells
nvm ls                     # list installed versions
```

## Global packages

Global npm packages are declared in `setup.toml` under `global_packages` and installed by
`inv node.install`. Currently:

| Package  | What it does                                                                 |
| -------- | ---------------------------------------------------------------------------- |
| `skills` | Install Claude Code slash commands from GitHub — `skills add <owner>/<repo>` |

### Global installs vs uv tool install

`npm install -g` puts all tools in a single shared location under the active nvm version — there is
no per-tool isolation like `uv tool install` provides. In practice this rarely causes conflicts
because Node CLI tools have few shared dependencies.

For one-off runs use `npx <tool>` (equivalent to `uvx`) — it downloads and runs without installing.
Only add to `global_packages` for commands used daily.

If tool isolation ever becomes a real need, [Volta](https://volta.sh) is the upgrade path: it
manages Node versions and installs global tools in isolated shims, pinnable per project via
`package.json`.

## Verify

```shell
node --version
npm --version
```

## See also

- [Dev container](dev-container.md) — why a non-interactive shell cannot see node
- [Claude Code](claude-code.md) — the global npm package the skills installer needs
- [Updating and removing](updating.md) — moving to a newer LTS
