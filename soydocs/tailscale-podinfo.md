# Exposing Kubernetes Ingress over Tailscale

This document explains how to expose your Kubernetes services (Podinfo in this
case) privately via Tailscale. Based on recent experiments and insights, we'll
use the Tailscale LoadBalancer for the ingress controller as it provides the
most flexible and maintainable solution.

> Note: While Tailscale offers multiple approaches, we specifically chose the
> LoadBalancer method as it integrates cleanly with our existing stack (MetalLB,
> external-dns, cert-manager) and provides full control over DNS and domain
> management.

## Implementation Approach: Tailscale LoadBalancer for the Ingress Controller

In this method, you reconfigure the ingress controller (e.g., Nginx Ingress) to
use a Tailscale-specific loadBalancer. This approach makes your ingress
controller receive a Tailscale IP (in the 100.x.x.x range) while maintaining
full control over DNS and domain management via external-dns. The flow is as
follows:

1. **Deployment Changes:**
   - Update the ingress controller's Service to be of type `LoadBalancer` and
     specify a `loadBalancerClass: tailscale`.
   - Example snippet for the Nginx ingress controller:

   ```yaml
   controller:
     replicaCount: 1
     service:
       type: LoadBalancer
       loadBalancerClass: tailscale
     ingressClassResource:
       default: false
     watchIngressWithoutClass: false
     metrics:
       enabled: true
       serviceMonitor:
         enabled: true
   ```

2. **DNS Setup:**
   - External-dns will publish an A record for your custom domain (e.g.
     podinfo.soyspray.vip) that points to the Tailscale-assigned IP.
   - This enables you to use your own domain names while maintaining the
     security of Tailscale's overlay network.

3. **Benefits:**
   - Provides a single ingress controller endpoint exclusively accessible via
     your Tailnet with standard TLS termination
   - Integrated with cert-manager for Let's Encrypt certificates
   - Full control over DNS and domain management via external-dns
   - Maintains existing ingress controller features and configuration
   - Centralizes Tailscale integration at the ingress level

## Additional Considerations

- **Cert-manager & DNS-01 Challenges:** Relies on cert-manager for obtaining
  valid TLS certificates via Let's Encrypt using the dns01 challenge. Ensure
  your Cloudflare credentials and configuration are correct.

- **External-dns Integration:** External-dns will update your domain records
  based on the Tailscale IP if correctly annotated. Verify that the TXT records
  for DNS ownership and the A records for your domain are correctly managed.

- **Testing:**
  - Verify that the Tailscale operator is running:

    ```bash
    kubectl get po -n tailscale-operator
    ```

  - On a Tailscale-connected device, test using:

    ```bash
    curl -v https://podinfo.soyspray.vip
    ```

  - Confirm DNS resolution returns a Tailscale IP (100.x.x.x) rather than a
    local MetalLB IP.

## Implementation Plan

### 1. Prerequisites Verification

Verify all required components are running:

```bash
# Check Tailscale Operator
kubectl get pods -n tailscale-system
kubectl get tailscale -n tailscale-system

# Check Nginx Ingress and its MetalLB IP
kubectl get svc -n ingress-nginx
kubectl get svc ingress-nginx -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Check MetalLB
kubectl get pods -n metallb-system
kubectl get ipaddresspools -n metallb-system

# Check Cert Manager
kubectl get pods -n cert-manager
kubectl get clusterissuers

# Check External DNS
kubectl get pods -n external-dns
```

### 2. Update Nginx Ingress ArgoCD App

The ingress-nginx service will maintain its MetalLB configuration while adding
Tailscale support:

```yaml
# nginx-ingress/values.yaml
controller:
  service:
    type: LoadBalancer
    loadBalancerClass: tailscale  # Add Tailscale support
    annotations:
      metallb.universe.tf/ip-allocated-from-pool: primary  # Maintain MetalLB config
```

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu kubespray/cluster.yml --tags ingress-nginx
```

Verification:

```bash
# Check service has both MetalLB and Tailscale configuration
kubectl get svc ingress-nginx -n ingress-nginx -o yaml
```

### 3. Configure Podinfo Ingress

Create/update podinfo ingress in ArgoCD app:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: podinfo
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-staging
    external-dns.alpha.kubernetes.io/hostname: podinfo.soyspray.vip
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - podinfo.soyspray.vip
    secretName: podinfo-tls
  rules:
  - host: podinfo.soyspray.vip
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: podinfo
            port:
              number: 9898
```

Verification:

```bash
# Check ingress is created
kubectl get ingress podinfo

# Check TLS certificate
kubectl get certificate podinfo-tls
kubectl describe certificate podinfo-tls

# Check DNS record in Cloudflare
dig podinfo.soyspray.vip
```

### 4. End-to-End Testing

From Tailscale-connected devices:

```bash
# From PC
curl -v https://podinfo.soyspray.vip

# From Android Phone
# Open browser and navigate to https://podinfo.soyspray.vip
```

Expected results:

- HTTPS connection successful with valid certificate from Let's Encrypt
- Podinfo UI/API accessible
- Connection works from all Tailscale devices
- DNS resolution working through Cloudflare

### 5. Monitoring

Monitor the setup:

```bash
# Check Tailscale operator logs
kubectl logs -n tailscale -l app=tailscale-operator

# Check Nginx Ingress logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx

# Check Podinfo logs
kubectl logs -l app=podinfo

# Check External DNS logs for Cloudflare updates
kubectl logs -n external-dns -l app=external-dns
```

## Rollback Plan

If issues occur:

1. Revert Nginx Ingress to previous configuration:

```bash
kubectl patch svc nginx-ingress-controller -n ingress-nginx --type=json \
  -p='[{"op": "remove", "path": "/spec/loadBalancerClass"}]'
```

