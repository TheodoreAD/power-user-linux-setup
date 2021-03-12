# Disable global user name and email in favor of project-specific ones
git config --global --unset user.name
git config --global --unset user.email
# set up project directories and configure per-directory identities
PROJECTS_ROOT="${HOME}/projects"
mkdir -p "${PROJECTS_ROOT}"
PROJECTS=(
    github.com-personal,"Teodor Dumitrescu","teodor.dumitrescu@gmail.com" \
)
for project in "${PROJECTS[@]}"; do
    project_dir=$(echo ${project} | cut -d "," -f 1)
    user_name=$(echo ${project} | cut -d "," -f 2)
    user_email=$(echo ${project} | cut -d "," -f 3)
    project_dir_full="${PROJECTS_ROOT}/${project_dir}"
    mkdir -p "${project_dir_full}"
    git config --global includeIf.gitdir:"${project_dir_full}/".path \
        \""${project_dir_full}/.gitconfig"\"
    git config --file "${project_dir_full}" user.name \""${user_name}"\"
    git config --file "${project_dir_full}" user.email \""${user_email}"\"
done
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
# Enable PyCharm as the default diff and merge tools, use with git difftool and git mergetool
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


# TODO: see if this is desirable
# When pulling code, always rebase your local changes
# git config --global pull.rebase true
# TODO: see if this is desirable
# Automatically prune deleted branches from your local copy when you fetch or pull
# git config --global fetch.prune true
# TODO: see if this is desirable
# [WINDOWS] Configure git not to mess with your line endings
# git config --global core.autocrlf false
# TODO: see if this is desirable
# Ignore symlinks
# If the setting doesn't work, try `git config --global --unset core.symlinks`
# git config --global core.symlinks false
# Disable SSL verify
# git config --global http.sslVerify false
# TODO: see if this is desirable
# TODO: add description
# git config --global status.showUntrackedFiles all
# TODO: see if this is desirable
# TODO: add description
# git config --global transfer.fsckobjects true

# GitHub CLI
curl -sS -L -o /tmp/gh_linux_amd64.deb https://github.com/cli/cli/releases/download/v0.6.4/gh_0.6.4_linux_amd64.deb
sudo dpkg -i /tmp/gh_linux_amd64.deb
