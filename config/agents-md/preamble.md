# Global agent instructions

This file is assembled from fragments in `power-user-linux-setup`'s `config/agents-md/` — edit the
fragment, never the deployed file, then `inv deploy.all --name agents-md`. Which fragment owns what
is in that directory's `README.md`; each rule's evidence and the admission criteria a new rule must
pass are in the same repo's `contributing/global-agents-md.md`. The `PULSE::` markers say which
fragment each section came from — this file is regenerated whole, so an edit made here is shown as a
diff and asked about on the next deploy, never silently kept.

Each cluster below is one subject. A rule heading may also carry a bracketed label naming what the
rule _assumes_: `[Claude Code]` means it describes one harness and does not transfer to another, and
`[needs <thing>]` means it holds because PULSE installed that thing and stops being true without it.
An unlabelled rule assumes neither and holds anywhere.
