# AI tools

Tools for running local LLMs, agentic coding, and getting more out of hosted assistants (Claude, Copilot).

---

## Local model runner — Ollama

<https://ollama.com>

The de-facto standard for running open-weight LLMs locally. MIT-licensed, exposes an OpenAI-compatible API on `localhost:11434`, and integrates with every tool in this doc.

```shell
curl -fsSL https://ollama.com/install.sh | sh

ollama pull qwen2.5-coder:7b    # fast autocomplete / chat
ollama pull qwen2.5-coder:32b   # stronger reasoning, needs ~20 GB VRAM
ollama pull codestral            # Mistral's coding model, strong on completions
ollama pull deepseek-coder-v2    # top open-weight coding model as of mid-2026
ollama serve                     # starts the API server (auto-started on install)
```

**Recommended models by use case:**

| Use case | Model |
|---|---|
| Autocomplete (fast) | `qwen2.5-coder:7b` |
| Chat / refactoring | `qwen2.5-coder:32b` or `deepseek-coder-v2` |
| Completions quality | `codestral` (Mistral, free for non-commercial) |
| General assistant | `llama3.3` or `mistral-small3.2` |

---

## CLI coding agents

### Aider

<https://aider.chat>

Terminal-native, git-first coding agent. Maps the codebase, edits files across multiple paths, and auto-commits every accepted change with a conventional message. Works with any LLM provider or a local Ollama model.

```shell
pip install aider-install && aider-install   # installs aider into its own venv

# With Claude (recommended for complex tasks)
aider --model claude-sonnet-4-6

# Fully local via Ollama
aider --model ollama/qwen2.5-coder:32b

# Add files to the context explicitly
aider src/main.go src/handler.go
```

### Claude Code

<https://claude.ai/code>

Anthropic's official terminal agent. Strongest at large-scope refactors, architecture reasoning, and multi-file changes. Requires an Anthropic API key or Pro/Max subscription.

```shell
npm install -g @anthropic-ai/claude-code
claude
```

See the [Claude Code docs](https://docs.anthropic.com/en/docs/claude-code) for MCP server setup, hooks, and slash commands.

### Goose

<https://goose-docs.ai>

Editor-agnostic autonomous agent (Apache-2.0, Linux Foundation AI). Goes beyond code: can run shell commands, manage files, call APIs, and execute test suites. Works offline with Ollama.

```shell
curl -fsSL https://github.com/block/goose/releases/latest/download/install.sh | sh
# or: pip install goose-ai

goose session start              # interactive REPL
goose run --recipe my-recipe.yaml  # automated workflow
```

Connects to Zed, JetBrains, or VS Code as an ACP server. Choose Goose when you need an agent that works outside VS Code or need repeatable "recipes" for recurring workflows.

### Gemini CLI

<https://github.com/google-gemini/gemini-cli>

Google's open-source terminal agent. Free tier is generous (1,500 requests/day with a personal Google account), making it useful for high-volume or exploratory tasks where you don't want to burn paid credits.

```shell
npm install -g @google/gemini-cli
gemini
```

---

## IDE extensions

### Continue.dev

<https://continue.dev>

The most editor-portable option: same config drives both VS Code and JetBrains extensions. Supports autocomplete, inline edit, and chat. Routes to any backend — Ollama, Claude, OpenAI, or a self-hosted Tabby server.

```shell
# VS Code
code --install-extension Continue.continue

# JetBrains: install "Continue" from the plugin marketplace
```

Config lives at `~/.continue/config.json`. Point at a local Ollama model:

```json
{
  "models": [{
    "title": "Qwen2.5-Coder 32B",
    "provider": "ollama",
    "model": "qwen2.5-coder:32b"
  }],
  "tabAutocompleteModel": {
    "title": "Qwen2.5-Coder 7B",
    "provider": "ollama",
    "model": "qwen2.5-coder:7b"
  }
}
```

### Cline

<https://github.com/cline/cline>

VS Code extension that gives you an autonomous coding agent in a side panel. Bring-your-own-key: Claude, GPT-4o, local Ollama, or any OpenAI-compatible endpoint. Cline CLI 2.0 (2026) supports headless and parallel workflows.

```shell
code --install-extension saoudrizwan.claude-dev
```

---

## Hosted assistants

### GitHub Copilot

<https://github.com/features/copilot>

The most widely-used paid assistant (~42% market share). Tight IDE integration and a free tier (50 agent requests + 2,000 completions/month). Pro is $10/month. Available in VS Code, JetBrains, Neovim, and the terminal.

```shell
# VS Code
code --install-extension GitHub.copilot
code --install-extension GitHub.copilot-chat

# Terminal (Copilot in the CLI)
gh extension install github/gh-copilot
gh copilot suggest "undo last git commit"
```

### Cursor

<https://cursor.sh>

VS Code fork with AI woven into every layer. Market leader in AI editors ($2B ARR). Best for developers who want deep autocomplete and Composer (multi-file agent) without leaving the editor. Linux `.deb` / AppImage available.

### Windsurf

<https://codeium.com/windsurf>

Another VS Code fork from Codeium. Notable for "Cascade" — a flow-based multi-step agent that maintains a codemap. Free tier available. Linux `.deb` available.

---

## Self-hosted inference server — Tabby

<https://tabby.tabbyml.com>

Self-hosted completion server. Runs on your own hardware, exposes an OpenAI-compatible API, and serves any GGUF model. Right choice when your org has data-residency requirements or you want team-wide shared inference.

```shell
docker run -it \
  --gpus all \
  -p 8080:8080 \
  -v ~/.tabby:/data \
  tabbyml/tabby serve \
    --model TabbyML/DeepseekCoder-6.7B \
    --device cuda
```

---

## Recommended combinations

| Scenario | Stack |
|---|---|
| Daily coding, mixed local + cloud | Copilot Pro ($10/mo) for autocomplete + Claude Code for complex refactors |
| Fully local / air-gapped | Ollama + Continue.dev (autocomplete) + Aider (agent) |
| Team, shared inference | Tabby server + Continue.dev on each workstation |
| Autonomous tasks, offline-capable | Ollama + Goose |
| VS Code power user | Cline + Ollama (local) with Claude fallback |
