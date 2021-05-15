# Zsh and Oh My Zsh

<http://www.bash2zsh.com/zsh_refcard/refcard.pdf>

<http://grml.org/zsh/zsh-lovers.html>

Install Zsh and change default shell:

```shell
sudo apt install -y zsh
chsh -s $(which zsh)
```

Log out and login back again to use your new default shell.

Install Oh My Zsh and set up themes and plugins:

```shell
sh -c "$(curl -sS -Lf https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
git clone --depth=1 \
  "https://github.com/romkatv/powerlevel10k.git" \
  "${ZSH}/themes/powerlevel10k"
sed -i \
  's:ZSH_THEME="robbyrussell":ZSH_THEME="powerlevel10k/powerlevel10k":' \
  "${HOME}/.zshrc"
# disable P10k pyenv prompt token, it becomes duplicate of virtualenv (bug?)
sed -i \
  "s/    pyenv/    # pyenv/" \
  "${HOME}/.p10k.zsh"
# set plugins, the more the slower the prompt
ZSH_PLUGINS=$(
  cat <<EOF
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
    poetry \n\
    rsync \n\
    thefuck \n\
    urltools \n\
    web-search \n\
)
EOF
)
sed -i \
  "s/plugins=(git)/${ZSH_PLUGINS}/" \
  "${HOME}/.zshrc"
```

!!! TODO
    Research other useful plugins

    Maybe:
    
    - pip
    - pyenv
    - pylint
    - python
    - redis-Compilation
    - sudo
    - tmux
    - tmuxinator
    - vscode
    
    Desired:
    
    - catimg
  
        <https://github.com/posva/catimg>

        requires convert from imagemagick, package is very large use C version from original repo

        <https://github.com/ohmyzsh/ohmyzsh/tree/master/plugins/catimg>
         
    - git-extras

        <https://github.com/tj/git-extras>

        <https://github.com/ohmyzsh/ohmyzsh/tree/master/plugins/git-extras>

        compatibility issue
    
    - <https://github.com/zsh-users/zsh-syntax-highlighting/blob/master/INSTALL.md>


Install [direnv](https://direnv.net/):

```shell
tee -a "${HOME}/.zshrc" >/dev/null <<EOF

# Add hooks for direnv to allow auto processing for .envrc files
export DIRENV_LOG_FORMAT=""
eval "\$(direnv hook zsh)"
EOF
```


Key bindings, aliases, completions, path:

```shell
tee -a "${HOME}/.zshrc" >/dev/null <<EOF

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
tee -a "${HOME}/.zshrc" >/dev/null <<EOF

# used to pipe into the clipboard, e.g. ps -e | xcc
alias xcc="xclip -rmlastnl -selection clipboard -filter | xclip -rmlastnl -selection primary"
# used to copy the current line, e.g. xc "abcd efgh"
function xc() { echo -n "\$*" | xcc ; }
# used to paste into stdout
alias xv="xclip -o"
EOF

# Aliases not covered by oh my zsh plugins
tee -a "${HOME}/.zshrc" >/dev/null <<EOF

# Common command aliases
# redirect following and silent except for errors
alias curl='curl -sS -L'
# sort keys in JSON output
alias jq='jq -S'
EOF

# add user binaries directory to PATH
# https://unix.stackexchange.com/questions/36871/where-should-a-local-executable-be-placed
mkdir -p "${HOME}/bin" "${HOME}/.local/bin"
sed -i \
  's%# export PATH=$HOME/bin:/usr/local/bin:$PATH%export PATH="${HOME}/bin:${HOME}/.local/bin:/usr/local/bin:${PATH}"%' \
  "${HOME}/.zshrc"

# init completions
tee -a "${HOME}/.zshrc" >/dev/null <<EOF

autoload -U compinit && compinit
EOF

source "${HOME}/.zshrc"
```

After the first run, configure the Oh My Zsh theme:

```shell
p10k configure
```


!!! TODO
    Investigate https://github.com/zsh-users/zsh-completions

    ```shell
    git clone https://github.com/zsh-users/zsh-completions ${ZSH_CUSTOM:=~/.oh-my-zsh/custom}/plugins/zsh-completions
    ```

    plugins=(... zsh-completions)

    must be placed before `compinit`

!!! TODO
    install colorls

    <https://github.com/athityakumar/colorls>

    <https://linuxize.com/post/how-to-install-ruby-on-ubuntu-18-04/>
