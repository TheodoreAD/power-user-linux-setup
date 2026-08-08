# Go

<https://go.dev/doc/install>
<https://github.com/golang-standards/project-layout>

Installed via `inv tools.install` (archive method — downloads the official tarball from go.dev and extracts to `~/.local/share/go`). Shell environment is written to `~/.zshrc` by `inv zsh.configure`.

## Environment

```shell
GOROOT=~/.local/share/go   # Go installation (binaries, stdlib)
GOPATH=~/go                # workspace (go install puts binaries in ~/go/bin)
```

Both are set automatically by the `zshrc` snippet in `setup.toml`.

## Version management

Go 1.21+ has built-in per-project version management. A `go.mod` declaring:

```
toolchain go1.26.4
```

will cause the `go` command to automatically download and use that exact version when you enter the project. `GOTOOLCHAIN=auto` (the default since 1.21) enables this behaviour — no extra tool needed.

Install one bootstrap version via `inv tools.install` and let projects pull their own toolchains as needed.

## To update the bootstrap install

```shell
rm -rf ~/.local/share/go
inv tools.install
```

## Verify

```shell
go version
```
