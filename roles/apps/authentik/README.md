# Authentik application role

This role creates stable Authentik secrets, publishes the blueprints, and
applies the Authentik and PostgreSQL Argo CD applications. It also configures
the supported native OIDC clients and forward-auth applications.

`defaults/main.yml` selects the pushed Git revision. `tasks/main.yml` preserves
runtime credentials and applies the applications. `tasks/native-apps.yml`
configures application settings that cannot come from an Authentik blueprint.

Run the role from the repository root after `make go` and after you push the
branch:

```bash
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/deploy-argocd-apps.yml --tags authentik -e authentik_target_revision="$(git branch --show-current)"
```

Check the role and SSO contracts with:

```bash
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml playbooks/deploy-argocd-apps.yml --syntax-check --tags authentik
pytest -q tests/test_sso.py tests/test_sso_headlamp.py tests/test_sso_legacy_proxy.py tests/test_sso_native_apps.py
```

The role has no disabled path. Keep Authentik running when an application is
stopped. Roll back with a pushed Git revision; do not delete generated secrets
or the Authentik database. See the [Authentik application guide](../../../playbooks/argocd/applications/security/authentik/README.md)
for access groups, live checks, limits, and rollback details.
