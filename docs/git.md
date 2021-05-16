# Git

Multi-email config

!!! TODO
    Get data from files instead of hardcoding here.

```shell
# Disable global user name and email in favor of project-specific ones
git config --global --unset user.name
git config --global --unset user.email
# set up project directories and configure per-directory identities
PROJECTS_ROOT="${HOME}/projects"
mkdir -p "${PROJECTS_ROOT}"
# no spaces allowed after the comma delimiters
# projects_directory,git_commit_name,git_commit_email
PROJECTS=(
  github.com-personal,"Teodor Dumitrescu","teodor.dumitrescu@gmail.com"
)
for project in "${PROJECTS[@]}"; do
  project_dir=$(echo ${project} | cut -d ',' -f 1)
  user_name=$(echo ${project} | cut -d ',' -f 2)
  user_email=$(echo ${project} | cut -d ',' -f 3)
  project_dir_full="${PROJECTS_ROOT}/${project_dir}"
  mkdir -p "${project_dir_full}"
  git config --global \
    includeIf.gitdir:"${project_dir_full}/".path \
    \""${project_dir_full}/.gitconfig"\"
  git config --file "${project_dir_full}/.gitconfig" user.name \""${user_name}"\"
  git config --file "${project_dir_full}/.gitconfig" user.email \""${user_email}"\"
done
```

## Configuration

```shell
# Make git aware of executable permissions
git config --global core.filemode true
# Push your current branch to a branch with the same name
git config --global push.default current
# Set VS Code as default editor
git config --global core.editor code
# configure the pager to just output content is below one page
git config --global core.pager "less --quit-if-one-screen --quit-at-eof --raw-control-chars --no-init"
# Display the command line interface in color
git config --global color.ui auto
# Show branch names with git log
git config --global log.decorate auto
# Enable parallel index preload for operations like git diff
git config --global core.preloadindex true
```

## Pycharm

Enable PyCharm as the default diff and merge tools, use with git difftool and git mergetool:

```shell
PYCHARM_PATH="$(which pycharm-professional)"
git config --global diff.tool pycharm-professional
git config --global difftool.prompt false
git config --global difftool.pycharm-professional.cmd \
  \""${PYCHARM_PATH}"\"' diff "$LOCAL" "$REMOTE"'
git config --global merge.tool pycharm-professional
git config --global mergetool.prompt false
git config --global mergetool.pycharm-professional.cmd \
  \""${PYCHARM_PATH}"\"' merge "$LOCAL" "$REMOTE" "$BASE" "$MERGED"'
git config --global mergetool.pycharm-professional.keepBackup false
```

!!! TODO
    See if this is desirable.

```shell
# When pulling code, always rebase your local changes
git config --global pull.rebase true
```

!!! TODO
    See if this is desirable.

```shell
# Automatically prune deleted branches from your local copy when you fetch or pull
git config --global fetch.prune true
```

!!! TODO
    See if this is desirable.

```shell
# Ignore symlinks
git config --global core.symlinks false
```

If the setting doesn't work, try:

```shell
git config --global --unset core.symlinks
```

!!! TODO
    See if this is desirable. Add description.

```shell
# Disable SSL verify
git config --global http.sslVerify false
```

!!! TODO
    See if this is desirable. Add description.

```shell
git config --global status.showUntrackedFiles all
```

!!! TODO
    See if this is desirable. Add description.

```shell
git config --global transfer.fsckobjects true
```
