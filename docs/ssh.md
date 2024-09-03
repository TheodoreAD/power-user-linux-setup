# SSH

Create a `${HOME}/ssh-emails.txt` file with your personal and/or work emails.
Rules:
- each line in the file will be used by the script to create one SSH key
- the machine (node) name and the email will be used in the key file name
- line format is `email`
- no spaces allowed before or after the email

!!! INFO
    You should have an SSH key for each email,
    so that when you have a security change
    you only lose access to the resources tied to one email.

!!! WARNING
    If you use the example below for creating the file
    you must change your name for each email.

```shell
tee "${HOME}/ssh-emails.txt" >/dev/null <<EOF
john.smith@gmail.com
john.smith@work.com
EOF
```

Create a `${HOME}/ssh-hosts.txt` file with your personal and/or work SSH hosts and user details.
Rules:
- each line in the file will be used by the script to create one SSH key
- the machine (node) name and the email will be used in the key file name
- line format is `user_name,host_alias,host_name,id_email`
- no spaces allowed before or after the comma delimiters

!!! INFO
    You need an entry for each host you intend to access.

    For git hosts, leave the host alias identical to the host name
    if you are using a single key for the platform, such as github.com.

    Specify an alias under Host and the address under HostName
    if there is more than one account for a platform such as github.com.

    You will need to use `git clone git@host_alias:user_name/repo_name.git`
    instead of `git clone git@github.com:user_name/repo_name.git`.

    For hosts intended for terminal access, you should use an alias
    to connect without having to remember IP adresses.

!!! WARNING
    If you use the example below for creating the file
    you must change your name for each email.

    The user name and IP address below are also just an example,
    if you don't plan to connect to any severs via terminal
    simply remove the line.

```shell
tee "${HOME}/ssh-hosts.txt" >/dev/null <<EOF
git,github.com,github.com,john.smith@gmail.com
git,gitlab.com,gitlab.com,john.smith@gmail.com
jsmith,10.11.12.13,john.smith@work.com
EOF
```

Create the SSH key(s) and config file, forward keys if any required, and set up the keychain:

```shell
IFS=$'\r\n' GLOBIGNORE='*' eval 'SSH_ID_EMAILS=($(<${HOME}/ssh-emails.txt))'
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

IFS=$'\r\n' GLOBIGNORE='*' eval 'SSH_HOSTS_TO_ID_EMAILS_MAP=($(<${HOME}/ssh-hosts.txt))'

function get_ssh_config_hosts() {
  for kvp in "${SSH_HOSTS_TO_ID_EMAILS_MAP[@]}"; do
    user_name=$(echo ${kvp} | cut -d ',' -f 1)
    host_alias=$(echo ${kvp} | cut -d ',' -f 2)
    host_name=$(echo ${kvp} | cut -d ',' -f 3)
    ssh_id_email=$(echo ${kvp} | cut -d ',' -f 4)
    echo "Host ${host_alias}"
    echo "  HostName ${host_name}"
    echo "  IdentityFile ${HOME}/.ssh/${ssh_id_email}__${NODE_NAME}_rsa"
    echo "  User ${user_name}\n"
  done
}

# config for automatic mapping of hosts with identities
mkdir -p "${HOME}/.ssh"
tee -a "${HOME}/.ssh/config" >/dev/null <<EOF
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
  # and abort if there's no response after 3 tries
  ServerAliveInterval 300
  ServerAliveCountMax 3
EOF

# this function ignores git hosts, it is meant for terminal connections to servers
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
