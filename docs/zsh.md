# Zsh

## Setup

All zsh configuration is declared in `setup.toml` and applied via invoke:

```shell
inv tools.install      # installs OMZ, Powerlevel10k, zsh-autosuggestions, zsh-syntax-highlighting
inv zsh.omz-configure  # updates plugins=() and ZSH_THEME in ~/.zshrc
inv zsh.configure      # writes sentinel blocks (completions, aliases, keybindings, direnv, etc.)
```

Or all at once via `inv setup`.

**First run only** — configure the Powerlevel10k prompt interactively:

```shell
p10k configure
```

Config is saved to `~/.p10k.zsh`. Re-run any time to change the prompt layout.

## What gets installed

| Package                 | Method                                      | Destination                                           |
| ----------------------- | ------------------------------------------- | ----------------------------------------------------- |
| Oh My Zsh               | script (official installer, `--unattended`) | `~/.oh-my-zsh`                                        |
| Powerlevel10k           | git-clone `--depth=1`                       | `~/.oh-my-zsh/custom/themes/powerlevel10k`            |
| zsh-autosuggestions     | git-clone                                   | `~/.oh-my-zsh/custom/plugins/zsh-autosuggestions`     |
| zsh-syntax-highlighting | git-clone                                   | `~/.oh-my-zsh/custom/plugins/zsh-syntax-highlighting` |

## Plugins

Applied by `inv zsh.omz-configure`, which rewrites the `plugins=(...)` block in `~/.zshrc` in-place. `zsh-syntax-highlighting` is always kept last — it post-processes already-parsed input.

The final plugins list is assembled from two sources:

- **Base plugins** in `[packages.oh-my-zsh].plugins` — always included, no external dependency
- **Tool plugins** via `omz_plugin` on each package entry — only included when that package is enabled

This means enabling `[packages.gcloud]` automatically adds the `gcloud` OMZ plugin; disabling it drops it.

**Always-on (base):**

| Plugin                    | What it provides                                                                               |
| ------------------------- | ---------------------------------------------------------------------------------------------- |
| `git`                     | ~60 aliases: `gs` (status), `ga` (add), `gc!` (commit --amend), `gp` (push), `gl` (pull), etc. |
| `rsync`                   | Aliases for common rsync invocations (rsync is a Ubuntu standard default)                      |
| `dirhistory`              | Ctrl+Up/Down to navigate `cd` history                                                          |
| `history`                 | `h` alias for `history`; `hsi` for history grep                                                |
| `web-search`              | `google term`, `bing term`, etc. open browser searches                                         |
| `zsh-autosuggestions`     | Fish-style inline suggestions from history as you type                                         |
| `zsh-syntax-highlighting` | Real-time command syntax highlighting in the prompt                                            |

**Tool-coupled (via `omz_plugin` on the package entry):**

| Plugin                     | Package                                 | What it provides                     |
| -------------------------- | --------------------------------------- | ------------------------------------ |
| `kubectl`                  | `[packages.kubectl]`                    | Tab completions; `k` alias           |
| `helm`                     | `[packages.helm]`                       | Tab completions                      |
| `docker`, `docker-compose` | `[packages.docker]` _(workstation tag)_ | Tab completions                      |
| `nvm`                      | `[packages.node]`                       | `.nvmrc` auto-detection on `cd`      |
| `gcloud`                   | `[packages.gcloud]` _(disabled)_        | Completions when gcloud is installed |

The `nvm` plugin lazy-loads nvm on first use but is kept for `.nvmrc` auto-detection. The `[packages.node]` sentinel block in `~/.zshrc` also eagerly sources `nvm.sh` — they coexist without conflict.

The `jsontools` plugin was removed — `ppjson`, `isjson`, `urlencode`, and `urldecode` are re-implemented in `[packages.jq-aliases]` (see Aliases).

## Keybindings

No custom bindings — OMZ uses emacs mode (`bindkey -e`) which covers everything via `Alt` (or `Esc`) combinations:

