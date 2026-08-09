from invoke import task

from . import apt, docker, fonts, node, python, system, tools, util, wsl, zsh


@task
def setup(c):
    """Run full machine setup (all tasks in order) — delegates to wsl.install under WSL."""
    if util.is_wsl():
        print(
            "[setup] WSL detected — delegating to `inv wsl.install` (different tag exclusions, "
            "DNS handling, and skips docker.configure/fonts.* by default; see docs/wsl.md). Run "
            "`inv wsl.install` directly if you want its --wslg/--docker/--dns options."
        )
        wsl.install(c)
        return

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
    zsh.set_default_shell(c)
    fonts.install(c)
    fonts.configure(c)
    util.print_next_steps()
