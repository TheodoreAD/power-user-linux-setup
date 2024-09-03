# Browsers

## Google Chrome

```shell
DEB_FILE="$(mktemp)"
URL="https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
curl -sS -L -o "${DEB_FILE}" "${URL}"
sudo dpkg -i "${DEB_FILE}"
rm -v -f "${DEB_FILE}"
```

## Microsoft Edge

```shell
# add the official GPG key to the keyring
KEY_FILE=/etc/apt/keyrings/microsoft.gpg
curl -sS -L -f https://packages.microsoft.com/keys/microsoft.asc \
  | sudo gpg --dearmor -o ${KEY_FILE}
sudo chmod a+r ${KEY_FILE}
# add the repository to Apt sources
OS_CODENAME=$(. /etc/os-release && echo "${VERSION_CODENAME}")
ARCH=$(dpkg --print-architecture)
REPO_URL=https://packages.microsoft.com/repos/edge
LIST_NAME=microsoft-edge-dev
echo "deb [arch=${ARCH} signed-by=${KEY_FILE}] ${REPO_URL} stable main" \
  | sudo tee /etc/apt/sources.list.d/${LIST_NAME}.list > /dev/null
sudo apt update
sudo apt install -y microsoft-edge-stable
```