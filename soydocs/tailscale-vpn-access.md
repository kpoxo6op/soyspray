# Tailscale VPN Access

The goal is to provide secure access to cluster services (*.soyspray.vip) through Tailscale VPN while maintaining local network access. This is achieved using a dual-ingress setup:

1. **Current Setup**:
   - MetalLB provides IP (192.168.1.120) for local network access
   - External-DNS updates Cloudflare DNS records
   - Ingress-NGINX handles traffic routing
   - Cert-Manager manages SSL certificates

   Important: The current ingress-nginx configuration is managed by Kubespray in `kubespray/inventory/soycluster/group_vars/k8s_cluster/addons.yml`:

   ```yaml
   # DO NOT MODIFY these settings directly - they are managed by Kubespray
   ingress_nginx_enabled: true
   ingress_nginx_host_network: false
   ingress_nginx_service_type: LoadBalancer
   ingress_nginx_service_annotations:
     external-dns.alpha.kubernetes.io/hostname: "*.soyspray.vip"
     tailscale.com/expose: "true"
   ```

   MetalLB configuration in the same file:

   ```yaml
   # DO NOT MODIFY these settings directly - they are managed by Kubespray
   metallb_enabled: true
   metallb_speaker_enabled: "{{ metallb_enabled }}"
   metallb_config:
     address_pools:
       primary:
         ip_range:
           - 192.168.1.120-192.168.1.140
         auto_assign: true
   ```

2. **Tailscale Access Options**:
   The Tailscale operator provides three ways to expose services:
   - Create a LoadBalancer service with `loadBalancerClass: tailscale`
   - Annotate existing services with `tailscale.com/expose: "true"`
   - Use Tailscale's ingress class

   We're currently using the annotation approach but will switch to LoadBalancer for better control.

3. **Dual-Access Implementation**:
   - IMPORTANT: Keep existing MetalLB-based ingress-nginx service untouched (managed by Kubespray)
   - Create additional ingress-nginx service with Tailscale LoadBalancer:

     ```yaml
     apiVersion: v1
     kind: Service
     metadata:
       name: ingress-nginx-tailscale  # Different name to avoid conflict
       namespace: ingress-nginx
       annotations:
         external-dns.alpha.kubernetes.io/hostname: "*.soyspray.vip"
     spec:
       type: LoadBalancer
       loadBalancerClass: tailscale
       ports:
         - name: http
           port: 80
         - name: https
           port: 443
       selector:
         app.kubernetes.io/name: ingress-nginx
     ```

   Note: The additional service uses the same selector to route to the existing ingress-nginx pods, avoiding duplication of the ingress controller itself.

### End Goal

- Access *.soyspray.vip domains from anywhere using Tailscale VPN
- Maintain local network access without VPN
- Keep all ingress-nginx features (SSL termination, path routing)
- Automatic DNS updates when IPs change
- No manual intervention needed for Tailscale IP changes

### Implementation State

Current progress:

- [x] Tailscale operator installed

  ```bash
  # Check Tailscale operator pods
  kubectl get pods -n tailscale-system
  ```

  Output:

  ```
  NAME                       READY   STATUS    RESTARTS   AGE
  operator-96dc568bb-f7vfx   1/1     Running   0          16h
  ts-ingress-nginx-vmcwj-0   1/1     Running   0          42h
  ```

- [x] External-DNS configured with Cloudflare

  ```bash
  # Check External-DNS pods and logs
  kubectl get pods -n external-dns
  kubectl logs -n external-dns -l app.kubernetes.io/name=external-dns --tail=5
  ```

  Output:

  ```
  NAME                            READY   STATUS    RESTARTS   AGE
  external-dns-564cb7b895-jnnrt   1/1     Running   0          16h
  # Logs show: "All records are already up to date"
  ```

- [x] MetalLB service working (192.168.1.120)

  ```bash
  # Check MetalLB components
  kubectl get pods -n metallb-system

  # Check ingress-nginx service
  kubectl get svc -n ingress-nginx ingress-nginx
  ```

  Output:

  ```
  # MetalLB components
  NAME                          READY   STATUS    RESTARTS   AGE
  controller-7f649565d4-gtbcx   1/1     Running   0          4d13h
  speaker-dg8p6                 1/1     Running   6          4d13h
  speaker-gdrj4                 1/1     Running   13         4d13h
  speaker-rwxjd                 1/1     Running   0          4d13h

  # Ingress Service
  NAME            TYPE           CLUSTER-IP     EXTERNAL-IP     PORT(S)
  ingress-nginx   LoadBalancer   10.233.25.42   192.168.1.120   80:32078/TCP,443:31244/TCP
  ```

