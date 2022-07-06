# Docker

Add the repository:

```shell
# update your existing list of packages
sudo apt update
# add the GPG key for the official Docker repository to your system
curl -sS -L -f "https://download.docker.com/linux/ubuntu/gpg" | sudo apt-key add -
# add the Docker repository to APT sources
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
# update the package database with the Docker packages from the newly added repo
sudo apt update
```

Make sure you are about to install from the Docker repo
instead of the default Ubuntu repo, namely `docker-ce` shouldn't be installed,
the candidate for installation should be from the Docker repository
for Ubuntu 20.04 (focal):

```shell
apt-cache policy docker-ce
```

Install:

```shell
sudo apt install -y docker-ce
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
sudo gpasswd -a ${USER} docker
# alternative method, less safe since without -a it would remove the user from all other groups
# sudo usermod -aG docker $USER
# ? ACTION: Log out and login back again to refresh group membership.
# restart the docker daemon for the group changes to take effect
sudo service docker restart
```

Check you can run without `sudo`:

```shell
docker run hello-world
```

!!! TODO
    Add the local subnet to DNS settings in a scripted way.

Change daemon storage driver to `overlay2` and cgroup driver to `systemd`, set up DNS:

```shell
LOCAL_SUBNET_IP="192.168.100.1"
sudo tee "/etc/docker/daemon.json" >/dev/null <<EOF
{
  "exec-opts": ["native.cgroupdriver=systemd"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m"
  },
  "storage-driver": "overlay2",
  "dns": ["1.1.1.1", "1.0.0.1", "${LOCAL_SUBNET_IP}"]
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
