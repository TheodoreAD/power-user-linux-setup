---
status: idea
updated: 2026-11-08
source_repo: github.com-personal/hekate
source_session: 5f84bc91-7291-42b4-9474-846d42d45b23.jsonl
source_moment: 2026-11-08T15:45:38Z
source_plan: github.com-personal/hekate/2026-11-08-hekate-tilt-kind-monorepo.md (plans store)
---

# Opt ctlptl out of usage analytics when installing it

## Context

A follow-up to `2026-11-08-ctlptl-package.md`, filed into this repo's store mirror the same day,
which adds `[packages.ctlptl]` to `setup.toml` modelled on tilt's entry. Filed as a separate plan
rather than an edit to that one, which may already be held or absorbed by a session working here.
Merge the two on absorption: this is one more step for the same package.

ctlptl sends anonymized usage statistics by default. Its README says so in one line and names the
opt-out: "`ctlptl` sends anonymized usage statistics, so we can improve it on every platform. Opt
out with `ctlptl analytics opt out`." The client is `tilt-dev/wmclient`'s remote analytics, wired up
in `pkg/cmd/analytics.go`. Read from a clone of `tilt-dev/ctlptl` at `main@9a9f7b1`, in the research
library, 2026-11-08.

Per the home rule that a feature phoning home by default is a decision rather than a default, the
install should pin it off deliberately.

## Evidence

- Transcript: the hekate session named in `source_session`, at the `source_moment` turn, while
  answering whether a Windows/WSL machine could join hekate's kind cluster.
- The user chose "File the opt-out (Recommended)" when asked whether the ctlptl package entry should
  also run `ctlptl analytics opt out`.

## Open questions

[NEEDS CLARIFICATION: where the opt-out state is stored, and whether running the command once at
install time is enough or it has to be re-applied, for instance after an upgrade or on a fresh home
directory. Check `wmclient`'s analytics package, not yet cloned, before choosing how the install
task applies it.]

[NEEDS CLARIFICATION: whether tilt's existing package entry already opts tilt out of its own
analytics, which uses the same `wmclient` library. If not, the same fix probably applies there.]

## Recommended direction

- Run `ctlptl analytics opt out` as a post-install step of `[packages.ctlptl]`, idempotently.
- Add a verify step that reads back the opt-out state, so a regression is reported instead of
  silently sending data again.
- If tilt has the same gap, fix both in one change.
