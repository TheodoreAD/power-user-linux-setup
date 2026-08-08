# Cloud

## Terraform

<https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli#install-terraform>

```shell
# add the official GPG key to the keyring and ensure it has the right permissions
KEY_FILE=/etc/apt/keyrings/hashicorp-archive-keyring.gpg
curl -sS -L https://apt.releases.hashicorp.com/gpg \
  | sudo gpg --dearmor -o ${KEY_FILE}
sudo chmod a+r ${KEY_FILE}
# add the repository to Apt sources
OS_CODENAME=$(. /etc/os-release && echo "${VERSION_CODENAME}")
REPO_URL=https://apt.releases.hashicorp.com
LIST_NAME=hashicorp
echo "deb [signed-by=${KEY_FILE}] ${REPO_URL} ${OS_CODENAME} main" \
  | sudo tee /etc/apt/sources.list.d/${LIST_NAME}.list > /dev/null
sudo apt update
sudo apt install -y terraform
```

!!! TODO
    See if this script doesn't cause problems with zsh.

If you want to enable autocompletion:

```shell
terraform -install-autocomplete
```

## Google Cloud SDK and CLI

!!! WARNING
    This is optional, do not install unless you're planning to work with Google Cloud.

<https://cloud.google.com/sdk/docs/install#deb>

```shell

# add the official GPG key to the keyring and ensure it has the right permissions
KEY_FILE=/usr/share/keyrings/cloud.google.gpg
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg \
  | sudo gpg --dearmor -o ${KEY_FILE}
sudo chmod a+r ${KEY_FILE}
# add the repository to Apt sources
REPO_URL=https://packages.cloud.google.com/apt
LIST_NAME=google-cloud-sdk
echo "deb [signed-by=${KEY_FILE}] ${REPO_URL} main" \
  | sudo tee /etc/apt/sources.list.d/${LIST_NAME}.list > /dev/null
sudo apt update
sudo apt install -y google-cloud-sdk
GOOGLE_INSTALL_PACKAGES=(
  google-cloud-sdk-app-engine-python
  google-cloud-sdk-app-engine-python-extras
  google-cloud-sdk-bigtable-emulator
  google-cloud-sdk-cbt
  google-cloud-sdk-cloud-build-local
  google-cloud-sdk-config-connector
  google-cloud-sdk-datalab
  google-cloud-sdk-datastore-emulator
  google-cloud-sdk-firestore-emulator
  google-cloud-sdk-kind
  google-cloud-sdk-kpt
  google-cloud-sdk-kubectl-oidc
  google-cloud-sdk-local-extract
  google-cloud-sdk-minikube
  google-cloud-sdk-pubsub-emulator
  google-cloud-sdk-skaffold
  kubectl
)
sudo apt install -y ${GOOGLE_INSTALL_PACKAGES[@]}
```

Although not essential (see below), `docker-credential-gcr` is missing from apt packages.

<https://github.com/GoogleCloudPlatform/docker-credential-gcr>

> Note: `docker-credential-gcr` is primarily intended for users
> wishing to authenticate with GCR in the absence of `gcloud`,
> though they are not mutually exclusive. For normal development setups,
> users are encouraged to use `gcloud auth configure-docker`, instead.

To later update all the packages:

```shell
GOOGLE_UPDATE_PACKAGES=(
  google-cloud-sdk
  google-cloud-sdk-anthos-auth
  google-cloud-sdk-app-engine-go
  google-cloud-sdk-app-engine-grpc
  google-cloud-sdk-app-engine-java
  google-cloud-sdk-app-engine-python
  google-cloud-sdk-app-engine-python-extras
  google-cloud-sdk-bigtable-emulator
  google-cloud-sdk-cbt
  google-cloud-sdk-cloud-build-local
  google-cloud-sdk-config-connector
  google-cloud-sdk-datalab
  google-cloud-sdk-datastore-emulator
  google-cloud-sdk-firestore-emulator
  google-cloud-sdk-kind
  google-cloud-sdk-kpt
  google-cloud-sdk-kubectl-oidc
  google-cloud-sdk-local-extract
  google-cloud-sdk-minikube
  google-cloud-sdk-pubsub-emulator
  google-cloud-sdk-skaffold
  google-cloud-sdk-spanner-emulator
  kubectl
)
sudo apt install -y --only-upgrade ${GOOGLE_UPDATE_PACKAGES[@]}
```

To fix GPG key expiration, run:

```shell
KEY_FILE=/usr/share/keyrings/cloud.google.gpg
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg \
  | sudo gpg --dearmor -o ${KEY_FILE}
```

!!! TODO
    Add auth instructions.

To configure:

```shell
gcloud init
```