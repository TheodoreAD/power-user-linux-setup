from invoke import Collection

from . import ai, apt, docker, docs, fonts, git, gnome, ide, node, python, screenshot, setup, ssh, system, tools, wsl, zsh

namespace = Collection(
    setup.setup,
    Collection.from_module(ai),
    Collection.from_module(apt),
    Collection.from_module(docker),
    Collection.from_module(docs),
    Collection.from_module(fonts),
    Collection.from_module(git),
    Collection.from_module(gnome),
    Collection.from_module(ide),
    Collection.from_module(python),
    Collection.from_module(screenshot),
    Collection.from_module(ssh),
    Collection.from_module(system),
    Collection.from_module(tools),
    Collection.from_module(node),
    Collection.from_module(wsl),
    Collection.from_module(zsh),
)
