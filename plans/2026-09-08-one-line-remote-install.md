---
status: idea
updated: 2026-09-08
---

# A one-line clone-and-install for a fresh machine

**The ask, stated 2026-09-08:** an install script that works in one line, so a person can clone and
install in one go — a bootstrap, in the sense the word has outside this repo.

## Context

Today the README's quick start is six lines: `cd ~`, `mkdir -p projects`, `cd projects`,
`git clone …`, `cd power-user-linux-setup`, `./bootstrap.sh`, `inv setup`. Nothing is wrong with
them, but they are six chances to be somewhere unexpected on a machine that has nothing on it yet,
and the first thing a fresh Ubuntu install cannot do is remember which directory you meant.

**Most of the work already exists, and it is not `bootstrap.sh`.** `bootstrap.sh` has to be run from
inside a checkout — it reads `${SCRIPT_DIR}/setup.toml` for the Python versions and the
`install_repo_tasks` default — so it can never be the thing you curl. The script that already does
the whole job is **`bootstrap-devcontainer.sh`**: it clones a pinned ref, runs `bootstrap.sh`,
re-exports `PATH`, and runs `inv setup`. A workstation entry point is that script with three
decisions changed, not a new design.

## What the existing script already settled, and must not be re-litigated

[PITFALL: **`curl … | bash` is ruled out here by measurement, not by taste, and it is the exact
shape "one line" asks for.** A pipeline reports its last command's status, so a failed download
hands bash an empty stdin and the whole thing exits 0 — the install claims success having done
nothing. `bootstrap-devcontainer.sh`'s header records the measurement against a ref that did not
exist: `curl -f` exits 22, the pipeline exits 0, the download-to-a-file form exits 22. A proxy error
page or a network blip does the same thing. So the one-liner is
`curl -fsSL <url> -o /tmp/pulse-install.sh && bash /tmp/pulse-install.sh` — still one line to paste,
and the `&&` is what makes it honest.]

Two further consequences fall out of the same choice, and both of them are reasons a workstation
install needs it even more than a container does:

- **`bootstrap.sh` asks a question.** The repo-tasks prompt is guarded by `[ -t 0 ]`, so a piped
  stdin does not merely lose the prompt — it silently takes `setup.toml`'s default and the user
  never learns a choice existed. A downloaded script keeps the terminal on stdin.
- **`inv setup` needs root, and collects it outside invoke.** `util.ensure_sudo()` falls back to
  "`sudo -v` as a plain subprocess owning the real terminal" when no GUI askpass can work — and on a
  fresh machine there is no `~/.local/bin/askpass-zenity` yet, because PULSE is what installs it. A
  piped stdin is exactly the case that has no terminal to own.

## The three decisions that differ from the container script

1. **The clone destination is permanent and load-bearing.** The container script clones into
   `~/.local/share/pulse-devcontainer-src` and `rm -rf`s it first, because nothing there outlives
   the image. On a workstation the opposite is true in a way that is easy to miss: `spowse` is
   installed `--editable` against the checkout, and `deploy.status` compares the machine to it, so
   **the directory the installer picks is a permanent dependency of the machine.** Probed 2026-09-08
   (see the portability plan): move the checkout and `spowse` dies at import with
   `ModuleNotFoundError: No module named 'tasks'`, naming neither the path nor this repo. So the
   installer must never `rm -rf` a destination, must adopt an existing checkout rather than clobber
   it, and should say the path out loud when it finishes.
2. **The tag defaults are the machine's, not the container's.** No `CONTAINER_EXCLUDE_TAGS`, and no
   `PULSE_ASSUME_YES=1` — that flag exists because unattended provisioning must overwrite a base
   image's dotfiles, which is the wrong default for a person's home directory. Pass `--yes` through
   for someone who wants it.
3. **How far the one line should go.** The container script runs `inv setup` to completion because
   an image build has no user to ask. A workstation run has a terminal, and `inv setup` installs apt
   packages, changes the shell and writes GNOME settings — the least reversible thing this repo
   does. Recommended below.

## Open questions

[NEEDS CLARIFICATION: **does the one line stop after `bootstrap.sh`, or run `inv setup` too?**
Stopping leaves the user two lines from done (`cd <path>` and `inv setup`) and makes the dangerous
half a deliberate command, which is the conservative reading of "clone and install". Running it
through is what "in one go" plainly asks for, and the run is interactive anyway. Recommendation
below is to go all the way with a printed summary and a confirmation before the `inv setup` step,
`--yes` to skip it — but this is the user's call, since it decides what a pasted line does to a
machine.]

[NEEDS CLARIFICATION: **the name and the URL.** `install.sh` is the ecosystem shape — it is what uv
itself uses (`curl -LsSf https://astral.sh/uv/install.sh | sh`) and what a person guesses. The
repo's own convention is the `bootstrap-` prefix, which would make it `bootstrap-remote.sh`.
`install.sh` is recommended: the README URL is the interface here, and it is read by people who have
never seen this repo's file naming.]

[NEEDS CLARIFICATION: **which ref does it clone?** `stable` is what the container script pins, moved
forward by CI only on a green smoke test, and reusing it costs nothing and introduces no new
concept. `master` gets the newest work and is what the README's manual clone gets today, so the two
documented paths would install different things. Recommended: `stable`, with `--ref` to override,
and the README's manual instructions changed to match so there is one answer.]

[NEEDS CLARIFICATION: **is the shared logic worth factoring?** The clone-then-`bootstrap.sh`-then-
`inv setup` spine is common to both scripts, but the three decisions above differ at every step, and
`bootstrap-devcontainer.sh` is on a CI smoke test that a refactor would be risking for a distributed
entry point. Leaning: leave them as two scripts and keep the never-pipe rationale in one place
rather than copied, since that is the part that is expensive to rediscover.]

## Recommended direction

1. **`install.sh` at the repo root**, a sibling of `bootstrap.sh` and `bootstrap-devcontainer.sh`,
   with the same download-to-a-file usage comment at the top and a pointer to the measurement rather
   than a restatement of it.
2. **Options that mirror the container script's**: `--ref <git-ref>` (default `stable`),
   `--dir <path>` (default `~/projects/power-user-linux-setup`), `--exclude-tags <tags>`,
   `--bootstrap-only`, `--yes`.
3. **Adopt, never clobber.** An existing directory that is a PULSE checkout is fetched and reused;
   an existing directory that is anything else is a refusal naming the path, not a `rm -rf`.
4. **Confirm before `inv setup`**, print the checkout path on the way out, and say that the path is
   permanent because `spowse` and `deploy.status` both resolve through it.
5. **One README quick start, not two.** The one-liner becomes the quick start; the six manual lines
   stay underneath as "or, step by step", on the same ref.
6. **Not a `curl | bash`, and not a `sudo bash`.** The script collects root the way `inv setup`
   already does, through `util.ensure_sudo()`, so nothing runs as root that does not need to.

[DECISION: **this is a distribution entry point, so it is pinned and inspectable rather than
convenient.** A pasted line runs unreviewed code with access to sudo on a fresh machine, which is
the one place this repo's usual "it is only my machine" reasoning does not apply — the audience is
whoever reads the README. The download-to-a-file form is what makes inspection possible at all
(`less /tmp/pulse-install.sh` before `bash`), and pinning to `stable` is what makes what you
inspected yesterday the same as what you run today.]
