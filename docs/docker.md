# Docker

<https://docs.docker.com/engine/install/ubuntu/>
<https://docs.docker.com/engine/install/linux-postinstall/>

If you've previously installed Docker uninstall everything:

```shell
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc
do
  sudo apt remove $pkg
done
```

Add the repository:

```shell
# add the official GPG key to the keyring
KEY_FILE=/etc/apt/keyrings/docker.asc
sudo curl -sS -L https://download.docker.com/linux/ubuntu/gpg -o ${KEY_FILE}
sudo chmod a+r ${KEY_FILE}
# add the repository to Apt sources
OS_CODENAME=$(. /etc/os-release && echo "${VERSION_CODENAME}")
ARCH=$(dpkg --print-architecture)
REPO_URL=https://download.docker.com/linux/ubuntu
LIST_NAME=docker
echo "deb [arch=${ARCH} signed-by=${KEY_FILE}] ${REPO_URL} ${OS_CODENAME} stable" \
  | sudo tee /etc/apt/sources.list.d/${LIST_NAME}.list > /dev/null
sudo apt update
```

Make sure you are about to install from the Docker repo
instead of the default Ubuntu repo, namely `docker-ce` shouldn't be installed,
the candidate for installation should be from the Docker repository
for Ubuntu 24.04 (noble):

```shell
apt-cache policy docker-ce
```

Install:

```shell
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Check that it’s running:

```shell
sudo systemctl status docker
```

If you get:

```
ERROR: Couldn't connect to Docker daemon at http+docker://localhost - is it running?
```

If it is stopped and masked: `Loaded: masked (Reason: Unit docker.service is masked.)`
then you need to unmask the service:

```shell
sudo systemctl unmask docker
```

On problems with the socket docker binds on you can allow your user to be owner of the socket:

```shell
sudo chown $USER:docker /var/run/docker.sock
```

Run docker without `sudo`:

```shell
# add the docker group if it doesn't already exist
sudo groupadd docker
# add docker group to the user
sudo gpasswd --add ${USER} docker
# alternative method, less safe since without -a it would remove the user from all other groups
# sudo usermod -aG docker $USER
# ? ACTION: Log out and login back again to refresh group membership.
# activate group changes right away
newgrp docker
# restart the docker daemon for the group changes to take effect
sudo service docker restart
```

Check you can run without `sudo`:

```shell
docker run hello-world
```

<https://docs.docker.com/reference/cli/dockerd/#daemon-configuration-file>
<https://docs.docker.com/config/containers/logging/configure/>

!!! TODO
    Add the local subnet to DNS settings in a scripted way.

Change daemon storage driver to `overlay2` and cgroup driver to `systemd`, set up DNS, logging:

```shell
LOCAL_SUBNET_IP="192.168.100.1"
sudo tee "/etc/docker/daemon.json" >/dev/null <<EOF
{
  "dns": ["1.1.1.1", "1.0.0.1", "8.8.8.8", "${LOCAL_SUBNET_IP}"],
  "exec-opts": ["native.cgroupdriver=systemd"],
  "log-driver": "local",
  "log-opts": {
    "max-size": "20m",
    "max-file": "5"
  },
  "storage-driver": "overlay2"
}
EOF
sudo mkdir -p /etc/systemd/system/docker.service.d
# restart docker
sudo systemctl daemon-reload
sudo systemctl restart docker
```

Check the your storage driver is `overlay2` and cgroup driver is `systemd`:

```shell
docker info
```

## Dive (Docker image inspection)

<https://github.com/wagoodman/dive?tab=readme-ov-file#installation>

```shell
DIVE_REPO="wagoodman/dive"
DIVE_VERSION=$(
  curl "https://api.github.com/repos/${DIVE_REPO}/releases/latest" \
    | grep '"tag_name": "v' \
    | sed -E 's#\s*"tag_name": "v([^"]+)".*#\1#'
)
DIVE_URL="https://github.com/${DIVE_REPO}/releases/download/v${DIVE_VERSION}/dive_${DIVE_VERSION}_linux_amd64.deb"
DIVE_DEB="$(mktemp)"
curl -sS -L -o "${DIVE_DEB}" "${DIVE_URL}"
sudo dpkg -i "${DIVE_DEB}"
rm "${DIVE_DEB}"
```
