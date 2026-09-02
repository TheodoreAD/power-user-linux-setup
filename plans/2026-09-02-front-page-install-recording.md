---
status: idea
updated: 2026-09-02
---

# A terminal recording of the install, on the front page

Asked for 2026-09-02: an asciinema-style recording of the install running **in a Docker container**,
for the docs front page — the container specifically because it is easier to build against than a
real machine.

## Context

`docs/index.md` opens with a paragraph, four use-case cards, then "What you get, out of the box" and
a **Quick start** code block that is the whole story in five lines: clone, `./bootstrap.sh`,
`inv setup`. A recording belongs directly above or beside that block, because it answers the
question the block only asserts — what actually happens when you run it.

The container is the right stage for three reasons beyond the one given:

- **It is already a supported path**, not a prop. `docker/Dockerfile` exists as the canonical
  example and local-WIP vehicle, reusing `bootstrap-devcontainer.sh --local`, and
  `devcontainer.CONTAINER_EXCLUDE_TAGS` is the single source of truth for the tag profile. A
  recording made there records a path the repo already claims works.
- **It is reproducible.** A recording of this machine is a recording of one machine's history — warm
  caches, existing installs, whatever is already on `PATH`. A container starts from the image every
  time, so the recording can be regenerated when the output changes rather than being a one-shot
  artifact nobody dares re-cut.
- **It cannot leak.** A terminal recording captures the prompt, the cwd and anything the commands
  print. On this machine that includes work roots and client repo names, which `~/AGENTS.md`'s
  publication rule forbids in a published repo — and a `.cast` file is text that goes into git and
  onto a public site. A container has none of those paths to capture. Whatever is recorded, run
  `plans.py scan --mode staged` over the artifact before committing it, because a cast is text and
  the scanner can read it.

Nothing for this exists yet: no recording tool is declared in `setup.toml` (checked — the apparent
hits are substring noise in "tagged"/"aggressive"), and neither `mkdocs.yml` nor any page references
a player.

## Open questions

[NEEDS CLARIFICATION: **which run is the recording of.** Three candidates, and they tell different
stories. (a) `./bootstrap.sh` alone — 30 seconds, honest, and undersells the project. (b) The full
`inv setup` under `CONTAINER_EXCLUDE_TAGS` — the real story, but ten-plus minutes of apt output that
has to be compressed hard to be watchable. (c) `PULSE_DRY_RUN=1 inv setup` — fast, deterministic,
shows the five-phase structure, and shows nothing actually being installed, which is either honest
framing or a bait-and-switch depending on how it is labelled. Recommendation is (b), compressed,
with (a) as a fallback if (b) cannot be got under about 90 seconds.]

[NEEDS CLARIFICATION: **whether the front page gets one recording or one per use-case card.** The
four cards — full workstation, headless, dev container, WSL2 — are the page's existing structure,
and a per-card recording would be the natural extension of it. That is four artifacts to regenerate
on every output change, against one. Start with one.]

## Recommended direction

### 1. Record a real run, never a scripted re-enactment

[PITFALL: **the tempting shortcut here fabricates evidence.** Every scripted-terminal tool — VHS's
`.tape` files most of all — will happily type a command and display output you wrote by hand. That
produces a clean, perfectly-timed recording of an install that never ran, on a front page whose
whole claim is reproducibility, and nothing about the artifact would say so. The recording must be a
capture of a real container run. Scripting may drive the _input_ (which keys are typed, and when);
it may never supply the output.]

This also decides the tool question below more than any feature comparison does.

### 2. Tool: `asciinema` to capture, and decide the render separately

Two decisions that are usually conflated:

- **Capture** — `asciinema rec` produces a `.cast`: a small JSON-lines file of real terminal output
  with timings. It is text, so it diffs, greps, and can be scanned for private names before it is
  committed. `--idle-time-limit 1` collapses the long apt waits without touching the content, which
  is exactly the compression this needs and is not available from a video format.
- **Render** — the `.cast` can be played by the asciinema player (JS + CSS, selectable text) or
  converted to a GIF by `agg`, or to an animated SVG.

VHS is the strongest alternative and is rejected for the reason in the pitfall above: its model is a
script that drives a terminal, and its convenience is precisely that it makes hand-authored demos
easy. It also emits video, so the compression trick is a re-encode rather than a metadata change.
Worth revisiting if the capture-real-output constraint is ever relaxed.

Both `asciinema` and `agg` go in `setup.toml` like anything else — never a manual install. Check for
a maintained PyPI wrapper first (`method = "uv-tool"`) and judge it from its own PyPI file list
rather than a search summary, per `~/AGENTS.md`'s installing-a-tool rule; `asciinema` was a Python
project historically and is Rust from v3, and `agg` is Rust, so the wrapper question has a real
answer that must be looked up rather than assumed.

### 3. Render without a CDN

[PITFALL: **the docs theme's existing diagram support is a CDN dependency, and copying that pattern
would repeat a fault this repo just measured.** The built bundle carries no mermaid — it lazy-loads
`https://unpkg.com/mermaid@11/dist/mermaid.min.js` when it finds a diagram. Confirmed 2026-09-02
while verifying the diagrams render (`2026-08-27-docs-site-usability.md`). So a reader behind a
proxy that blocks unpkg sees diagram source as plain text — on a site with a whole page about
corporate proxies. Do not add a second such dependency by pulling the asciinema player from a CDN.]

So either vendor the player's JS and CSS into `docs/extra/` and reference them from `mkdocs.yml`, or
render to an artifact that needs no JavaScript at all. The second is cheaper and degrades better;
the first keeps selectable, copy-pasteable text, which for a page whose subject is commands is a
real benefit rather than a nicety. Decide with the size of the vendored player in hand.

### 4. Regeneration is a task, and the output is committed

Per `~/AGENTS.md`'s regeneration rule: a deliberate standalone command (`inv docs.record` or
similar), never wired into `fix`/`check`/`precommit`, and the artifact committed rather than
gitignored as "reproducible". The recording is evidence about a version of the software, so
`git log` on it is how "what did the install look like then" gets answered. No CI job may commit a
regenerated recording back to a branch.

## Files this would touch

- `setup.toml` — one `[packages.*]` entry per tool
- `tasks/docs.py` — the record task, alongside `build`/`serve`/`clean`
- `docker/Dockerfile` or `bootstrap-devcontainer.sh` — the recording stage, if it needs one
- `docs/index.md`, and `docs/extra/` plus `mkdocs.yml` if the player is vendored
- `CONTRIBUTING.md` — the docs-site section, which already documents `docs.*`

## Verification

The recording plays on the built site (`inv docs.build`, then headless Chrome over the built page —
`google-chrome --headless=new --screenshot --virtual-time-budget=…`, which is how the mermaid
diagrams were verified on 2026-09-02 and needs no human to look). A strict build passing proves
nothing about a player, exactly as it proved nothing about the diagrams.
