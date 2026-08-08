from invoke import task

from . import apt, docker, fonts, node, python, system, tools, zsh


@task
def setup(c):
    """Run full machine setup (all tasks in order)."""
    system.locale(c)
    system.curlrc(c)
    system.dns(c)
    apt.configure(c)
    apt.repos(c)
    apt.base(c)
    docker.configure(c)
    apt.deb(c)
    tools.install(c)
    system.apparmor_profiles(c)
    zsh.omz_configure(c)
    python.tools(c)
    node.install(c)
    zsh.configure(c)
    zsh.p10k_configure(c)
    fonts.install(c)
    fonts.configure(c)
