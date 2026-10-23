# Crossover

Open <https://gi.soyspray.vip>. This is a private single-user planning page.
Boris signs in through the existing Authentik forward-auth page. No other
account can read the page or its data file.

The page is static. Everything it shows comes from one data file, which is
kept outside every repository and maintained by Claude from conversations.
Ansible publishes that file to the `gi-finance` Secret; the pod
mounts it read-only at `/data/finance.json`. The cluster keeps no other state
for this page.

## Normal use

Run these commands from the repository root:

```sh
make -f apps/gi/Makefile finance          # publish ~/.local/share/crossover/finance.json
make -f apps/gi/Makefile finance FILE=/path/to/finance.json
make smoke APP=gi                         # rollout, health, data file, sign-in gate
make check APP=gi
make diff APP=gi
kubectl -n argocd get application gi -o yaml
```

`finance` checks that the file is a Crossover data file, keeps a dated copy in
`history/` beside it, and writes the Secret. It prints the version fingerprint
and size, never the contents. The page shows the new version within about a
minute, without a restart. To return to an earlier version, publish its copy
from `history/`. The data format is documented in the private runtime
repository, `docs/DATA.md`.

Merge the pull request to deploy. Runtime source lives in a separate private
repository; a source change builds a separate immutable image, and a reviewed
digest promotion is what changes the running page.

## Access boundary

The whole site sits behind Authentik forward auth, including the page, its
scripts and the data file. The policy binds only the `gi-users` group, which is
separate from `cluster-admins` and `media-users`. An unavailable Authentik
service denies access rather than allowing it. The backend is an internal
ClusterIP Service. There is no public tunnel and no public landing page.

The container is nginx running as uid 101 with a read-only root filesystem and
a strict content security policy. It serves the built files, `/healthz` and
the mounted data file with `Cache-Control: no-store`; anything else under
`/data/` returns 404.

## Registry credential

The image is a private GHCR package, so the cluster needs a pull credential. It
is a GitHub personal access token (classic) with only the `read:packages` scope,
kept outside this checkout as an Ansible Vault variables file:

```yaml
gi_registry_username: kpoxo6op
gi_registry_token: <classic token with read:packages>
```

```sh
make check APP=gi
ansible-playbook apps/gi/bootstrap.yml -e @/path/to/gi-registry.vault.yml --ask-vault-pass
```

The bootstrap creates the `gi-registry` Secret in the `gi` namespace and never
replaces an existing credential. Without it the pod reports `ImagePullBackOff`,
because the package denies anonymous pulls.

## Earlier workspace

The page replaced an earlier SQLite workspace. Before the switch an isolated
restore of its last completed copy was verified in the cluster; it held no
records. Its two claims, `gi-data` and `gi-backups`, were then deleted with
`playbooks/operations/retirement/gi-sqlite-claims.yml`. Nothing in the cluster
holds its data any more, so reverting to its image would start it empty.

## What this package owns

`manifests/` holds the namespace, the deployment, the service, the
certificate, and the forward-auth ingress pair. `argocd/` holds
the Application and its AppProject. `finance.yml` publishes the data file and
`bootstrap.yml` the pull credential; Argo manages neither Secret. `tests/`
protects the access, data, and immutability boundaries.

The image digest in `manifests/deployment.yaml` is the only thing that decides
which reviewed code runs. The public repository never holds runtime source, a
data file, a figure, or a screenshot.