- [x] Cert-manager with DNS01 challenge (required for private ingress)

  ```bash
  # Check cert-manager pods
  kubectl get pods -n cert-manager

  # Check ClusterIssuers
  kubectl get clusterissuers

  # Check DNS01 configuration
  kubectl get clusterissuer letsencrypt-prod -o yaml | grep -A 10 solvers
  ```

  Output:

  ```
  # Cert-manager pods
  NAME                                      READY   STATUS    RESTARTS   AGE
  cert-manager-79747c8677-pcxpl             1/1     Running   1          3d18h
  cert-manager-cainjector-966b79998-s8vz2   1/1     Running   4          3d18h
  cert-manager-webhook-58ff58d95b-ckcp4     1/1     Running   0          3d18h

  # ClusterIssuers
  NAME                  READY   AGE
  letsencrypt-prod      True    3d19h
  letsencrypt-staging   True    3d19h

  # DNS01 Cloudflare configuration verified
  solvers:
    - dns01:
        cloudflare:
          apiTokenSecretRef:
            key: api-token
            name: cloudflare-api-token
  ```

- [~] Tailscale LoadBalancer service (In Progress)
  - Working on ingress configuration in `playbooks/yaml/argocd-apps/nginx/ingress.yaml`
  - Added Tailscale Funnel support with `tailscale.com/funnel: "true"` annotation
  - Verified annotations from official documentation
  - Next: Test and verify the configuration
- [ ] DNS records for dual access

Next steps:

1. Complete and verify Tailscale LoadBalancer service configuration
2. Verify External-DNS updates
3. Test VPN access
4. Document final configuration

### Implementation Notes

- The MetalLB ingress-nginx service is managed by Kubespray through addons.yml
- DO NOT modify the existing ingress-nginx service or MetalLB configuration directly
- All changes for Tailscale access should be done through additional resources
- Use ArgoCD to manage the additional Tailscale LoadBalancer service
- Changes to the base configuration should be made through Kubespray's inventory
- Must use DNS01 challenge for cert-manager since ingress isn't publicly accessible
- External-DNS policy should be set to "sync" to properly manage DNS records

### Prerequisites

1. Tailscale:
   - Operator installed with OAuth credentials
   - Proper ACL tags configured
2. External-DNS:
   - Configured with Cloudflare credentials
   - Policy set to "sync"
3. Cert-Manager:
   - DNS01 challenge configured
   - Cloudflare API token with proper permissions
4. ArgoCD:
   - Used for managing all additional resources
5. Existing Setup (Managed by Kubespray):
   - MetalLB (192.168.1.120-140 range)
   - Ingress-NGINX base installation

### Links

<https://medium.com/@mattiaforc/zero-trust-kubernetes-ingress-with-tailscale-operator-cert-manager-and-external-dns-8f42272f8647>

### DNS Strategy

We will use a single wildcard domain (*.soyspray.vip) with dual A records:

1. Local MetalLB IP (192.168.1.120)
2. Tailscale IP (dynamic, managed by Tailscale operator)

This approach means:

- Local network clients will use the MetalLB IP directly (faster)
- Remote clients using Tailscale VPN will use the Tailscale IP
- DNS resolution behavior:
  - Local network: Both IPs returned, local IP preferred due to network proximity
  - Remote/VPN: Both IPs returned, Tailscale IP accessible through VPN
  - Public internet: Both IPs returned but neither accessible (security by design)

Example DNS configuration:

```
*.soyspray.vip.    300    IN    A    192.168.1.120        # MetalLB IP
*.soyspray.vip.    300    IN    A    100.x.y.z            # Tailscale IP (dynamic)
```

This setup ensures:

- Single domain for all services (simpler certificate management)
- Automatic failover if one access method is unavailable
- No manual DNS updates needed when Tailscale IPs change
- Zero-trust security (services only accessible via local network or VPN)

### Common Pitfalls

When running dual A records with MetalLB and Tailscale LoadBalancer, be aware of these potential issues:

#### 1. DNS Resolution Behavior

- **Random IP Selection**:
  - DNS resolvers may randomize A record order
  - Clients might try unreachable IP first (brief delay)
  - Solution: Rely on OS routing preferences and connection timeouts

- **VPN vs Local Network**:
  - Local devices with Tailscale might prefer VPN route
  - Usually mitigated by lower latency of local network
  - Monitor client connection patterns if performance issues arise

