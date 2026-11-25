### The shell on the Windows machine [Claude Code]

The OS is Windows 11 and the shell for one-off commands is **PowerShell 7** (`pwsh`, installed with
scoop) — not Bash, and not Windows PowerShell 5.1. The Bash tool is disabled (`permissions.deny` in
`~/.claude/settings.json`), so every shell command goes through the PowerShell tool.

- PowerShell 7 syntax is fine: `&&`, `||`, `??`, `?.` and the ternary `?:` all work.
- Claude Code's own shell does not load the user's PowerShell profile.
- Prefer full cmdlet names (`Get-ChildItem`, `Get-Content`, `Where-Object`, `Remove-Item`, ...) over
  aliases, in commands you run and in commands you suggest.
- Unix tools come from Git's `usr/bin` (`grep`, `sed`, `awk`, ...). PowerShell's built-in aliases
  are kept everywhere (`ls`, `cat`, `rm`, `where`, `sort` are cmdlets), so call the GNU version with
  `.exe` (`ls.exe`, `cat.exe`).
- `rg`, `fd` and `curl` are available. When shell search is needed and no built-in tool covers it,
  `rg` for content and `fd` for files.

Always prefer Claude Code's built-in tools over shell commands. They are more transparent and
reviewable:

| Task                       | Use                                  | Never use                        |
| -------------------------- | ------------------------------------ | -------------------------------- |
| **Read a file**            | Read tool                            | `cat`, `head`, `tail`            |
| **Create or write a file** | Write tool (creates directories too) | `echo`, heredoc, `mkdir` + touch |
| **Edit a file**            | Edit tool                            | `sed`, `awk`                     |
| **Find files**             | Glob tool                            | `find`, `fd`                     |
| **Search content**         | Grep tool                            | `grep`, `rg`                     |
| **Run a one-off command**  | PowerShell 7                         | Bash                             |

### Writing a script on the Windows machine

- **A simple one-off command** is a PowerShell 7 one-liner.
- **Anything with logic, data processing or reuse value** is a Python script, saved to the project's
  `scripts/`.
- **Never write a PowerShell script** unless the user explicitly asks for one. PowerShell is only
  for quick one-liners.
- **Always ask the user whether a script should be saved for reuse.**

### Running a Python project's tools on the Windows machine [needs venv-shims]

**Run `python`, `pytest`, `inv` and `invoke` bare.** Each is a shim first on the user `PATH` that
runs the copy in the `.venv` of the nearest directory at or above the current one, so the project's
own interpreter and tools answer, and the command text, which your permission rules match, stays as
typed. Any other tool goes through `uv run <tool>` or the project's inv task. Never activate a venv
by hand, and expect `pip` to be absent: uv manages the environment. A tool that says "not found in a
.venv" means the project has no `.venv` yet; run `uv sync` there.
