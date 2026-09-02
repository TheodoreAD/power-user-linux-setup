# AI tooling survey — install notes

Reference notes on the coding agents, editor extensions and local model runners PULSE does **not**
install, kept for when one of them has to be set up or evaluated on a machine this repo provisions.

This is the research half of what used to be `docs/ai.md`. It was moved here 2026-09-02: the site
says what PULSE does, and a survey of tools this repo does not install is not that. Everything about
market share, pricing tiers, funding and "leader in X" was dropped rather than moved — none of it
survives contact with a date, and none of it helps someone install a thing. What is kept is what
affects a developer who has already chosen a tool: how it installs, where its config lives, what it
talks to.

## Local model runner — Ollama

<https://ollama.com> — MIT, exposes an OpenAI-compatible API on `localhost:11434`, which is what
every other tool here points at for local inference.

```shell
curl -fsSL https://ollama.com/install.sh | sh

ollama pull qwen2.5-coder:7b     # fast autocomplete / chat
ollama pull qwen2.5-coder:32b    # stronger reasoning, needs ~20 GB VRAM
ollama pull codestral            # Mistral's coding model, strong on completions
ollama serve                     # API server (already started by the installer)
```

Model choice moves faster than this file will, so treat any specific model name here as an example
of the shape rather than a recommendation.

**If it were ever added to `setup.toml`:** the install script is a `script`-method package, and its
`ollama serve` systemd unit means it also needs the `workstation` tag rather than being installed in
a container.

## CLI coding agents

### Aider

<https://aider.chat> — terminal-native and git-first: it maps the repo, edits across paths, and
commits every accepted change itself.

```shell
pip install aider-install && aider-install   # installs aider into its own venv
aider --model ollama/qwen2.5-coder:32b       # fully local
```

Install note: `aider-install` builds its own virtualenv rather than living in the ambient one, so it
does not fit the `uv-tool` method as cleanly as it first looks — its own installer is the supported
path.

### Claude Code

Installed by PULSE (`[packages.claude-code]`, the native `claude.ai/install.sh` installer, which
self-updates). `npm install -g @anthropic-ai/claude-code` still works and is the legacy path; the
native installer is what this repo uses. See [`docs/claude-code.md`](../docs/claude-code.md).

### Goose

<https://goose-docs.ai> — Apache-2.0, editor-agnostic, runs shell commands and test suites as well
as editing code, and speaks ACP so Zed/JetBrains/VS Code can drive it.

```shell
curl -fsSL https://github.com/block/goose/releases/latest/download/install.sh | sh
goose session start
goose run --recipe my-recipe.yaml   # repeatable workflow
```

### Gemini CLI

<https://github.com/google-gemini/gemini-cli> — `npm install -g @google/gemini-cli`.

Install note for this machine specifically: a global npm package lands under the nvm version path
(`~/.local/share/nvm/versions/node/<version>/bin`), which is only on `PATH` once `nvm.sh` has been
sourced. That is fine in a login shell and invisible to a `RUN` layer or a non-interactive script —
the same trap `[packages.node]`'s own `verify_cmd` documents, and the reason `node.nvm_command()`
exists.

It reads `~/.gemini/GEMINI.md`, which is one of the four paths `[packages.agents-md]` symlinks to
`~/AGENTS.md` — so installing it is enough to have it pick up this machine's instructions.

## IDE extensions

### Continue.dev

<https://continue.dev> — the portable one: the same config drives both the VS Code and JetBrains
extensions, and it routes to Ollama, Claude, OpenAI or a self-hosted Tabby.

```shell
code --install-extension Continue.continue
# JetBrains: install "Continue" from the plugin marketplace
```

Config is `~/.continue/config.json`; pointing it at local models:

```json
{
  "models": [{ "title": "Qwen2.5-Coder 32B", "provider": "ollama", "model": "qwen2.5-coder:32b" }],
  "tabAutocompleteModel": {
    "title": "Qwen2.5-Coder 7B",
    "provider": "ollama",
    "model": "qwen2.5-coder:7b"
  }
}
```

### Cline

<https://github.com/cline/cline> — VS Code side-panel agent, bring-your-own-key (Claude, local
Ollama, or any OpenAI-compatible endpoint). `code --install-extension saoudrizwan.claude-dev`.

## Hosted assistants

### GitHub Copilot

```shell
code --install-extension GitHub.copilot
code --install-extension GitHub.copilot-chat
gh extension install github/gh-copilot     # terminal
gh copilot suggest "undo last git commit"
```

Two PULSE-relevant details: it reads `~/.copilot/copilot-instructions.md`, which is symlinked to
`~/AGENTS.md`, and it is the second agent named in `[packages.agent-skills]`'s `agents` list, so the
`skills` CLI installs for it as well as for Claude Code. `inv ai.install-skills` checks for a
Copilot install but never writes its settings — see `docs/claude-code.md`.

### Cursor / Windsurf

VS Code forks, both distributing a Linux `.deb`. A `.deb` behind a download page rather than a
stable URL is the `download_page` shape in `setup.toml`, which currently prompts for a
hand-downloaded file — and that prompt hangs an unattended run
(`plans/2026-08-31-wsl-and-container-first-run-experience.md`). Worth knowing before adding either.

## Self-hosted inference — Tabby

<https://tabby.tabbyml.com> — completion server on your own hardware, OpenAI-compatible API, serves
GGUF models. The reason to run one is data residency or shared team inference rather than anything
about the models.

```shell
docker run -it --gpus all -p 8080:8080 -v ~/.tabby:/data \
  tabbyml/tabby serve --model TabbyML/DeepseekCoder-6.7B --device cuda
```
