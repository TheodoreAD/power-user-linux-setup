# pyenv
# =====
curl -sS -L https://pyenv.run | bash
tee -a "${HOME}/.zshrc" > /dev/null <<EOF

# pyenv
export PATH="\${HOME}/.pyenv/bin:\$PATH"
eval "\$(pyenv init -)"
eval "\$(pyenv virtualenv-init -)"
EOF
# to enable right away
source "${HOME}/.zshrc"
# install python 3.7.5, create and set a global virtual environment
pyenv install 3.7.5
pyenv virtualenv 3.7.5 global-375
pyenv global global-375

# pip configuration
# =================
PIP_INTERNAL_INDEX_URL=
mkdir -p "${HOME}/.config/pip"
tee -a "${HOME}/.config/pip/pip.conf" > /dev/null <<EOF
[global]
# index-url = ${PIP_INTERNAL_INDEX_URL}
# extra-index-url = https://pypi.org/simple
no-cache-dir = true
disable-pip-version-check = true

[install]
progress-bar = off

# [wheel]
# wheel-dir = /tmp/wheelhouse
# find-links = /tmp/wheelhouse

EOF

# poetry
# ======
# TODO: test
# curl -sS -L https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

# Enable plugin in Oh-My-Zsh
# mkdir -p "${ZSH}/plugins/poetry"
# poetry completions zsh > "${ZSH}/plugins/poetry/_poetry"
# enable poetry in your ~/.zshrc plugins
# plugins(
#     poetry
#     ...
#     )

# invoke
/usr/bin/python -m pip install invoke
sudo ln -s /home/tdumitrescu/.pyenv/versions/3.9.1/envs/auka-gae-test-app/bin/invoke /usr/bin/invoke

# nuitka
CODENAME=$(grep UBUNTU_CODENAME /etc/os-release | cut -d= -f2)
if [[ "${CODENAME}" = "" ]]; then
  CODENAME=$(lsb_release -c -s)
fi
wget -O - http://nuitka.net/deb/archive.key.gpg | sudo apt-key add -
echo "deb http://nuitka.net/deb/stable/${CODENAME} ${CODENAME} main" \
  | sudo tee "/etc/apt/sources.list.d/nuitka.list" > /dev/null
sudo apt update
sudo apt install nuitka
# only use if not using pyenv, otherwise make a dedicated pyenv virtualenv
if [[ ! -f "/usr/bin/nuitka" ]]; then
  sudo ln -s /usr/bin/nuitka3 /usr/bin/nuitka
fi

# TODO: test
python -m nuitka --module invoke --include-package=invoke
