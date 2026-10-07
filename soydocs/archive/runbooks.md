> Historical archive. Commands below describe former ownership and are not
> current procedures. Follow `inventory/soycluster/README.md` and app READMEs.

# Runbooks

## Cluster Creation

```sh
ansible-playbook -i inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu kubespray/cluster.yml
```

## Storage

```sh
cd soyspray
ansible-playbook -i inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/initialize-local-volumes.yml --tags storage
```

## How to provision [addons](inventory/soycluster/group_vars/k8s_cluster/addons.yml) only

```sh
ansible-playbook -i inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu kubespray/cluster.yml --tags apps
```

## How to provision [nginx ingress controller](kubespray/roles/kubernetes-apps/ingress_controller/meta/main.yml) only

```sh
ansible-playbook -i inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu kubespray/cluster.yml --tags ingress-nginx
```

Run Kubespray Runbook

```sh
cd kubespray
ansible-playbook -i inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu cluster.yml --tags apps
```

Run Soyspray Runbook

```sh
# Retired wrapper: use inventory/soycluster/README.md for foundation and app READMEs for inputs.
ansible-playbook -i inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/show-hello.yml
```
