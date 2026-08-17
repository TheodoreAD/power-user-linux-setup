# Scala

Scala is not in `setup.toml` — it is optional and the Coursier launcher runs a self-configuring
install that does not fit the standard package methods.

## Install via Coursier

[Coursier](https://get-coursier.io/) is the standard Scala artifact and tool manager. It bootstraps
itself and then installs `scala`, `scalac`, `sbt`, and other toolchain components.

```shell
SCALA_CLI_SETUP="$(mktemp)"
curl -fsSL "https://github.com/coursier/launchers/raw/master/cs-x86_64-pc-linux.gz" \
  | gzip -d > "${SCALA_CLI_SETUP}"
chmod +x "${SCALA_CLI_SETUP}"
"${SCALA_CLI_SETUP}" setup
rm "${SCALA_CLI_SETUP}"
```

This installs `cs` to `~/.local/share/coursier/bin` and adds it to PATH (via `~/.profile` update).
Open a new shell after install.

## Metals (VS Code extension)

For VS Code, install the **Metals** extension. It needs the Java home path from Coursier:

```shell
cs java -XshowSettings:properties -version 2>&1 | grep "java.home" | sed 's/.*= *//'
```

Paste this path into VS Code settings under `metals.javaHome`.

## Updating

```shell
cs update
```
