# Ingress Configuration and TLS Certificate Management

## Overview

This document describes the configuration of Ingress resources in the cluster and how TLS certificates are managed across namespaces.

## Components Used

- Nginx Ingress Controller (running on port 443)
- cert-manager (for TLS certificate management)
- Pihole DNS (192.168.1.33)
- Let's Encrypt (wildcard certificate issuer)

## Implementation Details

### 1. DNS Configuration

- Pihole DNS server (192.168.1.33) handles local resolution for `.soyspray.vip` domains
- DNS entries point to the Nginx Ingress Controller VIP (192.168.1.20)
- Example DNS records:

  ```
  argocd.soyspray.vip    -> 192.168.1.20
  grafana.soyspray.vip   -> 192.168.1.20
  pihole.soyspray.vip    -> 192.168.1.20
  ```

### 2. TLS Certificate Management

#### Certificate Details

- Wildcard certificate: `*.soyspray.vip`
- Issuer: Let's Encrypt
- Storage: Kubernetes Secret `prod-cert-tls`
- Primary namespace: `cert-manager`

#### Certificate Synchronization

Due to Kubernetes namespace isolation, TLS certificates must be copied to each namespace where they are needed. This is handled through Ansible playbooks:

1. Source certificate is stored in `cert-manager` namespace
2. Playbook copies the certificate to required namespaces (e.g., `argocd`)
3. Annotations are preserved to maintain cert-manager context

### 3. Ingress Configuration

Example ArgoCD ingress configuration:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd-ingress
  namespace: argocd
  annotations:
    kubernetes.io/ingress.class: nginx
spec:
  tls:
    - hosts:
        - argocd.soyspray.vip
      secretName: prod-cert-tls
  rules:
    - host: argocd.soyspray.vip
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: argocd-server
                port:
                  number: 80
```

## Troubleshooting

### Common Issues

1. Certificate Not Found Error:

```
Error getting SSL certificate "argocd/prod-cert-tls": local SSL certificate argocd/prod-cert-tls was not found
```

Solution: Run certificate sync playbook to copy certificate to the required namespace

### Diagnostic Commands

1. Check Ingress Status:

```bash
kubectl get ingress -n argocd
kubectl describe ingress argocd-ingress -n argocd
```

2. Verify Certificate Presence:

```bash
kubectl get secret prod-cert-tls -n argocd
```

3. Check Ingress Controller Logs:

```bash
kubectl logs -n ingress-nginx ingress-nginx-controller-xxxxx
```

4. Test DNS Resolution:

```bash
nslookup argocd.soyspray.vip 192.168.1.33
```

5. Verify HTTPS Access:

```bash
curl -vk https://192.168.1.20 -H 'Host: argocd.soyspray.vip'
```

6. Check TLS Certificate:

```bash
openssl s_client -connect 192.168.1.20:443 -servername argocd.soyspray.vip
```

## Certificate Sync Process

The certificate synchronization is managed through Ansible playbooks:

1. Extract certificate data:

```yaml
- name: Extract TLS certificate data
  shell: kubectl get secret prod-cert-tls -n cert-manager -o jsonpath='{.data.tls\.crt}'
  register: tls_crt
```

2. Copy to target namespace:

```yaml
- name: Copy TLS certificate
  kubernetes.core.k8s:
    state: present
    definition:
      apiVersion: v1
      kind: Secret
      metadata:
        name: prod-cert-tls
        namespace: argocd
        annotations:
          cert-manager.io/certificate-name: prod-cert
          cert-manager.io/issuer-kind: ClusterIssuer
          cert-manager.io/issuer-name: letsencrypt-prod
      type: kubernetes.io/tls
      data:
        tls.crt: "{{ tls_crt.stdout }}"
        tls.key: "{{ tls_key.stdout }}"
```
