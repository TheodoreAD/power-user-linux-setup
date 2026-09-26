---
status: idea
updated: 2026-09-05
---

# WebSearch and WebFetch are not one decision, and auto mode adds no security over acceptEdits

## Context

Asked 2026-09-05: _"in edit mode i have to validate more things than i'd like, especially web search
and fetch. web search should be enabled by default, as it's not risky from my research, but i want
you to find out how problematic both search and fetch can be and if how auto decides on running adds
any security vs edit"_. This is why the machine runs auto mode for 96% of its Bash calls despite
declaring `acceptEdits` — see `plans/2026-09-05-grep-glob-preference-is-inoperative.md`.

**No `WebSearch` or `WebFetch` rule exists in `~/.claude/settings.json` at all.** Neither is in
`allow`, `ask` or `deny`, so under `acceptEdits` both fall through to "unmatched, not built-in
read-only" and prompt on every single call.

Measured over 30 days, attributing each call to the `permissionMode` in force at its timestamp:

| tool        | calls | classifier-denied | user-declined |
| ----------- | ----- | ----------------- | ------------- |
| `WebSearch` | 858   | **0**             | 1             |
| `WebFetch`  | 704   | 10 (1.4%)         | 1             |

So `acceptEdits` costs roughly **1,562 approval prompts a month** for web work, and auto costs about
**ten false denials**. That is the whole of the friction, and it explains the mode choice
completely.

