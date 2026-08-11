from invoke import task

# cli-allowlist/rules/dprint.json is the allowlist pipeline's classification-rules file for the
# "dprint" CLI tool (one file per tool, mirroring help-cache/<tool>.json) — an unrelated file that
# happens to share dprint's own config filename. Without this flag, dprint's config-discovery
# treats it as a nested sub-project config and aborts fmt/check with "No formatting plugins found".
_DPRINT_FLAGS = "--config-discovery=ignore-descendants"


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
def test(c):
    """Run the pytest suite."""
    c.run("pytest tests/")


@task(pre=[lint_check, format_check, test])
def check(c):
    """CI-style gate: lint, format, and test checks — no changes written."""


@task(pre=[lint_apply, format_apply])
def apply(c):
    """Fix everything auto-fixable: ruff --fix, ruff format, dprint fmt."""


@task(pre=[apply, check])
def fix(c):
    """Fix everything auto-fixable, then run the CI-style gate: apply, then check."""
