# Runbooks

## Cluster Creation

```sh
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu kubespray/cluster.yml
```

## Storage

```sh
cd soyspray
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/setup-local-volumes.yml --tags storage
```

## How to provision [addons](kubespray/inventory/soycluster/group_vars/k8s_cluster/addons.yml) only

```sh
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu kubespray/cluster.yml --tags apps
```

## How to provision [nginx ingress controller](kubespray/roles/kubernetes-apps/ingress_controller/meta/main.yml) only

```sh
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu kubespray/cluster.yml --tags ingress-nginx
```

Run Kubespray Runbook

```sh
cd kubespray
ansible-playbook -i inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu cluster.yml --tags apps
```

Run Soyspray Runbook

```sh
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu main.yml --tags argocd,storage
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/hello-soy.yml
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/manage-argocd-apps.yml --tags pihole
```
