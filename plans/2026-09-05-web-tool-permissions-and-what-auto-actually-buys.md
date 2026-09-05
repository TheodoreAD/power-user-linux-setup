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

1. **Enable the Bash sandbox** and set `network.allowedDomains`. Free on this machine, and the only
   step that adds a boundary rather than removing a prompt. Take the AppArmor profile into
   `setup.toml` at the same time so it stops depending on another package's postinst.
2. **Allow `WebSearch`** at user scope on `[packages.claude-code]`. Needs no boundary, removes 55%
   of the friction.
3. **Then `WebFetch` domains**, single-tenant only, checked against the built-in preapproved set
   first, and aligned with the sandbox's `allowedDomains` rather than substituting for them.
4. **Only then revisit `claude_default_mode`.** The mode question is downstream of all of this and
   cannot be answered while the friction is what decides it.
