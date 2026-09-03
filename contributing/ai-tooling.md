# AI tooling survey — install notes

Reference notes on the coding agents, editor extensions and local model runners PULSE does **not**
install, kept for when one of them has to be set up or evaluated on a machine this repo provisions.

This is the research half of what used to be `docs/ai.md`. It was moved here 2026-09-02: the site
says what PULSE does, and a survey of tools this repo does not install is not that. Everything about
market share, pricing tiers, funding and "leader in X" was dropped rather than moved — none of it
survives contact with a date, and none of it helps someone install a thing. What is kept is what
affects a developer who has already chosen a tool: how it installs, where its config lives, what it
talks to.

## Where each agent looks for skills, and why the registry cannot be trusted for it

Measured 2026-09-04 against the installed `skills` CLI (v1.5.10,
[vercel-labs/skills](https://github.com/vercel-labs/skills)), reading its bundle rather than its
README. Read this before adding an agent to `[packages.agent-skills]`'s `agents` list or claiming on
the site that some agent "finds the skills".

Its registry holds **71 agents**, each with two path fields:

- **`skillsDir`** — the per-repository directory. 19 entries set it to `.agents/skills`: amp,
  antigravity, antigravity-cli, cline, codex, cursor, deepagents, dexto, firebender, gemini-cli,
  github-copilot, kimi-code-cli, loaf, opencode, promptscript, replit, universal, warp, zed. Claude
  Code is not among them — its `skillsDir` is `.claude/skills`, which is the whole reason
  `inv ai.install-skills` maintains the `~/.claude/skills` symlink.
- **`globalSkillsDir`** — the home-directory one, and **it is not where the agent looks.** Of those
  19, only 6 name `~/.agents/skills`; 3 name the XDG spelling `~/.config/agents/skills`, 9 name a
  vendor directory, and 1 names nothing.

The two fields disagree and the CLI disagrees with itself about which to use: `isUniversalAgent()`
is defined as `skillsDir === ".agents/skills"`, and `getAgentBaseDir()` short-circuits on it and
returns `~/.agents/skills` for all 19 without consulting `globalSkillsDir` — while the `list` scope
builder and the cleanup scanner read `globalSkillsDir` directly.

**The short-circuit is the correct half.** Three of the nine vendor-directory entries are agents
this repo already sends `~/AGENTS.md` to, and all three were checked against the vendor's own
source:

| agent            | registry's `globalSkillsDir` | what the vendor's own source says                                                                                                               |
| ---------------- | ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `codex`          | `~/.codex/skills`            | reads `~/.agents/skills` **and** `$CODEX_HOME/skills` — the latter commented "Deprecated user skills location, kept for backward compatibility" |
| `gemini-cli`     | `~/.gemini/skills`           | reads `~/.gemini/skills` **and** `~/.agents/skills`, the latter as the "user agent skills alias"                                                |
| `github-copilot` | `~/.copilot/skills`          | "For **personal skills**, shared across projects, create a `~/.copilot/skills` or `~/.agents/skills` directory"                                 |

Sources, each read directly rather than through a search summary:

- Codex — `codex-rs/ext/skills/src/host_roots.rs`, the `ConfigLayerSource::User` arm of
  `roots_from_layer_stack`, which pushes both roots and carries the deprecation comment.
- Gemini CLI — `packages/core/src/skills/skillManager.ts` step 3.1 loads
  `Storage.getUserAgentSkillsDir()`; `packages/core/src/config/storage.ts` defines it as
  `join(homedir(), ".agents", "skills")`.
- Copilot — `github/docs`, `data/reusables/copilot/creating-adding-skills.md`.

So `globalSkillsDir` is best read as the CLI's own preferred write target, not as a statement about
the agent, and it was stale or secondary in three out of three checks. Two consequences:

- **Never quote that field as "where agent X reads skills."** Check the vendor. The one time this
  repo took a path claim from a summary instead, it nearly deleted a working Copilot entry.
- **The `agents = ["claude-code", "github-copilot"]` list is harmless but does no work.** At
  `--global` scope every universal agent resolves to the same `~/.agents/skills`, so the second
  element adds no second copy — verified on this machine: one real directory, and no
  `~/.copilot/skills` was created. Adding `codex` or `gemini-cli` to the list would be an equally
  exact no-op.

Six of the nine vendor-directory entries are still unchecked — antigravity, antigravity-cli, cursor,
deepagents, firebender, opencode. None is installed here. Given three for three above, the
expectation is that most of them also read `~/.agents/skills`, but the site must not say so until
somebody looks.

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
`~/AGENTS.md` — so installing it is enough to have it pick up this machine's instructions. It also
reads `~/.agents/skills` directly, alongside its own `~/.gemini/skills`, so it picks up the skills
too with nothing added to `[packages.agent-skills]` — see the skills-directory section above.

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
`~/AGENTS.md`, and it accepts `~/.agents/skills` as a personal-skills location in its own right, so
it finds the installed skills whether or not it is named anywhere. It **is** the second agent in
`[packages.agent-skills]`'s `agents` list, but that entry is a no-op rather than what makes the
skills reach it — see the skills-directory section above. `inv ai.install-skills` checks for a
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
