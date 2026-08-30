# Global agent instructions

This file is assembled from fragments in `power-user-linux-setup`'s `config/agents-md/` — edit the
fragment, never the deployed file, then `inv deploy.all --name agents-md`. Which fragment owns what
is in that directory's `README.md`; each rule's evidence and the admission criteria a new rule must
pass are in the same repo's `contributing/global-agents-md.md`. The `PULSE::` markers say which
fragment each section came from — this file is regenerated whole, so an edit made here is shown as a
diff and asked about on the next deploy, never silently kept.

## This machine & this setup

Rules that are true because of how this particular machine and this user's repos are set up. Nothing
here is a general convention — on a different machine most of it is simply wrong.

### sudo

Always `sudo -A`, never plain `sudo` — `SUDO_ASKPASS` points at `~/.local/bin/askpass-zenity`, a
Zenity GUI password dialog, and plain `sudo` fails because the Bash tool has no TTY.

```shell
sudo -A apt install -y something   # correct
sudo apt install -y something      # wrong — hangs or "sudo: a terminal is required"
```

### git fetch/push needing an SSH key

**Run the plain `git` command — `git push`, `git fetch`, no prefix and no wrapper.** That is the
normal case and it is what to reach for every time. Keys live unlocked in the desktop keyring's
agent from login, and `~/.zprofile` points each shell at whichever agent actually holds keys, so
this normally just works with no prompt. `SSH_ASKPASS` (same Zenity helper,
`SSH_ASKPASS_REQUIRE=prefer`) pops a GUI passphrase dialog for a key that genuinely needs one; it
blocks on user input and times out if nobody is at the machine. No HTTPS/token workaround needed.

Everything below fires **only after a command has actually failed.** None of it is setup to do
first.

**When it fails with "Permission denied (publickey)", run `inv ssh.check` before anything else** —
do not reach for `ssh-add`, and never ask the user for a passphrase on the strength of that error.
This machine runs two agents (the keyring's and keychain's), and a shell pinned to the empty one
fails exactly that way while every key sits unlocked in the other. Confirmed 2026-08-28: a session
read the failure as a missing key, ran `ssh-add`, and had the user type a passphrase into three
dialogs for a key that was already loaded elsewhere and needed none. A session's own shell snapshot
is captured once and survives a reboot, so an agent session is the most likely thing to be holding a
stale socket. `ssh-add -l` exits 0 with keys, 1 for a live but empty agent, 2 for no agent — those
last two look alike and mean opposite things.

**When `ssh.check` has told you to, apply its verdict as a per-call prefix, not as an `export`.**
`ssh.check` ends with `export SSH_AUTH_SOCK=/run/user/1000/keyring/ssh` for a human's interactive
shell; an agent's Bash calls each get a fresh shell, so the export evaporates and the next command
fails exactly as before — which reads as "the fix didn't work" and sends the session back toward
`ssh-add`. Prefix instead, on every ssh call **for the rest of that diagnosis**:
`SSH_AUTH_SOCK=/run/user/1000/keyring/ssh git push`. Confirmed 2026-08-29: a session pushed with the
prefix, then ran a bare `git fetch` two turns later and got the same publickey error while every key
sat unlocked in the keyring's agent. The prefix is the repair for a shell pinned to the empty agent
— not the house style for pushing, and a session that has not seen a publickey failure should never
be typing it. `gh` is not affected — it authenticates with its own token, verified in the same
session — so a green `gh` command is not evidence that the shell's ssh agent is the right one.

### Formatting a date or decimal in a shell script

This machine's `LC_TIME`/`LC_NUMERIC` default to `ro_RO.UTF-8` (mixed locale — `LANG`/`LC_MESSAGES`
stay `en_US.UTF-8`), so `date` with a locale-sensitive specifier (`%a`, `%b`, ...) or `awk`/`printf`
with a decimal format silently emits Romanian-locale output. Force the C locale —
`LC_TIME=C date ...`, `LC_NUMERIC=C awk ...`. "The terminal looks fine" is not proof — verify the
actual bytes.

### Installing a tool on this machine

Never as a one-off manual step (`curl | bash`, a release tarball into `~/.local/bin`,
`gh extension install`) — every tool is a `[packages.<name>]` entry in `power-user-linux-setup`'s
`setup.toml`, installed by its `inv` task, or the machine silently diverges from its own setup and
the next machine never gets it. Look for a maintained PyPI wrapper first (`shellcheck-py`,
`shfmt-py`, `actionlint-py`, `act-bin` — `method = "uv-tool"`) before any other method, so setup
stays one mechanism deep; "maintained" means its version tracks the upstream release, checked
against the upstream changelog, not assumed. Judge the wrapper from its own PyPI file list
(`curl -s https://pypi.org/pypi/<name>/json`), never from a search summary: platform-tagged wheels
mean the binary ships inside one, an sdist alone means it fetches at install time, and the file
sizes and release count are the adoption cost. Measured 2026-08-26, both directions in one session —
a summary claimed `hadolint-py` downloads at install (it ships real 12 MB wheels, and was nearly
rejected for a false reason), while `lychee-bin` turned out to be a 78 MB wheel with exactly one
release ever, which reversed the decision that had already been made to adopt it. A tool a repo's
quality gate or test tasks run also goes in that repo's dependency group — the user-wide install is
for the human at the shell, the group is what CI and consumers resolve.

### Installing agent instructions and skills on this machine

`inv ai.install-skills` sets up `~`'s `.agents/skills/` and its `.claude/skills` symlink, and
installs every skill declared in `setup.toml` (never overwriting existing content). A new Python
project's own `AGENTS.md`/`CLAUDE.md`/`.agents/skills` scaffold comes from
[`scaffoldapy`](https://github.com/TheodoreAD/scaffoldapy) at generation time, not from a task run
afterwards. The convention these implement is in "Agent instructions & knowledge" below.

**Every skill on this machine is authored in `agent-skills`** — published as
`TheodoreAD/agent-skills`, checked out alongside the other personal repos — not in
`power-user-linux-setup`, which only installs them. To change one, edit it there and follow the
`skill-authoring` skill's sequence; the step that gets skipped is the push, because the installer
clones from the remote, so a committed but unpushed edit reaches nothing. Never edit the copy under
`~/.agents/skills/` — the next install overwrites it and it never leaves this machine.

### Pushing to a personal repo's default branch

Direct pushes to `main`/`master` are the norm on the user's own personal repos
(`power-user-linux-setup`, `repo-tasks`, `scaffoldapy`, ...) — sole contributor and owner, so PR
review gates nothing. A "bypassing branch protection" message on push is expected there (the rule is
a force-push guard, not a review gate) — don't flag it and don't suggest a PR. None of this
transfers to a shared/team repo with real other contributors.
