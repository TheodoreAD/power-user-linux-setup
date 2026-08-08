from invoke import Collection

from . import apt, docker, fonts, git, gnome, ide, node, python, screenshot, setup, ssh, system, tools, zsh

namespace = Collection(
    setup.setup,
    Collection.from_module(apt),
    Collection.from_module(docker),
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
    Collection.from_module(zsh),
)
