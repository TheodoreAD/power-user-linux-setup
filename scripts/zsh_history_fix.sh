#!/usr/bin/env zsh
# George Ornbo (shapeshed) http://shapeshed.com
# License - http://unlicense.org
#
# Fixes a corrupt .zsh_history file

mv "${HOME}/.zsh_history" "${HOME}/.zsh_history_bad"
strings "${HOME}/.zsh_history_bad" > "${HOME}/.zsh_history"
fc -R "${HOME}/.zsh_history"
rm "${HOME}/.zsh_history_bad"
