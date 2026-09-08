# Authentik input role

This role preserves runtime credentials, publishes Authentik blueprints, and
configures native OIDC clients. Argo CD owns the Authentik, PostgreSQL, and
forward-auth Application definitions.

Run it only when credentials, blueprints, or native client settings need work:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/bootstrap-app-inputs.yml --tags authentik
```

Use `--tags authentik-blueprints` for an explicit blueprint publish. The role
has no disabled path. Do not delete generated secrets or the Authentik database
for rollback.