[PITFALL: **all ten classifier denials were benign, and three of them were Claude Code's own
documentation.** The blocked URLs are `pypi.org/pypi/<pkg>/json` (four of them, prompts like _"What
is the license of this package"_),
`raw.githubusercontent.com/anthropics/claude-code/main/
CHANGELOG.md`,
`code.claude.com/docs/en/errors`, and `code.claude.com/docs/en/auto-mode-config` — the classifier
blocked a session from reading the documentation about auto mode. No true positive appears anywhere
in 704 fetches, so the classifier's false-**negative** rate is entirely untested: nothing in this
corpus tells us whether it would catch a real one.]

## The two tools differ structurally, and the difference is exactly what a permission gate governs

[DECISION: **`WebSearch`'s destination is fixed; `WebFetch`'s is chosen by the agent. That single
difference carries almost the whole security argument, and it supports allowing search by default.**
`WebSearch` sends a query to one search backend and gets results; the agent controls the query text
but not where it goes. So there is **no outbound channel an attacker can aim** — no exfiltration
endpoint, no SSRF. `WebFetch` takes an arbitrary agent-chosen URL, which is simultaneously an
outbound data channel (a secret encodes fine into a path or query string) and an inbound one into
whatever network the machine sits on. Residual `WebSearch` risk is real but bounded: the query text
itself leaves the machine, so a query built from a secret leaks it to a fixed third party, and
returned snippets are an injection surface — a lower-fidelity one than a full fetched page.]

Probed on this machine 2026-09-05, rather than assumed:

- **`WebFetch` will connect to loopback, and nothing in the permission layer objects.** A local
  `python3 -m http.server` on `127.0.0.1:18099` fetched as `http://127.0.0.1:18099/` returned
  `error:100000f7:SSL routines:OPENSSL_internal:WRONG_VERSION_NUMBER` — a **TLS handshake error**,
  which proves the request reached the socket. No prompt, no classifier denial.
- **The only barrier to plaintext internal services is the HTTP→HTTPS upgrade**, documented in the
  tool's own description. It is incidental protection, not a loopback block: it happens to stop the
  `169.254.169.254` cloud-metadata endpoint (HTTP-only) and the `ingesta` dev server observed
  running on `127.0.0.1:8765`, and it does **not** stop an internal host that speaks HTTPS.
- **Cross-host redirects are returned rather than followed**, so redirect laundering to an internal
  or exfiltration host does not happen silently; the agent must re-issue the call deliberately.

[PITFALL: **the dominant `WebFetch` risk is one no permission mode touches.** The permission
decision is made on the URL, **before any content exists**. Prompt injection arrives in the fetched
page, after the gate has already said yes. So on the biggest risk the two modes are exactly
equivalent, and any argument that one mode is "safer for web fetching" is really an argument about
exfiltration and internal reads only.]

## Does auto add security over acceptEdits? No — it substitutes a weaker check for a stronger one

[DECISION: **auto reduces the check rather than adding one, but `acceptEdits`' advantage is largely
notional at current volume, and that is the finding worth acting on.** On the risks a gate can
control, `acceptEdits` puts a human on the URL and auto puts a classifier. Only the human can know
that a given URL encodes something sensitive; a classifier sees a URL that looks like analytics. And
the classifier's measured output on this corpus is 10 false positives and zero demonstrated true
positives. **But** a check performed 1,562 times a month is a click-through machine, not a check. So
the honest conclusion is not "use `acceptEdits`" — it is that **prompt volume has to come down far
enough for the remaining prompts to be read**, which is a security improvement rather than a
convenience.]

## Checked against the primary source, which killed half the first proposal

Read from `code.claude.com/docs/en/permissions` and `/sandboxing` 2026-09-05, not from a search
summary.

[DECISION: **`github.com` and `raw.githubusercontent.com` must NOT be allowlisted, and the reason is
that path scoping does not exist.** The user's instinct — _"github.com and githubusercontent.com
seem risky for prompt injection, the rule should be paths there should be safe based on the
author/org"_ — is right about the risk and unavailable as a mechanism. `WebFetch` rules match **the
hostname only**, and the docs say so twice: _"WebFetch rules use a `domain:` prefix and match
against the hostname of the requested URL"_, and, in the list of fields that cannot be matched as
input parameters, _"`url` for WebFetch"_. So `WebFetch(domain:github.com)` allows **every repository
on GitHub**, including one an attacker creates specifically to be fetched. Multi-tenant hosts are
out.]

[DECISION: **the criterion that replaces "reputable organisation" is single-tenancy.** The user's
general rule — keep adding reputable organisations' sites — is right in spirit but does not survive
domain-granularity on its own: GitHub is a reputable organisation and `github.com` is the single
worst entry available. The workable form is **allow a domain only when one organisation controls
every byte served from it.** `docs.python.org`, `docs.astral.sh`, `docs.pytest.org`, `pypi.org` and
`code.claude.com` pass. `github.com`, `raw.githubusercontent.com`, `*.github.io`,
`*.readthedocs.io`, `medium.com` and every package-registry page that renders user-supplied README
content fail. Note `api.github.com` is a genuine borderline: the API serves attacker-authored
content too, just as JSON.]

[DECISION: **no curated "safe to fetch" list exists to borrow, and the published advice is against
the idea.** Searched 2026-09-05; the agent-security material converges on the opposite of a global
list — allowlist only what the agent's job needs and deny the rest, because a domain on the
allowlist is trusted _under prompt-injection conditions_. Popularity rankings (Tranco, Umbrella)
measure traffic, not safety, which is the same flaw the user's own instinct rejected for GitHub. So
the list is hand-maintained and short, and the measured distribution only chooses its first
entries.]

[PITFALL: **a `WebFetch` allowlist is not a network boundary while Bash can fetch, and today nothing
is a network boundary.** The docs state it plainly: _"using WebFetch alone doesn't prevent network
access. If Bash is allowed, Claude can still use `curl`, `wget`, or other tools to reach any URL."_
On this machine `Bash(curl:*)` is `ask` and `wget` matches no rule — but **96% of Bash calls run
under auto**, where a classifier decides rather than the allow/ask table. So the exfiltration
channel the `WebFetch` allowlist is meant to narrow is wide open beside it, and tightening
`WebFetch` alone buys prompt reduction rather than security.]

## The actual answer is the Bash sandbox, and every prerequisite is already installed

`sandbox.network.allowedDomains` is an **OS-enforced** egress allowlist covering every Bash command
and its children — the boundary `WebFetch` rules cannot be. And `sandbox.autoAllowBashIfSandboxed`
**defaults to `true`**, so sandboxed commands run _without prompting_. That inverts the trade the
whole question assumed: it reduces friction and adds enforcement at the same time.

Verified on this machine 2026-09-05:

- `bwrap` at `/usr/bin/bwrap` and `socat` at `/usr/bin/socat` — **both already present**.
- `kernel.apparmor_restrict_unprivileged_userns` is `1`, which is the Ubuntu 24.04 blocker the docs
  warn about — **and it is already worked around.** `/etc/apparmor.d/claude-desktop-bwrap` attaches
  to `/usr/bin/bwrap` (the path, not one application) and grants `userns`, so Claude Code's sandbox
  inherits it. Confirmed by running
  `bwrap --unshare-user --unshare-net --ro-bind / / --dev /dev
  /bin/echo`, exit 0.
- `settings.json` has no `sandbox` key at all. **It is simply not switched on.**

[PITFALL: **the AppArmor workaround belongs to another package and says so.** The profile's own
header reads _"managed by the claude-desktop package (postinst); direct edits will be overwritten on
upgrade"_. So the thing making the sandbox usable here can disappear on a `claude-desktop` upgrade,
silently — and the failure mode is sandboxed commands breaking with `Operation not permitted`, not a
warning. This repo already has an `apparmor-profile` install method (used for the JetBrains IDE
profiles), so it can own an equivalent profile rather than depending on another package's
side-effect.]

## What to do

1. **Allow `WebSearch` outright.** 858 of 1,562 prompts — 55% — for a tool with no agent-chosen
   destination to give away. Interactive approval saves it "permanently per repository", which is
   why it keeps recurring; a rule at **user scope** covers every repo at once, which is the actual
   fix.
2. **Allow `WebFetch(domain:…)` only for single-tenant hosts.** Starting set: `code.claude.com`,
   `docs.python.org`, `docs.astral.sh`, `docs.pytest.org`, `pypi.org`. That is ~7% of fetches, far
   less than the 40% first proposed, because the two GitHub hosts carrying 20% are exactly the ones
   that must be excluded.
3. **Keep the long tail prompting on purpose.** 239 distinct hosts in 30 days, 153 seen exactly
   once. A novel destination is where a human look earns its place; the tail is the design, not a
   gap in it.
4. **Enable the Bash sandbox**, which is the only item here that is actually a security improvement
   rather than a friction reduction, and which is free on this machine because everything it needs
   is installed.

[PITFALL: **the `cli-allowlist` pipeline cannot express any of this.** `tasks/allowlist.py` emits
only `Bash(...)` patterns — `_render` has no concept of a non-Bash tool — so the highest-value
permission change available to this machine has no home in the repo that owns its permissions.
`inv allowlist.apply` would not clobber a hand-added rule (it tracks a manifest of rules it wrote
and touches nothing else), so a hand edit survives — but it would exist only on this machine, which
is the divergence PULSE exists to prevent. Settled 2026-09-05: the declaration goes on
`[packages.claude-code]` in `setup.toml`, beside `claude_default_mode`, since that is already where
harness configuration lives.]

## The sandbox block, drafted 2026-09-05 — for review, not applied

Everyday posture, not a hardened one. Two choices carry that:

[DECISION: **`strictAllowlist` stays OFF.** With it on, a host outside the list is denied outright;
with it off, it **prompts**. That single flag is the difference between "an incomplete allowlist
breaks your work" and "an incomplete allowlist asks you once" — and since `autoAllowBashIfSandboxed`
defaults to `true`, sandboxed commands otherwise run with no prompt at all. Net friction goes down
against today's `acceptEdits` while a real boundary appears, which is the opposite of the trade the
question assumed. The list below therefore does not need to be exhaustive to be safe to try; a gap
costs one prompt.]

[DECISION: **`~/.claude` and `~/.agents` are deliberately NOT in `allowWrite`.** They are the
persistence targets an injection wants — settings, skills, the instructions file itself. PULSE's own
deploy tasks do write there, so they will hit the sandbox and fall back to the unsandboxed retry,
which the `Bash(dangerouslyDisableSandbox:true)` ask rule already declared turns into a visible
prompt. That is the correct trade: a deploy is rare and deliberate, and it is exactly the operation
worth seeing.]

```json
{
  "sandbox": {
    "enabled": true,
    "network": {
      "allowedDomains": [
        "archive.ubuntu.com",
        "security.ubuntu.com",
        "pypi.org",
        "files.pythonhosted.org",
        "astral.sh",
        "*.astral.sh",
        "registry.npmjs.org",
        "crates.io",
        "static.crates.io",
        "proxy.golang.org",
        "sum.golang.org",
        "github.com",
        "api.github.com",
        "codeload.github.com",
        "raw.githubusercontent.com",
        "objects.githubusercontent.com",
        "cli.github.com",
        "gitlab.com",
        "dl.google.com",
        "packages.microsoft.com",
        "download.docker.com",
        "apt.releases.hashicorp.com",
        "pkgs.k8s.io",
        "pkg.claude-desktop-debian.dev",
        "api.anthropic.com",
        "claude.ai",
        "code.claude.com"
      ]
    },
    "filesystem": {
      "allowWrite": [
        "~/plans",
        "~/plans-sensitive",
        "~/.cache",
        "~/.local/state/power-user-linux-setup",
        "~/.local/state/session-bash-audit"
      ]
    }
  }
}
```

The domain list is derived, not invented: every `https?://` host in `setup.toml`, plus the apt
repositories actually configured in `/etc/apt/sources.list.d/`, plus the package registries the
toolchain reaches (`uv` → pypi + pythonhosted, `npm`, `cargo`, `go`). `allowWrite` covers the four
places daily work writes outside a repo — the plan store, which `plans.py` touches constantly, and
the caches and manifests without which `uv` and the audit baselines fail.

[PITFALL: **this machine has the preconditions for a sandbox escape, and enabling the sandbox
without closing it would report a boundary that is not one.** Found 2026-09-05, before any trial run
— which is the only reason it was found before being trusted. Three facts together:

- `@anthropic-ai/sandbox-runtime`, the **optional seccomp filter, is what adds Unix domain socket
  blocking**, and it is **not installed** (`npm ls -g` finds nothing).
- `/var/run/docker.sock` exists, mode `srw-rw---- root:docker`.
- The user **is** in the `docker` group.

The sandboxing page names this combination in its own security limitations: _"allowing access to
`/var/run/docker.sock` effectively grants access to the host system through the Docker socket."_
With no filter, Unix sockets are not blocked at all, so a sandboxed command that reaches docker.sock
leaves the boundary entirely. Filesystem and network isolation are unaffected — those are bubblewrap
and socat, both present — so the sandbox is still worth having; what is absent is the socket layer.
Closing it is one declared package in `[packages.node].global_packages`, the same route `skills`
already takes, plus a Claude Code restart, since the dependency check runs at startup.]

[PITFALL: **the same filter governs the ssh-agent socket, so a `git fetch` test run today would not
answer the question for the configuration actually worth running.** `SSH_AUTH_SOCK` is
`/run/user/1000/keyring/ssh`, a Unix socket, and with no filter installed it is reachable — so an
SSH test now would likely pass on the agent-auth path and might stop passing once the filter is
added. The test is only conclusive when run in the final shape. This is why the ordering below is
filter first, restart, `/sandbox`, then test — not the reverse.]

[NEEDS CLARIFICATION: **does the sandbox proxy carry SSH, and therefore `git push`?** This is the
single biggest unknown and the one most likely to make the sandbox feel like a slog. Every remote
here is `git@github.com`, and the proxy is described in terms of hostnames and HTTPS, with the
optional seccomp filter governing Unix sockets — nothing in the page says what happens to an
outbound TCP connection on port 22. If SSH does not traverse it, every push falls back to the
unsandboxed retry and prompts. Testable in one command once the sandbox is on: `git fetch` in any
repo. Answer this before deciding whether the block is worth applying.]

[NEEDS CLARIFICATION: **`sandbox` is a top-level settings key, so no existing mechanism carries
it.** `claude_permissions_*` merge into `permissions`, and `claude_default_mode` /
`claude_statusline` set one scalar each. A `claude_sandbox` field holding this object needs a new
`_apply_declared_sandbox()` in `tasks/ai.py`, shaped like `_apply_declared_statusline` — absent, set
it; matches, no-op; set to something else, ask before replacing. Worth writing only once the SSH
question is answered, since the answer may change the block.]

[NEEDS CLARIFICATION: whether `~/.cache` is too broad. It is there because `uv` fails without it and
`uv` runs in every gate. Narrowing to `~/.cache/uv` plus whatever else turns out to be needed is
better, but the list can only be found by running with the broad entry first and watching what a
narrower one breaks.]

## Probed 2026-09-26: the sandbox now also carries cross-repo `git -C`

The 2026-09-26 allowlist rework (plan since retired; the reasoning is in
`contributing/cli-allowlist.md`, section "`mode_covered` and `repo_dir_options`") needed somewhere
for `git -C <repo> <read>` to run unprompted. No Claude rule shape is both safe and warning-free,
and one rule per repository overran the 2 MiB settings cap, so the allowlist now renders nothing for
`-C` and relies on this sandbox. Probed with this plan's block through `claude -p --settings`
(manual mode, nobody to answer, no `-C` rules, throwaway repos outside Claude's temp directory):

| command                                     | sandbox on                          | sandbox off |
| ------------------------------------------- | ----------------------------------- | ----------- |
| `git -C <other> status` / `log`             | runs, no prompt                     | prompts     |
| `git -C <other> add x`, `touch <other>/x`   | runs, fails `Read-only file system` | prompts     |
| `git -C <other> -c core.fsmonitor=… status` | prompts                             | prompts     |
| `git reset HEAD --hard` under an ask rule   | prompts                             | prompts     |
| `curl` to an unlisted host                  | blocked, `deny network-outbound`    | —           |

A directory under `/tmp/claude-1000` is writable from inside the sandbox, so a write test placed
there passes and proves nothing; probe outside it.

[PITFALL: **inside the sandbox the session's own working directory holds placeholder device files**
— `.bashrc`, `.gitconfig`, `.gitmodules`, `.idea`, `.vscode`, `.mcp.json`, `.claude/`, each a
`crw-rw-rw- nobody nogroup` node — and `git status` lists all of them as untracked. Not seen with
`git -C` into another repository. Noise in every status an agent reads, and a hazard for any broad
stage. Needs an answer before enabling: an upstream setting, a global excludes entry, or accepting
it.]

This makes the sandbox the owner of a second job, so enabling it now removes prompts that the
allowlist deliberately stopped trying to remove.

## Re-checked against the docs and changelog, 2026-09-26 (Claude Code 2.1.283)

Read in full: code.claude.com/docs/en/sandboxing and /permissions, plus every sandbox entry in the
Claude Code changelog. What moved since 2026-09-05:

- **The placeholder files are by design, with no exemption.** The page's "Protected paths" section
  lists what the sandbox denies writes to inside writable directories — `.claude` settings and
  `skills`/`agents`/`commands`/`hooks`, `.mcp.json`, and in the working directory only shell startup
  files, `.gitconfig`, `.vscode`, `.idea`, `.git/hooks`, `.git/config` — and its Troubleshooting
  entry says that on Linux a not-yet-existing protected path gets a read-only placeholder while a
  sandboxed command runs, removed afterwards ("Stale sandbox mask files left by a killed session" in
  `claude doctor` when cleanup is skipped). "There is no way to exempt one of these paths." So the
  `git status` noise above is permanent for sandboxed commands in the session's own repository. No
  upstream issue about it was found (`gh search issues --repo anthropics/claude-code`).
- **The seccomp filter is still optional and separate**:
  `npm install -g
  @anthropic-ai/sandbox-runtime`. Not installed (npm globals here: `skills` only),
  so the docker.sock escape stands until it is. `[packages.node].global_packages` is where it would
  be declared.
- **Default writable set** is the working directory, the per-user temp dir, and every
  `permissions.additionalDirectories` entry — which here already include `~/plans` and
  `/tmp/claude-1000` (and `~/.claude/jobs`). So the drafted `allowWrite` shrinks: `~/plans` is
  covered; `~/plans-sensitive` is not.
- **`docker` is documented as incompatible with the sandbox**; the fix the docs give is
  `sandbox.excludedCommands: ["docker *"]`, which runs it outside under the normal permission rules.
- **User-wide enabling needs `sandbox.enabled` in `~/.claude/settings.json`.** `/sandbox` saves only
  to the current project's `.claude/settings.local.json`. So the `claude_sandbox` field and an
  `_apply_declared_sandbox()` in `tasks/ai.py` remain necessary, as below.
- **The AppArmor profile now has a canonical form in the docs** (`/etc/apparmor.d/bwrap`,
  `profile bwrap /usr/bin/bwrap flags=(unconfined) { userns, ... }`), which PULSE's existing
  `apparmor-profile` method can own, ending the dependency on `claude-desktop`'s postinst.
- **HTTPS git through the proxy works** (changelog: "Fixed sandboxed `git` asking credential helpers
  to store the sandbox proxy's login"). SSH is still undocumented, and every remote here is SSH.

## Decisions parked for the user, 2026-09-26

The user stopped here deliberately: this is a larger change to the system than it looked, and each
of these wants thought before anything is installed.

[NEEDS CLARIFICATION: **the placeholder files in `git status`.** Options on the table: deploy
root-anchored entries (`/.bashrc`, `/.gitconfig`, `/.idea`, `/.vscode`, `/.mcp.json`, ...) to the
global git excludes file through PULSE, at the cost of also hiding a genuinely new untracked file at
one of those exact paths (tracked files are unaffected); accept the noise and tell agents in
`AGENTS.md`; or report upstream first.]

[NEEDS CLARIFICATION: **`docker` under the sandbox.** Exclude it (`excludedCommands: ["docker
*"]`,
running under the normal permission rules, where the read-only docker verbs are already allowed), or
leave it sandboxed and let every docker call go through the unsandboxed-retry prompt.]

[NEEDS CLARIFICATION: **whether and when to install.** The seccomp package is a user-level npm
global; the AppArmor profile needs a `sudo -A` password dialog. Nothing is installed or declared
yet; the order in "Recommended direction" below still holds.]

## Open questions

[NEEDS CLARIFICATION: whether `WebFetch` should be allowlisted at all before the sandbox is on.
Given that Bash-based fetching is unbounded under auto, a `WebFetch` domain list is prompt reduction
wearing security's clothes. The sequencing that makes each step honest is: sandbox first, so there
is a real egress boundary; `WebSearch` allow, which needs no boundary; and `WebFetch` domains last,
against the sandbox's `allowedDomains` rather than instead of them.]

[NEEDS CLARIFICATION: what the built-in preapproved documentation domains already cover. The
permissions page says `WebFetch` prompts _"except a built-in set of preapproved documentation
domains"_ and points at `tools-reference#webfetch-tool-behavior`, which has not been read. Some of
the five proposed hosts may already be free, which would shrink the list further — and a rule
duplicating a built-in is a rule to maintain for nothing.]

[NEEDS CLARIFICATION: whether `api.github.com` is in or out. It is the one borderline case in the
single-tenancy criterion: GitHub operates it, but what it serves is user-authored content rendered
as JSON, so an injection payload reaches the model just as readily as through the HTML site. Out on
a strict reading, and it is 17 of 704 fetches, so the cost of excluding it is small.]

[NEEDS CLARIFICATION: whether anything should be done about internal HTTPS reachability. The
HTTP→HTTPS upgrade covers plaintext services by accident. A `deny` rule for private address literals
would be explicit rather than incidental, but `WebFetch(domain:…)` matching against raw IPs and
whether a deny can express a CIDR range are both unverified.]

## Recommended direction

In order, because each step makes the next one honest:

1. **Enable the Bash sandbox**, in this order, because two of the steps change what the others
   measure — deferred 2026-09-05, nothing applied:
   1. Declare `@anthropic-ai/sandbox-runtime` in `[packages.node].global_packages` and install it,
      closing the docker.sock escape above. Optional in the sense that the sandbox runs without it;
      not optional on a machine whose user is in the `docker` group.
   2. Restart Claude Code — the dependency check runs at startup.
   3. Open `/sandbox`, auto-allow mode, `strictAllowlist` left off. Interactive, so it is the user's
      step; the harness writing the setting itself is the sanctioned exception to "settings.json is
      declared, not edited".
   4. Test in that shape and not before: `git fetch` (the SSH question), `inv quality.precommit` (uv
      cache plus network), and a `plans.py` write to `~/plans`.
   5. Only then write `claude_sandbox` + `_apply_declared_sandbox()` and move the settled block into
      `setup.toml`, so the mechanism is built around a configuration known to work.

   Take the AppArmor profile into `setup.toml` at the same time so it stops depending on another
   package's postinst.
2. **Allow `WebSearch`** at user scope on `[packages.claude-code]`. Needs no boundary, removes 55%
   of the friction.
3. **Then `WebFetch` domains**, single-tenant only, checked against the built-in preapproved set
   first, and aligned with the sandbox's `allowedDomains` rather than substituting for them.
4. **Only then revisit `claude_default_mode`.** The mode question is downstream of all of this and
   cannot be answered while the friction is what decides it.
