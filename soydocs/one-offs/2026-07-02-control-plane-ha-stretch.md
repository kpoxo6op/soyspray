# Control Plane HA Stretch

Date: 2026-07-02

Purpose: stretch the cluster so one node can be lost temporarily. Node-0 still
has the external media disk and MQTT/gateway hardware, so those remain manual
move/replug exceptions.

## Current Shape

```text
node-0
  kube-apiserver
  kube-controller-manager
  kube-scheduler
  etcd
  worker
  Longhorn SSD
  external media disk
  MQTT/gateway hardware

node-1
  worker
  Longhorn SSD

node-2
  worker
  Longhorn SSD
```

This survives losing node-1 or node-2 for many workloads, but losing node-0
takes away the API server, scheduler, controller manager, and etcd.

## Target Shape

```text
              API VIP
           192.168.20.13
                 |
     +-----------+-----------+
     |           |           |
  node-0      node-1      node-2
  api         api         api
  etcd        etcd        etcd
  worker      worker      worker
  SSD         SSD         SSD
```

After the stretch, the cluster should tolerate any one node being down:

```text
lose node-0 -> node-1 + node-2 keep etcd quorum and the API VIP
lose node-1 -> node-0 + node-2 keep etcd quorum and the API VIP
lose node-2 -> node-0 + node-1 keep etcd quorum and the API VIP
```

This is one-node tolerance only. Two nodes down is still an outage.

## Known Exceptions

```text
node-0 external media disk -> unavailable until replugged or moved
node-0 MQTT/gateway device -> unavailable until replugged or moved
local-media workloads      -> intentionally tied to node-0 media
```

## Validation

Before the HA config is merged, the checker should pass in current repo mode:

```bash
scripts/check-ha-stretch.sh --expect-current --repo-only
```

After the HA config PR, the repo should pass target mode:

```bash
scripts/check-ha-stretch.sh --expect-ha --repo-only --vip 192.168.20.13
```

After the Kubespray apply, the live cluster should pass target mode:

```bash
scripts/check-ha-stretch.sh --expect-ha --live --vip 192.168.20.13
```

The live check must prove:

- all three nodes are Ready
- all three nodes have the control-plane role
- API, controller-manager, and scheduler static pods run on all three nodes
- etcd has three members and peer URLs on `192.168.20.10-12`
- kube-vip runs on all three control-plane nodes
- the API VIP answers `/readyz`
- CoreDNS has at least two available replicas
- Longhorn volumes are healthy with at least three replicas
- Argo CD apps are Synced and Healthy

## Important Preflight Finding

On 2026-07-02, live etcd still reported node-0's peer URL as
`https://192.168.1.10:2380` while the client URL was already
`https://192.168.20.10:2379`. That old peer URL is harmless with one etcd
member but unsafe before adding node-1 and node-2 to etcd. The HA stretch is not
done until etcd peer URLs are the current LAN addresses:

```text
https://192.168.20.10:2380
https://192.168.20.11:2380
https://192.168.20.12:2380
```
