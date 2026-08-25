from invoke import Context, task

from . import ai, apt, docker, fonts, next_steps, node, phases, python, system, tools, util, verify, wsl, zsh

# Module-level so tasks/devcontainer.py's check() can dry-run the exact same phase composition
# `inv setup` uses (via phases.probe) instead of a second, driftable copy.
PACKAGES_PHASE = [
    apt.configure,
    apt.install_repos,
    apt.install_base,
    docker.configure,
    apt.install_debs,
    tools.install,
    ai.install_skills,
    system.install_apparmor_profiles,
    python.install_tools,
    node.install,
    verify.all,
]
PACKAGES_NOTE = (
    "apt config/repos/packages, Docker, .deb packages, script/binary tools, "
    "AI agent skills scaffolding, AppArmor profiles, Python and Node.js tools, "
    "then a hard functional-verification pass over everything just installed"
)
SHELL_PHASE = [zsh.configure_omz, zsh.configure, zsh.configure_p10k, zsh.set_default_shell]
SHELL_NOTE = "Oh My Zsh theme/plugins, zsh config blocks, Powerlevel10k baseline, default shell"


@task
def setup(c: Context):
    """Run full machine setup, in phases (system, packages, shell, desktop) — delegates to
    wsl.install under WSL. Each phase is skippable (default: skip) if it already looks done.
    Skips the system/desktop phases automatically in a container or other environment with no
    systemd (and not WSL) — see docs/dev-container.md.
    """
    if util.is_wsl():
        print(
            "[setup] WSL detected — delegating to `inv wsl.install` (different tag exclusions, "
            "DNS handling, and skips docker.configure/fonts.* by default; see docs/wsl.md). Run "
            "`inv wsl.install` directly if you want its --wslg/--docker/--dns options."
        )
        wsl.install(c)
        return

    if not util.has_systemd():
        print(
            "[setup] no systemd detected (not WSL) — skipping the `system` phase (locale/DNS "
            "need systemctl/localectl) and the `desktop` phase (fonts are meaningless in a "
            "headless container). See docs/dev-container.md for the container-specific setup "
            "path, or install/enable systemd if this environment should have it."
        )
        phases.run_phase(c, "packages", PACKAGES_PHASE, note=PACKAGES_NOTE)
        phases.run_phase(c, "shell", SHELL_PHASE, note=SHELL_NOTE)
        next_steps.print_next_steps()
        return

    phases.run_phase(
        c,
        "system",
        [system.set_locale, system.write_curlrc, system.configure_dns],
        note="locale, curl config, DNS",
    )

    phases.run_phase(c, "packages", PACKAGES_PHASE, note=PACKAGES_NOTE)

    phases.run_phase(c, "shell", SHELL_PHASE, note=SHELL_NOTE)

    phases.run_phase(c, "desktop", [fonts.install, fonts.configure], note="Nerd Fonts, monospace font config")

    next_steps.print_next_steps()
