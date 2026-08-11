# Autism traits assessment

This package serves the static assessment at `https://autism.soyspray.vip`.
The assessment has no server API. Answers and scoring stay in browser memory.
A refresh or closed page removes them. The application does not send them to
the origin or Cloudflare. Cloudflare can still process connection metadata to
deliver the site.

## Exposure boundary

The public path is one dedicated Cloudflare Tunnel:

```text
autism.soyspray.vip
  -> Cloudflare Tunnel autism-traits-public
  -> https://autism-traits.autism-traits.svc.cluster.local:443
  -> autism-traits web pod on 8443
```

The tunnel does not use `ingress-nginx`. The existing Ingress remains only for
the private LAN and Tailscale split-DNS path. Do not add a wildcard hostname,
a private network route, a NodePort, a LoadBalancer, `hostNetwork`, or a router
port forward. Do not add another hostname to this tunnel.

The connector uses `originServerName=autism.soyspray.vip` and
`noTLSVerify=false`. Nginx serves the existing cert-manager certificate on
8443. Thus, `cloudflared` verifies the origin certificate and hostname.
An exact-host Cloudflare response-header rule removes `NEL` and `Report-To`,
so the browser is not enrolled in Cloudflare Network Error Logging.

Namespace-wide Kubernetes NetworkPolicy defaults to deny. The web pod accepts
private HTTP only from `ingress-nginx` and HTTPS only from `cloudflared`. It has
zero egress. The connector can reach only:

- NodeLocal DNS at `169.254.25.10` on TCP and UDP port 53.
- The web pod on TCP port 8443.
- Cloudflare's published tunnel endpoints on TCP and UDP port 7844.

