# SSH

!!! TODO
    Get data from files instead of hardcoding here.

```shell
# one email per key, it will also be used as in the key file name
SSH_ID_EMAILS=(
  teodor.dumitrescu@gmail.com
)

NODE_NAME=$(uname -n)

# create key(s)
# enter and re-enter the password for each key
for ssh_id_email in "${SSH_ID_EMAILS[@]}"; do
  echo "Key for ${ssh_id_email}__${NODE_NAME}:"
  ssh-keygen \
    -t rsa -b 4096 \
    -C "${ssh_id_email}__${NODE_NAME}" \
    -f "${HOME}/.ssh/${ssh_id_email}__${NODE_NAME}_rsa"
done

# Troubleshooting
# if files have the wrong permissions:
#sudo chmod 600 "${HOME}/.ssh/${ssh_id_email}__${NODE_NAME}_rsa"
#sudo chmod 644 "${HOME}/.ssh/${ssh_id_email}__${NODE_NAME}_rsa.pub"
# to change comment:
#ssh-keygen -f ~/.ssh/keyfilename -o -c -C "new comment"
# Command options explained:
# -f: private key file
# -o: convert the private key from PEM to the new OpenSSH format
# -c: change the comment in the private and public key files
# -C: comment text

# no spaces allowed after the comma delimiters
# user_name,host,id_email
SSH_HOSTS_TO_ID_EMAILS_MAP=(
  git,github.com,teodor.dumitrescu@gmail.com
)

function get_ssh_config_hosts() {
  for kvp in "${SSH_HOSTS_TO_ID_EMAILS_MAP[@]}"; do
    user_name=$(echo ${kvp} | cut -d ',' -f 1)
    host=$(echo ${kvp} | cut -d ',' -f 2)
    ssh_id_email=$(echo ${kvp} | cut -d ',' -f 3)
    echo "Host ${host}"
    echo "  IdentityFile ${HOME}/.ssh/${ssh_id_email}__${NODE_NAME}_rsa"
    echo "  User ${user_name}\n"
  done
}

# config for automatic mapping of hosts with identities
mkdir -p "${HOME}/.ssh"
tee -a "${HOME}/.ssh/config" >/dev/null <<EOF
# Specify HostName if there are more than one github.com accounts
# you will need to do "git clone git@host_name:user_name/repo_name.git"
# instead of "git clone git@github.com:user_name/repo_name.git"

$(get_ssh_config_hosts)

# keep this at the end
Host *
  # add keys automatically to ssh-agent, ignore for old versions of ssh
  IgnoreUnknown AddKeysToAgent
  AddKeysToAgent yes
  # required for MacOS keychain, not relevant to Ubuntu but good to know
  #IgnoreUnknown UseKeychain
  #UseKeychain yes
  # define the order in which to try auth methods
  PreferredAuthentications publickey,keyboard-interactive,password,hostbased,gssapi-with-mic
  # enable to prevent the use of keys for undefined servers
  IdentitiesOnly yes
  # enable for large uncompressed data transfers only
  #Compression yes
  # send a null packet to the other side every 300 seconds
  #  and abort if there's no response after 3 tries
  ServerAliveInterval 300
  ServerAliveCountMax 3
EOF

function forward_ssh_ids() {
  for kvp in "${SSH_HOSTS_TO_ID_EMAILS_MAP[@]}"; do
    user_name=$(echo ${kvp} | cut -d ',' -f 1)
    if [ "${user_name}" != "git" ]; then
      host=$(echo ${kvp} | cut -d ',' -f 2)
      ssh_id_email=$(echo ${kvp} | cut -d ',' -f 3)
      ssh-copy-id -f \
        -i "${HOME}/.ssh/${ssh_id_email}__${NODE_NAME}_rsa.pub" \
        "${user_name}@${host}"
    fi
  done
}

# Put your public key e.g. ~/.ssh/id_rsa.pub in the remote computer's
# authorized_keys file, creating the .ssh directory and authorized_keys file
# with the right permissions if necessary.
forward_ssh_ids

# Add the ssh keys to the agent
ssh-add "${HOME}/.ssh/"*${NODE_NAME}_rsa

# Write keychain loading script to login shell run commands file
tee -a "${HOME}/.zprofile" >/dev/null <<EOF

# load keychain
eval \$(keychain --nogui --quick --quiet --lockwait 0 --agents ssh --eval --confhost)
[ -z "\{$HOSTNAME}" ] && HOSTNAME=\$(uname -n)
[ -f "\${HOME}/.keychain/\${HOSTNAME}-sh" ] && source "\${HOME}/.keychain/\${HOSTNAME}-sh"
EOF
```
