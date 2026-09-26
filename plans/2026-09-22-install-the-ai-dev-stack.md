---
status: idea
updated: 2026-09-22
---

# Installing the chosen AI dev stack, and the two-machine problem it creates

## Context

The **what** was settled elsewhere and is not re-argued here.
`$PLANS_HOME/_unscoped/2026-09-21-open-source-ai-dev-stack.md` holds the research: four named
candidates evaluated from their own source, three rejected, and a replacement stack chosen. It was
filed unscoped deliberately — _"this is more about an ai stack, and not primarily about power user
Linux setup, we'll create plans for installing the stack after we figure out the stack"_ — and this
is that follow-on.

The three sentences from it that bind this plan:

1. **Nothing may sit between an agent and its provider rewriting context.** Measured at 8.34× on
   this machine's real workload, because 98.75% of its input tokens are cache reads.
2. **Nothing may route a subscription credential.** Prohibited in writing by two of four providers.
3. **The local tier is a helper, not an agent** — summarisation, classification, embeddings, commit
   messages, offline fallback. Scoped by decision rather than by measurement, 2026-09-22.

Everything below follows from those plus this repo's own rule that every install is a declared
`[packages.*]` entry, never a manual `apt install` or `curl | bash`.

## What gets installed, and by which method

| component                      | where                         | method                                                        | notes                                                     |
| ------------------------------ | ----------------------------- | ------------------------------------------------------------- | --------------------------------------------------------- |
| **OpenCode**                   | this workstation              | ? — distribution not yet checked                              | needs a `symlink_dest` for `~/.config/opencode/AGENTS.md` |
| **ccusage**                    | this workstation              | `nvm`/npm — it is an npm package                              | read-only, no daemon                                      |
| **ast-grep**                   | this workstation              | `uv-tool` if a maintained PyPI wrapper exists, else `archive` | CLI only, not the MCP server                              |
| **llama.cpp (`llama-server`)** | **the 12 GB box**             | `archive` from GitHub releases                                | needs a systemd unit and a models directory               |
| LiteLLM                        | this workstation, **only if** | `uv-tool`                                                     | optional; see "the gateway is conditional"                |
| SkillSpector                   | this workstation, later       | ?                                                             | candidate, not load-bearing                               |

[NEEDS CLARIFICATION: **how is OpenCode actually distributed on Linux?** The research read its
source, not its install path. npm, a single binary, an install script, or several — this decides
whether it is a `script`, `binary`, `archive` or npm entry, and whether it self-updates in a way
that fights a declared version. Check before writing the entry, not after.]

Two rules from this repo that apply directly and are easy to miss here:

- **XDG**: `llama.cpp` is a multi-file runtime, so `~/.local/share/llama.cpp` with the binary
  symlinked into `~/.local/bin`, never a `~/.llama.cpp`. The models directory is the awkward part —
  tens of gigabytes is not obviously `~/.local/share` material, and it is the one path here whose
  size argues for a deliberate location rather than a default.

- **`spowse` vs `inv`**: any new task here administers a machine rather than this repo, so it ships
  in `spowse` and must **not** be marked `@util.dev_only`. `tests/unit/test_cli.py` pins membership,
  so getting it wrong fails the gate rather than shipping.

### The router-mode flags, verified against the clone 2026-09-26

Read from `common/arg.cpp` in `$RESEARCH_HOME/repos/github.com--ggml-org--llama.cpp`, not from a
report. Every flag the design depends on exists, with these exact spellings:

| flag                                         | line            | what it does                                                     |
| -------------------------------------------- | --------------- | ---------------------------------------------------------------- |
| `--models-dir PATH`                          | `3629`          | the router's model directory — **default: disabled**             |
| `--models-preset PATH`                       | `3636`          | **an INI file of model presets** — default: disabled             |
| `--models-max N`                             | `3643`          | max models resident at once; `0` = unlimited                     |
| `--models-autoload` / `--no-models-autoload` | `3650`          | load on demand or not                                            |
| `--sleep-idle-seconds SECONDS`               | `3797`          | release after idle; `-1` disables, and it **rejects 0 and < -1** |
| `--api-key KEY` / `--api-key-file FNAME`     | `3479` / `3490` | inbound auth — the reason this beat Ollama                       |
| `--ssl-key-file FNAME`                       | `3507`          | TLS                                                              |
| `-cmoe, --cpu-moe` / `-ncmoe, --n-cpu-moe N` | `2756` / `2763` | MoE expert offload to system RAM                                 |

Two findings from reading it that change how this gets declared, and both make the job easier than
the table above assumed:

[DECISION: **the systemd unit carries `Environment=` lines, not a long `ExecStart`.** Every router
flag has a matching `LLAMA_ARG_*` environment variable declared via `.set_env(...)` —
`LLAMA_ARG_MODELS_DIR`, `LLAMA_ARG_MODELS_PRESET`, `LLAMA_ARG_MODELS_MAX`,
`LLAMA_ARG_MODELS_AUTOLOAD`. So the unit stays short and each setting is one greppable line, rather
than a single command string where a change is a diff nobody can read.]

[DECISION: **`--models-preset` is the declarable surface, and it solves the config half outright.**
It takes an **INI file**, which is a plain text file this repo can hold as a repo-side source and
deploy through a `config_files` mapping like any other dotfile — diffable, reviewable, and visible
to `inv deploy.status`. That is the property LiteLLM was praised for above and 9Router was rejected
for, and llama.cpp has it natively. The model _weights_ stay undeclared, which is correct: they are
bulk data, not configuration.]

