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

## What to do

1. **Allow `WebSearch` outright.** 858 of 1,562 prompts — 55% — for a tool with no agent-chosen
   destination to give away. This is the user's own conclusion and the structural argument above
   agrees with it.
2. **Allow `WebFetch(domain:…)` for a small set of high-volume, low-risk hosts** and leave the rest
   prompting: `github.com`, `raw.githubusercontent.com`, `api.github.com`, `pypi.org`,
   `code.claude.com`, `docs.python.org`, `docs.astral.sh`, `docs.pytest.org` ≈ 40% of fetches.
3. **Keep the long tail prompting on purpose.** `WebFetch` hit **239 distinct hosts in 30 days, 153
   of them exactly once**, and the top 18 hosts are only 50% of calls. A novel destination is
   precisely where a human look is worth having, so the tail is not a gap in the design — it is the
   design.

Net effect: `acceptEdits` web prompts fall from ~1,562 to ~420 a month, and those 420 are the ones
worth reading. That removes the reason the machine runs auto, without asking anyone to accept more
risk.

[PITFALL: **the `cli-allowlist` pipeline cannot express any of this.** `tasks/allowlist.py` emits
only `Bash(...)` patterns — `_render` has no concept of a non-Bash tool — so the highest-value
permission change available to this machine has no home in the repo that owns its permissions.
`inv allowlist.apply` would not clobber a hand-added rule (it tracks a manifest of rules it wrote
and touches nothing else), so a hand edit survives — but it would exist only on this machine, which
is the divergence PULSE exists to prevent.]

## Open questions

[NEEDS CLARIFICATION: where non-Bash tool rules should be declared. Candidates: a new table in
`cli-allowlist/tools.toml` that `_render` reads alongside the Bash rules; a `claude_permissions`
field on `[packages.claude-code]` beside `claude_default_mode`; or a separate small file the same
task applies. The first keeps one pipeline; the second keeps harness config with the harness
package, which is where `claude_default_mode` and `claude_additional_directories` already live.]

[NEEDS CLARIFICATION: whether the `WebFetch` domain list is maintained by hand or derived. Deriving
it from transcript frequency is tempting and wrong for the same reason the tail is kept prompting —
a host becomes allowed by being used often, which is not a security property. Hand-maintained and
short is probably right, with the measured distribution used only to choose the first entries.]

[NEEDS CLARIFICATION: whether anything should be done about internal HTTPS reachability. The
HTTP→HTTPS upgrade covers plaintext services by accident. A `deny` rule for private address literals
would be explicit rather than incidental, but `WebFetch(domain:…)` matching against raw IPs and
whether a deny can express a CIDR range are both unverified.]

## Recommended direction

Land 1 and 2 through whichever declaration mechanism the first open question settles, measure the
prompt count after a week, and only then revisit whether `claude_default_mode` should stay
`acceptEdits` — the mode question is downstream of this one and cannot be answered while the
friction is what decides it.
