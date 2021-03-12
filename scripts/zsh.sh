# http://www.bash2zsh.com/zsh_refcard/refcard.pdf
# http://grml.org/zsh/zsh-lovers.html
sudo apt install -y zsh
# change the current default shell
chsh -s $(which zsh)
# ACTION: Log out and login back again to use your new default shell.
sh -c "$(curl -sS -Lf https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git $ZSH/themes/powerlevel10k
# Set ZSH_THEME=powerlevel10k/powerlevel10k in your ~/.zshrc.
sed -i 's:ZSH_THEME="robbyrussell":ZSH_THEME="powerlevel10k/powerlevel10k":' "${HOME}/.zshrc"
# disable P10k pyenv prompt token, it becomes duplicate of virtualenv (bug?)
sed -i "s/    pyenv/    # pyenv/" "${HOME}/.p10k.zsh"
# set plugins, the more the slower the prompt
# Maybe:
#    pip
#    pyenv
#    pylint
#    python
#    redis-Compilation
#    sudo
#    tmux
#    tmuxinator
#    vscode
# Desired:
# https://github.com/posva/catimg
# requires convert from imagemagick, package is very large
# use C version from original repo
# https://github.com/ohmyzsh/ohmyzsh/tree/master/plugins/catimg
#    catimg
# https://github.com/tj/git-extras
# https://github.com/ohmyzsh/ohmyzsh/tree/master/plugins/git-extras
# compatibility issue
#    git-extras
# https://github.com/zsh-users/zsh-syntax-highlighting/blob/master/INSTALL.md
ZSH_PLUGINS=$(cat <<EOF
plugins=( \n\
    command-not-found \n\
    dirhistory \n\
    docker \n\
    docker-compose \n\
    encode64 \n\
    git \n\
    helm \n\
    history \n\
    jsontools \n\
    kubectl \n\
    urltools \n\
    web-search \n\
)
EOF
)
sed -i "s/plugins=(git)/${ZSH_PLUGINS}/" "${HOME}/.zshrc"
tee -a "${HOME}/.zshrc" > /dev/null <<EOF

# key bindings for navigating the command line
# home
bindkey "^[[H" beginning-of-line
# end
bindkey "^[[F" end-of-line
# ctrl + right arrow
bindkey "^[[1;5C" forward-word
# ctrl + left arrow
bindkey "^[[1;5D" backward-word
# ctrl + backspace
bindkey "^H" backward-delete-word
# ctrl + delete
bindkey "^[[3;5~" delete-word
# esc '
bindkey "^[;" quote-line
# ctrl + alt + ' (at the end of the region)
bindkey "^[\x27" quote-region
# ctrl + o
bindkey "^O" up-case-word
# ctrl + l
bindkey "^L" down-case-word
EOF

# Terminal copy-paste with xclip
tee -a "${HOME}/.zshrc" > /dev/null <<EOF

# used to pipe into the clipboard, e.g. ps -e | xcc
alias xcc="xclip -rmlastnl -selection clipboard -filter | xclip -rmlastnl -selection primary"
# used to copy the current line, e.g. xc "abcd efgh"
function xc() { echo -n "\$*" | xcc ; }
# used to paste into stdout
alias xv="xclip -o"
EOF

# Aliases not covered by oh my zsh plugins
tee -a "${HOME}/.zshrc" > /dev/null <<EOF

# Common command aliases
alias curl='curl -sSL'
EOF

# add user binaries directory to PATH
# https://unix.stackexchange.com/questions/36871/where-should-a-local-executable-be-placed
mkdir -p "${HOME}/bin" "${HOME}/.local/bin"
sed -i 's%# export PATH=$HOME/bin:/usr/local/bin:$PATH%export PATH="${HOME}/bin:${HOME}/.local/bin:/usr/local/bin:${PATH}"%' "${HOME}/.zshrc"

# TODO: install colorls
# https://github.com/athityakumar/colorls
# https://linuxize.com/post/how-to-install-ruby-on-ubuntu-18-04/


tee -a "${HOME}/.zshrc" > /dev/null <<EOF

# Add hooks for direnv to allow auto processing for .envrc files
export DIRENV_LOG_FORMAT=""
eval "$(direnv hook zsh)"
EOF

source "${HOME}/.zshrc"
# use `p10k configure` to configure after the first run


# TODO: poetry
