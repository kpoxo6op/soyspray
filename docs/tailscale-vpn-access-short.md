# Tailscale VPN Access - Quick Guide

## Goal
Access home k8s cluster services from anywhere using Tailscale VPN, with automatic DNS resolution:
- Local network: `*.soyspray.vip` → 192.168.1.120
- Remote access: `*.ts.soyspray.vip` → 100.102.114.103

## Connection Flow
```
                                                     ┌─────────────────┐
                                                     │                 │
                                                     │ Cloudflare DNS  │
                                                     │                 │
                                                     └────────┬────────┘
                                                              │
                                                              │
┌──────────────┐          ┌──────────────┐          ┌────────┴────────┐
│              │          │              │          │                 │
│  Local PC    │◄────────►│ Home Router  │◄────────►│ Home K8s        │
│              │          │              │          │ Cluster         │
└──────┬───────┘          └──────────────┘          └────────┬────────┘
       │                                                      │
       │                  ┌──────────────┐                    │
       │                  │              │                    │
       └──────────────────► Tailscale    ◄────────────────────┘
                         │ Network       │
                         │              │
                         └──────────────┘
```

## How it Works
- Local access: Browser → Router → K8s Cluster (MetalLB IP)
- Remote access: Browser → Tailscale Network → K8s Cluster (Tailscale IP)

## TODO to Reach Goal
1. Install Tailscale operator in cluster
   - Deploy via ArgoCD
   - Configure OAuth credentials

2. Configure DNS
   - Set up external-dns with Cloudflare
   - Configure wildcard domains:
     - `*.soyspray.vip` for local access
     - `*.ts.soyspray.vip` for Tailscale access

3. Configure Services
   - Set up MetalLB for local LoadBalancer
   - Configure Tailscale LoadBalancer
   - Add correct annotations for DNS management

4. Test Access
   - Verify local DNS resolution
   - Test Tailscale VPN connection
   - Confirm automatic DNS switching
