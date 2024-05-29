# Kuberentes for local development

## Kubectl

<https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/#install-using-native-package-management>

```shell
K8S_GPG_FILE="/usr/share/keyrings/kubernetes-archive-keyring.gpg"
K8S_GPG_URL="https://packages.cloud.google.com/apt/doc/apt-key.gpg"
curl -sS -L "${K8S_GPG_URL}" | sudo apt-key add -
# xenial is the repo that receives updates
echo "deb [signed-by=${K8S_GPG_FILE}] https://apt.kubernetes.io/ kubernetes-xenial main" \
  | sudo tee "/etc/apt/sources.list.d/kubernetes.list"
# alternatively
# sudo apt-add-repository "deb http://apt.kubernetes.io/ kubernetes-xenial main"
sudo apt update
sudo apt install -y kubectl
```

## Helm

<https://helm.sh/docs/intro/install/>

```shell
curl -sS -L "https://baltocdn.com/helm/signing.asc" | sudo apt-key add -
echo -sS -L "deb https://baltocdn.com/helm/stable/debian/ all main" \
  | sudo tee "/etc/apt/sources.list.d/helm-stable-debian.list"
sudo apt update
sudo apt install -y helm
# alternatively
# curl -sS -L "https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3" | bash
helm repo add stable "https://kubernetes-charts.storage.googleapis.com"
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
