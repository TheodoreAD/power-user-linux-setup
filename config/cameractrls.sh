#!/bin/sh
# Starts the cameractrls GTK4 GUI from [packages.cameractrls]'s clone. The system interpreter is
# named explicitly rather than through the script's own `env python3` shebang: launched from a
# terminal inside a direnv project, that resolves to the project's venv, which has no PyGObject.
exec /usr/bin/python3 "${HOME}/.local/share/cameractrls/cameractrlsgtk4.py" "$@"
