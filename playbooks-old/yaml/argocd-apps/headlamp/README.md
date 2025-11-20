# headlamp

Headlamp dashboard deployed via its Helm chart and exposed through an ingress.
Helm chart version pinned at 0.35.

## Authentication

Get access token

```sh
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/new-headlamp-token.yml
```

Copy the generated token and paste it into the headlamp login page at https://headlamp.soyspray.vip