| Key                    | Action                              |
| ---------------------- | ----------------------------------- |
| Home / End             | `beginning-of-line` / `end-of-line` |
| Ctrl+Right / Ctrl+Left | `forward-word` / `backward-word`    |
| Alt+Backspace          | `backward-kill-word`                |
| Alt+D                  | `kill-word`                         |
| Alt+U                  | `up-case-word`                      |
| Alt+L                  | `down-case-word`                    |
| Alt+'                  | `quote-line`                        |
| Alt+"                  | `quote-region`                      |
| Ctrl+L                 | `clear-screen`                      |
| Ctrl+R                 | incremental history search backward |
| Ctrl+X Ctrl+E          | edit current command in `$EDITOR`   |

## Aliases

- `jq='jq -S'`: sort keys by default — declared in `[packages.jq-aliases]`; alias scope means scripts calling `jq` directly are unaffected (jq has no config file or `JQ_FLAGS` env var)
- `ppjson`: pretty-print JSON from stdin — wraps `jq .` (inherits `-S`, so keys are sorted)
- `isjson`: validate JSON from stdin — prints `true`/`false` to stdout and exits 0/1
- `urlencode`: URI-encode stdin — wraps `jq -Rr @uri` (RFC 3986, spaces → `%20`); replaces the `urltools` OMZ plugin which was arg-based and used `quote_plus` (spaces → `+`)
- `urldecode`: URI-decode stdin — wraps `python3 urllib.parse.unquote` (no jq equivalent)
- `k` → `kubectl`: provided by the OMZ `kubectl` plugin, not declared here
- `curl` defaults: `--silent --show-error --location` written to `~/.config/curlrc` by `inv system.curlrc` — no alias needed

## Clipboard

Declared in `[packages.clipboard]` in `setup.toml`. Requires `wl-clipboard` (apt). **Wayland only — does not work over SSH or in X11-only sessions.**

| Command     | Action                                     |
| ----------- | ------------------------------------------ |
| `xcc`       | Pipe stdin to clipboard: `cat file \| xcc` |
| `xc "text"` | Copy argument to clipboard                 |
| `xv`        | Paste clipboard to stdout                  |

## Completions

Sourced as sentinel blocks in `~/.zshrc` after `source $ZSH/oh-my-zsh.sh`:

| Tool        | Source                                                      |
| ----------- | ----------------------------------------------------------- |
| `fzf`       | `/usr/share/doc/fzf/examples/` (key bindings + completions) |
| `uv`, `uvx` | `uv generate-shell-completion zsh`                          |
| `kind`      | `kind completion zsh`                                       |
| `tilt`      | `tilt completion zsh`                                       |

OMZ calls `compinit` internally — no manual `autoload -Uz compinit && compinit` needed.

## History

Declared in `[packages.zsh-history]`:

```shell
HISTSIZE=1000000
SAVEHIST=1000000
setopt EXTENDED_HISTORY       # record timestamp + elapsed time per command
setopt HIST_IGNORE_ALL_DUPS   # remove older duplicate when same command is entered
setopt HIST_FIND_NO_DUPS      # skip duplicates during Ctrl+R search
setopt HIST_IGNORE_SPACE      # don't record commands prefixed with a space
setopt HIST_REDUCE_BLANKS     # strip superfluous whitespace before recording
setopt HIST_VERIFY            # show expanded history before executing (e.g. !foo)
setopt SHARE_HISTORY          # live cross-session sharing via atomic appends
setopt HIST_FCNTL_LOCK        # fcntl-based file locking for concurrent-session writes
```

**Corruption:** `EXTENDED_HISTORY` + `SHARE_HISTORY` is the standard zsh combo for a large,
cross-session-shared history, but zsh's history file format has no crash-safety against power
loss mid-write — an unfixed upstream limitation, not something a `setopt` can close. `HIST_FCNTL_LOCK`
mitigates the other real-world cause (concurrent shells racing to write the file at once) by using
standard `fcntl()` locking instead of zsh's ad-hoc default. If `~/.zsh_history` still gets corrupted
(unreadable lines, `zsh: corrupt history file`), recover it with:

```shell
inv zsh.history-fix   # strings(1) strips non-printable bytes, then reloads history
```

