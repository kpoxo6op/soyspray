# Nginx

Testing providing custom values.yaml file

## Helm value files from external Git repository

<https://argo-cd.readthedocs.io/en/stable/user-guide/multiple_sources/#helm-value-files-from-external-git-repository>

Testing

Update replicaCount from `5` to `2`

Push changes to remote

```sh
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/manage-argocd-apps.yml --tags nginx
```