So the two halves separate cleanly — **an INI file of presets is configuration and gets deployed;
the GGUF files are data and get fetched by a deliberate standalone task.** That mirrors the repo's
existing rule for regenerated files: run it explicitly, never wire it into routine setup.

## The two-machine problem — the real design question

This would be the first time PULSE provisions **two machines with different roles**: a workstation
that is a client, and a headless box that serves inference. Nothing in the repo expresses that
today, and the naive approaches both break.

### Why a tag alone does not work

`docs/configuration.md` records that **only 7 tags gate anything** — `gui`, `desktop`, `gnome`,
`workstation`, `corporate`, `ide`, `windows-native` — and that building an environment profile by
setting `PULSE_EXCLUDE_TAGS` alone is **not sufficient**, because several tasks read `[packages.*]`
sections directly and ignore tags entirely. So an `inference-host` tag is not self-evidently a
mechanism; it would have to be made one, and the table says which tasks would have to change.

### Why declaring it breaks `inv setup` on this machine

This is the sharper half, and it is already written down in `CLAUDE.md`:

> A destination declared in `setup.toml` is one `inv verify.all` requires to exist at the end of
> `inv setup`'s packages phase.

So a `[packages.llama-cpp]` entry declared unconditionally **fails verification on the
workstation**, which will never have it installed. The documented escape hatch is exactly this
shape: a file "written only in some situations (a corporate-only systemd unit)" goes through
`deploy.py` without being declared — construct a `deploy.Managed` in the writing module and call
`deploy.deploy()`.

[DECISION: **the corporate-only systemd unit is the precedent to follow, not a new mechanism.** It
is the same problem — a unit that exists on some machines and not others — and it is already solved
here in a way `verify.all` tolerates and `home.list-claims` records. Reaching for a new tag first
would be inventing a mechanism where an existing one fits; read `contributing/home-claims.md` before
extending the registry either way.]

[NEEDS CLARIFICATION: **is the 12 GB box a machine PULSE should provision at all?** Its OS and
uptime are unknown, and the answer changes the shape completely. A Linux box running this repo's own
setup is one thing; a Windows or hand-managed box means the llama.cpp half of this plan is a
documented manual procedure rather than a package, and only the client half is declarable. Ask
before designing either.]

## The gateway is conditional, and the condition is narrow

LiteLLM earns a process **only** if something speaking Anthropic's `/v1/messages` must reach the
local model, because `llama-server` speaks OpenAI only. If every consumer is OpenAI-shaped, it buys
nothing that `llama-server --api-key` does not already provide, and it is one more process, one more
auth boundary and one more timeout chain.

If it is adopted, three settings are not optional:

- `LITELLM_LOCAL_MODEL_COST_MAP=True` — it otherwise fetches its cost map from GitHub at import, and
  the `litellm` server entry point is **not** in the exemption list that covers its CLI names.
- `DISABLE_ADMIN_UI=true` — with no database, a UI write falls through to `yaml.dump()` **over the
  config file**, reordered and comment-stripped. That would rewrite a repo-deployed file in place.
- Declare llama-server as `hosted_vllm/<name>`, **not** `openai/<name>` — the latter routes
  `/v1/messages` to the Responses API, which llama-server does not serve.

Its config is a plain YAML file with `os.environ/` secret references, so it deploys through
`config_files` like any other dotfile. That is the axis on which it beat the alternative.

## Verification

Per this repo's convention, each package needs a `check_cmd` and, where invocation differs, a
`verify_cmd`. Two things to get right rather than discover:

- **`llama-server` must not be verified by starting it.** `contributing/verify.md` records a real
  machine freeze from an unrecognized-flag hang. A `--version` probe, confirmed by hand first.
- **`inv verify.all` is not read-only** and must not be re-run to filter its own output.

## Open questions

[NEEDS CLARIFICATION: **does OpenCode on Copilot actually work for this user's daily work?** The
whole design rests on Copilot being an adequate engine for the second agent, and that is an
assumption, not a measurement. Worth a week of real use before the install plan is promoted past
`idea` — and cheap to test, since OpenCode's Copilot login is built in and needs none of this plan's
infrastructure.]

[NEEDS CLARIFICATION: **where do the models live, and who downloads them?** Narrowed 2026-09-26 by
the `--models-preset` finding above: the _configuration_ half is settled (an INI file, deployed like
any dotfile), so what is left is only the weights. Tens of gigabytes of GGUF is not a `setup.toml`
download, and a first-run fetch inside a systemd unit is the kind of surprise this repo exists to
avoid. A separate deliberate task, run explicitly. What remains undecided is the **path** — it is
bulk data rather than application state, so `~/.local/share` is arguable rather than obvious.]

## Recommended direction

Order matters here, and the cheap reversible things come first:

1. **Try OpenCode on Copilot by hand, before declaring anything.** It answers the open question the
   rest of the plan rests on, costs nothing, and needs no infrastructure.
2. **Declare the two zero-risk client tools** — `ccusage` and `ast-grep`. Both are read-only, both
   fit existing methods, and neither depends on any decision above.
3. **Ask about the 12 GB box** — OS, uptime, whether PULSE provisions it — and only then design the
   inference-host half against the corporate-systemd-unit precedent.
4. **Leave the gateway out** until something Anthropic-shaped actually needs the local model. It is
   the one component whose absence costs nothing.
