from invoke import Collection

try:
    # repo_tasks (github.com/TheodoreAD/repo-tasks) is a dev-only dependency, resolved through
    # this project's own venv. bootstrap.sh's zero-install path (a bare `uv tool install invoke`,
    # no `uv sync` — see docker/Dockerfile, which never installs this project's own dependencies
    # either) has nothing for it to resolve against, so these tasks just aren't available there
    # rather than taking down every other `inv` command with an import error.
    from repo_tasks import configs, dev_env, docs, quality
except ImportError:
    configs = dev_env = docs = quality = None

from . import (
    ai,
    allowlist,
    apt,
    certs,
    cleanup,
    devcontainer,
    docker,
    fonts,
    git,
    gnome,
    ide,
    identity,
    node,
    proxy,
    python,
    screenshot,
    setup,
    ssh,
    system,
    tools,
    verify,
    wsl,
    zsh,
)

namespace = Collection(
    setup.setup,
    Collection.from_module(ai),
    Collection.from_module(allowlist),
    Collection.from_module(apt),
    Collection.from_module(certs),
    Collection.from_module(cleanup),
    Collection.from_module(devcontainer),
    Collection.from_module(docker),
    Collection.from_module(fonts),
    Collection.from_module(git),
    Collection.from_module(gnome),
    Collection.from_module(identity),
    Collection.from_module(ide),
    Collection.from_module(proxy),
    Collection.from_module(python),
    Collection.from_module(screenshot),
    Collection.from_module(ssh),
    Collection.from_module(system),
    Collection.from_module(tools),
    Collection.from_module(node),
    Collection.from_module(verify),
    Collection.from_module(wsl),
    Collection.from_module(zsh),
)
if quality is not None:
    namespace.add_collection(Collection.from_module(quality))
if dev_env is not None:
    namespace.add_collection(Collection.from_module(dev_env), name="dev-env")
if docs is not None:
    namespace.add_collection(Collection.from_module(docs))
if configs is not None:
    # Not repo_tasks' bare top-level `configure` — this repo already has its own top-level
    # entrypoints (`inv setup` for full machine bootstrap, `inv dev-env.setup` for the dev loop);
    # only the nested `inv configs.pull`/`inv configs.diff` are relevant here.
    namespace.add_collection(Collection.from_module(configs))
