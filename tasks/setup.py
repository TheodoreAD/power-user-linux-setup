from invoke import task

from . import ai, apt, docker, fonts, next_steps, node, phases, python, system, tools, util, wsl, zsh


@task
def setup(c):
    """Run full machine setup, in phases (system, packages, shell, desktop) — delegates to
    wsl.install under WSL. Each phase is skippable (default: skip) if it already looks done.
    """
    if util.is_wsl():
        print(
            "[setup] WSL detected — delegating to `inv wsl.install` (different tag exclusions, "
            "DNS handling, and skips docker.configure/fonts.* by default; see docs/wsl.md). Run "
            "`inv wsl.install` directly if you want its --wslg/--docker/--dns options."
        )
        wsl.install(c)
        return

    phases.run(c, "system", [system.locale, system.curlrc, system.dns],
               note="locale, curl config, DNS")

    phases.run(
        c, "packages",
        [apt.configure, apt.repos, apt.base, docker.configure, apt.deb,
         tools.install, ai.skills, system.apparmor_profiles, python.tools, node.install],
        note="apt config/repos/packages, Docker, .deb packages, script/binary tools, "
             "AI agent skills scaffolding, AppArmor profiles, Python and Node.js tools",
    )

    phases.run(
        c, "shell",
        [zsh.omz_configure, zsh.configure, zsh.p10k_configure, zsh.set_default_shell],
        note="Oh My Zsh theme/plugins, zsh config blocks, Powerlevel10k baseline, default shell",
    )

    phases.run(c, "desktop", [fonts.install, fonts.configure],
               note="Nerd Fonts, monospace font config")

    next_steps.print_next_steps()
