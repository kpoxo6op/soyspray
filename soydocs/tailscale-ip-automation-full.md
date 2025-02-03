# Automating Tailscale IP in Kubernetes

## Current Setup

We have hardcoded Tailscale IP in two places:

```yaml
extraArgs:
  - --annotation-filter=external-dns.alpha.kubernetes.io/target in (100.69.17.31)
```

```yaml
annotations:
  external-dns.alpha.kubernetes.io/target: "100.69.17.31"
```

## Problem

The Tailscale IP changes when operator restarts. Screenshot shows different IPs after operator restart:

ingress-nginx-ingress-nginx: 100.100.115.18
ingress-nginx-ingress-nginx-1: 100.69.17.31

## Solution

Use Tailscale operator as LoadBalancer controller and let ExternalDNS read IPs dynamically.

1. Let Tailscale Operator Act as the “Load Balancer Controller”

Typically in Kubernetes, an Ingress or a Service of type=LoadBalancer is assigned an external IP by a load balancer controller (e.g. AWS ELB, MetalLB, etc.). Tailscale’s Operator can do something similar: it can publish your Service/Ingress on the Tailscale network and then update the .status.loadBalancer.ingress field in that resource with the Tailscale IP that it obtains.

    For Services: Tailscale can create a proxy Pod/Service to route Tailscale traffic, then set Service.status.loadBalancer.ingress = 100.x.x.x.
    For Ingress: Tailscale can “front” your NGINX Ingress with a Tailscale IP, effectively bridging the Tailscale network to the Ingress.

A. Use Tailscale Operator’s “Cluster Ingress” feature

Tailscale’s docs show how to create a CR or annotation that instructs the operator to handle your Ingress resources. See:

    Tailscale Operator: Cluster Ingress

When you configure it, Tailscale operator will:

    Spin up a tailscaled instance for your Ingress.
    Acquire a Tailscale IP (or multiple IPs for an HA setup).
    Update your Ingress’s .status.loadBalancer.ingress[0].ip with that Tailscale IP.

At that point, you do not need to specify a target: 100.x.x.x annotation on the Ingress at all. The operator takes care of it.
2. Let ExternalDNS Read the .status.loadBalancer.ingress IP

Once the Tailscale IP is in .status.loadBalancer.ingress, you can let ExternalDNS do its normal thing:

    Set sources: [ingress] (which you already have).
    Remove the --annotation-filter=external-dns.alpha.kubernetes.io/target in (100.69.17.31) so that ExternalDNS does not rely on a hardcoded IP. Instead, it will pick up the IP from .status.loadBalancer.ingress.
    You may still want a label/annotation filter if you only want to publish certain ingresses. But the key point is not to filter by a specific IP.
    If needed, you can also keep the --ignore-ingress-rules-spec or --ignore-ingress-status flags in your config. But make sure not to ignore the status if you want ExternalDNS to pick up the new IP automatically.

Sample values.yaml snippet

Below is a simplified approach for your external-dns/values.yaml so it uses .status.loadBalancer.ingress for records:

sources:

- ingress

extraArgs:

- --txt-prefix=external-dns-
- --ignore-ingress-tls-spec
- --ignore-ingress-rules-spec

# remove the IP-based annotation filter

# - --annotation-filter=external-dns.alpha.kubernetes.io/target in (100.69.17.31)

# Keep your domain filters, policy, etc

domainFilters:

- soyspray.vip
policy: upsert-only
registry: txt
txtOwnerId: k8s
provider:
  name: cloudflare

3. Remove IP Hard‐Coding from the Ingress

Now that Tailscale operator handles the IP, you do not need to put:

external-dns.alpha.kubernetes.io/target: "100.69.17.31"

on the Ingress. Remove that annotation. Your final Ingress might look like:

apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: podinfo
  namespace: podinfo
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-staging
    cert-manager.io/common-name: podinfo.test.soyspray.vip
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    external-dns.alpha.kubernetes.io/hostname: "podinfo.test.soyspray.vip"
    # remove external-dns.alpha.kubernetes.io/target entirely
    # optional: add a label or annotation to let Tailscale operator do "Cluster Ingress"
spec:
  ingressClassName: nginx
  rules:
    - host: podinfo.test.soyspray.vip
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: podinfo
                port:
                  number: 9898
  tls:
    - hosts:
        - podinfo.test.soyspray.vip
      secretName: podinfo-cert-tls

After the Tailscale operator sets .status.loadBalancer.ingress[0].ip to e.g. 100.100.115.18, ExternalDNS sees it and publishes podinfo.test.soyspray.vip → 100.100.115.18 in Cloudflare.
4. Handling Operator Restarts

If Tailscale operator is restarted and re‐assigns new Tailscale IP addresses, the steps happen automatically:

    Tailscale operator updates your Ingress .status.loadBalancer.ingress with the new IP.
    ExternalDNS sees that your Ingress status changed.
    ExternalDNS updates the DNS record in Cloudflare.

No manual editing or re‐deployment is needed.
Summary

    Use Tailscale Operator as if it were any other cloud LoadBalancer: it assigns an IP and updates .status.loadBalancer.ingress.
    Remove any reference to a hardcoded Tailscale IP from your Ingress and ExternalDNS flags. Let the operator supply the IP.
    Configure ExternalDNS to watch the Ingress status IP (no special annotation for the address needed).
    Result: Whenever Tailscale changes the IP (like on an operator restart), you get an automatic DNS update—no manual edits required.

This is the most “Kubernetes‐native” way to do it: treat Tailscale as your LB for Ingress or Service, let .status.loadBalancer.ingress reflect the assigned IP, and let ExternalDNS publish that IP. That solves the hardcoding problem and keeps your cluster fully dynamic.

## Implementation Steps

1. Remove hardcoded IP from external-dns values.yaml:

```yaml
sources:
  - ingress

extraArgs:
  - --txt-prefix=external-dns-
  - --ignore-ingress-tls-spec
  - --ignore-ingress-rules-spec
  - --fqdn-template={{.Name}}.{{.Namespace}}.soyspray.vip

domainFilters:
  - soyspray.vip
policy: upsert-only
registry: txt
txtOwnerId: k8s
provider:
  name: cloudflare
```

2. Update ingress.yaml to use Tailscale ingress:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: podinfo
  namespace: podinfo
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-staging
    cert-manager.io/common-name: podinfo.test.soyspray.vip
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    external-dns.alpha.kubernetes.io/hostname: "podinfo.test.soyspray.vip"
    external-dns.alpha.kubernetes.io/ttl: "60"
spec:
  ingressClassName: tailscale
  rules:
    - host: podinfo.test.soyspray.vip
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: podinfo
                port:
                  number: 9898
  tls:
    - hosts:
        - podinfo.test.soyspray.vip
      secretName: podinfo-cert-tls
```

## How It Works

1. Tailscale operator assigns IP to ingress
2. IP gets written to .status.loadBalancer.ingress
3. ExternalDNS reads IP from status and updates DNS
4. When operator restarts and IP changes, process repeats automatically

## Verification

Check ingress status for new IP:

```sh
kubectl get ingress podinfo -n podinfo -o yaml
```

Check DNS record updates:

```sh
dig podinfo.test.soyspray.vip
```

Test HTTPS access:

```sh
curl -v https://podinfo.test.soyspray.vip
```

## Additional Options

Use Tailscale Funnel to expose service publicly:

```yaml
metadata:
  annotations:
    tailscale.com/funnel: "true"
spec:
  ingressClassName: tailscale
```

Use LoadBalancer service instead of Ingress:

```yaml
spec:
  type: LoadBalancer
  loadBalancerClass: tailscale
```
