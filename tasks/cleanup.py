from invoke import task

from . import apt, docker, node, python, tools


@task(pre=[apt.clean_cache, python.clean_cache, node.clean_cache, tools.clean_cache])
def caches(c):
    """Conservatively remove build/download caches left behind by apt, uv, npm, and cargo
    installs (each self-skips if that tool isn't installed) — keeps entries still useful for a
    future install (e.g. apt.clean-cache's `autoclean`, uv's `cache prune`), only removing what's
    already unreachable/obsolete. Opt-in: not part of `inv setup`, since a persistent workstation
    usually wants to *keep* these caches. For a full wipe instead, see `cleanup.caches-full`.
    """


@task(pre=[apt.clean_cache_full, python.clean_cache_full, node.clean_cache_full, tools.clean_cache_full])
def caches_full(c):
    """Fully wipe apt/uv/npm/cargo caches (each self-skips if that tool isn't installed) —
    reclaims more disk space than `cleanup.caches`, at the cost of the next install of each being
    slower, since there's no local cache to hit at all. Opt-in, not part of `inv setup`. A
    container build calls this explicitly at the end of its Dockerfile, since there's no "next
    install" on that machine to speed up — see docs/dev-container.md.
    """


@task(pre=[caches, docker.clean])
def all(c):  # noqa: A001
    """Everything reclaimable, conservatively: caches() plus Docker's conservative prune
    (stopped containers, dangling images — see `docker.clean`). For a full wipe of everything
    instead, see `cleanup.all-full`.
    """


@task(pre=[caches_full, docker.clean_full])
def all_full(c):
    """Everything reclaimable, fully wiped: caches_full() plus Docker's full prune (also removes
    unused-but-tagged images — see `docker.clean-full`). Neither this nor any task it depends on
    touches Docker volumes — see `docker.clean`'s docstring for why.
    """