**Atuin** (SQLite-backed history with a richer Ctrl+R UI, exit codes, durations, optional sync) was
evaluated and deliberately deferred — fzf's Ctrl+R over the native history file is sufficient for now
and adds no daemon or separate data store. `[packages.atuin]` exists in `setup.toml` with
`enabled = false` for whenever it's worth revisiting; see the fzf section below for what changes
when switching.

## fzf

fzf is wired to `fd` (fast file finder) and `bat` (syntax-highlighted preview) via env vars in `[packages.fzf]`. All bindings open an interactive fuzzy picker — type to filter, `Enter` to accept, `Esc` to cancel.

### Key bindings

**`Ctrl+R` — history search**

Opens a picker over your full shell history. Type any fragment of the command. Results are sorted by recency. Press `Ctrl+/` to toggle a preview pane showing the full command text (useful for long commands). Accepts into the prompt without executing — press `Enter` again to run.

**`Ctrl+T` — file picker**

Searches files recursively from the current directory (via `fd`, so `.gitignore` is respected and `.git` directories are excluded). Pastes the selected path at the cursor position in the current command. Useful mid-command:

```
vim <Ctrl+T>          # pick a file to open
cp <Ctrl+T> ./dest/   # pick the source file
git add <Ctrl+T>      # stage a specific file
```

Preview pane shows the file's contents via `bat` (syntax highlighting, line numbers, first 300 lines).

**`Alt+C` — directory jump**

Searches subdirectories recursively and `cd`s into the selected one immediately. Preview shows `ls -la` of the directory.

### `**` fuzzy tab completion

Type a command, then `**` and press `Tab` to get a fuzzy picker for what comes next:

```
vim **<Tab>           # pick any file under current dir
cd **<Tab>            # pick a subdirectory to cd into
ssh **<Tab>           # pick from ~/.ssh/config hosts
kill **<Tab>          # pick a running process by name
unset **<Tab>         # pick an environment variable
export **<Tab>        # pick an environment variable
```

The picker for each context is context-aware — `kill **<Tab>` shows processes, `ssh **<Tab>` shows hosts from your SSH config, etc.

### In scripts and pipelines

fzf can be used directly in scripts as a generic picker — pipe any list to it and it returns the selected line:

```shell
# pick a git branch to check out
git checkout $(git branch | fzf)

# pick a running docker container to exec into
docker exec -it $(docker ps --format '{{.Names}}' | fzf) bash

# pick a file to edit from ripgrep results
vim $(rg --files | fzf)
```

### Navigation inside fzf

| Key              | Action                                              |
| ---------------- | --------------------------------------------------- |
| Type             | filter results                                      |
| `↑` / `↓`        | move selection                                      |
| `Enter`          | accept                                              |
| `Esc` / `Ctrl+C` | cancel                                              |
| `Ctrl+/`         | toggle preview pane (where configured)              |
| `Tab`            | mark multiple items (where multi-select is enabled) |

**When enabling Atuin:** remove the `key-bindings.zsh` source from `[packages.fzf]` in `setup.toml` (keep `completion.zsh`) to avoid the `Ctrl+R` conflict. `Ctrl+T`, `Alt+C`, and `**` completion are unaffected.

## PATH

PATH is controlled entirely through `setup.toml` sentinel blocks written to `~/.zshenv` (loaded for all zsh instances):

| Entry                            | Adds                                                              |
| -------------------------------- | ----------------------------------------------------------------- |
| `[packages.zsh-path]`            | `~/.local/bin` prepended — user tools shadow system tools         |
| `[packages.go]`                  | `$GOROOT/bin` (`go`, `gofmt`), `$GOPATH/bin` (go-installed tools) |
| `[packages.gcloud]` _(disabled)_ | `~/.local/share/google-cloud-sdk/bin`                             |

`~/.local/bin` goes in `~/.zshenv` rather than `~/.zshrc` so they are available to all zsh instances, including non-interactive scripts. `/usr/local/bin` is already in the system PATH via `/etc/environment` and is not duplicated here.

When adding a new tool that needs a PATH entry, prefer creating a symlink in `~/.local/bin` over a new PATH manipulation. Only add a PATH entry when the tool writes multiple binaries to its own directory dynamically (like `go install` populating `$GOPATH/bin`).
