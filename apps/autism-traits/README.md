# Autism traits assessment

Open <https://autism.soyspray.vip>, choose a length, and answer the questions.
Results describe traits and link to their sources. Answers and scoring stay in
browser memory. Refreshing or closing the page clears the answers.

The site sends no answers, analytics, or third-party script requests. Cloudflare
processes connection metadata to deliver the public site. Nginx accepts only GET
and HEAD, sets no cookies, and keeps `connect-src 'none'`.

## Change and check

The `platform` operator owns this app. Source and browser checks are in `app/`;
Nginx configuration is in `config/`; deployment and boundary checks are in `tests/`.
The native root owns the existing Application and AppProject in `argocd/` and reads
`manifests/` directly. Application deletion leaves the workloads in place.

```sh
make check APP=autism-traits
make diff APP=autism-traits
make full-check
soyspray-venv/bin/python apps/autism-traits/test-image.py --url https://autism.soyspray.vip
```

For frontend work, run `npm ci`, `npm run check`, and `npm run test:e2e` in `app/`.
CI also checks the built image over HTTP and TLS, compares served images with the
source files, and runs phone and desktop browsers against that image.

A source merge builds an immutable GHCR image and opens a draft promotion PR.
The promotion changes the image digest in `manifests/deployment.yaml`. A source-only
merge does not change the running image. Build output stays local.

Commit and push, then preview the deployment:

```sh
make deploy APP=autism-traits REVISION=YOUR_PUSHED_BRANCH
```

After merge, run `make deploy APP=autism-traits`. This uses the
standard Ansible bootstrap and native root operation. Check `make status
APP=autism-traits FORMAT=json`, public and private access, and the actual browser
journey. `AUTISM_TRAITS_ENABLED=false` cannot delete an adopted app. Retirement
requires an explicit operation after removing its root registration.

## Access and recovery

The public route uses the dedicated Cloudflare Tunnel `autism-traits-public`.
The connector verifies the origin certificate and hostname over TLS. The private
LAN and Tailscale route uses the existing Ingress. Preserve the tunnel identity,
`autism-traits-cloudflared-token`, `autism-traits-tls`, and the public hostname.
Cert-manager owns certificate issuance; this bootstrap does not replace its key.

`bootstrap.yml` uses the shared `apps/bootstrap-secret-tasks.yml` procedure and preserves an existing token. A different supplied value stops
before any write. A matching value makes no change. The operation creates only
a missing Secret; native create rejects a competing creation instead of replacing
it. Check mode validates inputs and skips Secret creation. To restore a
missing token, put `autism_traits_cloudflared_token` in an Ansible Vault variables
file outside the checkout. Use the saved token from the off-cluster runtime backup;
do not create a new tunnel or commit the token. Run from the repository root:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu apps/autism-traits/bootstrap.yml \
  --ask-vault-pass -e @/private/path/autism-traits.vault.yml
```

There is no server-side answer database to restore. Recovery reinstalls the pinned
image and restores the access identity. Keep the Vault password outside the cluster.
Roll back the image digest and any configuration required by that image together.

The network policies allow the connector only DNS, the web service, and the
specified Cloudflare tunnel endpoints. Calico also closes the host and local IPVS
exceptions; the web container has no egress. Preserve the three declared host
endpoints when changing networking. Useful checks:

```sh
kubectl -n autism-traits get deployment,service,ingress,networkpolicy
kubectl -n autism-traits logs deployment/autism-traits-cloudflared --since=10m
dig @1.1.1.1 autism.soyspray.vip A +short
```

Check the public route through public DNS, not the private split-DNS address.
The existing independent external status-page integration remains in use.
