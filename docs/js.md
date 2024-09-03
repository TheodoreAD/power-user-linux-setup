# Javascript

## NVM

<https://github.com/nvm-sh/nvm?tab=readme-ov-file#installing-and-updating>

```shell
NVM_TAG=$(
  curl -sS -L https://api.github.com/repos/nvm-sh/nvm/releases/latest \
    | grep 'tag_name' \
    | cut -d\" -f4
)
curl -sS -L -o- https://raw.githubusercontent.com/nvm-sh/nvm/${NVM_TAG}/install.sh \
  | bash
# to enable right away
source "${HOME}/.zshrc"
```

## Node

!!! TODO
    Install.

## NPM and/or Yarn 
    Install.
