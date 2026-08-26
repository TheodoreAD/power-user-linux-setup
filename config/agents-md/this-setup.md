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

Run the `git` command as normal — `SSH_ASKPASS` (same Zenity helper, with
`SSH_ASKPASS_REQUIRE=prefer`) pops a GUI passphrase dialog when no key is loaded in the
`keychain`-managed agent, instead of failing with "Permission denied (publickey)". No HTTPS/token
workaround needed. The dialog blocks on user input and times out if nobody is at the machine.

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
against the upstream changelog, not assumed. A tool a repo's quality gate or test tasks run also
goes in that repo's dependency group — the user-wide install is for the human at the shell, the
group is what CI and consumers resolve.

### Installing agent instructions and skills on this machine

`inv ai.install-skills` sets up `~`'s `.agents/skills/` and its `.claude/skills` symlink, and
installs every skill declared in `setup.toml` (never overwriting existing content). A new Python
project's own `AGENTS.md`/`CLAUDE.md`/`.agents/skills` scaffold comes from
[`scaffoldapy`](https://github.com/TheodoreAD/scaffoldapy) at generation time, not from a task run
afterwards. The convention these implement is in "Agent instructions & knowledge" below.

### Pushing to a personal repo's default branch

Direct pushes to `main`/`master` are the norm on the user's own personal repos
(`power-user-linux-setup`, `repo-tasks`, `scaffoldapy`, ...) — sole contributor and owner, so PR
review gates nothing. A "bypassing branch protection" message on push is expected there (the rule is
a force-push guard, not a review gate) — don't flag it and don't suggest a PR. None of this
transfers to a shared/team repo with real other contributors.
