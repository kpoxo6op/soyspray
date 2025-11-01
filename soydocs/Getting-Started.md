# Getting Started

Starting on new machine

```sh
git submodule update --init --recursive
```

Get the private key from Enpass

```sh
mkdir -p ~/.ssh
touch ~/.ssh/id_rsa
# paste and check
chmod 600 ~/.ssh/id_rsa
ssh-keygen -lf ~/.ssh/id_rsa
2048 SHA256:fOPZU/+rmjfNyUQeFyIv+rXcdr+IRRuSnu7gSkI++OlkM boris@borex-pc (RSA)
```

[SSH access](https://github.com/kubernetes-sigs/kubespray/blob/master/docs/getting_started/setting-up-your-first-cluster.md#access-the-kubernetes-cluster)

```sh
IP_CONTROLLER_0=192.168.1.10
mkdir -p ~/.kube
ssh ubuntu@$IP_CONTROLLER_0

USERNAME=$(whoami)
sudo chown -R $USERNAME:$USERNAME /etc/kubernetes/admin.conf
exit

scp ubuntu@$IP_CONTROLLER_0:/etc/kubernetes/admin.conf ~/.kube/config
sed -i "s/127.0.0.1/$IP_CONTROLLER_0/" ~/.kube/config
chmod 600 ~/.kube/config
```

Install tools

```sh
sudo apt install make -y
sudo make install

# Install k9s
curl -sS https://webi.sh/k9s | sh
source ~/.config/envman/PATH.env

# Install argonaut
curl -sSL https://raw.githubusercontent.com/darksworm/argonaut/main/install.sh | sudo sh
```

Test

```sh
kubectl get nodes
NAME     STATUS   ROLES           AGE     VERSION
# nodes
```

ArgoCD setup

```sh
# Set config directory to avoid legacy path issues
export ARGOCD_CONFIG_DIR="$HOME/.config/argocd"

# Login to ArgoCD
argocd login argocd.soyspray.vip --grpc-web --username admin --password password

# Test argonaut (requires TTY)
argonaut
```

Venv

```sh
python3 -m venv soyspray-venv
source soyspray-venv/bin/activate
pip install -U -r kubespray/requirements.txt
# cycle through The authenticity of host '192.168.1.xxx' can't be established.
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/show-hello.yml
```
