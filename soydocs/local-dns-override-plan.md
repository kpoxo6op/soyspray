# Local DNS Override Plan

## Overview

This document outlines the plan to implement local DNS override (split-horizon DNS) for unified domain access to cluster services. The goal is to use a single hostname that resolves to different IPs based on the client's location (local vs. VPN/external).

## Target Architecture

```mermaid
graph TB
    subgraph "Unified DNS Architecture"
        subgraph "Local Network"
            L[Local Users] --> LD[Local DNS Server]
            LD --> |Override| IP1[192.168.1.x]
            LD --> |Conditional Forward| CF[Cloudflare DNS]
        end

        subgraph "External Access"
            V[VPN Users] --> CF
            CF --> IP2[100.x.x.x]
        end

        subgraph "Unified Resources"
            H[podinfo.test.soyspray.vip/]
            C[Single Certificate]
            ING[Single Ingress]

            H --> C
            H --> ING
        end

        L & V --> H
    end
```

## DNS Resolution Flow

```mermaid
sequenceDiagram
    participant Client
    participant LocalDNS as Local DNS Server
    participant Router
    participant Cloudflare as Cloudflare DNS
    participant K8s as Kubernetes

    alt Local Network Query
        Client->>Router: DHCP Request
        Router-->>Client: Use Local DNS Server
        Client->>LocalDNS: Query podinfo.test.soyspray.vip/
        LocalDNS-->>Client: Return 192.168.1.x
        Client->>K8s: Direct Access
    else External/VPN Query
        Client->>Cloudflare: Query podinfo.test.soyspray.vip/
        Cloudflare-->>Client: Return 100.x.x.x
        Client->>K8s: Access via Tailscale
    end
```
