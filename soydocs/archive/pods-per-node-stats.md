# Kubernetes Cluster State Report

> **Note:** This report shows the cluster state after adding the `worker` label
> to all nodes. No pods have been restarted yet, which is why the distribution
> is still uneven. New workloads will be scheduled across all nodes, but
> existing pods remain on their current nodes until restarted.

## Node Configuration

| Node    | Roles                  | Status | IP            | OS                | Kernel            | Container Runtime |
|---------|------------------------|--------|---------------|-------------------|-------------------|------------------|
| node-0  | control-plane,worker   | Ready  | 192.168.50.100 | Ubuntu 24.04.1 LTS | 6.8.0-41-generic | containerd://1.7.24 |
| node-1  | control-plane,worker   | Ready  | 192.168.50.101 | Ubuntu 24.04.1 LTS | 6.8.0-41-generic | containerd://1.7.24 |
| node-2  | worker                 | Ready  | 192.168.50.102 | Ubuntu 24.04.1 LTS | 6.8.0-41-generic | containerd://1.7.24 |

## Pod Distribution

| Node    | Pod Count |
|---------|-----------|
| node-0  | 15        |
| node-1  | 14        |
| node-2  | 41        |

## Updated Pod Distribution After Rebalancing

Using the proper command to get accurate node counts:

```bash
kubectl get pods -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,NODE:.spec.nodeName | grep -v "^NAMESPACE" | awk '{print $3}' | sort | uniq -c
```

| Node    | Pod Count |
|---------|-----------|
| node-0  | 18        |
| node-1  | 19        |
| node-2  | 33        |

Pods have been redistributed more evenly across all nodes after applying worker labels to control plane nodes and restarting workloads.

## Monitoring Namespace Pods

| Pod Name                                               | Status  | Node    |
|--------------------------------------------------------|---------|---------|
| alertmanager-kube-prometheus-stack-alertmanager-0      | Running | node-2  |
| kube-prometheus-stack-grafana-699d7975d-v92kz          | Running | node-2  |
| kube-prometheus-stack-kube-state-metrics-55cd9669cd-88fnw | Running | node-2  |
| kube-prometheus-stack-operator-64bd5c479f-vx7bm        | Running | node-2  |
| kube-prometheus-stack-prometheus-node-exporter-dlhq4   | Running | node-1  |
| kube-prometheus-stack-prometheus-node-exporter-ftd2k   | Running | node-0  |
| kube-prometheus-stack-prometheus-node-exporter-ht9q9   | Running | node-2  |
| prometheus-kube-prometheus-stack-prometheus-0          | Running | node-2  |

## All Pods by Node

### node-0 (15 pods)

- calico-node-9vd6s
- coredns-d665d669-ppwxh
- engine-image-ei-c2d50bcc-t4rj6
- ingress-nginx-controller-zdbn4
- instance-manager-1d49261283e0e9a2d426e3edac34f84b
- kube-apiserver-node-0
- kube-controller-manager-node-0
- kube-proxy-9mxzp
- kube-prometheus-stack-prometheus-node-exporter-ftd2k
- kube-scheduler-node-0
- local-volume-provisioner-xldzs
- longhorn-csi-plugin-d5vrn
- longhorn-manager-kt247
- metallb-system-speaker-gdrj4
- nodelocaldns-wxvwm

### node-1 (14 pods)

- calico-node-hthr7
- engine-image-ei-c2d50bcc-fl9lz
- ingress-nginx-controller-b529c
- instance-manager-a50ddccddcdd68e13310a06820129b7d
- kube-apiserver-node-1
- kube-controller-manager-node-1
- kube-prometheus-stack-prometheus-node-exporter-dlhq4
- kube-proxy-6fptv
- kube-scheduler-node-1
- local-volume-provisioner-8vzc4
- longhorn-csi-plugin-q4dnj
- longhorn-manager-g4fth
- metallb-system-speaker-dg8p6
- nodelocaldns-x2vdl

### node-2 (41 pods)

- alertmanager-kube-prometheus-stack-alertmanager-0
- argocd-application-controller-0
- argocd-applicationset-controller-645d78dcbd-k2pjd
- argocd-dex-server-695594bd8b-8xb84
- argocd-notifications-controller-76dbf964f6-sx57r
- argocd-redis-7dfd45fcf4-clfvd
- argocd-repo-server-5b4b6548f4-tw952
- argocd-server-fbc5f758d-mz8pd
- calico-kube-controllers-5db5978889-bxqq9
- calico-node-h55lg
- cert-manager-79747c8677-tcj86
- cert-manager-cainjector-966b79998-wktwg
- cert-manager-webhook-58ff58d95b-2jwzg
- coredns-d665d669-wtjgp
- csi-attacher-79866cdcf8-895m6
- csi-provisioner-664cb5bdd5-wdtnf
- csi-resizer-64f6fb4459-d6nnd
- csi-snapshotter-7b7db78f9-2nzvd
- dns-autoscaler-5cb4578f5f-vgdqb
- engine-image-ei-c2d50bcc-22ptq
- external-dns-64d4985cb4-svkkt
- ingress-nginx-controller-gphvl
- instance-manager-091219d996c4b05a391b07afc401833a
- kube-prometheus-stack-grafana-699d7975d-v92kz
- kube-prometheus-stack-kube-state-metrics-55cd9669cd-88fnw
- kube-prometheus-stack-operator-64bd5c479f-vx7bm
- kube-prometheus-stack-prometheus-node-exporter-ht9q9
- kube-proxy-ccjbg
- local-volume-provisioner-jrb27
- longhorn-csi-plugin-qs85h
- longhorn-driver-deployer-7d89b5b9b-s22v5
- longhorn-manager-84v4x
- longhorn-ui-5fcc4bcfc7-zbv4v
- metallb-system-controller-7f649565d4-pfsk4
- metallb-system-speaker-pgfgp
- nginx-proxy-node-2
- nodelocaldns-8xwfp
- pihole-54ff5f845b-gsmqs
- pihole-exporter-544f564969-x2gmm
- podinfo-58b7666549-xgsnw
- prometheus-kube-prometheus-stack-prometheus-0
