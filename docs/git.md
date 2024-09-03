# Git

## Multi-email config

### Config file

Create a `${HOME}/git-projects.txt` file with your personal and/or work profiles.

Rules:

- each line in the file will be used by the script to create one directory
- line format is `projects_directory,git_commit_name,git_commit_email`
- no spaces allowed before or after the comma delimiters
- no quotes allowed, no commas allowed inside names

!!! INFO
    You should have a directory for each profile,
    so that when you clone projects in each directory
    git automatically uses the right name, email
    and any other custom settings might be required.

!!! WARNING
    If you use the example below for creating the file
    you must change your name and email for each context,
    i.e. personal GitHub or work GitHub.

To create the file via command line:

```shell
tee "${HOME}/git-projects.txt" >/dev/null <<EOF
github.com-personal,John Smith,john.smith@gmail.com
github.com-work,John Smith,john.smith@work.com
gitlab.com-personal,John Smith,john.smith@gmail.com
EOF
```

### Directory structure and per-directory configuration

```shell
# Disable global user name and email in favor of project-specific ones
git config --global --unset user.name
git config --global --unset user.email
# set up project directories and configure per-directory identities
PROJECTS_ROOT="${HOME}/projects"
mkdir -p "${PROJECTS_ROOT}"
IFS=$'\r\n' GLOBIGNORE='*' eval 'PROJECTS=($(<${HOME}/git-projects.txt))'
for project in "${PROJECTS[@]}"; do
  project_dir=$(echo ${project} | cut -d ',' -f 1)
  user_name=$(echo ${project} | cut -d ',' -f 2)
  user_email=$(echo ${project} | cut -d ',' -f 3)
  project_dir_full="${PROJECTS_ROOT}/${project_dir}"
  mkdir -p "${project_dir_full}"
  git config --global \
    includeIf.gitdir:"${project_dir_full}/".path "${project_dir_full}/.gitconfig"
  git config --file "${project_dir_full}/.gitconfig" \
    user.name "${user_name}"
  git config --file "${project_dir_full}/.gitconfig" \
    user.email "${user_email}"
done
```

## Global configuration

### Essentials

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

### Diffs and merge conflict resolution with Pycharm

Enable PyCharm as the default diff and merge tools, use with git difftool and git mergetool:

```shell
# change this to pycharm-community if you are using that
PYCHARM_BIN=pycharm-professional
PYCHARM_PATH="$(which ${PYCHARM_BIN})"
git config --global diff.tool ${PYCHARM_BIN}
git config --global difftool.prompt false
git config --global difftool.${PYCHARM_BIN}.cmd \
  \""${PYCHARM_PATH}"\"' diff "$LOCAL" "$REMOTE"'
git config --global merge.tool ${PYCHARM_BIN}
git config --global mergetool.prompt false
git config --global mergetool.${PYCHARM_BIN}.cmd \
  \""${PYCHARM_PATH}"\"' merge "$LOCAL" "$REMOTE" "$BASE" "$MERGED"'
git config --global mergetool.${PYCHARM_BIN}.keepBackup false
```

### Experimental

!!! WARNING
    Optional. Don't use unless you understand the effects.

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
