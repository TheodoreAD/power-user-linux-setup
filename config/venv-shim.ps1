# Venv shim for native Windows: run this command from the .venv of the nearest directory at or
# above the current one that has one, else from the next copy on PATH. Deployed by
# [packages.venv-shims] in power-user-linux-setup's setup.toml, once per command name (python.ps1,
# pytest.ps1, ...); the command is this file's own name, so every copy is the same file. Edit it
# there, never here.
#
# Why shims: Claude Code's PowerShell tool starts every call with -NoProfile, drops any
# CLAUDE_ENV_FILE value containing a path separator, and checks permission rules against a
# PreToolUse hook's rewritten command, which a PATH assignment always makes prompt. A shim on PATH
# needs none of that, and the command text, so every permission rule, stays exactly as typed.
# Measured 2026-11-25 in headless sessions; docs/claude-code.md has the details.
#
# Why venvs inherited from the launch environment are skipped in the fallback: a venv active in the
# shell Claude Code was started from is never the current directory's (same decision as the Linux
# hook, config/claude-direnv-hook.sh).

$name = [IO.Path]::GetFileNameWithoutExtension($MyInvocation.MyCommand.Name)
$here = $PSScriptRoot
$dir = (Get-Location).ProviderPath
while ($dir) {
    $exe = Join-Path $dir ".venv\Scripts\$name.exe"
    if (Test-Path -LiteralPath $exe) {
        $env:VIRTUAL_ENV = Join-Path $dir ".venv"
        $env:PATH = (Join-Path $dir ".venv\Scripts") + ";" + $env:PATH
        & $exe @args
        exit $LASTEXITCODE
    }
    $dir = Split-Path -Parent $dir
}
$next = Get-Command -Name $name -CommandType Application -All -ErrorAction SilentlyContinue |
    Where-Object { (Split-Path -Parent $_.Source) -ne $here -and $_.Source -notlike '*\.venv\Scripts\*' } |
    Select-Object -First 1
if (-not $next) {
    Write-Error "${name}: not found in a .venv at or above $(Get-Location), or on PATH"
    exit 127
}
& $next.Source @args
exit $LASTEXITCODE
