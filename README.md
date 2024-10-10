# Soyspray

Home Cluster created with Kubespray on Soyo miniPCs.

## Temporary section - plan for Friday presentation

### inspiration

Alex "Private DNS"

Elliot Raspberry Pie on the Wall

David's own Kafka for learning

My son's intolenarnce to ads on mum's iPhone

### hardware

<https://www.aliexpress.com/item/1005006320947006.html?spm=a2g0o.order_list.order_list_main.11.b4cc1802ibY2k1>

raspberries are expensive, arm, power over ethernet, silent

Soyo no coolers, cheap, x86, power over 12v adapter

issues with widescreen monitor, issues at BPTech

does not have wake up on LAN

3d printed case

<https://github.com/jazwa/rackstack>

google [rackstack reddit](https://www.google.com/search?sca_esv=247a3cc0ba513c42&rlz=1C1GCEA_enNZ1125NZ1125&sxsrf=ADLYWILfr1QEWB3epzfxn33ovoS6t2Rowg:1728515483876&q=rackstack+reddit&udm=2&fbs=AEQNm0Aa4sjWe7Rqy32pFwRj0UkWd8nbOJfsBGGB5IQQO6L3J5MIFhvnvU242yFxzEEp3BfRFWcyM5BvpTgNzM3vKj4sd0YwvsXKiE93XEiAQkwpov3q73VlvX-t4vUzh_CK-Q9-yrbrCA6jPEVhd5czRbqluzhmH8XK9o0zlN-IQ8mQEpGRrtLGIAdoJ0yGhjmjrgJq5y1FNfejqu22xT_9bOL7drs8ig&sa=X&ved=2ahUKEwj4zJ77tYKJAxXtrlYBHS6sCkcQtKgLegQIFBAB&biw=1383&bih=1180&dpr=1&safe=active&ssui=on#vhid=re_s3Yssn2FUfM&vssid=mosaic)

commercial shop, blockhouse bay library, westgate library, central library experience

show 3d printed parts on camera

temporary solution cable box

crimping experience

pass through vs classic connectors

pinning Chinese devices in Taiwanese router by MAC

web interface throws 'Invalid MAC error'

ASUS mobile app allows pinning

### software

talos os

<https://www.talos.dev/v1.8/introduction/quickstart/>

out ot the box repos

<https://github.com/onedr0p/cluster-template>

kubespray

<https://github.com/kubernetes-sigs/kubespray>

cringey talosctl soyctl hide what is going on

bare kubeadm is hard

minikube and k3s are too stripped

kubespray is 16k stars, integratable, ansible, made by k8s sig

### my journey so far

started with Farhad's video

compiling ethernet driver from source

other people reported HomeOS not working with Motorcomm ethernet adapter

<https://github.com/silent-reader-cn/yt6801>

destroying the OS by installing incompatible packages

using correct WSL2 ubuntu server

bringing it together with ubuntu autoinstall

autoinstall is a mix of Canoninal made syntax with cloudinit in it

destroying the OS by updating kernel

ubuntu server power saving mode

testing pi-hole with manual helm install

destroying the OS by mounting k8s local storage to /

local storage provisioner

<https://github.com/kubernetes-sigs/sig-storage-local-static-provisioner>

properly intregrating kubespray into my own repo

exposing argoCD over plain http

installing Pi Hole via ArgoCD

importing filters to Pi Hole

### learnings

kubespray is fire

andible vs terraform

linux commands `lshw`, `ip link show`

kernel verion folders

compiled device driver files in kernel folder

kernel pin

my thoughts on ansible

my thoughts on ChatGPT 4o and o1

<https://repo2txt.simplebasedomain.com/>

### what is next

?

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

## How to Apply Argo CD Applications

```sh
cd soyspray

ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/install-k8s-python-libs.yml

ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/manage-argocd-apps.yml
```

## Testing Pi Hole

Updated my PC DNS to Pi Hole service

```sh
nslookup doubleclick.net
Server:  UnKnown
Address:  192.168.1.122

Name:    doubleclick.net
Addresses:  ::
          0.0.0.0
```

NZ Herald is full of ads in Edge, it is clean in FIrefox (uBlock Origin).

Updated Gravity (list of blocked domains) <http://192.168.1.122/admin/gravity.php>

Read <https://github.com/gorhill/uBlock/wiki/About-%22Why-uBlock-Origin-works-so-much-better-than-Pi%E2%80%91hole-does%3F%22>

Read <https://forum.level1techs.com/t/anyone-know-of-ublock-lists-for-pihole/212747>

Added Green lists from <https://firebog.net/>

Never try to add uBlock etc lists <https://www.reddit.com/r/pihole/comments/kv5rgp/ublock_origin_blocklists/>

Same experience by other dude <https://discourse.pi-hole.net/t/ads-are-displayed-everywhere-unsure-if-pi-hole-is-correctly-set-up/71127>

Check tips about secondary DNS. Check IPv6 toggling on router.

Looks like adding filters and not using secondary DNS helps.

## TODO

Test Pi Hole with secondary DNS and without secondary DNS.

Check how to pin nginx to `192.168.1.120` to metalLB so nothing else takes its address

Can't login to ArgoCD this time. How ArgoCD password is set? Workaround: run addons and expose argocd again.

## Backlog

Find out how Pi Hole gets its default password so we don't have to reset it

Ensure DNS is properly configured if using cert-manager with DNS-01 challenge
for certificate validation

Explore cert-manager for HTTPS access

linter to force `.yml` extension and `-` in file names

Codify List of local DNS domains setting <http://192.168.1.122/admin/dns_records.php>

```sh
#domain           IP
pihole.local      192.168.1.122
```
