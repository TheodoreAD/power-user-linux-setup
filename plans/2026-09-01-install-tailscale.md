---
status: idea
updated: 2026-09-01
source_repo: github.com-personal/ingesta
source_session: bf19d40e-bb8f-4341-a396-77194e946991.jsonl
source_moment: 2026-09-01T18:30:18Z
---

# Install Tailscale as part of the machine setup

## Context

A personal project on this machine needs a **secure browser context reachable from a phone** — a
service worker only registers over HTTPS, and the `localhost` exemption does not extend to a phone
on the LAN, so an offline-capable web app cannot be tested on a real device at all without one. A
tailnet supplies exactly that with no domain, no certificate authority and no inbound port:
`tailscale serve` publishes a local port on the machine's MagicDNS name over HTTPS with the
certificate managed for you.

That project's plan settled on this route on 2026-09-01, and then found **Tailscale is not installed
on this machine** — `which tailscale` finds nothing. It is a machine-level install (an apt
repository, a daemon, a one-time browser login), so by this repo's own rule it is a `setup.toml`
entry rather than a one-off `curl | bash`, and it is filed here rather than performed from a session
working in the other repo.

Not project-specific, which is why it is worth a `setup.toml` entry rather than a note in that
project: a tailnet is the general answer to "reach this machine from my phone, or reach another
machine of mine, without exposing anything", and this workstation currently has no answer to that at
all.

## Evidence

The need and the route are recorded in the other project's own plan,
`plans/2026-09-01-shipping-to-a-phone.md`, whose recommended first step is:

> Serve `web/` to a phone from this machine, over the tailnet. Tailscale on this machine and on the
> two phones, MagicDNS and HTTPS certificates enabled, `tailscale serve` in front of the static
> server the harness already runs.

Facts gathered in that session, from Tailscale's own documentation, that bear on how the entry
should be written:

- HTTPS certificates require **MagicDNS enabled** and **HTTPS enabled** in the tailnet's DNS
  settings, and acknowledging that machine names are published to a **public Certificate
  Transparency ledger**. That last one is a naming decision, not a checkbox: the name is permanent
  and public.
- `tailscale cert` writes cert files and leaves **renewal to you** — 90-day expiry, and the daemon
  does not reinstate a file-based cert. `tailscale serve` manages it instead. Prefer `serve`.
- Let's Encrypt rate limits apply; repeated certificate requests can mean a **34-hour** wait.
- The free **Personal** plan was restructured in April 2026 to **6 users and unlimited user
  devices**, so a personal tailnet across a workstation and a couple of phones costs nothing and has
  no device ceiling to plan around.

## Open questions

[NEEDS CLARIFICATION: which install method the `[packages.tailscale]` entry should use. Unlike the
usual case, there is **no maintained PyPI wrapper** to prefer here — Tailscale ships an apt
repository with a signing key, which is the upstream-supported route on Ubuntu and the one that gets
security updates through the ordinary `apt upgrade`. The `uv-tool`-first rule does not apply to a
system daemon. Whether this repo's manifest already has a shape for "apt repository plus key" or
needs one is the actual question, and it is answerable by reading `setup.toml` rather than by
research.]

[NEEDS CLARIFICATION: whether the entry should stop at installing the daemon, or also enable and
start it. Enabling `tailscaled` on a machine nobody has logged in yet is inert and harmless; a task
that runs `tailscale up` is not, because it opens a browser for authentication and blocks. The
authentication is a human gesture either way, so the likely answer is install and enable, then print
what the human has to do — but that is this repo's convention to decide, not the calling project's.]

[NEEDS CLARIFICATION: whether the two admin-console settings (MagicDNS, HTTPS certificates) belong
in a documented checklist here or stay entirely in the consuming project. They are tailnet-wide
rather than machine-level, so they are configured once for an account and not per machine — which
argues for a line in this repo's docs and nothing executable.]

## Recommended direction

1. A `[packages.tailscale]` entry in `setup.toml` using Tailscale's own apt repository, following
   whatever shape this manifest already uses for a keyed third-party repository. Install and enable
   the daemon; do not attempt to log in.
2. One line in the relevant docs saying what the human does once: `sudo tailscale up`, then enable
   MagicDNS and HTTPS certificates in the admin console, and choose a machine name that **names no
   person** — it becomes publicly searchable in the CT ledger.
3. Prefer `tailscale serve` over `tailscale cert` anywhere this repo's docs or tasks mention issuing
   a certificate, for the renewal reason above.