Calico policies end with an explicit deny. They also block node-host traffic
that standard Kubernetes NetworkPolicy does not cover. This blocks the
Kubernetes API, other namespaces, and `192.168.20.0/24`. Check the endpoint
list against the [Cloudflare tunnel firewall requirements](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/tunnel-with-firewall/)
before a connector upgrade. See also the [Cloudflare Kubernetes guide](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/deployment-guides/kubernetes/)
and [Kubernetes NetworkPolicy behavior](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

## Build and verify locally

Build the bundle before you commit deployment changes:

```bash
cd kubernetes/autism-traits/app
npm ci
npm run check
npx playwright install chromium
npm run test:e2e
```

Kustomize puts the bundle in bounded, content-hashed ConfigMaps and projects
the files into read-only `/site` paths. Render the package from the repository
root:

```bash
kubectl kustomize kubernetes/autism-traits
make check
```

## Create the dedicated tunnel

Create one remotely managed tunnel named `autism-traits-public` in Cloudflare
Zero Trust. Do not reuse a shared tunnel. Do not add the public hostname yet.
Copy only this tunnel's connector token into the ignored local `.env` file:

```dotenv
AUTISM_TRAITS_CLOUDFLARED_TOKEN=<dedicated-tunnel-token>
```

Never use `CLOUDFLARE_API_TOKEN` as the connector token. The Ansible role reads
`AUTISM_TRAITS_CLOUDFLARED_TOKEN` through `roles/app-secret`, creates the
`autism-traits-cloudflared-token` Secret, applies the restricted AppProject,
and then applies the Argo CD Application.

Deploy a pushed topic branch first:

```bash
make autism-traits AUTISM_TRAITS_REVISION=feat/autism-cloudflare-tunnel
kubectl -n autism-traits rollout status deployment/autism-traits
kubectl -n autism-traits rollout status deployment/autism-traits-cloudflared
```

Confirm that the Ingress no longer has the ExternalDNS hostname annotation:

```bash
kubectl -n autism-traits get ingress autism-traits \
  -o jsonpath='{.metadata.annotations.external-dns\.alpha\.kubernetes\.io/hostname}{"\n"}'
```

The output must be empty before the DNS cutover.

## Controlled DNS cutover

ExternalDNS uses `upsert-only`. Removing its annotation does not remove the old
records. Delete only the stale A, CNAME, and ownership TXT records for this
hostname. The ownership record is
`external-dns-autism.soyspray.vip`. Do not change any other DNS record.

Use the Cloudflare DNS API token only for this DNS cleanup. First list and
inspect the exact records:

```bash
set -a
source .env
set +a
AUTISM_ZONE_ID=$(curl --fail --silent --show-error \
  --header "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  'https://api.cloudflare.com/client/v4/zones?name=soyspray.vip' | \
  jq -er '.result | select(length == 1) | .[0].id')
AUTISM_RECORDS_FILE=$(mktemp)
curl --fail --silent --show-error \
  --header "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  "https://api.cloudflare.com/client/v4/zones/${AUTISM_ZONE_ID}/dns_records?per_page=100" \
  | jq '[.result[] | select(
      ((.name == "autism.soyspray.vip") and (.type == "A" or .type == "CNAME")) or
      ((.name == "external-dns-autism.soyspray.vip") and .type == "TXT")
    )]' > "${AUTISM_RECORDS_FILE}"
jq -r '.[] | [.id, .type, .name, .content] | @tsv' "${AUTISM_RECORDS_FILE}"
```

Stop if the output contains an unexpected name or type. When the list is
correct, delete only those returned record IDs:

```bash
while IFS= read -r AUTISM_RECORD_ID; do
  curl --fail --silent --show-error --request DELETE \
    --header "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    "https://api.cloudflare.com/client/v4/zones/${AUTISM_ZONE_ID}/dns_records/${AUTISM_RECORD_ID}" \
    | jq -e '.success == true'
done < <(jq -r '.[].id' "${AUTISM_RECORDS_FILE}")
rm -f "${AUTISM_RECORDS_FILE}"
```

Now add one Public Hostname route to `autism-traits-public`:

- Hostname: `autism.soyspray.vip`
- Service: `https://autism-traits.autism-traits.svc.cluster.local:443`
- Origin Server Name: `autism.soyspray.vip`
- No TLS Verify: disabled, which means `noTLSVerify=false`

Cloudflare creates the proxied tunnel CNAME. Do not create it before the stale
records are removed. Do not configure a wildcard or a private network route.

Cloudflare can add browser Network Error Logging headers to proxied responses.
Create one Response Header Transform Rule named
`autism-traits response privacy` with this exact expression:

```text
(http.host eq "autism.soyspray.vip")
```

Remove the `NEL` and `Report-To` response headers in that rule. Do not apply the
rule to the complete zone or another hostname.

## Cutover verification

Check the Cloudflare DNS record through the API. It must be one proxied CNAME
for `autism.soyspray.vip` whose content ends in `.cfargotunnel.com`. The old
ownership TXT record must be absent. Then check public resolvers:

```bash
dig @1.1.1.1 autism.soyspray.vip A +short
dig @1.1.1.1 autism.soyspray.vip AAAA +short
dig @1.1.1.1 external-dns-autism.soyspray.vip TXT +short
curl --fail --head https://autism.soyspray.vip/
test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --request POST https://autism.soyspray.vip/)" = 405
```

The A and AAAA answers must be public Cloudflare addresses. They must not be
`192.168.20.20`, `100.96.77.28`, or another private address. The TXT answer
must be empty. GET and HEAD must work. POST and every other method must return
405. Browser developer tools must show no answer submission, analytics,
telemetry, or third-party script request. The CSP must retain
`connect-src 'none'`. The response must not contain `NEL` or `Report-To`.

Confirm the deployed boundary and CNI:

```bash
kubectl get pods -n kube-system -l k8s-app=calico-node \
  -o jsonpath='{range .items[*]}{.spec.containers[0].image}{"\n"}{end}'
kubectl -n autism-traits get networkpolicy
kubectl -n autism-traits get networkpolicy.crd.projectcalico.org -o yaml
kubectl -n autism-traits get pods -o wide
kubectl -n autism-traits logs deployment/autism-traits-cloudflared --since=10m
for NODE_IP in 192.168.20.10 192.168.20.11 192.168.20.12; do
  ssh "ubuntu@${NODE_IP}" \
    "sudo iptables-save | grep -E 'autism-traits-(cloudflared-boundary|web-zero-egress)' || true"
done
```

Both connector replicas must be Ready on separate nodes. Healthy connector
logs must not show DNS, policy, origin TLS, or registration errors. The two
Calico policies must be present. Nodes that host the web or connector pods must
show their policy chains, including the final DROP rules.

Finally, test from a device that is off the home LAN and Tailscale. The autism
hostname must load. Every other hostname returned by this private command must
fail public DNS lookup and HTTPS connection:

```bash
kubectl get ingress --all-namespaces \
  -o jsonpath='{range .items[*].spec.rules[*]}{.host}{"\n"}{end}' | sort -u
```

Do not run this public isolation test through local or Tailscale split DNS.
The repository adds no router rule, NodePort, LoadBalancer, or host network.

## Normal deployment, disable, and rollback

After merge, reconcile `HEAD`:

```bash
make autism-traits AUTISM_TRAITS_REVISION=HEAD
```

To remove public exposure but keep the private site, delete only the
`autism.soyspray.vip` Public Hostname route from `autism-traits-public`. Confirm
that its tunnel CNAME is gone. Remove the `autism-traits response privacy`
header rule when this hostname is no longer public. Do not restore the old
ExternalDNS annotation or the private-address public A record.

To park the complete application, including both connector replicas and the
connector Secret, use the existing lifecycle switch:

```bash
make autism-traits AUTISM_TRAITS_ENABLED=false
```

The disable path quiesces Argo CD, removes the tunnel token, removes the
Application and its resources, and then removes the AppProject. It leaves the
remote Cloudflare tunnel object for controlled inspection or deletion.

For a code rollback, first remove the Cloudflare Public Hostname route. Then
reconcile a reviewed commit that already contains the DNS-detachment change:

```bash
make autism-traits AUTISM_TRAITS_REVISION=<known-good-safe-commit>
```

Do not roll back to a commit that gives ExternalDNS ownership of
`autism.soyspray.vip`; that can recreate the stale public A and TXT records.
