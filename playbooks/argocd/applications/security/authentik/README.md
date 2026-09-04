# Authentik

Authentik provides single sign-on for private cluster applications. The Ansible
role creates stable runtime secrets and applies this Argo CD application.

## Normal use

The blueprints define two access groups:

- `media-users` can use Jellyfin.
- `cluster-admins` can use administrative applications and Jellyfin
  administration.

`blueprints/legacy-forward-auth.yaml` protects browser surfaces through the
Authentik proxy outpost. `blueprints/native-apps.yaml` defines OpenID Connect
(OIDC) clients for applications that support native sign-in. Jellyfin uses
native OIDC in a browser. Dispatcharr uses forward auth as an access gate and
still requires its local administrator login.

Jellyfin keeps its API outside forward auth so native clients can use Quick
Connect. LAN and Tailscale source restrictions remain separate from Authentik
authorization. Media Helper has no ingress or user interface. Its internal
service uses network rules instead of interactive SSO.

## Commands and checks

Run the local checks before deployment:

```bash
source soyspray-venv/bin/activate
pytest -q tests/test_sso.py tests/test_sso_headlamp.py tests/test_sso_legacy_proxy.py tests/test_sso_native_apps.py tests/test_live_tv.py
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml playbooks/deploy-argocd-apps.yml --syntax-check --tags authentik
```

After the branch is pushed, reconcile Authentik from that revision:

```bash
make go
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/deploy-argocd-apps.yml --tags authentik -e authentik_target_revision="$(git branch --show-current)"
```

Check the Argo CD application and workloads:

```bash
kubectl -n argocd get application authentik
kubectl -n authentik get deployment,pod
```

For live acceptance, confirm these results:

1. `https://tv.soyspray.vip` opens Jellyfin.
2. A Jellyfin browser user can sign in through Authentik.
3. A member of `media-users` can use Live TV but cannot open Dispatcharr administration.
4. A member of `cluster-admins` can open Dispatcharr administration.
5. Jellyfin native-client Quick Connect works.

## Limits

Forward auth protects access to an application. It does not add native OIDC to
an application that does not support it. Local recovery accounts remain enabled
for Argo CD, Jellyfin, and other applications that need them.

The role preserves generated client secrets. A secret resource-version
annotation restarts Authentik when those secrets change. Do not edit generated
secrets in Git.

## Shutdown and rollback

Authentik has no application-specific shutdown switch. Do not stop identity
services when you stop Live TV. `LIVE_TV_ENABLED=false` removes the Live TV
applications and leaves Authentik running.

To roll back, revert the applicable commits on a topic branch, push the branch,
and reconcile Authentik with that branch as `authentik_target_revision`. After
merge, reconcile `HEAD`. The rollback must preserve `authentik-runtime` and the
PostgreSQL data.