- **Public Internet Access**:
  - Both IPs (192.168.1.x and 100.x.x.x) are non-routable
  - Expect connection attempts from internet scanners
  - Monitor logs but no action needed (security by design)

#### 2. Certificate Management

- **Wildcard Certificate Requirements**:
  - Using single wildcard cert for all ingresses
  - Must use DNS01 challenge (HTTP01 impossible for private IPs)
  - Ensure Cloudflare token permissions remain valid

- **DNS Propagation**:
  - DNS01 challenges depend on proper external-dns setup
  - Watch cert-manager logs for renewal issues
  - Keep Cloudflare API token permissions updated

#### 3. Tailscale IP Management

- **IP Address Changes**:
  - Tailscale IPs can change on operator restart
  - External-DNS handles updates automatically
  - Expect brief propagation delays during changes

- **Service Recreation**:
  - New services might get different Tailscale IPs
  - Operator tries to maintain IP consistency
  - Monitor during cluster maintenance

#### 4. External-DNS Configuration

- **Multiple Services, Same Hostname**:

  ```yaml
  annotations:
    external-dns.alpha.kubernetes.io/hostname: "*.soyspray.vip"
  ```

  - Both services update same DNS record
  - Use `policy: sync` to prevent ownership conflicts
  - Watch for repeated record updates in logs

#### 5. Traffic Management

- **Shared Ingress Controller**:
  - Both paths use same ingress-nginx pods
  - Logs don't distinguish traffic source (MetalLB vs Tailscale)
  - Consider adding source annotations if needed

- **Monitoring Considerations**:
  - Single wildcard cert for all traffic
  - TLS handshakes look identical
  - Add custom headers/logging for path tracking

#### 6. Network Routing

- **Path Selection**:
  - OS routing usually prefers available path
  - Local network typically chosen over Tailscale
  - Test both paths during implementation

- **Firewall Rules**:
  - Check NAT handling for both paths
  - Ensure return traffic isn't blocked
  - Document any special firewall rules

#### 7. Kubespray Integration

- **Service Management**:

  ```yaml
  # Kubespray-managed (DO NOT MODIFY):
  - ingress-nginx service (MetalLB)
  - MetalLB configuration

  # Managed separately:
  - ingress-nginx-tailscale service
  - Tailscale operator configuration
  ```

- **Upgrade Considerations**:
  - Keep Tailscale services in separate manifests
  - Watch for Kubespray changes during upgrades
  - Document service ownership clearly

#### Monitoring Checklist

Regular checks for healthy dual-access:

```bash
# 1. Check DNS Records
dig *.soyspray.vip

# 2. Verify Services
kubectl get svc -n ingress-nginx

# 3. Monitor External-DNS
kubectl logs -n external-dns -l app.kubernetes.io/name=external-dns

# 4. Check Cert-Manager
kubectl get certificates -A
kubectl get certificaterequests -A

# 5. Verify Tailscale Status
kubectl logs -n tailscale-system -l app.kubernetes.io/name=operator
```

### Current Architecture

```
External Clients                                     Local Network Clients
(with Tailscale VPN)                                (192.168.1.0/24)
       │                                                   │
       │                                                   │
       ▼                                                   ▼
   Tailscale                                         Local Router
[100.102.114.103]                                [192.168.1.120]
       │                                                   │
       │                                                   │
       └──────────────────────┬───────────────────────────┘
                             │
                             ▼
                    DNS: *.soyspray.vip
                    [Cloudflare DNS]
                    A → 192.168.1.120
                    A → 100.102.114.103
                             │
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
    Service: ingress-nginx      Service: ingress-nginx-tailscale
    Type: LoadBalancer          Type: LoadBalancer
    IP: 192.168.1.120          IP: 100.102.114.103
    (Managed by Kubespray)      (Managed by ArgoCD)
              │                             │
              └──────────────┬──────────────┘
                            │
                            ▼
                   Ingress-NGINX Pods
                   (Same pods for both services)
                            │
                            ▼
                   Kubernetes Services
                   (Various applications)
```

### Components

1. **DNS Layer**:
   - External-DNS managing Cloudflare records
   - Dual A records for *.soyspray.vip
   - Automatic updates when IPs change

2. **Access Layer**:
   - Tailscale VPN access: 100.102.114.103
   - Local network access: 192.168.1.120
   - Zero-trust security model

3. **Service Layer**:
   - Two LoadBalancer services
   - Same ingress-nginx backend pods
   - Shared SSL termination

4. **Management**:
   - MetalLB service: Managed by Kubespray
   - Tailscale service: Managed by ArgoCD
   - Cert-Manager: DNS01 challenges via Cloudflare
