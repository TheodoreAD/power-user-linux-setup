# pyright: reportImportCycles=false
# This package imports every submodule to build the invoke Collection below, and those submodules
# do `from . import <sibling>` — a cycle only in the checker's graph (Python resolves it at
# runtime), and the exact pattern the shared pyrightconfig.json documents. Suppressed here, in the
# one file that structurally trips it, so `failOnWarnings` can stay on and the rule stays live for
# every other file. See repo-tasks' contributing/type-checking.md.

from invoke import Collection

from . import (
    ai,
    allowlist,
    apt,
    catalog,
    certs,
    chrome,
    clean,
    deploy,
    devcontainer,
    docker,
    fonts,
    git,
    gnome,
    home,
    ide,
    identity,
    net,
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


def _import_repo_tasks_modules(simulate_missing: bool = False):
    """repo_tasks (github.com/TheodoreAD/repo-tasks) is a dev-only dependency, resolved through
    this project's own venv. bootstrap.sh's zero-install path (a bare `uv tool install invoke`,
    no `uv sync` — see docker/Dockerfile, which never installs this project's own dependencies
    either) has nothing for it to resolve against, so this returns all-Nones rather than taking
    down every other `inv` command with an import error. The real `from repo_tasks import ...`
    statement stays a literal import (so pyright keeps real module types instead of `Any`, unlike
    an `importlib.import_module` indirection); `simulate_missing` exercises the degraded branch
    directly and testably instead, with no need to fake an import failure via sys.modules
    patching."""
    if simulate_missing:
        return None, None, None, None, None, None, None, None
    try:
        from repo_tasks import agents, ci, configs, deps, dev_env, docs, quality, testing  # noqa: PLC0415
    except ImportError:
        return None, None, None, None, None, None, None, None
    return agents, ci, configs, deps, dev_env, docs, quality, testing


agents, ci, configs, deps, dev_env, docs, quality, testing = _import_repo_tasks_modules()

namespace = Collection(
    setup.setup,
    Collection.from_module(ai),
    Collection.from_module(allowlist),
    Collection.from_module(apt),
    Collection.from_module(catalog),
    Collection.from_module(certs),
    Collection.from_module(chrome),
    Collection.from_module(clean),
    Collection.from_module(deploy),
    Collection.from_module(devcontainer),
    Collection.from_module(docker),
    Collection.from_module(fonts),
    Collection.from_module(git),
    Collection.from_module(gnome),
    Collection.from_module(home),
    Collection.from_module(identity),
    Collection.from_module(ide),
    Collection.from_module(net),
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
if testing is not None:
    # repo_tasks keeps the module named `testing` (a `test.py` inside an installed package would
    # sit next to CPython's own stdlib `test`) and publishes it as `test` on the CLI — same name
    # every consumer in the family uses (`inv test.unit`, `inv test.integration`, ...).
    namespace.add_collection(Collection.from_module(testing), name="test")
if dev_env is not None:
    namespace.add_collection(Collection.from_module(dev_env), name="dev-env")
if agents is not None:
    # `inv agents.wire-claude-hook` used to reach this repo as `inv dev-env.claude-hook`, which
    # existed only because repo_tasks' dev_env.py imports it for a pre= chain and
    # Collection.from_module republished it. That leak is fixed upstream, so the namespace it
    # really lives in has to be wired explicitly or the command disappears from this repo — and
    # docs/claude-code.md documents it.
    namespace.add_collection(Collection.from_module(agents))
if docs is not None:
    namespace.add_collection(Collection.from_module(docs))
if ci is not None:
    # `inv ci.status` before a push, `inv ci.check-actions` when a workflow is edited. Both are
    # network+`gh` tasks and neither is in `quality.check`, which stays offline.
    #
    # Wired 2026-09-04, after doing a whole CI sweep with raw `gh api` calls because the namespace
    # was not published here. `ci.status` is the one that matters: it prints the latest run's
    # warning annotations, and an annotation on a *green* run is the only signal for a deprecation
    # — `actions/checkout@v4` carried one for eleven months while every run passed. `--branch
    # master`, since its default is `main` and this repo is not.
    namespace.add_collection(Collection.from_module(ci))
if deps is not None:
    # `deps.check` (lock drift) is a member of `quality.check`'s pre-chain, so the gate ran it
    # while `inv deps.check` did not exist here — a failing check nobody could re-run on its own
    # to see what it objected to. The rest of the namespace (`lock`, `audit`, `list`, `tree`,
    # `export`) comes with it, the same way every other repo_tasks collection is published whole.
    namespace.add_collection(Collection.from_module(deps))
if configs is not None:
    # Not repo_tasks' bare top-level `configure` — this repo already has its own top-level
    # entrypoints (`inv setup` for full machine bootstrap, `inv dev-env.setup` for the dev loop);
    # only the nested `inv configs.pull`/`inv configs.diff` are relevant here.
    namespace.add_collection(Collection.from_module(configs))
