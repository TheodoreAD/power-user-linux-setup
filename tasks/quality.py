from invoke import task

# cli-allowlist/rules/dprint.json is the allowlist pipeline's classification-rules file for the
# "dprint" CLI tool (one file per tool, mirroring help-cache/<tool>.json) — an unrelated file that
# happens to share dprint's own config filename. Without this flag, dprint's config-discovery
# treats it as a nested sub-project config and aborts fmt/check with "No formatting plugins found".
_DPRINT_FLAGS = "--config-discovery=ignore-descendants"

# -i 4 -ci matches this repo's existing shell-script indent style (4 spaces, case labels indented
# under `case`) — shfmt's own defaults are tabs with un-indented case labels, which would rewrite
# every script's style on first run rather than just catching real drift.
_SHFMT_FLAGS = "-i 4 -ci"


@task
def lint_check(c):
    """Run ruff's linter (no fixes)."""
    c.run("ruff check .")


@task
def lint_apply(c):
    """Run ruff's linter and apply auto-fixes."""
    c.run("ruff check --fix .")


@task
def format_check(c):
    """Check formatting — ruff format and dprint — without writing changes."""
    c.run("ruff format --check .")
    c.run(f"dprint check {_DPRINT_FLAGS}")


@task
def format_apply(c):
    """Apply formatting: ruff format, then dprint fmt."""
    c.run("ruff format .")
    c.run(f"dprint fmt {_DPRINT_FLAGS}")


@task
def type_check(c):
    """Run basedpyright's type checker."""
    c.run("basedpyright")


@task
def shell_check(c):
    """Run shellcheck against every *.sh file in the repo."""
    c.run("shellcheck $(fd -e sh .)")


@task
def shell_format_check(c):
    """Check shell script formatting (shfmt) without writing changes."""
    c.run(f"shfmt {_SHFMT_FLAGS} -d $(fd -e sh .)")


@task
def shell_format_apply(c):
    """Apply shell script formatting (shfmt)."""
    c.run(f"shfmt {_SHFMT_FLAGS} -w $(fd -e sh .)")


@task
def test(c):
    """Run the pytest suite."""
    c.run("pytest tests/")


@task(pre=[lint_check, format_check, type_check, shell_check, shell_format_check, test])
def check(c):
    """CI-style gate: lint, format, type, shell, and test checks — no changes written."""


@task(pre=[lint_apply, format_apply, shell_format_apply])
def fix(c):
    """Fix everything auto-fixable: ruff --fix, ruff format, dprint fmt, shfmt -w."""


@task(pre=[fix, check])
def precommit(c):
    """Fix everything auto-fixable, then run the CI-style gate: fix, then check."""
