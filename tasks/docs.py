import shutil
from pathlib import Path

from invoke import task

_SITE_DIR = Path(__file__).parent.parent / "site"


@task
def clean(c):
    """Remove the built docs site (site/)."""
    if not _SITE_DIR.exists():
        print("[docs] site/ not present — nothing to clean")
        return
    shutil.rmtree(_SITE_DIR)
    print("[docs] site/ removed")


@task(pre=[clean])
def build(c):
    """Build the docs site with zensical in strict mode (fails on any warning)."""
    c.run("zensical build --strict")


@task
def serve(c):
    """Serve the docs site locally with live reload (zensical serve)."""
    c.run("zensical serve")
