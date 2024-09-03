# Shell: Zsh + Oh My Zsh + PowerLevel10k

!!! TODO
  Research:
  <http://www.bash2zsh.com/zsh_refcard/refcard.pdf>
  <http://grml.org/zsh/zsh-lovers.html>
  <http://zsh.sourceforge.net/Doc/Release/Shell-Builtin-Commands.html>

Install Zsh and log out, when you login back again zsh will be your new default shell:

```shell
sudo apt install -y zsh
# change default shell
chsh -s $(which zsh)
# log out
gnome-session-quit --no-prompt
```

Open a terminal and choose the following when being prompted for the zsh config:

```
(1)  Continue to the main menu.
(1)  Configure settings for history, i.e. command lines remembered
     and saved by the shell.  (Recommended.)
  # (1) Number of lines of history kept within the shell.
  100000
  # (3) Number of lines of history to save to $HISTFILE.
  # (0)  Remember edits and return to main menu (does not save file yet)
(2)  Configure the new completion system.  (Recommended.)
  (1)  Turn on completion with the default options.
(4)  Pick some of the more common shell options.  These are simple "on"
     or "off" switches controlling the shell's features.
  # (1) Change directory given just path.
    (s) to set it (turn it on)
  # (4) Beep on errors.
    (s) to set it (turn it on)
  # (0)  Remember edits and return to main menu (does not save file yet)
(0)  Exit, saving the new settings.  They will take effect immediately.
```

<https://github.com/ohmyzsh/ohmyzsh?tab=readme-ov-file#basic-installation>
<https://github.com/romkatv/powerlevel10k?tab=readme-ov-file#oh-my-zsh>

Install Oh My Zsh, this will close the current terminal:

```shell
# TODO: try using: sh -s --unattended
curl -sS -L -f "https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh" \
  | sh
exit
```

!!! WARNING
    At this point you should have the fonts installed as per the [guide](fonts.md).

Open a new terminal and set up the theme, this will close the current terminal:


```shell
git clone --depth=1 \
  "https://github.com/romkatv/powerlevel10k.git" \
  ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k
sed -i \
  's:ZSH_THEME="robbyrussell":ZSH_THEME="powerlevel10k/powerlevel10k":' \
  "${HOME}/.zshrc"
exit
```

Open a terminal and choose the following when being prompted for the powerlevel10k config:

```
Does this look like a diamond (rotated square)?
  (y)  Yes.
Does this look like a lock?
  (y)  Yes.
Does this look like an upwards arrow?
  (n)  No.
Does this look like an upwards arrow?
  (y)  Yes.
What digit is the downwards arrow pointing at?
  (1)  It is pointing at '1'.
Do all these icons fit between the crosses?
  (n)  No. Some icons overlap neighbouring crosses.
Prompt Style
  (1)  Lean.
Character Set
  (1)  Unicode.
Prompt Colors
  (1)  256 colors.
Show current time?
  (2)  24-hour format.
Prompt Height
  (2)  Two lines.
Prompt Connection
  (1)  Disconnected.
Prompt Frame
  (1)  No frame.
Prompt Spacing
  (1)  Compact.
Icons
  (2)  Many icons.
Prompt Flow
  (1)  Concise.
Enable Transient Prompt?
  (y)  Yes.
Instant Prompt Mode
  (1)  Verbose (recommended).
Apply changes to ~/.zshrc?
  (y)  Yes (recommended).
```

If you decide to skip this, you can configure the Oh My Zsh theme using:

```shell
p10k configure
```

!!! TODO
    Fix basic zsh settings not being saved, e.g. HISTSIZE

Set up the plugins:

```shell
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
    #thefuck \n\
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
# add user binaries directory to PATH
# https://unix.stackexchange.com/questions/36871/where-should-a-local-executable-be-placed
mkdir -p "${HOME}/bin" "${HOME}/.local/bin"
sed -i \
  's%# \(export PATH=$HOME.*\)%\1%' \
  "${HOME}/.zshrc"

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
alias pyjsonlint='python -m json.tool'
alias pyjsonlint-no-stdout='pyjsonlint >/dev/null'
EOF

# init completions
tee -a "${HOME}/.zshrc" >/dev/null <<EOF

autoload -Uz compinit && compinit
EOF

source "${HOME}/.zshrc"
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

!!! TODO
    ```shell
    # The following lines were added by compinstall

    zstyle ':completion:*' completer _complete _ignored
    zstyle :compinstall filename '/home/tdumitrescu/.zshrc'
    
    autoload -Uz compinit
    compinit
    # End of lines added by compinstall
    # Lines configured by zsh-newuser-install
    HISTFILE=~/.histfile
    HISTSIZE=100000
    SAVEHIST=100000
    setopt autocd beep nomatch notify
    bindkey -e
    # End of lines configured by zsh-newuser-install
    ```
