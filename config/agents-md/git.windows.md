### Writing the commit command in PowerShell

Pass the whole message as **one single-quoted here-string** to one `-m`, with the pathspec last:

```powershell
git commit -m @'
Subject line

Body: what changed, by name; then what it is for, what it beat, what it cost.
'@ -- path/one path/two
```

The closing `'@` must start its own line at column 0; an indented one is a parse error. Inside a
single-quoted here-string nothing is expanded, so backticks, `$` and quotes in the message are safe
as written. A double-quoted `@"..."@` expands `$`, and the backtick is PowerShell's escape
character.

`git commit -F -` does not take the here-string: `-F -` reads stdin, and the here-string becomes a
pathspec, which fails with "pathspec ... did not match any file(s)".
