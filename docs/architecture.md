# Architecture

Soyspray separates ownership so that routine application delivery does not
silently change the cluster foundation.

```text
Git pull request
├── Kubespray and Ansible -> nodes, bootstrap inputs, recovery operations
└── Argo CD               -> application workloads from main
    └── application       -> manifests, checks, data and recovery contract
```

## Main boundaries

- The cluster has three nodes so ordinary maintenance can preserve service
  while one node is unavailable.
- Kubespray owns Kubernetes installation and cluster-wide configuration.
- Argo CD owns declared workloads and follows the reviewed `main` branch.
- The monitoring stack and CRDs retain non-pruning owners. A separate
  `prometheus-config` child may prune only generated dashboards and custom
  alert rules in `monitoring`, so Git removal and rollback remove those inputs.
- Longhorn provides replicated persistent volumes and native backup records.
- Stateful applications keep their recovery contract beside their manifests.
- Recovery keys and private bootstrap inputs stay outside the cluster and Git.

The [Argo CD root](https://github.com/kpoxo6op/soyspray/tree/main/argocd)
contains the application catalogue. The [Kubespray inventory](https://github.com/kpoxo6op/soyspray/tree/main/inventory/soycluster)
contains the declared cluster membership. The pinned provisioner is unchanged;
its upstream migration is blocked by cert-manager namespace deletion and
requires parity before any full reconciliation.

## Incident pipeline

Prometheus owns health detection. Alertmanager sends native critical and warning
alerts to Telegram and keeps the independent Watchdog route. Alloy exports
bounded failure counters and sends searchable logs to Loki. Inspect logs in
Grafana when an alert needs context. Missing evidence is unknown; absence of an
alert does not establish recovery. There is no supplemental diagnosis writer.
