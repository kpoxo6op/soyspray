# Upgrade Kubespray 2.26->2.27

Checked out Kubespray submodule at tag 2.27, reapplied my customisations.

Created 2.27 branch in main soyspray repo.

Updated `kube_version` in my inventory

```sh
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu  kubespray/upgrade-cluster.yml
```