2. Remove Podinfo Ingress:

```bash
kubectl delete ingress podinfo
```

3. Remove DNS record from Cloudflare if needed (this should be handled by
   external-dns)

## Success Criteria

- Podinfo accessible via HTTPS on podinfo.soyspray.vip
- Valid Let's Encrypt TLS certificate issued by cert-manager
- DNS resolution working through Cloudflare
- Access working from all Tailscale devices
- No exposure outside Tailscale network
- External-dns successfully managing Cloudflare DNS records

## Additional Considerations

### Local vs Remote Access

1. **Local Network Access:**
   - Services remain accessible via MetalLB IP (192.168.1.120)
   - No changes needed for local network clients
   - Local DNS can resolve to MetalLB IP for faster local access

2. **Remote Access via Tailscale:**
   - Tailscale provides secure overlay network access
   - Cloudflare DNS can be configured to return appropriate IP based on client
     location
   - All traffic is encrypted via Tailscale network

### DNS Configuration

For optimal routing:

- Configure split DNS if possible:
  - Local DNS resolves to MetalLB IP (192.168.1.120)
  - External DNS resolves to Tailscale IP
- If split DNS is not possible, Cloudflare DNS will work for both local and
  remote access

### Security Considerations

1. **Firewall Rules:**
   - Ensure firewall allows traffic from Tailscale network to Kubernetes nodes
   - MetalLB IP should only be accessible within local network
   - External access should only be possible via Tailscale

2. **Network Policies:**
   - Consider implementing Kubernetes Network Policies to restrict pod-to-pod
     communication
   - Ensure ingress-nginx can only be accessed via intended paths

## Integrating Podinfo with Tailscale

This document outlines the steps to expose the Podinfo application securely over
Tailscale.

## Prerequisites

- Kubernetes cluster with MetalLB configured
- Cert-manager installed and configured with Cloudflare DNS
- External-DNS configured for automatic DNS management
- Tailscale operator installed in the cluster
- A Cloudflare-managed domain (soyspray.vip)

## Architecture Overview

The setup involves multiple components working together:

1. MetalLB provides local network load balancing (192.168.1.x range)
2. Nginx Ingress handles TLS termination and routing
3. Cert-manager manages TLS certificates via Let's Encrypt
4. Tailscale provides secure remote access via its overlay network

## Required Steps

### 1. Configure Tailscale Operator for Service Access

The Tailscale operator must be configured to either:

- Set up subnet routing to advertise the cluster's service network
- Create a proxy that listens on a Tailscale IP (100.x.x.x) for ingress traffic

This is crucial as MetalLB IPs (192.168.1.x) are not directly accessible over
Tailscale.

### 2. Configure Ingress Resource

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: podinfo
  namespace: podinfo
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-staging"
    external-dns.alpha.kubernetes.io/hostname: "podinfo.soyspray.vip"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - podinfo.soyspray.vip
    secretName: podinfo-tls
  rules:
  - host: podinfo.soyspray.vip
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: podinfo
            port:
              number: 9898
```

### 3. Certificate Configuration

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: podinfo-tls
  namespace: podinfo
spec:
  secretName: podinfo-tls
  duration: 2160h
  renewBefore: 360h
  issuerRef:
    name: letsencrypt-staging
    kind: ClusterIssuer
  dnsNames:
  - podinfo.soyspray.vip
```

## Networking Flow

1. Remote Tailscale Client (e.g., phone) → Tailscale Overlay Network (100.x.x.x)
2. Tailscale Operator (proxy/router) → MetalLB Service IP (192.168.1.x)
3. Nginx Ingress → Podinfo Service → Podinfo Pod

## Testing and Verification

1. Verify Tailscale operator configuration:

```bash
kubectl get po -n tailscale-operator
```

2. Check if service is properly advertised on Tailscale:

```bash
# On a Tailscale-connected device
curl -v https://podinfo.soyspray.vip
```

3. Monitor certificate status:

```bash
kubectl get certificate -n podinfo
kubectl get certificaterequest -n podinfo
```

## Troubleshooting

1. DNS Resolution
   - Ensure podinfo.soyspray.vip resolves to the correct Tailscale IP
   - Check external-dns logs for any synchronization issues

2. Tailscale Connectivity
   - Verify Tailscale operator is running and healthy
   - Check if the service is properly advertised in Tailscale admin console
   - Ensure proper subnet routes or proxy configuration is in place

3. Certificate Issues
   - Monitor cert-manager logs
   - Verify Cloudflare DNS-01 challenge records
   - Check certificate and secret creation in the podinfo namespace

## Next Steps

1. Configure Tailscale operator for proper service advertisement (subnet routing
   or proxy mode)
2. Test connectivity from Tailscale-connected devices
3. Once verified with staging certificates, switch to production Let's Encrypt
   issuer

## Success Criteria

- Podinfo accessible via HTTPS on podinfo.soyspray.vip
- Valid Let's Encrypt TLS certificate issued by cert-manager
- DNS resolution working through Cloudflare
- Access working from all Tailscale devices
- No exposure outside Tailscale network
- External-dns successfully managing Cloudflare DNS records

## Conclusion

By using the Tailscale LoadBalancer approach for our ingress controller, we
maintain a clean and manageable architecture while gaining the security benefits
of Tailscale's overlay network. This method integrates seamlessly with our
existing cert-manager and external-dns setup, allowing for automated certificate
management and DNS record updates while maintaining full control over our domain
naming strategy.

---

*This implementation is based on practical experience and has been refined to
provide the most flexible solution for managing both Tailscale connectivity and
custom domain names.*
