# Cert Manager Configuration

This ArgoCD application configures Let's Encrypt issuer for cert-manager that
was installed by Kubespray.

Note: We are NOT using cert-manager Helm chart, as Kubespray handles the core
installation. This application only manages the ClusterIssuer configuration
through kustomize.

## Installation

Cert Manager is installed via Kubespray addons:

```yaml
# kubespray/inventory/soycluster/group_vars/k8s_cluster/addons.yml
cert_manager_enabled: true
cert_manager_namespace: "cert-manager"
```

This installs:

- cert-manager namespace
- cert-manager CRDs
- cert-manager controller
- cert-manager webhook
- cert-manager cainjector

This ArgoCD application adds:

- Let's Encrypt ClusterIssuers:
  - Staging issuer for testing
  - Production issuer for valid certificates
- Test and production certificates
- Sample workloads with HTTPS ingress
- DNS-01 challenge using Cloudflare
  - Domain soyspray.vip managed by Cloudflare DNS
  - Uses [Cloudflare API token] for DNS validation

## DNS Verification

Verify DNS records with:

```bash
# Check A record
dig soyspray.vip

# Check TXT records for cert challenges
dig _acme-challenge.soyspray.vip TXT
```

## DNSSEC

DNSSEC is enabled and managed by Cloudflare. Cert-manager is configured to use DNSSEC-aware nameservers for validation.

## Check Certificate Status

Monitor certificates and challenges:

```sh
(
  echo "=== ClusterIssuers ===" && kubectl get clusterissuer -o wide && echo && \
  echo "=== Certificates ===" && kubectl get certificate -n cert-manager && echo && \
  echo "=== Certificate Details ===" && kubectl describe certificate -n cert-manager prod-cert && echo && \
  echo "=== Challenges ===" && kubectl get challenges -n cert-manager && echo && \
  echo "=== Challenge Details ===" && kubectl describe challenges -n cert-manager && echo && \
  echo "=== Ingresses ===" && kubectl get ingress -n cert-manager && echo && \
  echo "=== Secrets ===" && kubectl get secrets -n cert-manager | grep -E 'tls|cert' && echo && \
  echo "=== cert-manager Pods ===" && kubectl get pods -n cert-manager && echo && \
  echo "=== cert-manager Logs ===" && kubectl logs -n cert-manager deployment/cert-manager | tail -n 50
) > cert-check.txt
```

[Cloudflare API token]: <https://dash.cloudflare.com/profile/api-tokens>
