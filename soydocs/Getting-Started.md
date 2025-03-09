# Getting Started

Starting on new machine

```sh
git submodule update --init --recursive
```

Get the private key from Enpass

```sh
ssh-keygen -lf ~/.ssh/id_rsa
2048 SHA256:fOPZU/+rmjfNyUQeFyIv+rXr+IRRuSnu7gSkI++OlkM boris@borex-pc (RSA)
```

[SSH access](https://github.com/kubernetes-sigs/kubespray/blob/master/docs/getting_started/setting-up-your-first-cluster.md#access-the-kubernetes-cluster)

```sh
IP_CONTROLLER_0=192.168.1.100
mkdir -p ~/.kube
ssh ubuntu@$IP_CONTROLLER_0

USERNAME=$(whoami)
sudo chown -R $USERNAME:$USERNAME /etc/kubernetes/admin.conf
exit

IP_CONTROLLER_0=192.168.1.100
scp ubuntu@$IP_CONTROLLER_0:/etc/kubernetes/admin.conf ~/.kube/config
sed -i "s/127.0.0.1/$IP_CONTROLLER_0/" ~/.kube/config
chmod 600 ~/.kube/config
```

Install tools

```sh
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
sudo git clone https://github.com/ahmetb/kubectx /opt/kubectx && sudo ln -s /opt/kubectx/kubectx /usr/local/bin/kubectx && sudo ln -s /opt/kubectx/kubens /usr/local/bin/kubens
```

Test

```sh
kubectl get nodes
NAME     STATUS   ROLES           AGE   VERSION
node-0   Ready    control-plane   81d   v1.31.1
node-1   Ready    control-plane   81d   v1.31.1
node-2   Ready    <none>          81d   v1.31.1
```

Venv

```sh
sudo apt-get install python3-pip python3.12-venv -y
python3 -m venv soyspray-venv
source soyspray-venv/bin/activate
cd kubespray
pip install -U -r requirements.txt
```
