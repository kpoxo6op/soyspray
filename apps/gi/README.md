# GI private workspace

Open <https://gi.soyspray.vip>. This is a private single-user workspace. Boris
signs in through the existing Authentik forward-auth page. No other account can
read the pages, the API, or an export.

The workspace shows one position, the recent change, the next milestone, and one
primary action. Use **Record an update** to enter a dated, source-backed value,
review it, and save it. **Journey** keeps history and targets. **Plan** holds the
original assumptions, the reviewed import, and the export control.

The app keeps its records in SQLite on the single-writer `gi` deployment. The
`gi-data` claim holds the live database and `gi-backups` holds completed copies.
Both claims are home-cluster only. They are deliberately outside the off-cluster
Longhorn recovery groups, so they do not protect against complete loss of the
home cluster. Changing that boundary needs a separate decision.

Run these commands from the repository root:

```sh
make status APP=gi FORMAT=json
make check APP=gi
make diff APP=gi
```

Merge the pull request to deploy. Runtime source lives in a separate private
repository; a source change builds a separate immutable image, and a reviewed
digest promotion is what changes the running app.

## Access boundary

The whole site sits behind Authentik forward auth, including HTML, scripts, the
API, imports, and exports. The policy binds only the `gi-users` group, which is
separate from `cluster-admins` and `media-users`. An unavailable Authentik
service denies access rather than allowing it. The backend is an internal
ClusterIP Service. There is no public tunnel and no public landing page.

## What this package owns

`manifests/` holds the namespace, the two claims, the deployment, the service,
the certificate, and the forward-auth ingress pair. `argocd/` holds the
Application and its AppProject. `tests/` protects the access, data, and
immutability boundaries.

The image digest in `manifests/deployment.yaml` is the only thing that decides
which reviewed code runs. The public repository never holds runtime source, a
dataset, a record, an export, or a screenshot.
