# Kuberentes for local development

## Kubectl

<https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/#install-using-native-package-management>

```shell
# add the official GPG key to the keyring and ensure it has the right permissions
VERSION=1.30
KEY_FILE=/etc/apt/keyrings/kubernetes-apt-keyring.gpg
curl -sS -L https://pkgs.k8s.io/core:/stable:/v${VERSION}/deb/Release.key \
  | sudo gpg --dearmor -o ${KEY_FILE}
sudo chmod a+r ${KEY_FILE}
# add the repository to Apt sources
REPO_URL=https://pkgs.k8s.io/core:/stable:/v${VERSION}/deb/
LIST_NAME=kubernetes
echo "deb [signed-by=${KEY_FILE}] ${REPO_URL} /" \
  | sudo tee /etc/apt/sources.list.d/${LIST_NAME}.list > /dev/null
sudo apt update
sudo apt install -y kubectl
```

## Helm

<https://helm.sh/docs/intro/install/#from-apt-debianubuntu>

```shell
KEY_FILE=/usr/share/keyrings/helm.gpg
curl https://baltocdn.com/helm/signing.asc \
  | sudo gpg --dearmor -o ${KEY_FILE}
ARCH=$(dpkg --print-architecture)
REPO_URL=https://baltocdn.com/helm/stable/debian/
LIST_NAME=helm-stable-debian
echo "deb [arch=${ARCH} signed-by=${KEY_FILE}] ${REPO_URL} all main" \
  | sudo tee /etc/apt/sources.list.d/${LIST_NAME}.list > /dev/null
sudo apt update
sudo apt install -y helm
# configure
helm repo add stable "https://charts.helm.sh/stable"
helm repo add bitnami "https://charts.bitnami.com/bitnami"
helm repo update
```

## KIND

Kubernetes in Docker. A neat distribution relying solely on Docker, used for testing K8s itself.

For when you kinda want the banana but without the gorilla and the whole jungle.

Allows you to create and manage a single node K8s cluster on your machine
without the pain of setting up kubeadm, kubelet & friends.

<https://kind.sigs.k8s.io/docs/user/quick-start/>

```shell
curl -sS -L -o "./kind" "https://kind.sigs.k8s.io/dl/v0.10.0/kind-linux-amd64"
chmod +x "./kind"
mv "./kind" "${HOME}/local/bin/kind"
```

Alternatively, if you have `go` installed:

```shell
GO111MODULE="on" go get "sigs.k8s.io/kind@v0.10.0"
```
