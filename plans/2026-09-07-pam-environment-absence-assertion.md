---
status: idea
updated: 2026-09-07
---

# Should `inv verify.all` assert that `~/.pam_environment` does not exist?

## Context

Carried out of `plans/2026-08-24-environment-d-session-env.md` when that plan was retired on
2026-09-07. Everything else in it was answered or made moot — the session environment already
reaches `app.slice`, so the `environment.d` surface it proposed is not needed, and the rationale
moved to `contributing/session-environment.md`. This question survived because it is about a
different thing: a fourth possible origin for an environment variable, on a removal timer.

**Verified 2026-08-24, and not re-checked since.** `~/.pam_environment` was deprecated in pam 1.5.0
and removed in 1.6.0. This machine runs pam 1.5.3 and still carries `user_readenv=1` in
`/etc/pam.d/gdm-password` and `/etc/pam.d/sshd`, so the file **would** be read if it existed. It
does not exist here, and nothing asserts that.

The risk is narrow but real and silent: a variable set there works today and stops working on the
Ubuntu release that ships pam 1.6, with no error anywhere — the same failure shape as every other
finding in the retired plan. Nothing in this repo writes that file; the concern is a machine where
somebody once did, by hand or by following a decade-old Ask Ubuntu answer.

## Open questions

[NEEDS CLARIFICATION: is an assertion the right instrument at all? `verify.all` is a hard,
first-failure-aborts check over what a run just installed, and this file is neither installed by
PULSE nor a failure of anything PULSE did. Failing a whole setup run over a file the user wrote
themselves years ago is a poor trade; a warning where its absence is noticed may be the honest
shape. The neighbouring precedent is section 7 of
`plans/2026-09-06-corporate-cert-proxy-wsl-gaps.md`, which declined a `verify.all` gate for the
login-shell prerequisite on the same reasoning and reported it at the point of discovery instead.]

[NEEDS CLARIFICATION: where would it be noticed? `inv home.list-claims` is the registry of what this
repo puts in the home directory, and a file PULSE never writes is out of its scope by construction.
`inv net.check` and `inv wsl.check` are diagnostics for other subjects. There may be no existing
command whose job this is, in which case the answer is "nowhere yet" rather than "verify.all".]

[NEEDS CLARIFICATION: does it deserve action before the removal actually lands? pam 1.6 is not in
any Ubuntu release this repo targets. Checking `pam --version` against the machine, and revisiting
when 1.6 appears, may be the whole of the work.]

## Recommended direction

Cheap first step, before deciding anything: confirm the 2026-08-24 reading still holds — pam's
version, whether `user_readenv=1` is still in those two files, and whether the file exists. If pam
has moved to 1.6 on this machine the question changes shape entirely, because the file would then be
inert rather than live.

Then prefer reporting over asserting, and prefer an existing diagnostic over a new one. If no
command's subject covers it, that is a finding worth recording rather than a reason to invent a
gate.
