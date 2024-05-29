# Cloud

## Terraform

```shell
curl -sS -L -f https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt update
sudo apt install -y terraform
```

## Google Cloud SDK and CLI

!!! WARNING
    This is optional, do not install unless you're planning to work with Google Cloud.

!!! TODO
    Add post-install auth instructions.

```shell

echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
  | sudo tee -a "/etc/apt/sources.list.d/google-cloud-sdk.list"
curl -sS -L "https://packages.cloud.google.com/apt/doc/apt-key.gpg" \
  | sudo apt-key --keyring "/usr/share/keyrings/cloud.google.gpg" add -
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
curl -sS -L "https://packages.cloud.google.com/apt/doc/apt-key.gpg" \
  | sudo apt-key --keyring "/usr/share/keyrings/cloud.google.gpg" add -
```