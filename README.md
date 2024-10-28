# Soyspray 🌱💦

Home Cluster created with Kubespray on Soyo miniPCs.

[hosts.yml](kubespray/inventory/soycluster/hosts.yml)

[addons.yml](kubespray/inventory/soycluster/group_vars/k8s_cluster/addons.yml)

[argocd-apps](playbooks/yaml/argocd-apps)

## Network Configuration

The router DHCP range was updated to 192.168.1.50-192.168.1.99.

Static IPs were
assigned to the miniPCs by MAC address: 192.168.1.100, 192.168.1.101, and
192.168.1.102.

Static IP assignment only worked using the Asus router mobile
app. The web GUI produced an "invalid MAC" error.

## System Installation

Ubuntu Server 24.04 was installed on the Soyo miniPCs using autoinstall.

Ethernet drivers for the Motorcomm ethernet adapter were compiled during the
autoinstall process.

## Repo Setup

This repository was created using guidance from Farhad's video, Kubespray's
`integration.md`, and Kubespray Ansible installation docs.

### Hosts YAML Generation

To generate the `hosts.yaml` file, the following steps were used:

```sh
# Copy sample inventory
# Declare the IPs and hostnames for the nodes
# Generate the hosts.yaml file
# View the generated hosts.yaml
cp -rfp inventory/sample inventory/soycluster
declare -a IPS=(node-0,192.168.1.100 node-1,192.168.1.101 node-2,192.168.1.102)
CONFIG_FILE=inventory/soycluster/hosts.yaml python3 contrib/inventory_builder/inventory.py ${IPS[@]}
cat inventory/soycluster/hosts.yaml
```

A virtual environment (`soyspray-venv`) was used for dependency management and is included in `.gitignore` to keep environment-specific files out of the repository. Kubespray was integrated as a submodule in this repository.

```sh
# Create virtual environment
# Activate virtual environment
# Install requirements from the kubespray submodule
python3 -m venv soyspray-venv
source soyspray-venv/bin/activate
cd kubespray
pip install -U -r requirements.txt
```

## Cluster Creation

```sh
cd kubespray
ansible-playbook -i inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu cluster.yml
```

## Storage

```sh
cd soyspray
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/prepare-local-storage.yml --tags storage
```

## How to provision [addons](kubespray/inventory/soycluster/group_vars/k8s_cluster/addons.yml) only

```sh
cd kubespray
ansible-playbook -i inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu cluster.yml --tags apps
```

## Expose ArgoCD

To expose ArgoCD, the service was configured as a LoadBalancer in Kubernetes and
assigned the IP 192.168.1.121 using MetalLB.

The `argocd-cmd-params-cm` config map was updated to ensure that ArgoCD would
operate in insecure mode by keeping the `server.insecure` key set to "true". This
change enabled HTTP access without requiring HTTPS.

After updating the configuration, the argocd-server deployment was restarted to
apply the changes. The new pod was successfully started, exposing ArgoCD via
HTTP.

ArgoCD was then available at `http://192.168.1.121`.

```sh
cd soyspray
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu main.yml --tags expose-argocd
```

## Enable Kustomize

```sh
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu main.yml --tags enable-kustomize-argocd
```

## How to Apply Argo CD Applications

```sh
cd soyspray

ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/install-k8s-python-libs.yml

ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/manage-argocd-apps.yml
```

## Testing Pi-Hole as DNS Server

Update Router DNS settings via mobile app

| Type      | IP               | Note          |
| --------- | ---------------- | ------------- |
| Primary   | 192.168.1.122    |  Pi Hole      |
| Secondary | 8.8.8.8          |  Google       |

Set Up Pi-hole to Handle Local DNS Entries

| Domain                                         | IP               | Note          |
| ---------------------------------------------- | ---------------- | ------------- |
| [argocd.lan](http://argocd.lan/applications)   | 192.168.1.121    |               |
| [pihole.lan](http://pihole.lan/admin/login.php)| 192.168.1.122    |               |

Looks like adding filters and not using secondary DNS helps.

## Validate ArgoCD YAMLs

<https://go.dev/doc/install>

```sh
wget https://go.dev/dl/go1.23.2.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.23.2.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin
go version
#go version go1.23.2 linux/amd64
```

<https://github.com/yannh/kubeconform?tab=readme-ov-file#installation>

```sh
go install github.com/yannh/kubeconform/cmd/kubeconform@v0.6.7
export PATH=$PATH:$(go env GOPATH)/bin
source ~/.bashrc
kubeconform -h
```

```sh
kubeconform -summary -schema-location default -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/refs/heads/main/argoproj.io/application_v1alpha1.json' playbooks/yaml/argocd-apps/prometheus/prometheus-application.yaml
```

## How to Check Rendered Charts

```sh
helm template prometheus-stack prometheus-community/kube-prometheus-stack -f playbooks/yaml/argocd-apps/prometheus/values.yaml > rendered.yaml
